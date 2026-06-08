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

from forge_bridge.orchestration.drivers import GenerationDriverRegistry
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

    backend_identity_triple = dict(driver.backend_identity_triple)
    inputs = [_artifact_ref(item) for item in (step.get("inputs") or [])]
    envelope = InvocationEnvelope(
        operator_id=str(step["operator_id"]),
        inputs=inputs,
        backend_identity_triple=backend_identity_triple,
    )

    handle = await driver.submit(envelope)

    body = {
        "name": f"orch_generation_artifact:{step['operator_id']}:{handle.request_id}",
        "platform_locators": {},
        "content_provenance": {
            "operator_id": step["operator_id"],
            "plan_id": str(plan.id),
            "planned_output_artifact_id": step.get("output_artifact_id"),
            "inputs": [_dump_artifact_ref(ref) for ref in inputs],
            "lineage": {
                "source_plan_id": str(plan.id),
                "input_artifact_ids": [ref.artifact_id for ref in inputs],
            },
        },
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

    await event_appender(
        "generation_dispatch_submitted",
        {
            "plan_id": str(plan.id),
            "artifact_id": str(artifact.id),
            "operator_id": step["operator_id"],
            "backend_id": backend_id,
            "request_id": handle.request_id,
            "run_id": str(run_id) if run_id is not None else None,
        },
    )
    await event_appender(
        "generation_dispatch_lineage_recorded",
        {
            "artifact_id": str(artifact.id),
            "plan_id": str(plan.id),
            "input_artifact_ids": [ref.artifact_id for ref in inputs],
        },
    )
    return DispatchResult(
        status="submitted",
        artifact_id=artifact.id,
        execution_result_ids=tuple(execution_result_ids),
    )
