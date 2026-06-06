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


def _generation_step(plan: DBOrchExecutionPlan) -> dict[str, Any] | None:
    for step in plan.operator_sequence or []:
        if not isinstance(step, dict):
            continue
        if step.get("backend_id") and step.get("operator_id"):
            return step
    return None


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
) -> DispatchResult:
    """Dispatch the selected generation step and create a submitted artifact."""

    step = _generation_step(plan)
    if step is None:
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
        return DispatchResult(status="refused", refusal_code="dispatch_no_driver")

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
    return DispatchResult(status="submitted", artifact_id=artifact.id)
