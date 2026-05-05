"""Phase A regression tests — chat handler MUST round-trip the router's full
ChatTurnResult through `/api/v1/chat`.

Pins the chat-endpoint side of the Phase A contract:
  - Response JSON includes top-level final_text, messages, tool_trace.
  - The handler does NOT collapse to `input + final_text` (the bug Phase A fixes).
  - PR20 short-circuit and real LLM-loop paths produce structurally identical
    top-level keys (canonical baseline = the short-circuit's existing
    message-preserving shape).

Tests fail on current main:
  - `from forge_bridge.llm.router import ChatTurnResult` — ImportError.
  - Even mocked, handlers.py:1205 collapses to input+final_text.
  - Short-circuit/LLM-loop top-level keys diverge (final_text, tool_trace
    do not exist in either response yet).
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


# ---------------------------------------------------------------------------
# LLM-loop path — handler must surface the router's full ChatTurnResult
# ---------------------------------------------------------------------------


def test_llm_loop_response_includes_final_text_messages_and_tool_trace():
    """When the LLM loop runs, the response JSON has:
      - final_text (top-level)
      - messages preserving any tool activity from the router
      - tool_trace mirroring that activity
    Fails on main: handler collapses to input+final_text; final_text/tool_trace
    keys do not exist."""
    mock_router = MagicMock()

    fake_messages = [
        {"role": "user", "content": "show projects"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{
                "id": "call_xyz",
                "type": "function",
                "function": {
                    "name": "forge_list_projects",
                    "arguments": "{}",
                },
            }],
        },
        {
            "role": "tool",
            "tool_call_id": "call_xyz",
            "name": "forge_list_projects",
            "content": '{"projects": []}',
        },
        {"role": "assistant", "content": "There are no projects yet."},
    ]
    fake_trace = [{
        "tool_name": "forge_list_projects",
        "arguments": {},
        "result": {"projects": []},
        "error": None,
        "index": 0,
    }]
    mock_router.complete_with_tools = AsyncMock(
        return_value=ChatTurnResult(
            final_text="There are no projects yet.",
            messages=fake_messages,
            tool_trace=fake_trace,
        )
    )

    app, _ = _build_app_with_router(
        mock_router,
        [_tool("forge_list_projects"), _tool("forge_ping")],
    )

    with patch(
        "forge_bridge.mcp.server.mcp.list_tools",
        new=AsyncMock(return_value=[_tool("forge_list_projects"), _tool("forge_ping")]),
    ), patch(
        "forge_bridge.console.handlers.filter_tools_by_reachable_backends",
        side_effect=_passthrough_filter,
    ):
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "general query"}]},
        )

    assert r.status_code == 200, r.text
    body = r.json()

    assert "final_text" in body, "response missing top-level final_text"
    assert body["final_text"] == "There are no projects yet."

    assert "tool_trace" in body, "response missing top-level tool_trace"
    assert body["tool_trace"] == fake_trace

    # messages must include both the assistant tool_calls turn AND the role:tool entry.
    roles = [m["role"] for m in body["messages"]]
    assert "tool" in roles, (
        f"handler dropped the tool message from the LLM-loop path: {body['messages']!r}"
    )
    assert any(
        m["role"] == "assistant" and m.get("tool_calls")
        for m in body["messages"]
    ), f"handler dropped the assistant tool_calls turn: {body['messages']!r}"

    # Final message MUST be the terminal assistant turn with string content.
    assert body["messages"][-1]["role"] == "assistant"
    assert body["messages"][-1]["content"] == "There are no projects yet."


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


def test_short_circuit_and_llm_loop_have_identical_top_level_keys():
    """Structural parity invariant: both response paths produce the same
    top-level key set. Phase A's failure-visibility contract requires that
    the schema does not vary by path. Fails on main: top-level keys differ
    (LLM-loop lacks final_text/tool_trace; short-circuit has tool_forced
    but neither path exposes the new keys)."""
    tools = [_tool("forge_ping"), _tool("forge_list_projects")]

    async def _call_tool(name, args):
        block = MagicMock()
        block.text = '{"status":"ok"}'
        return [block]

    # ---- 1. Short-circuit path response keys --------------------------------
    mock_router_sc = MagicMock()
    mock_router_sc.complete_with_tools = AsyncMock(return_value=ChatTurnResult(
        final_text="UNREACHED", messages=[], tool_trace=[],
    ))
    app_sc, _ = _build_app_with_router(mock_router_sc, tools)
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
        r_sc = TestClient(app_sc).post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "ping"}]},
        )
    body_sc = r_sc.json()
    assert body_sc.get("stop_reason") == "tool_forced"

    # ---- 2. LLM-loop path response keys -------------------------------------
    mock_router_loop = MagicMock()
    mock_router_loop.complete_with_tools = AsyncMock(return_value=ChatTurnResult(
        final_text="hello",
        messages=[
            {"role": "user", "content": "general query"},
            {"role": "assistant", "content": "hello"},
        ],
        tool_trace=[],
    ))
    app_loop, _ = _build_app_with_router(mock_router_loop, tools)
    with patch(
        "forge_bridge.mcp.server.mcp.list_tools",
        new=AsyncMock(return_value=tools),
    ), patch(
        "forge_bridge.console.handlers.filter_tools_by_reachable_backends",
        side_effect=_passthrough_filter,
    ):
        r_loop = TestClient(app_loop).post(
            "/api/v1/chat",
            # generic query — prefilter falls back to full list, no short-circuit.
            json={"messages": [{"role": "user", "content": "tell me a story"}]},
        )
    body_loop = r_loop.json()
    assert body_loop.get("stop_reason") == "end_turn"

    # ---- Structural parity invariant ----------------------------------------
    assert set(body_sc.keys()) == set(body_loop.keys()), (
        f"top-level key sets diverge:\n"
        f"  short-circuit: {sorted(body_sc.keys())}\n"
        f"  llm-loop:      {sorted(body_loop.keys())}\n"
        f"Phase A invariant: both paths must expose the same canonical schema."
    )
    # And the new keys must actually be present.
    for key in ("final_text", "messages", "tool_trace"):
        assert key in body_sc, f"short-circuit missing {key!r}"
        assert key in body_loop, f"llm-loop missing {key!r}"
