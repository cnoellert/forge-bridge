"""Functional test for /ui/chat nav stub (D-28/29)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.testclient import TestClient

from forge_bridge.console.app import build_console_app


@pytest.fixture
def fake_read_api():
    api = MagicMock()
    api.get_tools = AsyncMock(return_value=[])
    api.get_tool = AsyncMock(return_value=None)
    api.get_executions = AsyncMock(return_value=([], 0))
    api.get_manifest = AsyncMock(return_value={"tools": [], "count": 0, "schema_version": "1"})
    api.get_health = AsyncMock(return_value={
        "status": "ok",
        "services": {
            "mcp": {"status": "ok", "detail": ""},
            "flame_bridge": {"status": "ok", "detail": ""},
            "ws_server": {"status": "ok", "detail": ""},
            "llm_backends": [],
            "watcher": {"status": "ok", "detail": ""},
            "storage_callback": {"status": "absent", "detail": ""},
            "console_port": {"status": "ok", "port": 9996, "detail": ""},
        },
        "instance_identity": {
            "execution_log": {"id_match": True, "detail": "canonical"},
            "manifest_service": {"id_match": True, "detail": "canonical"},
        },
    })
    return api


@pytest.fixture
def client(fake_read_api):
    return TestClient(build_console_app(fake_read_api))


def test_ui_chat_stub_renders_200(client):
    r = client.get("/ui/chat")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")


def test_ui_chat_stub_body_copy(client):
    r = client.get("/ui/chat")
    assert r.status_code == 200
    assert "LLM Chat" in r.text
    assert (
        "LLM chat launches in Phase 12. For now, use the structured query console "
        "to explore tools and execution history."
    ) in r.text


def test_ui_chat_stub_chip_links(client):
    r = client.get("/ui/chat")
    assert r.status_code == 200
    assert 'href="/ui/tools?origin=synthesized"' in r.text
    assert "Browse synthesized tools" in r.text
    assert 'href="/ui/execs"' in r.text
    assert "View recent executions" in r.text


def test_ui_chat_stub_preserves_shell_chrome(client):
    """D-28: Full shell.html render with health strip intact."""
    r = client.get("/ui/chat")
    assert r.status_code == 200
    assert '<nav class="top-nav"' in r.text
    assert 'id="health-strip"' in r.text
    # Active nav state: chat link marked
    assert 'aria-current="page"' in r.text


def test_ui_chat_stub_uses_chat_stub_card_class(client):
    """CSS class contract — forge-console.css defines .chat-stub-card styling."""
    r = client.get("/ui/chat")
    assert "chat-stub-card" in r.text
