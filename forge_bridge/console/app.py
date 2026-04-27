"""Starlette application factory for the v1.3 Artist Console HTTP API."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from forge_bridge.console.handlers import (
    chat_handler,                      # NEW (Phase 16 / FB-D)
    execs_handler,
    health_handler,
    manifest_handler,
    staged_approve_handler,   # NEW (Plan 14-03)
    staged_list_handler,      # NEW (Plan 14-03)
    staged_reject_handler,    # NEW (Plan 14-03)
    tool_detail_handler,
    tools_handler,
)
from forge_bridge.console.ui_fragments import (
    execs_table_fragment,
    health_strip_fragment,
    health_view_fragment,
    manifest_table_fragment,
    tools_table_fragment,
)
from forge_bridge.console.ui_handlers import (
    ui_chat_stub_handler,
    ui_exec_detail_handler,
    ui_execs_handler,
    ui_health_view_handler,
    ui_index_handler,
    ui_manifest_handler,
    ui_tool_detail_handler,
    ui_tools_handler,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from forge_bridge.console.read_api import ConsoleReadAPI

logger = logging.getLogger(__name__)

# Localhost-only CORS allow-list (D-28 locks bind to 127.0.0.1; browser
# tabs may present as http://127.0.0.1:9996 OR http://localhost:9996).
_ALLOW_ORIGINS = ["http://127.0.0.1:9996", "http://localhost:9996"]

_CONSOLE_DIR = Path(__file__).parent


def build_console_app(
    read_api: "ConsoleReadAPI",
    session_factory: Optional["async_sessionmaker"] = None,
) -> Starlette:
    """Construct the Starlette ASGI app for /api/v1/* and /ui/*.

    Phase 9 shipped /api/v1/* JSON routes. Phase 10 adds /ui/* HTML routes
    (Jinja2 templates), /ui/fragments/* htmx partial routes, and the
    /ui/static/* static-asset mount — all served from the SAME Starlette
    instance, reading through the SAME ConsoleReadAPI. No second app, no
    second read layer (Phase 9 D-25).
    """
    templates = Jinja2Templates(directory=str(_CONSOLE_DIR / "templates"))

    routes = [
        # Phase 9 — JSON API (UNCHANGED)
        Route("/api/v1/tools", tools_handler, methods=["GET"]),
        Route("/api/v1/tools/{name}", tool_detail_handler, methods=["GET"]),
        Route("/api/v1/execs", execs_handler, methods=["GET"]),
        Route("/api/v1/manifest", manifest_handler, methods=["GET"]),
        Route("/api/v1/health", health_handler, methods=["GET"]),
        # Phase 10 — full-page /ui/* routes (HTML via Jinja2)
        Route("/ui/", ui_index_handler, methods=["GET"]),
        Route("/ui/tools", ui_tools_handler, methods=["GET"]),
        Route("/ui/tools/{name}", ui_tool_detail_handler, methods=["GET"]),
        Route("/ui/execs", ui_execs_handler, methods=["GET"]),
        Route("/ui/execs/{code_hash}/{timestamp}", ui_exec_detail_handler, methods=["GET"]),
        Route("/ui/manifest", ui_manifest_handler, methods=["GET"]),
        Route("/ui/health", ui_health_view_handler, methods=["GET"]),
        Route("/ui/chat", ui_chat_stub_handler, methods=["GET"]),
        # Phase 10 — fragment /ui/fragments/* routes (htmx partial swaps)
        Route("/ui/fragments/health-strip", health_strip_fragment, methods=["GET"]),
        Route("/ui/fragments/tools-table", tools_table_fragment, methods=["GET"]),
        Route("/ui/fragments/execs-table", execs_table_fragment, methods=["GET"]),
        Route("/ui/fragments/manifest-table", manifest_table_fragment, methods=["GET"]),
        Route("/ui/fragments/health-view", health_view_fragment, methods=["GET"]),
        # Phase 10 — static assets served from forge_bridge/console/static/
        Mount("/ui/static", StaticFiles(directory=str(_CONSOLE_DIR / "static")), name="static"),
        # Phase 14 (FB-B) — staged operations
        Route("/api/v1/staged", staged_list_handler, methods=["GET"]),
        Route("/api/v1/staged/{id}/approve", staged_approve_handler, methods=["POST"]),
        Route("/api/v1/staged/{id}/reject", staged_reject_handler, methods=["POST"]),
        # Phase 16 (FB-D) — chat endpoint
        Route("/api/v1/chat", chat_handler, methods=["POST"]),
    ]
    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=_ALLOW_ORIGINS,
            allow_methods=["GET", "POST"],  # NEW: POST for /staged/{id}/approve|reject
            allow_headers=["*"],            # already allows X-Forge-Actor via wildcard
            allow_credentials=False,
        ),
    ]
    app = Starlette(routes=routes, middleware=middleware)
    app.state.console_read_api = read_api
    app.state.session_factory = session_factory   # NEW (D-05) — write handlers read this
    app.state.templates = templates
    return app
