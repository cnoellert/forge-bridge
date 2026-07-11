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
from typing import Any

from forge_bridge.orchestration.discovery import make_db_event_appender
from forge_bridge.orchestration.dispatcher import (
    DispatchResult,
    InvocationEnvelope,
    _advisory_grant_check,
    _check_model_not_revoked,
    dispatch_envelope,
)
from forge_bridge.orchestration.drivers import GenerationDriverRegistry
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
    """Runtime-bound entry onto the plan-free ``dispatch_envelope`` core.

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
    """
    session_factory = get_async_session_factory()
    event_appender = make_db_event_appender(session_factory)
    driver_registry = get_generation_driver_registry()

    # ── SEAM (#141 idempotency pre-submit check) ───────────────────────────
    # A dedup check keyed on ``idempotency_key`` belongs HERE, above the single
    # submit chokepoint, so a retried forge_generate_* call collapses to the
    # first artifact instead of double-submitting. ``idempotency_key`` is
    # accepted in the signature now; the dedup logic is a SEPARATE slice and is
    # intentionally NOT enforced yet.
    #
    # ── GenerationGrant authority guard (#146) — direct-door advisory ──────
    # Early, NON-consuming fail-fast for the direct (plan-free) caller: peek the
    # resolved grant and refuse before doing envelope work if it is not a
    # ratified, unspent grant. This is ADVISORY only — the single atomic consume
    # stays at the mandatory chokepoint inside ``dispatch_envelope`` (calling the
    # consuming helper here would double-spend). Assent/ratify stays in the tool
    # layer ABOVE this entry.
    grant_ok, refusal_code = await _advisory_grant_check(
        session_factory, grant_id=grant_id, run_id=run_id,
    )
    if not grant_ok:
        return DispatchResult(status="refused", refusal_code=refusal_code)

    # ── Fitted-model revocation gate (#160) — direct-door advisory ─────────
    # The envelope carries fitted_model_asset_id here (it is an envelope field),
    # so mirror the model pre-check: fail-fast before envelope work if the named
    # fitted-model asset is missing or revoked. The authoritative gate still
    # runs at the mandatory chokepoint inside dispatch_envelope; this is the same
    # advisory-early-refuse shape as the grant check above (no event emitted —
    # the chokepoint owns the audit event).
    model_ok, model_refusal_code = await _check_model_not_revoked(
        session_factory, fitted_model_asset_id=envelope.fitted_model_asset_id,
    )
    if not model_ok:
        return DispatchResult(status="refused", refusal_code=model_refusal_code)

    return await dispatch_envelope(
        envelope,
        provenance=provenance,
        driver_registry=driver_registry,
        session_factory=session_factory,
        event_appender=event_appender,
        run_id=run_id,
        grant_id=grant_id,
    )
