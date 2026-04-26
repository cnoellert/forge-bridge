"""Route handlers for the v1.3 Artist Console HTTP API.

Every handler reads through `request.app.state.console_read_api` (the
ConsoleReadAPI singleton attached in build_console_app). No handler parses
JSONL, queries the MCP registry, or hits ExecutionLog/ManifestService
internals directly — EXECS-04 and API-01 compliance.

Envelope contract (D-01):
  - 2xx: {"data": <payload>, "meta": {...}}
  - 4xx/5xx: {"error": {"code": "<machine_string>", "message": "<human>"}}

Pagination contract (D-02 + D-05):
  - `?limit=N&offset=M` with defaults limit=50, offset=0, max limit=500 (silently clamped).
  - meta.limit reflects the CLAMPED limit.
  - meta.total is the count BEFORE pagination.

Filter contract (D-03):
  - `?since=<iso8601>` — parsed via datetime.fromisoformat; unparseable → 400.
  - `?promoted_only=true|false|1|0` — bool.
  - `?tool=<glob>` — REJECTED with 400 `not_implemented` in v1.3 (W-01,
    RESEARCH.md Open Questions (RESOLVED) Q#1). Revisit in v1.4.
  - `?code_hash=<prefix>` — string prefix match.

Phase 14 (FB-B) additions:
  - staged_list_handler  — GET /api/v1/staged (D-01, D-05, D-10)
  - staged_approve_handler — POST /api/v1/staged/{id}/approve (D-06, D-09, D-10)
  - staged_reject_handler  — POST /api/v1/staged/{id}/reject  (D-06, D-09, D-10)
  - _resolve_actor         — D-06 actor priority helper
  - _STAGED_STATUSES       — frozenset of valid status values for D-10 invalid_filter
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict
from datetime import datetime
from typing import Optional

from starlette.requests import Request
from starlette.responses import JSONResponse

from forge_bridge.store.staged_operations import StagedOpRepo, StagedOpLifecycleError

logger = logging.getLogger(__name__)

_DEFAULT_LIMIT = 50
_MAX_LIMIT = 500  # D-05


# -- Envelope helpers -------------------------------------------------------

def _envelope(data, **meta) -> JSONResponse:
    """2xx envelope — applied on every success path (D-01)."""
    return JSONResponse({"data": data, "meta": meta})


def _error(code: str, message: str, status: int = 400) -> JSONResponse:
    """4xx/5xx envelope — applied on every failure path. NEVER leak tracebacks."""
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)


def _envelope_json(data, **meta) -> str:
    """SAME serialization as _envelope — for MCP resource / tool shim use.

    Per D-26, resources/tools return byte-identical payloads to the HTTP route.
    This string form is what `register_console_resources` calls; the HTTP
    JSONResponse uses the SAME json.dumps path under the hood.
    """
    return json.dumps({"data": data, "meta": meta}, default=str)


# -- Query-param parsing ----------------------------------------------------

def _parse_pagination(request: Request) -> tuple[int, int]:
    """Return (limit, offset). limit clamped to [1, 500] per D-05."""
    try:
        limit = int(request.query_params.get("limit", _DEFAULT_LIMIT))
    except ValueError:
        limit = _DEFAULT_LIMIT
    try:
        offset = int(request.query_params.get("offset", 0))
    except ValueError:
        offset = 0
    limit = max(1, min(limit, _MAX_LIMIT))
    offset = max(0, offset)
    return limit, offset


def _parse_filters(request: Request) -> tuple[Optional[datetime], bool, Optional[str]]:
    """Return (since, promoted_only, code_hash).

    NOTE (W-01): `tool` is NOT parsed here — the route handler rejects
    `?tool=...` with a 400 `not_implemented` response BEFORE this function
    is called. Do not restore the `tool` parse without also removing the
    handler-level early-return (see execs_handler).
    """
    qp = request.query_params
    since_raw = qp.get("since")
    since: Optional[datetime] = None
    if since_raw is not None:
        try:
            since = datetime.fromisoformat(since_raw)
        except ValueError:
            # Surface as a parse error at the route boundary
            raise ValueError(f"invalid 'since' value: {since_raw!r} (expected ISO 8601)")
    promoted_only_raw = qp.get("promoted_only", "").lower()
    promoted_only = promoted_only_raw in ("1", "true", "yes", "on")
    code_hash = qp.get("code_hash") or None
    return since, promoted_only, code_hash


# -- Phase 14 (FB-B) — staged operations ------------------------------------

_STAGED_STATUSES = frozenset({"proposed", "approved", "rejected", "executed", "failed"})


async def _resolve_actor(request: Request) -> str:
    """D-06 priority: X-Forge-Actor header → body 'actor' field → 'http:anonymous'.

    Empty string in EITHER explicit source raises ValueError (caller maps to 400 bad_actor).
    Missing both → 'http:anonymous' fallback. Body parse failure (malformed JSON) is
    swallowed silently — falls through to 'http:anonymous'.
    """
    header_val = request.headers.get("X-Forge-Actor")
    if header_val is not None:
        if not header_val.strip():
            raise ValueError("X-Forge-Actor header is empty")
        return header_val

    body: dict | None = None
    try:
        body = await request.json()
    except Exception:
        body = None
    if isinstance(body, dict) and "actor" in body:
        actor = body["actor"]
        if not isinstance(actor, str) or not actor.strip():
            raise ValueError("body 'actor' field is empty or non-string")
        return actor

    return "http:anonymous"


async def staged_list_handler(request: Request) -> JSONResponse:
    """GET /api/v1/staged — list staged operations with optional filters.

    Reads through request.app.state.console_read_api.get_staged_ops (D-25 single
    read facade). All input is validated before reaching the DB (T-14-03-01).
    """
    try:
        limit, offset = _parse_pagination(request)
        status = request.query_params.get("status")
        if status is not None and status not in _STAGED_STATUSES:
            return _error(
                "invalid_filter",
                f"unknown status {status!r}; expected one of {sorted(_STAGED_STATUSES)}",
                status=400,
            )
        project_id_raw = request.query_params.get("project_id")
        project_id: uuid.UUID | None = None
        if project_id_raw is not None:
            try:
                project_id = uuid.UUID(project_id_raw)
            except ValueError:
                return _error("bad_request", "invalid project_id", status=400)
        records, total = await request.app.state.console_read_api.get_staged_ops(
            status=status, limit=limit, offset=offset, project_id=project_id,
        )
        return _envelope(
            [r.to_dict() for r in records],
            limit=limit, offset=offset, total=total,
        )
    except Exception as exc:
        logger.warning("staged_list_handler failed: %s", type(exc).__name__, exc_info=True)
        return _error("internal_error", "failed to read staged operations", status=500)


async def staged_approve_handler(request: Request) -> JSONResponse:
    """POST /api/v1/staged/{id}/approve — advance proposed → approved.

    D-04: writes bypass ConsoleReadAPI, go directly through StagedOpRepo.
    D-06: actor sourced from X-Forge-Actor header → body.actor → 'http:anonymous'.
    D-09: illegal transitions (including re-approve) return 409, never 200.
    D-10: from_status is None → 404; otherwise 409 with current_status.
    T-14-03-02: op_id parsed via uuid.UUID before reaching DB.
    """
    op_id_raw = request.path_params["id"]
    try:
        op_id = uuid.UUID(op_id_raw)
    except ValueError:
        return _error("bad_request", "invalid staged_operation id", status=400)

    try:
        actor = await _resolve_actor(request)
    except ValueError as ve:
        return _error("bad_actor", str(ve), status=400)

    try:
        session_factory = request.app.state.session_factory
        async with session_factory() as session:
            repo = StagedOpRepo(session)
            try:
                op = await repo.approve(op_id, approver=actor)
            except StagedOpLifecycleError as exc:
                if exc.from_status is None:
                    return _error(
                        "staged_op_not_found",
                        f"no staged_operation with id {op_id}",
                        status=404,
                    )
                return JSONResponse(
                    {"error": {
                        "code": "illegal_transition",
                        "message": str(exc),
                        "current_status": exc.from_status,
                    }},
                    status_code=409,
                )
            await session.commit()
        return _envelope(op.to_dict())
    except Exception as exc:
        logger.warning("staged_approve_handler failed: %s", type(exc).__name__, exc_info=True)
        return _error("internal_error", "failed to approve staged operation", status=500)


async def staged_reject_handler(request: Request) -> JSONResponse:
    """POST /api/v1/staged/{id}/reject — advance proposed → rejected.

    Symmetric to staged_approve_handler. Same D-04/D-06/D-09/D-10 contracts.
    """
    op_id_raw = request.path_params["id"]
    try:
        op_id = uuid.UUID(op_id_raw)
    except ValueError:
        return _error("bad_request", "invalid staged_operation id", status=400)

    try:
        actor = await _resolve_actor(request)
    except ValueError as ve:
        return _error("bad_actor", str(ve), status=400)

    try:
        session_factory = request.app.state.session_factory
        async with session_factory() as session:
            repo = StagedOpRepo(session)
            try:
                op = await repo.reject(op_id, actor=actor)
            except StagedOpLifecycleError as exc:
                if exc.from_status is None:
                    return _error(
                        "staged_op_not_found",
                        f"no staged_operation with id {op_id}",
                        status=404,
                    )
                return JSONResponse(
                    {"error": {
                        "code": "illegal_transition",
                        "message": str(exc),
                        "current_status": exc.from_status,
                    }},
                    status_code=409,
                )
            await session.commit()
        return _envelope(op.to_dict())
    except Exception as exc:
        logger.warning("staged_reject_handler failed: %s", type(exc).__name__, exc_info=True)
        return _error("internal_error", "failed to reject staged operation", status=500)


# -- Handlers ---------------------------------------------------------------

async def tools_handler(request: Request) -> JSONResponse:
    try:
        tools = await request.app.state.console_read_api.get_tools()
        return _envelope([t.to_dict() for t in tools], total=len(tools))
    except Exception as exc:
        logger.warning("tools_handler failed: %s", type(exc).__name__, exc_info=True)
        return _error("internal_error", "failed to read tools", status=500)


async def tool_detail_handler(request: Request) -> JSONResponse:
    name = request.path_params["name"]
    try:
        tool = await request.app.state.console_read_api.get_tool(name)
    except Exception as exc:
        logger.warning("tool_detail_handler failed: %s", type(exc).__name__, exc_info=True)
        return _error("internal_error", "failed to read tool", status=500)
    if tool is None:
        return _error("tool_not_found", f"no tool named {name!r}", status=404)
    return _envelope(tool.to_dict())


async def execs_handler(request: Request) -> JSONResponse:
    try:
        # W-01: reject `?tool=...` with 400 `not_implemented` — deferred to
        # v1.4 per RESEARCH.md Open Questions (RESOLVED) Q#1. Must fire
        # BEFORE any other parsing so a bad-tool + bad-since request
        # surfaces the more important `not_implemented` signal.
        if request.query_params.get("tool"):
            return _error(
                "not_implemented",
                "tool filter reserved for v1.4",
                status=400,
            )
        limit, offset = _parse_pagination(request)
        try:
            since, promoted_only, code_hash = _parse_filters(request)
        except ValueError as ve:
            return _error("bad_request", str(ve), status=400)
        records, total = await request.app.state.console_read_api.get_executions(
            limit=limit, offset=offset, since=since,
            promoted_only=promoted_only, code_hash=code_hash,
        )
        return _envelope(
            [asdict(r) for r in records],
            limit=limit, offset=offset, total=total,
        )
    except Exception as exc:
        logger.warning("execs_handler failed: %s", type(exc).__name__, exc_info=True)
        return _error("internal_error", "failed to read execs", status=500)


async def manifest_handler(request: Request) -> JSONResponse:
    try:
        data = await request.app.state.console_read_api.get_manifest()
        return _envelope(data)
    except Exception as exc:
        logger.warning("manifest_handler failed: %s", type(exc).__name__, exc_info=True)
        return _error("internal_error", "failed to read manifest", status=500)


async def health_handler(request: Request) -> JSONResponse:
    try:
        data = await request.app.state.console_read_api.get_health()
        return _envelope(data)
    except Exception as exc:
        logger.warning("health_handler failed: %s", type(exc).__name__, exc_info=True)
        return _error("internal_error", "failed to read health", status=500)
