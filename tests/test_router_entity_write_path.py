"""Entity write-path behaviour over the WS router (#266, #267).

Drives the real ``Router`` handlers against the per-test Postgres database
(``session_factory``); ``get_session`` is patched to that factory and the
connection manager is a mock, so no WebSocket listener is needed.
"""
from __future__ import annotations

import re
import uuid
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from forge_bridge.core import Project, Registry, Status
from forge_bridge.mcp import tools
from forge_bridge.server.protocol import MsgType, entity_create, entity_get, entity_update
from forge_bridge.store.repo import EventRepo, ProjectRepo


# ─────────────────────────────────────────────────────────────
# #267 — advertised shot statuses are the canonical vocabulary
# ─────────────────────────────────────────────────────────────

def _advertised_statuses(description: str) -> list[str]:
    _, _, tail = description.partition("One of:")
    values = tail.split("(")[0]
    return [v.strip() for v in values.split(",") if v.strip()]


@pytest.mark.parametrize("model", [tools.ListShotsInput, tools.UpdateShotStatusInput])
def test_every_advertised_shot_status_parses(model):
    description = model.model_fields["status"].description
    advertised = _advertised_statuses(description)
    assert advertised == [s.value for s in Status]
    for value in advertised:
        assert Status.from_string(value).value == value


def test_update_shot_status_docstring_does_not_hand_list_statuses():
    doc = tools.update_shot_status.__doc__ or ""
    assert not re.search(r"pending,\s*in_progress", doc)


def test_on_hold_is_canonical_and_hold_aliases_it():
    assert Status.from_string("on_hold") is Status.ON_HOLD
    assert Status.from_string("hold") is Status.ON_HOLD
    assert Status.from_string("HOLD") is Status.ON_HOLD


def test_entity_update_wire_shape_unchanged_without_note():
    assert "note" not in entity_update("abc", status="review")
    assert entity_update("abc", status="review", note="client asked")["note"] == "client asked"


# ─────────────────────────────────────────────────────────────
# Router harness
# ─────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def router(session_factory, monkeypatch):
    from forge_bridge.server import router as router_module

    @asynccontextmanager
    async def session_scope():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    monkeypatch.setattr(router_module, "get_session", session_scope)
    connections = MagicMock()
    connections.broadcast_event = AsyncMock()
    return router_module.Router(connections, Registry.default())


@pytest.fixture
def client():
    return SimpleNamespace(client_name="test", session_id=uuid.uuid4())


@pytest_asyncio.fixture
async def project_id(session_factory):
    project = Project(name="Write Path", code=f"WP{uuid.uuid4().hex[:8]}")
    async with session_factory() as session:
        await ProjectRepo(session).save(project)
        await session.commit()
    return str(project.id)


async def _create(router, client, project_id, entity_type, attributes, name="E010"):
    resp = await router._handle_entity_create(
        entity_create(entity_type, project_id, attributes, name=name), client,
    )
    assert resp["type"] == MsgType.OK, resp
    return resp["result"]["entity_id"]


async def _update(router, client, entity_id, **kwargs):
    resp = await router._handle_entity_update(entity_update(entity_id, **kwargs), client)
    assert resp["type"] == MsgType.OK, resp
    return resp


async def _get(router, client, entity_id) -> dict:
    resp = await router._handle_entity_get(entity_get(entity_id), client)
    assert resp["type"] == MsgType.OK, resp
    return resp["result"]


async def _last_update_event(session_factory, entity_id) -> dict:
    async with session_factory() as session:
        events = await EventRepo(session).get_recent(
            event_type="entity.updated", entity_id=uuid.UUID(entity_id), limit=1,
        )
    assert events
    return events[0].payload


# ─────────────────────────────────────────────────────────────
# #267 — status update over the router
# ─────────────────────────────────────────────────────────────

async def test_on_hold_status_update_and_note_reach_event(router, client, project_id, session_factory):
    shot_id = await _create(router, client, project_id, "shot", {})

    await _update(router, client, shot_id, status="on_hold", note="waiting on plates")

    assert (await _get(router, client, shot_id))["status"] == "on_hold"
    payload = await _last_update_event(session_factory, shot_id)
    assert payload["status"] == "on_hold"
    assert payload["note"] == "waiting on plates"


async def test_update_without_note_leaves_event_payload_unannotated(router, client, project_id, session_factory):
    shot_id = await _create(router, client, project_id, "shot", {})

    await _update(router, client, shot_id, status="review")

    assert "note" not in await _last_update_event(session_factory, shot_id)


# ─────────────────────────────────────────────────────────────
# #266 — custom attributes survive create/update; metadata merge-patches
# ─────────────────────────────────────────────────────────────

# Entity types whose entity.create preserves non-typed attributes in metadata.
_METADATA_TYPES = {
    "shot":    {"cut_in": "01:00:00:00", "cut_out": "01:00:04:00"},
    "asset":   {"asset_type": "vehicle"},
    "version": {"iteration": 1},
    "media":   {"format": "EXR"},
}
_EXTERNAL_REF = {"system": "nim", "id": 123}


@pytest.mark.parametrize("entity_type", sorted(_METADATA_TYPES))
async def test_create_preserves_extra_attribute(router, client, project_id, entity_type):
    attrs = {**_METADATA_TYPES[entity_type], "external_ref": _EXTERNAL_REF}
    entity_id = await _create(router, client, project_id, entity_type, attrs)

    got = await _get(router, client, entity_id)
    assert got["metadata"]["external_ref"] == _EXTERNAL_REF


async def test_create_shot_keeps_typed_fields_out_of_metadata(router, client, project_id):
    shot_id = await _create(
        router, client, project_id, "shot",
        {**_METADATA_TYPES["shot"], "external_ref": _EXTERNAL_REF},
    )
    got = await _get(router, client, shot_id)
    assert not {"cut_in", "cut_out", "sequence_id"} & set(got["metadata"])
    assert got["cut_in"] is not None


@pytest.mark.parametrize("entity_type", sorted(_METADATA_TYPES))
async def test_update_stores_unknown_attribute(router, client, project_id, entity_type):
    entity_id = await _create(router, client, project_id, entity_type, _METADATA_TYPES[entity_type])

    await _update(router, client, entity_id, attributes={"external_ref": _EXTERNAL_REF})

    got = await _get(router, client, entity_id)
    assert got["metadata"]["external_ref"] == _EXTERNAL_REF


@pytest.mark.parametrize("entity_type", sorted(_METADATA_TYPES))
async def test_update_metadata_merges_rather_than_replaces(router, client, project_id, entity_type):
    entity_id = await _create(
        router, client, project_id, entity_type, {**_METADATA_TYPES[entity_type], "a": 1},
    )

    await _update(router, client, entity_id, attributes={"metadata": {"b": 2}})

    got = await _get(router, client, entity_id)
    assert got["metadata"]["a"] == 1
    assert got["metadata"]["b"] == 2


@pytest.mark.parametrize("entity_type", sorted(_METADATA_TYPES))
async def test_update_metadata_null_deletes_key(router, client, project_id, entity_type):
    entity_id = await _create(
        router, client, project_id, entity_type, {**_METADATA_TYPES[entity_type], "a": 1, "b": 2},
    )

    await _update(router, client, entity_id, attributes={"metadata": {"a": None}})

    got = await _get(router, client, entity_id)
    assert "a" not in got["metadata"]
    assert got["metadata"]["b"] == 2


async def test_update_metadata_merges_nested_dicts(router, client, project_id):
    version_id = await _create(
        router, client, project_id, "version",
        {"iteration": 1, "lock": {"locked_by": "alice", "locked_on_machine": "ws-01"}},
    )

    await _update(router, client, version_id,
                  attributes={"metadata": {"lock": {"locked_by": "bob", "locked_on_machine": None}}})

    got = await _get(router, client, version_id)
    assert got["metadata"]["lock"] == {"locked_by": "bob"}


async def test_update_rejects_non_object_metadata(router, client, project_id):
    shot_id = await _create(router, client, project_id, "shot", {})
    resp = await router._handle_entity_update(
        entity_update(shot_id, attributes={"metadata": "nope"}), client,
    )
    assert resp["type"] == MsgType.ERROR


async def test_mcp_update_asset_stores_attributes_through_router(router, client, project_id, monkeypatch):
    class _RouterClient:
        async def request(self, msg):
            resp = await router._dispatch[msg.type](msg, client)
            assert resp["type"] == MsgType.OK, resp
            return resp.get("result") or {}

    monkeypatch.setattr(tools, "_client", lambda: _RouterClient())
    asset_id = await _create(router, client, project_id, "asset", {"asset_type": "vehicle", "a": 1})

    await tools.update_asset(tools.UpdateAssetInput(asset_id=asset_id, attributes={"external_ref": _EXTERNAL_REF}))

    got = await _get(router, client, asset_id)
    assert got["asset_type"] == "vehicle"
    assert got["metadata"] == {"a": 1, "external_ref": _EXTERNAL_REF}


def test_merge_patch_does_not_mutate_target():
    from forge_bridge.server.router import _merge_patch

    target = {"a": {"x": 1}, "b": 2}
    assert _merge_patch(target, {"a": {"y": 2}, "b": None}) == {"a": {"x": 1, "y": 2}}
    assert target == {"a": {"x": 1}, "b": 2}


# ─────────────────────────────────────────────────────────────
# #270 — attributes allowlist: protected keys, coercion, methods
# ─────────────────────────────────────────────────────────────

async def _update_error(router, client, entity_id, **kwargs):
    resp = await router._handle_entity_update(entity_update(entity_id, **kwargs), client)
    assert resp["type"] == MsgType.ERROR, resp
    assert resp["code"] == "INVALID", resp
    return resp


async def _snapshot(router, client, entity_id) -> dict:
    # created_at is not persisted on entities (re-stamped on every load).
    got = await _get(router, client, entity_id)
    got.pop("created_at", None)
    return got


async def _entity_count(session_factory) -> int:
    from sqlalchemy import func, select

    from forge_bridge.store.models import DBEntity

    async with session_factory() as session:
        return (await session.execute(select(func.count()).select_from(DBEntity))).scalar_one()


@pytest.mark.parametrize("key, value", [
    ("id", str(uuid.uuid4())),
    ("entity_type", "version"),
    ("created_at", "2020-01-01T00:00:00"),
    ("project_id", str(uuid.uuid4())),
    ("to_dict", 1),
    ("add_relationship", 1),
    ("duration", 10),
    ("_relationships", []),
])
async def test_update_rejects_protected_key_and_mutates_nothing(
    router, client, project_id, key, value,
):
    shot_id = await _create(router, client, project_id, "shot", {"cut_in": "01:00:00:00", "a": 1})
    before = await _snapshot(router, client, shot_id)

    # The rejected key rides with valid changes; none of them may land.
    resp = await _update_error(router, client, shot_id, name="RENAMED", status="review",
                               attributes={"b": 2, key: value})

    assert key in resp["message"]
    assert await _snapshot(router, client, shot_id) == before


async def test_update_id_cannot_create_or_clobber_another_entity(router, client, project_id, session_factory):
    shot_id = await _create(router, client, project_id, "shot", {}, name="SHOT")
    version_id = await _create(router, client, project_id, "version", {"iteration": 1}, name="VER")
    version_before = await _snapshot(router, client, version_id)
    count = await _entity_count(session_factory)

    await _update_error(router, client, shot_id, name="HIJACK", attributes={"id": version_id})
    await _update_error(router, client, shot_id, name="DUPE", attributes={"id": str(uuid.uuid4())})

    assert await _entity_count(session_factory) == count
    assert await _snapshot(router, client, version_id) == version_before
    assert (await _get(router, client, shot_id))["name"] == "SHOT"


async def test_update_status_in_attributes_is_validated(router, client, project_id):
    shot_id = await _create(router, client, project_id, "shot", {})

    await _update_error(router, client, shot_id, attributes={"status": "anything"})
    assert (await _get(router, client, shot_id))["status"] == "pending"

    await _update(router, client, shot_id, attributes={"status": "hold"})
    got = await _get(router, client, shot_id)
    assert got["status"] == "on_hold"
    assert "status" not in got["metadata"]


async def test_update_invalid_top_level_status_is_invalid(router, client, project_id):
    shot_id = await _create(router, client, project_id, "shot", {})
    await _update_error(router, client, shot_id, status="anything")
    assert (await _get(router, client, shot_id))["status"] == "pending"


async def test_update_name_in_attributes_applies_like_top_level(router, client, project_id):
    shot_id = await _create(router, client, project_id, "shot", {}, name="OLD")

    await _update(router, client, shot_id, attributes={"name": "NEW"})

    got = await _get(router, client, shot_id)
    assert got["name"] == "NEW"
    assert "name" not in got["metadata"]


async def test_update_coerces_shot_typed_fields(router, client, project_id):
    seq_id = await _create(router, client, project_id, "sequence", {})
    shot_id = await _create(router, client, project_id, "shot", {"cut_in": "01:00:00:00"})

    await _update(router, client, shot_id, attributes={
        "cut_in": "01:00:01:00", "cut_out": "01:00:03:00", "sequence_id": seq_id,
    })

    got = await _get(router, client, shot_id)
    assert got["cut_in"]["timecode"] == "01:00:01:00"
    assert got["cut_out"]["timecode"] == "01:00:03:00"
    assert got["duration_frames"] == 48
    assert got["sequence_id"] == seq_id
    assert not {"cut_in", "cut_out", "sequence_id"} & set(got["metadata"])


async def test_update_coerces_version_and_media_typed_fields(router, client, project_id):
    version_id = await _create(router, client, project_id, "version", {"iteration": 1})
    media_id = await _create(router, client, project_id, "media", {"format": "EXR"})

    await _update(router, client, version_id, attributes={"version_number": "3"})
    await _update(router, client, media_id, attributes={
        "frame_range": {"start": 1001, "end": 1100, "fps": "24"}, "version_id": version_id,
    })

    assert (await _get(router, client, version_id))["version_number"] == 3
    media = await _get(router, client, media_id)
    assert media["frame_range"]["start"] == 1001 and media["frame_range"]["end"] == 1100
    assert media["version_id"] == version_id


@pytest.mark.parametrize("entity_type, create_attrs, attributes", [
    ("shot",     {}, {"cut_in": "not a timecode"}),
    ("shot",     {}, {"cut_in": 86400}),
    ("shot",     {}, {"sequence_id": "not-a-uuid"}),
    ("shot",     {}, {"name": None}),
    ("version",  {"iteration": 1}, {"version_number": "three"}),
    ("version",  {"iteration": 1}, {"version_number": True}),
    ("media",    {"format": "EXR"}, {"frame_range": {"start": 1100, "end": 1001}}),
    ("media",    {"format": "EXR"}, {"frame_range": "1001-1100"}),
    ("sequence", {}, {"frame_rate": "fast"}),
])
async def test_update_rejects_bad_typed_value(router, client, project_id, entity_type, create_attrs, attributes):
    entity_id = await _create(router, client, project_id, entity_type, create_attrs)
    before = await _snapshot(router, client, entity_id)

    resp = await _update_error(router, client, entity_id, attributes=attributes)

    assert next(iter(attributes)) in resp["message"]
    assert await _snapshot(router, client, entity_id) == before


async def test_mcp_update_asset_does_not_replay_protected_metadata_keys(
    router, client, project_id, monkeypatch,
):
    class _RouterClient:
        async def request(self, msg):
            resp = await router._dispatch[msg.type](msg, client)
            assert resp["type"] == MsgType.OK, resp
            return resp.get("result") or {}

    monkeypatch.setattr(tools, "_client", lambda: _RouterClient())
    # entity.create keeps unknown keys in metadata, including protected names.
    asset_id = await _create(router, client, project_id, "asset",
                             {"asset_type": "vehicle", "created_at": "legacy"})

    result = await tools.update_asset(tools.UpdateAssetInput(asset_id=asset_id, attributes={"b": 2}))

    assert "error" not in result
    got = await _get(router, client, asset_id)
    assert got["metadata"] == {"created_at": "legacy", "b": 2}


async def test_update_rejects_non_object_attributes(router, client, project_id):
    shot_id = await _create(router, client, project_id, "shot", {})
    await _update_error(router, client, shot_id, attributes=["cut_in"])
