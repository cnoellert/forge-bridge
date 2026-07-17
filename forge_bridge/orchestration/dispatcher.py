"""Generation dispatch spine (Phase 7 vertical 1).

This module proves the bridge-owned lifecycle from a selected generation step
to a submitted artifact. It is intentionally not wired into a production stage
transition yet; callers invoke ``dispatch_plan`` directly while the substrate
round-trip hardens.
"""

from __future__ import annotations

import hashlib
import json
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
from forge_bridge.store.fitted_model_lifecycle_repo import FittedModelLifecycleRepo
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
    # fail-closed lifecycle gate can read it at the submit chokepoint. Defaults
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


def _normalize_generation_idempotency_key(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("generation idempotency_key must be a string or None")
    if not value or value != value.strip():
        raise ValueError("generation idempotency_key must be non-empty and unpadded")
    if len(value.encode("utf-8")) > 512:
        raise ValueError("generation idempotency_key must not exceed 512 UTF-8 bytes")
    return value


def _generation_invocation_fingerprint(envelope: InvocationEnvelope) -> str:
    """Hash the work identity shared by direct and planner dispatch doors."""
    seed = json.dumps(
        {
            "operator_id": envelope.operator_id,
            "inputs": [_dump_artifact_ref(ref) for ref in envelope.inputs],
            "backend_identity_triple": envelope.backend_identity_triple,
            "fitted_model_asset_id": envelope.fitted_model_asset_id,
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


async def _existing_idempotency_result(
    existing: Any,
    *,
    idempotency_key: str,
    invocation_fingerprint: str,
    operator_id: str,
    backend_id: str | None,
    event_appender: Callable[[str, dict], Awaitable[None]],
    run_id: uuid.UUID | None,
    plan_id: Any = None,
    execution_result_ids: tuple[uuid.UUID, ...] = (),
) -> DispatchResult:
    payload: dict[str, Any] = {
        "artifact_id": str(existing.id),
        "operator_id": operator_id,
        "backend_id": backend_id,
        "idempotency_key": idempotency_key,
        "run_id": str(run_id) if run_id is not None else None,
    }
    if plan_id is not None:
        payload = {"plan_id": plan_id, **payload}

    if existing.idempotency_fingerprint != invocation_fingerprint:
        await event_appender(
            "generation_dispatch_idempotency_conflict",
            {
                **payload,
                "stored_fingerprint": existing.idempotency_fingerprint,
                "requested_fingerprint": invocation_fingerprint,
            },
        )
        return DispatchResult(
            status="refused",
            refusal_code="idempotency_conflict",
            execution_result_ids=execution_result_ids,
        )

    await event_appender(
        "generation_dispatch_deduplicated",
        {**payload, "lifecycle_state": existing.lifecycle_state},
    )
    return DispatchResult(
        status="submitted",
        artifact_id=existing.id,
        execution_result_ids=execution_result_ids,
    )


# ─────────────────────────────────────────────────────────────
# GenerationGrant spend-gate (#146)
# ─────────────────────────────────────────────────────────────
# The grant authority is resolved and consumed HERE, at the shared dispatch
# core, so BOTH doors — the planner (`dispatch_plan`) and the direct
# `forge_generate_*` tool (`dispatch_generation`) — are gated at one point.
# The direct door may refuse earlier via a non-consuming advisory check and
# records that as `dispatch_advisory_refused`; this chokepoint remains
# authoritative and owns `dispatch_grant_refused` after an attempted consume.
# The grant handle is resolved from an explicit `grant_id` kwarg, or from the
# run's durable `run.grant_id` when only a `run_id` is supplied. A caller-
# supplied id is a LOOKUP KEY only — never trusted as authority; the persisted
# status and immutable operator/backend terms are the authority. Fail-closed: no
# resolvable ratified grant matching the exact invocation terms -> refuse.


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
    operator_id: str,
    backend_identity_triple: dict[str, Any],
) -> tuple[bool, str | None]:
    """Mandatory chokepoint gate: resolve the grant and atomically consume it.

    Returns ``(True, None)`` when a ratified grant was consumed exactly once;
    ``(False, refusal_code)`` otherwise. ``refusal_code`` is ``grant_consumed``
    for the already-spent (replay) case, ``grant_terms_mismatch`` when a
    ratified grant names a different operator or backend identity, and
    ``grant_not_ratified`` for every other refusal.
    Fail-closed by construction — ``run_id=None`` AND ``grant_id=None`` refuses.
    """
    resolved = await _resolve_grant_id(
        session_factory, grant_id=grant_id, run_id=run_id,
    )
    if resolved is None:
        return False, "grant_not_ratified"
    async with session_factory() as session:
        repo = GenerationGrantRepo(session)
        existing = await repo.get_by_grant_id(resolved)
        if existing is None:
            return False, "grant_not_ratified"
        if existing.status == "consumed":
            return False, "grant_consumed"
        if existing.status != "ratified":
            return False, "grant_not_ratified"
        if not _grant_terms_match(
            existing,
            operator_id=operator_id,
            backend_identity_triple=backend_identity_triple,
        ):
            return False, "grant_terms_mismatch"
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
    operator_id: str,
    backend_identity_triple: dict[str, Any],
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
    if not _grant_terms_match(
        existing,
        operator_id=operator_id,
        backend_identity_triple=backend_identity_triple,
    ):
        return False, "grant_terms_mismatch"
    return True, None


def _grant_terms_match(
    grant: Any,
    *,
    operator_id: str,
    backend_identity_triple: dict[str, Any],
) -> bool:
    """Match immutable grant terms to the exact invocation being authorized."""

    return (
        grant.operator_id == operator_id
        and dict(grant.backend_identity_triple) == dict(backend_identity_triple)
    )


# ─────────────────────────────────────────────────────────────
# Fitted-model availability gate (#160)
# ─────────────────────────────────────────────────────────────
# Fail-closed lifecycle enforcement at the submit chokepoint: a revoked, marked,
# collected, malformed, or missing fitted-model asset must never be inferred
# against. The authoritative path locks the model row through submit and records
# use in the artifact transaction, preventing collection from racing inference.


async def _lock_model_for_submit(
    session: AsyncSession,
    *,
    fitted_model_asset_id: str | None,
) -> tuple[DBEntity | None, str | None]:
    """Lock and validate the fitted-model named by an invocation.

    ``None`` remains the no-model/no-regression path. A named model must resolve
    to an active ``fitted-model`` asset; the returned row lock is owned by the
    caller's transaction and must remain held through backend submission.
    """
    if fitted_model_asset_id is None:
        return None, None
    try:
        asset_uuid = uuid.UUID(str(fitted_model_asset_id))
    except (ValueError, AttributeError, TypeError):
        return None, "model_not_found"
    return await FittedModelLifecycleRepo(session).lock_for_inference(asset_uuid)


async def _check_model_not_revoked(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    fitted_model_asset_id: str | None,
) -> tuple[bool, str | None]:
    """Advisory fitted-model availability check for pre-dispatch callers.

    This compatibility seam now covers the complete lifecycle, despite its
    historical name. Its row lock ends when the advisory session closes; the
    authoritative dispatch path repeats the check and holds its lock through
    submit.
    """
    async with session_factory() as session:
        _model, refusal_code = await _lock_model_for_submit(
            session,
            fitted_model_asset_id=fitted_model_asset_id,
        )
    return refusal_code is None, refusal_code


async def dispatch_plan(
    plan: DBOrchExecutionPlan,
    *,
    driver_registry: GenerationDriverRegistry,
    session_factory: async_sessionmaker[AsyncSession],
    event_appender: Callable[[str, dict], Awaitable[None]],
    run_id: uuid.UUID | None = None,
    grant_id: str | None = None,
    idempotency_key: str | None = None,
) -> DispatchResult:
    """Dispatch plan execution through family-specific evidence lanes.

    The planner door is spend-gated at the shared chokepoint: ``grant_id`` (an
    explicit handle) or the run's durable ``run.grant_id`` (resolved from
    ``run_id`` inside ``dispatch_envelope``) must name a ratified grant, else
    the generation submit is refused. Perception-only plans never reach the
    chokepoint, so they are unaffected.

    ``idempotency_key`` may be supplied explicitly or carried by the generation
    step. If both are present they must match. The shared envelope boundary
    serializes and resolves that key before authority spend.
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
    # ``fitted_model_asset_id`` is threaded from the plan step onto this envelope,
    # so the same lifecycle gate enforces plan-driven and direct dispatch.
    envelope = InvocationEnvelope(
        operator_id=str(step["operator_id"]),
        inputs=inputs,
        backend_identity_triple=backend_identity_triple,
        fitted_model_asset_id=step.get("fitted_model_asset_id"),
    )
    step_idempotency_key = step.get("idempotency_key")
    if (
        idempotency_key is not None
        and step_idempotency_key is not None
        and idempotency_key != step_idempotency_key
    ):
        raise ValueError(
            "dispatch_plan idempotency_key conflicts with the generation step"
        )
    resolved_idempotency_key = (
        idempotency_key if idempotency_key is not None else step_idempotency_key
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
        idempotency_key=resolved_idempotency_key,
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
    idempotency_key: str | None = None,
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
      - ``source_author_artifact_id`` — an approved prompt artifact that
        authored this downstream generation invocation.

    A non-None ``idempotency_key`` is globally unique for generation artifacts.
    Calls sharing a key and invocation fingerprint return the first artifact;
    a key reused for different work refuses with ``idempotency_conflict``.
    """

    execution_result_ids = tuple(provenance.get("execution_result_ids") or ())
    plan_id = provenance.get("plan_id")
    idempotency_key = _normalize_generation_idempotency_key(idempotency_key)
    invocation_fingerprint = (
        _generation_invocation_fingerprint(envelope)
        if idempotency_key is not None
        else None
    )

    backend_id = backend_id_from_identity_triple(dict(envelope.backend_identity_triple))
    async with session_factory() as artifact_session:
        artifact_repo = GenerationArtifactRepo(artifact_session)
        if idempotency_key is not None:
            await artifact_repo.lock_idempotency_key(idempotency_key)
            existing = await artifact_repo.get_by_idempotency_key(idempotency_key)
            if existing is not None:
                assert invocation_fingerprint is not None
                return await _existing_idempotency_result(
                    existing,
                    idempotency_key=idempotency_key,
                    invocation_fingerprint=invocation_fingerprint,
                    operator_id=envelope.operator_id,
                    backend_id=backend_id,
                    event_appender=event_appender,
                    run_id=run_id,
                    plan_id=plan_id,
                    execution_result_ids=execution_result_ids,
                )

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

        # --- single driver.submit() chokepoint ----------------------------
        # Idempotency lookup above precedes authority spend. The per-key
        # transaction lock remains held through submit and artifact insert, so
        # concurrent callers cannot both cross this line for the same key.
        grant_ok, refusal_code = await _resolve_and_consume_grant(
            session_factory,
            grant_id=grant_id,
            run_id=run_id,
            operator_id=envelope.operator_id,
            backend_identity_triple=backend_identity_triple,
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

        model_entity, model_refusal_code = await _lock_model_for_submit(
            artifact_session,
            fitted_model_asset_id=envelope.fitted_model_asset_id,
        )
        if model_refusal_code is not None:
            model_refuse_payload: dict[str, Any] = {
                "operator_id": envelope.operator_id,
                "backend_id": backend_id,
                "refusal_code": model_refusal_code,
                "fitted_model_asset_id": envelope.fitted_model_asset_id,
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
        if model_entity is not None:
            await FittedModelLifecycleRepo(artifact_session).record_use(
                model_entity,
                operator_id=envelope.operator_id,
                request_id=handle.request_id,
            )
        # ------------------------------------------------------------------

        content_provenance: dict[str, Any] = {
            "operator_id": envelope.operator_id,
            "planned_output_artifact_id": provenance.get(
                "planned_output_artifact_id"
            ),
            "inputs": [_dump_artifact_ref(ref) for ref in inputs],
            "lineage": {
                "input_artifact_ids": [ref.artifact_id for ref in inputs],
            },
        }
        if plan_id is not None:
            content_provenance["plan_id"] = plan_id
            content_provenance["lineage"]["source_plan_id"] = plan_id
        source_author_artifact_id = provenance.get("source_author_artifact_id")
        if source_author_artifact_id is not None:
            content_provenance["source_author_artifact_id"] = str(
                source_author_artifact_id
            )
            content_provenance["lineage"]["source_author_artifact_id"] = str(
                source_author_artifact_id
            )
        if model_entity is not None:
            fitted_model_asset_id = str(model_entity.id)
            content_provenance["fitted_model_asset_id"] = fitted_model_asset_id
            content_provenance["lineage"][
                "fitted_model_asset_id"
            ] = fitted_model_asset_id

        body: dict[str, Any] = {
            "name": (
                f"orch_generation_artifact:{envelope.operator_id}:"
                f"{handle.request_id}"
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
        if idempotency_key is not None:
            assert invocation_fingerprint is not None
            body["idempotency_key"] = idempotency_key
            body["idempotency_fingerprint"] = invocation_fingerprint

        artifact = await artifact_repo.insert_submitted(body)
        await artifact_session.commit()

    submitted_event: dict[str, Any] = {
        "artifact_id": str(artifact.id),
        "operator_id": envelope.operator_id,
        "backend_id": backend_id,
        "request_id": handle.request_id,
        "run_id": str(run_id) if run_id is not None else None,
    }
    if idempotency_key is not None:
        submitted_event["idempotency_key"] = idempotency_key
    if model_entity is not None:
        submitted_event["fitted_model_asset_id"] = str(model_entity.id)
    if plan_id is not None:
        submitted_event = {"plan_id": plan_id, **submitted_event}
    await event_appender("generation_dispatch_submitted", submitted_event)

    lineage_event: dict[str, Any] = {
        "artifact_id": str(artifact.id),
        "input_artifact_ids": [ref.artifact_id for ref in inputs],
    }
    if model_entity is not None:
        lineage_event["fitted_model_asset_id"] = str(model_entity.id)
    if plan_id is not None:
        lineage_event["plan_id"] = plan_id
    await event_appender("generation_dispatch_lineage_recorded", lineage_event)

    return DispatchResult(
        status="submitted",
        artifact_id=artifact.id,
        execution_result_ids=execution_result_ids,
    )
