"""Registry-owned retention and two-phase GC for fitted-model assets (#160)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from forge_bridge.core import Asset, Project, Registry, Status
from forge_bridge.core.entities import Media, Version
from forge_bridge.store.fitted_model_lifecycle_repo import (
    GC_ACTIVE,
    GC_COLLECTED,
    GC_MARKED,
    FittedModelLifecycleError,
    FittedModelLifecycleRepo,
)
from forge_bridge.store.models import DBEntity, DBEvent, DBLocation
from forge_bridge.store.repo import EntityRepo, LocationRepo, ProjectRepo


pytestmark = pytest.mark.asyncio

_NOW = datetime(2026, 7, 17, 12, tzinfo=timezone.utc)


async def _registered_model(session_factory) -> tuple[uuid.UUID, uuid.UUID, str]:
    project = Project(name="GC Test", code=f"GC{uuid.uuid4().hex[:8]}")
    model = Asset(
        name="hero.fitted",
        asset_type="fitted-model",
        project_id=project.id,
        status=Status.APPROVED,
    )
    version = Version(version_number=1, parent_id=model.id, parent_type="asset")
    weights = Media(
        format="safetensors",
        version_id=version.id,
        name="hero.v1.safetensors",
    )
    path = "s3://forge-models/hero/v1/weights.safetensors"
    weights.add_location(path, storage_type="cloud", priority=10)

    async with session_factory() as session:
        await ProjectRepo(session).save(project)
        entities = EntityRepo(session, Registry.default())
        for entity in (model, version, weights):
            await entities.save(entity, project.id)
        await LocationRepo(session).save_entity_locations(weights)
        await session.commit()

    async with session_factory() as session:
        location = (
            await session.execute(
                select(DBLocation).where(DBLocation.entity_id == weights.id)
            )
        ).scalar_one()
    return model.id, location.id, path


async def _set_retention(
    session_factory,
    asset_id: uuid.UUID,
    retention_until: datetime,
) -> None:
    async with session_factory() as session:
        await FittedModelLifecycleRepo(session).set_retention(
            asset_id,
            retention_until=retention_until,
            actor="operator",
        )
        await session.commit()


async def test_unbounded_retention_is_not_a_gc_candidate(session_factory):
    asset_id, _location_id, _path = await _registered_model(session_factory)

    async with session_factory() as session:
        candidates = await FittedModelLifecycleRepo(session).list_gc_candidates(
            as_of=_NOW
        )

    assert all(candidate.asset_id != asset_id for candidate in candidates)


async def test_explicit_expired_retention_yields_weights_locations(session_factory):
    asset_id, location_id, path = await _registered_model(session_factory)
    await _set_retention(session_factory, asset_id, _NOW - timedelta(days=1))

    async with session_factory() as session:
        candidates = await FittedModelLifecycleRepo(session).list_gc_candidates(
            as_of=_NOW
        )

    candidate = next(item for item in candidates if item.asset_id == asset_id)
    assert candidate.to_dict()["locations"] == [{
        "location_id": str(location_id),
        "entity_id": str(candidate.locations[0].entity_id),
        "path": path,
        "storage_type": "cloud",
    }]


async def test_use_after_retention_deadline_removes_candidate(session_factory):
    asset_id, _location_id, _path = await _registered_model(session_factory)
    deadline = _NOW - timedelta(days=2)
    await _set_retention(session_factory, asset_id, deadline)

    async with session_factory() as session:
        repo = FittedModelLifecycleRepo(session)
        entity, refusal = await repo.lock_for_inference(asset_id)
        assert refusal is None
        await repo.record_use(
            entity,
            operator_id="swap",
            request_id="req-1",
            used_at=_NOW - timedelta(days=1),
        )
        await session.commit()

    async with session_factory() as session:
        candidates = await FittedModelLifecycleRepo(session).list_gc_candidates(
            as_of=_NOW
        )
    assert all(candidate.asset_id != asset_id for candidate in candidates)


async def test_mark_blocks_inference_and_retention_extension_unmarks(session_factory):
    asset_id, _location_id, _path = await _registered_model(session_factory)
    await _set_retention(session_factory, asset_id, _NOW - timedelta(days=1))

    async with session_factory() as session:
        repo = FittedModelLifecycleRepo(session)
        marked = await repo.mark_gc(
            asset_id,
            collect_after=_NOW + timedelta(days=7),
            actor="operator",
            as_of=_NOW,
        )
        await session.commit()
    assert marked["gc_state"] == GC_MARKED

    async with session_factory() as session:
        _entity, refusal = await FittedModelLifecycleRepo(session).lock_for_inference(
            asset_id
        )
    assert refusal == "model_gc_pending"

    async with session_factory() as session:
        state = await FittedModelLifecycleRepo(session).set_retention(
            asset_id,
            retention_until=_NOW + timedelta(days=30),
            actor="operator",
            reason="active show",
        )
        await session.commit()
    assert state["gc_state"] == GC_ACTIVE
    assert state["gc_marked_at"] is None

    async with session_factory() as session:
        _entity, refusal = await FittedModelLifecycleRepo(session).lock_for_inference(
            asset_id
        )
    assert refusal is None


async def test_finalize_requires_elapsed_grace_and_complete_receipts(session_factory):
    asset_id, location_id, path = await _registered_model(session_factory)
    await _set_retention(session_factory, asset_id, _NOW - timedelta(days=1))
    async with session_factory() as session:
        await FittedModelLifecycleRepo(session).mark_gc(
            asset_id,
            collect_after=_NOW + timedelta(days=7),
            actor="operator",
            as_of=_NOW,
        )
        await session.commit()

    receipt = {"location_id": str(location_id), "path": path, "deleted": True}
    async with session_factory() as session:
        with pytest.raises(FittedModelLifecycleError) as exc:
            await FittedModelLifecycleRepo(session).finalize_gc(
                asset_id,
                deletion_receipts=[receipt],
                actor="collector",
                as_of=_NOW + timedelta(days=1),
            )
    assert exc.value.code == "gc_grace_active"

    async with session_factory() as session:
        with pytest.raises(FittedModelLifecycleError) as exc:
            await FittedModelLifecycleRepo(session).finalize_gc(
                asset_id,
                deletion_receipts=[],
                actor="collector",
                as_of=_NOW + timedelta(days=8),
            )
    assert exc.value.code == "deletion_unproven"


async def test_finalize_archives_aggregate_and_preserves_deletion_proof(session_factory):
    asset_id, location_id, path = await _registered_model(session_factory)
    await _set_retention(session_factory, asset_id, _NOW - timedelta(days=1))
    async with session_factory() as session:
        await FittedModelLifecycleRepo(session).mark_gc(
            asset_id,
            collect_after=_NOW + timedelta(days=7),
            actor="operator",
            as_of=_NOW,
        )
        await session.commit()

    receipt = {
        "location_id": str(location_id),
        "path": path,
        "deleted": True,
        "storage_receipt": "s3-delete-version:abc",
    }
    async with session_factory() as session:
        state = await FittedModelLifecycleRepo(session).finalize_gc(
            asset_id,
            deletion_receipts=[receipt],
            actor="collector",
            as_of=_NOW + timedelta(days=8),
        )
        await session.commit()

    assert state["gc_state"] == GC_COLLECTED
    assert len(state["archived_entity_ids"]) == 3
    async with session_factory() as session:
        aggregate = (
            await session.execute(
                select(DBEntity).where(
                    DBEntity.id.in_(
                        [uuid.UUID(value) for value in state["archived_entity_ids"]]
                    )
                )
            )
        ).scalars().all()
        location = await session.get(DBLocation, location_id)
        events = (
            await session.execute(
                select(DBEvent).where(
                    DBEvent.event_type == "fitted_model.gc_collected",
                    DBEvent.entity_id == asset_id,
                )
            )
        ).scalars().all()

    assert {entity.status for entity in aggregate} == {"archived"}
    model = next(entity for entity in aggregate if entity.id == asset_id)
    assert model.attributes["gc_state"] == GC_COLLECTED
    assert location.exists is False
    assert location.checked_at == _NOW + timedelta(days=8)
    assert location.attributes["gc_deletion_receipt"] == receipt
    assert len(events) == 1


async def test_non_fitted_asset_cannot_enter_lifecycle(session_factory):
    project = Project(name="Asset Test", code=f"A{uuid.uuid4().hex[:8]}")
    asset = Asset(name="plate", asset_type="plate", project_id=project.id)
    async with session_factory() as session:
        await ProjectRepo(session).save(project)
        await EntityRepo(session, Registry.default()).save(asset, project.id)
        await session.commit()

    async with session_factory() as session:
        with pytest.raises(FittedModelLifecycleError) as exc:
            await FittedModelLifecycleRepo(session).set_retention(
                asset.id,
                retention_until=_NOW,
                actor="operator",
            )
    assert exc.value.code == "model_not_found"
