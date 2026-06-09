"""Regression: entity.get / entity.list must hydrate locations + relationships.

The WS read seam (`entity.get` / `entity.list`, router.py) serializes `to_dict()`
straight off `EntityRepo._to_core`, which reconstructs only the `DBEntity` row.
Locations and outgoing relationships live in sibling tables and were never
attached, so the response reported `locations: []` / `relationships: []` even when
the store held rows — and `BridgeAssetClient.resolve_locations()` (the render-client
import path) always got nothing. See issue #22.
"""
from __future__ import annotations

import uuid

import pytest

from forge_bridge.core.traits import get_default_registry
from forge_bridge.store.models import (
    DBEntity,
    DBLocation,
    DBProject,
    DBRelationship,
)
from forge_bridge.store.repo import EntityRepo

_PATH = "/var/folders/xy/p36r_src_5q0zgkva.exr"


async def _seed(session) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """A media with one location row + one outgoing member_of edge."""
    project_id = uuid.uuid4()
    media_id = uuid.uuid4()
    version_id = uuid.uuid4()
    member_of = get_default_registry().relationships.get_key("member_of")

    session.add(DBProject(id=project_id, name="portofino", code="PORT"))
    session.add(DBEntity(id=media_id, entity_type="media", project_id=project_id,
                         name="p36r_src", status="pending", attributes={"role": "raw"}))
    session.add(DBEntity(id=version_id, entity_type="version", project_id=project_id,
                         name="v001", status="pending", attributes={}))
    # exists=None on purpose: every store row is NULL (never existence-checked);
    # the read surface must return it as-is, not filter it out.
    session.add(DBLocation(entity_id=media_id, path=_PATH, storage_type="local",
                           priority=0, exists=None, attributes={}))
    session.add(DBRelationship(source_id=media_id, target_id=version_id,
                               rel_type_key=member_of, attributes={}))
    await session.commit()
    return project_id, media_id, version_id


@pytest.mark.asyncio
async def test_entity_get_hydrates_locations_and_relationships(session_factory):
    async with session_factory() as session:
        _project_id, media_id, version_id = await _seed(session)

        entity = await EntityRepo(session, registry=None).get(media_id)
        assert entity is not None
        d = entity.to_dict()

        assert len(d["locations"]) == 1, "location row must be hydrated, not empty"
        assert d["locations"][0]["path"] == _PATH
        assert d["locations"][0]["exists"] is None  # NULL returned as-is

        assert len(d["relationships"]) == 1, "outgoing edge must be hydrated"
        assert d["relationships"][0]["target_id"] == str(version_id)
        assert d["relationships"][0]["type_name"] == "member_of"


@pytest.mark.asyncio
async def test_entity_list_hydrates_locations(session_factory):
    async with session_factory() as session:
        project_id, media_id, _version_id = await _seed(session)

        entities = await EntityRepo(session, registry=None).list_by_type(
            "media", project_id)
        media = [e for e in entities if e.id == media_id]
        assert len(media) == 1
        d = media[0].to_dict()
        assert len(d["locations"]) == 1
        assert d["locations"][0]["path"] == _PATH
