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


# -- Tools table fragment (Wave 1: stub; 10-04 fills in) --------------------

async def tools_table_fragment(request: Request) -> HTMLResponse:
    return HTMLResponse(
        "<p>tools-table fragment — pending plan 10-04.</p>",
        status_code=501,
    )


# -- Execs table fragment (Wave 1: stub; 10-05 fills in) --------------------

async def execs_table_fragment(request: Request) -> HTMLResponse:
    return HTMLResponse(
        "<p>execs-table fragment — pending plan 10-05.</p>",
        status_code=501,
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
