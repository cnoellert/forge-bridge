"""Functional tests for /ui/tools view.

Covers TOOLS-01 (browse + filters), TOOLS-02 (drilldown with provenance +
raw source), CONSOLE-03 (structured query console).
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.testclient import TestClient

from forge_bridge.console.app import build_console_app
from forge_bridge.console.manifest_service import ToolRecord


def _make_record(name, origin="synthesized", namespace="synth",
                 code_hash="a" * 64, synthesized_at="2026-04-01T12:00:00Z",
                 observation_count=5, tags=(), meta=()):
    return ToolRecord(
        name=name, origin=origin, namespace=namespace,
        synthesized_at=synthesized_at, code_hash=code_hash,
        version="1.0.0", observation_count=observation_count,
        tags=tags, meta=meta,
    )


@pytest.fixture
def sample_tools():
    return [
        _make_record("synth_recent_a", origin="synthesized", namespace="synth",
                     synthesized_at="2026-04-22T10:00:00Z",
                     observation_count=7, tags=("cursor", "claude")),
        _make_record("synth_recent_b", origin="synthesized", namespace="synth",
                     synthesized_at="2026-04-22T09:00:00Z",
                     observation_count=3, tags=("claude",)),
        _make_record("flame_builtin_timeline", origin="builtin",
                     namespace="flame", code_hash=None, synthesized_at=None,
                     observation_count=0, tags=()),
        _make_record("forge_builtin_shot", origin="builtin", namespace="forge",
                     code_hash=None, synthesized_at=None, observation_count=0),
    ]


@pytest.fixture
def fake_read_api(sample_tools):
    api = MagicMock()
    api.get_tools = AsyncMock(return_value=sample_tools)

    async def _get_tool(name):
        for t in sample_tools:
            if t.name == name:
                return t
        return None
    api.get_tool = _get_tool
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


# -- Full-page /ui/tools ---------------------------------------------------

def test_ui_tools_full_page_renders_list(client):
    r = client.get("/ui/tools")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert "Registered Tools" in r.text
    assert "Refresh tools" in r.text
    assert 'id="query-console-input"' in r.text
    for name in ("synth_recent_a", "synth_recent_b",
                 "flame_builtin_timeline", "forge_builtin_shot"):
        assert name in r.text, f"missing tool {name}"


def test_ui_tools_empty_state(fake_read_api):
    fake_read_api.get_tools = AsyncMock(return_value=[])
    c = TestClient(build_console_app(fake_read_api))
    r = c.get("/ui/tools")
    assert r.status_code == 200
    assert "No tools registered" in r.text


def test_ui_tools_filter_origin_synthesized(client):
    r = client.get("/ui/tools?origin=synthesized")
    assert r.status_code == 200
    assert "synth_recent_a" in r.text
    assert "synth_recent_b" in r.text
    assert "flame_builtin_timeline" not in r.text


def test_ui_tools_filter_namespace(client):
    r = client.get("/ui/tools?namespace=flame")
    assert r.status_code == 200
    assert "flame_builtin_timeline" in r.text
    assert "synth_recent_a" not in r.text


def test_ui_tools_filter_q_substring(client):
    r = client.get("/ui/tools?q=recent")
    assert r.status_code == 200
    assert "synth_recent_a" in r.text
    assert "synth_recent_b" in r.text
    assert "flame_builtin_timeline" not in r.text


def test_ui_tools_query_input_prepopulated_from_url(client):
    r = client.get("/ui/tools?origin=synthesized")
    assert r.status_code == 200
    assert "origin:synthesized" in r.text


def test_ui_tools_preset_chips_present(client):
    r = client.get("/ui/tools")
    assert r.status_code == 200
    assert "Synth only" in r.text
    assert "Builtin only" in r.text


# -- Fragment /ui/fragments/tools-table ------------------------------------

def test_fragment_tools_table_returns_partial(client):
    r = client.get("/ui/fragments/tools-table")
    assert r.status_code == 200
    assert '<table class="data-table">' in r.text
    assert '<nav class="top-nav"' not in r.text
    assert 'id="health-strip"' not in r.text


def test_fragment_tools_table_honors_filters(client):
    r = client.get("/ui/fragments/tools-table?origin=builtin")
    assert r.status_code == 200
    assert "flame_builtin_timeline" in r.text
    assert "synth_recent_a" not in r.text


# -- Drilldown /ui/tools/{name} --------------------------------------------

def test_ui_tool_detail_shows_all_five_meta_fields(client):
    r = client.get("/ui/tools/synth_recent_a")
    assert r.status_code == 200
    for key in ("origin", "code_hash", "synthesized_at", "version", "observation_count"):
        assert f"<dt>{key}</dt>" in r.text, f"missing dt {key}"
    # Full code_hash shown (D-16)
    assert "a" * 64 in r.text
    assert "cursor" in r.text
    assert "claude" in r.text


def test_ui_tool_detail_builtin_has_no_raw_source_section(client):
    r = client.get("/ui/tools/flame_builtin_timeline")
    assert r.status_code == 200
    assert "Copy source" not in r.text


def test_ui_tool_detail_not_found(client):
    r = client.get("/ui/tools/nonexistent-tool")
    assert r.status_code == 404
    assert "Not Found" in r.text or "not found" in r.text.lower()


def test_ui_tool_detail_renders_sidecar_details_collapsed(client):
    r = client.get("/ui/tools/synth_recent_a")
    assert r.status_code == 200
    assert "Show raw sidecar JSON (engineer mode)" in r.text
    assert "<details" in r.text
    assert "Copy JSON" in r.text


# -- Error posture ---------------------------------------------------------

def test_ui_tools_500_renders_error_template_without_traceback(fake_read_api):
    fake_read_api.get_tools = AsyncMock(side_effect=RuntimeError("boom"))
    c = TestClient(build_console_app(fake_read_api))
    r = c.get("/ui/tools", follow_redirects=False)
    assert r.status_code == 500
    assert "boom" not in r.text
    assert "Traceback" not in r.text
    assert "Could not load" in r.text or "console API may be restarting" in r.text
