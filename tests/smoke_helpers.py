"""Shared fixtures for Phase 4B end-to-end smoke tests."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from forge_bridge.orchestration.drivers import (
    DriverPollResult,
    GenerationDriverRegistry,
)
from forge_bridge.orchestration.engine import GraphEngine
from forge_bridge.orchestration.event_consumer import (
    ConsumerProcessResult,
    GraphEngineEventConsumer,
)
from forge_bridge.orchestration.identity_registries import (
    InMemoryPlatformUUIDRegistry,
    InMemoryTrainedIdentityRegistry,
)
from forge_bridge.orchestration.lineage_graph import InMemoryLineageGraph
from forge_bridge.orchestration.manifest import ProvenanceManifestAssembler
from forge_bridge.orchestration.planner import Planner
from forge_bridge.orchestration.registration import ToolRegistration, ToolRegistry
from forge_bridge.orchestration.worker import GenerationPoller
from forge_bridge.store.models import DBEntity, DBEvent
from forge_bridge.store.orch_audit_report_repo import AuditReportRepo
from forge_bridge.store.orch_entity_views import DBOrchExecutionPlan, DBOrchProvenanceManifest
from forge_bridge.store.orch_generation_artifact_repo import GenerationArtifactRepo
from forge_bridge.store.orch_inputs_catalog_repo import InputsCatalogRepo
from forge_bridge.store.orch_locked_intent_repo import LockedIntentRepo
from forge_bridge.store.orch_partial_fidelity_snapshot_repo import (
    PartialFidelitySnapshotRepo,
)
from forge_bridge.store.orch_rule_snapshot_repo import RuleSnapshotRepo
from forge_bridge.store.orch_spec_convergence_trace_repo import SpecConvergenceTraceRepo
from forge_bridge.store.orchestration_lifecycle_state_repo import (
    OrchestrationLifecycleStateRepo,
)
from forge_bridge.store.orchestration_promotion_ledger_repo import (
    OrchestrationPromotionLedgerRepo,
)

MOCK_BACKEND_ID = "mock.backend"


@dataclass
class SmokeFixtures:
    tool_registry: ToolRegistry
    driver_registry: GenerationDriverRegistry
    platform_uuid_registry: InMemoryPlatformUUIDRegistry
    trained_identity_registry: InMemoryTrainedIdentityRegistry
    lineage_graph: InMemoryLineageGraph
    driver: ScriptedGenerationDriver


@dataclass
class SmokeRunContext:
    run_id: uuid.UUID
    shot_id: uuid.UUID
    intent_id: uuid.UUID
    rule_snapshot_id: uuid.UUID
    partial_fidelity_snapshot_id: uuid.UUID
    capability_snapshot_id: uuid.UUID | None
    inputs_catalog_id: uuid.UUID
    spec_convergence_trace_id: uuid.UUID
    plan_id: uuid.UUID | None = None


class ScriptedGenerationDriver:
    """Test driver returning scripted DriverPollResults per artifact."""

    def __init__(
        self,
        backend_id: str,
        script: list[DriverPollResult] | None = None,
    ) -> None:
        self.backend_id = backend_id
        self._script = script or []
        self._sequence_index: dict[uuid.UUID, int] = {}

    def set_script(self, script: list[DriverPollResult]) -> None:
        self._script = script
        self._sequence_index.clear()

    async def poll(self, artifact) -> DriverPollResult:
        idx = self._sequence_index.get(artifact.id, 0)
        if idx >= len(self._script):
            return self._script[-1]
        result = self._script[idx]
        self._sequence_index[artifact.id] = idx + 1
        return result


def build_smoke_setup(
    *,
    backend_id: str = MOCK_BACKEND_ID,
    driver_script: list[DriverPollResult] | None = None,
) -> SmokeFixtures:
    tool_registry = ToolRegistry()
    driver_registry = GenerationDriverRegistry()
    platform = InMemoryPlatformUUIDRegistry()
    trained = InMemoryTrainedIdentityRegistry()
    lineage = InMemoryLineageGraph()
    surface, path = backend_id.split(".", 1)
    driver = ScriptedGenerationDriver(backend_id, driver_script)
    driver_registry.register_driver(driver)
    tool_registry.register(
        ToolRegistration(
            tool_id=f"forge_generators.{backend_id}",
            family="generation",
            payload_family="generation_v1",
            schema={"type": "object"},
            handler=driver,
            capabilities={
                "backend_identity_triple": {
                    "surface": surface,
                    "path": path,
                    "revision": "v1",
                },
                "first_frame_guarantee": True,
                "acceptance_score": 0.9,
                "estimated_cost": 1.0,
            },
        ),
        sibling_name="forge_generators",
    )
    return SmokeFixtures(
        tool_registry=tool_registry,
        driver_registry=driver_registry,
        platform_uuid_registry=platform,
        trained_identity_registry=trained,
        lineage_graph=lineage,
        driver=driver,
    )


def default_happy_driver_script(
    *,
    rule_snapshot_id: uuid.UUID,
    cost: float = 10.0,
) -> list[DriverPollResult]:
    terminal = {
        "backend_identity_triple": {
            "surface": "mock",
            "path": "backend",
            "revision": "v1",
        },
        "cost": {"currency": "USD", "amount": cost},
        "rule_snapshot_id": str(rule_snapshot_id),
    }
    return [
        DriverPollResult(
            next_state="polling",
            polling_event={"status": "in_progress"},
        ),
        DriverPollResult(
            next_state="complete",
            polling_event={"status": "done"},
            terminal_provenance=terminal,
        ),
    ]


def default_failed_driver_script() -> list[DriverPollResult]:
    return [
        DriverPollResult(
            next_state="polling",
            polling_event={"status": "in_progress"},
        ),
        DriverPollResult(
            next_state="failed",
            polling_event={"status": "failed"},
            terminal_provenance={
                "backend_identity_triple": {
                    "surface": "mock",
                    "path": "backend",
                    "revision": "v1",
                },
            },
        ),
    ]


async def seed_smoke_entities(session: AsyncSession) -> SmokeRunContext:
    shot_id = uuid.uuid4()
    run_id = uuid.uuid4()
    rule = await RuleSnapshotRepo(session).insert_if_absent(
        {
            "rules": [{"rule_id": "R1", "statement": "smoke"}],
            "source_ref": "methodology/smoke",
            "snapshot_timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
    partial = await PartialFidelitySnapshotRepo(session).insert_if_absent(
        {
            "models": [
                {
                    "backend_identity_triple": {"surface": "mock", "path": "backend"},
                    "dimensions": [{"axis": "motion", "scalar": 0.1}],
                }
            ]
        }
    )
    trace = await SpecConvergenceTraceRepo(session).insert_if_absent(
        {"iterations": [{"version": 1}], "lock_event": {"locked_at": "2026-05-28T12:00:00Z"}}
    )
    inputs = await InputsCatalogRepo(session).insert_if_absent(
        {"inputs": [], "role_assignments": {}}
    )
    intent = await LockedIntentRepo(session).insert_if_absent(
        {
            "source_read": {"shot_id": str(shot_id)},
            "change_manifest": [],
            "success_criteria": [
                {
                    "criterion_id": "motion_arc",
                    "statement": "hand reaches target",
                    "measurement_spec": {"method": "temporal_ioU"},
                    "tolerances": {"min": 0.7},
                }
            ],
            "allowed_compromises": [{"criterion_id": "motion_arc", "budget": 0.5}],
            "hard_constraints": [],
            "escalation_threshold": 0.9,
            "deliverable_spec": {
                "medium": "video",
                "requires_first_frame": True,
            },
        }
    )
    session.add(
        DBEntity(
            id=run_id,
            entity_type="orch_pipeline_run",
            content_hash=f"run-{run_id.hex}",
            attributes={
                "run_kind": "original",
                "intent_id": str(intent.id),
                "spec_convergence_trace_id": str(trace.id),
                "authored_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    )
    await session.flush()
    return SmokeRunContext(
        run_id=run_id,
        shot_id=shot_id,
        intent_id=intent.id,
        rule_snapshot_id=rule.id,
        partial_fidelity_snapshot_id=partial.id,
        capability_snapshot_id=None,
        inputs_catalog_id=inputs.id,
        spec_convergence_trace_id=trace.id,
    )


async def stage_to_routing(
    session: AsyncSession,
    *,
    ctx: SmokeRunContext,
    engine: GraphEngine,
) -> None:
    await engine.create_run(run_id=ctx.run_id, shot_id=ctx.shot_id)
    await engine.transition(ctx.run_id, to_stage="spec_convergence")
    await engine.apply_decision_event(
        ctx.run_id,
        "lock_intent",
        {"intent_id": str(ctx.intent_id)},
    )


async def stage_to_execution_via_planner(
    session: AsyncSession,
    *,
    ctx: SmokeRunContext,
    engine: GraphEngine,
    planner: Planner,
) -> DBOrchExecutionPlan:
    plan = await planner.plan(
        intent_id=ctx.intent_id,
        run_id=ctx.run_id,
        rule_snapshot_id=ctx.rule_snapshot_id,
        partial_fidelity_snapshot_id=ctx.partial_fidelity_snapshot_id,
        inputs_catalog_id=ctx.inputs_catalog_id,
        capability_snapshot_id=ctx.capability_snapshot_id,
    )
    ctx.plan_id = plan.id
    ctx.capability_snapshot_id = plan.capability_snapshot_id
    if plan.feasibility_verdict not in {"feasible", "constrained-but-feasible"}:
        raise RuntimeError(f"Planner infeasible: {plan.refusal_code}")
    await engine.transition(
        ctx.run_id,
        to_stage="execution",
        plan_id=plan.id,
        intent_id=ctx.intent_id,
    )
    return plan


async def insert_submitted_artifacts(
    session: AsyncSession,
    *,
    run_id: uuid.UUID,
    count: int = 2,
    rule_snapshot_id: uuid.UUID | None = None,
) -> list[uuid.UUID]:
    repo = GenerationArtifactRepo(session)
    artifact_ids: list[uuid.UUID] = []
    for slot in range(count):
        body = {
            "run_id": str(run_id),
            "artifact_slot": slot,
            "platform_locators": {},
            "content_provenance": {"reference_inputs": []},
            "execution_provenance": {
                "backend_identity_triple": {
                    "surface": "mock",
                    "path": "backend",
                    "revision": "v1",
                },
            },
        }
        if rule_snapshot_id is not None:
            body["execution_provenance"]["rule_snapshot_id"] = str(rule_snapshot_id)
        row = await repo.insert_submitted(body)
        artifact_ids.append(row.id)
    return artifact_ids


async def drive_execution_to_terminal(
    session_factory: async_sessionmaker,
    *,
    poller: GenerationPoller,
    artifact_ids: list[uuid.UUID] | None = None,
    max_passes: int = 20,
) -> list[DBEvent]:
    terminal_events: list[DBEvent] = []
    seen: set[uuid.UUID] = set()
    artifact_id_set = {str(aid) for aid in artifact_ids} if artifact_ids else None
    for _ in range(max_passes):
        result = await poller.poll_once()
        async with session_factory() as session:
            events = await session.execute(
                select(DBEvent)
                .where(DBEvent.event_type == "generation_artifact_terminal")
                .order_by(DBEvent.occurred_at.asc())
            )
            for event in events.scalars().all():
                if artifact_id_set is not None:
                    payload_artifact = (event.payload or {}).get("artifact_id")
                    if payload_artifact not in artifact_id_set:
                        continue
                if event.id not in seen:
                    seen.add(event.id)
                    terminal_events.append(event)
            repo = GenerationArtifactRepo(session)
            remaining = await repo.find_non_terminal()
            if artifact_id_set is not None:
                remaining = [
                    row for row in remaining if str(row.id) in artifact_id_set
                ]
        if result.processed == 0 and not remaining:
            break
    return terminal_events


async def drive_consumer_to_audit(
    session: AsyncSession,
    *,
    terminal_events: list[DBEvent],
    consumer: GraphEngineEventConsumer,
) -> ConsumerProcessResult:
    result: ConsumerProcessResult | None = None
    for event in terminal_events:
        result = await consumer.process_terminal_event(event)
    assert result is not None
    return result


async def emit_audit_and_promote(
    session: AsyncSession,
    *,
    ctx: SmokeRunContext,
    candidate_artifact_id: uuid.UUID,
    engine: GraphEngine,
) -> uuid.UUID:
    audit = await AuditReportRepo(session).insert_if_absent(
        {
            "candidate_artifact_id": str(candidate_artifact_id),
            "intent_id": str(ctx.intent_id),
            "rules_snapshot_ref": str(ctx.rule_snapshot_id),
            "per_criterion": [],
            "cross_criterion_summary": {"overall_verdict": "pass"},
        }
    )
    await engine.apply_decision_event(
        ctx.run_id,
        "promote_candidate",
        {"promoted_artifact_id": str(candidate_artifact_id)},
    )
    promotion = await OrchestrationPromotionLedgerRepo(session).insert_promotion(
        shot_id=ctx.shot_id,
        promoted_artifact_id=candidate_artifact_id,
        promoted_by="smoke-test",
        rationale="smoke promotion",
        audit_report_id=audit.id,
    )
    return promotion.promotion_id


async def transition_publish_and_assemble_manifest(
    session: AsyncSession,
    *,
    ctx: SmokeRunContext,
    promotion_id: uuid.UUID,
    engine: GraphEngine,
    assembler: ProvenanceManifestAssembler,
) -> DBOrchProvenanceManifest:
    await engine.transition(ctx.run_id, to_stage="publish")
    await engine.transition(ctx.run_id, to_status="completed")
    return await assembler.assemble(promotion_id=promotion_id)


async def run_events(session: AsyncSession, run_id: uuid.UUID) -> list[str]:
    result = await session.execute(
        select(DBEvent)
        .where(DBEvent.entity_id == run_id)
        .order_by(DBEvent.occurred_at.asc(), DBEvent.id.asc())
    )
    return [row.event_type for row in result.scalars().all()]


def make_planner(session: AsyncSession, fixtures: SmokeFixtures) -> Planner:
    return Planner(
        session,
        tool_registry=fixtures.tool_registry,
        platform_uuid_registry=fixtures.platform_uuid_registry,
        trained_identity_registry=fixtures.trained_identity_registry,
        lineage_graph=fixtures.lineage_graph,
    )


async def lifecycle_for(session: AsyncSession, run_id: uuid.UUID):
    row = await OrchestrationLifecycleStateRepo(session).get_by_run_id(run_id)
    assert row is not None
    return row
