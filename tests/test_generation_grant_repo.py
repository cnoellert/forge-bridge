"""GenerationGrant entity + repo tests (#146) — the spend-gate foundation."""

from __future__ import annotations

import pytest

from forge_bridge.core.generation_grant import GenerationGrant
from forge_bridge.store.generation_grant_repo import GenerationGrantRepo


_TRIPLE = {"surface": "higgsfield-api", "path": "video-v1", "version": "1"}
_COST = {"currency": "USD", "amount": 0.42}


def test_entity_to_dict_shape():
    grant = GenerationGrant(
        operator_id="generate_video_from_image",
        backend_identity_triple=_TRIPLE,
        estimated_cost=_COST,
        run_kind="generation",
        nonce="deadbeef",
        grant_id="0123456789ab",
    )
    d = grant.to_dict()
    # base keys
    for key in ("id", "entity_type", "created_at", "metadata",
                "locations", "relationships"):
        assert key in d
    assert d["entity_type"] == "generation_grant"
    # added keys — the canonical extensible shape
    assert d["grant_id"] == "0123456789ab"
    assert d["operator_id"] == "generate_video_from_image"
    assert d["backend_identity_triple"] == _TRIPLE
    assert d["estimated_cost"] == _COST
    assert d["run_kind"] == "generation"
    assert d["nonce"] == "deadbeef"
    assert d["status"] == "proposed"
    assert d["decided_by"] is None
    assert d["decided_at"] is None
    assert d["consumed_at"] is None
    # NO chain_steps / applied_at / apply_result — the runs spend, not the grant
    assert "chain_steps" not in d
    assert "applied_at" not in d
    assert "apply_result" not in d


@pytest.mark.asyncio
async def test_propose_ratify_consume_happy_path(session_factory):
    async with session_factory() as session:
        repo = GenerationGrantRepo(session)
        grant = await repo.propose(
            operator_id="generate_video_from_image",
            backend_identity_triple=_TRIPLE,
            estimated_cost=_COST,
            run_kind="generation",
        )
        await session.commit()
        grant_id = grant.grant_id
        assert grant.status == "proposed"
        assert grant_id and len(grant_id) == 12

    async with session_factory() as session:
        ratified = await GenerationGrantRepo(session).ratify(grant_id, actor="cnoellert")
        await session.commit()
        assert ratified.status == "ratified"
        assert ratified.decided_by == "cnoellert"
        assert ratified.decided_at is not None

    async with session_factory() as session:
        consumed = await GenerationGrantRepo(session).consume_atomic(grant_id)
        await session.commit()
        assert consumed is not None
        assert consumed.status == "consumed"
        assert consumed.consumed_at is not None


@pytest.mark.asyncio
async def test_consume_on_non_ratified_refuses(session_factory):
    """A proposed (never ratified) grant cannot be consumed."""
    async with session_factory() as session:
        repo = GenerationGrantRepo(session)
        grant = await repo.propose(
            operator_id="op",
            backend_identity_triple=_TRIPLE,
            estimated_cost=_COST,
            run_kind="generation",
        )
        await session.commit()
        grant_id = grant.grant_id

    async with session_factory() as session:
        refused = await GenerationGrantRepo(session).consume_atomic(grant_id)
        await session.commit()
        assert refused is None  # fail-closed: not ratified


@pytest.mark.asyncio
async def test_double_consume_replay_refuses(session_factory):
    """The second consume of a ratified grant (replay) is refused."""
    async with session_factory() as session:
        repo = GenerationGrantRepo(session)
        grant = await repo.propose(
            operator_id="op",
            backend_identity_triple=_TRIPLE,
            estimated_cost=_COST,
            run_kind="generation",
        )
        await session.commit()
        grant_id = grant.grant_id

    async with session_factory() as session:
        await GenerationGrantRepo(session).ratify(grant_id, actor="op")
        await session.commit()

    async with session_factory() as session:
        first = await GenerationGrantRepo(session).consume_atomic(grant_id)
        await session.commit()
        assert first is not None and first.status == "consumed"

    async with session_factory() as session:
        second = await GenerationGrantRepo(session).consume_atomic(grant_id)
        await session.commit()
        assert second is None  # #141 idempotency for free


@pytest.mark.asyncio
async def test_nonce_makes_identical_cost_mints_distinct(session_factory):
    """Two identical-cost quotes mint distinct grant_ids (nonce uniqueness)."""
    async with session_factory() as session:
        repo = GenerationGrantRepo(session)
        a = await repo.propose(
            operator_id="op",
            backend_identity_triple=_TRIPLE,
            estimated_cost=_COST,
            run_kind="generation",
        )
        b = await repo.propose(
            operator_id="op",
            backend_identity_triple=_TRIPLE,
            estimated_cost=_COST,
            run_kind="generation",
        )
        await session.commit()
        assert a.grant_id != b.grant_id
        assert a.nonce != b.nonce
