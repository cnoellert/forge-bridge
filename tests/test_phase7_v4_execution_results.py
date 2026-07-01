"""Phase 7 V4 — execution completion is family-agnostic."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

from sqlalchemy import select

from forge_bridge.orchestration import (
    DispatchResult,
    GenerationDriverRegistry,
    GenerationPoller,
    dispatch_plan,
)
from forge_bridge.orchestration.engine import GraphEngine
from forge_bridge.orchestration.event_consumer import GraphEngineEventConsumer
from forge_bridge.store.models import DBEntity, DBEvent
from forge_bridge.store.orch_execution_plan_repo import ExecutionPlanRepo
from forge_bridge.store.orch_execution_result_repo import ExecutionResultRepo
from forge_bridge.store.orch_generation_artifact_repo import GenerationArtifactRepo
from forge_bridge.store.orch_pipeline_run_repo import PipelineRunRepo
from forge_bridge.store.orchestration_lifecycle_state_repo import (
    OrchestrationLifecycleStateRepo,
)
from forge_bridge.store.repo import EventRepo

from tests.test_phase7_generation_vertical import (
    _BACKEND_ID,
    _TRIPLE,
    FaithfulLifecycleDriver,
    _ratified_grant_id,
)


def _generation_step() -> dict:
    return {
        "operator_id": "generate_video_from_image",
        "backend_id": _BACKEND_ID,
        "inputs": [],
        "output_artifact_id": str(uuid.uuid4()),
    }


def _perception_step(
    *,
    step_id: str = "vision-check",
    disposition: str = "candidate",
) -> dict:
    return {
        "step_id": step_id,
        "operator_id": "vision_content_policy_check",
        "family": "perception",
        "payload_family": "perception_v1",
        "disposition": disposition,
        "result_payload": {"label": "safe", "confidence": 0.98},
    }


def _plan_body(operator_sequence: list[dict]) -> dict:
    return {
        "operator_sequence": operator_sequence,
        "backend_assignments": {
            step["operator_id"]: step.get("backend_id")
            for step in operator_sequence
            if step.get("backend_id")
        },
        "transforms_inserted": [],
        "external_uploads_required": [],
        "cost_estimate": {},
        "predicted_compromise_consumption": [],
        "provenance_obligations": [],
        "feasibility_verdict": "feasible",
        "feasibility_explanation": "",
        "refusal_code": None,
        "intent_id": str(uuid.uuid4()),
        "planner_version": "phase7-v4-test",
        "capability_snapshot_id": None,
        "rule_snapshot_id": str(uuid.uuid4()),
        "partial_fidelity_snapshot_id": str(uuid.uuid4()),
    }


async def _seed_execution_run(session_factory, operator_sequence: list[dict]):
    async with session_factory() as session:
        plan = await ExecutionPlanRepo(session).insert_if_absent(
            _plan_body(operator_sequence)
        )
        run = await PipelineRunRepo(session).insert_if_absent(
            {"run_kind": "phase7-v4-test", "intent_id": str(uuid.uuid4())}
        )
        run_id = run.id
        engine = GraphEngine(session)
        await engine.create_run(
            run_id=run_id,
            shot_id=uuid.uuid4(),
            initial_stage="routing",
        )
        await engine.transition(run_id, to_stage="execution", plan_id=plan.id)
        await session.commit()
        return run_id, plan


def _db_event_appender(session_factory) -> Callable[[str, dict], Awaitable[None]]:
    async def append(event_type: str, payload: dict) -> None:
        run_raw = payload.get("run_id")
        entity_id = uuid.UUID(str(run_raw)) if run_raw else None
        async with session_factory() as session:
            await EventRepo(session).append(event_type, payload, entity_id=entity_id)
            await session.commit()

    return append


async def _consume_pending(session_factory):
    async with session_factory() as session:
        engine = GraphEngine(session)
        consumer = GraphEngineEventConsumer(session, graph_engine=engine)
        results = await consumer.process_pending()
        await session.commit()
        return results


async def _consume_after(session_factory, event_id: uuid.UUID):
    async with session_factory() as session:
        engine = GraphEngine(session)
        consumer = GraphEngineEventConsumer(session, graph_engine=engine)
        results = await consumer.process_pending(after_event_id=event_id)
        await session.commit()
        return results


async def test_sync_perception_result_advances_only_after_consumer(
    session_factory,
) -> None:
    run_id, plan = await _seed_execution_run(session_factory, [_perception_step()])

    result = await dispatch_plan(
        plan,
        driver_registry=GenerationDriverRegistry(),
        session_factory=session_factory,
        event_appender=_db_event_appender(session_factory),
        run_id=run_id,
    )

    assert result == DispatchResult(
        status="completed",
        execution_result_ids=result.execution_result_ids,
    )
    assert len(result.execution_result_ids) == 1

    async with session_factory() as session:
        lifecycle = await OrchestrationLifecycleStateRepo(session).get_by_run_id(run_id)
        assert lifecycle is not None
        assert lifecycle.current_stage == "execution"

        artifact_rows = await session.execute(
            select(DBEntity).where(DBEntity.entity_type == "orch_generation_artifact")
        )
        assert list(artifact_rows.scalars().all()) == []

        execution_results = await ExecutionResultRepo(session).list_for_run(run_id)
        assert len(execution_results) == 1
        assert execution_results[0].family == "perception"
        assert execution_results[0].disposition == "candidate"

        events = await session.execute(select(DBEvent))
        event_types = {event.event_type for event in events.scalars().all()}
        assert "execution_step_terminal" in event_types
        assert "generation_artifact_terminal" not in event_types
        assert "engine_consumer_advanced" not in event_types

    consume_results = await _consume_pending(session_factory)
    advanced = [r for r in consume_results if r.action == "advanced_to_audit"]
    assert len(advanced) == 1
    assert advanced[0].candidates_count == 1

    async with session_factory() as session:
        lifecycle = await OrchestrationLifecycleStateRepo(session).get_by_run_id(run_id)
        assert lifecycle is not None
        assert lifecycle.current_stage == "audit"


async def test_mixed_generation_and_perception_partition_advances_together(
    session_factory,
) -> None:
    driver = FaithfulLifecycleDriver()
    registry = GenerationDriverRegistry()
    registry.register_driver(driver)
    run_id, plan = await _seed_execution_run(
        session_factory,
        [_generation_step(), _perception_step()],
    )

    grant_id = await _ratified_grant_id(session_factory)
    dispatch = await dispatch_plan(
        plan,
        driver_registry=registry,
        session_factory=session_factory,
        event_appender=_db_event_appender(session_factory),
        run_id=run_id,
        grant_id=grant_id,
    )
    assert dispatch.status == "submitted"
    assert dispatch.artifact_id is not None
    assert len(dispatch.execution_result_ids) == 1

    first_pass = await _consume_pending(session_factory)
    waiting = [r for r in first_pass if r.action == "waiting_on_more_artifacts"]
    assert len(waiting) == 1
    assert waiting[0].candidates_count == 1
    assert waiting[0].in_flight_count == 1

    poll = await GenerationPoller(session_factory, registry).poll_once()
    assert poll.terminal == 1

    second_pass = await _consume_after(session_factory, first_pass[-1].event_id)
    advanced = [r for r in second_pass if r.action == "advanced_to_audit"]
    assert len(advanced) == 1
    assert advanced[0].candidates_count == 2
    assert advanced[0].diagnostics_count == 0

    async with session_factory() as session:
        lifecycle = await OrchestrationLifecycleStateRepo(session).get_by_run_id(run_id)
        assert lifecycle is not None
        assert lifecycle.current_stage == "audit"

        artifacts = await session.execute(
            select(DBEntity).where(DBEntity.entity_type == "orch_generation_artifact")
        )
        artifact_rows = list(artifacts.scalars().all())
        assert len(artifact_rows) == 1
        artifact = await GenerationArtifactRepo(session).get_by_id(artifact_rows[0].id)
        assert artifact is not None
        assert artifact.lifecycle_state == "complete"
        assert artifact.execution_provenance["backend_identity_triple"] == _TRIPLE

        execution_results = await ExecutionResultRepo(session).list_for_run(run_id)
        assert len(execution_results) == 1
        assert execution_results[0].family == "perception"

        events = await session.execute(select(DBEvent))
        event_types = {event.event_type for event in events.scalars().all()}
        assert {
            "execution_step_terminal",
            "generation_artifact_terminal",
            "engine_consumer_advanced",
        } <= event_types
