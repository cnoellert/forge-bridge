"""#274 slice 3 — scheduling MCP tools.

Advertised state values are generated from the forge-contracts sets (#267
pattern), and every tool round-trips through the real ``Router`` against the
per-test Postgres database (harness from ``test_router_scheduling``), with
``tools._client`` swapped for a client that dispatches straight into the router.
"""
from __future__ import annotations

import json

import pytest
from forge_contracts import KNOWN_PROJECT_STATES, KNOWN_TASK_STATES, TASK_STATE_COMPLETE
from forge_contracts.scheduling import (
    BOOKING_STATE_CANCELLED,
    BOOKING_STATE_CONFIRMED,
    BOOKING_STATE_PENCIL,
    KNOWN_BOOKING_STATES,
    KNOWN_RESOURCE_KINDS,
    PROJECT_STATE_AWARDED,
    RESOURCE_KIND_PERSON,
    RESOURCE_KIND_ROOM,
    RESPONSIBILITY_PARTY_PERSON,
    TASK_SOURCING_INTERNAL,
)

from forge_bridge.mcp import tools
from forge_bridge.server.protocol import MsgType, entity_create, project_get
from tests.test_router_scheduling import (  # noqa: F401  (fixtures)
    _at,
    _create,
    _get,
    _ok,
    client,
    project_id,
    router,
    world,
)


# ─────────────────────────────────────────────────────────────
# Advertised states == contract sets
# ─────────────────────────────────────────────────────────────

def _advertised(description: str) -> list[str]:
    _, _, tail = description.partition("Known values include:")
    return [v.strip() for v in tail.split("(")[0].split(",") if v.strip()]


@pytest.mark.parametrize("model, field, known", [
    (tools.CreateTaskInput, "status", KNOWN_TASK_STATES),
    (tools.UpdateTaskStatusInput, "status", KNOWN_TASK_STATES),
    (tools.CreateBookingInput, "state", KNOWN_BOOKING_STATES),
    (tools.UpdateBookingStateInput, "state", KNOWN_BOOKING_STATES),
    (tools.ListBookingsInput, "states", KNOWN_BOOKING_STATES),
    (tools.SetProjectStateInput, "state", KNOWN_PROJECT_STATES),
    (tools.ListResourcesInput, "resource_kind", KNOWN_RESOURCE_KINDS),
])
def test_advertised_values_are_the_contract_set(model, field, known):
    description = model.model_fields[field].description
    assert _advertised(description) == sorted(known)
    assert "open set" in description


# ─────────────────────────────────────────────────────────────
# Router round-trips
# ─────────────────────────────────────────────────────────────

class _RouterError(Exception):
    pass


@pytest.fixture
def via_router(router, client, monkeypatch):
    """Point the MCP tools at the router; error replies raise like AsyncClient."""
    class _RouterClient:
        async def request(self, msg):
            resp = await router.dispatch(msg, client)
            if resp["type"] != MsgType.OK:
                raise _RouterError(resp.get("message") or dict(resp))
            return resp.get("result") or {}

    monkeypatch.setattr(tools, "_client", lambda: _RouterClient())


async def _call(fn, model, **kwargs) -> dict:
    payload = json.loads(await fn(model(**kwargs)))
    assert "error" not in payload, payload
    return payload


async def test_create_task_and_update_status_round_trip(router, client, world, via_router):
    created = await _call(
        tools.create_task, tools.CreateTaskInput,
        project_id=world["project"], owner_id=world["shot"], owner_type="shot",
        task_type="roto", sourcing=TASK_SOURCING_INTERNAL, due_date="2026-11-20",
    )
    task = await _get(router, client, created["task_id"])
    assert (task["task_type"], task["status"], task["due_date"]) == ("roto", "pending", "2026-11-20")

    await _call(tools.update_task_status, tools.UpdateTaskStatusInput,
                task_id=created["task_id"], status=TASK_STATE_COMPLETE)
    # Stored raw: never aliased to Status.DELIVERED.
    assert (await _get(router, client, created["task_id"]))["status"] == TASK_STATE_COMPLETE


async def test_update_task_status_refuses_a_non_task(world, via_router):
    payload = json.loads(await tools.update_task_status(
        tools.UpdateTaskStatusInput(task_id=world["shot"], status="review"),
    ))
    assert payload["code"] == "WRONG_ENTITY_TYPE"


async def test_create_task_surfaces_router_rejection(world, via_router):
    payload = json.loads(await tools.create_task(tools.CreateTaskInput(
        project_id=world["project"], owner_id=world["shot"], owner_type="shot",
        task_type="comp", sourcing="offshore",
    )))
    assert "sourcing" in payload["error"]


async def test_create_booking_and_update_state_round_trip(router, client, world, via_router):
    created = await _call(
        tools.create_booking, tools.CreateBookingInput,
        project_id=world["project"],
        resources=[{"resource_id": world["room"]}, {"resource_id": world["facet"]}],
        starts_at=_at(0), ends_at=_at(4), state=BOOKING_STATE_PENCIL,
        task_id=world["task"], label="Comp review",
    )
    booking = await _get(router, client, created["booking_id"])
    assert booking["status"] == BOOKING_STATE_PENCIL
    assert booking["name"] == "Comp review"
    assert {r["resource_id"] for r in booking["resources"]} == {world["room"], world["facet"]}

    await _call(tools.update_booking_state, tools.UpdateBookingStateInput,
                booking_id=created["booking_id"], state=BOOKING_STATE_CONFIRMED)
    assert (await _get(router, client, created["booking_id"]))["status"] == BOOKING_STATE_CONFIRMED


async def test_set_project_state_round_trip(router, client, world, via_router):
    await _call(tools.set_project_state, tools.SetProjectStateInput,
                project_id=world["project"], state=PROJECT_STATE_AWARDED)
    project = await _ok(router, client, project_get(world["project"]))
    assert project["lifecycle_state"] == PROJECT_STATE_AWARDED


async def test_list_tasks_by_project_owner_and_party(router, client, world, via_router):
    await _create(router, client, "responsibility", {
        "party_type": RESPONSIBILITY_PARTY_PERSON, "party_id": world["person"], "task_id": world["task"],
        "responsibility_type": "artist", "effective_from": "2026-11-01",
    }, world["project"])

    by_project = await _call(tools.list_tasks, tools.ListTasksInput, project_id=world["project"])
    by_owner = await _call(tools.list_tasks, tools.ListTasksInput, owner_id=world["shot"])
    by_party = await _call(tools.list_tasks, tools.ListTasksInput,
                           party_type=RESPONSIBILITY_PARTY_PERSON, party_id=world["person"], on="2026-11-05")
    for result in (by_project, by_owner, by_party):
        assert [t["id"] for t in result["tasks"]] == [world["task"]]
        assert result["count"] == 1


async def test_list_tasks_rejects_two_selectors(world, via_router):
    payload = json.loads(await tools.list_tasks(
        tools.ListTasksInput(project_id=world["project"], owner_id=world["shot"]),
    ))
    assert "error" in payload


async def test_list_bookings_by_resource_range_and_project(router, client, world, via_router):
    kept = await _create(router, client, "booking", {
        "starts_at": _at(0), "ends_at": _at(4), "resources": [{"resource_id": world["room"]}],
    }, world["project"], status=BOOKING_STATE_CONFIRMED)
    await _create(router, client, "booking", {
        "starts_at": _at(1), "ends_at": _at(2), "resources": [{"resource_id": world["room"]}],
    }, world["project"], status=BOOKING_STATE_CANCELLED)

    in_range = await _call(tools.list_bookings, tools.ListBookingsInput,
                           resource_ids=[world["room"]], start=_at(-1), end=_at(8),
                           states=[BOOKING_STATE_CONFIRMED])
    assert [b["id"] for b in in_range["bookings"]] == [kept]
    by_project = await _call(tools.list_bookings, tools.ListBookingsInput, project_id=world["project"])
    assert by_project["count"] == 2


async def test_list_resources_with_kind_filter(world, via_router):
    everything = await _call(tools.list_resources, tools.ListResourcesInput)
    assert {r["id"] for r in everything["resources"]} == {world["room"], world["facet"]}
    rooms = await _call(tools.list_resources, tools.ListResourcesInput, resource_kind=RESOURCE_KIND_ROOM)
    assert [r["id"] for r in rooms["resources"]] == [world["room"]]
    people = await _call(tools.list_resources, tools.ListResourcesInput, resource_kind=RESOURCE_KIND_PERSON)
    assert [r["person_id"] for r in people["resources"]] == [world["person"]]


async def test_get_person_by_id_and_username(router, client, world, via_router):
    by_id = await _call(tools.get_person, tools.GetPersonInput, person_id=world["person"])
    by_name = await _call(tools.get_person, tools.GetPersonInput, username="ada")
    for result in (by_id, by_name):
        assert result["person"]["id"] == world["person"]
        assert result["resource_id"] == world["facet"]

    unknown = await _call(tools.get_person, tools.GetPersonInput, username="nobody")
    assert unknown == {"person": None, "resource_id": None}

    not_bookable = await _ok(router, client, entity_create(
        "person", None, {"email": "lin@studio.io", "bookable": False}, name="Lin",
    ))
    lin = await _call(tools.get_person, tools.GetPersonInput, person_id=not_bookable["entity_id"])
    assert lin["resource_id"] is None


async def test_get_person_refuses_a_non_person(world, via_router):
    payload = json.loads(await tools.get_person(tools.GetPersonInput(person_id=world["room"])))
    assert payload["code"] == "WRONG_ENTITY_TYPE"


async def test_list_bids_exposes_full_lines_and_rates(router, client, world, via_router):
    # Several awarded bids per project are allowed (operator decision, #274).
    second = await _create(router, client, "bid", {
        "version": 2, "currency": "usd", "is_active": True, "is_awarded": True,
    }, world["project"])
    third = await _create(router, client, "bid", {
        "version": 3, "currency": "usd", "is_awarded": True,
    }, world["project"])

    awarded = await _call(tools.list_bids, tools.ListBidsInput, project_id=world["project"], awarded=True)
    assert {b["id"] for b in awarded["bids"]} == {second, third}
    assert all("lines" not in b for b in awarded["bids"])

    with_lines = await _call(tools.list_bids, tools.ListBidsInput,
                             project_id=world["project"], include_lines=True)
    first = next(b for b in with_lines["bids"] if b["id"] == world["bid"])
    assert [(line["id"], line["qty"], line["rate"]) for line in first["lines"]] == [
        (world["bid_line"], "10", "650.00"),
    ]
