"""Unit tests for forge_bridge/console/handlers.py chat_handler (CHAT-01/02 + D-14a).

All tests use a mocked LLMRouter (no real Ollama dep). Rate-limit module is
reset before each test for isolation. Tool registry snapshot is patched to
return a fixed Tool list so the empty-registry guard does NOT short-circuit.

Test roster (11 tests):
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
"""
from __future__ import annotations

import asyncio

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


@pytest.fixture
def chat_client():
    """TestClient with mocked LLMRouter; complete_with_tools returns 'OK'.

    Patches forge_bridge.mcp.server.mcp.list_tools at the import path the
    handler resolves (`from forge_bridge.mcp import server as _mcp_server;
    await _mcp_server.mcp.list_tools()`) so the empty-registry guard does
    NOT short-circuit any test.
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
