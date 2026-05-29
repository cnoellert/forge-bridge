from __future__ import annotations

import pytest
from sqlalchemy import select

from forge_bridge.store.assent_record_repo import (
    AssentRecordLifecycleError,
    AssentRecordNotFound,
    AssentRecordRepo,
)
from forge_bridge.store.content_addressed_repo import ImmutableArtifactError
from forge_bridge.store.models import DBEvent


@pytest.mark.asyncio
async def test_assent_record_repo_propose_is_content_addressed(session_factory):
    async with session_factory() as session:
        repo = AssentRecordRepo(session)

        first = await repo.propose(["list shots", "commit"])
        second = await repo.propose(["list shots", "commit"])

        assert first.id == second.id
        assert first.status == "proposed"
        assert len(first.graph_intent_id) == 12
        assert first.chain_steps == ["list shots", "commit"]

        events = (
            await session.execute(
                select(DBEvent).where(DBEvent.event_type == "assent.proposed")
            )
        ).scalars().all()
        assert len(events) == 1
        assert events[0].payload["graph_intent_id"] == first.graph_intent_id
        assert events[0].payload["chain_step_count"] == 2
        assert events[0].payload["requires_ratification"] is True


@pytest.mark.asyncio
async def test_assent_record_repo_ratify_and_illegal_reratify(session_factory):
    async with session_factory() as session:
        repo = AssentRecordRepo(session)
        record = await repo.propose(["list shots", "commit"])

        ratified = await repo.ratify(record.graph_intent_id, actor="local")

        assert ratified.status == "ratified"
        assert ratified.decided_by == "local"
        assert ratified.decided_at is not None

        events = (
            await session.execute(
                select(DBEvent)
                .where(DBEvent.event_type == "assent.ratified")
            )
        ).scalars().all()
        assert len(events) == 1
        assert events[0].client_name == "local"
        assert events[0].payload["decided_by"] == "local"

        with pytest.raises(AssentRecordLifecycleError) as exc:
            await repo.ratify(record.graph_intent_id, actor="local")
        assert exc.value.from_status == "ratified"
        assert exc.value.to_status == "ratified"


@pytest.mark.asyncio
async def test_assent_record_repo_unknown_graph_intent_raises(session_factory):
    async with session_factory() as session:
        repo = AssentRecordRepo(session)

        assert await repo.get_by_graph_intent_id("nonexistent") is None
        with pytest.raises(AssentRecordNotFound):
            await repo.ratify("nonexistent", actor="local")


@pytest.mark.asyncio
async def test_assent_record_repo_applied_and_failed_transitions(session_factory):
    async with session_factory() as session:
        repo = AssentRecordRepo(session)
        applied_record = await repo.propose(["list shots", "commit"])
        await repo.ratify(applied_record.graph_intent_id, actor="local")

        applied = await repo.mark_applied(
            applied_record.graph_intent_id,
            result={"status": "success"},
        )

        assert applied.status == "applied"
        assert applied.applied_at is not None
        assert applied.apply_result == {"status": "success"}

        failed_record = await repo.propose(["rename shots", "commit"])
        await repo.ratify(failed_record.graph_intent_id, actor="local")
        failed = await repo.mark_failed(
            failed_record.graph_intent_id,
            reason="drift_invalid",
        )

        assert failed.status == "failed"
        assert failed.applied_at is not None
        assert failed.apply_failure_reason == "drift_invalid"

        event_types = [
            event.event_type
            for event in (
                await session.execute(select(DBEvent).order_by(DBEvent.event_type))
            ).scalars()
        ]
        assert "assent.applied" in event_types
        assert "assent.failed" in event_types


@pytest.mark.asyncio
async def test_assent_record_repo_list_pending_and_immutability(session_factory):
    async with session_factory() as session:
        repo = AssentRecordRepo(session)
        proposed = await repo.propose(["list shots", "commit"])
        ratified = await repo.propose(["rename shots", "commit"])
        await repo.ratify(ratified.graph_intent_id, actor="local")

        records, total = await repo.list_pending(status="proposed")

        assert total == 1
        assert [record.id for record in records] == [proposed.id]

        with pytest.raises(ImmutableArtifactError):
            await repo.update(proposed.id, {"chain_steps": ["other"]})
        with pytest.raises(ImmutableArtifactError):
            await repo.delete(proposed.id)


def test_content_addressed_repo_docstring_names_assent_repo():
    from forge_bridge.store import content_addressed_repo

    assert "assent_record_repo.py" in (content_addressed_repo.__doc__ or "")
    assert "content-addressed semantic-artifact" in (
        content_addressed_repo.ContentAddressedRepo.__doc__ or ""
    )
