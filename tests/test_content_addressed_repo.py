"""Phase 4B Step 3 — ContentAddressedRepo pattern tests (LockedIntentRepo exemplar)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from forge_bridge.store.content_addressed_repo import (
    ContentAddressedRepo,
    ImmutableArtifactError,
)
from forge_bridge.store.models import DBEntity, DBOrchLockedIntent
from forge_bridge.store.orch_locked_intent_repo import LockedIntentRepo


def _sample_locked_intent_body(**overrides) -> dict:
    body = {
        "source_read": {"shot_id": "shot-001"},
        "change_manifest": [{"field": "motion", "from": "a", "to": "b"}],
        "success_criteria": [
            {
                "criterion_id": "motion_arc",
                "statement": "hand reaches clock face",
                "measurement_spec": {"method": "temporal_ioU"},
                "tolerances": {"min": 0.7},
            }
        ],
        "allowed_compromises": [{"criterion_id": "timing", "budget": 0.1}],
        "hard_constraints": ["no identity drift"],
        "escalation_threshold": 0.8,
        "deliverable_spec": {"format": "video", "duration_seconds": 5},
    }
    body.update(overrides)
    return body


class _RuleSnapshotView:
    ENTITY_TYPE = "orch_rule_snapshot"

    def __init__(self, entity: DBEntity) -> None:
        self._entity = entity

    @classmethod
    def from_entity(cls, entity: DBEntity) -> _RuleSnapshotView:
        return cls(entity)

    @property
    def id(self) -> uuid.UUID:
        return self._entity.id


class _RuleSnapshotRepo(ContentAddressedRepo[_RuleSnapshotView]):
    __entity_type__ = "orch_rule_snapshot"
    __model__ = _RuleSnapshotView


async def test_insert_if_absent_idempotent(session_factory) -> None:
    body = _sample_locked_intent_body()

    async with session_factory() as session:
        repo = LockedIntentRepo(session)
        first = await repo.insert_if_absent(body)
        second = await repo.insert_if_absent(body)
        await session.commit()

        assert first.id == second.id
        assert first.content_hash == second.content_hash

    async with session_factory() as session:
        count = await session.scalar(
            select(func.count())
            .select_from(DBEntity)
            .where(
                DBEntity.entity_type == "orch_locked_intent",
                DBEntity.content_hash == first.content_hash,
            )
        )
        assert count == 1


async def test_insert_if_absent_distinct_bodies(session_factory) -> None:
    body_a = _sample_locked_intent_body(escalation_threshold=0.8)
    body_b = _sample_locked_intent_body(escalation_threshold=0.9)

    async with session_factory() as session:
        repo = LockedIntentRepo(session)
        row_a = await repo.insert_if_absent(body_a)
        row_b = await repo.insert_if_absent(body_b)
        await session.commit()

        assert row_a.id != row_b.id
        assert row_a.content_hash != row_b.content_hash


async def test_insert_if_absent_canonicalization(session_factory) -> None:
    body_a = {"a": 1, "b": 2}
    body_b = {"b": 2, "a": 1}

    async with session_factory() as session:
        repo = LockedIntentRepo(session)
        first = await repo.insert_if_absent(body_a)
        second = await repo.insert_if_absent(body_b)
        await session.commit()

        assert first.id == second.id
        assert first.content_hash == second.content_hash


async def test_get_by_content_hash(session_factory) -> None:
    body = _sample_locked_intent_body()

    async with session_factory() as session:
        repo = LockedIntentRepo(session)
        inserted = await repo.insert_if_absent(body)
        await session.commit()
        content_hash = inserted.content_hash

    async with session_factory() as session:
        repo = LockedIntentRepo(session)
        found = await repo.get_by_content_hash(content_hash)
        missing = await repo.get_by_content_hash("0" * 64)

        assert found is not None
        assert found.id == inserted.id
        assert missing is None


async def test_get_by_id(session_factory) -> None:
    body = _sample_locked_intent_body()

    async with session_factory() as session:
        repo = LockedIntentRepo(session)
        inserted = await repo.insert_if_absent(body)
        await session.commit()
        entity_id = inserted.id

    async with session_factory() as session:
        repo = LockedIntentRepo(session)
        found = await repo.get_by_id(entity_id)
        missing = await repo.get_by_id(uuid.uuid4())

        assert found is not None
        assert found.id == entity_id
        assert found.source_read == body["source_read"]
        assert missing is None


async def test_update_refusal(session_factory) -> None:
    body = _sample_locked_intent_body()

    async with session_factory() as session:
        repo = LockedIntentRepo(session)
        inserted = await repo.insert_if_absent(body)
        await session.commit()
        entity_id = inserted.id
        original_attrs = dict(inserted.attributes)

    async with session_factory() as session:
        repo = LockedIntentRepo(session)
        with pytest.raises(ImmutableArtifactError) as exc:
            await repo.update(entity_id, {"source_read": {"tampered": True}})

        assert "orch_locked_intent" in str(exc.value)
        assert "update" in str(exc.value)

        entity = await session.get(DBEntity, entity_id)
        assert entity is not None
        assert entity.attributes == original_attrs


async def test_delete_refusal(session_factory) -> None:
    body = _sample_locked_intent_body()

    async with session_factory() as session:
        repo = LockedIntentRepo(session)
        inserted = await repo.insert_if_absent(body)
        await session.commit()
        entity_id = inserted.id

    async with session_factory() as session:
        repo = LockedIntentRepo(session)
        with pytest.raises(ImmutableArtifactError) as exc:
            await repo.delete(entity_id)

        assert "orch_locked_intent" in str(exc.value)
        assert "delete" in str(exc.value)

        entity = await session.get(DBEntity, entity_id)
        assert entity is not None


async def test_entity_type_isolation(session_factory) -> None:
    body = _sample_locked_intent_body()

    async with session_factory() as session:
        intent_repo = LockedIntentRepo(session)
        inserted = await intent_repo.insert_if_absent(body)
        await session.commit()
        content_hash = inserted.content_hash

    async with session_factory() as session:
        rule_repo = _RuleSnapshotRepo(session)
        assert await rule_repo.get_by_content_hash(content_hash) is None

        entity = await session.scalar(
            select(DBEntity).where(
                DBEntity.entity_type == "orch_locked_intent",
                DBEntity.content_hash == content_hash,
            )
        )
        assert entity is not None
        assert entity.entity_type == "orch_locked_intent"


async def test_name_and_status_defaults(session_factory) -> None:
    body = _sample_locked_intent_body()

    async with session_factory() as session:
        repo = LockedIntentRepo(session)
        inserted = await repo.insert_if_absent(body)
        await session.commit()

        assert inserted.status == "locked"
        assert inserted.name == f"orch_locked_intent:{inserted.content_hash[:12]}"
        assert inserted.name.startswith("orch_locked_intent:")


async def test_project_scoped_insert(session_factory, seeded_project) -> None:
    body = _sample_locked_intent_body()

    async with session_factory() as session:
        repo = LockedIntentRepo(session)
        scoped = await repo.insert_if_absent(body, project_id=seeded_project)
        unscoped = await repo.insert_if_absent(
            _sample_locked_intent_body(escalation_threshold=0.5),
            project_id=None,
        )
        await session.commit()

        assert scoped.project_id == seeded_project
        assert unscoped.project_id is None


async def test_db_orch_locked_intent_typed_accessors(session_factory) -> None:
    body = _sample_locked_intent_body()

    async with session_factory() as session:
        repo = LockedIntentRepo(session)
        inserted = await repo.insert_if_absent(body)
        await session.commit()

        assert isinstance(inserted, DBOrchLockedIntent)
        assert inserted.change_manifest == body["change_manifest"]
        assert inserted.success_criteria[0]["measurement_spec"] == {
            "method": "temporal_ioU"
        }
        assert inserted.deliverable_spec == body["deliverable_spec"]
