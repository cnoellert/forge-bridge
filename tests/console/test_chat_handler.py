"""Unit tests for forge_bridge/console/handlers.py chat_handler (CHAT-01/02 + D-14a).

All tests use a mocked LLMRouter (no real Ollama dep). Rate-limit module is
reset before each test for isolation. Tool registry snapshot is patched to
return a fixed Tool list so the empty-registry guard does NOT short-circuit.

Test roster (15 tests):
  1. test_chat_happy_path_returns_200
  2. test_chat_invalid_json_body_returns_422
  3. test_chat_missing_messages_field_returns_422
  4. test_chat_unsupported_role_returns_422
  5. test_chat_rate_limit_returns_429_with_retry_after
  6. test_chat_loop_budget_exceeded_returns_504
  7. test_chat_outer_timeout_returns_504
  8. test_chat_recursive_loop_error_returns_500
  9. test_chat_tool_error_returns_500
 10. test_chat_envelope_shape_is_nested
 11. test_chat_passes_messages_list_to_router
 12. test_ui_chat_handler_renders_panel_template
 13. test_chat_filters_unreachable_backends (Phase 16.1 D-01)
 14. test_chat_503_when_no_backends_reachable (Phase 16.1 D-01)
 15. test_chat_logs_tools_offered_count_on_success (Phase 16.1 D-01 + D-21)
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
from forge_bridge.llm.router import (
    LLMLoopBudgetExceeded,
    LLMToolError,
    RecursiveToolLoopError,
)


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
    """TestClient with mocked LLMRouter; complete_with_tools returns 'OK'.

    Patches forge_bridge.mcp.server.mcp.list_tools at the import path the
    handler resolves (`from forge_bridge.mcp import server as _mcp_server;
    await _mcp_server.mcp.list_tools()`) so the empty-registry guard does
    NOT short-circuit any test.

    Also patches filter_tools_by_reachable_backends to pass all tools through
    (no TCP probe in test context). Tests that exercise filtering behavior provide
    their own patch that overrides this default.
    """
    mock_router = MagicMock()
    mock_router.complete_with_tools = AsyncMock(return_value="OK from mock LLM")

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
    ):
        yield TestClient(app), mock_router


# ── Happy path ─────────────────────────────────────────────────────────────────

def test_chat_happy_path_returns_200(chat_client):
    client, mock_router = chat_client
    r = client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "user", "content": "what week is it?"}]},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["stop_reason"] == "end_turn"
    assert "request_id" in body
    assert isinstance(body["messages"], list) and len(body["messages"]) == 2
    assert body["messages"][-1] == {"role": "assistant", "content": "OK from mock LLM"}
    assert "X-Request-ID" in r.headers
    # D-05: sensitive must be hardcoded True regardless of the request body.
    call_kwargs = mock_router.complete_with_tools.call_args.kwargs
    assert call_kwargs["sensitive"] is True


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

def test_chat_loop_budget_exceeded_returns_504(chat_client):
    client, mock_router = chat_client
    mock_router.complete_with_tools.side_effect = LLMLoopBudgetExceeded(
        "max_seconds", -1, 120.0,
    )
    r = client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 504
    assert r.json()["error"]["code"] == "request_timeout"


def test_chat_outer_timeout_returns_504(chat_client):
    """asyncio.TimeoutError from the outer wait_for translates to 504 per D-14a."""
    client, mock_router = chat_client
    mock_router.complete_with_tools.side_effect = asyncio.TimeoutError()
    r = client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 504
    assert r.json()["error"]["code"] == "request_timeout"


# ── 500 internal error paths (D-14a) ───────────────────────────────────────────

def test_chat_recursive_loop_error_returns_500(chat_client):
    client, mock_router = chat_client
    mock_router.complete_with_tools.side_effect = RecursiveToolLoopError(
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
    mock_router.complete_with_tools.side_effect = LLMToolError("provider 5xx")
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


def test_chat_passes_messages_list_to_router(chat_client):
    """D-02a: messages list is passed verbatim (no lossy stitching)."""
    client, mock_router = chat_client
    history = [
        {"role": "user", "content": "first turn"},
        {"role": "assistant", "content": "first reply"},
        {"role": "user", "content": "second turn"},
    ]
    r = client.post("/api/v1/chat", json={"messages": history})
    assert r.status_code == 200, r.text
    call_kwargs = mock_router.complete_with_tools.call_args.kwargs
    assert call_kwargs["messages"] == history
    # And NOT the legacy prompt= path.
    assert call_kwargs.get("prompt", "") == ""


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
    unreachable. Asserts complete_with_tools() receives only the filtered list.

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
    call_kwargs = mock_router.complete_with_tools.call_args.kwargs
    forwarded_tools = call_kwargs["tools"]
    assert len(forwarded_tools) == 1
    assert forwarded_tools[0].name == "synth_test"


def test_chat_503_when_no_backends_reachable(chat_client):
    """D-01: when filter_tools_by_reachable_backends returns empty list,
    chat handler returns 503 with service_unavailable envelope.
    complete_with_tools must NOT be called.
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
    mock_router.complete_with_tools.assert_not_called()


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
    success_logs = [m for m in log_messages if "stop_reason=end_turn" in m]
    assert len(success_logs) >= 1, (
        f"Expected at least one 'chat ok' log line, got: {log_messages}"
    )
    assert "tools_offered_count=2" in success_logs[0], (
        f"Expected tools_offered_count=2 in log line, got: {success_logs[0]}"
    )


# ── PR15: deterministic-tool-call enforcement ─────────────────────────────


def test_pr15_chat_handler_passes_enforcement_system_prompt(chat_client):
    """The chat handler MUST override system= with the PR15 enforcement
    prompt — preserving the router's base prompt at the top of the stack."""
    client, mock_router = chat_client
    mock_router.system_prompt = "You are a VFX pipeline assistant."

    r = client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "user", "content": "use forge_test_probe"}]},
    )
    assert r.status_code == 200, r.text
    kwargs = mock_router.complete_with_tools.call_args.kwargs
    sys_msg = kwargs.get("system")
    assert isinstance(sys_msg, str)
    assert sys_msg.startswith("You are a VFX pipeline assistant.")
    assert "tool-using agent" in sys_msg
    assert "YOU MUST CALL IT" in sys_msg


def test_pr15_chat_handler_injects_hard_tool_mode_when_one_tool(chat_client):
    """Single tool surviving the filter triggers HARD-TOOL injection."""
    client, mock_router = chat_client
    mock_router.system_prompt = "base"
    # The mock fixture installs exactly one tool (forge_test_probe), and the
    # passthrough filter keeps all of them. The PR14 message filter will keep
    # it (no tokens overlap → fallback to full list = 1 tool).
    r = client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "user", "content": "anything goes"}]},
    )
    assert r.status_code == 200, r.text
    sys_msg = mock_router.complete_with_tools.call_args.kwargs["system"]
    assert "exactly ONE tool" in sys_msg
    assert "MUST call this tool" in sys_msg


def test_pr15_chat_handler_omits_hard_tool_mode_when_multiple_tools(chat_client):
    """No HARD-TOOL line when more than one tool is offered to the model."""
    from mcp.types import Tool

    client, mock_router = chat_client
    mock_router.system_prompt = "base"

    fake_tools = [
        Tool(name="forge_a", description="x",
             inputSchema={"type": "object", "properties": {}}),
        Tool(name="forge_b", description="x",
             inputSchema={"type": "object", "properties": {}}),
    ]

    async def fake_passthrough(tools):
        return tools

    with patch(
        "forge_bridge.mcp.server.mcp.list_tools",
        new=AsyncMock(return_value=fake_tools),
    ), patch(
        "forge_bridge.console.handlers.filter_tools_by_reachable_backends",
        side_effect=fake_passthrough,
    ):
        r = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "hi"}]},
        )
    assert r.status_code == 200
    sys_msg = mock_router.complete_with_tools.call_args.kwargs["system"]
    assert "tool-using agent" in sys_msg
    assert "MUST call this tool" not in sys_msg


def test_pr15_chat_handler_response_body_carries_tool_enforced(chat_client):
    """Success body must include ``tool_enforced`` for the wrapper trace."""
    client, mock_router = chat_client
    mock_router.system_prompt = "base"
    r = client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # The fixture installs 1 tool → tools_filtered=1 → tool_enforced=True.
    assert body["tool_enforced"] is True


def test_pr15_chat_handler_returns_500_on_malformed_tool_text(chat_client):
    """Hallucinated tool-call text in the assistant response → 500."""
    client, mock_router = chat_client
    mock_router.system_prompt = "base"
    mock_router.complete_with_tools = AsyncMock(
        return_value='<|im_start|>{"name": "forge_test_probe", "arguments": {}}'
    )
    r = client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "internal_error"


def test_pr15_chat_handler_legitimate_response_not_flagged(chat_client):
    """A normal assistant response must still 200 — no false-positive 500s."""
    client, mock_router = chat_client
    mock_router.system_prompt = "base"
    mock_router.complete_with_tools = AsyncMock(
        return_value="There are 4 libraries: Default, WIP, Postings, Delivery."
    )
    r = client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "user", "content": "list libraries"}]},
    )
    assert r.status_code == 200, r.text


def test_pr15_no_regression_pr14_counts_still_present(chat_client):
    """tools_available / tools_filtered (PR14) must still ship alongside
    the new tool_enforced field — no key churn for downstream consumers."""
    client, mock_router = chat_client
    mock_router.system_prompt = "base"
    r = client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 200
    body = r.json()
    for key in ("tools_available", "tools_filtered", "tool_enforced",
                "messages", "stop_reason", "request_id"):
        assert key in body, f"missing {key} in response body"


# ── PR20: deterministic forced execution when filter narrows to 1 ──────────


def _pr20_make_tool(name: str):
    """Tool with no required params — forced execution sends `{}`."""
    from mcp.types import Tool
    return Tool(
        name=name,
        description=f"{name} description",
        inputSchema={"type": "object", "properties": {}, "required": []},
    )


def _pr20_build_app(tools_list, fake_call_tool=None):
    """Spin up a chat app with a custom tool registry. Returns
    (client, mock_router, call_mock). Each test wires its own tools
    list so PR20's narrow-to-1 condition can be exercised precisely."""
    from mcp.types import TextContent

    mock_router = MagicMock()
    mock_router.complete_with_tools = AsyncMock(return_value="UNREACHED LLM")
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
    mock_router.complete_with_tools.assert_not_called()
    # Tool called with empty args, exactly once.
    call_mock.assert_called_once_with("forge_list_versions", {})
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
    mock_router.complete_with_tools.assert_not_called()
    call_mock.assert_called_once_with("forge_list_versions", {})


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
    mock_router.complete_with_tools.assert_not_called()
    call_mock.assert_called_once_with("forge_list_versions", {})


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
    assert body["stop_reason"] == "end_turn"
    mock_router.complete_with_tools.assert_called_once()
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
    mock_router.complete_with_tools.assert_not_called()
    tool_msg = body["messages"][-1]
    assert tool_msg["role"] == "tool"
    assert tool_msg["name"] == "forge_list_versions"
    payload = json.loads(tool_msg["content"])
    assert payload["error"]["type"] == "ToolError"
    assert "missing required argument" in payload["error"]["message"]


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
    assert body["stop_reason"] == "end_turn"
    assert body.get("tool_forced") in (None, False)
    mock_router.complete_with_tools.assert_called_once()


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
    assert body["stop_reason"] == "end_turn"
    assert body.get("tool_forced") in (None, False)
    mock_router.complete_with_tools.assert_called_once()
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
    mock_router.complete_with_tools.assert_not_called()
    call_mock.assert_called_once_with("forge_list_versions", {})


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
    mock_router.complete_with_tools.assert_not_called()
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
    mock_router.complete_with_tools.assert_not_called()
    call_mock.assert_called_once_with("forge_list_versions", {})


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
    assert body["stop_reason"] == "end_turn"
    mock_router.complete_with_tools.assert_called_once()
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
    mock_router.complete_with_tools.assert_not_called()
    call_mock.assert_called_once_with("forge_list_versions", {})


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


def test_state_invariant_multi_tool_llm_path():
    """LLM path with multiple survivors: filtered>1 AND enforced=False
    together. Pre-fix the ≤3 PR15 threshold made enforced=True for
    filtered=2..3, breaking the invariant."""
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
    assert body["tools_filtered"] > 1
    assert body["tool_enforced"] is False
    _assert_tool_state_invariant(body)
    mock_router.complete_with_tools.assert_called_once()


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
    # The LLM was called — verify the count matches what was forwarded.
    forwarded = mock_router.complete_with_tools.call_args.kwargs["tools"]
    assert body["tools_filtered"] == len(forwarded)
    _assert_tool_state_invariant(body)
