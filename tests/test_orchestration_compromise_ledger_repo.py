"""Tests for OrchestrationCompromiseLedgerRepo."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from forge_bridge.store.errors import AppendOnlyLedgerError
from forge_bridge.store.orchestration_compromise_ledger_repo import (
    OrchestrationCompromiseLedgerRepo,
)


async def test_compromise_insert_roundtrips(session_factory) -> None:
    intent_id = uuid.uuid4()
    run_id = uuid.uuid4()
    plan_id = uuid.uuid4()
    artifact_id = uuid.uuid4()

    async with session_factory() as session:
        repo = OrchestrationCompromiseLedgerRepo(session)
        planned = await repo.insert_planned_predicted(
            intent_id=intent_id,
            run_id=run_id,
            plan_id=plan_id,
            criterion_id="motion_arc",
            dimension="dynamic_range",
            magnitude={"scalar": 0.3},
        )
        actual = await repo.insert_audit_actual(
            intent_id=intent_id,
            run_id=run_id,
            artifact_id=artifact_id,
            criterion_id="motion_arc",
            dimension="dynamic_range",
            magnitude={"scalar": 0.5},
        )
        await session.commit()

        assert planned.side == "planned_predicted"
        assert actual.side == "audit_actual"
        assert actual.artifact_id == artifact_id


async def test_compromise_get_entries_ordered(session_factory) -> None:
    intent_id = uuid.uuid4()
    run_id = uuid.uuid4()
    base = datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc)

    async with session_factory() as session:
        repo = OrchestrationCompromiseLedgerRepo(session)
        await repo.insert_audit_actual(
            intent_id=intent_id,
            run_id=run_id,
            artifact_id=uuid.uuid4(),
            criterion_id="motion_arc",
            dimension="dynamic_range",
            magnitude={"scalar": 0.2},
            recorded_at=base,
        )
        await repo.insert_audit_actual(
            intent_id=intent_id,
            run_id=run_id,
            artifact_id=uuid.uuid4(),
            criterion_id="timing",
            dimension="beat_alignment",
            magnitude={"scalar": 0.1},
            recorded_at=base + timedelta(minutes=1),
        )
        await session.commit()

    async with session_factory() as session:
        entries = await OrchestrationCompromiseLedgerRepo(session).get_entries(intent_id)
        assert len(entries) == 2
        assert entries[0].criterion_id == "motion_arc"
        assert entries[1].criterion_id == "timing"


async def test_compromise_get_entries_filter_criterion(session_factory) -> None:
    intent_id = uuid.uuid4()

    async with session_factory() as session:
        repo = OrchestrationCompromiseLedgerRepo(session)
        await repo.insert_audit_actual(
            intent_id=intent_id,
            run_id=uuid.uuid4(),
            artifact_id=uuid.uuid4(),
            criterion_id="motion_arc",
            dimension="dynamic_range",
            magnitude={"scalar": 0.2},
        )
        await repo.insert_audit_actual(
            intent_id=intent_id,
            run_id=uuid.uuid4(),
            artifact_id=uuid.uuid4(),
            criterion_id="timing",
            dimension="beat_alignment",
            magnitude={"scalar": 0.1},
        )
        await session.commit()

    async with session_factory() as session:
        entries = await OrchestrationCompromiseLedgerRepo(session).get_entries(
            intent_id,
            criterion_id="motion_arc",
        )
        assert len(entries) == 1
        assert entries[0].criterion_id == "motion_arc"


async def test_compromise_get_entries_filter_side(session_factory) -> None:
    intent_id = uuid.uuid4()
    run_id = uuid.uuid4()
    plan_id = uuid.uuid4()

    async with session_factory() as session:
        repo = OrchestrationCompromiseLedgerRepo(session)
        await repo.insert_planned_predicted(
            intent_id=intent_id,
            run_id=run_id,
            plan_id=plan_id,
            criterion_id="motion_arc",
            dimension="dynamic_range",
            magnitude={"scalar": 0.3},
        )
        await repo.insert_audit_actual(
            intent_id=intent_id,
            run_id=run_id,
            artifact_id=uuid.uuid4(),
            criterion_id="motion_arc",
            dimension="dynamic_range",
            magnitude={"scalar": 0.5},
        )
        await session.commit()

    async with session_factory() as session:
        repo = OrchestrationCompromiseLedgerRepo(session)
        planned = await repo.get_entries(intent_id, side="planned_predicted")
        actual = await repo.get_entries(intent_id, side="audit_actual")
        assert len(planned) == 1
        assert len(actual) == 1


async def test_compromise_get_entries_filter_all_dimensions(session_factory) -> None:
    intent_id = uuid.uuid4()

    async with session_factory() as session:
        repo = OrchestrationCompromiseLedgerRepo(session)
        await repo.insert_audit_actual(
            intent_id=intent_id,
            run_id=uuid.uuid4(),
            artifact_id=uuid.uuid4(),
            criterion_id="motion_arc",
            dimension="dynamic_range",
            magnitude={"scalar": 0.2},
        )
        await repo.insert_audit_actual(
            intent_id=intent_id,
            run_id=uuid.uuid4(),
            artifact_id=uuid.uuid4(),
            criterion_id="motion_arc",
            dimension="timing",
            magnitude={"scalar": 0.1},
        )
        await session.commit()

    async with session_factory() as session:
        entries = await OrchestrationCompromiseLedgerRepo(session).get_entries(
            intent_id,
            criterion_id="motion_arc",
            dimension="dynamic_range",
            side="audit_actual",
        )
        assert len(entries) == 1
        assert entries[0].dimension == "dynamic_range"


async def test_compromise_multi_run_entries(session_factory) -> None:
    intent_id = uuid.uuid4()
    run_a = uuid.uuid4()
    run_b = uuid.uuid4()

    async with session_factory() as session:
        repo = OrchestrationCompromiseLedgerRepo(session)
        for run_id in (run_a, run_b, run_a):
            await repo.insert_audit_actual(
                intent_id=intent_id,
                run_id=run_id,
                artifact_id=uuid.uuid4(),
                criterion_id="motion_arc",
                dimension="dynamic_range",
                magnitude={"scalar": 0.1},
            )
        await session.commit()

    async with session_factory() as session:
        entries = await OrchestrationCompromiseLedgerRepo(session).get_entries(
            intent_id,
            criterion_id="motion_arc",
            dimension="dynamic_range",
        )
        assert len(entries) == 3
        assert {entry.run_id for entry in entries} == {run_a, run_b}


async def test_compromise_update_and_delete_refused(session_factory) -> None:
    async with session_factory() as session:
        repo = OrchestrationCompromiseLedgerRepo(session)
        row = await repo.insert_audit_actual(
            intent_id=uuid.uuid4(),
            run_id=uuid.uuid4(),
            artifact_id=uuid.uuid4(),
            criterion_id="motion_arc",
            dimension="dynamic_range",
            magnitude={"scalar": 0.2},
        )
        await session.commit()
        entry_id = row.entry_id

    async with session_factory() as session:
        repo = OrchestrationCompromiseLedgerRepo(session)
        with pytest.raises(AppendOnlyLedgerError):
            await repo.update(entry_id, magnitude={"scalar": 9})
        with pytest.raises(AppendOnlyLedgerError):
            await repo.delete(entry_id)


async def test_compromise_invalid_side_rejected(session_factory) -> None:
    async with session_factory() as session:
        repo = OrchestrationCompromiseLedgerRepo(session)
        with pytest.raises(ValueError, match="side"):
            await repo._insert_entry(
                intent_id=uuid.uuid4(),
                run_id=uuid.uuid4(),
                criterion_id="motion_arc",
                dimension="dynamic_range",
                side="invalid_side",
                magnitude={"scalar": 0.1},
            )
