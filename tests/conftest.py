"""
Shared pytest fixtures for forge-bridge test suite.

Fixtures:
    monkeypatch_bridge  — patches forge_bridge.bridge.execute with a mock BridgeResponse
    mock_openai         — patches openai at module level to prevent import errors
    mock_anthropic      — patches anthropic at module level to prevent import errors
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from forge_bridge.bridge import BridgeResponse


@pytest.fixture
def monkeypatch_bridge(monkeypatch):
    """Patch forge_bridge.bridge.execute to return a predictable BridgeResponse.

    Usage:
        def test_something(monkeypatch_bridge):
            # bridge.execute is now a coroutine returning the mock response
            ...

    The fixture yields the mock so tests can reconfigure it:
        monkeypatch_bridge.result = '{"key": "value"}'
    """
    mock_response = BridgeResponse(
        stdout='{"result": "ok"}',
        stderr="",
        result="ok",
        error=None,
        traceback=None,
    )

    mock_execute = AsyncMock(return_value=mock_response)

    with patch("forge_bridge.bridge.execute", mock_execute):
        yield mock_execute


@pytest.fixture
def mock_openai():
    """Patch openai so tests run without the package installed.

    Provides a MagicMock at the openai module level. Individual tests
    can configure mock_openai.return_value as needed.
    """
    mock = MagicMock()
    with patch.dict("sys.modules", {"openai": mock, "openai.OpenAI": mock.OpenAI}):
        yield mock


@pytest.fixture
def mock_anthropic():
    """Patch anthropic so tests run without the package installed.

    Provides a MagicMock at the anthropic module level. Individual tests
    can configure mock_anthropic.return_value as needed.
    """
    mock = MagicMock()
    with patch.dict("sys.modules", {"anthropic": mock}):
        yield mock


# ============================================================
# Phase 11 fixtures — shared across all tests/test_cli_*.py files
# ============================================================

import socket as _phase11_socket  # noqa: E402 — alias to avoid collision with existing imports


@pytest.fixture
def free_port() -> int:
    """Return an available local port on 127.0.0.1.

    Source: extracted from tests/test_console_http_transport.py:_find_free_port.
    Used by every Phase 11 CLI integration test that boots a fixture server.
    """
    with _phase11_socket.socket(_phase11_socket.AF_INET, _phase11_socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
