"""Tests for OrchestrationLifecycleStateRepo."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

import pytest

from forge_bridge.store.errors import LifecycleConsistencyError, MultipleActiveRunsError
from forge_bridge.store.models import DBEntity, DBOrchestrationLifecycleState
from forge_bridge.store.orchestration_lifecycle_state_repo import (
    OrchestrationLifecycleStateRepo,
)


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


async def test_lifecycle_insert_and_get_roundtrip(session_factory) -> None:
    run_id = uuid.uuid4()
    shot_id = uuid.uuid4()

    async with session_factory() as session:
        await _insert_run_entity(session, run_id)
        repo = OrchestrationLifecycleStateRepo(session)
        inserted = await repo.insert(
            run_id=run_id,
            shot_id=shot_id,
            current_stage="ingest",
        )
        await session.commit()

    async with session_factory() as session:
        repo = OrchestrationLifecycleStateRepo(session)
        fetched = await repo.get_by_run_id(run_id)
        assert fetched is not None
        assert fetched.run_id == inserted.run_id
        assert fetched.shot_id == shot_id
        assert fetched.current_stage == "ingest"
        assert fetched.status == "active"


async def test_lifecycle_update_state_selective_fields(session_factory) -> None:
    run_id = uuid.uuid4()
    shot_id = uuid.uuid4()
    intent_id = uuid.uuid4()
    plan_id = uuid.uuid4()
    canonical_id = uuid.uuid4()
    event_id = uuid.uuid4()

    async with session_factory() as session:
        await _insert_run_entity(session, run_id)
        repo = OrchestrationLifecycleStateRepo(session)
        await repo.insert(run_id=run_id, shot_id=shot_id, current_stage="ingest")
        updated = await repo.update_state(
            run_id,
            current_stage="execution",
            status="paused",
            intent_id=intent_id,
            plan_id=plan_id,
            current_canonical=canonical_id,
            last_event_id=event_id,
            block={"kind": "awaiting_review"},
        )
        await session.commit()

        assert updated.current_stage == "execution"
        assert updated.status == "paused"
        assert updated.intent_id == intent_id
        assert updated.plan_id == plan_id
        assert updated.current_canonical == canonical_id
        assert updated.last_event_id == event_id
        assert updated.block == {"kind": "awaiting_review"}


async def test_lifecycle_clear_block(session_factory) -> None:
    run_id = uuid.uuid4()
    shot_id = uuid.uuid4()

    async with session_factory() as session:
        await _insert_run_entity(session, run_id)
        repo = OrchestrationLifecycleStateRepo(session)
        await repo.insert(
            run_id=run_id,
            shot_id=shot_id,
            current_stage="ingest",
            status="paused",
            block={"reason": "hold"},
        )
        updated = await repo.update_state(
            run_id,
            status="active",
            clear_block=True,
        )
        await session.commit()
        assert updated.status == "active"
        assert updated.block is None


async def test_lifecycle_block_unchanged_when_not_provided(session_factory) -> None:
    run_id = uuid.uuid4()
    shot_id = uuid.uuid4()

    async with session_factory() as session:
        await _insert_run_entity(session, run_id)
        repo = OrchestrationLifecycleStateRepo(session)
        await repo.insert(
            run_id=run_id,
            shot_id=shot_id,
            current_stage="ingest",
            status="paused",
            block={"reason": "hold"},
        )
        updated = await repo.update_state(run_id, current_stage="routing")
        await session.commit()
        assert updated.block == {"reason": "hold"}


@pytest.mark.parametrize(
    "status,block",
    [
        ("paused", None),
        ("active", {"reason": "unexpected"}),
    ],
)
async def test_lifecycle_insert_block_consistency_errors(
    session_factory,
    status,
    block,
) -> None:
    run_id = uuid.uuid4()

    async with session_factory() as session:
        await _insert_run_entity(session, run_id)
        repo = OrchestrationLifecycleStateRepo(session)
        with pytest.raises(LifecycleConsistencyError):
            await repo.insert(
                run_id=run_id,
                shot_id=uuid.uuid4(),
                current_stage="ingest",
                status=status,
                block=block,
            )


async def test_lifecycle_insert_paused_with_block_succeeds(session_factory) -> None:
    run_id = uuid.uuid4()

    async with session_factory() as session:
        await _insert_run_entity(session, run_id)
        repo = OrchestrationLifecycleStateRepo(session)
        row = await repo.insert(
            run_id=run_id,
            shot_id=uuid.uuid4(),
            current_stage="ingest",
            status="paused",
            block={"kind": "blocked"},
        )
        await session.commit()
        assert row.status == "paused"
        assert row.block == {"kind": "blocked"}


async def test_lifecycle_update_active_to_paused_requires_block(session_factory) -> None:
    run_id = uuid.uuid4()

    async with session_factory() as session:
        await _insert_run_entity(session, run_id)
        repo = OrchestrationLifecycleStateRepo(session)
        await repo.insert(run_id=run_id, shot_id=uuid.uuid4(), current_stage="ingest")
        with pytest.raises(LifecycleConsistencyError):
            await repo.update_state(run_id, status="paused")


async def test_lifecycle_update_paused_to_active_requires_clear_block(
    session_factory,
) -> None:
    run_id = uuid.uuid4()

    async with session_factory() as session:
        await _insert_run_entity(session, run_id)
        repo = OrchestrationLifecycleStateRepo(session)
        await repo.insert(
            run_id=run_id,
            shot_id=uuid.uuid4(),
            current_stage="ingest",
            status="paused",
            block={"kind": "blocked"},
        )
        with pytest.raises(LifecycleConsistencyError):
            await repo.update_state(run_id, status="active")


async def test_lifecycle_find_active(session_factory) -> None:
    active_run = uuid.uuid4()
    completed_run = uuid.uuid4()
    shot_a = uuid.uuid4()
    shot_b = uuid.uuid4()

    async with session_factory() as session:
        await _insert_run_entity(session, active_run)
        await _insert_run_entity(session, completed_run)
        repo = OrchestrationLifecycleStateRepo(session)
        await repo.insert(run_id=active_run, shot_id=shot_a, current_stage="ingest")
        await repo.insert(
            run_id=completed_run,
            shot_id=shot_b,
            current_stage="publish",
            status="completed",
        )
        await session.commit()

    async with session_factory() as session:
        repo = OrchestrationLifecycleStateRepo(session)
        active_rows = await repo.find_active()
        assert {row.run_id for row in active_rows} == {active_run}


async def test_lifecycle_find_active_for_shot(session_factory) -> None:
    run_id = uuid.uuid4()
    shot_id = uuid.uuid4()

    async with session_factory() as session:
        await _insert_run_entity(session, run_id)
        repo = OrchestrationLifecycleStateRepo(session)
        await repo.insert(run_id=run_id, shot_id=shot_id, current_stage="ingest")
        await session.commit()

    async with session_factory() as session:
        repo = OrchestrationLifecycleStateRepo(session)
        found = await repo.find_active_for_shot(shot_id)
        assert found is not None
        assert found.run_id == run_id
        assert await repo.find_active_for_shot(uuid.uuid4()) is None


async def test_lifecycle_multiple_active_runs_error(session_factory) -> None:
    shot_id = uuid.uuid4()
    run_a = uuid.uuid4()
    run_b = uuid.uuid4()
    now = datetime.now(timezone.utc)

    async with session_factory() as session:
        await _insert_run_entity(session, run_a)
        await _insert_run_entity(session, run_b)
        session.add_all(
            [
                DBOrchestrationLifecycleState(
                    run_id=run_a,
                    shot_id=shot_id,
                    current_stage="ingest",
                    stage_entered_at=now,
                    status="active",
                ),
                DBOrchestrationLifecycleState(
                    run_id=run_b,
                    shot_id=shot_id,
                    current_stage="ingest",
                    stage_entered_at=now,
                    status="active",
                ),
            ]
        )
        await session.commit()

    async with session_factory() as session:
        repo = OrchestrationLifecycleStateRepo(session)
        with pytest.raises(MultipleActiveRunsError):
            await repo.find_active_for_shot(shot_id)


async def test_lifecycle_updated_at_advances(session_factory) -> None:
    run_id = uuid.uuid4()

    async with session_factory() as session:
        await _insert_run_entity(session, run_id)
        repo = OrchestrationLifecycleStateRepo(session)
        row = await repo.insert(run_id=run_id, shot_id=uuid.uuid4(), current_stage="ingest")
        original_updated = row.updated_at
        await asyncio.sleep(0.01)
        updated = await repo.update_state(run_id, current_stage="routing")
        await session.commit()
        assert updated.updated_at >= original_updated


async def test_lifecycle_invalid_stage_and_status_rejected(session_factory) -> None:
    run_id = uuid.uuid4()

    async with session_factory() as session:
        await _insert_run_entity(session, run_id)
        repo = OrchestrationLifecycleStateRepo(session)
        with pytest.raises(ValueError, match="current_stage"):
            await repo.insert(
                run_id=run_id,
                shot_id=uuid.uuid4(),
                current_stage="invalid_stage",
            )
        with pytest.raises(ValueError, match="status"):
            await repo.insert(
                run_id=run_id,
                shot_id=uuid.uuid4(),
                current_stage="ingest",
                status="invalid_status",
            )
