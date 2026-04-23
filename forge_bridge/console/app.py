"""Starlette application factory for the v1.3 Artist Console HTTP API."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Route

from forge_bridge.console.handlers import (
    execs_handler,
    health_handler,
    manifest_handler,
    tool_detail_handler,
    tools_handler,
)

if TYPE_CHECKING:
    from forge_bridge.console.read_api import ConsoleReadAPI

logger = logging.getLogger(__name__)

# Localhost-only CORS allow-list (D-28 locks bind to 127.0.0.1; browser
# tabs may present as http://127.0.0.1:9996 OR http://localhost:9996).
_ALLOW_ORIGINS = ["http://127.0.0.1:9996", "http://localhost:9996"]


def build_console_app(read_api: "ConsoleReadAPI") -> Starlette:
    """Construct the Starlette ASGI app for /api/v1/*.

    The ConsoleReadAPI is attached to `app.state.console_read_api` so route
    handlers can reach it via `request.app.state.console_read_api` without
    module-level globals.
    """
    routes = [
        Route("/api/v1/tools", tools_handler, methods=["GET"]),
        Route("/api/v1/tools/{name}", tool_detail_handler, methods=["GET"]),
        Route("/api/v1/execs", execs_handler, methods=["GET"]),
        Route("/api/v1/manifest", manifest_handler, methods=["GET"]),
        Route("/api/v1/health", health_handler, methods=["GET"]),
    ]
    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=_ALLOW_ORIGINS,
            allow_methods=["GET"],
            allow_headers=["*"],
            allow_credentials=False,
        ),
    ]
    app = Starlette(routes=routes, middleware=middleware)
    app.state.console_read_api = read_api
    return app
