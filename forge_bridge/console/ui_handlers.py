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
import os
from pathlib import Path

from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

logger = logging.getLogger(__name__)

# Path to synthesized tool source files (T-10-18: confined to SYNTH_ROOT)
_SYNTH_ROOT = Path(os.environ.get(
    "FORGE_SYNTH_ROOT",
    str(Path.home() / ".forge-bridge" / "tools" / "synth"),
))


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


def _tools_preset_chips() -> list:
    """D-09: preset chip roster for the tools view."""
    return [
        {"label": "Active synth", "tokens": "origin:synthesized"},
        {"label": "Quarantined", "tokens": "origin:synthesized q:quarantined"},
        {"label": "Builtin only", "tokens": "origin:builtin"},
    ]


def _filter_tools(tools, qp):
    """Apply UI-grammar filters to get_tools() result.

    v1.3 does filtering in-Python because /api/v1/tools has no server-side
    filter params (D-23 — structured query console + preset chips are the
    only filter surface in v1.3).
    """
    origin = qp.get("origin")
    namespace = qp.get("namespace")
    readonly = qp.get("readonly")
    q = (qp.get("q") or "").lower()
    out = []
    for t in tools:
        if origin and t.origin != origin:
            continue
        if namespace and t.namespace != namespace:
            continue
        if readonly is not None:
            m = dict(t.meta) if t.meta else {}
            if str(m.get("read_only_hint", "")).lower() != readonly.lower():
                continue
        if q and q not in t.name.lower():
            continue
        out.append(t)
    return out


def _read_synth_source(name: str) -> str | None:
    """Best-effort: read raw source for a synthesized tool.

    Returns None if the file is missing or unreadable. Includes path-traversal
    guard (T-10-18): verifies the resolved path is still under _SYNTH_ROOT
    before reading.
    """
    candidate = _SYNTH_ROOT / f"{name}.py"
    try:
        resolved = candidate.resolve()
        try:
            resolved.relative_to(_SYNTH_ROOT.resolve())
        except ValueError:
            # Path escaped SYNTH_ROOT — reject silently (traversal attempt)
            return None
        if resolved.is_file():
            return resolved.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        logger.warning(
            "_read_synth_source failed for %s: %s",
            name, type(exc).__name__, exc_info=True,
        )
    return None


# -- Root redirect ----------------------------------------------------------

async def ui_index_handler(request: Request) -> HTMLResponse:
    """Redirect /ui/ -> /ui/tools (the default view)."""
    return RedirectResponse(url="/ui/tools", status_code=302)


# -- Tools view ---------------------------------------------------------------

async def ui_tools_handler(request: Request) -> HTMLResponse:
    """Full-page /ui/tools handler. Implements TOOLS-01 + CONSOLE-03."""
    try:
        tools = await request.app.state.console_read_api.get_tools()
    except Exception as exc:
        logger.warning(
            "ui_tools_handler failed: %s", type(exc).__name__, exc_info=True,
        )
        return _render_error(
            request, "errors/read_failed.html",
            "Could not load tools — the console API may be restarting. Refresh to try again.",
            500,
        )
    filtered = _filter_tools(tools, dict(request.query_params))
    querystring = "?" + str(request.query_params) if request.query_params else ""
    return request.app.state.templates.TemplateResponse(
        "tools/list.html",
        {
            "request": request,
            "active_view": "tools",
            "tools": [t.to_dict() for t in filtered],
            "query_params": dict(request.query_params),
            "query_params_as_tokens": _query_params_as_tokens(
                request.query_params, _TOOLS_KEYS,
            ),
            "querystring": querystring,
            "view_slug": "tools",
            "preset_chips": _tools_preset_chips(),
            "supported_keys": _TOOLS_KEYS,
        },
    )


async def ui_tool_detail_handler(request: Request) -> HTMLResponse:
    """Drilldown /ui/tools/{name} handler. Implements TOOLS-02."""
    name = request.path_params["name"]
    try:
        tool = await request.app.state.console_read_api.get_tool(name)
    except Exception as exc:
        logger.warning(
            "ui_tool_detail_handler failed: %s", type(exc).__name__, exc_info=True,
        )
        return _render_error(
            request, "errors/read_failed.html",
            "Could not load tool detail — the console API may be restarting.",
            500,
        )
    if tool is None:
        return _render_error(
            request, "errors/not_found.html",
            f"No tool named {name!r}.",
            404,
        )
    raw_code = None
    if tool.origin == "synthesized":
        raw_code = _read_synth_source(name)
    return request.app.state.templates.TemplateResponse(
        "tools/detail.html",
        {
            "request": request,
            "active_view": "tools",
            "tool": tool.to_dict(),
            "raw_code": raw_code,
        },
    )


# -- Execs view ---------------------------------------------------------------

def _execs_preset_chips() -> list:
    """D-09: preset chip roster for the execs view.

    'Last 24h' requires a client-computed ISO timestamp; for v1.3 we ship
    two absolute chips instead (planner recommendation — scope note in plan).
    """
    return [
        {"label": "Promoted only", "tokens": "promoted:true"},
        {"label": "Hash prefix", "tokens": "hash:abcd"},
    ]


async def ui_execs_handler(request: Request) -> HTMLResponse:
    """Full-page /ui/execs handler. Implements EXECS-01 + CONSOLE-03."""
    from dataclasses import asdict
    from forge_bridge.console.handlers import _parse_pagination, _parse_filters
    try:
        limit, offset = _parse_pagination(request)
        try:
            since, promoted_only, code_hash = _parse_filters(request)
        except ValueError as ve:
            return _render_error(
                request, "errors/read_failed.html",
                f"Could not load executions — {ve}",
                400,
            )
        records, total = await request.app.state.console_read_api.get_executions(
            limit=limit, offset=offset, since=since,
            promoted_only=promoted_only, code_hash=code_hash,
        )
    except Exception as exc:
        logger.warning(
            "ui_execs_handler failed: %s", type(exc).__name__, exc_info=True,
        )
        return _render_error(
            request, "errors/read_failed.html",
            "Could not load execution history — the console API may be restarting.",
            500,
        )
    # Build filter_querystring (filters only, no limit/offset — so pagination
    # links preserve filter state without multiplying pagination params).
    filter_parts = []
    for key in ("since", "promoted_only", "code_hash"):
        val = request.query_params.get(key)
        if val:
            filter_parts.append(f"&{key}={val}")
    filter_qs = "".join(filter_parts)
    querystring = "?" + str(request.query_params) if request.query_params else ""
    return request.app.state.templates.TemplateResponse(
        "execs/list.html",
        {
            "request": request,
            "active_view": "execs",
            "records": [asdict(r) for r in records],
            "total": total,
            "limit": limit,
            "offset": offset,
            "querystring": querystring,
            "filter_querystring": filter_qs,
            "query_params": dict(request.query_params),
            "query_params_as_tokens": _query_params_as_tokens(
                request.query_params, _EXECS_KEYS,
            ),
            "view_slug": "execs",
            "preset_chips": _execs_preset_chips(),
            "supported_keys": _EXECS_KEYS,
        },
    )


async def ui_exec_detail_handler(request: Request) -> HTMLResponse:
    """Drilldown /ui/execs/{code_hash}/{timestamp} handler. Implements EXECS-02."""
    from dataclasses import asdict
    code_hash = request.path_params["code_hash"]
    timestamp = request.path_params["timestamp"]
    try:
        # Find the record: ask for records matching this hash prefix; match timestamp.
        records, _ = await request.app.state.console_read_api.get_executions(
            limit=500, offset=0, code_hash=code_hash,
        )
    except Exception as exc:
        logger.warning(
            "ui_exec_detail_handler failed: %s", type(exc).__name__, exc_info=True,
        )
        return _render_error(
            request, "errors/read_failed.html",
            "Could not load execution detail.",
            500,
        )
    match = next(
        (r for r in records if r.code_hash == code_hash and r.timestamp == timestamp),
        None,
    )
    if match is None:
        return _render_error(
            request, "errors/not_found.html",
            f"No execution recorded for hash {code_hash[:8]!r} at {timestamp!r}.",
            404,
        )
    return request.app.state.templates.TemplateResponse(
        "execs/detail.html",
        {
            "request": request,
            "active_view": "execs",
            "record": asdict(match),
        },
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
