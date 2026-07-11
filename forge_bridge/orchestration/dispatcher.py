"""Generation dispatch spine (Phase 7 vertical 1).

This module proves the bridge-owned lifecycle from a selected generation step
to a submitted artifact. It is intentionally not wired into a production stage
transition yet; callers invoke ``dispatch_plan`` directly while the substrate
round-trip hardens.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from forge_contracts.references import ArtifactRef, Reference
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from forge_bridge.orchestration.drivers import (
    GenerationDriverRegistry,
    backend_id_from_identity_triple,
)
from forge_bridge.store.generation_grant_repo import GenerationGrantRepo
from forge_bridge.store.models import DBEntity
from forge_bridge.store.orch_entity_views import DBOrchExecutionPlan
from forge_bridge.store.orch_execution_result_repo import ExecutionResultRepo
from forge_bridge.store.orch_generation_artifact_repo import GenerationArtifactRepo
from forge_bridge.store.orch_pipeline_run_repo import PipelineRunRepo


@dataclass(frozen=True)
class InvocationEnvelope:
    """Bridge-local invocation envelope on contract reference currency."""

    operator_id: str
    inputs: list[ArtifactRef]
    backend_identity_triple: dict[str, Any]
    # #160 — the fitted-model asset this invocation runs against. Intrinsic to
    # the invocation (an envelope FIELD, not a dispatch kwarg), so the
    # fail-closed revocation gate can read it at the submit chokepoint. Defaults
    # None; existing construction sites keep working unchanged (no model named →
    # gate no-ops, preserving existing behavior).
    fitted_model_asset_id: str | None = None


@dataclass(frozen=True)
class DispatchResult:
    status: str
    artifact_id: uuid.UUID | None = None
    refusal_code: str | None = None
    execution_result_ids: tuple[uuid.UUID, ...] = ()


def _generation_step(plan: DBOrchExecutionPlan) -> dict[str, Any] | None:
    for step in plan.operator_sequence or []:
        if not isinstance(step, dict):
            continue
        if _is_sync_perception_step(step):
            continue
        if step.get("backend_id") and step.get("operator_id"):
            return step
    return None


def _is_sync_perception_step(step: dict[str, Any]) -> bool:
    return (
        step.get("family") == "perception"
        or step.get("capability_family") == "perception"
        or step.get("payload_family") == "perception"
        or step.get("payload_family") == "perception_v1"
    )


def _sync_perception_steps(
    plan: DBOrchExecutionPlan,
) -> list[tuple[int, dict[str, Any]]]:
    steps: list[tuple[int, dict[str, Any]]] = []
    for index, step in enumerate(plan.operator_sequence or []):
        if isinstance(step, dict) and _is_sync_perception_step(step):
            steps.append((index, step))
    return steps


def _step_id(index: int, step: dict[str, Any]) -> str:
    return str(
        step.get("step_id")
        or step.get("operator_id")
        or step.get("operator")
        or f"step-{index}"
    )


def _artifact_ref(value: Any) -> ArtifactRef:
    if isinstance(value, ArtifactRef):
        return value
    if isinstance(value, dict):
        locator = value.get("locator")
        if isinstance(locator, dict):
            locator = Reference(**locator)
        return ArtifactRef(
            artifact_id=str(
                value.get("artifact_id")
                or value.get("source_artifact_id")
                or value.get("id")
                or ""
            ),
            artifact_type=str(value.get("artifact_type") or "artifact"),
            payload_id=value.get("payload_id"),
            locator=locator,
            metadata=dict(value.get("metadata") or {}),
        )
    return ArtifactRef(
        artifact_id=str(value),
        artifact_type="artifact",
        metadata={},
    )


def _dump_artifact_ref(ref: ArtifactRef) -> dict[str, Any]:
    return ref.model_dump(mode="json", exclude_none=True)


# ─────────────────────────────────────────────────────────────
# GenerationGrant spend-gate (#146)
# ─────────────────────────────────────────────────────────────
# The grant authority is resolved and consumed HERE, at the shared dispatch
# core, so BOTH doors — the planner (`dispatch_plan`) and the direct
# `forge_generate_*` tool (`dispatch_generation`) — are gated at one point.
# The grant handle is resolved from an explicit `grant_id` kwarg, or from the
# run's durable `run.grant_id` when only a `run_id` is supplied. A caller-
# supplied id is a LOOKUP KEY only — never trusted as authority; the persisted
# `status` is the authority. Fail-closed: no resolvable ratified grant → refuse.


async def _resolve_grant_id(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    grant_id: str | None,
    run_id: uuid.UUID | None,
) -> str | None:
    """Resolve the grant handle: explicit kwarg first, else run.grant_id.

    Single source of resolution shared by the mandatory chokepoint consume and
    the direct-door advisory peek (never a second copy of the logic).
    """
    if grant_id is not None:
        return grant_id
    if run_id is not None:
        async with session_factory() as session:
            run = await PipelineRunRepo(session).get_by_id(run_id)
            if run is not None:
                resolved = run.grant_id
                if resolved:
                    return str(resolved)
    return None


async def _resolve_and_consume_grant(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    grant_id: str | None,
    run_id: uuid.UUID | None,
) -> tuple[bool, str | None]:
    """Mandatory chokepoint gate: resolve the grant and atomically consume it.

    Returns ``(True, None)`` when a ratified grant was consumed exactly once;
    ``(False, refusal_code)`` otherwise. ``refusal_code`` is ``grant_consumed``
    for the already-spent (replay) case and ``grant_not_ratified`` for every
    other refusal (no anchor, unknown id, still-proposed, revoked/failed).
    Fail-closed by construction — ``run_id=None`` AND ``grant_id=None`` refuses.
    """
    resolved = await _resolve_grant_id(
        session_factory, grant_id=grant_id, run_id=run_id,
    )
    if resolved is None:
        return False, "grant_not_ratified"
    async with session_factory() as session:
        repo = GenerationGrantRepo(session)
        consumed = await repo.consume_atomic(resolved)
        if consumed is not None:
            await session.commit()
            return True, None
        # CAS lost / no ratified row — classify without mutating.
        existing = await repo.get_by_grant_id(resolved)
    if existing is not None and existing.status == "consumed":
        return False, "grant_consumed"
    return False, "grant_not_ratified"


async def _advisory_grant_check(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    grant_id: str | None,
    run_id: uuid.UUID | None,
) -> tuple[bool, str | None]:
    """Direct-door advisory peek — NON-consuming fail-fast.

    Shares ``_resolve_grant_id`` with the chokepoint (no second copy of the
    resolution logic) but deliberately does NOT consume: the single atomic
    consume stays at the mandatory chokepoint. This lets the direct
    ``forge_generate_*`` door refuse early before doing envelope work; the
    chokepoint remains the authoritative gate.
    """
    resolved = await _resolve_grant_id(
        session_factory, grant_id=grant_id, run_id=run_id,
    )
    if resolved is None:
        return False, "grant_not_ratified"
    async with session_factory() as session:
        existing = await GenerationGrantRepo(session).get_by_grant_id(resolved)
    if existing is None:
        return False, "grant_not_ratified"
    if existing.status == "consumed":
        return False, "grant_consumed"
    if existing.status != "ratified":
        return False, "grant_not_ratified"
    return True, None


# ─────────────────────────────────────────────────────────────
# Fitted-model revocation gate (#160)
# ─────────────────────────────────────────────────────────────
# Fail-closed consent enforcement at the submit chokepoint: a revoked
# fitted-model asset must never be inferred against. Mirrors
# ``_resolve_and_consume_grant``'s session usage and return shape, but this is a
# pure READ — a revocation flag is never a spend, so there is no CAS/consume.


async def _check_model_not_revoked(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    fitted_model_asset_id: str | None,
) -> tuple[bool, str | None]:
    """Resolve the fitted-model asset and verify it is not revoked.

    Returns ``(True, None)`` when NO model is named (the no-op / no-regression
    case — existing envelopes without the field pass straight through) OR the
    named asset exists and carries no ``attributes.revoked_at``. Returns
    ``(False, "model_not_found")`` when the id resolves to no asset, and
    ``(False, "model_revoked")`` when the asset's JSONB has ``revoked_at`` set.
    Fail-closed by construction: any resolvable-but-revoked or missing model
    refuses before the single ``driver.submit`` chokepoint runs.
    """
    if fitted_model_asset_id is None:
        return True, None
    try:
        asset_uuid = uuid.UUID(str(fitted_model_asset_id))
    except (ValueError, AttributeError, TypeError):
        # An unparseable id resolves to no asset — fail closed.
        return False, "model_not_found"
    async with session_factory() as session:
        db_entity = await session.get(DBEntity, asset_uuid)
    if db_entity is None:
        return False, "model_not_found"
    # Presence-based, fail-closed: any non-None ``revoked_at`` means revoked.
    # Do NOT revert to truthiness — a falsy sentinel ("" / 0) from a future
    # writer (the #161 consent path) would silently open the gate.
    if (db_entity.attributes or {}).get("revoked_at") is not None:
        return False, "model_revoked"
    return True, None


async def dispatch_plan(
    plan: DBOrchExecutionPlan,
    *,
    driver_registry: GenerationDriverRegistry,
    session_factory: async_sessionmaker[AsyncSession],
    event_appender: Callable[[str, dict], Awaitable[None]],
    run_id: uuid.UUID | None = None,
    grant_id: str | None = None,
) -> DispatchResult:
    """Dispatch plan execution through family-specific evidence lanes.

    The planner door is spend-gated at the shared chokepoint: ``grant_id`` (an
    explicit handle) or the run's durable ``run.grant_id`` (resolved from
    ``run_id`` inside ``dispatch_envelope``) must name a ratified grant, else
    the generation submit is refused. Perception-only plans never reach the
    chokepoint, so they are unaffected.
    """

    execution_result_ids: list[uuid.UUID] = []
    sync_steps = _sync_perception_steps(plan)
    if sync_steps and run_id is None:
        await event_appender(
            "dispatch_missing_run_id",
            {"plan_id": str(plan.id), "family": "perception"},
        )
        return DispatchResult(status="refused", refusal_code="dispatch_missing_run_id")
    assert run_id is not None or not sync_steps

    for index, sync_step in sync_steps:
        step_id = _step_id(index, sync_step)
        disposition = str(sync_step.get("disposition") or "candidate")
        result_payload = sync_step.get("result_payload")
        if not isinstance(result_payload, dict):
            result_payload = {
                "operator_id": sync_step.get("operator_id"),
                "step_id": step_id,
            }
        async with session_factory() as session:
            result = await ExecutionResultRepo(session).insert_result(
                run_id=run_id,
                step_id=step_id,
                family="perception",
                disposition=disposition,
                result_payload=result_payload,
                result_ref=sync_step.get("result_ref")
                if isinstance(sync_step.get("result_ref"), dict)
                else None,
            )
            await session.commit()
        execution_result_ids.append(result.id)
        await event_appender(
            "execution_step_terminal",
            {
                "plan_id": str(plan.id),
                "run_id": str(run_id) if run_id is not None else None,
                "step_id": step_id,
                "family": "perception",
                "disposition": disposition,
                "execution_result_id": str(result.id),
            },
        )

    step = _generation_step(plan)
    if step is None:
        if execution_result_ids:
            return DispatchResult(
                status="completed",
                execution_result_ids=tuple(execution_result_ids),
            )
        await event_appender(
            "dispatch_no_generation_step",
            {"plan_id": str(plan.id)},
        )
        return DispatchResult(status="refused", refusal_code="dispatch_no_generation_step")

    backend_id = str(step["backend_id"])
    driver = driver_registry.get_driver(backend_id)
    if driver is None:
        await event_appender(
            "dispatch_no_driver",
            {
                "plan_id": str(plan.id),
                "operator_id": step.get("operator_id"),
                "backend_id": backend_id,
            },
        )
        return DispatchResult(
            status="refused",
            refusal_code="dispatch_no_driver",
            execution_result_ids=tuple(execution_result_ids),
        )

    # The backend triple lives on the resolved driver, not the plan, so the
    # plan prologue resolves the driver here to author the envelope. The
    # plan-free ``dispatch_envelope`` re-resolves (idempotent dict lookup) as
    # the single submit chokepoint, so both doors reach the identical path.
    backend_identity_triple = dict(driver.backend_identity_triple)
    inputs = [_artifact_ref(item) for item in (step.get("inputs") or [])]
    # ponytail: ``fitted_model_asset_id`` is intentionally NOT threaded onto this
    # plan-authored envelope yet — no fitted-model plan steps exist, so the
    # revocation gate no-ops for all plan-driven dispatch (envelope carries no
    # model id → ``_check_model_not_revoked`` returns the no-op pass). Upgrade
    # path: when a fitted-model plan step lands, thread
    # ``step[...] → fitted_model_asset_id`` here (mirroring how
    # ``dispatch_envelope`` carries it) and the existing gate starts enforcing.
    envelope = InvocationEnvelope(
        operator_id=str(step["operator_id"]),
        inputs=inputs,
        backend_identity_triple=backend_identity_triple,
    )

    provenance: dict[str, Any] = {
        "plan_id": str(plan.id),
        "planned_output_artifact_id": step.get("output_artifact_id"),
        "execution_result_ids": tuple(execution_result_ids),
    }
    return await dispatch_envelope(
        envelope,
        provenance=provenance,
        driver_registry=driver_registry,
        session_factory=session_factory,
        event_appender=event_appender,
        run_id=run_id,
        grant_id=grant_id,
    )


async def dispatch_envelope(
    envelope: InvocationEnvelope,
    *,
    provenance: dict[str, Any],
    driver_registry: GenerationDriverRegistry,
    session_factory: async_sessionmaker[AsyncSession],
    event_appender: Callable[[str, dict], Awaitable[None]],
    run_id: uuid.UUID | None = None,
    grant_id: str | None = None,
) -> DispatchResult:
    """Plan-free submit-and-persist core for a single generation invocation.

    Both the planner-driven ``dispatch_plan`` and a future direct
    ``forge_generate_*`` tool converge here: resolve the backend driver from the
    envelope's identity triple, submit exactly once, persist the submitted
    artifact, and emit the two lineage events. The result is a pollable
    ``artifact_id`` in the same status-driven lifecycle the poller consumes.

    ``provenance`` carries OPTIONAL plan-lineage:
      - ``plan_id`` — when present, stamped onto ``content_provenance``,
        ``content_provenance.lineage.source_plan_id`` and both lineage events;
        a plan-free caller OMITS it and it is absent everywhere downstream.
      - ``planned_output_artifact_id`` — optional provenance string.
      - ``execution_result_ids`` — upstream (plan-shaped) perception-lane
        result ids threaded onto the returned ``DispatchResult`` so the plan
        path is byte-preserved.
    """

    execution_result_ids = tuple(provenance.get("execution_result_ids") or ())
    plan_id = provenance.get("plan_id")

    backend_id = backend_id_from_identity_triple(dict(envelope.backend_identity_triple))
    driver = driver_registry.get_driver(backend_id) if backend_id else None
    if driver is None:
        no_driver_payload: dict[str, Any] = {
            "operator_id": envelope.operator_id,
            "backend_id": backend_id,
        }
        if plan_id is not None:
            no_driver_payload = {"plan_id": plan_id, **no_driver_payload}
        await event_appender("dispatch_no_driver", no_driver_payload)
        return DispatchResult(
            status="refused",
            refusal_code="dispatch_no_driver",
            execution_result_ids=execution_result_ids,
        )

    backend_identity_triple = dict(driver.backend_identity_triple)
    inputs = list(envelope.inputs)

    # --- single driver.submit() chokepoint --------------------------------
    # GenerationGrant CAS authority guard (#146): gate spend HERE so both the
    # planner door and a direct forge_generate_* tool are gated at one point.
    # Consume-then-submit — the atomic ratified->consumed flip MUST succeed
    # before driver.submit() runs; a refusal never submits. Assent/ratify stays
    # ABOVE this core in the tool layer; never submit above this line.
    grant_ok, refusal_code = await _resolve_and_consume_grant(
        session_factory, grant_id=grant_id, run_id=run_id,
    )
    if not grant_ok:
        refuse_payload: dict[str, Any] = {
            "operator_id": envelope.operator_id,
            "backend_id": backend_id,
            "refusal_code": refusal_code,
            "run_id": str(run_id) if run_id is not None else None,
        }
        if plan_id is not None:
            refuse_payload = {"plan_id": plan_id, **refuse_payload}
        await event_appender("dispatch_grant_refused", refuse_payload)
        return DispatchResult(
            status="refused",
            refusal_code=refusal_code,
            execution_result_ids=execution_result_ids,
        )

    # Fitted-model revocation gate (#160): fail-closed consent enforcement at
    # the same submit chokepoint. If the envelope names a fitted-model asset it
    # MUST resolve and MUST NOT be revoked, else refuse before driver.submit().
    # No model named → no-op (skip), preserving existing behavior. This is a
    # pure read — never a spend — so it does not consume anything.
    model_ok, model_refusal_code = await _check_model_not_revoked(
        session_factory, fitted_model_asset_id=envelope.fitted_model_asset_id,
    )
    if not model_ok:
        model_refuse_payload: dict[str, Any] = {
            "operator_id": envelope.operator_id,
            "backend_id": backend_id,
            "refusal_code": model_refusal_code,
            "run_id": str(run_id) if run_id is not None else None,
        }
        if plan_id is not None:
            model_refuse_payload = {"plan_id": plan_id, **model_refuse_payload}
        await event_appender("dispatch_model_refused", model_refuse_payload)
        return DispatchResult(
            status="refused",
            refusal_code=model_refusal_code,
            execution_result_ids=execution_result_ids,
        )
    handle = await driver.submit(envelope)
    # ----------------------------------------------------------------------

    content_provenance: dict[str, Any] = {
        "operator_id": envelope.operator_id,
        "planned_output_artifact_id": provenance.get("planned_output_artifact_id"),
        "inputs": [_dump_artifact_ref(ref) for ref in inputs],
        "lineage": {
            "input_artifact_ids": [ref.artifact_id for ref in inputs],
        },
    }
    if plan_id is not None:
        content_provenance["plan_id"] = plan_id
        content_provenance["lineage"]["source_plan_id"] = plan_id

    body: dict[str, Any] = {
        "name": (
            f"orch_generation_artifact:{envelope.operator_id}:{handle.request_id}"
        ),
        "platform_locators": {},
        "content_provenance": content_provenance,
        "execution_provenance": {
            "backend_identity_triple": backend_identity_triple,
            "request_id": handle.request_id,
            "submitted_at": handle.submitted_at.isoformat(),
            "raw_response_summary": dict(handle.raw_response_summary),
        },
        "polling_history": [],
    }
    if run_id is not None:
        body["run_id"] = str(run_id)

    async with session_factory() as session:
        artifact = await GenerationArtifactRepo(session).insert_submitted(body)
        await session.commit()

    submitted_event: dict[str, Any] = {
        "artifact_id": str(artifact.id),
        "operator_id": envelope.operator_id,
        "backend_id": backend_id,
        "request_id": handle.request_id,
        "run_id": str(run_id) if run_id is not None else None,
    }
    if plan_id is not None:
        submitted_event = {"plan_id": plan_id, **submitted_event}
    await event_appender("generation_dispatch_submitted", submitted_event)

    lineage_event: dict[str, Any] = {
        "artifact_id": str(artifact.id),
        "input_artifact_ids": [ref.artifact_id for ref in inputs],
    }
    if plan_id is not None:
        lineage_event["plan_id"] = plan_id
    await event_appender("generation_dispatch_lineage_recorded", lineage_event)

    return DispatchResult(
        status="submitted",
        artifact_id=artifact.id,
        execution_result_ids=execution_result_ids,
    )
