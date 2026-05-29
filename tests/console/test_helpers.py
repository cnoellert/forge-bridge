from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import timedelta

import pytest

from forge_bridge.console import helpers
from forge_bridge.store.assent_record_repo import AssentRecordRepo


@pytest.fixture
def helper_session(monkeypatch, session_factory):
    @asynccontextmanager
    async def _get_session():
        async with session_factory() as session:
            yield session

    monkeypatch.setattr(helpers, "get_session", _get_session)
    return session_factory


@pytest.mark.asyncio
async def test_recent_ratifications_returns_ratified_records(helper_session):
    async with helper_session() as session:
        repo = AssentRecordRepo(session)
        proposed = await repo.propose(["pending", "commit"])
        ratified = await repo.propose(["ratified", "commit"])
        await repo.ratify(ratified.graph_intent_id, actor="operator")
        await session.commit()

    records = await helpers.recent_ratifications()

    assert [record.graph_intent_id for record in records] == [
        ratified.graph_intent_id
    ]
    assert proposed.graph_intent_id not in {record.graph_intent_id for record in records}


@pytest.mark.asyncio
async def test_recent_ratifications_empty_result(helper_session):
    records = await helpers.recent_ratifications(window=timedelta(seconds=1))

    assert records == []


@pytest.mark.asyncio
async def test_pending_assent_records_returns_proposed_records(helper_session):
    async with helper_session() as session:
        repo = AssentRecordRepo(session)
        proposed = await repo.propose(["pending", "commit"])
        ratified = await repo.propose(["ratified", "commit"])
        await repo.ratify(ratified.graph_intent_id, actor="operator")
        await session.commit()

    records = await helpers.pending_assent_records()

    assert [record.graph_intent_id for record in records] == [
        proposed.graph_intent_id
    ]


@pytest.mark.asyncio
async def test_pending_assent_records_empty_result(helper_session):
    records = await helpers.pending_assent_records()

    assert records == []


@pytest.mark.asyncio
async def test_recent_failed_applies_returns_failed_records(helper_session):
    async with helper_session() as session:
        repo = AssentRecordRepo(session)
        failed = await repo.propose(["failed", "commit"])
        applied = await repo.propose(["applied", "commit"])
        await repo.ratify(failed.graph_intent_id, actor="operator")
        await repo.mark_failed(failed.graph_intent_id, reason="chain_aborted")
        await repo.ratify(applied.graph_intent_id, actor="operator")
        await repo.mark_applied(applied.graph_intent_id, result={"status": "success"})
        await session.commit()

    records = await helpers.recent_failed_applies()

    assert [record.graph_intent_id for record in records] == [
        failed.graph_intent_id
    ]


@pytest.mark.asyncio
async def test_recent_failed_applies_empty_result(helper_session):
    records = await helpers.recent_failed_applies(window=timedelta(seconds=1))

    assert records == []
