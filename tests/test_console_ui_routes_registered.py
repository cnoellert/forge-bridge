"""Route-registration smoke test for the v1.3 Artist Console Web UI.

Every /ui/* and /ui/fragments/* route MUST be registered in
forge_bridge/console/app.py so Wave 2 plans can fill in handlers without
touching the route table. This test asserts every route resolves (200 or
501, never 404) and that the Phase 9 /api/v1/* surface still returns 200.

Run: pytest tests/test_console_ui_routes_registered.py -x
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.testclient import TestClient

from forge_bridge.console.app import build_console_app


@pytest.fixture
def fake_read_api():
    """Minimal ConsoleReadAPI stand-in; all methods return empty/valid shapes."""
    read_api = MagicMock()
    read_api.get_tools = AsyncMock(return_value=[])
    read_api.get_tool = AsyncMock(return_value=None)
    read_api.get_executions = AsyncMock(return_value=([], 0))
    read_api.get_manifest = AsyncMock(
        return_value={"tools": [], "count": 0, "schema_version": "1"}
    )
    read_api.get_health = AsyncMock(
        return_value={
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
        }
    )
    return read_api


@pytest.fixture
def client(fake_read_api):
    app = build_console_app(fake_read_api)
    return TestClient(app)


# -- Phase 9 regression: /api/v1/* still works -----------------------------

@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/tools",
        "/api/v1/execs",
        "/api/v1/manifest",
        "/api/v1/health",
    ],
)
def test_phase9_api_routes_return_200(client, path):
    r = client.get(path)
    assert r.status_code == 200, f"{path} regressed to {r.status_code}"


# -- Phase 10: /ui/ root redirects to /ui/tools ----------------------------

def test_ui_root_redirects_to_tools(client):
    r = client.get("/ui/", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/ui/tools"


# -- Phase 10: full-page /ui/* routes are REGISTERED (never 404) -----------

@pytest.mark.parametrize(
    "path",
    [
        "/ui/tools",
        "/ui/tools/example-tool",
        "/ui/execs",
        "/ui/execs/abc123/2026-01-01T00:00:00Z",
        "/ui/manifest",
        "/ui/health",
        "/ui/chat",
    ],
)
def test_ui_full_page_routes_registered(client, path):
    r = client.get(path)
    # Wave 1 stubs return 501 until Wave 2 fills them in; health strip
    # fragment returns 200 because it has a real Wave-1 implementation.
    # What we're guarding against is a 404 — that would mean a route the
    # Wave 2 plans need is MISSING from the registry.
    assert r.status_code != 404, (
        f"{path} returned 404 — route not registered. "
        f"Wave 2 plans depend on every /ui/* route being present."
    )


# -- Phase 10: fragment /ui/fragments/* routes are REGISTERED --------------

@pytest.mark.parametrize(
    "path",
    [
        "/ui/fragments/health-strip",
        "/ui/fragments/tools-table",
        "/ui/fragments/execs-table",
        "/ui/fragments/manifest-table",
        "/ui/fragments/health-view",
    ],
)
def test_ui_fragment_routes_registered(client, path):
    r = client.get(path)
    assert r.status_code != 404, f"{path} returned 404 — fragment route not registered"


# -- Phase 10: health strip fragment is Wave-1 functional (200, not stub) --

def test_health_strip_fragment_returns_200_in_wave_1(client):
    """shell.html server-side-includes the health strip on every view;
    if this returns 501 or 500 in Wave 1, every view 500s."""
    r = client.get("/ui/fragments/health-strip")
    assert r.status_code == 200, (
        f"/ui/fragments/health-strip returned {r.status_code}. "
        f"Wave 1 plan 10-03 must ship a real implementation of "
        f"health_strip_fragment so shell.html's server-side {{% include %}} "
        f"succeeds on first paint of every view."
    )
    # Body MUST contain the health-strip container and aggregate pill.
    assert 'id="health-strip"' in r.text
    assert "agg-pill" in r.text


# -- Phase 10: static asset mount is registered at /ui/static ----------------

def test_ui_static_mount_registered(client):
    """StaticFiles mount at /ui/static should serve forge-console.css."""
    r = client.get("/ui/static/forge-console.css")
    assert r.status_code == 200, (
        f"/ui/static/forge-console.css returned {r.status_code}. "
        f"Expected 200; the Mount at /ui/static in build_console_app "
        f"must resolve to forge_bridge/console/static/forge-console.css."
    )
    assert "text/css" in r.headers.get("content-type", ""), (
        f"content-type was {r.headers.get('content-type')}"
    )


# -- Phase 10: vendored JS assets served through the mount -------------------

@pytest.mark.parametrize(
    "path",
    [
        "/ui/static/vendor/htmx-2.0.10.min.js",
        "/ui/static/vendor/alpinejs-3.14.1.min.js",
    ],
)
def test_vendored_js_assets_served(client, path):
    r = client.get(path)
    assert r.status_code == 200, f"{path} returned {r.status_code}"
    ctype = r.headers.get("content-type", "")
    assert "javascript" in ctype.lower() or "text" in ctype.lower(), (
        f"unexpected content-type for {path}: {ctype}"
    )


# -- Phase 10: app.state.templates is wired --------------------------------

def test_app_state_templates_attached(fake_read_api):
    app = build_console_app(fake_read_api)
    # Starlette .state raises on unknown attrs; hasattr wouldn't; explicit:
    assert app.state.templates is not None
    # Phase 9 contract preserved
    assert app.state.console_read_api is fake_read_api
