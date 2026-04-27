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
