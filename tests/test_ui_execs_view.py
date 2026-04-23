"""Functional tests for /ui/execs view — pagination, filter round-trip, drilldown."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.testclient import TestClient

from forge_bridge.console.app import build_console_app
from forge_bridge.learning.execution_log import ExecutionRecord


def _rec(code_hash, timestamp, intent="tool call", promoted=False, raw_code="bridge.execute('print(1)')"):
    return ExecutionRecord(
        code_hash=code_hash, raw_code=raw_code, intent=intent,
        timestamp=timestamp, promoted=promoted,
    )


@pytest.fixture
def sample_records():
    return [
        _rec("a" * 64, "2026-04-22T12:00:00+00:00", intent="list timeline", promoted=True),
        _rec("b" * 64, "2026-04-22T11:00:00+00:00", intent="get shot", promoted=False),
        _rec("c" * 64, "2026-04-22T10:00:00+00:00", intent="media scan", promoted=True),
    ]


@pytest.fixture
def fake_read_api(sample_records):
    api = MagicMock()

    async def _get_execs(limit=50, offset=0, since=None, promoted_only=False, code_hash=None):
        # Simulate server-side filter semantics
        records = list(sample_records)
        if since is not None:
            records = [r for r in records if datetime.fromisoformat(r.timestamp) >= since]
        if promoted_only:
            records = [r for r in records if r.promoted]
        if code_hash:
            records = [r for r in records if r.code_hash.startswith(code_hash)]
        total = len(records)
        return records[offset:offset + limit], total

    api.get_executions = _get_execs
    api.get_tools = AsyncMock(return_value=[])
    api.get_tool = AsyncMock(return_value=None)
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


def test_ui_execs_full_page(client):
    r = client.get("/ui/execs")
    assert r.status_code == 200
    assert "Execution History" in r.text
    assert "Refresh history" in r.text
    assert 'id="query-console-input"' in r.text
    assert "list timeline" in r.text
    assert "get shot" in r.text
    assert "media scan" in r.text


def test_ui_execs_empty_state(fake_read_api):
    async def _empty(limit=50, offset=0, **kw): return [], 0
    fake_read_api.get_executions = _empty
    c = TestClient(build_console_app(fake_read_api))
    r = c.get("/ui/execs")
    assert r.status_code == 200
    assert "No executions recorded" in r.text


def test_ui_execs_filter_promoted_only(client):
    r = client.get("/ui/execs?promoted_only=true")
    assert r.status_code == 200
    assert "list timeline" in r.text
    assert "media scan" in r.text
    assert "get shot" not in r.text
    # D-26: input pre-populated with `promoted:true`
    assert "promoted:true" in r.text


def test_ui_execs_filter_since_parses_iso(client):
    r = client.get("/ui/execs?since=2026-04-22T11:30:00%2B00:00")
    assert r.status_code == 200
    assert "list timeline" in r.text
    assert "get shot" not in r.text


def test_ui_execs_filter_since_invalid_returns_400(client):
    r = client.get("/ui/execs?since=not-a-date")
    assert r.status_code == 400
    assert "Traceback" not in r.text
    # errors/read_failed.html template rendered
    assert "Could not load" in r.text or "invalid" in r.text.lower()


def test_ui_execs_pagination(client):
    r = client.get("/ui/execs?limit=2&offset=0")
    assert r.status_code == 200
    # Page 1 of 2 for 3 records with limit=2
    assert "Page 1 of 2" in r.text
    # Next link present
    assert "offset=2" in r.text


def test_ui_execs_pagination_page2(client):
    r = client.get("/ui/execs?limit=2&offset=2")
    assert r.status_code == 200
    assert "Page 2 of 2" in r.text
    # Prev link present
    assert "offset=0" in r.text


def test_fragment_execs_table_returns_partial(client):
    r = client.get("/ui/fragments/execs-table")
    assert r.status_code == 200
    assert '<table class="data-table">' in r.text
    assert '<nav class="top-nav"' not in r.text


def test_fragment_execs_table_honors_filters(client):
    r = client.get("/ui/fragments/execs-table?promoted_only=true")
    assert r.status_code == 200
    assert "list timeline" in r.text
    assert "get shot" not in r.text


def test_ui_exec_detail_found(client):
    r = client.get("/ui/execs/" + "a" * 64 + "/2026-04-22T12:00:00%2B00:00")
    assert r.status_code == 200
    # Full hash rendered (D-16)
    assert "a" * 64 in r.text
    assert "list timeline" in r.text
    assert "Copy code" in r.text


def test_ui_exec_detail_not_found(client):
    r = client.get("/ui/execs/deadbeef/2026-04-22T12:00:00%2B00:00")
    assert r.status_code == 404
    assert "Not Found" in r.text or "not found" in r.text.lower()


def test_ui_execs_500_renders_error_template_without_traceback(fake_read_api):
    async def _boom(**kw): raise RuntimeError("boom")
    fake_read_api.get_executions = _boom
    c = TestClient(build_console_app(fake_read_api))
    r = c.get("/ui/execs", follow_redirects=False)
    assert r.status_code == 500
    assert "boom" not in r.text
    assert "Traceback" not in r.text
