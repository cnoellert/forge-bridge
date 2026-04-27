"""Phase 16.1 (D-07 #2) — UI-render regression guard.

Renders every /ui/* full-page route end-to-end and asserts (a) HTTP 200
after redirect resolution and (b) the canonical id="health-strip" sentinel
inherited from shell.html (Phase 10.1 D-39 invariant — every page that
extends shell.html contains the health-strip fragment).

Catches Bug A class: TemplateResponse signature drift (Starlette 1.0.0+)
silently breaks every UI route. With this test in default pytest discovery,
the deploy bug from 2026-04-27 fails on `pytest tests/` BEFORE deploy.

See:
  - .planning/phases/16-fb-d-chat-endpoint/16-VERIFICATION.md "Bug A"
  - .planning/phases/16.1-fb-d-chat-gap-closure/16.1-RESEARCH.md §5
  - forge_bridge/console/templates/shell.html line 16
  - forge_bridge/console/templates/fragments/health_strip.html line 2
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.testclient import TestClient


# Static enumeration of every `/ui/*` full-page route from
# `forge_bridge/console/app.py`. Parameterized routes
# (/ui/tools/{name}, /ui/execs/{code_hash}/{timestamp}) are excluded —
# they require seeded data; this guard covers shell rendering, not data binding.
# When a new /ui/* full-page route lands, add it to this list.
UI_ROUTES_TO_TEST = [
    "/ui/",            # ui_index_handler — 302 to /ui/tools
    "/ui/tools",       # ui_tools_handler
    "/ui/execs",       # ui_execs_handler
    "/ui/manifest",    # ui_manifest_handler
    "/ui/health",      # ui_health_view_handler
    "/ui/chat",        # ui_chat_handler (Phase 16)
]


@pytest.fixture
def render_client():
    """TestClient with every ConsoleReadAPI.get_* method stubbed AsyncMock.
    Sufficient to drive the TemplateResponse render path on every route."""
    from forge_bridge.console.app import build_console_app
    from forge_bridge.console.read_api import ConsoleReadAPI

    api = MagicMock(spec=ConsoleReadAPI)
    api.get_tools       = AsyncMock(return_value=[])
    api.get_executions  = AsyncMock(return_value=([], 0))
    api.get_manifest    = AsyncMock(return_value={"tools": []})
    api.get_health      = AsyncMock(return_value={
        "status": "ok", "services": {}, "instance_identity": {},
    })
    # llm_router not exercised by /ui/chat shell render — chat panel JS
    # owns the POST to /api/v1/chat. Setting attribute is harmless.
    api._llm_router = MagicMock()

    app = build_console_app(api)
    return TestClient(app)


@pytest.mark.parametrize("path", UI_ROUTES_TO_TEST)
def test_ui_route_renders_with_health_strip_sentinel(render_client, path):
    """Bug A regression guard.

    Phase 16 deploy bug (2026-04-27): Starlette 1.0.0 TemplateResponse signature
    drift caused every /ui/* page to fail at render with
    `TypeError: unhashable type: 'dict'`. This test asserts the rendered HTML
    contains the canonical id="health-strip" sentinel from shell.html.
    """
    response = render_client.get(path, follow_redirects=False)
    if response.status_code in (301, 302, 307, 308):
        response = render_client.get(response.headers["location"])
    assert response.status_code == 200, (
        f"GET {path} returned {response.status_code}: {response.text[:500]}"
    )
    assert 'id="health-strip"' in response.text, (
        f'GET {path} missing canonical id="health-strip" sentinel from '
        f"shell.html line 16 (Phase 10.1 D-39 invariant). "
        f"Rendered HTML: {response.text[:1000]}"
    )


def test_health_strip_sentinel_exists_in_shell():
    """Pin Phase 10.1 D-39 invariant: shell.html includes the health-strip fragment.
    If shell.html ever drops `{% include "fragments/health_strip.html" %}`,
    every parameterized test in this module fails together — this test
    catches the upstream drift directly."""
    shell_path = Path(__file__).parent.parent.parent / (
        "forge_bridge/console/templates/shell.html"
    )
    text = shell_path.read_text(encoding="utf-8")
    assert '{% include "fragments/health_strip.html" %}' in text, (
        "shell.html no longer includes the health-strip fragment. "
        "Phase 10.1 D-39 invariant violated. Either restore the include or "
        "update UI_ROUTES_TO_TEST sentinel pinning in this test module."
    )
