"""Fragment /ui/fragments/* route handlers for htmx partial swaps.

Fragment templates are bare HTML (no {% extends %}) and carry their own
hx-trigger declaration so each poll re-emits the next poll cycle (D-06).

All handlers read through request.app.state.console_read_api and log
exceptions without leaking tracebacks, same posture as ui_handlers.py.
"""
from __future__ import annotations

import logging

from starlette.requests import Request
from starlette.responses import HTMLResponse

from forge_bridge.console.ui_handlers import _filter_tools

logger = logging.getLogger(__name__)


# -- Health strip fragment (Wave 1: SMALL REAL IMPLEMENTATION so shell.html's
# -- server-side {% include %} works on first paint even before 10-06 runs). --

async def health_strip_fragment(request: Request) -> HTMLResponse:
    """Poll target for the persistent health strip (D-06, D-20: 10s cadence).

    Plan 10-06 may enhance this, but Wave 1 ships a minimal working
    implementation so shell.html's first-paint {% include %} resolves
    correctly during Wave 2 development.
    """
    try:
        data = await request.app.state.console_read_api.get_health()
    except Exception as exc:
        logger.warning(
            "health_strip_fragment failed: %s", type(exc).__name__,
            exc_info=True,
        )
        data = {
            "status": "fail",
            "services": {},
            "instance_identity": {},
        }
    return request.app.state.templates.TemplateResponse(
        "fragments/health_strip.html",
        {"request": request, "health": data},
    )


# -- Tools table fragment -----------------------------------------------------

async def tools_table_fragment(request: Request) -> HTMLResponse:
    """Bare table fragment for htmx outerHTML swap from the Refresh tools button."""
    try:
        tools = await request.app.state.console_read_api.get_tools()
    except Exception as exc:
        logger.warning(
            "tools_table_fragment failed: %s", type(exc).__name__, exc_info=True,
        )
        return HTMLResponse(
            '<div class="empty-state">'
            "<strong>Could not load tools</strong><br>"
            "The console API may be restarting."
            "</div>",
            status_code=500,
        )
    filtered = _filter_tools(tools, dict(request.query_params))
    return request.app.state.templates.TemplateResponse(
        "fragments/tools_table.html",
        {
            "request": request,
            "tools": [t.to_dict() for t in filtered],
        },
    )


# -- Execs table fragment -----------------------------------------------------

async def execs_table_fragment(request: Request) -> HTMLResponse:
    """Bare table fragment for htmx outerHTML swap from the Refresh history button."""
    from dataclasses import asdict
    from forge_bridge.console.handlers import _parse_pagination, _parse_filters
    try:
        limit, offset = _parse_pagination(request)
        try:
            since, promoted_only, code_hash = _parse_filters(request)
        except ValueError as ve:
            return HTMLResponse(
                f'<div class="empty-state"><strong>Invalid filter</strong><br>{ve}</div>',
                status_code=400,
            )
        records, total = await request.app.state.console_read_api.get_executions(
            limit=limit, offset=offset, since=since,
            promoted_only=promoted_only, code_hash=code_hash,
        )
    except Exception as exc:
        logger.warning(
            "execs_table_fragment failed: %s", type(exc).__name__, exc_info=True,
        )
        return HTMLResponse(
            '<div class="empty-state"><strong>Could not load executions</strong></div>',
            status_code=500,
        )
    return request.app.state.templates.TemplateResponse(
        "fragments/execs_table.html",
        {
            "request": request,
            "records": [asdict(r) for r in records],
        },
    )


# -- Manifest table fragment (Wave 1: stub; 10-06 fills in) -----------------

async def manifest_table_fragment(request: Request) -> HTMLResponse:
    return HTMLResponse(
        "<p>manifest-table fragment — pending plan 10-06.</p>",
        status_code=501,
    )


# -- Health view fragment (Wave 1: stub; 10-06 fills in) --------------------

async def health_view_fragment(request: Request) -> HTMLResponse:
    return HTMLResponse(
        "<p>health-view fragment — pending plan 10-06.</p>",
        status_code=501,
    )
