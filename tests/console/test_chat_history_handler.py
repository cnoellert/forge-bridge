"""A.1/CR.1 chat-history disposition tests.

The agentic LLM-loop response-shape contract retired with the A.1 compile
branch. This file now preserves the surviving PR20 short-circuit handler
contract: short-circuit responses still expose final_text and tool_trace, and
CR.1 answers successful single-result read tools through messages.
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
    mock_router.acomplete = AsyncMock(return_value="The daemon is ok.")
    mock_router.local_model = "qwen-test"

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

    emit_capture = MagicMock()
    with patch(
        "forge_bridge.mcp.server.mcp.list_tools",
        new=AsyncMock(return_value=tools),
    ), patch(
        "forge_bridge.console.handlers.filter_tools_by_reachable_backends",
        side_effect=_passthrough_filter,
    ), patch(
        "forge_bridge.mcp.server.mcp.call_tool",
        new=AsyncMock(side_effect=_call_tool),
    ), patch(
        "forge_bridge.console.handlers.emit_comprehension_capture",
        emit_capture,
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
    assert body["messages"] == [{
        "role": "assistant",
        "content": "The daemon is ok.",
    }]
    # Short-circuit fired exactly one tool — trace has one entry.
    assert len(body["tool_trace"]) == 1
    assert body["tool_trace"][0]["tool_name"] == "forge_ping"
    assert body["tool_trace"][0]["index"] == 0
    mock_router.acomplete.assert_awaited_once()
    emit_capture.assert_called_once_with(
        question="ping the daemon",
        chain=[{"step": "forge_ping {}", "result": {"status": "ok"}}],
        answer="The daemon is ok.",
        wall_clock_ms=emit_capture.call_args.kwargs["wall_clock_ms"],
        model="qwen-test",
    )


def test_short_circuit_non_json_result_preserves_trace_without_answer():
    """A non-JSON forced-tool result cannot fail the already-succeeded read."""
    mock_router = MagicMock()
    mock_router.complete_with_tools = AsyncMock(return_value=ChatTurnResult(
        final_text="UNREACHED", messages=[], tool_trace=[],
    ))
    mock_router.acomplete = AsyncMock(return_value="UNREACHED")
    tools = [_tool("forge_ping"), _tool("forge_list_projects")]

    async def _call_tool(name, args):
        block = MagicMock()
        block.text = "plain text result"
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
        r = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "ping the daemon"}]},
        )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["stop_reason"] == "tool_forced"
    assert body["final_text"] == ""
    assert len(body["messages"]) == 3
    assert body["messages"][1]["tool_calls"][0]["function"]["name"] == "forge_ping"
    assert body["messages"][2]["content"] == "plain text result"
    assert body["tool_trace"][0]["result"] == "plain text result"
    mock_router.acomplete.assert_not_awaited()


def test_short_circuit_answer_failure_preserves_trace():
    """Forced read synthesis failures degrade to the existing trace envelope."""
    mock_router = MagicMock()
    mock_router.complete_with_tools = AsyncMock(return_value=ChatTurnResult(
        final_text="UNREACHED", messages=[], tool_trace=[],
    ))
    mock_router.acomplete = AsyncMock(side_effect=RuntimeError("ollama down"))
    tools = [_tool("forge_ping"), _tool("forge_list_projects")]

    async def _call_tool(name, args):
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
        r = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "ping the daemon"}]},
        )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["stop_reason"] == "tool_forced"
    assert body["final_text"] == ""
    assert len(body["messages"]) == 3
    assert body["messages"][2]["content"] == '{"status":"ok"}'
    assert body["tool_trace"][0]["result"] == {"status": "ok"}
    mock_router.acomplete.assert_awaited_once()


def test_short_circuit_tool_error_emits_failure_capture():
    """Forced-tool errors are captured with an outcome tag, but still return."""
    mock_router = MagicMock()
    mock_router.complete_with_tools = AsyncMock(return_value=ChatTurnResult(
        final_text="UNREACHED", messages=[], tool_trace=[],
    ))
    mock_router.local_model = "qwen-test"
    tools = [_tool("forge_ping"), _tool("forge_list_projects")]

    async def _call_tool(name, args):
        raise RuntimeError("tool failed")

    app, _ = _build_app_with_router(mock_router, tools)
    emit_capture = MagicMock()

    with patch(
        "forge_bridge.mcp.server.mcp.list_tools",
        new=AsyncMock(return_value=tools),
    ), patch(
        "forge_bridge.console.handlers.filter_tools_by_reachable_backends",
        side_effect=_passthrough_filter,
    ), patch(
        "forge_bridge.mcp.server.mcp.call_tool",
        new=AsyncMock(side_effect=_call_tool),
    ), patch(
        "forge_bridge.console.handlers.emit_comprehension_capture",
        emit_capture,
    ):
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "ping the daemon"}]},
        )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["stop_reason"] == "tool_forced"
    assert body["tool_trace"][0]["error"] == "RuntimeError: tool failed"
    emit_capture.assert_called_once_with(
        question="ping the daemon",
        chain=[{
            "step": "forge_ping {}",
            "result": {
                "error": {
                    "type": "RuntimeError",
                    "message": "tool failed",
                },
            },
        }],
        answer="",
        wall_clock_ms=0,
        model="qwen-test",
        outcome="forced_tool_error",
    )
