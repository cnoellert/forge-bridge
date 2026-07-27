"""#242 — migration 0016 shape + the generic workflow-record repo.

The migration assertions follow the 0009/0014 idiom (import the module, pin the
revision chain and the index identity). The repo assertions need live Postgres
via the ``session_factory`` fixture and are skipped without it.
"""

from __future__ import annotations

import importlib
import re

import pytest
from sqlalchemy import select

from forge_bridge.store.models import DBEntity
from forge_bridge.store.orch_workflow_record_repo import (
    ENTITY_TYPE,
    OrchWorkflowRecordExists,
    OrchWorkflowRecordNotFound,
    OrchWorkflowRecordRepo,
)


_KIND = "bridge.editorial_workspace.publish_workflow"
_OTHER_KIND = "bridge.some_other.workflow"


def _migration():
    return importlib.import_module(
        "forge_bridge.store.migrations.versions.0016_orch_workflow_record"
    )


def _quoted_types(check: str) -> list[str]:
    return re.findall(r"'([^']+)'", check)


# --------------------------------------------------------------------------- #
# Migration shape
# --------------------------------------------------------------------------- #
def test_migration_0016_revision_chain_and_scope() -> None:
    migration = _migration()

    assert migration.revision == "0016"
    assert migration.down_revision == "0015"
    assert migration.INDEX_NAME == (
        "uq_entities_orch_workflow_record_kind_proposal_id"
    )
    assert migration.INDEX_EXPRESSIONS == (
        "(attributes ->> 'kind')",
        "(attributes ->> 'proposal_id')",
    )
    assert migration.INDEX_PREDICATE == (
        "entity_type = 'orch_workflow_record' "
        "AND attributes ? 'kind' "
        "AND attributes ? 'proposal_id'"
    )


def test_migration_0016_adds_exactly_one_entity_type() -> None:
    migration = _migration()

    pre = _quoted_types(
        migration._entity_type_check(migration._PRE_242_ENTITY_TYPES)
    )
    post = _quoted_types(
        migration._entity_type_check(migration._POST_242_ENTITY_TYPES)
    )

    assert set(post) - set(pre) == {"orch_workflow_record"}
    assert len(post) == len(pre) + 1
    assert post == sorted(post)
    # 0015's shipped type is carried forward untouched — no data migration.
    assert "editorial_edit_workflow" in pre
    assert "editorial_edit_workflow" in post


def test_migration_0016_matches_the_orm_entity_types() -> None:
    from forge_bridge.store.models import ENTITY_TYPES

    migration = _migration()

    assert ENTITY_TYPE in ENTITY_TYPES
    assert set(migration._POST_242_ENTITY_TYPES) == set(ENTITY_TYPES)


# --------------------------------------------------------------------------- #
# Repo behaviour (live Postgres)
# --------------------------------------------------------------------------- #
def _record(proposal_id: str, **extra) -> dict:
    record = {
        "proposal_id": proposal_id,
        "workflow_id": f"wf-{proposal_id}",
        "status": "proposed",
        "authority_fingerprint": "a" * 64,
    }
    record.update(extra)
    return record


@pytest.mark.asyncio
async def test_repo_round_trips_and_stamps_the_kind(session_factory) -> None:
    async with session_factory() as session:
        repo = OrchWorkflowRecordRepo(session, kind=_KIND)

        created = await repo.create(_record("epw_1"))
        assert created["kind"] == _KIND

        loaded = await repo.get_by_proposal_id("epw_1")
        assert loaded is not None
        assert loaded["workflow_id"] == "wf-epw_1"
        assert loaded["status"] == "proposed"

        entity = (
            await session.execute(
                select(DBEntity).where(DBEntity.entity_type == ENTITY_TYPE)
            )
        ).scalar_one()
        assert entity.status == "proposed"
        assert entity.name == f"{_KIND}:epw_1"
        assert entity.content_hash is None


@pytest.mark.asyncio
async def test_repo_update_promotes_status_and_keeps_kind(
    session_factory,
) -> None:
    async with session_factory() as session:
        repo = OrchWorkflowRecordRepo(session, kind=_KIND)
        await repo.create(_record("epw_2"))

        updated = await repo.update(
            "epw_2", {"status": "applied", "kind": "spoofed", "extra": 1}
        )

        assert updated["status"] == "applied"
        assert updated["kind"] == _KIND
        assert updated["extra"] == 1
        assert updated["workflow_id"] == "wf-epw_2"

        entity = (
            await session.execute(
                select(DBEntity).where(DBEntity.entity_type == ENTITY_TYPE)
            )
        ).scalar_one()
        assert entity.status == "applied"


@pytest.mark.asyncio
async def test_repo_duplicate_proposal_fails_closed(session_factory) -> None:
    async with session_factory() as session:
        repo = OrchWorkflowRecordRepo(session, kind=_KIND)
        await repo.create(_record("epw_3"))

        with pytest.raises(OrchWorkflowRecordExists):
            await repo.create(_record("epw_3"))


@pytest.mark.asyncio
async def test_repo_is_scoped_by_kind(session_factory) -> None:
    """The kind discriminator is what lets a second workflow family (#241)
    reuse this row family with no further migration."""
    async with session_factory() as session:
        mine = OrchWorkflowRecordRepo(session, kind=_KIND)
        theirs = OrchWorkflowRecordRepo(session, kind=_OTHER_KIND)

        await mine.create(_record("shared_id"))
        # Same proposal_id under a different kind is a DIFFERENT authority row.
        await theirs.create(_record("shared_id", workflow_id="other"))

        assert (await mine.get_by_proposal_id("shared_id"))["kind"] == _KIND
        other = await theirs.get_by_proposal_id("shared_id")
        assert other["kind"] == _OTHER_KIND
        assert other["workflow_id"] == "other"

        assert await mine.get_by_authority_fingerprint("a" * 64) is not None
        with pytest.raises(OrchWorkflowRecordNotFound):
            await OrchWorkflowRecordRepo(
                session, kind="bridge.absent"
            ).update("shared_id", {"status": "applied"})


@pytest.mark.asyncio
async def test_repo_authority_lookup_is_field_parameterized(
    session_factory,
) -> None:
    async with session_factory() as session:
        repo = OrchWorkflowRecordRepo(
            session, kind=_KIND, authority_field="publish_preview_fingerprint"
        )
        await repo.create(
            _record("epw_4", publish_preview_fingerprint="b" * 64)
        )

        assert await repo.get_by_authority_fingerprint("b" * 64) is not None
        assert await repo.get_by_authority_fingerprint("c" * 64) is None


def test_repo_requires_a_kind() -> None:
    with pytest.raises(ValueError):
        OrchWorkflowRecordRepo(object(), kind="  ")
