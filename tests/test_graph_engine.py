"""Tests for GraphEngine (Phase 4B Step 6)."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import select

from forge_bridge.orchestration import (
    DecisionNotAllowedAtStageError,
    GraphEngine,
    InvalidStageTransitionError,
    InvalidStatusTransitionError,
    LifecycleStateAlreadyExistsError,
    LifecycleStateNotFoundError,
    UnknownDecisionEventError,
)
from forge_bridge.store.errors import LifecycleConsistencyError
from forge_bridge.store.models import DBEntity, DBEvent, DBOrchestrationLifecycleState
from forge_bridge.store.orchestration_lifecycle_state_repo import (
    OrchestrationLifecycleStateRepo,
)
from forge_bridge.store.repo import EventRepo


async def _insert_run_entity(session, run_id: uuid.UUID | None = None) -> uuid.UUID:
    run_id = run_id or uuid.uuid4()
    session.add(
        DBEntity(
            id=run_id,
            entity_type="orch_pipeline_run",
            content_hash=f"run-{run_id.hex}",
            attributes={"run_kind": "original"},
        )
    )
    await session.flush()
    return run_id


async def _events_for_run(session, run_id: uuid.UUID) -> list[DBEvent]:
    result = await session.execute(
        select(DBEvent)
        .where(DBEvent.entity_id == run_id)
        .order_by(DBEvent.occurred_at.asc())
    )
    return list(result.scalars().all())


async def _create_run(
    session,
    *,
    run_id: uuid.UUID | None = None,
    shot_id: uuid.UUID | None = None,
) -> tuple[uuid.UUID, uuid.UUID]:
    run_id = run_id or uuid.uuid4()
    shot_id = shot_id or uuid.uuid4()
    await _insert_run_entity(session, run_id)
    engine = GraphEngine(session)
    await engine.create_run(run_id=run_id, shot_id=shot_id)
    return run_id, shot_id


# ── create_run ──────────────────────────────────────────────────────────────


async def test_create_run_inserts_lifecycle_and_run_created_event(
    session_factory,
) -> None:
    run_id = uuid.uuid4()
    shot_id = uuid.uuid4()

    async with session_factory() as session:
        await _insert_run_entity(session, run_id)
        engine = GraphEngine(session)
        row = await engine.create_run(run_id=run_id, shot_id=shot_id)
        await session.commit()

    assert row.current_stage == "ingest"
    assert row.status == "active"
    assert row.last_event_id is not None

    async with session_factory() as session:
        lifecycle = OrchestrationLifecycleStateRepo(session)
        fetched = await lifecycle.get_by_run_id(run_id)
        assert fetched is not None
        events = await _events_for_run(session, run_id)
        assert len(events) == 1
        assert events[0].event_type == "run_created"
        assert events[0].id == fetched.last_event_id
        assert events[0].payload["initial_stage"] == "ingest"


async def test_create_run_collision_raises(session_factory) -> None:
    run_id = uuid.uuid4()
    shot_id = uuid.uuid4()

    async with session_factory() as session:
        await _insert_run_entity(session, run_id)
        engine = GraphEngine(session)
        await engine.create_run(run_id=run_id, shot_id=shot_id)
        with pytest.raises(LifecycleStateAlreadyExistsError):
            await engine.create_run(run_id=run_id, shot_id=shot_id)


# ── transition — legal stage sequence ───────────────────────────────────────


async def test_transition_full_happy_path_stage_sequence(session_factory) -> None:
    run_id = uuid.uuid4()
    shot_id = uuid.uuid4()
    intent_id = uuid.uuid4()
    promoted_id = uuid.uuid4()

    async with session_factory() as session:
        await _insert_run_entity(session, run_id)
        engine = GraphEngine(session)
        await engine.create_run(run_id=run_id, shot_id=shot_id)

        await engine.transition(run_id, to_stage="spec_convergence")
        await engine.apply_decision_event(
            run_id,
            "lock_intent",
            {"intent_id": str(intent_id)},
        )
        for stage in ("execution", "audit"):
            await engine.transition(run_id, to_stage=stage)
        await engine.apply_decision_event(
            run_id,
            "promote_candidate",
            {"promoted_artifact_id": str(promoted_id)},
        )
        await engine.transition(run_id, to_stage="publish")
        final = await engine.transition(run_id, to_status="completed")
        await session.commit()

    assert final.current_stage == "publish"
    assert final.status == "completed"
    assert final.intent_id == intent_id
    assert final.current_canonical == promoted_id

    async with session_factory() as session:
        events = await _events_for_run(session, run_id)
        types = [e.event_type for e in events]
        assert types[0] == "run_created"
        assert "stage_advanced" in types
        assert "lock_intent" in types
        assert "promote_candidate" in types
        assert types[-1] == "status_changed"

        lifecycle = OrchestrationLifecycleStateRepo(session)
        row = await lifecycle.get_by_run_id(run_id)
        assert row is not None
        assert row.last_event_id == events[-1].id


async def test_transition_advances_last_event_id_each_time(session_factory) -> None:
    async with session_factory() as session:
        run_id, _ = await _create_run(session)
        engine = GraphEngine(session)
        prev = (await OrchestrationLifecycleStateRepo(session).get_by_run_id(run_id)).last_event_id

        row = await engine.transition(run_id, to_stage="spec_convergence")
        await session.commit()

    assert row.last_event_id != prev
    async with session_factory() as session:
        events = await _events_for_run(session, run_id)
        assert events[-1].event_type == "stage_advanced"
        assert events[-1].id == row.last_event_id


# ── transition — invalid stage transitions ──────────────────────────────────


async def test_transition_ingest_to_audit_raises(session_factory) -> None:
    async with session_factory() as session:
        run_id, _ = await _create_run(session)
        engine = GraphEngine(session)
        with pytest.raises(InvalidStageTransitionError) as exc:
            await engine.transition(run_id, to_stage="audit")
        assert exc.value.from_stage == "ingest"
        assert exc.value.to_stage == "audit"


async def test_transition_backward_audit_to_routing_raises(session_factory) -> None:
    async with session_factory() as session:
        run_id, _ = await _create_run(session)
        engine = GraphEngine(session)
        await engine.transition(run_id, to_stage="spec_convergence")
        await engine.apply_decision_event(
            run_id, "lock_intent", {"intent_id": str(uuid.uuid4())}
        )
        for stage in ("execution", "audit"):
            await engine.transition(run_id, to_stage=stage)
        with pytest.raises(InvalidStageTransitionError) as exc:
            await engine.transition(run_id, to_stage="routing")
        assert exc.value.from_stage == "audit"
        assert exc.value.to_stage == "routing"


async def test_transition_same_stage_no_op_raises(session_factory) -> None:
    async with session_factory() as session:
        run_id, _ = await _create_run(session)
        engine = GraphEngine(session)
        with pytest.raises(InvalidStageTransitionError):
            await engine.transition(run_id, to_stage="ingest")


# ── transition — status & block semantics ───────────────────────────────────


async def test_transition_active_to_paused_requires_block(session_factory) -> None:
    async with session_factory() as session:
        run_id, _ = await _create_run(session)
        engine = GraphEngine(session)
        with pytest.raises(LifecycleConsistencyError):
            await engine.transition(run_id, to_status="paused")


async def test_transition_active_to_paused_with_block(session_factory) -> None:
    async with session_factory() as session:
        run_id, _ = await _create_run(session)
        engine = GraphEngine(session)
        row = await engine.transition(
            run_id,
            to_status="paused",
            block={"kind": "awaiting_review"},
        )
        await session.commit()

    assert row.status == "paused"
    assert row.block == {"kind": "awaiting_review"}


async def test_transition_paused_to_active_requires_clear_block(session_factory) -> None:
    async with session_factory() as session:
        run_id, _ = await _create_run(session)
        engine = GraphEngine(session)
        await engine.transition(
            run_id,
            to_status="paused",
            block={"kind": "hold"},
        )
        with pytest.raises(LifecycleConsistencyError):
            await engine.transition(run_id, to_status="active")


async def test_transition_paused_to_active_with_clear_block(session_factory) -> None:
    async with session_factory() as session:
        run_id, _ = await _create_run(session)
        engine = GraphEngine(session)
        await engine.transition(
            run_id,
            to_status="paused",
            block={"kind": "hold"},
        )
        row = await engine.transition(
            run_id,
            to_status="active",
            clear_block=True,
        )
        await session.commit()

    assert row.status == "active"
    assert row.block is None


async def test_transition_cancelled_from_any_active_stage(session_factory) -> None:
    async with session_factory() as session:
        run_id, _ = await _create_run(session)
        engine = GraphEngine(session)
        await engine.transition(run_id, to_stage="spec_convergence")
        row = await engine.transition(run_id, to_status="cancelled")
        await session.commit()

    assert row.current_stage == "spec_convergence"
    assert row.status == "cancelled"


async def test_transition_completed_only_from_publish(session_factory) -> None:
    async with session_factory() as session:
        run_id, _ = await _create_run(session)
        engine = GraphEngine(session)
        with pytest.raises(InvalidStatusTransitionError):
            await engine.transition(run_id, to_status="completed")


async def test_transition_failed_from_active(session_factory) -> None:
    async with session_factory() as session:
        run_id, _ = await _create_run(session)
        engine = GraphEngine(session)
        row = await engine.transition(run_id, to_status="failed")
        await session.commit()

    assert row.status == "failed"


# ── apply_decision_event ────────────────────────────────────────────────────


async def test_decision_lock_intent_at_spec_convergence(session_factory) -> None:
    intent_id = uuid.uuid4()
    async with session_factory() as session:
        run_id, _ = await _create_run(session)
        engine = GraphEngine(session)
        await engine.transition(run_id, to_stage="spec_convergence")
        row = await engine.apply_decision_event(
            run_id,
            "lock_intent",
            {"intent_id": str(intent_id)},
        )
        await session.commit()

    assert row.current_stage == "routing"
    assert row.intent_id == intent_id
    async with session_factory() as session:
        events = await _events_for_run(session, run_id)
        assert any(e.event_type == "lock_intent" for e in events)


async def test_decision_lock_intent_wrong_stage_raises(session_factory) -> None:
    async with session_factory() as session:
        run_id, _ = await _create_run(session)
        engine = GraphEngine(session)
        await engine.transition(run_id, to_stage="spec_convergence")
        await engine.apply_decision_event(
            run_id, "lock_intent", {"intent_id": str(uuid.uuid4())}
        )
        with pytest.raises(DecisionNotAllowedAtStageError):
            await engine.apply_decision_event(
                run_id, "lock_intent", {"intent_id": str(uuid.uuid4())}
            )


async def test_decision_promote_candidate_at_audit(session_factory) -> None:
    promoted_id = uuid.uuid4()
    async with session_factory() as session:
        run_id, _ = await _create_run(session)
        engine = GraphEngine(session)
        await engine.transition(run_id, to_stage="spec_convergence")
        await engine.apply_decision_event(
            run_id, "lock_intent", {"intent_id": str(uuid.uuid4())}
        )
        for stage in ("execution", "audit"):
            await engine.transition(run_id, to_stage=stage)
        row = await engine.apply_decision_event(
            run_id,
            "promote_candidate",
            {"promoted_artifact_id": str(promoted_id)},
        )
        await session.commit()

    assert row.current_stage == "promotion"
    assert row.current_canonical == promoted_id


async def test_decision_promote_candidate_wrong_stage_raises(session_factory) -> None:
    async with session_factory() as session:
        run_id, _ = await _create_run(session)
        engine = GraphEngine(session)
        await engine.transition(run_id, to_stage="spec_convergence")
        await engine.apply_decision_event(
            run_id, "lock_intent", {"intent_id": str(uuid.uuid4())}
        )
        await engine.transition(run_id, to_stage="execution")
        with pytest.raises(DecisionNotAllowedAtStageError):
            await engine.apply_decision_event(
                run_id,
                "promote_candidate",
                {"promoted_artifact_id": str(uuid.uuid4())},
            )


async def test_decision_cancel_run(session_factory) -> None:
    async with session_factory() as session:
        run_id, _ = await _create_run(session)
        engine = GraphEngine(session)
        row = await engine.apply_decision_event(run_id, "cancel_run", {})
        await session.commit()

    assert row.status == "cancelled"
    async with session_factory() as session:
        events = await _events_for_run(session, run_id)
        assert events[-1].event_type == "cancel_run"


async def test_decision_cancel_run_already_cancelled_raises(session_factory) -> None:
    async with session_factory() as session:
        run_id, _ = await _create_run(session)
        engine = GraphEngine(session)
        await engine.apply_decision_event(run_id, "cancel_run", {})
        with pytest.raises(InvalidStatusTransitionError):
            await engine.apply_decision_event(run_id, "cancel_run", {})


async def test_decision_approve_remediation_records_event_no_transition(
    session_factory,
) -> None:
    async with session_factory() as session:
        run_id, _ = await _create_run(session)
        engine = GraphEngine(session)
        before = await OrchestrationLifecycleStateRepo(session).get_by_run_id(run_id)
        await engine.transition(
            run_id,
            to_status="paused",
            block={"kind": "remediation_pending"},
        )
        row = await engine.apply_decision_event(
            run_id,
            "approve_remediation",
            {"approved_by": "operator"},
        )
        await session.commit()

    assert row.current_stage == before.current_stage
    assert row.status == "paused"
    assert row.block == {"kind": "remediation_pending"}
    async with session_factory() as session:
        events = await _events_for_run(session, run_id)
        assert any(e.event_type == "approve_remediation" for e in events)


async def test_decision_unknown_type_raises(session_factory) -> None:
    async with session_factory() as session:
        run_id, _ = await _create_run(session)
        engine = GraphEngine(session)
        with pytest.raises(UnknownDecisionEventError):
            await engine.apply_decision_event(run_id, "mystery_decision", {})


async def test_transition_missing_run_raises(session_factory) -> None:
    async with session_factory() as session:
        engine = GraphEngine(session)
        with pytest.raises(LifecycleStateNotFoundError):
            await engine.transition(uuid.uuid4(), to_stage="spec_convergence")


# ── single-transaction atomicity ────────────────────────────────────────────


async def test_transition_rolls_back_lifecycle_when_event_append_fails(
    session_factory,
) -> None:
    run_id = uuid.uuid4()
    shot_id = uuid.uuid4()

    async with session_factory() as session:
        await _insert_run_entity(session, run_id)
        engine = GraphEngine(session)
        await engine.create_run(run_id=run_id, shot_id=shot_id)
        await session.commit()

    async with session_factory() as session:
        engine = GraphEngine(session)
        repo = OrchestrationLifecycleStateRepo(session)

        real_append = EventRepo.append

        async def append_then_fail(self, *args, **kwargs):
            result = await real_append(self, *args, **kwargs)
            raise RuntimeError("simulated event append failure")

        with patch.object(EventRepo, "append", append_then_fail):
            with pytest.raises(RuntimeError):
                await engine.transition(run_id, to_stage="spec_convergence")
        await session.rollback()

    async with session_factory() as session:
        row = await OrchestrationLifecycleStateRepo(session).get_by_run_id(run_id)
        assert row is not None
        assert row.current_stage == "ingest"
        events = await _events_for_run(session, run_id)
        assert len(events) == 1
        assert events[0].event_type == "run_created"


# ── caller-owned transaction ────────────────────────────────────────────────


async def test_caller_commits_multiple_transitions_once(session_factory) -> None:
    run_id = uuid.uuid4()
    shot_id = uuid.uuid4()

    async with session_factory() as session:
        await _insert_run_entity(session, run_id)
        engine = GraphEngine(session)
        await engine.create_run(run_id=run_id, shot_id=shot_id)
        await engine.transition(run_id, to_stage="spec_convergence")
        intent = uuid.uuid4()
        await engine.transition(run_id, intent_id=intent)

        visible_in_tx = await OrchestrationLifecycleStateRepo(session).get_by_run_id(
            run_id
        )
        assert visible_in_tx is not None
        assert visible_in_tx.current_stage == "spec_convergence"
        assert visible_in_tx.intent_id == intent
        await session.commit()

    async with session_factory() as session:
        row = await OrchestrationLifecycleStateRepo(session).get_by_run_id(run_id)
        assert row is not None
        assert row.current_stage == "spec_convergence"
        assert row.intent_id == intent
        events = await _events_for_run(session, run_id)
        assert len(events) >= 3


async def test_uncommitted_transitions_not_visible_outside_session(
    session_factory,
) -> None:
    run_id = uuid.uuid4()
    shot_id = uuid.uuid4()

    async with session_factory() as session:
        await _insert_run_entity(session, run_id)
        engine = GraphEngine(session)
        await engine.create_run(run_id=run_id, shot_id=shot_id)
        await engine.transition(run_id, to_stage="spec_convergence")

    async with session_factory() as session:
        row = await OrchestrationLifecycleStateRepo(session).get_by_run_id(run_id)
        assert row is None
