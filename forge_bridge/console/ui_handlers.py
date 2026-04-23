"""Full-page /ui/* route handlers for the v1.3 Artist Console Web UI.

Every handler reads through request.app.state.console_read_api (the
ConsoleReadAPI singleton from Phase 9). No handler parses JSONL, queries
ManifestService internals, or touches ExecutionLog fields directly -- the
instance-identity gate (Phase 9 API-04) silently enforces this at runtime.

Handler contract (mirrors handlers.py):
  - Wrap body in try/except Exception
  - Log type(exc).__name__ at WARNING with exc_info=True
  - NEVER leak tracebacks
  - Return TemplateResponse (errors/read_failed.html for 500)
"""
from __future__ import annotations

import logging

from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

logger = logging.getLogger(__name__)


# -- Helper: map query_params -> token string for D-26 pre-population --

_TOOLS_KEYS = ["origin", "namespace", "readonly", "q"]
_EXECS_KEYS = ["tool", "since", "until", "promoted", "hash"]
_MANIFEST_KEYS = ["q", "status"]

# API-param -> UI-grammar key reverse mapping (see fragments/query_console.html parse())
_API_TO_UI_KEY = {
    "promoted_only": "promoted",
    "code_hash": "hash",
}


def _query_params_as_tokens(query_params, supported_keys: list[str]) -> str:
    """D-26: reconstruct a `key:value key:value` token string from URL params
    so the query console input is pre-populated on first paint."""
    tokens = []
    for k, v in query_params.items():
        if k in ("limit", "offset"):
            continue  # pagination stays out of the query console
        ui_key = _API_TO_UI_KEY.get(k, k)
        if ui_key in supported_keys:
            tokens.append(f"{ui_key}:{v}")
        elif k in supported_keys:
            tokens.append(f"{k}:{v}")
    return " ".join(tokens)


def _render_error(request: Request, template: str, message: str, status: int) -> HTMLResponse:
    return request.app.state.templates.TemplateResponse(
        template,
        {"request": request, "message": message, "active_view": None},
        status_code=status,
    )


# -- Root redirect ----------------------------------------------------------

async def ui_index_handler(request: Request) -> HTMLResponse:
    """Redirect /ui/ -> /ui/tools (the default view)."""
    return RedirectResponse(url="/ui/tools", status_code=302)


# -- Tools view (Wave 1: registered-but-NOT-IMPLEMENTED; 10-04 fills in) ----

async def ui_tools_handler(request: Request) -> HTMLResponse:
    """501 stub. Plan 10-04 implements this."""
    return HTMLResponse(
        "<!doctype html><html><body><h1>Not Implemented</h1>"
        "<p>/ui/tools — pending plan 10-04.</p></body></html>",
        status_code=501,
    )


async def ui_tool_detail_handler(request: Request) -> HTMLResponse:
    """501 stub. Plan 10-04 implements this."""
    return HTMLResponse(
        "<!doctype html><html><body><h1>Not Implemented</h1>"
        "<p>/ui/tools/{name} — pending plan 10-04.</p></body></html>",
        status_code=501,
    )


# -- Execs view (Wave 1: stub; 10-05 fills in) ------------------------------

async def ui_execs_handler(request: Request) -> HTMLResponse:
    return HTMLResponse(
        "<!doctype html><html><body><h1>Not Implemented</h1>"
        "<p>/ui/execs — pending plan 10-05.</p></body></html>",
        status_code=501,
    )


async def ui_exec_detail_handler(request: Request) -> HTMLResponse:
    return HTMLResponse(
        "<!doctype html><html><body><h1>Not Implemented</h1>"
        "<p>/ui/execs/{code_hash}/{timestamp} — pending plan 10-05.</p></body></html>",
        status_code=501,
    )


# -- Manifest view (Wave 1: stub; 10-06 fills in) ---------------------------

async def ui_manifest_handler(request: Request) -> HTMLResponse:
    return HTMLResponse(
        "<!doctype html><html><body><h1>Not Implemented</h1>"
        "<p>/ui/manifest — pending plan 10-06.</p></body></html>",
        status_code=501,
    )


# -- Health dedicated view (Wave 1: stub; 10-06 fills in) -------------------

async def ui_health_view_handler(request: Request) -> HTMLResponse:
    return HTMLResponse(
        "<!doctype html><html><body><h1>Not Implemented</h1>"
        "<p>/ui/health — pending plan 10-06.</p></body></html>",
        status_code=501,
    )


# -- Chat stub (Wave 1: stub; 10-07 fills in) -------------------------------

async def ui_chat_stub_handler(request: Request) -> HTMLResponse:
    return HTMLResponse(
        "<!doctype html><html><body><h1>Not Implemented</h1>"
        "<p>/ui/chat — pending plan 10-07.</p></body></html>",
        status_code=501,
    )
