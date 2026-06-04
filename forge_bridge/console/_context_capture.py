"""S3.2 — ``POST /api/v1/context-capture``: storage-only capture endpoint.

ROUTE-SEPARATION INVARIANT (room ruling, Fork 1 / Option B). This module imports
ONLY ``forge_bridge.context_pressure`` (the canonical assembler/builder/append) +
starlette + the compile-free ``_rate_limit``. It MUST NOT import ``compile_intent``
/ ``run_compile_branch`` / ``_chat_compile`` / ``handlers`` (which pulls the compile
path) / any compile-path entrypoint. Resolver-blindness is enforced structurally
here and verified in ``tests/console/test_context_capture_route_separation.py``:
the compile route never receives world_state; the capture route never compiles.

The Console posts the raw Flame world_state snapshot + the compiled graph + the
observed terminal outcome; this endpoint runs the CANONICAL context_pressure
functions (single source of truth — the Option-B benefit) and appends to the
capture corpus. It never compiles, never mutates Flame/pipeline state.
"""
from __future__ import annotations

import uuid

from starlette.requests import Request
from starlette.responses import JSONResponse

from forge_bridge.console._rate_limit import check_rate_limit
from forge_bridge.context_pressure import (
    SchemaValidationError,
    append_record,
    assemble_world_state,
    build_record,
)


def _err(code: str, message: str, status: int, request_id: str) -> JSONResponse:
    return JSONResponse(
        {"error": {"code": code, "message": message}, "request_id": request_id},
        status_code=status,
    )


async def context_capture_handler(request: Request) -> JSONResponse:
    """Validate + assemble + build + append a ContextPressureRecord. Storage-only."""
    request_id = str(uuid.uuid4())
    client_ip = request.client.host if request.client else "unknown"

    decision = check_rate_limit(client_ip)
    if not decision.allowed:
        return _err(
            "rate_limit_exceeded",
            f"Rate limit reached — wait {decision.retry_after}s before retrying.",
            429, request_id,
        )

    try:
        body = await request.json()
    except Exception:
        return _err("validation_error", "request body is not valid JSON", 400, request_id)
    if not isinstance(body, dict):
        return _err("validation_error", "request body must be a JSON object", 400, request_id)

    prompt = body.get("prompt")
    compiled_graph = body.get("compiled_graph")
    outcome = body.get("outcome")
    world_state_raw = body.get("world_state_raw")
    provenance = body.get("provenance")
    captured_at = body.get("captured_at")
    ratified_graph = body.get("ratified_graph")  # optional; defaults to None

    if not isinstance(captured_at, str) or not captured_at:
        return _err("validation_error", "captured_at (request-time) must be a non-empty string", 400, request_id)
    if not isinstance(prompt, str):
        return _err("validation_error", "prompt must be a string", 400, request_id)
    if not isinstance(compiled_graph, list) or not all(isinstance(s, str) for s in compiled_graph):
        return _err("validation_error", "compiled_graph must be a list of strings", 400, request_id)
    if not isinstance(world_state_raw, dict):
        return _err("validation_error", "world_state_raw must be an object", 400, request_id)
    if not isinstance(provenance, dict) or not isinstance(provenance.get("context_source"), str):
        return _err("validation_error", "provenance.context_source is required", 400, request_id)
    if ratified_graph is not None and (
        not isinstance(ratified_graph, list) or not all(isinstance(s, str) for s in ratified_graph)
    ):
        return _err("validation_error", "ratified_graph must be a list of strings or null", 400, request_id)

    try:
        world_state = assemble_world_state(world_state_raw, source=provenance["context_source"])
        record = build_record(
            captured_at=captured_at,
            provenance=provenance,
            prompt=prompt,
            observed_translation={"compiled_graph": compiled_graph, "ratified_graph": ratified_graph},
            outcome=outcome,
            world_state=world_state,
        )
        path = append_record(record)
    except SchemaValidationError as exc:
        return _err("validation_error", str(exc), 400, request_id)

    return JSONResponse({"data": {"appended": True, "path": str(path)}, "request_id": request_id})
