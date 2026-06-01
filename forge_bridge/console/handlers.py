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

import asyncio
import json
import logging
import re
import time
import uuid
from dataclasses import asdict
from datetime import datetime
from typing import Any, Optional

from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse

from forge_bridge.console._constants import CHAIN_MAX_STEPS
from forge_bridge.console._answer import _last_user_question, _synthesize_answer
from forge_bridge.console._chat_compile import (
    build_compile_system_prompt,
    run_apply_branch,
    run_compile_branch,
)
from forge_bridge.console._engine import run_chain_steps
from forge_bridge.console._macros import delete_macro, expand_macro, list_macros
from forge_bridge.console._step import serialize_forced_tool_result
from forge_bridge.console._rate_limit import (
    RateLimitDecision,
    check_rate_limit,
)
from forge_bridge.console._tool_enforcement import is_tool_enforced
from forge_bridge.console._tool_filter import (
    deterministic_narrow,
    filter_tools_by_message,
    filter_tools_by_reachable_backends,
)
from forge_bridge.llm.router import (
    CompileBudgetExceeded,
    CompileInvalidChainShape,
    CompileSeamViolation,
    CompileToolUnknown,
    CompileUnresolvableIntent,
    LLMLoopBudgetExceeded,
    LLMToolError,
    RecursiveToolLoopError,
)
from forge_bridge.llm.resolver import (
    enrich_messages_with_resolved_entities,
    resolve_query_entities,
    resolved_entity_params,
)
from forge_bridge.mcp.arguments import normalize_tool_args
from forge_bridge.store.staged_operations import StagedOpRepo, StagedOpLifecycleError
from forge_bridge.comprehension import emit_comprehension_capture

# Shape A — top-level guarded import (PR 4 step 6 topology lock).
#
# Corpus availability is resolved ONCE at handler module load. The
# `except ImportError:` branch defines fallback bindings that
# preserve the call-site contract (divergence_capture_enabled
# returns False; emit_divergence_capture is a no-op) when the
# corpus package is structurally absent.
#
# Maintenance invariant: fallback signatures intentionally mirror
# the public corpus API surface. Signature drift between the
# fallback and the real implementation risks asymmetric behavior
# under hostile environments — future corpus API expansion must
# preserve compatibility with the fallback shapes here. The *_args,
# **_kwargs catchalls absorb benign evolution; semantic changes
# (e.g., adding a required parameter that fallbacks must honor)
# require explicit synchronized updates to both surfaces.
#
# This duplication is intentional, not participation creep — the
# fallbacks observe nothing about the corpus, do nothing about
# arbitration, and disappear when the real corpus is importable.
# Per A.5.3.2-PR4-FRAMING.md §1.4, the no-dependency property
# requires that the import itself be optional; this is the
# minimum surface that makes that requirement operational.
try:
    from forge_bridge.corpus import (
        divergence_capture_enabled,
        emit_divergence_capture,
    )
except ImportError as _corpus_import_error:
    # Direct getLogger call used intentionally here: this branch
    # executes during module-load-time topology resolution before
    # the module-level logger binding below exists.
    logging.getLogger(__name__).warning(
        "forge_bridge.corpus is structurally absent at handler load; "
        "divergence-capture disabled for this process lifetime. "
        "(Import-time observation, distinct from "
        "FORGE_BRIDGE_DIVERGENCE_CAPTURE env-driven gating.) "
        "import_error=%s",
        _corpus_import_error,
    )

    def divergence_capture_enabled(*_args, **_kwargs) -> bool:
        return False

    def emit_divergence_capture(*_args, **_kwargs) -> None:
        pass

logger = logging.getLogger(__name__)

_APPLY_GRAMMAR = re.compile(r"^apply\s+([a-f0-9]{12})\s*$")

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
        return header_val.strip()

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


# -- PR40 — POST /api/v1/exec (deterministic execute; PR31 body, not D-01) ---

_EXEC_HTTP_TIMEOUT = 60.0
_exec_sem = asyncio.Semaphore(1)
_exec_log = logging.getLogger("forge.exec")


async def api_v1_exec_handler(request: Request) -> JSONResponse:
    """Run ``execute_command`` with server-side serialization and a time limit.

    Returns the raw PR31 dict (``status``, ``request_id``, ``chain``, ``error``).
    """
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}

    raw = payload.get("text")
    text = raw.strip() if isinstance(raw, str) else ""

    http_rid = str(uuid.uuid4())
    _exec_log.info("exec start rid=%s text=%r", http_rid, text)

    from forge_bridge.console import app as appmod

    try:
        async with _exec_sem:
            result = await asyncio.wait_for(
                appmod.execute_command(text),
                timeout=_EXEC_HTTP_TIMEOUT,
            )
    except asyncio.TimeoutError:
        rid = str(uuid.uuid4())
        _exec_log.info(
            "exec end rid=%s engine_rid=%s status=error code=TIMEOUT",
            http_rid,
            None,
        )
        return JSONResponse(
            {
                "status": "error",
                "request_id": rid,
                "chain": [],
                "error": {
                    "code": "TIMEOUT",
                    "message": "Command execution exceeded time limit.",
                    "step_index": None,
                    "original_error": None,
                },
            }
        )

    engine_rid = result.get("request_id")
    _exec_log.info(
        "exec end rid=%s engine_rid=%s status=%s",
        http_rid,
        engine_rid,
        result.get("status"),
    )
    return JSONResponse(result)


# -- Phase 16 (FB-D) — chat endpoint -----------------------------------------

# D-02 valid roles per native provider shape (Anthropic + Ollama both accept these).
_CHAT_VALID_ROLES = frozenset({"user", "assistant", "tool"})


# PR20 — deterministic tool execution when filter narrows to a single tool.
#
# Trigger condition:
#     tools_filtered_count == 1 AND tools_filtered_count < tools_available_count
#
# The second clause is the safety guard against the degenerate case where the
# system itself has only one tool available (test fixtures, bare-backend
# deployments). In that case the filter cannot narrow — a single survivor is
# either a coincidence or the capability-loss fallback (see
# `_tool_filter.filter_tools_by_message` — falls back to the full list when
# no tool name matches the message). Forcing in that case would call a tool
# the user never asked for, so we leave the LLM in charge.
#
# Behavior:
#   - Tool is invoked with empty arguments (`{}`). PR brief: "params = None
#     (default) OR minimal inferred params if trivial" — empty dict is the
#     trivial case and matches what the LLM would send for a no-arg call.
#   - Validation / tool errors return a structured tool message in the chat
#     reply (NOT 500) so the consumer (`fbridge chat`) can surface the error
#     with the same shape as `fbridge run`. The HTTP envelope stays 200.
#   - Response carries `tool_forced=True` (only on this path) plus a new
#     `stop_reason="tool_forced"` so the wrapper trace can distinguish a
#     forced call from a normal `end_turn`.
#   - LLM router is NEVER invoked on this path. No clarification round-trip,
#     no fallback to text — see brief STOP CONDITIONS.


async def _execute_forced_tool(
    *,
    tool: Any,
    messages: list,
    request_id: str,
    started: float,
    client_ip: str,
    tools_available_count: int,
    tools_filtered_count: int,
    tool_enforced_flag: bool,
    user_params: Optional[dict] = None,
) -> JSONResponse:
    """PR20 short-circuit: invoke the sole filtered tool and shape the chat
    reply. The LLM router is not called on this path.

    PR28 — ``user_params`` carries values the user explicitly supplied in
    the message (today: ``project_id=<uuid>`` or a single bare UUID; see
    ``_param_extract.extract_explicit_params``). They flow into
    ``resolve_required_params`` as caller params, so PR26's precedence
    chain (explicit > memory > resolver) collapses ambiguity before the
    PR27 disambiguation envelope would fire."""
    from forge_bridge.console._name_resolve import resolve_name_from_candidates
    from forge_bridge.console._tool_chain import (
        DISAMBIGUATION_KEY,
        UNRESOLVED_KEY,
        resolve_required_params,
    )
    from forge_bridge.mcp import server as _mcp_server

    tool_call_id = f"forced_{uuid.uuid4().hex[:12]}"
    tool_name = tool.name

    # PR25/26/27/28/29: deterministic required-parameter resolution. For
    # tools listed in the chain registry, this issues at most one upstream
    # tool call (e.g. `forge_list_projects`) and merges the resolved value
    # into params when — and only when — the system state is unambiguous.
    # PR28 seeds the resolver with caller-supplied params extracted from
    # the user message (handler scope), so an explicit ``project_id=<uuid>``
    # short-circuits both memory hydration and the upstream probe via the
    # PR26 precedence chain (explicit > memory > resolver). Returns the
    # PR27 disambiguation sentinel when the resolver finds 2+ candidates
    # AND the caller did not supply the required key explicitly.
    #
    # PR29 — ``project_name`` is consumed by the handler's name-resolution
    # branch below, NOT by the resolver. Pop it BEFORE the resolver call
    # so it doesn't leak into the tool's argument dict (forge tools
    # don't accept a ``project_name`` kwarg, and the trace would be
    # noisier than necessary). The popped value flows through to the
    # disambiguation branch via ``requested_name``.
    resolver_input = dict(user_params or {})
    requested_name = resolver_input.pop("project_name", None)
    resolver_message = next(
        (
            m["content"] for m in reversed(messages)
            if isinstance(m, dict)
            and m.get("role") == "user"
            and isinstance(m.get("content"), str)
        ),
        "",
    )
    params: dict = await resolve_required_params(
        tool_name, resolver_input, _mcp_server.mcp, message=resolver_message,
    )

    # PR27: ambiguity short-circuit. When the resolver finds multiple
    # valid candidates (today: 2+ projects), it returns a sentinel dict
    # in place of a usable params payload. PR29 adds a deterministic
    # second chance: if the user supplied ``project_name=<string>``
    # in the message, attempt an exact match against the SAME candidate
    # list before surfacing the structured 400 envelope. On a unique
    # match, inject the resolved id, re-run the resolver (which short-
    # circuits in memory hydration since project_id is now caller-
    # supplied), and fall through to the tool-execution path below.
    # Otherwise, surface ``MULTIPLE_PROJECTS`` exactly as PR27 does.
    if DISAMBIGUATION_KEY in params:
        disambiguation = params[DISAMBIGUATION_KEY]
        candidates = disambiguation.get("candidates", []) or []
        candidate_count = len(candidates)

        # PR29 — name-resolution fallback. ``requested_name`` is the
        # value popped above from ``user_params["project_name"]`` (set
        # only when the caller wrote ``project_name=<value>`` in the
        # message — PR28's extractor). Resolution is exact-match-only
        # and operates entirely on the candidate list returned by the
        # resolver — no upstream probe, no LLM, no memory read.
        # Returns ``None`` on zero or 2+ matches; in either case we
        # fall through to the existing MULTIPLE_PROJECTS envelope.
        resolved_id: Optional[str] = None
        if requested_name:
            resolved_id = resolve_name_from_candidates(
                requested_name, candidates,
            )

        if resolved_id:
            elapsed_ms = int((time.monotonic() - started) * 1000)
            # Telemetry — log the LABEL of the resolved key only,
            # never the name string or the resolved id. Mirrors the
            # disambiguation log shape so consumers can compare
            # rates of "resolved via name" vs "fell through to 400".
            logger.info(
                "chat tool_forced_name_resolved key=project_id "
                "request_id=%s client_ip=%s tool=%s "
                "tools_available=%d tools_filtered=%d wall_clock_ms=%d "
                "candidates=%d",
                request_id, client_ip, tool_name,
                tools_available_count, tools_filtered_count, elapsed_ms,
                candidate_count,
            )
            # Re-run resolution with the now-explicit project_id. The
            # re-call short-circuits before any upstream probe (PR26's
            # caller-params-take-precedence guard) and never writes
            # memory (PR28's "explicit never writes memory" contract
            # carries through unchanged). The returned dict is the
            # canonical post-resolution params for the trace below.
            params = await resolve_required_params(
                tool_name,
                {"project_id": resolved_id},
                _mcp_server.mcp,
                message=resolver_message,
            )
            # Fall through to the ``mcp.call_tool`` block below. DO
            # NOT return — the rest of the forced-execution path
            # (trace assembly, telemetry, JSONResponse) must run.
        else:
            elapsed_ms = int((time.monotonic() - started) * 1000)
            # ``key=project_id`` is the triggering parameter — hardcoded
            # today because ``project_id`` is the only disambiguatable
            # required key in the chain registry. When multi-key chains
            # ship, derive this from the disambiguation payload (e.g.
            # via a ``key`` field on the sentinel) instead of the
            # ``type`` field. Logs only the LABEL of the missing key —
            # never any candidate id or name.
            logger.info(
                "chat tool_forced_disambiguation key=project_id "
                "request_id=%s client_ip=%s tool=%s "
                "tools_available=%d tools_filtered=%d wall_clock_ms=%d "
                "candidates=%d",
                request_id, client_ip, tool_name,
                tools_available_count, tools_filtered_count, elapsed_ms,
                candidate_count,
            )
            return _chat_error(
                code="MULTIPLE_PROJECTS",
                message="Multiple projects found. Please specify one.",
                status=400,
                request_id=request_id,
                details=disambiguation,
            )

    if UNRESOLVED_KEY in params:
        unresolved = params[UNRESOLVED_KEY]
        key = unresolved.get("key")
        message = (
            "Could not resolve sequence name from your query. "
            "Please specify the exact sequence name."
        )
        if key == "reel_name":
            message = (
                "Could not resolve reel name from your query. "
                "Please specify the exact reel name."
            )
        elapsed_ms = int((time.monotonic() - started) * 1000)
        logger.info(
            "chat tool_forced_unresolved key=%s request_id=%s client_ip=%s "
            "tool=%s tools_available=%d tools_filtered=%d wall_clock_ms=%d",
            key, request_id, client_ip, tool_name,
            tools_available_count, tools_filtered_count, elapsed_ms,
        )
        return JSONResponse(
            {
                "error": message,
                "request_id": request_id,
                "tool": tool_name,
                "unresolved": unresolved,
                "tools_available": tools_available_count,
                "tools_filtered": tools_filtered_count,
                "tool_enforced": tool_enforced_flag,
                "tool_forced": False,
                "stop_reason": "tool_unresolved",
            },
            status_code=200,
            headers={"X-Request-ID": request_id},
        )

    # Phase A.2 trace bookkeeping — the short-circuit invokes exactly one
    # tool, so the trace always has exactly one entry. Result is the parsed
    # tool output on success, None on failure; error is the failure message
    # or None on success. Symmetric with the LLM-loop path's _record_trace.
    trace_result: Any = None
    trace_error: Optional[str] = None

    try:
        params = normalize_tool_args(tool_name, params, [tool])
        raw = await _mcp_server.mcp.call_tool(tool_name, params)
        tool_content = serialize_forced_tool_result(raw)
        tool_ok = True
        # Surface the parsed tool output in the trace when it's JSON; fall
        # back to the raw string so callers never lose visibility on shape.
        try:
            trace_result = json.loads(tool_content) if isinstance(tool_content, str) else tool_content
        except (json.JSONDecodeError, ValueError):
            trace_result = tool_content
    except Exception as exc:  # noqa: BLE001 — classify, don't propagate
        # Validation / tool error — surface as a structured tool message
        # mirroring the `fbridge run` failure shape so the CLI can render
        # it identically to a normal tool failure.
        tool_content = json.dumps({
            "error": {
                "type": type(exc).__name__,
                "message": str(exc),
            }
        })
        tool_ok = False
        trace_error = f"{type(exc).__name__}: {exc!s}"
        logger.info(
            "chat tool_forced_error request_id=%s tool=%s exc_type=%s",
            request_id, tool_name, type(exc).__name__,
        )

    out_messages = list(messages) + [
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{
                "id": tool_call_id,
                "type": "function",
                "function": {"name": tool_name, "arguments": json.dumps(params)},
            }],
        },
        {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": tool_content,
        },
    ]

    # Phase A.2: short-circuit always produces exactly one trace entry.
    tool_trace: list[dict] = [{
        "tool_name": tool_name,
        "arguments": dict(params) if params else {},
        "result": trace_result,
        "error": trace_error,
        "index": 0,
    }]

    elapsed_ms = int((time.monotonic() - started) * 1000)
    logger.info(
        "chat tool_forced request_id=%s client_ip=%s tool=%s "
        "tools_available=%d tools_filtered=%d wall_clock_ms=%d "
        "stop_reason=tool_forced tool_ok=%s",
        request_id, client_ip, tool_name,
        tools_available_count, tools_filtered_count, elapsed_ms, tool_ok,
    )
    return JSONResponse(
        {
            # Phase A: short-circuit emits the same canonical top-level keys
            # as the LLM-loop path. The model never spoke on this path, so
            # final_text is empty by Phase A decision (the assistant turn
            # in messages is the synthetic tool_call entry, not a reply).
            "final_text": "",
            "messages": out_messages,
            "tool_trace": tool_trace,
            "stop_reason": "tool_forced",
            "request_id": request_id,
            "tools_available": tools_available_count,
            "tools_filtered": tools_filtered_count,
            "tool_enforced": tool_enforced_flag,
            "tool_forced": True,
        },
        status_code=200,
        headers={"X-Request-ID": request_id},
    )


# -- PR30 — multi-step tool chaining ---------------------------------------
# Step execution: ``forge_bridge.console._step.execute_chain_step``.
# Shared engine dict: ``forge_bridge.console._engine.run_chain_steps``.


async def _execute_chain(
    *,
    steps: list[str],
    tools: list,
    request_id: str,
    client_ip: str,
    started: float,
) -> JSONResponse:
    """Sequentially execute a list of chain steps. Abort on first error.

    PR31 — unified envelope (body built by ``run_chain_steps``).
    """
    from forge_bridge.mcp import server as _mcp_server

    mcp = _mcp_server.mcp
    body = await run_chain_steps(
        steps=steps,
        tools=tools,
        mcp=mcp,
        request_id=request_id,
        client_ip=client_ip,
        started=started,
    )
    status_code = 400 if body.get("status") == "error" else 200
    return JSONResponse(
        body,
        status_code=status_code,
        headers={"X-Request-ID": request_id},
    )


def _chat_error(
    code: str,
    message: str,
    status: int,
    request_id: str,
    extra_headers: Optional[dict] = None,
    details: Optional[dict] = None,
) -> JSONResponse:
    """Chat-endpoint error helper (D-17 NESTED envelope + X-Request-ID always).

    The existing `_error()` helper at lines 58-60 produces the same body shape
    but does not accept a headers kwarg; the chat endpoint needs every reply
    to carry X-Request-ID per D-17 / D-21, so this thin wrapper is the single
    error-path emitter throughout chat_handler.

    PR27 — optional ``details`` field. When present, it's nested under
    the ``error`` object so structured-error consumers (e.g. the chat
    UI rendering a disambiguation prompt) can pull machine-readable
    context from one canonical location:

        {"error": {"code": "...", "message": "...", "details": {...}}}

    Existing callers that don't pass ``details`` see no shape change.
    """
    headers = {"X-Request-ID": request_id}
    if extra_headers:
        headers.update(extra_headers)
    body: dict = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return JSONResponse(
        body,
        status_code=status,
        headers=headers,
    )


def _compile_error_payload(exc: Exception) -> tuple[str, str, int, dict]:
    """Map compile-stage structural errors to chat error envelopes."""
    if isinstance(exc, CompileUnresolvableIntent):
        return (
            "compile_unresolvable_intent",
            "Could not compile the request into a graph intent.",
            422,
            {"raw_response": exc.raw_response},
        )
    if isinstance(exc, CompileInvalidChainShape):
        return (
            "compile_invalid_chain_shape",
            "Compiled graph intent was malformed.",
            422,
            {
                "raw_response": exc.raw_response,
                "parse_error": exc.parse_error,
            },
        )
    if isinstance(exc, CompileToolUnknown):
        return (
            "compile_tool_unknown",
            "Compiled graph intent referenced an unavailable tool.",
            422,
            {
                "unknown_tool": exc.unknown_tool,
                "step_index": exc.step_index,
                "step_text": exc.step_text,
            },
        )
    if isinstance(exc, CompileBudgetExceeded):
        return (
            "compile_budget_exceeded",
            "Compile timed out — try a simpler request.",
            504,
            {
                "max_seconds": exc.max_seconds,
                "elapsed_s": exc.elapsed_s,
            },
        )
    if isinstance(exc, CompileSeamViolation):
        return (
            "compile_seam_violation",
            "Compiled graph intent violated the mutation authority seam.",
            500,
            {
                "offending_step_text": exc.offending_step_text,
                "offending_step_index": exc.offending_step_index,
            },
        )
    return (
        "compile_error",
        "Compile failed — check console for details.",
        500,
        {},
    )


def _ambiguity_state_for(n: int) -> str:
    """Translate narrowing-count to the schema's ``ambiguity_state``
    string. Translation-only; no inferential logic per the binding
    constraint in ``A.5.3.2-PR4-SPEC.md`` §4.1.

    A future PR proposing to add "smart" ambiguity detection
    (e.g., "if multi_survivor but the tools share a common prefix,
    classify as semi_collapsed") is rejected at the spec layer —
    that interpretation belongs in Layer 2 or a higher analytic
    layer, not in the capture call site.
    """
    return {0: "zero_survivor", 1: "single_survivor"}.get(n, "multi_survivor")


def _format_sse_event(event: str, data: dict) -> str:
    """Format one Server-Sent Events frame per the HTML5 SSE spec.

    `data:` is single-line JSON per W3C — no embedded newlines in payload
    (json.dumps with default separators is single-line, so no escaping
    needed for our schema). Trailing blank line is the frame terminator.
    """
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _apply_complete_body(outcome, transport: str) -> dict:
    return {
        "kind": "apply_complete",
        "graph_intent_id": outcome.graph_intent_id,
        "chain": outcome.chain_body,
        "stop_reason": "apply_complete",
        "chat_regime": "ratified_apply",
        "transport": transport,
    }


async def _chat_sse_response(
    *,
    router: Any,
    messages: list[dict],
    tools: list,
    mcp: Any,
    max_iterations: int,
    tool_result_max_bytes: Optional[int],
    request_id: str,
    client_ip: str,
    started: float,
    tool_call_count_in: int,
    tools_available_count: int,
    tools_filtered_count: int,
    session_factory: Optional[Any] = None,
) -> StreamingResponse:
    """SSE response for the A.1 compile branch."""
    msg_queue: asyncio.Queue = asyncio.Queue()
    _DONE = object()  # sentinel for end of stream

    async def _run_loop() -> None:
        try:
            try:
                compile_prompt = next(
                    (
                        m["content"] for m in reversed(messages)
                        if isinstance(m, dict)
                        and m.get("role") == "user"
                        and isinstance(m.get("content"), str)
                    ),
                    "",
                )
                apply_match = _APPLY_GRAMMAR.match(compile_prompt.strip())
                if apply_match:
                    outcome = await run_apply_branch(
                        graph_intent_id=apply_match.group(1),
                        session_factory=session_factory,
                        tools=tools,
                        mcp=mcp,
                        request_id=request_id,
                        client_ip=client_ip,
                        started=started,
                    )
                    if outcome.regime == "error":
                        await msg_queue.put(("error", {"error": outcome.error}))
                        return
                    if outcome.regime == "chain_aborted":
                        body = dict(outcome.chain_body or {})
                        body["stop_reason"] = "chain_aborted"
                        body["graph_intent_id"] = outcome.graph_intent_id
                        await msg_queue.put(("chain_aborted", body))
                        return
                    await msg_queue.put((
                        "apply_complete",
                        _apply_complete_body(outcome, "sse"),
                    ))
                    return
                outcome = await asyncio.wait_for(
                    run_compile_branch(
                        router=router,
                        user_prompt=compile_prompt,
                        tools=tools,
                        mcp=mcp,
                        request_id=request_id,
                        client_ip=client_ip,
                        started=started,
                        compile_system=build_compile_system_prompt(tools),
                        session_factory=session_factory,
                    ),
                    timeout=125.0,
                )
            except asyncio.TimeoutError:
                elapsed_ms = int((time.monotonic() - started) * 1000)
                logger.info(
                    "chat timeout request_id=%s client_ip=%s message_count_in=%d "
                    "tools_offered_count=%d wall_clock_ms=%d "
                    "stop_reason=outer_wait_for_timeout transport=sse",
                    request_id, client_ip, len(messages), len(tools), elapsed_ms,
                )
                await msg_queue.put(("error", {"error": {
                    "code": "request_timeout",
                    "message": "Response timed out — try a simpler question or fewer tools.",
                }}))
                return
            except LLMLoopBudgetExceeded:
                elapsed_ms = int((time.monotonic() - started) * 1000)
                logger.info(
                    "chat loop_budget request_id=%s client_ip=%s tools_offered_count=%d "
                    "wall_clock_ms=%d stop_reason=loop_budget_exceeded transport=sse",
                    request_id, client_ip, len(tools), elapsed_ms,
                )
                await msg_queue.put(("error", {"error": {
                    "code": "request_timeout",
                    "message": "Response timed out — try a simpler question or fewer tools.",
                }}))
                return
            except RecursiveToolLoopError:
                logger.warning(
                    "chat recursive_loop request_id=%s transport=sse — should not "
                    "reach handler (synthesizer guard). Investigate.",
                    request_id,
                )
                await msg_queue.put(("error", {"error": {
                    "code": "internal_error",
                    "message": "Chat error — check console for details.",
                }}))
                return
            except LLMToolError as exc:
                logger.warning(
                    "chat tool_error request_id=%s exc_type=%s transport=sse",
                    request_id, type(exc).__name__,
                )
                await msg_queue.put(("error", {"error": {
                    "code": "internal_error",
                    "message": "Chat error — check console for details.",
                }}))
                return
            except Exception as exc:
                logger.warning(
                    "chat_handler sse failed request_id=%s exc_type=%s",
                    request_id, type(exc).__name__, exc_info=True,
                )
                await msg_queue.put(("error", {"error": {
                    "code": "internal_error",
                    "message": "Chat error — check console for details.",
                }}))
                return

            elapsed_ms = int((time.monotonic() - started) * 1000)
            if outcome.regime == "compile_error":
                code, message, _status, details = _compile_error_payload(
                    outcome.compile_error
                )
                logger.info(
                    "chat compile_error request_id=%s client_ip=%s "
                    "tools_offered_count=%d wall_clock_ms=%d "
                    "transport=sse chat_regime=compile_error",
                    request_id, client_ip, len(tools), elapsed_ms,
                )
                await msg_queue.put(("compile_error", {"error": {
                    "code": code,
                    "message": message,
                    "details": details,
                }, "stop_reason": "compile_error", "request_id": request_id}))
                return

            if outcome.steps:
                await msg_queue.put(("compile_complete", {
                    "request_id": request_id,
                    "steps_count": len(outcome.steps),
                }))

            if outcome.regime == "chain_aborted":
                body = dict(outcome.chain_body or {})
                body["stop_reason"] = "chain_aborted"
                logger.info(
                    "chat chain_aborted request_id=%s client_ip=%s "
                    "steps=%d tools_offered_count=%d wall_clock_ms=%d "
                    "transport=sse chat_regime=compiled_non_mutating",
                    request_id, client_ip, len(outcome.steps), len(tools),
                    elapsed_ms,
                )
                await msg_queue.put(("chain_aborted", body))
                return

            if outcome.regime == "compiled_mutating_preview":
                logger.info(
                    "chat preview_emitted request_id=%s client_ip=%s "
                    "steps=%d tools_offered_count=%d wall_clock_ms=%d "
                    "transport=sse chat_regime=compiled_mutating_preview",
                    request_id, client_ip, len(outcome.steps), len(tools),
                    elapsed_ms,
                )
                await msg_queue.put(("preview_emitted", {
                    "preview": outcome.preview,
                    "chain": [],
                    "stop_reason": "preview_emitted",
                    "request_id": request_id,
                    "tools_available": tools_available_count,
                    "tools_filtered": tools_filtered_count,
                    "tool_enforced": False,
                    "tool_forced": False,
                }))
                return

            chain_body = outcome.chain_body or {}
            logger.info(
                "chat ok request_id=%s client_ip=%s message_count_in=%d "
                "steps=%d tool_call_count=%d tools_offered_count=%d "
                "wall_clock_ms=%d stop_reason=chain_complete transport=sse "
                "chat_regime=compiled_non_mutating",
                request_id, client_ip, len(messages), len(outcome.steps),
                tool_call_count_in, len(tools), elapsed_ms,
            )
            await msg_queue.put(("chain_complete", {
                "chain": chain_body.get("chain", []),
                "stop_reason": "chain_complete",
                "request_id": request_id,
                "tools_available": tools_available_count,
                "tools_filtered": tools_filtered_count,
                "tool_enforced": False,
                "tool_forced": False,
                "preview": None,
            }))
        finally:
            # Sentinel guarantees the SSE generator unblocks even if the
            # loop crashes in an unhandled way before reaching an explicit
            # error/done emit (defense-in-depth — the per-except blocks
            # above all explicit-return before reaching this finally).
            await msg_queue.put(_DONE)

    loop_task = asyncio.create_task(_run_loop())

    async def _event_generator():
        try:
            while True:
                item = await msg_queue.get()
                if item is _DONE:
                    return
                event_kind, payload = item
                yield _format_sse_event(event_kind, payload)
        finally:
            if not loop_task.done():
                loop_task.cancel()
                # Don't await — we're in cleanup; await would block on the
                # cancellation that's already in flight.

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "X-Request-ID": request_id,
            "Cache-Control": "no-cache",
            # X-Accel-Buffering disables nginx response buffering for SSE in
            # case a future deployment puts forge-bridge behind nginx —
            # harmless when no proxy is present (operator-workstation default).
            "X-Accel-Buffering": "no",
        },
    )


async def ratify_endpoint(request: Request) -> JSONResponse:
    """POST /api/v1/ratify — atomic ratify + apply for fbridge ratify."""
    request_id = str(uuid.uuid4())
    client_ip = request.client.host if request.client else "unknown"
    started = time.monotonic()

    decision: RateLimitDecision = check_rate_limit(client_ip)
    if not decision.allowed:
        return _chat_error(
            "rate_limit_exceeded",
            f"Rate limit reached — wait {decision.retry_after}s before retrying.",
            429,
            request_id,
            extra_headers={"Retry-After": str(decision.retry_after)},
        )

    try:
        body = await request.json()
    except Exception:
        return _chat_error(
            "validation_error",
            "request body is not valid JSON",
            400,
            request_id,
        )
    if not isinstance(body, dict):
        return _chat_error(
            "validation_error",
            "request body must be a JSON object",
            400,
            request_id,
        )

    graph_intent_id = body.get("graph_intent_id")
    actor = body.get("actor", "local")
    if not isinstance(graph_intent_id, str) or not re.fullmatch(
        r"[a-f0-9]{12}",
        graph_intent_id,
    ):
        return _chat_error(
            "validation_error",
            "graph_intent_id must be a 12-character lowercase hex string",
            400,
            request_id,
        )
    if not isinstance(actor, str) or not actor.strip():
        return _chat_error(
            "validation_error",
            "actor must be a non-empty string",
            400,
            request_id,
        )

    from forge_bridge.mcp import server as _mcp_server

    tools = await _mcp_server.mcp.list_tools()
    tools = await filter_tools_by_reachable_backends(tools)
    outcome = await run_apply_branch(
        graph_intent_id=graph_intent_id,
        session_factory=request.app.state.session_factory,
        tools=tools,
        mcp=_mcp_server.mcp,
        request_id=request_id,
        client_ip=client_ip,
        started=started,
        actor=actor.strip(),
    )
    if outcome.regime == "error":
        error = dict(outcome.error or {})
        return _chat_error(
            error.pop("code", "internal_error"),
            error.pop("message", "Ratify failed."),
            outcome.status_code,
            request_id,
            details=error or None,
        )
    if outcome.regime == "chain_aborted":
        body = dict(outcome.chain_body or {})
        body["stop_reason"] = "chain_aborted"
        body["graph_intent_id"] = outcome.graph_intent_id
        return JSONResponse(
            body,
            status_code=400,
            headers={"X-Request-ID": request_id},
        )
    return JSONResponse(
        {"apply_complete": _apply_complete_body(outcome, "json")},
        status_code=200,
        headers={"X-Request-ID": request_id},
    )


async def chat_handler(request: Request) -> Response:
    """POST /api/v1/chat — Phase 16 FB-D chat endpoint.

    See `.planning/phases/16-fb-d-chat-endpoint/16-CONTEXT.md` for the
    full decision register. Brief contract:

      Request body (D-02):
        {"messages": [{"role": "user|assistant|tool", "content": "...",
                       "tool_call_id": "..."}, ...],
         "max_iterations": 8, "max_seconds": 120.0,
         "tool_result_max_bytes": 8192}

      Response body (D-03), success:
        {"messages": [...full echoed history...],
         "stop_reason": "end_turn",
         "request_id": "<uuid>"}

      Response body, failure (D-17):
        {"error": {"code": "<machine_code>", "message": "<human>"}}
        + X-Request-ID response header

      Sensitivity (D-05): sensitive=True hardcoded — local Ollama path only.
      Rate limit (D-13/CHAT-01): IP-keyed token bucket; 11th request in 60s -> 429.
      Timeout (D-14/CHAT-02): outer asyncio.wait_for(125s) wraps FB-C's 120s loop cap.
      Sanitization (D-15): tool defs + tool results already wired by Phase 7 + FB-C;
        the handler does NOT re-sanitize. CHAT-03 verified by plan 16-06 integration test.
      LLMRouter (D-16): reuse request.app.state.console_read_api._llm_router.
      Logging (D-21): one structured log line per call.
    """
    request_id = str(uuid.uuid4())
    client_ip = request.client.host if request.client else "unknown"
    started = time.monotonic()

    # ---- CHAT-01 / D-13: rate-limit pre-gate ---------------------------------

    decision: RateLimitDecision = check_rate_limit(client_ip)
    if not decision.allowed:
        logger.info(
            "chat rate_limit request_id=%s client_ip=%s retry_after=%d",
            request_id, client_ip, decision.retry_after,
        )
        return _chat_error(
            "rate_limit_exceeded",
            f"Rate limit reached — wait {decision.retry_after}s before retrying.",
            429,
            request_id,
            extra_headers={"Retry-After": str(decision.retry_after)},
        )

    # ---- D-02 body validation ------------------------------------------------

    try:
        body = await request.json()
    except Exception:
        return _chat_error(
            "validation_error",
            "request body is not valid JSON",
            422,
            request_id,
        )
    if not isinstance(body, dict):
        return _chat_error(
            "validation_error",
            "request body must be a JSON object",
            422,
            request_id,
        )
    messages = body.get("messages")
    if not isinstance(messages, list) or not messages:
        return _chat_error(
            "validation_error",
            "messages: non-empty list[dict] is required",
            422,
            request_id,
        )
    for i, msg in enumerate(messages):
        if not isinstance(msg, dict):
            return _chat_error(
                "validation_error",
                f"messages[{i}] must be a dict",
                422,
                request_id,
            )
        role = msg.get("role")
        if role not in _CHAT_VALID_ROLES:
            return _chat_error(
                "unsupported_role",
                (
                    f"messages[{i}].role={role!r} not in "
                    f"{sorted(_CHAT_VALID_ROLES)}"
                ),
                422,
                request_id,
            )
        if not isinstance(msg.get("content"), str):
            return _chat_error(
                "validation_error",
                f"messages[{i}].content must be a string",
                422,
                request_id,
            )

    # Optional loop-cap kwargs (D-02).
    max_iterations = body.get("max_iterations", 8)
    if not isinstance(max_iterations, int) or max_iterations < 1 or max_iterations > 32:
        return _chat_error(
            "validation_error",
            "max_iterations must be an int in [1, 32]",
            422,
            request_id,
        )
    tool_result_max_bytes = body.get("tool_result_max_bytes")
    if tool_result_max_bytes is not None and (
        not isinstance(tool_result_max_bytes, int)
        or tool_result_max_bytes < 512
        or tool_result_max_bytes > 131072
    ):
        return _chat_error(
            "validation_error",
            "tool_result_max_bytes must be int in [512, 131072]",
            422,
            request_id,
        )

    # ---- D-16: LLMRouter access via ConsoleReadAPI ---------------------------

    router = getattr(request.app.state.console_read_api, "_llm_router", None)
    if router is None:
        logger.warning(
            "chat_handler: LLM router not configured request_id=%s", request_id,
        )
        return _chat_error(
            "internal_error",
            "LLM router not configured",
            500,
            request_id,
        )

    # ---- D-04: snapshot all registered MCP tools at request time -------------

    try:
        from forge_bridge.mcp import server as _mcp_server
        tools = await _mcp_server.mcp.list_tools()
    except Exception as exc:
        logger.warning(
            "chat_handler: mcp.list_tools failed: %s request_id=%s",
            type(exc).__name__, request_id, exc_info=True,
        )
        return _chat_error(
            "internal_error",
            "Tool registry not available",
            500,
            request_id,
        )
    if not tools:
        return _chat_error(
            "internal_error",
            "No tools registered",
            500,
            request_id,
        )

    # PR 4 §5 — deployment identity snapshot. Truth captured at the
    # moment of authority; subsequent rebinds of `tools` do not
    # erode this binding. Per framing §3: "The integration layer
    # passes truth. The integration layer never reconstructs truth."
    #
    # Placement note: lands here (post-empty-list-guard) rather
    # than immediately post-list_tools() because the binding is
    # only meaningful on the success path. Implicit invariant:
    # lines between list_tools() and this binding must remain
    # transformation-free; a future addition transforming `tools`
    # in that range would silently corrupt this snapshot's
    # semantic meaning.
    registered_tools = tools

    # ---- 16.1 D-01: backend-aware tool-list filter ---------------------------
    # Drop tools whose runtime backend is unreachable. `synth_*` and the
    # in-process `forge_*` tools (staged-ops, manifest_read, tools_read)
    # stay regardless. See forge_bridge/console/_tool_filter.py for the
    # per-tool routing classification; the prefix-only mapping in
    # 16.1-CONTEXT.md D-01 was incomplete (most `forge_*` are also
    # Flame-dependent).
    filtered_tools = await filter_tools_by_reachable_backends(tools)
    if not filtered_tools:
        return _chat_error(
            "service_unavailable",
            "No tool backends reachable — chat cannot run.",
            503,
            request_id,
        )

    # PR 4 §5 — runtime topology snapshot. Captures the post-
    # reachability set BEFORE the `tools = filtered_tools` rebind
    # has any chance to be misread (spec §4.1). Snapshot derives
    # from `filtered_tools` (the authoritative producer surface)
    # rather than the downstream alias — framing §3:
    # "The integration layer passes truth. The integration layer
    # never reconstructs truth."
    tools_post_reachability = filtered_tools

    tools = filtered_tools  # rebind so downstream uses filtered list

    # ---- PR14: message-based pre-filter to narrow tool selection ------------
    # Reduce LLM mis-selection + latency by trimming tools to those whose
    # name/keywords overlap the most recent user message. Falls back to the
    # full reachable-backend list when nothing matches (no capability loss).
    tools_available_count = len(tools)
    last_user_text = next(
        (
            m["content"] for m in reversed(messages)
            if isinstance(m, dict)
            and m.get("role") == "user"
            and isinstance(m.get("content"), str)
        ),
        "",
    )

    text = last_user_text.strip()
    lower = text.lower()

    if lower == "list macros":
        return JSONResponse(
            {
                "status": "success",
                "request_id": request_id,
                "macros": list_macros(),
            },
            status_code=200,
            headers={"X-Request-ID": request_id},
        )

    if lower == "delete macro" or lower.startswith("delete macro "):
        if lower == "delete macro":
            name = ""
        elif lower.startswith("delete macro "):
            name = text[len("delete macro "):].strip()
        if not name:
            return JSONResponse(
                {
                    "status": "success",
                    "request_id": request_id,
                    "deleted": None,
                },
                status_code=200,
                headers={"X-Request-ID": request_id},
            )
        delete_macro(name)
        return JSONResponse(
            {
                "status": "success",
                "request_id": request_id,
                "deleted": name,
            },
            status_code=200,
            headers={"X-Request-ID": request_id},
        )

    last_user_text = expand_macro(last_user_text)
    resolved_entities = resolve_query_entities(last_user_text)
    resolved_params = resolved_entity_params(resolved_entities)
    messages_for_llm = [dict(message) for message in messages]
    for index in range(len(messages_for_llm) - 1, -1, -1):
        message = messages_for_llm[index]
        if message.get("role") == "user" and isinstance(message.get("content"), str):
            message["content"] = last_user_text
            break
    messages_for_llm = enrich_messages_with_resolved_entities(
        messages_for_llm, resolved_entities,
    )

    # ---- PR30: deterministic multi-step tool chaining -----------------------
    # If the user message contains the ``->`` separator, parse it into a
    # sequence of standalone steps and execute each through the same
    # forced-execution pipeline (filter → resolve → call). The chain
    # path runs entirely WITHOUT the LLM and uses the PR31 unified envelope
    # (``status``, ``request_id``, ``chain``, ``error``) — including
    # CHAIN_TOO_LONG before execution and outcomes from ``_execute_chain``.
    # Single-step messages (``parse_chain`` returns 1 element) fall through
    # to the existing PR20/28/29 forced-execution path unchanged.
    from forge_bridge.console._chain_parse import parse_chain
    chain_steps = parse_chain(last_user_text)
    if len(chain_steps) > CHAIN_MAX_STEPS:
        logger.info(
            "chat chain_too_long request_id=%s client_ip=%s steps=%d",
            request_id, client_ip, len(chain_steps),
        )
        return JSONResponse(
            {
                "status": "error",
                "request_id": request_id,
                "chain": [],
                "error": {
                    "code": "CHAIN_TOO_LONG",
                    "message": (
                        f"Chain hit runaway guard at {CHAIN_MAX_STEPS} steps — "
                        f"chain length is normally unconstrained, this likely "
                        f"indicates a pathological loop. Check for runaway "
                        f"recursion or chain misexpansion."
                    ),
                    "step_index": None,
                    "original_error": None,
                },
            },
            status_code=400,
            headers={"X-Request-ID": request_id},
        )
    if len(chain_steps) > 1:
        return await _execute_chain(
            steps=chain_steps,
            tools=tools,
            request_id=request_id,
            client_ip=client_ip,
            started=started,
        )

    # PR 4 §4.1 — narrower-latency instrumentation. Measurement
    # happens regardless of divergence_capture_enabled() per spec:
    # latency belongs to the arbitration path, not the capture
    # path. Decoupling protects against a later "let's only
    # measure when capturing" simplification that would couple
    # arbitration timing to capture state.
    narrower_started = time.perf_counter()
    tools = filter_tools_by_message(tools, last_user_text)
    tools_filtered_count = len(tools)

    # PR 4 §5 — arbitration-input snapshot. Captures the
    # post-PR14 set BEFORE the PR21 deterministic-narrow pass
    # would collapse it. Used by collapse_occurred derivation
    # (multi-to-single transition diagnostic).
    tools_post_pr14 = tools

    # ---- PR21: deterministic disambiguation for multi-tool matches ----------
    # When PR14 returns >1 candidate, attempt a second narrowing pass: max
    # token-overlap (Rule 1) + pairwise domain priority (Rule 2). If the
    # rules collapse the set to exactly one tool, the PR20 short-circuit
    # below picks it up and force-executes — same path, same telemetry.
    # If still ambiguous, the LLM decides on the (unchanged) survivor set.
    # See deterministic_narrow() in _tool_filter.py for the rule contract.
    #
    # State-consistency contract — REBIND on ANY reduction (not just to 1):
    # if narrowing shrinks the candidate set at all, both `tools` and
    # `tools_filtered_count` must reflect the new set. Previously this
    # rebind only fired at narrowed==1, which let multi-tool reductions
    # silently drop on the floor: the LLM still saw the unnarrowed list
    # while the count diverged from the actual candidates. The invariant
    # below depends on a single source of truth — `tools_filtered_count`
    # equals `len(tools)` from this point onward.
    if tools_filtered_count > 1:
        narrowed = deterministic_narrow(tools, last_user_text)
        if len(narrowed) < len(tools):
            tools = narrowed
            tools_filtered_count = len(narrowed)
    narrower_latency_ms = (time.perf_counter() - narrower_started) * 1000.0

    # ── Capture is emitted after arbitration decisions are finalized
    #    and must not structurally participate in the arbitration
    #    pipeline. (PR 3 spec §0; PR 4 framing §0.)
    #
    #    PR 4 is the controlled introduction of observational
    #    side-effects into live arbitration surfaces. The risk
    #    category has shifted from persistence-substrate risk to
    #    participation-creep risk. (PR 4 framing §0.)
    #
    #    The call site is the source of the three explicit inputs.
    #    The integration layer passes truth. The integration layer
    #    never reconstructs truth. The builder does not discover
    #    runtime state. (PR 4 framing §3.)
    #
    #    Capture emission occurs only after arbitration state is
    #    finalized for the current execution path. Capture records
    #    completed arbitration observations, not provisional
    #    intermediate state. (PR 4 spec §0.)

    if divergence_capture_enabled():
        emit_divergence_capture(
            prompt=last_user_text,
            registered_tools=registered_tools,
            candidate_set_post_reachability=tools_post_reachability,
            candidate_set_post_pr14=tools_post_pr14,
            narrower_decision=tools,
            pr20_condition_met=(
                tools_filtered_count == 1
                and tools_filtered_count < tools_available_count
            ),
            collapse_occurred=(
                tools_filtered_count == 1
                and len(tools_post_pr14) > 1
            ),
            ambiguity_state=_ambiguity_state_for(tools_filtered_count),
            narrower_latency_ms=narrower_latency_ms,
            source="runtime",
        )

    # ---- PR15: deterministic-tool-call enforcement state --------------------
    # PR20 still reports whether the deterministic forced-tool rule applies.
    # The compiled JSON path below uses a compile-specific prompt instead of
    # PR15's executor prompt.
    tool_enforced_flag = is_tool_enforced(tools_filtered_count)

    # ---- PR20: deterministic forced execution when filter narrowed to 1 -----
    # If the message-based filter actively narrowed a multi-tool registry down
    # to exactly one survivor, the LLM has nothing to decide — call the tool
    # directly. Skip when `available == filtered == 1` (degenerate / fallback)
    # to avoid invoking a tool the user never asked for. See module-level
    # PR20 comment block above _execute_forced_tool for the full contract.
    #
    # PR28: extract any user-supplied parameters (today: ``project_id=<uuid>``
    # or a single bare UUID) from the last user message and forward them as
    # caller params. Phase 24.11 layers deterministic query-time entity
    # resolution into the same caller-param map before the FastMCP boundary;
    # no LLM, no fuzzy matching. PR26's precedence chain (explicit > memory >
    # resolver) ensures an explicit value collapses ambiguity before the PR27
    # disambiguation envelope would fire.
    if tools_filtered_count == 1 and tools_filtered_count < tools_available_count:
        from forge_bridge.console._param_extract import extract_explicit_params

        user_params = {
            **resolved_params,
            **extract_explicit_params(last_user_text),
        }
        return await _execute_forced_tool(
            tool=tools[0],
            messages=messages,
            request_id=request_id,
            started=started,
            client_ip=client_ip,
            tools_available_count=tools_available_count,
            tools_filtered_count=tools_filtered_count,
            tool_enforced_flag=tool_enforced_flag,
            user_params=user_params,
        )

    # ---- Defensive: empty-tools guard before LLM dispatch -------------------
    # `filter_tools_by_message` falls back to the full list when nothing
    # matches, and `deterministic_narrow` only ever returns a non-empty
    # subset, so reaching this point with `tools == []` is an unexpected
    # state — likely a bug in a future filter edit. Rather than dispatching
    # a no-op LLM call that would loop or hang, return a safe 503 envelope
    # and log loudly so the operator can trace it. Mirrors the upstream
    # reachable-backends empty-list guard (Phase 16.1 D-01).
    if not tools:
        logger.warning(
            "chat empty_tool_set_after_filters request_id=%s "
            "client_ip=%s tools_available=%d — investigate filter pipeline",
            request_id, client_ip, tools_available_count,
        )
        return _chat_error(
            "service_unavailable",
            "No tools available for this request — chat cannot proceed.",
            503,
            request_id,
        )

    # ---- D-14 / CHAT-02: outer 125s wraps FB-C's 120s inner cap --------------
    # D-14a translation matrix applied below — every cap-fire becomes 504, every
    # structural error becomes 500. Sensitivity is hardcoded D-05 (sensitive=True).
    #
    # Safe-envelope contract: every code path that exits the try-block below
    # MUST go through `_chat_error()` (status 4xx/5xx, NEVER leaks the
    # exception string into the response body — only the request_id + a
    # human message). The catch-all `except Exception as exc:` at the bottom
    # of the chain is the load-bearing guarantee — any router/serialization/
    # transport-level error becomes a deterministic 500 envelope rather than
    # a Starlette default 500 with a traceback.

    tool_call_count_in = sum(1 for m in messages_for_llm if m.get("role") == "tool")

    # Phase 24.3 commit 4 — content-negotiated SSE response. When the client
    # sends `Accept: text/event-stream`, switch the response shape to SSE
    # (history-grows per framing §6.5). Default Accept (or any other content
    # type) keeps the existing JSONResponse path below unchanged. Pre-flight
    # validation (D-02), rate limit (D-13), tool-list assembly, and short-
    # circuit paths (macros, chains, PR20 forced execution) all return JSON
    # regardless — only the LLM-loop path branches on the Accept header.
    # Per framing §4.0: streaming exposes forward progress, NOT redefines
    # conversational success. The JSON and SSE paths emit semantically
    # equivalent terminal state (final_text + stop_reason + tool_trace).
    wants_sse = "text/event-stream" in request.headers.get("accept", "").lower()
    if wants_sse:
        return await _chat_sse_response(
            router=router,
            messages=messages_for_llm,
            tools=tools,
            mcp=_mcp_server.mcp,
            max_iterations=max_iterations,
            tool_result_max_bytes=tool_result_max_bytes,
            request_id=request_id,
            client_ip=client_ip,
            started=started,
            tool_call_count_in=tool_call_count_in,
            tools_available_count=tools_available_count,
            tools_filtered_count=tools_filtered_count,
            session_factory=request.app.state.session_factory,
        )

    compile_prompt = next(
        (
            m["content"] for m in reversed(messages_for_llm)
            if isinstance(m, dict)
            and m.get("role") == "user"
            and isinstance(m.get("content"), str)
        ),
        "",
    )
    apply_match = _APPLY_GRAMMAR.match(compile_prompt.strip())
    if apply_match:
        outcome = await run_apply_branch(
            graph_intent_id=apply_match.group(1),
            session_factory=request.app.state.session_factory,
            tools=tools,
            mcp=_mcp_server.mcp,
            request_id=request_id,
            client_ip=client_ip,
            started=started,
        )
        if outcome.regime == "error":
            error = dict(outcome.error or {})
            return _chat_error(
                error.pop("code", "internal_error"),
                error.pop("message", "Chat error — check console for details."),
                outcome.status_code,
                request_id,
                details=error or None,
            )
        if outcome.regime == "chain_aborted":
            body = dict(outcome.chain_body or {})
            body["stop_reason"] = "chain_aborted"
            body["graph_intent_id"] = outcome.graph_intent_id
            return JSONResponse(
                body,
                status_code=400,
                headers={"X-Request-ID": request_id},
            )
        return JSONResponse(
            {"apply_complete": _apply_complete_body(outcome, "json")},
            status_code=200,
            headers={"X-Request-ID": request_id},
        )
    compile_system = build_compile_system_prompt(tools)

    try:
        outcome = await asyncio.wait_for(
            run_compile_branch(
                router=router,
                user_prompt=compile_prompt,
                tools=tools,
                mcp=_mcp_server.mcp,
                request_id=request_id,
                client_ip=client_ip,
                started=started,
                compile_system=compile_system,
                session_factory=request.app.state.session_factory,
            ),
            timeout=125.0,
        )
    except asyncio.TimeoutError:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        logger.info(
            "chat timeout request_id=%s client_ip=%s message_count_in=%d "
            "tools_offered_count=%d wall_clock_ms=%d stop_reason=outer_wait_for_timeout",
            request_id, client_ip, len(messages), len(tools), elapsed_ms,
        )
        return _chat_error(
            "request_timeout",
            "Response timed out — try a simpler question or fewer tools.",
            504,
            request_id,
        )
    except LLMLoopBudgetExceeded:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        logger.info(
            "chat loop_budget request_id=%s client_ip=%s tools_offered_count=%d "
            "wall_clock_ms=%d stop_reason=loop_budget_exceeded",
            request_id, client_ip, len(tools), elapsed_ms,
        )
        return _chat_error(
            "request_timeout",
            "Response timed out — try a simpler question or fewer tools.",
            504,
            request_id,
        )
    except RecursiveToolLoopError:
        logger.warning(
            "chat recursive_loop request_id=%s — should not reach handler "
            "(synthesizer guard). Investigate.", request_id,
        )
        return _chat_error(
            "internal_error",
            "Chat error — check console for details.",
            500,
            request_id,
        )
    except LLMToolError as exc:
        logger.warning(
            "chat tool_error request_id=%s exc_type=%s",
            request_id, type(exc).__name__,
        )
        return _chat_error(
            "internal_error",
            "Chat error — check console for details.",
            500,
            request_id,
        )
    except Exception as exc:
        logger.warning(
            "chat_handler failed request_id=%s exc_type=%s",
            request_id, type(exc).__name__, exc_info=True,
        )
        return _chat_error(
            "internal_error",
            "Chat error — check console for details.",
            500,
            request_id,
        )

    elapsed_ms = int((time.monotonic() - started) * 1000)
    if outcome.regime == "compile_error":
        code, message, status, details = _compile_error_payload(outcome.compile_error)
        logger.info(
            "chat compile_error request_id=%s client_ip=%s "
            "tools_offered_count=%d wall_clock_ms=%d chat_regime=compile_error",
            request_id, client_ip, len(tools), elapsed_ms,
        )
        return _chat_error(
            code,
            message,
            status,
            request_id,
            details=details,
        )

    if outcome.regime == "chain_aborted":
        body = dict(outcome.chain_body or {})
        body["stop_reason"] = "chain_aborted"
        logger.info(
            "chat chain_aborted request_id=%s client_ip=%s "
            "steps=%d tools_offered_count=%d wall_clock_ms=%d "
            "chat_regime=compiled_non_mutating",
            request_id, client_ip, len(outcome.steps), len(tools), elapsed_ms,
        )
        return JSONResponse(
            body,
            status_code=400,
            headers={"X-Request-ID": request_id},
        )

    if outcome.regime == "compiled_mutating_preview":
        logger.info(
            "chat preview_emitted request_id=%s client_ip=%s "
            "steps=%d tools_offered_count=%d wall_clock_ms=%d "
            "chat_regime=compiled_mutating_preview",
            request_id, client_ip, len(outcome.steps), len(tools), elapsed_ms,
        )
        return JSONResponse(
            {
                "preview": outcome.preview,
                "chain": [],
                "stop_reason": "preview_emitted",
                "request_id": request_id,
                "tools_available": tools_available_count,
                "tools_filtered": tools_filtered_count,
                "tool_enforced": False,
                "tool_forced": False,
            },
            status_code=200,
            headers={"X-Request-ID": request_id},
        )

    chain_body = outcome.chain_body or {}
    chain = chain_body.get("chain", [])
    answer, answer_ms = await _synthesize_answer(router, messages, chain)
    if answer:
        emit_comprehension_capture(
            question=_last_user_question(messages),
            chain=chain,
            answer=answer,
            wall_clock_ms=answer_ms,
            model=getattr(router, "local_model", "unknown"),
        )
    logger.info(
        "chat ok request_id=%s client_ip=%s message_count_in=%d "
        "steps=%d tools_offered_count=%d wall_clock_ms=%d "
        "stop_reason=chain_complete chat_regime=compiled_non_mutating",
        request_id, client_ip, len(messages), len(outcome.steps),
        len(tools), elapsed_ms,
    )
    return JSONResponse(
        {
            "chain": chain,
            "messages": [{"role": "assistant", "content": answer}] if answer else [],
            "stop_reason": "chain_complete",
            "request_id": request_id,
            "tools_available": tools_available_count,
            "tools_filtered": tools_filtered_count,
            "tool_enforced": False,
            "tool_forced": False,
            "preview": None,
        },
        status_code=200,
        headers={"X-Request-ID": request_id},
    )
