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
