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
from forge_bridge.store.orch_entity_views import DBOrchExecutionPlan
from forge_bridge.store.orch_execution_result_repo import ExecutionResultRepo
from forge_bridge.store.orch_generation_artifact_repo import GenerationArtifactRepo


@dataclass(frozen=True)
class InvocationEnvelope:
    """Bridge-local invocation envelope on contract reference currency."""

    operator_id: str
    inputs: list[ArtifactRef]
    backend_identity_triple: dict[str, Any]


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


async def dispatch_plan(
    plan: DBOrchExecutionPlan,
    *,
    driver_registry: GenerationDriverRegistry,
    session_factory: async_sessionmaker[AsyncSession],
    event_appender: Callable[[str, dict], Awaitable[None]],
    run_id: uuid.UUID | None = None,
) -> DispatchResult:
    """Dispatch plan execution through family-specific evidence lanes."""

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
    )


async def dispatch_envelope(
    envelope: InvocationEnvelope,
    *,
    provenance: dict[str, Any],
    driver_registry: GenerationDriverRegistry,
    session_factory: async_sessionmaker[AsyncSession],
    event_appender: Callable[[str, dict], Awaitable[None]],
    run_id: uuid.UUID | None = None,
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
    # SEAM (Rung-C / #31 D6): the future GenerationGrant CAS authority guard
    # gates spend HERE so both the planner door and a direct forge_generate_*
    # tool are gated at one point. Assent/ratify stays ABOVE this core in the
    # tool layer; never submit above this line. The grant mechanism is
    # design-stage and intentionally NOT built in HALF 1.
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
