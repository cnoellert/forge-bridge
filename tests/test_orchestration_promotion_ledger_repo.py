"""Tests for OrchestrationPromotionLedgerRepo."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from forge_bridge.store.errors import AppendOnlyLedgerError
from forge_bridge.store.orchestration_promotion_ledger_repo import (
    OrchestrationPromotionLedgerRepo,
)


async def test_promotion_insert_roundtrip(session_factory) -> None:
    shot_id = uuid.uuid4()
    artifact_id = uuid.uuid4()

    async with session_factory() as session:
        repo = OrchestrationPromotionLedgerRepo(session)
        row = await repo.insert_promotion(
            shot_id=shot_id,
            promoted_artifact_id=artifact_id,
            promoted_by="operator",
            rationale="audit pass",
        )
        await session.commit()
        promotion_id = row.promotion_id

    async with session_factory() as session:
        history = await OrchestrationPromotionLedgerRepo(session).get_history(shot_id)
        assert len(history) == 1
        assert history[0].promotion_id == promotion_id
        assert history[0].promoted_artifact_id == artifact_id


async def test_promotion_get_current_canonical(session_factory) -> None:
    shot_id = uuid.uuid4()
    older = uuid.uuid4()
    newer = uuid.uuid4()
    base = datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc)

    async with session_factory() as session:
        repo = OrchestrationPromotionLedgerRepo(session)
        await repo.insert_promotion(
            shot_id=shot_id,
            promoted_artifact_id=older,
            promoted_by="operator",
            rationale="first",
            promoted_at=base,
        )
        await repo.insert_promotion(
            shot_id=shot_id,
            promoted_artifact_id=newer,
            promoted_by="operator",
            rationale="second",
            promoted_at=base + timedelta(hours=1),
        )
        await session.commit()

    async with session_factory() as session:
        repo = OrchestrationPromotionLedgerRepo(session)
        current = await repo.get_current_canonical(shot_id)
        assert current is not None
        assert current.promoted_artifact_id == newer
        assert await repo.get_current_canonical(uuid.uuid4()) is None


async def test_promotion_get_canonical_at(session_factory) -> None:
    shot_id = uuid.uuid4()
    first_artifact = uuid.uuid4()
    second_artifact = uuid.uuid4()
    t0 = datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc)

    async with session_factory() as session:
        repo = OrchestrationPromotionLedgerRepo(session)
        await repo.insert_promotion(
            shot_id=shot_id,
            promoted_artifact_id=first_artifact,
            promoted_by="operator",
            rationale="first",
            promoted_at=t0,
        )
        await repo.insert_promotion(
            shot_id=shot_id,
            promoted_artifact_id=second_artifact,
            promoted_by="operator",
            rationale="second",
            promoted_at=t0 + timedelta(hours=2),
        )
        await session.commit()

    async with session_factory() as session:
        repo = OrchestrationPromotionLedgerRepo(session)
        at_first = await repo.get_canonical_at(shot_id, t0 + timedelta(minutes=30))
        at_second = await repo.get_canonical_at(shot_id, t0 + timedelta(hours=3))
        before_any = await repo.get_canonical_at(shot_id, t0 - timedelta(hours=1))

        assert at_first.promoted_artifact_id == first_artifact
        assert at_second.promoted_artifact_id == second_artifact
        assert before_any is None


async def test_promotion_get_history_newest_first(session_factory) -> None:
    shot_id = uuid.uuid4()
    base = datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc)

    async with session_factory() as session:
        repo = OrchestrationPromotionLedgerRepo(session)
        await repo.insert_promotion(
            shot_id=shot_id,
            promoted_artifact_id=uuid.uuid4(),
            promoted_by="operator",
            rationale="older",
            promoted_at=base,
        )
        await repo.insert_promotion(
            shot_id=shot_id,
            promoted_artifact_id=uuid.uuid4(),
            promoted_by="operator",
            rationale="newer",
            promoted_at=base + timedelta(hours=1),
        )
        await session.commit()

    async with session_factory() as session:
        history = await OrchestrationPromotionLedgerRepo(session).get_history(shot_id)
        assert len(history) == 2
        assert history[0].rationale == "newer"
        assert history[1].rationale == "older"


async def test_promotion_was_ever_canonical(session_factory) -> None:
    artifact_id = uuid.uuid4()

    async with session_factory() as session:
        repo = OrchestrationPromotionLedgerRepo(session)
        row = await repo.insert_promotion(
            shot_id=uuid.uuid4(),
            promoted_artifact_id=artifact_id,
            promoted_by="operator",
            rationale="promoted",
        )
        await session.commit()
        promotion_id = row.promotion_id

    async with session_factory() as session:
        repo = OrchestrationPromotionLedgerRepo(session)
        found = await repo.was_ever_canonical(artifact_id)
        assert found is not None
        assert found.promotion_id == promotion_id
        assert await repo.was_ever_canonical(uuid.uuid4()) is None


async def test_promotion_update_and_delete_refused(session_factory) -> None:
    async with session_factory() as session:
        repo = OrchestrationPromotionLedgerRepo(session)
        row = await repo.insert_promotion(
            shot_id=uuid.uuid4(),
            promoted_artifact_id=uuid.uuid4(),
            promoted_by="operator",
            rationale="once",
        )
        await session.commit()
        promotion_id = row.promotion_id

    async with session_factory() as session:
        repo = OrchestrationPromotionLedgerRepo(session)
        with pytest.raises(AppendOnlyLedgerError):
            await repo.update(promotion_id, rationale="tampered")
        with pytest.raises(AppendOnlyLedgerError):
            await repo.delete(promotion_id)


async def test_promotion_repromotion_same_artifact_allowed(session_factory) -> None:
    shot_id = uuid.uuid4()
    artifact_id = uuid.uuid4()
    base = datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc)

    async with session_factory() as session:
        repo = OrchestrationPromotionLedgerRepo(session)
        await repo.insert_promotion(
            shot_id=shot_id,
            promoted_artifact_id=artifact_id,
            promoted_by="operator",
            rationale="first",
            promoted_at=base,
        )
        await repo.insert_promotion(
            shot_id=shot_id,
            promoted_artifact_id=artifact_id,
            promoted_by="operator",
            rationale="re-promoted",
            promoted_at=base + timedelta(hours=1),
        )
        await session.commit()

    async with session_factory() as session:
        history = await OrchestrationPromotionLedgerRepo(session).get_history(shot_id)
        assert len(history) == 2
        assert all(row.promoted_artifact_id == artifact_id for row in history)
