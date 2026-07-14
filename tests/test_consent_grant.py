"""ConsentGrant entity + repo tests (#161) — the fitted-model consent latch.

Covers the to_dict generators-compatibility contract, the proposed→ratified→
withdrawn lifecycle + events, illegal transitions, bind_asset rules, and — the
SAFETY-CRITICAL path — that withdrawing a BOUND grant propagates to asset
revocation atomically so the #160 gate immediately refuses inference.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from forge_bridge.core.consent_grant import ConsentGrant
from forge_bridge.orchestration.dispatcher import _check_model_not_revoked
from forge_bridge.store.consent_grant_repo import (
    ConsentGrantBindingError,
    ConsentGrantLifecycleError,
    ConsentGrantNotFound,
    ConsentGrantRepo,
)
from forge_bridge.store.models import DBEntity, DBEvent
from sqlalchemy import select


_VALID_FROM = datetime(2026, 1, 1, tzinfo=timezone.utc)
_VALID_UNTIL = datetime(2027, 1, 1, tzinfo=timezone.utc)


# ── Entity to_dict shape — generators-compatibility contract ─────────────────

def test_entity_to_dict_generators_compatible_keys():
    grant = ConsentGrant(
        owner_of_likeness="Jane Doe",
        allowed_shot_scopes=["this_clip_only"],
        forbidden_uses=["advertising"],
        valid_from=_VALID_FROM,
        valid_until=_VALID_UNTIL,
        nonce="deadbeef",
        grant_id="0123456789ab",
        fitted_model_asset_id="11111111-1111-1111-1111-111111111111",
    )
    d = grant.to_dict()
    # base keys
    for key in ("id", "entity_type", "created_at", "metadata",
                "locations", "relationships"):
        assert key in d
    assert d["entity_type"] == "consent_grant"
    # generators-local ConsentGrant shape (src/forge_generators/artifacts/consent.py)
    for key in ("grant_id", "identity_id", "owner_of_likeness",
                "allowed_shot_scopes", "forbidden_uses", "valid_from",
                "valid_until", "revoked", "revocation_handle", "status"):
        assert key in d, f"missing generators-compatible key {key!r}"
    # identity_id IS the bound fitted-model asset id
    assert d["identity_id"] == "11111111-1111-1111-1111-111111111111"
    assert d["fitted_model_asset_id"] == d["identity_id"]
    assert d["owner_of_likeness"] == "Jane Doe"
    assert d["allowed_shot_scopes"] == ["this_clip_only"]
    assert d["forbidden_uses"] == ["advertising"]
    assert d["valid_from"] == _VALID_FROM.isoformat()
    assert d["valid_until"] == _VALID_UNTIL.isoformat()
    assert d["status"] == "proposed"
    # revoked is DERIVED from status
    assert d["revoked"] is False


def test_entity_revoked_derived_from_withdrawn_status():
    grant = ConsentGrant(owner_of_likeness="Jane Doe", status="withdrawn")
    assert grant.revoked is True
    assert grant.to_dict()["revoked"] is True


def test_entity_defaults_this_clip_only():
    grant = ConsentGrant(owner_of_likeness="Jane Doe")
    assert grant.allowed_shot_scopes == ["this_clip_only"]
    assert grant.forbidden_uses == []
    assert grant.fitted_model_asset_id is None
    assert grant.to_dict()["identity_id"] is None


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _make_asset(session_factory) -> uuid.UUID:
    asset_id = uuid.uuid4()
    async with session_factory() as session:
        session.add(DBEntity(
            id=asset_id,
            entity_type="asset",
            name="fitted-model-jane",
            status="active",
            attributes={"asset_type": "fitted_model"},
        ))
        await session.commit()
    return asset_id


async def _proposed(session_factory, owner="Jane Doe") -> str:
    async with session_factory() as session:
        grant = await ConsentGrantRepo(session).propose(
            owner_of_likeness=owner,
            valid_from=_VALID_FROM,
            valid_until=_VALID_UNTIL,
        )
        await session.commit()
        return grant.grant_id


async def _ratified(session_factory, owner="Jane Doe") -> str:
    grant_id = await _proposed(session_factory, owner=owner)
    async with session_factory() as session:
        await ConsentGrantRepo(session).ratify(grant_id, actor="operator")
        await session.commit()
    return grant_id


async def _event_types(session_factory, grant_id: str) -> list[str]:
    async with session_factory() as session:
        rows = (await session.execute(
            select(DBEvent).order_by(DBEvent.occurred_at.asc())
        )).scalars().all()
    return [
        r.event_type for r in rows
        if (r.payload or {}).get("grant_id") == grant_id
        or (r.payload or {}).get("operation") == "consent_grant"
    ]


# ── Lifecycle: propose → ratify → withdrawn + events ─────────────────────────

@pytest.mark.asyncio
async def test_propose_ratify_withdraw_happy_path(session_factory):
    async with session_factory() as session:
        repo = ConsentGrantRepo(session)
        grant = await repo.propose(
            owner_of_likeness="Jane Doe",
            valid_from=_VALID_FROM,
            valid_until=_VALID_UNTIL,
        )
        await session.commit()
        grant_id = grant.grant_id
        assert grant.status == "proposed"
        assert grant_id and len(grant_id) == 12

    async with session_factory() as session:
        ratified = await ConsentGrantRepo(session).ratify(grant_id, actor="cnoellert")
        await session.commit()
        assert ratified.status == "ratified"
        assert ratified.decided_by == "cnoellert"
        assert ratified.decided_at is not None

    async with session_factory() as session:
        withdrawn = await ConsentGrantRepo(session).withdraw(grant_id, actor="cnoellert")
        await session.commit()
        assert withdrawn.status == "withdrawn"
        assert withdrawn.withdrawn_at is not None
        assert withdrawn.revoked is True

    types = await _event_types(session_factory, grant_id)
    assert "consent_grant.proposed" in types
    assert "consent_grant.ratified" in types
    assert "consent_grant.withdrawn" in types


@pytest.mark.asyncio
async def test_withdraw_directly_from_proposed(session_factory):
    """proposed -> withdrawn is legal (consent revoked before ratification)."""
    grant_id = await _proposed(session_factory)
    async with session_factory() as session:
        withdrawn = await ConsentGrantRepo(session).withdraw(grant_id, actor="op")
        await session.commit()
        assert withdrawn.status == "withdrawn"


@pytest.mark.asyncio
async def test_double_ratify_is_illegal(session_factory):
    grant_id = await _ratified(session_factory)
    async with session_factory() as session:
        with pytest.raises(ConsentGrantLifecycleError) as exc:
            await ConsentGrantRepo(session).ratify(grant_id, actor="op")
        assert exc.value.from_status == "ratified"


@pytest.mark.asyncio
async def test_ratify_missing_grant_raises_not_found(session_factory):
    async with session_factory() as session:
        with pytest.raises(ConsentGrantNotFound):
            await ConsentGrantRepo(session).ratify("ffffffffffff", actor="op")


@pytest.mark.asyncio
async def test_nonce_makes_identical_terms_mints_distinct(session_factory):
    async with session_factory() as session:
        repo = ConsentGrantRepo(session)
        a = await repo.propose(owner_of_likeness="Jane Doe", valid_from=_VALID_FROM)
        b = await repo.propose(owner_of_likeness="Jane Doe", valid_from=_VALID_FROM)
        await session.commit()
        assert a.grant_id != b.grant_id
        assert a.nonce != b.nonce


# ── bind_asset rules ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_bind_asset_sets_id_on_ratified(session_factory):
    grant_id = await _ratified(session_factory)
    asset_id = await _make_asset(session_factory)
    async with session_factory() as session:
        bound = await ConsentGrantRepo(session).bind_asset(grant_id, asset_id, actor="fit")
        await session.commit()
        assert bound.fitted_model_asset_id == str(asset_id)
        assert bound.to_dict()["identity_id"] == str(asset_id)

    types = await _event_types(session_factory, grant_id)
    assert "consent_grant.bound" in types


@pytest.mark.asyncio
async def test_bind_asset_rejects_on_proposed(session_factory):
    grant_id = await _proposed(session_factory)
    asset_id = await _make_asset(session_factory)
    async with session_factory() as session:
        with pytest.raises(ConsentGrantBindingError) as exc:
            await ConsentGrantRepo(session).bind_asset(grant_id, asset_id, actor="fit")
        assert exc.value.current_status == "proposed"


@pytest.mark.asyncio
async def test_bind_asset_rejects_on_withdrawn(session_factory):
    grant_id = await _ratified(session_factory)
    async with session_factory() as session:
        await ConsentGrantRepo(session).withdraw(grant_id, actor="op")
        await session.commit()
    asset_id = await _make_asset(session_factory)
    async with session_factory() as session:
        with pytest.raises(ConsentGrantBindingError) as exc:
            await ConsentGrantRepo(session).bind_asset(grant_id, asset_id, actor="fit")
        assert exc.value.current_status == "withdrawn"


@pytest.mark.asyncio
async def test_bind_asset_idempotent_same_asset(session_factory):
    grant_id = await _ratified(session_factory)
    asset_id = await _make_asset(session_factory)
    async with session_factory() as session:
        repo = ConsentGrantRepo(session)
        await repo.bind_asset(grant_id, asset_id, actor="fit")
        await session.commit()
    async with session_factory() as session:
        again = await ConsentGrantRepo(session).bind_asset(grant_id, asset_id, actor="fit")
        await session.commit()
        assert again.fitted_model_asset_id == str(asset_id)
    # Exactly one bound event — the idempotent re-bind emitted none.
    types = await _event_types(session_factory, grant_id)
    assert types.count("consent_grant.bound") == 1


@pytest.mark.asyncio
async def test_bind_asset_rejects_different_asset_when_bound(session_factory):
    grant_id = await _ratified(session_factory)
    asset_a = await _make_asset(session_factory)
    asset_b = await _make_asset(session_factory)
    async with session_factory() as session:
        await ConsentGrantRepo(session).bind_asset(grant_id, asset_a, actor="fit")
        await session.commit()
    async with session_factory() as session:
        with pytest.raises(ConsentGrantBindingError):
            await ConsentGrantRepo(session).bind_asset(grant_id, asset_b, actor="fit")


# ── SAFETY-CRITICAL: withdrawal propagation end-to-end ───────────────────────

@pytest.mark.asyncio
async def test_withdraw_bound_grant_revokes_asset_and_refuses_inference(session_factory):
    """Withdrawing a BOUND grant → grant withdrawn, asset revoked, gate refuses.

    Proves consent-withdrawal ⇒ inference-refusal (the #161 ship-blocker).
    """
    grant_id = await _ratified(session_factory)
    asset_id = await _make_asset(session_factory)
    async with session_factory() as session:
        await ConsentGrantRepo(session).bind_asset(grant_id, asset_id, actor="fit")
        await session.commit()

    # Pre-withdrawal: the gate ALLOWS inference on the bound-but-live model.
    ok, code = await _check_model_not_revoked(
        session_factory, fitted_model_asset_id=str(asset_id),
    )
    assert ok is True and code is None

    # Withdraw — the load-bearing path.
    async with session_factory() as session:
        withdrawn = await ConsentGrantRepo(session).withdraw(
            grant_id, reason="likeness_owner_withdrew", actor="operator",
        )
        await session.commit()

    # (a) grant status is withdrawn
    assert withdrawn.status == "withdrawn"

    # (b) the linked asset now carries revoked_at
    async with session_factory() as session:
        asset = await session.get(DBEntity, asset_id)
        assert asset.attributes.get("revoked_at") is not None
        assert asset.attributes.get("revocation_reason") == "likeness_owner_withdrew"

    # (c) the #160 gate now REFUSES for that asset
    ok, code = await _check_model_not_revoked(
        session_factory, fitted_model_asset_id=str(asset_id),
    )
    assert ok is False
    assert code == "model_revoked"


@pytest.mark.asyncio
async def test_withdraw_propagation_is_atomic_rollback(session_factory):
    """If the withdraw session rolls back, NEITHER grant nor asset changes."""
    grant_id = await _ratified(session_factory)
    asset_id = await _make_asset(session_factory)
    async with session_factory() as session:
        await ConsentGrantRepo(session).bind_asset(grant_id, asset_id, actor="fit")
        await session.commit()

    async with session_factory() as session:
        await ConsentGrantRepo(session).withdraw(grant_id, actor="op")
        # deliberately DO NOT commit — roll back instead
        await session.rollback()

    # Grant still ratified, asset still live — the two moved together (or not).
    async with session_factory() as session:
        grant = await ConsentGrantRepo(session).get_by_grant_id(grant_id)
        assert grant.status == "ratified"
        asset = await session.get(DBEntity, asset_id)
        assert asset.attributes.get("revoked_at") is None


@pytest.mark.asyncio
async def test_withdraw_unbound_grant_flips_state_no_revoke(session_factory):
    """Withdrawing an UNBOUND grant flips state, revokes nothing, raises nothing."""
    grant_id = await _ratified(session_factory)
    async with session_factory() as session:
        withdrawn = await ConsentGrantRepo(session).withdraw(grant_id, actor="op")
        await session.commit()
        assert withdrawn.status == "withdrawn"
        assert withdrawn.fitted_model_asset_id is None
    # No asset.revoked event was emitted (nothing to revoke).
    async with session_factory() as session:
        rows = (await session.execute(
            select(DBEvent).where(DBEvent.event_type == "asset.revoked")
        )).scalars().all()
        assert rows == []


@pytest.mark.asyncio
async def test_idempotent_re_withdraw_no_double_revoke(session_factory):
    """Re-withdrawing a withdrawn grant is a no-op — no 2nd revoke, no 2nd event."""
    grant_id = await _ratified(session_factory)
    asset_id = await _make_asset(session_factory)
    async with session_factory() as session:
        await ConsentGrantRepo(session).bind_asset(grant_id, asset_id, actor="fit")
        await session.commit()

    async with session_factory() as session:
        await ConsentGrantRepo(session).withdraw(grant_id, actor="op")
        await session.commit()

    async with session_factory() as session:
        again = await ConsentGrantRepo(session).withdraw(grant_id, actor="op")
        await session.commit()
        assert again.status == "withdrawn"

    # Exactly one withdrawn event and one asset.revoked event.
    types = await _event_types(session_factory, grant_id)
    assert types.count("consent_grant.withdrawn") == 1
    async with session_factory() as session:
        revokes = (await session.execute(
            select(DBEvent).where(DBEvent.event_type == "asset.revoked")
        )).scalars().all()
        assert len(revokes) == 1


# ── Migration / entity_type validity ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_consent_grant_persists_as_valid_entity_type(session_factory):
    """consent_grant is an accepted entity_type after schema build (create_all)."""
    grant_id = await _proposed(session_factory)
    async with session_factory() as session:
        row = (await session.execute(
            select(DBEntity).where(DBEntity.entity_type == "consent_grant")
        )).scalar_one()
        assert row.content_hash.startswith(grant_id)
        assert row.status == "proposed"
