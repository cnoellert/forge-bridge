"""Unit tests for forge_bridge/console/handlers.py chat_handler (CHAT-01/02 + D-14a).

All tests use a mocked LLMRouter.compile_intent (no real Ollama dep).
Rate-limit module is reset before each test for isolation. Tool registry
snapshot is patched to return a fixed Tool list so the empty-registry guard
does NOT short-circuit.
"""
from __future__ import annotations

import asyncio
import json
import logging

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from starlette.testclient import TestClient

from forge_bridge.console import _rate_limit
from forge_bridge.console.app import build_console_app
from forge_bridge.console.manifest_service import ManifestService
from forge_bridge.console.read_api import ConsoleReadAPI
from forge_bridge.llm.router import LLMToolError, RecursiveToolLoopError

@pytest.fixture(autouse=True)
def _reset_rate_limit():
    """Reset bucket state before AND after every test for isolation."""
    _rate_limit._reset_for_tests()
    yield
    _rate_limit._reset_for_tests()


def _make_test_tool():
    """A non-empty Tool so chat_handler's empty-registry guard does not fire."""
    from mcp.types import Tool
    return Tool(
        name="forge_test_probe",
        description="Test probe tool for chat handler unit tests.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    )


async def _passthrough_filter(tools):
    """Default filter stub: passes all tools through. Used in chat_client fixture
    so that existing tests (which don't test filtering) are not broken by the real
    TCP probe attempting to connect to :9999 in test context."""
    return tools


@pytest.fixture
def chat_client():
    """TestClient with mocked LLMRouter.compile_intent.

    Patches forge_bridge.mcp.server.mcp.list_tools at the import path the
    handler resolves (`from forge_bridge.mcp import server as _mcp_server;
    await _mcp_server.mcp.list_tools()`) so the empty-registry guard does
    NOT short-circuit any test.

    Also patches filter_tools_by_reachable_backends to pass all tools through
    (no TCP probe in test context). Tests that exercise filtering behavior provide
    their own patch that overrides this default.
    """
    mock_router = MagicMock()
    mock_router.compile_intent = AsyncMock(return_value=["forge_test_probe"])
    mock_router.complete_with_tools = AsyncMock()

    ms = ManifestService()
    mock_log = MagicMock()
    mock_log.snapshot.return_value = ([], 0)
    api = ConsoleReadAPI(
        execution_log=mock_log,
        manifest_service=ms,
        llm_router=mock_router,
    )
    app = build_console_app(api)

    with patch(
        "forge_bridge.mcp.server.mcp.list_tools",
        new=AsyncMock(return_value=[_make_test_tool()]),
    ), patch(
        "forge_bridge.console.handlers.filter_tools_by_reachable_backends",
        side_effect=_passthrough_filter,
    ), patch(
        "forge_bridge.console._chat_compile.run_chain_steps",
        new=AsyncMock(return_value={
            "status": "success",
            "request_id": "test-request",
            "chain": [{"step": "forge_test_probe", "result": {"ok": True}}],
            "error": None,
        }),
    ):
        yield TestClient(app), mock_router


# ── Happy path ─────────────────────────────────────────────────────────────────


# ── 422 validation paths ───────────────────────────────────────────────────────

def test_chat_invalid_json_body_returns_422(chat_client):
    client, _ = chat_client
    r = client.post(
        "/api/v1/chat",
        content=b"{not json",
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 422
    body = r.json()
    assert body["error"]["code"] == "validation_error"
    assert "X-Request-ID" in r.headers


def test_chat_missing_messages_field_returns_422(chat_client):
    client, _ = chat_client
    r = client.post("/api/v1/chat", json={"foo": "bar"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_chat_unsupported_role_returns_422(chat_client):
    client, _ = chat_client
    r = client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "system", "content": "hi"}]},
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "unsupported_role"


def test_chat_planner_front_timeout_returns_store_unavailable(chat_client):
    client, _ = chat_client

    async def _hang(*args, **kwargs):
        await asyncio.sleep(10)

    with patch(
        "forge_bridge.console._planner_front.run_planner_front",
        new=AsyncMock(side_effect=_hang),
    ), patch(
        "forge_bridge.console.handlers._PLANNER_FRONT_TIMEOUT_S",
        0.01,
    ):
        r = client.post(
            "/api/v1/chat?planner_front=true",
            json={"messages": [{"role": "user", "content": "show me shots"}]},
        )

    assert r.status_code == 200
    body = r.json()
    assert body["stop_reason"] == "store_unavailable"
    assert "can't reach the project store" in body["final_text"]
    assert body["plan"] == []
    assert body["chain"] == []


# ── 429 rate limit ─────────────────────────────────────────────────────────────

def test_chat_rate_limit_returns_429_with_retry_after(chat_client):
    client, _ = chat_client
    payload = {"messages": [{"role": "user", "content": "hi"}]}
    # First 10 requests succeed (capacity=10 per D-13)
    for _ in range(10):
        r = client.post("/api/v1/chat", json=payload)
        assert r.status_code == 200, r.text
    # 11th request exceeds capacity
    r = client.post("/api/v1/chat", json=payload)
    assert r.status_code == 429
    body = r.json()
    assert body["error"]["code"] == "rate_limit_exceeded"
    assert "Retry-After" in r.headers
    assert int(r.headers["Retry-After"]) >= 1
    assert "X-Request-ID" in r.headers


# ── 504 timeout paths (D-14a) ──────────────────────────────────────────────────


def test_chat_outer_timeout_returns_504(chat_client):
    """asyncio.TimeoutError from the outer wait_for translates to 504 per D-14a."""
    client, mock_router = chat_client
    mock_router.compile_intent.side_effect = asyncio.TimeoutError()
    r = client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 504
    assert r.json()["error"]["code"] == "request_timeout"


def test_chat_recursive_loop_error_returns_500(chat_client):
    client, mock_router = chat_client
    mock_router.compile_intent.side_effect = RecursiveToolLoopError(
        "test recursive loop"
    )
    r = client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "internal_error"


def test_chat_tool_error_returns_500(chat_client):
    client, mock_router = chat_client
    mock_router.compile_intent.side_effect = LLMToolError("provider 5xx")
    r = client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "internal_error"


# ── Structural / contract pinning ──────────────────────────────────────────────

def test_chat_envelope_shape_is_nested(chat_client):
    """D-17: error envelope is the FB-B nested shape {error: {code, message}}."""
    client, _ = chat_client
    r = client.post("/api/v1/chat", json={"foo": "bar"})  # 422 validation_error
    body = r.json()
    assert "error" in body
    assert isinstance(body["error"], dict)
    assert "code" in body["error"]
    assert "message" in body["error"]
    # Flat shape MUST NOT exist — divergence-from-FB-B test.
    assert "code" not in body
    assert "message" not in body


# ── Plan 16-07 post-rename guard ───────────────────────────────────────────────

def test_ui_chat_handler_renders_panel_template(chat_client):
    """Plan 16-07: post-rename guard — /ui/chat must render chat/panel.html
    (NOT the deleted chat/stub.html). Replaces tests/test_ui_chat_stub.py."""
    client, _ = chat_client
    r = client.get("/ui/chat")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    body = r.text
    # The new live panel mounts the chatPanel Alpine factory.
    assert 'x-data="chatPanel()"' in body
    # The deleted stub copy MUST NOT appear.
    assert "launches in Phase 12" not in body
    assert "chat-stub-card" not in body


# ── Phase 16.1 D-01: backend-aware tool-list filter ───────────────────────────

def test_chat_filters_unreachable_backends(chat_client):
    """D-01: chat handler drops forge_* and flame_* tools whose backends are
    unreachable. Asserts compile_intent() receives only the filtered list.

    Patches forge_bridge.console.handlers.filter_tools_by_reachable_backends
    (the module-top import binding) to simulate no Flame backend reachable.
    """
    from mcp.types import Tool

    client, mock_router = chat_client

    fake_tools = [
        Tool(name="forge_test", description="x", inputSchema={"type": "object"}),
        Tool(name="flame_test", description="x", inputSchema={"type": "object"}),
        Tool(name="synth_test", description="x", inputSchema={"type": "object"}),
    ]

    async def fake_filter(tools):
        # Simulate: only synth_test survives (no Flame, no in-process forge_test)
        return [t for t in tools if t.name.startswith("synth_")]

    with patch(
        "forge_bridge.mcp.server.mcp.list_tools",
        new=AsyncMock(return_value=fake_tools),
    ), patch(
        "forge_bridge.console.handlers.filter_tools_by_reachable_backends",
        side_effect=fake_filter,
    ):
        r = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "hi"}]},
        )

    assert r.status_code == 200, r.text
    forwarded_tools = mock_router.compile_intent.call_args.args[1]
    assert len(forwarded_tools) == 1
    assert forwarded_tools[0].name == "synth_test"


def test_chat_503_when_no_backends_reachable(chat_client):
    """D-01: when filter_tools_by_reachable_backends returns empty list,
    chat handler returns 503 with service_unavailable envelope.
    compile_intent must NOT be called.
    """
    from mcp.types import Tool

    client, mock_router = chat_client

    fake_tools = [
        Tool(name="forge_test", description="x", inputSchema={"type": "object"}),
        Tool(name="flame_test", description="x", inputSchema={"type": "object"}),
    ]

    async def fake_filter_empty(tools):
        return []

    with patch(
        "forge_bridge.mcp.server.mcp.list_tools",
        new=AsyncMock(return_value=fake_tools),
    ), patch(
        "forge_bridge.console.handlers.filter_tools_by_reachable_backends",
        side_effect=fake_filter_empty,
    ):
        r = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "hi"}]},
        )

    assert r.status_code == 503, r.text
    body = r.json()
    assert body["error"]["code"] == "service_unavailable"
    assert "No tool backends reachable" in body["error"]["message"]
    assert "X-Request-ID" in r.headers
    mock_router.compile_intent.assert_not_called()


def test_chat_logs_tools_offered_count_on_success(chat_client, caplog):
    """D-21 extension: success log line includes tools_offered_count field.

    Verifies that after filtering, the chat ok log entry records both
    tool_call_count (existing Phase 16 contract) and tools_offered_count (new).
    """
    from mcp.types import Tool

    client, mock_router = chat_client

    fake_tools = [
        Tool(name="synth_a", description="x", inputSchema={"type": "object"}),
        Tool(name="synth_b", description="x", inputSchema={"type": "object"}),
    ]

    async def fake_filter_two(tools):
        return tools  # return all 2 tools

    with caplog.at_level(logging.INFO, logger="forge_bridge.console.handlers"), \
         patch(
             "forge_bridge.mcp.server.mcp.list_tools",
             new=AsyncMock(return_value=fake_tools),
         ), patch(
             "forge_bridge.console.handlers.filter_tools_by_reachable_backends",
             side_effect=fake_filter_two,
         ):
        r = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "hi"}]},
        )

    assert r.status_code == 200, r.text
    # Assert the success log line contains both fields
    log_messages = [r.message for r in caplog.records]
    success_logs = [
        m for m in log_messages
        if "stop_reason=chain_complete" in m
        and "chat_regime=compiled_non_mutating" in m
    ]
    assert len(success_logs) >= 1, (
        f"Expected at least one 'chat ok' log line, got: {log_messages}"
    )
    assert "tools_offered_count=2" in success_logs[0], (
        f"Expected tools_offered_count=2 in log line, got: {success_logs[0]}"
    )


def test_pr15_malformed_tool_text_validation_retired(chat_client):
    """A.1 compiles text to graph-intent; PR15 terminal-text validation no longer runs."""
    client, mock_router = chat_client
    mock_router.compile_intent = AsyncMock(
        return_value=['<|im_start|>{"name": "forge_test_probe", "arguments": {}}']
    )
    r = client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 200, r.text


# ── PR20: deterministic forced execution when filter narrows to 1 ──────────


def _pr20_make_tool(name: str):
    """Tool with no required params — forced execution sends `{}`."""
    from mcp.types import Tool, ToolAnnotations
    return Tool(
        name=name,
        description=f"{name} description",
        annotations=ToolAnnotations(readOnlyHint=True),
        inputSchema={"type": "object", "properties": {}, "required": []},
    )


def _pr20_make_wrapped_tool(name: str):
    """Tool with required top-level params wrapper."""
    from mcp.types import Tool, ToolAnnotations
    return Tool(
        name=name,
        description=f"{name} description",
        annotations=ToolAnnotations(readOnlyHint=True),
        inputSchema={
            "$defs": {
                "WrappedInput": {
                    "type": "object",
                    "properties": {"sequence_name": {"type": "string"}},
                    "required": ["sequence_name"],
                },
            },
            "type": "object",
            "properties": {"params": {"$ref": "#/$defs/WrappedInput"}},
            "required": ["params"],
        },
    )


def _pr20_build_app(tools_list, fake_call_tool=None):
    """Spin up a chat app with a custom tool registry. Returns
    (client, mock_router, call_mock). Each test wires its own tools
    list so PR20's narrow-to-1 condition can be exercised precisely."""
    from mcp.types import TextContent

    mock_router = MagicMock()
    mock_router.compile_intent = AsyncMock(return_value=["commit"])
    mock_router.complete_with_tools = AsyncMock()
    mock_router.system_prompt = "base"

    ms = ManifestService()
    mock_log = MagicMock()
    mock_log.snapshot.return_value = ([], 0)
    api = ConsoleReadAPI(
        execution_log=mock_log,
        manifest_service=ms,
        llm_router=mock_router,
    )
    app = build_console_app(api)

    if fake_call_tool is None:
        async def fake_call_tool(name, arguments):
            # PR24 — when a forced tool is on the project_id-injection
            # allow-list, the handler probes `forge_list_projects` first.
            # Default fixture: zero projects → no injection fires, so the
            # downstream tool gets called with `{}` exactly as before.
            if name == "forge_list_projects":
                return [TextContent(
                    type="text",
                    text=json.dumps({"count": 0, "projects": []}),
                )]
            return [TextContent(type="text", text=f"{name}-result:{arguments!r}")]

    list_patch = patch(
        "forge_bridge.mcp.server.mcp.list_tools",
        new=AsyncMock(return_value=tools_list),
    )
    backend_patch = patch(
        "forge_bridge.console.handlers.filter_tools_by_reachable_backends",
        side_effect=_passthrough_filter,
    )
    call_patch = patch(
        "forge_bridge.mcp.server.mcp.call_tool",
        new=AsyncMock(side_effect=fake_call_tool),
    )
    return list_patch, backend_patch, call_patch, app, mock_router


# Registry where forge_list_versions is the ONLY tool whose normalized
# tokens overlap with the test message ``"forge ... versions"`` (where
# `...` is `fetch`/`get`/`list`/etc., all collapsing to `list`).
# Companion tools have disjoint vocabulary — no shared `forge`, `list`,
# or `version` tokens — so the message-filter narrows to a single
# survivor and PR20's narrow-to-1 condition fires.
_PR20_VERSIONS_TOOLS = [
    "forge_list_versions",   # the target — {forge, list, version}
    "flame_alpha",           # disjoint
    "flame_beta",            # disjoint
    "synth_gamma",           # disjoint
    "flame_delta_unrelated", # disjoint (no overlap with msg tokens)
]

# Registry where multiple tools share normalized tokens with the message —
# used to verify PR20 does NOT short-circuit on filtered>1.
_PR20_MULTI_MATCH_TOOLS = [
    "forge_list_versions",
    "forge_list_projects",
    "forge_list_shots",
    "flame_list_libraries",
    "flame_ping",
]


def test_pr20_fetch_versions_forces_forge_list_versions():
    """AC #1: ``"forge fetch versions"`` narrows the registry to exactly
    forge_list_versions; PR20 must bypass the LLM and invoke the tool
    directly with empty args."""
    tools = [_pr20_make_tool(n) for n in _PR20_VERSIONS_TOOLS]
    list_p, back_p, call_p, app, mock_router = _pr20_build_app(tools)
    with list_p, back_p, call_p as call_mock:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": "forge fetch versions"},
            ]},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tool_forced"] is True
    assert body["stop_reason"] == "tool_forced"
    assert body["tools_filtered"] == 1
    assert body["tools_available"] > 1
    # Hard contract — LLM was NEVER called on the forced path.
    mock_router.compile_intent.assert_not_called()
    # PR24 — `forge_list_versions` is on the project_id-injection allow-list,
    # so the handler probes `forge_list_projects` first. Default fixture
    # returns zero projects → no injection → tool still called with `{}`.
    call_mock.assert_any_call("forge_list_projects", {})
    call_mock.assert_any_call("forge_list_versions", {})
    assert call_mock.call_count == 2
    # Reply tail carries assistant tool_call + tool result message.
    msgs = body["messages"]
    assert msgs[-2]["role"] == "assistant"
    assert msgs[-2]["tool_calls"][0]["function"]["name"] == "forge_list_versions"
    assert msgs[-1]["role"] == "tool"
    assert msgs[-1]["name"] == "forge_list_versions"
    assert "forge_list_versions-result" in msgs[-1]["content"]


def test_pr20_get_versions_forces_forge_list_versions():
    """AC #2: ``"forge get versions"`` — same forced execution via
    PR19.1 `get`→`list` and `versions`→`version` normalization."""
    tools = [_pr20_make_tool(n) for n in _PR20_VERSIONS_TOOLS]
    list_p, back_p, call_p, app, mock_router = _pr20_build_app(tools)
    with list_p, back_p, call_p as call_mock:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": "forge get versions"},
            ]},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tool_forced"] is True
    assert body["stop_reason"] == "tool_forced"
    mock_router.compile_intent.assert_not_called()
    # PR24 — probe call to forge_list_projects + actual tool call.
    call_mock.assert_any_call("forge_list_projects", {})
    call_mock.assert_any_call("forge_list_versions", {})
    assert call_mock.call_count == 2


def test_pr20_list_version_singular_forces_forge_list_versions():
    """AC #3: singular ``"forge list version"`` — proves singular↔plural
    symmetry survives all the way through to forced execution."""
    tools = [_pr20_make_tool(n) for n in _PR20_VERSIONS_TOOLS]
    list_p, back_p, call_p, app, mock_router = _pr20_build_app(tools)
    with list_p, back_p, call_p as call_mock:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": "forge list version"},
            ]},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tool_forced"] is True
    mock_router.compile_intent.assert_not_called()
    # PR24 — probe call to forge_list_projects + actual tool call.
    call_mock.assert_any_call("forge_list_projects", {})
    call_mock.assert_any_call("forge_list_versions", {})
    assert call_mock.call_count == 2


def test_pr20_multi_tool_match_does_not_force():
    """AC #4: when the message matches multiple tools AND PR21 cannot
    deterministically narrow them, the LLM still decides — PR20 must
    NOT short-circuit on filtered>1.

    Note: post-PR21, ``"list projects"`` would actually narrow (Rule 1
    picks forge_list_projects on overlap=2 vs. 1 for siblings). So this
    test uses bare ``"list"`` which ties every list-bearing tool at
    overlap=1 with no priority-pair tokens to break the tie."""
    tools = [_pr20_make_tool(n) for n in _PR20_MULTI_MATCH_TOOLS]
    list_p, back_p, call_p, app, mock_router = _pr20_build_app(tools)
    with list_p, back_p, call_p as call_mock:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": "list"},
            ]},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("tool_forced") in (None, False)
    assert body["stop_reason"] == "preview_emitted"
    mock_router.compile_intent.assert_awaited_once()
    # The handler did NOT call the tool directly on the LLM path.
    call_mock.assert_not_called()


def test_pr20_validation_error_returns_structured_tool_message():
    """When the forced tool call raises (validation / runtime), the chat
    reply still returns 200 with a `tool` message carrying a structured
    error payload — NO LLM fallback to text."""
    from mcp.server.fastmcp.exceptions import ToolError

    tools = [_pr20_make_tool(n) for n in _PR20_VERSIONS_TOOLS]

    async def boom(name, arguments):
        raise ToolError("missing required argument 'project'")

    list_p, back_p, call_p, app, mock_router = _pr20_build_app(
        tools, fake_call_tool=boom,
    )
    with list_p, back_p, call_p:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": "forge fetch versions"},
            ]},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tool_forced"] is True
    assert body["stop_reason"] == "tool_forced"
    mock_router.compile_intent.assert_not_called()
    tool_msg = body["messages"][-1]
    assert tool_msg["role"] == "tool"
    assert tool_msg["name"] == "forge_list_versions"
    payload = json.loads(tool_msg["content"])
    assert payload["error"]["type"] == "ToolError"
    assert "missing required argument" in payload["error"]["message"]


def test_pr20_forced_path_does_not_call_when_sequence_unresolved():
    """Unresolved required sequence params stop before FastMCP validation."""
    from mcp.types import TextContent

    tools = [
        _pr20_make_wrapped_tool("flame_get_sequence_segments"),
        _pr20_make_tool("forge_unrelated"),
    ]

    async def fake_call_tool(name, arguments):
        return [TextContent(type="text", text=json.dumps({"arguments": arguments}))]

    list_p, back_p, call_p, app, mock_router = _pr20_build_app(
        tools, fake_call_tool=fake_call_tool,
    )
    with list_p, back_p, call_p as call_mock:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": "get sequence segments"},
            ]},
        )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tool_forced"] is False
    assert body["stop_reason"] == "clarification_needed"
    clarification = body["clarification_needed"]
    assert clarification["kind"] == "referent"
    assert clarification["resolve_hint"]["key"] == "sequence_name"
    assert clarification["prompt"] == "Which sequence should I use?"
    assert body["error"] == (
        "Could not resolve sequence name from your query. "
        "Please specify the exact sequence name."
    )
    assert body["unresolved"] == {
        "key": "sequence_name",
        "tool": "flame_get_sequence_segments",
        "candidates": [],
    }
    mock_router.compile_intent.assert_not_called()
    call_mock.assert_awaited_once_with("flame_context", {})


def test_pr20_forced_path_uses_query_resolved_sequence_name():
    """Forced execution receives deterministic query-time entity resolution."""
    from mcp.types import TextContent

    tools = [
        _pr20_make_wrapped_tool("flame_get_sequence_segments"),
        _pr20_make_tool("forge_unrelated"),
    ]

    async def fake_call_tool(name, arguments):
        return [TextContent(type="text", text=json.dumps({"arguments": arguments}))]

    list_p, back_p, call_p, app, mock_router = _pr20_build_app(
        tools, fake_call_tool=fake_call_tool,
    )
    with list_p, back_p, call_p as call_mock:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": "get sequence segments on 30sec 21"},
            ]},
        )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tool_forced"] is True
    mock_router.compile_intent.assert_not_called()
    call_mock.assert_awaited_once_with(
        "flame_get_sequence_segments",
        {"params": {"sequence_name": "30sec_21"}},
    )
    assistant = body["messages"][-2]
    args_str = assistant["tool_calls"][0]["function"]["arguments"]
    assert json.loads(args_str) == {"params": {"sequence_name": "30sec_21"}}


def test_pr20_trace_tool_forced_absent_when_not_forced():
    """`tool_forced` MUST be absent (or falsy) on the multi-tool LLM path —
    only present on forced executions. Use a bare ``"list"`` message so
    PR21 ties on every list-tool at overlap=1 and cannot narrow."""
    tools = [_pr20_make_tool(n) for n in _PR20_MULTI_MATCH_TOOLS]
    list_p, back_p, call_p, app, _ = _pr20_build_app(tools)
    with list_p, back_p, call_p:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": "list"},
            ]},
        )
    assert r.status_code == 200
    body = r.json()
    assert "tool_forced" not in body or body["tool_forced"] in (False, None)


def test_pr20_trace_tool_forced_true_on_forced_path():
    """`tool_forced=True` and `stop_reason="tool_forced"` on the forced
    path — both fields make the path machine-distinguishable from the
    regular `end_turn` reply."""
    tools = [_pr20_make_tool(n) for n in _PR20_VERSIONS_TOOLS]
    list_p, back_p, call_p, app, _ = _pr20_build_app(tools)
    with list_p, back_p, call_p:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": "forge fetch versions"},
            ]},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["tool_forced"] is True
    assert body["stop_reason"] == "tool_forced"


def test_pr20_does_not_force_when_available_equals_filtered_equals_one(chat_client):
    """Safety guard: when the system itself has only ONE tool registered
    (test fixtures, bare-backend deployments), the filter cannot have
    actively narrowed — a single survivor is either coincidence or the
    capability-loss fallback. PR20 must NOT force in that case, otherwise
    every fixture-based test would call its sole probe tool."""
    client, mock_router = chat_client
    r = client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "user", "content": "fetch versions"}]},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["stop_reason"] == "chain_complete"
    assert body.get("tool_forced") in (None, False)
    mock_router.compile_intent.assert_awaited_once()


def test_phase_24_11_llm_path_receives_resolved_entity_context(chat_client):
    """The LLM path sees deterministic resolved-entity context in-band."""
    client, mock_router = chat_client
    r = client.post(
        "/api/v1/chat",
        json={"messages": [
            {
                "role": "user",
                "content": "Give me the versions on the sequence 30sec 21",
            },
        ]},
    )

    assert r.status_code == 200, r.text
    mock_router.compile_intent.assert_awaited_once()
    forwarded = mock_router.compile_intent.call_args.args[0]
    assert forwarded.startswith("[Resolved entities from query]\n")
    assert 'sequence_name: "30sec_21"  (normalized from "30sec 21")' in (
        forwarded
    )
    assert "User query: Give me the versions" in forwarded


def test_pr20_envelope_keys_on_forced_path():
    """Forced-path envelope carries the same PR14/PR15 telemetry keys as
    the LLM path, plus the new `tool_forced` flag — no key churn."""
    tools = [_pr20_make_tool(n) for n in _PR20_VERSIONS_TOOLS]
    list_p, back_p, call_p, app, _ = _pr20_build_app(tools)
    with list_p, back_p, call_p:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": "forge fetch versions"},
            ]},
        )
    assert r.status_code == 200
    body = r.json()
    for key in ("messages", "stop_reason", "request_id",
                "tools_available", "tools_filtered", "tool_enforced",
                "tool_forced"):
        assert key in body, f"missing {key} in forced-path envelope"


def test_pr20_no_regression_pr14_filter_still_in_place():
    """PR14 message-based filtering remains intact: the multi-tool LLM
    path still sees a narrowed tool list, not the full registry."""
    tools = [_pr20_make_tool(n) for n in _PR20_MULTI_MATCH_TOOLS]
    list_p, back_p, call_p, app, _ = _pr20_build_app(tools)
    with list_p, back_p, call_p:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": "list projects"},
            ]},
        )
    assert r.status_code == 200
    body = r.json()
    # PR14 narrowed the registry down to the `list`-overlap subset.
    assert body["tools_filtered"] < body["tools_available"]
    assert "tool_enforced" in body


def test_pr20_no_regression_pr15_enforcement_unchanged_on_llm_path():
    """PR15's `tool_enforced` flag still rides the LLM path correctly."""
    tools = [_pr20_make_tool(n) for n in _PR20_MULTI_MATCH_TOOLS]
    list_p, back_p, call_p, app, _ = _pr20_build_app(tools)
    with list_p, back_p, call_p:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": "list projects"},
            ]},
        )
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["tool_enforced"], bool)


def test_pr20_does_not_force_when_message_does_not_match_any_tool():
    """PR14 fallback: when the message overlaps no tool tokens, the
    filter falls back to the FULL multi-tool list. With multiple tools,
    PR20's narrow-to-1 condition is not met — LLM still decides."""
    tools = [_pr20_make_tool(n) for n in _PR20_MULTI_MATCH_TOOLS]
    list_p, back_p, call_p, app, mock_router = _pr20_build_app(tools)
    with list_p, back_p, call_p as call_mock:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": "tell me a joke about elephants"},
            ]},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["stop_reason"] == "preview_emitted"
    assert body.get("tool_forced") in (None, False)
    mock_router.compile_intent.assert_awaited_once()
    call_mock.assert_not_called()


# ── PR21: deterministic disambiguation wired into chat handler ─────────────


# Tools that tie under Rule 1 for "list project versions" and let Rule 2
# (version > project) break the tie. Both tools normalize to 2 overlap
# tokens with the message; neither PR18 token-complete fires because
# `forge` isn't in the message.
_PR21_PROJECT_VERSION_TOOLS = [
    "forge_list_projects",
    "forge_list_versions",
    "flame_alpha",   # disjoint vocab — won't match the message
    "flame_beta",
]


def test_pr21_list_project_versions_forces_forge_list_versions():
    """AC #1: ``"list project versions"`` ties forge_list_projects and
    forge_list_versions on overlap=2. PR21 Rule 2 (version > project)
    breaks the tie → PR20 short-circuit force-executes
    forge_list_versions."""
    tools = [_pr20_make_tool(n) for n in _PR21_PROJECT_VERSION_TOOLS]
    list_p, back_p, call_p, app, mock_router = _pr20_build_app(tools)
    with list_p, back_p, call_p as call_mock:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": "list project versions"},
            ]},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tool_forced"] is True
    assert body["stop_reason"] == "tool_forced"
    assert body["tools_filtered"] == 1
    assert body["tools_available"] > 1
    mock_router.compile_intent.assert_not_called()
    # PR24 — probe call to forge_list_projects + actual tool call.
    call_mock.assert_any_call("forge_list_projects", {})
    call_mock.assert_any_call("forge_list_versions", {})
    assert call_mock.call_count == 2


def test_pr21_list_projects_forces_forge_list_projects():
    """AC #2: ``"list projects"`` — Rule 1 alone narrows to
    forge_list_projects (2-token overlap vs. forge_list_versions's
    1-token overlap on `list`). Rule 2 doesn't fire (`version` not in
    msg). PR20 force-executes forge_list_projects."""
    tools = [_pr20_make_tool(n) for n in _PR21_PROJECT_VERSION_TOOLS]
    list_p, back_p, call_p, app, mock_router = _pr20_build_app(tools)
    with list_p, back_p, call_p as call_mock:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": "list projects"},
            ]},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tool_forced"] is True
    assert body["stop_reason"] == "tool_forced"
    mock_router.compile_intent.assert_not_called()
    call_mock.assert_called_once_with("forge_list_projects", {})


def test_pr21_list_versions_forces_forge_list_versions():
    """``"list versions"`` — Rule 1 alone narrows. Counterpart to the
    above test: proves the symmetric path."""
    tools = [_pr20_make_tool(n) for n in _PR21_PROJECT_VERSION_TOOLS]
    list_p, back_p, call_p, app, mock_router = _pr20_build_app(tools)
    with list_p, back_p, call_p as call_mock:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": "list versions"},
            ]},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tool_forced"] is True
    mock_router.compile_intent.assert_not_called()
    # PR24 — probe call to forge_list_projects + actual tool call.
    call_mock.assert_any_call("forge_list_projects", {})
    call_mock.assert_any_call("forge_list_versions", {})
    assert call_mock.call_count == 2


def test_pr21_unbreakable_tie_falls_back_to_llm():
    """When PR21 cannot collapse to a single survivor, the LLM still
    decides — the chat handler hands the surviving set unchanged."""
    # forge_list_projects vs. forge_list_shots. Message "list" overlaps
    # both on 1 token; no priority pair applies. Both survive → LLM.
    tools = [
        _pr20_make_tool("forge_list_projects"),
        _pr20_make_tool("forge_list_shots"),
        _pr20_make_tool("flame_alpha"),
    ]
    list_p, back_p, call_p, app, mock_router = _pr20_build_app(tools)
    with list_p, back_p, call_p as call_mock:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": "list"},
            ]},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("tool_forced") in (None, False)
    assert body["stop_reason"] == "preview_emitted"
    mock_router.compile_intent.assert_awaited_once()
    call_mock.assert_not_called()


def test_pr21_no_regression_pr20_single_match_still_forces():
    """PR20's original path (PR14 already returns 1 tool) is unaffected
    by PR21 — narrowing's `len(tools) <= 1` short-circuit means PR21
    is a no-op when there's nothing to narrow."""
    tools = [_pr20_make_tool(n) for n in _PR20_VERSIONS_TOOLS]
    list_p, back_p, call_p, app, mock_router = _pr20_build_app(tools)
    with list_p, back_p, call_p as call_mock:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": "forge fetch versions"},
            ]},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tool_forced"] is True
    assert body["stop_reason"] == "tool_forced"
    mock_router.compile_intent.assert_not_called()
    # PR24 — probe call to forge_list_projects + actual tool call.
    call_mock.assert_any_call("forge_list_projects", {})
    call_mock.assert_any_call("forge_list_versions", {})
    assert call_mock.call_count == 2


# ── PR24: deterministic project_id injection for single-project context ────


def _pr24_make_call_tool(*, project_count: int, project_id: str = "proj-uuid-1"):
    """Build a fake `mcp.call_tool` that simulates a deployment with N
    projects AND the PR22 graceful contract on `forge_list_versions`.

    - `forge_list_projects` returns `{count, projects}` matching N.
    - `forge_list_versions` with no `project_id` returns the
      MISSING_PROJECT_ID payload (PR22 contract); with one, returns a
      success payload tagged with the injected id so the test can assert
      what the tool actually saw.
    """
    from mcp.types import TextContent

    if project_count == 0:
        projects: list[dict] = []
    elif project_count == 1:
        projects = [{"id": project_id, "name": "Solo", "code": "SOL"}]
    else:
        projects = [
            {"id": f"proj-{i}", "name": f"P{i}", "code": f"P{i}"}
            for i in range(project_count)
        ]

    async def fake(name, arguments):
        if name == "forge_list_projects":
            return [TextContent(
                type="text",
                text=json.dumps({"count": len(projects), "projects": projects}),
            )]
        if name == "forge_list_versions":
            if "project_id" not in arguments:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "error": "project_id is required.",
                        "code": "MISSING_PROJECT_ID",
                    }),
                )]
            return [TextContent(
                type="text",
                text=json.dumps({
                    "project_id": arguments["project_id"],
                    "count": 0,
                    "versions": [],
                }),
            )]
        # Other tools — repr passthrough (matches default fixture style).
        return [TextContent(
            type="text", text=f"{name}-result:{arguments!r}",
        )]

    return fake


def test_pr24_single_project_injects_project_id():
    """AC #1: with exactly one project in the system, the handler probes
    `forge_list_projects`, sees count==1, and injects `project_id` into
    the forced tool call. Tool sees the id; success payload returns."""
    tools = [_pr20_make_tool(n) for n in _PR20_VERSIONS_TOOLS]
    fake = _pr24_make_call_tool(project_count=1, project_id="solo-uuid-001")
    list_p, back_p, call_p, app, mock_router = _pr20_build_app(
        tools, fake_call_tool=fake,
    )
    with list_p, back_p, call_p as call_mock:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": "forge fetch versions"},
            ]},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    # PR24 invariants: forced path still owns the call, LLM untouched.
    assert body["tool_forced"] is True
    assert body["stop_reason"] == "tool_forced"
    assert body["tools_filtered"] == 1
    mock_router.compile_intent.assert_not_called()
    # The probe ran, AND the forced tool was called with the injected id.
    call_mock.assert_any_call("forge_list_projects", {})
    call_mock.assert_any_call(
        "forge_list_versions", {"project_id": "solo-uuid-001"},
    )
    assert call_mock.call_count == 2
    # Tool result reflects the injected id (success payload, no error).
    tool_msg = body["messages"][-1]
    assert tool_msg["role"] == "tool"
    assert tool_msg["name"] == "forge_list_versions"
    payload = json.loads(tool_msg["content"])
    assert payload["project_id"] == "solo-uuid-001"
    assert "error" not in payload
    # Assistant tool_calls argument string also reflects the injection —
    # consumers parsing the trace see the actual params, not a lie.
    assistant = body["messages"][-2]
    assert assistant["role"] == "assistant"
    args_str = assistant["tool_calls"][0]["function"]["arguments"]
    assert json.loads(args_str) == {"project_id": "solo-uuid-001"}


def test_pr24_zero_projects_does_not_inject_and_surfaces_missing_project_id():
    """AC #2: zero projects → no injection. The forced tool gets called
    with `{}` and the PR22 graceful contract surfaces MISSING_PROJECT_ID
    in the tool result message."""
    tools = [_pr20_make_tool(n) for n in _PR20_VERSIONS_TOOLS]
    fake = _pr24_make_call_tool(project_count=0)
    list_p, back_p, call_p, app, mock_router = _pr20_build_app(
        tools, fake_call_tool=fake,
    )
    with list_p, back_p, call_p as call_mock:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": "forge fetch versions"},
            ]},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tool_forced"] is True
    assert body["stop_reason"] == "tool_forced"
    assert body["tools_filtered"] == 1
    mock_router.compile_intent.assert_not_called()
    # Forced tool called with EMPTY args — no injection took place.
    call_mock.assert_any_call("forge_list_projects", {})
    call_mock.assert_any_call("forge_list_versions", {})
    assert call_mock.call_count == 2
    # PR22 contract error surfaces in the tool message, not a 5xx.
    tool_msg = body["messages"][-1]
    payload = json.loads(tool_msg["content"])
    assert payload.get("code") == "MISSING_PROJECT_ID"


def test_pr24_multiple_projects_returns_pr27_disambiguation_envelope():
    """Multi-project case — PR27 supersedes the original PR24 behavior.

    PR24's original contract here was 200 + tool message with
    MISSING_PROJECT_ID (the same shape as zero projects). PR27 changed
    that to a structured MULTIPLE_PROJECTS envelope. CR.2 keeps the
    deterministic candidate source but normalizes it into a continuation
    prompt instead of a terminal error.

    What's preserved from PR24:
      - The forced tool itself is NEVER called (no `forge_list_versions`).
      - The LLM is NEVER invoked.
      - `forge_list_projects` IS called once (the resolver probe).
    What's new under CR.2:
      - HTTP 200 continuation instead of terminal error.
      - ``clarification_needed`` envelope with deterministic candidates.
      - ``tool_forced=False`` and no downstream forced-tool execution.
    """
    tools = [_pr20_make_tool(n) for n in _PR20_VERSIONS_TOOLS]
    fake = _pr24_make_call_tool(project_count=3)
    list_p, back_p, call_p, app, mock_router = _pr20_build_app(
        tools, fake_call_tool=fake,
    )
    with list_p, back_p, call_p as call_mock:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": "forge fetch versions"},
            ]},
        )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["stop_reason"] == "clarification_needed"
    assert body["tool_forced"] is False
    details = body["clarification_needed"]
    assert details["kind"] == "referent"
    assert details["resolve_hint"]["key"] == "project_id"
    assert details["prompt"] == "Found 3 projects. Which one?"
    candidates = details["candidates"]
    assert len(candidates) == 3
    for c in candidates:
        assert "id" in c and "name" in c
    # Request-id header still present on the continuation path (D-21).
    assert "X-Request-ID" in r.headers

    # Hard contract: NO LLM, NO downstream tool call.
    mock_router.compile_intent.assert_not_called()
    call_mock.assert_called_once_with("forge_list_projects", {})


def test_pr24_does_not_fire_for_tools_outside_allow_list():
    """A forced tool that is NOT on the PR24 allow-list (e.g. a flame
    tool) must NOT trigger the projects probe. PR24 is a tight
    allow-list, not a schema-driven heuristic."""
    # Single non-allow-listed tool — narrows to 1 → forced execution.
    tools = [
        _pr20_make_tool("flame_ping"),    # target — not on allow-list
        _pr20_make_tool("forge_alpha"),   # disjoint
        _pr20_make_tool("synth_beta"),    # disjoint
    ]
    fake = _pr24_make_call_tool(project_count=1)
    list_p, back_p, call_p, app, mock_router = _pr20_build_app(
        tools, fake_call_tool=fake,
    )
    with list_p, back_p, call_p as call_mock:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": "flame ping"},
            ]},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tool_forced"] is True
    mock_router.compile_intent.assert_not_called()
    # Crucial: NO probe call to forge_list_projects, only the target.
    call_mock.assert_called_once_with("flame_ping", {})


# ── PR20/PR21 state-consistency invariant — runtime guard ──────────────────


def _assert_tool_state_invariant(body):
    """Joint invariant the runtime trace consumers rely on:
        tool_enforced ⇔ tools_filtered == 1
    Two combinations are forbidden EVERYWHERE in the chat response:
        (tools_filtered > 1) ∧ (tool_enforced == True)
        (tools_filtered == 1) ∧ (tool_enforced == False)
    """
    filtered = body.get("tools_filtered")
    enforced = body.get("tool_enforced")
    assert filtered is not None and isinstance(enforced, bool), body
    assert not (filtered > 1 and enforced), (
        f"forbidden state: tools_filtered={filtered} tool_enforced=True "
        f"in body={body}"
    )
    assert not (filtered == 1 and not enforced), (
        f"forbidden state: tools_filtered=1 tool_enforced=False "
        f"in body={body}"
    )


def test_state_invariant_fetch_versions_force_path():
    """Forced single-tool path: filtered==1 AND enforced=True together."""
    tools = [_pr20_make_tool(n) for n in _PR20_VERSIONS_TOOLS]
    list_p, back_p, call_p, app, _ = _pr20_build_app(tools)
    with list_p, back_p, call_p:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": "forge fetch versions"},
            ]},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["tools_filtered"] == 1
    assert body["tool_enforced"] is True
    assert body["tool_forced"] is True
    _assert_tool_state_invariant(body)


def test_state_invariant_pr21_narrowing_force_path():
    """PR21 narrowing-then-force path: post-narrow filtered==1 AND
    enforced=True. Pre-fix this would have shown filtered>1 ∧ enforced=True
    because the count wasn't rebound after a partial PR21 reduction."""
    tools = [_pr20_make_tool(n) for n in _PR21_PROJECT_VERSION_TOOLS]
    list_p, back_p, call_p, app, _ = _pr20_build_app(tools)
    with list_p, back_p, call_p:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": "list project versions"},
            ]},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["tools_filtered"] == 1
    assert body["tool_enforced"] is True
    assert body["tool_forced"] is True
    _assert_tool_state_invariant(body)


def test_state_invariant_tools_filtered_equals_actual_tool_count():
    """Single source of truth: `tools_filtered` in the body must equal
    the number of tools the chat handler actually forwarded to the LLM
    (or, on the forced path, the size of the input that produced the
    single forced call)."""
    tools = [_pr20_make_tool(n) for n in _PR20_MULTI_MATCH_TOOLS]
    list_p, back_p, call_p, app, mock_router = _pr20_build_app(tools)
    with list_p, back_p, call_p:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": "list"},
            ]},
        )
    assert r.status_code == 200
    body = r.json()
    # The compile path was called — verify the count matches what was forwarded.
    forwarded = mock_router.compile_intent.call_args.args[1]
    assert body["tools_filtered"] == len(forwarded)
    _assert_tool_state_invariant(body)


# ── Defensive: empty-tools guard + safe error envelope ────────────────────


def test_chat_returns_503_when_filter_pipeline_yields_empty_tool_set():
    """Defensive guard: if a future filter edit ever returns an empty
    `tools` list at the LLM-dispatch boundary, the handler must short-
    circuit with a 503 service_unavailable envelope (matching the
    upstream reachable-backends empty-list shape) — NOT call the LLM
    with no tools (which would loop or hang) and NOT raise."""
    from mcp.types import Tool

    # Patch filter_tools_by_message itself to simulate the bug condition:
    # a future filter that drops every tool. The reachable-backends filter
    # is patched separately to keep an upstream non-empty list so we
    # specifically exercise the post-PR21 guard.
    fake_tools = [
        Tool(name="forge_alpha", description="x", inputSchema={"type": "object"}),
        Tool(name="forge_beta",  description="x", inputSchema={"type": "object"}),
    ]

    mock_router = MagicMock()
    mock_router.compile_intent = AsyncMock(return_value=["commit"])
    mock_router.complete_with_tools = AsyncMock()
    mock_router.system_prompt = "base"
    ms = ManifestService()
    mock_log = MagicMock()
    mock_log.snapshot.return_value = ([], 0)
    api = ConsoleReadAPI(
        execution_log=mock_log,
        manifest_service=ms,
        llm_router=mock_router,
    )
    app = build_console_app(api)

    def _empty_filter(tools, message, **_kw):
        return []  # simulate broken filter — never happens in real code

    with patch(
        "forge_bridge.mcp.server.mcp.list_tools",
        new=AsyncMock(return_value=fake_tools),
    ), patch(
        "forge_bridge.console.handlers.filter_tools_by_reachable_backends",
        side_effect=_passthrough_filter,
    ), patch(
        "forge_bridge.console.handlers.filter_tools_by_message",
        side_effect=_empty_filter,
    ):
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "hi"}]},
        )

    assert r.status_code == 503, r.text
    body = r.json()
    assert body["error"]["code"] == "service_unavailable"
    # LLM must NOT have been called.
    mock_router.compile_intent.assert_not_called()


def test_chat_safe_error_envelope_when_router_raises_arbitrary_exception(chat_client):
    """The catch-all `except Exception as exc:` must convert ANY router
    failure into a structured 500 envelope — never leak the exception
    string into the response body, never let the framework return a
    Starlette default 500 with a traceback."""
    client, mock_router = chat_client
    mock_router.compile_intent.side_effect = RuntimeError(
        "secret detail in exception text — must NOT leak"
    )
    r = client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 500
    body = r.json()
    # Nested shape (D-17) — never the framework default.
    assert body["error"]["code"] == "internal_error"
    assert isinstance(body["error"]["message"], str)
    # Exception text MUST NOT appear in the response.
    assert "secret detail" not in body["error"]["message"]
    # X-Request-ID header is still present (D-21).
    assert "X-Request-ID" in r.headers


def test_chat_safe_error_envelope_when_router_raises_value_error(chat_client):
    """Same contract under a different exception class — proves the
    catch-all is the load-bearing guarantee, not just LLMToolError."""
    client, mock_router = chat_client
    mock_router.compile_intent.side_effect = ValueError("oops")
    r = client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "internal_error"
    assert "oops" not in r.json()["error"]["message"]


# ── Phase 24.5 — Console UI consumer projection of orchestration_terminated ──
#
# Static structural tests against the shipped panel.html template + the static
# forge-chat.js + forge-console.css. Pattern parity with the existing
# test_ui_chat_handler_renders_panel_template (line 289). Tests verify the
# Console UI surface implements the §4 consumer contract and honors the
# §10.1 anti-impersonation guard at the chrome layer ("the consumer may
# project, but does not synthesize").
#
# Browser-runtime behavioral verification (Alpine consuming the envelope and
# rendering it live) is covered by the §8.2 forcing-function rerun bundle in
# the canonical-probe rerun commit (commit 4 of the 4-commit arc) — opt-in
# pytest-playwright extras, not part of the default suite.


def _static_asset_source(filename: str) -> str:
    """Read a forge_bridge/console/static asset for structural assertions."""
    from pathlib import Path
    pkg_root = Path(__file__).resolve().parent.parent.parent / "forge_bridge"
    return (pkg_root / "console" / "static" / filename).read_text(encoding="utf-8")


def test_ui_chat_panel_has_orchestration_termination_section(chat_client):
    """Phase 24.5: panel.html ships the orchestration-termination block.

    Section is at top-level — a SIBLING of the message list, not nested
    inside any .chat-message variant (framing §5 + §6: distinct KIND).
    """
    client, _ = chat_client
    r = client.get("/ui/chat")
    assert r.status_code == 200
    body = r.text
    # Top-level section with distinct class + ARIA region role.
    assert '<section class="orchestration-termination"' in body
    assert 'role="region"' in body
    assert 'aria-label="Orchestration termination"' in body
    # Conditionally shown via Alpine x-show against `termination` state.
    assert 'x-show="termination"' in body
    # Uppercase taxon header per framing §5.
    assert "Orchestration Termination" in body
    assert "orchestration-termination__taxon" in body
    # Sub-tag explicitly distinguishes from model completion.
    assert "policy-decided" in body
    assert "not model completion" in body


def test_ui_chat_panel_orchestration_termination_uses_x_text_not_markdown(chat_client):
    """Framing §10.1 — NO markdown rendering of envelope strings.

    trigger / reason / iterations / accumulated_results.content are all
    operator-authored at the orchestrator; the consumer projects them
    verbatim via x-text. ANY x-html binding (or use of renderContent)
    would route them through renderMarkdown(), which is consumer-side
    synthesis through markdown transformation.
    """
    client, _ = chat_client
    body = client.get("/ui/chat").text
    # All five contract facts bind via x-text on the termination object.
    assert 'x-text="termination && termination.trigger"' in body
    assert 'x-text="termination && termination.reason"' in body
    assert 'x-text="termination && termination.iterations"' in body
    # accumulated_results.content uses <pre> + x-text (verbatim display)
    assert 'x-text="entry.content"' in body
    # Anti-synthesis guard: locate the termination <section> and verify
    # renderContent / x-html appear NOWHERE inside it.
    start = body.find('<section class="orchestration-termination"')
    end = body.find("</section>", start)
    assert start > 0 and end > start
    ot_block = body[start:end]
    assert "renderContent" not in ot_block
    assert "x-html" not in ot_block


def test_ui_chat_panel_orchestration_termination_is_sibling_not_message_variant(chat_client):
    """Framing §6: termination is a sibling of messages, not a styled
    .chat-message-- variant. DOM order: termination block appears AFTER
    the message x-for template, and the block's class namespace MUST NOT
    include any .chat-message-- leak (which would semantically subordinate
    it under the assistant family per operator's commit-3 reinforcement)."""
    client, _ = chat_client
    body = client.get("/ui/chat").text
    xfor_idx = body.find('x-for="msg in renderableMessages()"')
    ot_idx = body.find("orchestration-termination")
    assert xfor_idx > 0 and ot_idx > 0
    assert ot_idx > xfor_idx, "termination section must appear after the message x-for"
    # Termination block uses its own class namespace; no chat-message-- leak.
    start = body.find('<section class="orchestration-termination"')
    end = body.find("</section>", start)
    ot_block = body[start:end]
    assert "chat-message--" not in ot_block
    assert "chat-message-content" not in ot_block


def test_ui_chat_panel_orchestration_termination_done_path_byte_identical(chat_client):
    """Anti-scope §7.4: done-path rendering structurally unchanged at 24.5.

    The orchestration-termination section is x-show'd against termination
    state — when termination is null (done path), the section is hidden.
    No new elements leak into the done rendering path.
    """
    client, _ = chat_client
    body = client.get("/ui/chat").text
    # Existing message-rendering chrome unchanged.
    assert ':class="messageClass(msg)"' in body
    assert "chat-message--user" in body or "messageClass" in body  # via JS
    # Empty-state copy unchanged.
    assert "Ask about pipeline state, tools, or execution history" in body


# ── forge-chat.js orchestration_terminated detection ────────────────────────


def test_forge_chat_js_has_termination_state_field():
    """Phase 24.5: chatPanel() factory carries `termination: null` state."""
    src = _static_asset_source("forge-chat.js")
    assert "termination: null" in src


def test_forge_chat_js_clears_termination_on_new_send():
    """A new send() must clear any prior turn's termination state.

    Otherwise stale termination chrome persists into the next turn —
    operator perceives "this conversation is policy-terminated" when in
    fact a new send is in flight.
    """
    src = _static_asset_source("forge-chat.js")
    # The clear assignment exists; locate it INSIDE the send() body by
    # finding the marker that precedes it ("this.error = "").
    error_clear_idx = src.find('this.error = ""')
    term_clear_idx = src.find("this.termination = null")
    assert error_clear_idx > 0 and term_clear_idx > 0
    # The termination clear must follow the error clear (both at the top
    # of send() per the convention established by D-09).
    assert term_clear_idx > error_clear_idx


def test_forge_chat_js_detects_orchestration_terminated_envelope():
    """Detection key: stop_reason === "orchestration_terminated" AND
    a typeof-checked termination object."""
    src = _static_asset_source("forge-chat.js")
    assert 'body.stop_reason === "orchestration_terminated"' in src
    assert "body.termination" in src
    # Typeof guard prevents detection on malformed envelopes (defensive
    # parsing parity with CLI _is_orchestration_terminated).
    assert 'typeof body.termination === "object"' in src


def test_forge_chat_js_does_not_paraphrase_or_transform_termination():
    """Framing §10.1: assignment is verbatim — `this.termination = body.termination`.

    No JSON.parse, no Object.assign with overrides, no field renames, no
    field synthesis. The envelope IS the consumer state. Any transform
    pattern (.map / JSON.parse on body.termination) is the synthesis red
    flag this test catches.
    """
    src = _static_asset_source("forge-chat.js")
    assert "this.termination = body.termination" in src
    # Specific synthesis anti-patterns: explicit absence assertions.
    assert "JSON.parse(body.termination" not in src
    assert "body.termination.map" not in src
    # No spread-and-mutate (would allow field injection / rename).
    assert "...body.termination" not in src


def test_forge_chat_js_termination_null_when_envelope_lacks_it():
    """Defensive: when the envelope's stop_reason is anything OTHER than
    orchestration_terminated, termination is explicitly set to null (not
    left stale from prior turns)."""
    src = _static_asset_source("forge-chat.js")
    # Look for the else branch clearing termination.
    # Loose pattern: an explicit `this.termination = null` after the
    # detection block (i.e. the second occurrence in the file — first is
    # the top-of-send clear, second is the else branch).
    occurrences = src.count("this.termination = null")
    assert occurrences >= 2, "Need both top-of-send clear AND else-branch clear"


# ── forge-console.css orchestration_terminated chrome ───────────────────────


def test_forge_console_css_has_orchestration_termination_chrome():
    """Phase 24.5: CSS ships distinct visual chrome for termination."""
    src = _static_asset_source("forge-console.css")
    assert ".orchestration-termination{" in src
    assert ".orchestration-termination__taxon" in src
    assert ".orchestration-termination__header" in src
    assert ".orchestration-termination__facts" in src
    assert ".orchestration-termination__results" in src
    assert ".orchestration-termination__entry" in src


def test_forge_console_css_termination_is_not_styled_assistant_variant():
    """Framing §5 + operator's commit-3 reinforcement: termination must
    NOT visually subordinate beneath assistant styling.

    Concretely: no compound selector chains .chat-message--assistant with
    .orchestration-termination (which would layer assistant chrome under
    termination, or vice versa). Independent visual KINDS.
    """
    src = _static_asset_source("forge-console.css")
    # Compound-selector laundering patterns must not exist.
    assert ".chat-message--assistant.orchestration-termination" not in src
    assert ".orchestration-termination.chat-message" not in src
    assert ".chat-message .orchestration-termination" not in src
    # Inside the termination block (locate by its first selector through
    # its next /* === comment marker), no chat-message references.
    start = src.find(".orchestration-termination{")
    end = src.find("/* ===", start)
    if end < 0:
        end = len(src)
    block = src[start:end]
    assert "chat-message" not in block


def test_forge_console_css_termination_uses_distinct_shape_signals():
    """Distinction-by-shape (not just color): box outline + thick left
    band (4px — distinct from .chat-message--*'s 2px) + mono font +
    uppercase taxon header. Four independent visual signals so the
    distinction survives single-channel degradation (colorblind,
    high-contrast mode, low-color-depth displays)."""
    src = _static_asset_source("forge-console.css")
    start = src.find(".orchestration-termination{")
    end = src.find("/* ===", start)
    if end < 0:
        end = len(src)
    block = src[start:end]
    # 1. Box outline (NOT single-side border like .chat-message--user/assistant)
    assert "border:1px solid" in block
    # 2. Thick left band — 4px distinct from .chat-message--*'s 2px
    assert "border-left:4px" in block
    # 3. Monospace font signals "structured truth" not "prose"
    assert "var(--font-mono)" in block
    # 4. Uppercase taxon header for at-a-glance distinction
    assert "text-transform:uppercase" in block
