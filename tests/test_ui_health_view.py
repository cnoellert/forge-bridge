"""Functional tests for /ui/health view + /ui/fragments/health-view."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.testclient import TestClient

from forge_bridge.console.app import build_console_app


@pytest.fixture
def sample_health():
    return {
        "status": "degraded",
        "ts": "2026-04-22T12:00:00+00:00",
        "version": "1.3.0",
        "services": {
            "mcp": {"status": "ok", "detail": "lifespan started"},
            "flame_bridge": {"status": "fail", "detail": "ConnectTimeout", "url": "http://127.0.0.1:9999"},
            "ws_server": {"status": "ok", "detail": "tcp reachable", "url": "ws://127.0.0.1:9998"},
            "llm_backends": [
                {"name": "local", "status": "ok", "detail": "model=qwen2.5:3b"},
                {"name": "cloud", "status": "fail", "detail": "model=claude-3.5-sonnet"},
            ],
            "watcher": {"status": "ok", "detail": "", "task_done": False},
            "storage_callback": {"status": "absent", "detail": "no callback set"},
            "console_port": {"status": "ok", "port": 9996, "detail": "serving"},
        },
        "instance_identity": {
            "execution_log": {"id_match": True, "detail": "canonical"},
            "manifest_service": {"id_match": True, "detail": "canonical"},
        },
    }


@pytest.fixture
def fake_read_api(sample_health):
    api = MagicMock()
    api.get_health = AsyncMock(return_value=sample_health)
    api.get_tools = AsyncMock(return_value=[])
    api.get_tool = AsyncMock(return_value=None)
    api.get_executions = AsyncMock(return_value=([], 0))
    api.get_manifest = AsyncMock(return_value={"tools": [], "count": 0, "schema_version": "1"})
    return api


@pytest.fixture
def client(fake_read_api):
    return TestClient(build_console_app(fake_read_api))


def test_ui_health_full_page(client):
    r = client.get("/ui/health")
    assert r.status_code == 200
    assert "System Health" in r.text
    # Poll declaration
    assert 'id="health-view-content"' in r.text
    assert 'hx-trigger="every 5s[!document.hidden]"' in r.text
    # All services present
    assert "MCP server" in r.text
    assert "Flame bridge" in r.text
    assert "Watcher" in r.text
    # LLM backends rendered as separate cards
    assert "LLM: local" in r.text
    assert "LLM: cloud" in r.text
    # Aggregate pill
    assert "Degraded" in r.text
    # Instance identity section
    assert "Instance identity" in r.text


def test_fragment_health_view_returns_partial(client):
    r = client.get("/ui/fragments/health-view")
    assert r.status_code == 200
    assert "health-grid" in r.text
    assert '<nav class="top-nav"' not in r.text


def test_ui_health_500_no_traceback(fake_read_api):
    fake_read_api.get_health = AsyncMock(side_effect=RuntimeError("boom"))
    c = TestClient(build_console_app(fake_read_api))
    r = c.get("/ui/health", follow_redirects=False)
    assert r.status_code == 500
    assert "boom" not in r.text
    assert "Traceback" not in r.text
