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
import time
import uuid
from dataclasses import asdict
from datetime import datetime
from typing import Any, Optional

from starlette.requests import Request
from starlette.responses import JSONResponse

from forge_bridge.console._rate_limit import (
    RateLimitDecision,
    check_rate_limit,
)
from forge_bridge.console._tool_enforcement import (
    build_enforcement_system_prompt,
    is_response_text_malformed_tool,
    is_tool_enforced,
)
from forge_bridge.console._tool_filter import (
    deterministic_narrow,
    filter_tools_by_message,
    filter_tools_by_reachable_backends,
)
from forge_bridge.llm.router import (
    LLMLoopBudgetExceeded,
    LLMToolError,
    RecursiveToolLoopError,
)
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


def _serialize_forced_tool_result(raw: Any) -> str:
    """Serialize a FastMCP `call_tool` return into a string suitable for the
    `tool` message body.

    FastMCP's `call_tool(..., convert_result=True)` actually returns a
    2-tuple ``(content_blocks, structured_dict)`` — the type hint advertises
    ``Sequence[ContentBlock] | dict``, but observed runtime is the tuple
    form (the convert path produces both). We detect the tuple, prefer the
    structured `result` payload when present (already a JSON string from
    the tool's ``_ok``/``_err`` helpers), and fall back to extracting text
    from the content blocks. Plain str / dict / list returns are handled
    too for forward compatibility with future FastMCP shape changes.
    """
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        # FastMCP convert path may also pass a bare dict — pull "result"
        # if present (the tool's stringified payload), else dump the dict.
        if "result" in raw and isinstance(raw["result"], str):
            return raw["result"]
        return json.dumps(raw, default=str)
    if isinstance(raw, tuple) and len(raw) == 2:
        blocks, structured = raw
        # Structured dict path — `_ok`/`_err` already produced a JSON string
        # which FastMCP wraps as ``{"result": "<json>"}``.
        if isinstance(structured, dict) and isinstance(
            structured.get("result"), str
        ):
            return structured["result"]
        # Otherwise fall through to block-level extraction.
        raw = blocks
    if isinstance(raw, (list, tuple)):
        # ContentBlock sequence — pull out text payloads, fall back to repr.
        parts: list[str] = []
        for block in raw:
            text = getattr(block, "text", None)
            if isinstance(text, str):
                parts.append(text)
                continue
            dump = getattr(block, "model_dump_json", None)
            if callable(dump):
                try:
                    parts.append(dump())
                    continue
                except Exception:  # noqa: BLE001 — best-effort serialization
                    pass
            parts.append(repr(block))
        return "\n".join(parts) if parts else ""
    return repr(raw)


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
) -> JSONResponse:
    """PR20 short-circuit: invoke the sole filtered tool and shape the chat
    reply. The LLM router is not called on this path."""
    from forge_bridge.console._tool_chain import resolve_required_params
    from forge_bridge.mcp import server as _mcp_server

    tool_call_id = f"forced_{uuid.uuid4().hex[:12]}"
    tool_name = tool.name

    # PR25: deterministic required-parameter resolution. For tools listed
    # in the chain registry, this issues a single upstream tool call (e.g.
    # `forge_list_projects`) and merges the resolved value into params
    # when — and only when — the system state is unambiguous. Returns
    # `params` unchanged otherwise; the downstream PR22 graceful contract
    # then surfaces a structured `MISSING_*` error.
    params: dict = await resolve_required_params(
        tool_name, {}, _mcp_server.mcp,
    )

    try:
        raw = await _mcp_server.mcp.call_tool(tool_name, params)
        tool_content = _serialize_forced_tool_result(raw)
        tool_ok = True
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
            "messages": out_messages,
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


def _chat_error(
    code: str,
    message: str,
    status: int,
    request_id: str,
    extra_headers: Optional[dict] = None,
) -> JSONResponse:
    """Chat-endpoint error helper (D-17 NESTED envelope + X-Request-ID always).

    The existing `_error()` helper at lines 58-60 produces the same body shape
    but does not accept a headers kwarg; the chat endpoint needs every reply
    to carry X-Request-ID per D-17 / D-21, so this thin wrapper is the single
    error-path emitter throughout chat_handler.
    """
    headers = {"X-Request-ID": request_id}
    if extra_headers:
        headers.update(extra_headers)
    return JSONResponse(
        {"error": {"code": code, "message": message}},
        status_code=status,
        headers=headers,
    )


async def chat_handler(request: Request) -> JSONResponse:
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
    tools = filter_tools_by_message(tools, last_user_text)
    tools_filtered_count = len(tools)

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

    # ---- PR15: deterministic-tool-call enforcement --------------------------
    # Stack the existing pipeline system prompt with the PR15 rule block so
    # the model treats tools as the primary response modality. When exactly
    # one tool survives the filter, append the HARD-TOOL instruction.
    enforced_system = build_enforcement_system_prompt(
        router.system_prompt, tools_filtered_count,
    )
    tool_enforced_flag = is_tool_enforced(tools_filtered_count)

    # ---- PR20: deterministic forced execution when filter narrowed to 1 -----
    # If the message-based filter actively narrowed a multi-tool registry down
    # to exactly one survivor, the LLM has nothing to decide — call the tool
    # directly. Skip when `available == filtered == 1` (degenerate / fallback)
    # to avoid invoking a tool the user never asked for. See module-level
    # PR20 comment block above _execute_forced_tool for the full contract.
    if tools_filtered_count == 1 and tools_filtered_count < tools_available_count:
        return await _execute_forced_tool(
            tool=tools[0],
            messages=messages,
            request_id=request_id,
            started=started,
            client_ip=client_ip,
            tools_available_count=tools_available_count,
            tools_filtered_count=tools_filtered_count,
            tool_enforced_flag=tool_enforced_flag,
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

    tool_call_count_in = sum(1 for m in messages if m.get("role") == "tool")

    try:
        result_text = await asyncio.wait_for(
            router.complete_with_tools(
                messages=messages,            # D-02a (plan 16-01)
                tools=tools,
                sensitive=True,               # D-05 hardcoded
                system=enforced_system,       # PR15 deterministic enforcement
                max_iterations=max_iterations,
                max_seconds=120.0,            # FB-C inner cap
                tool_result_max_bytes=tool_result_max_bytes,
            ),
            timeout=125.0,                    # CHAT-02 outer cap
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

    # ---- PR15: output validation -------------------------------------------
    # The model sometimes emits a hallucinated tool-call as free text instead
    # of actually invoking a tool (qwen2.5-coder leaks chat-template tokens
    # like ``<|im_start|>{"name": ..., "arguments": ...}``). Detect that
    # pattern and return 500 → wrapper classifies as invalid_response so the
    # operator sees a deterministic failure instead of a nonsense reply.
    if is_response_text_malformed_tool(result_text):
        logger.warning(
            "chat malformed_tool_text request_id=%s tools_offered_count=%d",
            request_id, len(tools),
        )
        return _chat_error(
            "internal_error",
            "Model produced a hallucinated tool-call as text — see logs.",
            500,
            request_id,
        )

    # ---- Success path -------------------------------------------------------

    elapsed_ms = int((time.monotonic() - started) * 1000)
    out_messages = list(messages) + [{"role": "assistant", "content": result_text}]
    logger.info(
        "chat ok request_id=%s client_ip=%s message_count_in=%d "
        "message_count_out=%d tool_call_count=%d tools_offered_count=%d "
        "wall_clock_ms=%d stop_reason=end_turn",
        request_id, client_ip, len(messages), len(out_messages),
        tool_call_count_in, len(tools), elapsed_ms,
    )
    return JSONResponse(
        {
            "messages": out_messages,
            "stop_reason": "end_turn",
            "request_id": request_id,
            # PR14 — narrow-tool-selection telemetry surfaced for the wrapper
            # trace summary (forge_bridge/llm/call_wrapper.py).
            "tools_available": tools_available_count,
            "tools_filtered": tools_filtered_count,
            # PR15 — true when the filtered set was small enough that we
            # forced the deterministic-call rules (≤3 tools).
            "tool_enforced": tool_enforced_flag,
        },
        status_code=200,
        headers={"X-Request-ID": request_id},
    )
