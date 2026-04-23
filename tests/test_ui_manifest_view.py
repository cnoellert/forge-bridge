"""Functional tests for /ui/manifest view."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.testclient import TestClient

from forge_bridge.console.app import build_console_app


@pytest.fixture
def sample_manifest():
    return {
        "tools": [
            {
                "name": "synth_recent_a",
                "origin": "synthesized",
                "namespace": "synth",
                "synthesized_at": "2026-04-22T10:00:00Z",
                "code_hash": "a" * 64,
                "version": "1.0.0",
                "observation_count": 7,
                "tags": ["cursor"],
                "meta": {},
            },
            {
                "name": "synth_orphan",
                "origin": "synthesized",
                "namespace": "synth",
                "synthesized_at": None,
                "code_hash": None,
                "version": None,
                "observation_count": 0,
                "tags": [],
                "meta": {},
            },
        ],
        "count": 2,
        "schema_version": "1",
    }


@pytest.fixture
def fake_read_api(sample_manifest):
    api = MagicMock()
    api.get_manifest = AsyncMock(return_value=sample_manifest)
    api.get_tools = AsyncMock(return_value=[])
    api.get_tool = AsyncMock(return_value=None)
    api.get_executions = AsyncMock(return_value=([], 0))
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


def test_ui_manifest_full_page(client):
    r = client.get("/ui/manifest")
    assert r.status_code == 200
    assert "Synthesis Manifest" in r.text
    assert "Refresh manifest" in r.text
    assert "synth_recent_a" in r.text
    assert "synth_orphan" in r.text
    assert "2 entries" in r.text


def test_ui_manifest_empty(fake_read_api):
    fake_read_api.get_manifest = AsyncMock(return_value={
        "tools": [], "count": 0, "schema_version": "1",
    })
    c = TestClient(build_console_app(fake_read_api))
    r = c.get("/ui/manifest")
    assert r.status_code == 200
    assert "Manifest is empty" in r.text


def test_ui_manifest_filter_q(client):
    r = client.get("/ui/manifest?q=recent")
    assert r.status_code == 200
    assert "synth_recent_a" in r.text
    assert "synth_orphan" not in r.text


def test_ui_manifest_filter_status_orphaned(client):
    r = client.get("/ui/manifest?status=orphaned")
    assert r.status_code == 200
    assert "synth_orphan" in r.text
    assert "synth_recent_a" not in r.text


def test_fragment_manifest_table_returns_partial(client):
    r = client.get("/ui/fragments/manifest-table")
    assert r.status_code == 200
    assert '<table class="data-table">' in r.text
    assert '<nav class="top-nav"' not in r.text


def test_ui_manifest_500_no_traceback(fake_read_api):
    fake_read_api.get_manifest = AsyncMock(side_effect=RuntimeError("boom"))
    c = TestClient(build_console_app(fake_read_api))
    r = c.get("/ui/manifest", follow_redirects=False)
    assert r.status_code == 500
    assert "boom" not in r.text
    assert "Traceback" not in r.text
