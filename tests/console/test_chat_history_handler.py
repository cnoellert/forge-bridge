"""A.1 chat-history disposition tests.

The agentic LLM-loop response-shape contract retired with the A.1 compile
branch. This file now preserves the surviving PR20 short-circuit handler
contract: short-circuit responses still expose final_text and tool_trace.
"""
from __future__ import annotations

import pytest
from mcp.types import Tool
from starlette.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from forge_bridge.console import _rate_limit
from forge_bridge.console.app import build_console_app
from forge_bridge.console.manifest_service import ManifestService
from forge_bridge.console.read_api import ConsoleReadAPI
from forge_bridge.llm.router import ChatTurnResult


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    _rate_limit._reset_for_tests()
    yield
    _rate_limit._reset_for_tests()


def _tool(name: str) -> Tool:
    return Tool(
        name=name,
        description=f"test tool {name}",
        inputSchema={"type": "object", "properties": {}, "required": []},
    )


async def _passthrough_filter(tools):
    return tools


def _build_app_with_router(mock_router, registered_tools):
    """Build a TestClient + app whose chat endpoint dispatches to mock_router."""
    ms = ManifestService()
    mock_log = MagicMock()
    mock_log.snapshot.return_value = ([], 0)
    api = ConsoleReadAPI(
        execution_log=mock_log,
        manifest_service=ms,
        llm_router=mock_router,
    )
    app = build_console_app(api)
    return app, registered_tools


def test_short_circuit_response_includes_final_text_and_tool_trace():
    """The PR20 short-circuit path also exposes final_text and tool_trace.
    Fails on main: short-circuit response lacks both keys today."""
    mock_router = MagicMock()
    mock_router.complete_with_tools = AsyncMock(return_value=ChatTurnResult(
        final_text="UNREACHED", messages=[], tool_trace=[],
    ))

    # Two tools registered so PR20's `tools_filtered_count < tools_available_count`
    # guard can fire when the prefilter narrows to 1.
    tools = [_tool("forge_ping"), _tool("forge_list_projects")]

    fake_call_result = MagicMock()
    fake_call_result.__iter__ = lambda self: iter([{"text": '{"status":"ok"}'}])

    async def _call_tool(name, args):
        # Mimic FastMCP shape: returns an iterable of TextContent-like objects.
        block = MagicMock()
        block.text = '{"status":"ok"}'
        return [block]

    app, _ = _build_app_with_router(mock_router, tools)

    with patch(
        "forge_bridge.mcp.server.mcp.list_tools",
        new=AsyncMock(return_value=tools),
    ), patch(
        "forge_bridge.console.handlers.filter_tools_by_reachable_backends",
        side_effect=_passthrough_filter,
    ), patch(
        "forge_bridge.mcp.server.mcp.call_tool",
        new=AsyncMock(side_effect=_call_tool),
    ):
        client = TestClient(app)
        # "ping" matches forge_ping but not forge_list_projects → prefilter
        # narrows to 1 → short-circuit fires.
        r = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "ping the daemon"}]},
        )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("stop_reason") == "tool_forced", (
        f"expected short-circuit, got {body.get('stop_reason')!r}: {body!r}"
    )
    assert "final_text" in body, "short-circuit response missing final_text"
    assert "tool_trace" in body, "short-circuit response missing tool_trace"
    # Short-circuit does not run the LLM, so final_text is empty by Phase A
    # decision (the model never spoke).
    assert body["final_text"] == ""
    # Short-circuit fired exactly one tool — trace has one entry.
    assert len(body["tool_trace"]) == 1
    assert body["tool_trace"][0]["tool_name"] == "forge_ping"
    assert body["tool_trace"][0]["index"] == 0
