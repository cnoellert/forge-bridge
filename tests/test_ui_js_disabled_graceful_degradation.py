"""JS-disabled graceful degradation smoke test (D-05).

Direct URL navigation to every full-page /ui/* route returns a complete
HTML document (doctype, head, body, main content) on first paint — no
JS required to render the correct view content. This is not a certified
UAT surface, but it's a regression guard against htmx breakage and a
free gift for SSH-tunnel workflows.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.testclient import TestClient

from forge_bridge.console.app import build_console_app
from forge_bridge.console.manifest_service import ToolRecord


@pytest.fixture
def fake_read_api():
    tool = ToolRecord(
        name="synth_example", origin="synthesized", namespace="synth",
        synthesized_at="2026-04-22T10:00:00Z",
        code_hash="a" * 64, version="1.0.0", observation_count=5,
        tags=("cursor",), meta=(),
    )
    api = MagicMock()
    api.get_tools = AsyncMock(return_value=[tool])
    api.get_tool = AsyncMock(return_value=tool)
    api.get_executions = AsyncMock(return_value=([], 0))
    api.get_manifest = AsyncMock(return_value={
        "tools": [tool.to_dict()], "count": 1, "schema_version": "1",
    })
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


@pytest.mark.parametrize("path,expected_substr", [
    ("/ui/tools",                "Registered Tools"),
    ("/ui/tools/synth_example",  "Provenance (_meta)"),
    ("/ui/execs",                "Execution History"),
    ("/ui/manifest",             "Synthesis Manifest"),
    ("/ui/health",               "System Health"),
    ("/ui/chat",                 "LLM Chat"),
])
def test_direct_navigation_renders_full_document(client, path, expected_substr):
    """D-05: every full-page route returns a complete HTML doc on first paint."""
    r = client.get(path)
    assert r.status_code == 200
    # Complete HTML structure
    assert "<!doctype html>" in r.text.lower()
    assert "<html" in r.text
    assert "</html>" in r.text
    assert "<head>" in r.text
    assert "<body>" in r.text
    # Shell chrome present (so health strip + nav render without JS hydrate)
    assert '<nav class="top-nav"' in r.text
    assert 'id="health-strip"' in r.text
    # View-specific content
    assert expected_substr in r.text


def test_health_strip_included_server_side_on_first_paint(client):
    """D-06: shell.html server-side-includes the health strip so it paints
    immediately — no JS needed for HEALTH-04 first-paint compliance."""
    r = client.get("/ui/tools")
    assert r.status_code == 200
    # The fragment is included inline (not loaded via hx-get on mount)
    assert 'id="health-strip"' in r.text
    # Aggregate pill + dot row — NOT just a loading placeholder
    assert "agg-pill" in r.text
    assert "dot-row" in r.text


def test_css_link_present_for_js_disabled_styling(client):
    """All views link the stylesheet so basic typography + color survive
    JS-disabled mode."""
    r = client.get("/ui/tools")
    assert 'href="/ui/static/forge-console.css"' in r.text


def test_nav_links_are_anchor_tags_not_buttons(client):
    """D-03/D-05: nav uses `<a href>` so browsers handle them natively with
    JS off. htmx only enhances them; it doesn't replace them."""
    r = client.get("/ui/tools")
    assert 'href="/ui/tools"' in r.text
    assert 'href="/ui/execs"' in r.text
    assert 'href="/ui/manifest"' in r.text
    assert 'href="/ui/health"' in r.text
    assert 'href="/ui/chat"' in r.text
