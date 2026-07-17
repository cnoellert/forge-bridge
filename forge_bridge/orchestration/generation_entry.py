"""Runtime-bound generation dispatch entry (bridge issue #139).

Neutral, importable-without-``mcp.server`` module that lets an in-process
sibling handler reach the plan-free ``dispatch_envelope`` core.

A Pass-B sibling registers its ``forge_generate_*`` handler via
``register_with(mcp)`` — which passes ONLY ``mcp``. That handler therefore
cannot receive the three runtime deps (``session_factory``, ``event_appender``,
``driver_registry``) at registration time. The answer is this module-level
``dispatch_generation``: it resolves the three deps at INVOCATION time (always
post-bootstrap) and forwards to ``dispatch_envelope``. ``register_with`` stays
mcp-only; the sibling contract is unchanged.

Import direction is strictly one-way: ``mcp/server.py`` imports THIS module at
bootstrap to publish the driver registry (``set_generation_driver_registry``).
This module must NEVER import ``mcp.server`` — a neutral process-level holder is
used precisely so a sibling can import the entry without pulling in the MCP
server (which would risk a bootstrap-time circular import).
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from forge_bridge.orchestration.discovery import make_db_event_appender
from forge_bridge.orchestration.dispatcher import (
    DispatchResult,
    InvocationEnvelope,
    _advisory_grant_check,
    _check_model_not_revoked,
    _existing_idempotency_result,
    _generation_invocation_fingerprint,
    _normalize_generation_idempotency_key,
    dispatch_envelope,
)
from forge_bridge.orchestration.drivers import (
    GenerationDriverRegistry,
    backend_id_from_identity_triple,
)
from forge_bridge.store.orch_generation_artifact_repo import GenerationArtifactRepo
from forge_bridge.store.session import get_async_session_factory

# ─────────────────────────────────────────────────────────────
# Process-level driver-registry holder
# ─────────────────────────────────────────────────────────────
# The registry is created inside ``bootstrap_daemon`` and has no public getter
# there. It is published HERE (a neutral module) rather than on ``mcp.server``
# so a sibling can resolve it at invocation time without importing the MCP
# server. Last bootstrap wins (overwrite is intentional — a re-bootstrap in the
# same process re-points the holder at the fresh registry).
_generation_driver_registry: GenerationDriverRegistry | None = None


def set_generation_driver_registry(registry: GenerationDriverRegistry) -> None:
    """Publish the daemon's generation driver registry for invocation-time
    resolution.

    Called once from ``bootstrap_daemon`` immediately after the registry is
    created (see ``mcp/server.py``).
    """
    global _generation_driver_registry
    _generation_driver_registry = registry


def get_generation_driver_registry() -> GenerationDriverRegistry:
    """Return the process generation driver registry.

    Raises ``RuntimeError`` when unset — the daemon has not bootstrapped, so
    generation dispatch is unavailable. This is the pre-bootstrap safety guard:
    a direct ``forge_generate_*`` handler must never submit against a registry
    that was never wired.
    """
    if _generation_driver_registry is None:
        raise RuntimeError(
            "generation driver registry not set — daemon not bootstrapped, "
            "generation dispatch unavailable. bootstrap_daemon publishes the "
            "registry via set_generation_driver_registry()."
        )
    return _generation_driver_registry


async def dispatch_generation(
    envelope: InvocationEnvelope,
    *,
    provenance: dict[str, Any],
    idempotency_key: str | None = None,
    run_id: uuid.UUID | None = None,
    grant_id: str | None = None,
) -> DispatchResult:
    """Runtime-bound direct door onto the plan-free dispatch core.

    This is the door a Pass-B sibling's in-process ``forge_generate_*`` handler
    calls. Because that handler is registered via ``register_with(mcp)`` (which
    passes only ``mcp``), it cannot receive the three runtime deps at
    registration time; this function resolves them at invocation time (always
    post-bootstrap) and forwards to ``dispatch_envelope``:

      - ``session_factory`` — the public process singleton
        (:func:`get_async_session_factory`).
      - ``event_appender``  — DERIVED per call from that session factory (it is
        not a singleton).
      - ``driver_registry`` — the process holder published at bootstrap via
        :func:`set_generation_driver_registry`.

    Generation has two dispatch doors with distinct authority semantics:

      - This direct door performs advisory grant and fitted-model checks. It
        first returns any matching idempotent artifact, then fails fast without
        spending the grant and emits
        ``dispatch_advisory_refused`` when either check refuses.
      - :func:`dispatch_envelope` is the authoritative chokepoint for both this
        direct door and the planner door. It atomically consumes the grant,
        rechecks fitted-model authority, emits its own authoritative refusal
        events, and is the only path to ``driver.submit``.
    """
    session_factory = get_async_session_factory()
    event_appender = make_db_event_appender(session_factory)
    driver_registry = get_generation_driver_registry()

    # ── Idempotency preflight (#141) ────────────────────────────────────────
    # A sequential retry may arrive with an already-consumed grant, so look up
    # the durable artifact before the direct door's advisory grant check. The
    # authoritative locked recheck still happens in dispatch_envelope; this
    # preflight is an optimization and cannot authorize a new submit.
    idempotency_key = _normalize_generation_idempotency_key(idempotency_key)
    if idempotency_key is not None:
        invocation_fingerprint = _generation_invocation_fingerprint(envelope)
        async with session_factory() as session:
            existing = await GenerationArtifactRepo(
                session
            ).get_by_idempotency_key(idempotency_key)
        if existing is not None:
            return await _existing_idempotency_result(
                existing,
                idempotency_key=idempotency_key,
                invocation_fingerprint=invocation_fingerprint,
                operator_id=envelope.operator_id,
                backend_id=backend_id_from_identity_triple(
                    dict(envelope.backend_identity_triple)
                ),
                event_appender=event_appender,
                run_id=run_id,
            )

    # ── GenerationGrant authority guard (#146) — direct-door advisory ──────
    # Early, NON-consuming fail-fast for the direct (plan-free) caller: peek the
    # resolved grant and refuse before doing envelope work if it is not a
    # ratified, unspent grant. This is ADVISORY only — the single atomic consume
    # stays at the mandatory chokepoint inside ``dispatch_envelope`` (calling the
    # consuming helper here would double-spend). Assent/ratify stays in the tool
    # layer ABOVE this entry.
    grant_ok, refusal_code = await _advisory_grant_check(
        session_factory,
        grant_id=grant_id,
        run_id=run_id,
        operator_id=envelope.operator_id,
        backend_identity_triple=dict(envelope.backend_identity_triple),
    )
    if not grant_ok:
        await _emit_advisory_refusal(
            event_appender,
            envelope=envelope,
            refusal_code=refusal_code,
            advisory_check="generation_grant",
            run_id=run_id,
        )
        return DispatchResult(status="refused", refusal_code=refusal_code)

    # ── Fitted-model lifecycle gate (#160) — direct-door advisory ──────────
    # The envelope carries fitted_model_asset_id here (it is an envelope field),
    # so mirror the model pre-check: fail-fast before envelope work if the named
    # fitted-model asset is unavailable (missing, revoked, marked, collected, or
    # malformed). The authoritative gate still runs at the mandatory chokepoint
    # inside dispatch_envelope; this is the same advisory-early-refuse shape as
    # the grant check above. Its audit event is deliberately distinct from the
    # chokepoint's authoritative refusal event.
    model_ok, model_refusal_code = await _check_model_not_revoked(
        session_factory, fitted_model_asset_id=envelope.fitted_model_asset_id,
    )
    if not model_ok:
        await _emit_advisory_refusal(
            event_appender,
            envelope=envelope,
            refusal_code=model_refusal_code,
            advisory_check="fitted_model",
            run_id=run_id,
        )
        return DispatchResult(status="refused", refusal_code=model_refusal_code)

    return await dispatch_envelope(
        envelope,
        provenance=provenance,
        driver_registry=driver_registry,
        session_factory=session_factory,
        event_appender=event_appender,
        run_id=run_id,
        grant_id=grant_id,
        idempotency_key=idempotency_key,
    )


async def _emit_advisory_refusal(
    event_appender: Callable[[str, dict], Awaitable[None]],
    *,
    envelope: InvocationEnvelope,
    refusal_code: str | None,
    advisory_check: str,
    run_id: uuid.UUID | None,
) -> None:
    """Record a direct-door refusal without impersonating the chokepoint."""
    await event_appender(
        "dispatch_advisory_refused",
        {
            "door": "dispatch_generation",
            "advisory_check": advisory_check,
            "operator_id": envelope.operator_id,
            "refusal_code": refusal_code,
            "run_id": str(run_id) if run_id is not None else None,
        },
    )
