"""#274 slice 2 — scheduling records and queries over the WS router.

Drives the real ``Router`` against the per-test Postgres database, reusing the
harness from ``test_router_entity_write_path`` (``get_session`` patched to the
per-test ``session_factory``; connection manager mocked). Requests go through
``Router.dispatch`` so INVALID-vs-INTERNAL mapping is exercised end to end.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from forge_contracts.scheduling import (
    BID_LINE_KIND_LABOUR,
    BOOKING_STATE_CONFIRMED,
    BOOKING_STATE_PENCIL,
    CAPACITY_KIND_COUNTED,
    PROJECT_STATE_ON_HOLD,
    RESOURCE_KIND_PERSON,
    RESOURCE_KIND_ROOM,
    RESPONSIBILITY_PARTY_PERSON,
    RESPONSIBILITY_PARTY_VENDOR,
    TASK_SOURCING_INTERNAL,
)
from forge_contracts import TASK_STATE_COMPLETE

from forge_bridge.core import Project
from forge_bridge.server.protocol import (
    MsgType,
    entity_create,
    entity_get,
    entity_list,
    entity_update,
    project_create,
    project_get,
    project_list,
    project_update,
    query_bids,
    query_bookings,
    query_person_by_username,
    query_tasks,
)
from forge_bridge.store.repo import ProjectRepo
from tests.test_router_entity_write_path import (  # noqa: F401  (fixtures)
    _entity_count,
    client,
    project_id,
    router,
)

T0 = datetime(2026, 11, 2, 9, 0, tzinfo=timezone.utc)


def _at(hours: float) -> str:
    return (T0 + timedelta(hours=hours)).isoformat()


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

async def _send(router, client, msg) -> dict:
    return await router.dispatch(msg, client)


async def _ok(router, client, msg) -> dict:
    resp = await _send(router, client, msg)
    assert resp["type"] == MsgType.OK, dict(resp)
    return resp.get("result") or {}


async def _invalid(router, client, msg) -> dict:
    resp = await _send(router, client, msg)
    assert resp["type"] == MsgType.ERROR, dict(resp)
    assert resp["code"] == "INVALID", dict(resp)
    return resp


async def _create(router, client, entity_type, attributes, project_id=None, name=None, status=None):
    result = await _ok(router, client, entity_create(
        entity_type, project_id, attributes, name=name, status=status,
    ))
    return result["entity_id"]


async def _get(router, client, entity_id) -> dict:
    return await _ok(router, client, entity_get(entity_id))


async def _snapshot(router, client, entity_id) -> dict:
    got = await _get(router, client, entity_id)
    got.pop("created_at", None)  # re-stamped on every load
    return got


async def _other_project(session_factory) -> str:
    project = Project(name="Elsewhere", code=f"EL{uuid.uuid4().hex[:8]}")
    async with session_factory() as session:
        await ProjectRepo(session).save(project)
        await session.commit()
    return str(project.id)


@pytest.fixture
async def world(router, client, project_id):
    """One of everything a scheduling record can reference."""
    w = {"project": project_id}
    w["shot"] = await _create(router, client, "shot", {}, project_id, name="SH010")
    w["asset"] = await _create(router, client, "asset", {"asset_type": "prop"}, project_id, name="Car")
    person = await _ok(router, client, entity_create(
        "person", None, {"email": "ada@studio.io", "usernames": ["ada"]}, name="Ada",
    ))
    w["person"], w["facet"] = person["entity_id"], person["resource_id"]
    w["vendor"] = await _create(router, client, "vendor", {"contacts": []}, name="Acme VFX")
    w["room"] = await _create(router, client, "resource", {"resource_kind": RESOURCE_KIND_ROOM}, name="Suite 1")
    w["task"] = await _create(router, client, "task", {
        "owner_id": w["shot"], "owner_type": "shot", "task_type": "comp",
        "sourcing": TASK_SOURCING_INTERNAL,
    }, project_id)
    w["bid"] = await _create(router, client, "bid", {"version": 1, "currency": "usd"}, project_id)
    w["bid_line"] = await _create(router, client, "bid_line", {
        "bid_id": w["bid"], "kind": BID_LINE_KIND_LABOUR, "qty": "10", "rate": "650.00",
    }, project_id)
    return w


# ─────────────────────────────────────────────────────────────
# create / get / update / list per kind
# ─────────────────────────────────────────────────────────────

# kind → (project-scoped?, name, create attributes(world), update attributes, expected after update)
_KINDS = {
    "task": (True, None, lambda w: {
        "owner_id": w["asset"], "owner_type": "asset", "task_type": "model",
        "sourcing": TASK_SOURCING_INTERNAL,
    }, {"estimate": "1.5", "due_date": "2026-12-01"}, {"estimate": "1.5", "due_date": "2026-12-01"}),
    "responsibility": (True, None, lambda w: {
        "party_type": RESPONSIBILITY_PARTY_PERSON, "party_id": w["person"], "task_id": w["task"],
        "responsibility_type": "artist", "effective_from": "2026-11-01",
    }, {"effective_until": "2026-12-01"}, {"effective_until": "2026-12-01"}),
    "person": (False, "Grace", lambda w: {
        "email": "grace@studio.io", "usernames": ["grace"],
    }, {"usernames": ["grace", "ghopper"]}, {"usernames": ["grace", "ghopper"]}),
    "vendor": (False, "Outpost", lambda w: {"contacts": []},
               {"contacts": [{"name": "Bob"}]}, {"contacts": [{"name": "Bob"}]}),
    "resource": (False, "Suite 2", lambda w: {"resource_kind": RESOURCE_KIND_ROOM},
                 {"capacity_kind": CAPACITY_KIND_COUNTED}, {"capacity_kind": CAPACITY_KIND_COUNTED}),
    "resource_dependency": (False, None, lambda w: {
        "resource_type": "flame", "requires_type": "flame_licence",
    }, {"quantity": 2}, {"quantity": 2}),
    "booking": (True, "Comp suite", lambda w: {
        "starts_at": _at(0), "ends_at": _at(4), "resources": [{"resource_id": w["room"]}],
    }, {"ends_at": _at(6), "label": "Comp suite (ext)"}, {"ends_at": _at(6), "name": "Comp suite (ext)"}),
    "bid": (True, None, lambda w: {"version": 2, "currency": "eur"},
            {"is_awarded": True}, {"is_awarded": True, "currency": "EUR"}),
    "bid_line": (True, None, lambda w: {
        "bid_id": w["bid"], "kind": BID_LINE_KIND_LABOUR, "qty": "5", "rate": "600",
    }, {"rate": "700.50", "vendor_id": None}, {"rate": "700.50"}),
}


@pytest.mark.parametrize("kind", sorted(_KINDS))
async def test_create_get_update_list(router, client, world, kind):
    scoped, name, create_attrs, update_attrs, expected = _KINDS[kind]
    pid = world["project"] if scoped else None

    entity_id = await _create(router, client, kind, {**create_attrs(world), "external_ref": 7}, pid, name=name)
    got = await _get(router, client, entity_id)
    assert got["project_id"] == pid
    assert got["metadata"] == {"external_ref": 7}

    await _ok(router, client, entity_update(entity_id, attributes=update_attrs))
    got = await _get(router, client, entity_id)
    for key, value in expected.items():
        assert got[key] == value, key
    assert got["metadata"] == {"external_ref": 7}

    listed = await _ok(router, client, entity_list(kind, pid))
    assert entity_id in {e["id"] for e in listed["entities"]}


# ─────────────────────────────────────────────────────────────
# scope: studio-scoped kinds have no project; project-scoped need one
# ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("kind", ["person", "vendor", "resource", "resource_dependency"])
async def test_studio_scoped_kind_rejects_project_id(router, client, project_id, kind):
    _, name, create_attrs, _, _ = _KINDS[kind]
    resp = await _invalid(router, client, entity_create(kind, project_id, create_attrs({}), name=name))
    assert "studio-scoped" in resp["message"]
    resp = await _invalid(router, client, entity_list(kind, project_id))
    assert "studio-scoped" in resp["message"]


@pytest.mark.parametrize("kind", ["task", "responsibility", "booking", "bid", "bid_line"])
async def test_project_scoped_kind_requires_project_id(router, client, world, kind):
    _, name, create_attrs, _, _ = _KINDS[kind]
    resp = await _invalid(router, client, entity_create(kind, None, create_attrs(world), name=name))
    assert "project-scoped" in resp["message"]
    resp = await _invalid(router, client, entity_list(kind))
    assert "project-scoped" in resp["message"]


async def test_non_scheduling_list_still_requires_project_id(router, client):
    resp = await _invalid(router, client, entity_list("shot"))
    assert "project_id required" in resp["message"]


# ─────────────────────────────────────────────────────────────
# update allowlist: protected typed keys
# ─────────────────────────────────────────────────────────────

_PROTECTED = [
    ("task", "owner_id", lambda w: w["asset"]),
    ("task", "owner_type", lambda w: "asset"),
    ("responsibility", "party_type", lambda w: RESPONSIBILITY_PARTY_VENDOR),
    ("responsibility", "party_id", lambda w: w["vendor"]),
    ("responsibility", "task_id", lambda w: str(uuid.uuid4())),
    ("responsibility", "effective_from", lambda w: "2026-10-01"),
    ("resource", "resource_kind", lambda w: "workstation"),
    ("resource", "person_id", lambda w: w["person"]),
    ("resource_dependency", "resource_type", lambda w: "nuke"),
    ("resource_dependency", "requires_type", lambda w: "nuke_licence"),
    ("bid", "version", lambda w: 9),
    ("bid_line", "bid_id", lambda w: str(uuid.uuid4())),
    ("booking", "project_id", lambda w: str(uuid.uuid4())),
]


@pytest.mark.parametrize("kind, key, value", _PROTECTED, ids=[f"{k}.{f}" for k, f, _ in _PROTECTED])
async def test_update_rejects_protected_key_and_mutates_nothing(router, client, world, kind, key, value):
    scoped, name, create_attrs, update_attrs, _ = _KINDS[kind]
    entity_id = await _create(router, client, kind, create_attrs(world), world["project"] if scoped else None, name=name)
    before = await _snapshot(router, client, entity_id)

    # The rejected key rides with a valid change; neither may land.
    resp = await _invalid(router, client, entity_update(entity_id, attributes={**update_attrs, key: value(world)}))

    assert key in resp["message"]
    assert await _snapshot(router, client, entity_id) == before


# ─────────────────────────────────────────────────────────────
# coercion / validation failures are INVALID, never INTERNAL
# ─────────────────────────────────────────────────────────────

_BAD_UPDATES = [
    ("task", {"sourcing": "vendor"}),
    ("task", {"estimate": 1.5}),
    ("task", {"due_date": "soon"}),
    ("task", {"status": ""}),
    ("person", {"email": "not-an-email"}),
    ("person", {"usernames": "ada"}),
    ("vendor", {"contacts": ["Bob"]}),
    ("resource", {"capacity_kind": "shared"}),
    ("resource", {"availability": [{"kind": "down", "from": "2026-11-02", "until": "2026-11-01"}]}),
    ("resource_dependency", {"quantity": 0}),
    ("booking", {"ends_at": _at(-1)}),            # merged result: ends before starts
    ("booking", {"starts_at": "2026-11-02T09:00:00"}),  # naive
    ("booking", {"resources": []}),
    ("bid", {"is_active": "yes"}),
    ("bid", {"currency": "dollars"}),
    ("bid_line", {"qty": 1.5}),
    ("bid_line", {"rate": "lots"}),
    ("responsibility", {"effective_until": "2026-10-01"}),  # before effective_from
]


@pytest.mark.parametrize("kind, attributes", _BAD_UPDATES, ids=[f"{k}-{i}" for i, (k, _) in enumerate(_BAD_UPDATES)])
async def test_update_bad_value_is_invalid_and_mutates_nothing(router, client, world, kind, attributes):
    scoped, name, create_attrs, _, _ = _KINDS[kind]
    entity_id = await _create(router, client, kind, create_attrs(world), world["project"] if scoped else None, name=name)
    before = await _snapshot(router, client, entity_id)

    resp = await _invalid(router, client, entity_update(entity_id, attributes=attributes))

    assert next(iter(attributes)) in resp["message"]
    assert await _snapshot(router, client, entity_id) == before


_BAD_CREATES = [
    ("task", lambda w: {"owner_id": w["shot"], "owner_type": "shot", "task_type": "comp", "sourcing": "bogus"}),
    ("task", lambda w: {"owner_id": w["shot"], "owner_type": "shot", "task_type": "comp"}),  # missing sourcing
    ("booking", lambda w: {"starts_at": "2026-11-02T09:00:00", "ends_at": _at(4),
                           "resources": [{"resource_id": w["room"]}]}),
    ("bid", lambda w: {"version": 1, "currency": "usd", "is_active": "yes"}),
    ("bid", lambda w: {"version": 1, "currency": "usd", "id": str(uuid.uuid4())}),
    ("resource", lambda w: {"resource_kind": RESOURCE_KIND_PERSON}),  # person facet needs person_id
]


@pytest.mark.parametrize("kind, attributes", _BAD_CREATES, ids=[f"{k}-{i}" for i, (k, _) in enumerate(_BAD_CREATES)])
async def test_create_bad_value_is_invalid(router, client, world, session_factory, kind, attributes):
    scoped, name, _, _, _ = _KINDS[kind]
    count = await _entity_count(session_factory)
    await _invalid(router, client, entity_create(
        kind, world["project"] if scoped else None, attributes(world), name=name or "X",
    ))
    assert await _entity_count(session_factory) == count


@pytest.mark.parametrize("entity_type, attributes", [
    ("version", {"iteration": "three"}),
    ("shot", {"cut_in": "not a timecode"}),
])
async def test_non_scheduling_create_bad_value_is_invalid(router, client, project_id, entity_type, attributes):
    await _invalid(router, client, entity_create(entity_type, project_id, attributes, name="X"))


# ─────────────────────────────────────────────────────────────
# references: task owner, responsibility party, booking, bid_line
# ─────────────────────────────────────────────────────────────

async def test_task_owner_must_match_owner_type_and_project(router, client, world, session_factory):
    other = await _other_project(session_factory)
    foreign_shot = await _create(router, client, "shot", {}, other, name="SH999")
    count = await _entity_count(session_factory)
    base = {"task_type": "comp", "sourcing": TASK_SOURCING_INTERNAL}

    wrong_type = await _invalid(router, client, entity_create(
        "task", world["project"], {**base, "owner_id": world["shot"], "owner_type": "asset"},
    ))
    assert "owner_id" in wrong_type["message"] and "shot" in wrong_type["message"]
    other_project = await _invalid(router, client, entity_create(
        "task", world["project"], {**base, "owner_id": foreign_shot, "owner_type": "shot"},
    ))
    assert "another project" in other_project["message"]
    missing = await _invalid(router, client, entity_create(
        "task", world["project"], {**base, "owner_id": str(uuid.uuid4()), "owner_type": "shot"},
    ))
    assert "not found" in missing["message"]
    assert await _entity_count(session_factory) == count


@pytest.mark.parametrize("kind, attributes", [
    ("responsibility", lambda w: {"party_type": RESPONSIBILITY_PARTY_VENDOR, "party_id": w["person"],
                                  "task_id": w["task"], "responsibility_type": "artist",
                                  "effective_from": "2026-11-01"}),
    ("responsibility", lambda w: {"party_type": RESPONSIBILITY_PARTY_PERSON, "party_id": w["person"],
                                  "task_id": w["shot"], "responsibility_type": "artist",
                                  "effective_from": "2026-11-01"}),
    ("booking", lambda w: {"starts_at": _at(0), "ends_at": _at(1), "resources": [{"resource_id": w["person"]}]}),
    ("booking", lambda w: {"starts_at": _at(0), "ends_at": _at(1), "resources": [{"resource_id": w["room"]}],
                           "task_id": w["bid"]}),
    ("bid_line", lambda w: {"bid_id": w["task"], "kind": "labour", "qty": "1", "rate": "1"}),
    ("bid_line", lambda w: {"bid_id": w["bid"], "kind": "labour", "qty": "1", "rate": "1", "vendor_id": w["person"]}),
])
async def test_create_rejects_wrong_reference(router, client, world, session_factory, kind, attributes):
    count = await _entity_count(session_factory)
    await _invalid(router, client, entity_create(kind, world["project"], attributes(world)))
    assert await _entity_count(session_factory) == count


async def test_booking_update_to_unknown_resource_is_invalid(router, client, world):
    booking = await _create(router, client, "booking", _KINDS["booking"][2](world), world["project"])
    before = await _snapshot(router, client, booking)
    await _invalid(router, client, entity_update(
        booking, attributes={"resources": [{"resource_id": str(uuid.uuid4())}]},
    ))
    assert await _snapshot(router, client, booking) == before


# ─────────────────────────────────────────────────────────────
# states: task state raw; entity Status unchanged for shots
# ─────────────────────────────────────────────────────────────

async def test_task_complete_is_stored_raw(router, client, world):
    await _ok(router, client, entity_update(world["task"], status=TASK_STATE_COMPLETE))
    assert (await _get(router, client, world["task"]))["status"] == "complete"

    await _ok(router, client, entity_update(world["task"], status="In_Progress"))
    assert (await _get(router, client, world["task"]))["status"] == "in_progress"

    await _ok(router, client, entity_update(world["task"], attributes={"status": TASK_STATE_COMPLETE}))
    got = await _get(router, client, world["task"])
    assert got["status"] == "complete"
    assert "status" not in got["metadata"]


async def test_task_created_with_complete_status_stays_complete(router, client, world):
    task = await _create(router, client, "task", {
        "owner_id": world["shot"], "owner_type": "shot", "task_type": "roto",
        "sourcing": TASK_SOURCING_INTERNAL,
    }, world["project"], status=TASK_STATE_COMPLETE)
    assert (await _get(router, client, task))["status"] == "complete"


async def test_shot_complete_still_aliases_to_delivered(router, client, world):
    await _ok(router, client, entity_update(world["shot"], status="complete"))
    assert (await _get(router, client, world["shot"]))["status"] == "delivered"
    await _ok(router, client, entity_update(world["shot"], status="pending"))
    await _ok(router, client, entity_update(world["shot"], attributes={"status": "complete"}))
    assert (await _get(router, client, world["shot"]))["status"] == "delivered"


async def test_booking_state_update_reaches_index(router, client, world):
    booking = await _create(router, client, "booking", _KINDS["booking"][2](world), world["project"])
    assert (await _get(router, client, booking))["status"] == "planning"

    await _ok(router, client, entity_update(booking, status=BOOKING_STATE_PENCIL))
    assert (await _get(router, client, booking))["status"] == "pencil"
    await _ok(router, client, entity_update(booking, attributes={"status": "Tentative"}))  # open set
    assert (await _get(router, client, booking))["status"] == "tentative"
    await _ok(router, client, entity_update(booking, status=BOOKING_STATE_CONFIRMED))

    found = await _ok(router, client, query_bookings(
        resource_ids=[world["room"]], from_=_at(0), to=_at(1), states=[BOOKING_STATE_CONFIRMED],
    ))
    assert [b["id"] for b in found["bookings"]] == [booking]


# ─────────────────────────────────────────────────────────────
# person: bookable facet, uniqueness
# ─────────────────────────────────────────────────────────────

async def test_person_create_bookable_returns_linked_facet(router, client, world):
    facet = await _get(router, client, world["facet"])
    assert facet["entity_type"] == "resource"
    assert facet["resource_kind"] == RESOURCE_KIND_PERSON
    assert facet["person_id"] == world["person"]
    assert facet["project_id"] is None

    result = await _ok(router, client, entity_create(
        "person", None, {"email": "free@lance.io", "bookable": False}, name="Freelancer",
    ))
    assert result["resource_id"] is None


async def test_person_bookable_flag_must_be_bool(router, client, session_factory):
    count = await _entity_count(session_factory)
    await _invalid(router, client, entity_create(
        "person", None, {"email": "x@y.io", "bookable": "yes"}, name="X",
    ))
    assert await _entity_count(session_factory) == count


async def test_duplicate_email_is_invalid_and_writes_nothing(router, client, world, session_factory):
    count = await _entity_count(session_factory)
    resp = await _invalid(router, client, entity_create(
        "person", None, {"email": "ADA@studio.io"}, name="Ada Two",
    ))
    assert "person" in resp["message"]
    dup_user = await _invalid(router, client, entity_create(
        "person", None, {"email": "other@studio.io", "usernames": ["ada"]}, name="Other",
    ))
    assert "person" in dup_user["message"]
    assert await _entity_count(session_factory) == count


async def test_update_to_duplicate_email_is_invalid(router, client, world):
    other = await _create(router, client, "person", {"email": "lin@studio.io"}, name="Lin")
    before = await _snapshot(router, client, other)
    await _invalid(router, client, entity_update(other, attributes={"email": "ada@studio.io"}))
    assert await _snapshot(router, client, other) == before


# ─────────────────────────────────────────────────────────────
# project lifecycle
# ─────────────────────────────────────────────────────────────

async def test_project_lifecycle_create_update_and_list_filter(router, client):
    code = f"LC{uuid.uuid4().hex[:6]}"
    pid = (await _ok(router, client, project_create("Lifecycle", code, lifecycle_state="bidding")))["project_id"]
    assert (await _ok(router, client, project_get(pid)))["lifecycle_state"] == "bidding"

    await _ok(router, client, project_update(pid, lifecycle_state=PROJECT_STATE_ON_HOLD))
    assert (await _ok(router, client, project_get(pid)))["lifecycle_state"] == PROJECT_STATE_ON_HOLD

    default_pid = (await _ok(router, client, project_create("Default", f"DF{uuid.uuid4().hex[:6]}")))["project_id"]
    assert (await _ok(router, client, project_get(default_pid)))["lifecycle_state"] == "active"

    on_hold = await _ok(router, client, project_list(PROJECT_STATE_ON_HOLD))
    assert {p["id"] for p in on_hold["projects"]} == {pid}
    both = await _ok(router, client, project_list([PROJECT_STATE_ON_HOLD, "active"]))
    assert {pid, default_pid} <= {p["id"] for p in both["projects"]}
    everything = await _ok(router, client, project_list())
    assert {pid, default_pid} <= {p["id"] for p in everything["projects"]}

    # An update that leaves lifecycle_state out keeps it.
    await _ok(router, client, project_update(pid, name="Renamed"))
    assert (await _ok(router, client, project_get(pid)))["lifecycle_state"] == PROJECT_STATE_ON_HOLD


@pytest.mark.parametrize("state", ["", "   ", 5])
async def test_project_lifecycle_must_be_non_empty_string(router, client, state):
    await _invalid(router, client, project_create("Bad", f"BD{uuid.uuid4().hex[:6]}", lifecycle_state=state))
    pid = (await _ok(router, client, project_create("Ok", f"OK{uuid.uuid4().hex[:6]}")))["project_id"]
    await _invalid(router, client, project_update(pid, lifecycle_state=state))
    assert (await _ok(router, client, project_get(pid)))["lifecycle_state"] == "active"


# ─────────────────────────────────────────────────────────────
# queries
# ─────────────────────────────────────────────────────────────

async def test_query_bookings_range_overlap_is_half_open(router, client, world):
    other_room = await _create(router, client, "resource", {"resource_kind": RESOURCE_KIND_ROOM}, name="Suite 9")
    booking = await _create(router, client, "booking", {
        "starts_at": _at(0), "ends_at": _at(4),
        "resources": [{"resource_id": world["room"]}, {"resource_id": world["facet"]}],
    }, world["project"])

    async def ids(resource_ids, start, end, states=None):
        result = await _ok(router, client, query_bookings(
            resource_ids=resource_ids, from_=_at(start), to=_at(end), states=states,
        ))
        assert result["count"] == len(result["bookings"])
        return [b["id"] for b in result["bookings"]]

    assert await ids([world["room"]], 3, 5) == [booking]
    assert await ids([world["facet"]], -2, 1) == [booking]
    assert await ids([world["room"]], 4, 6) == []        # touches the end
    assert await ids([world["room"]], -2, 0) == []       # touches the start
    assert await ids([other_room], 0, 4) == []
    assert await ids([world["room"]], 0, 4, states=["confirmed"]) == []

    by_project = await _ok(router, client, query_bookings(project_id=world["project"]))
    assert [b["id"] for b in by_project["bookings"]] == [booking]


@pytest.mark.parametrize("kwargs", [
    {},
    {"resource_ids": ["x"], "from_": _at(0), "to": _at(1)},
    {"resource_ids": [str(uuid.uuid4())], "from_": "2026-11-02T09:00:00", "to": _at(1)},
    {"resource_ids": [str(uuid.uuid4())], "from_": _at(2), "to": _at(1)},
    {"resource_ids": [str(uuid.uuid4())], "from_": _at(0)},
    {"resource_ids": [str(uuid.uuid4())], "from_": _at(0), "to": _at(1), "project_id": str(uuid.uuid4())},
    {"project_id": "nope"},
])
async def test_query_bookings_bad_input_is_invalid(router, client, kwargs):
    await _invalid(router, client, query_bookings(**kwargs))


async def test_query_tasks_by_party_owner_and_project(router, client, world):
    asset_task = await _create(router, client, "task", {
        "owner_id": world["asset"], "owner_type": "asset", "task_type": "model",
        "sourcing": TASK_SOURCING_INTERNAL,
    }, world["project"])
    await _create(router, client, "responsibility", {
        "party_type": RESPONSIBILITY_PARTY_PERSON, "party_id": world["person"], "task_id": world["task"],
        "responsibility_type": "artist", "effective_from": "2026-11-01", "effective_until": "2026-11-30",
    }, world["project"])

    async def ids(**kwargs):
        result = await _ok(router, client, query_tasks(**kwargs))
        return [t["id"] for t in result["tasks"]]

    assert await ids(party_type="person", party_id=world["person"]) == [world["task"]]
    assert await ids(party_type="person", party_id=world["person"], on="2026-11-15") == [world["task"]]
    assert await ids(party_type="person", party_id=world["person"], on="2026-12-15") == []
    assert await ids(party_type="vendor", party_id=world["vendor"]) == []
    assert await ids(owner_id=world["asset"]) == [asset_task]
    assert set(await ids(project_id=world["project"])) == {world["task"], asset_task}


@pytest.mark.parametrize("kwargs", [
    {},
    {"owner_id": str(uuid.uuid4()), "project_id": str(uuid.uuid4())},
    {"party_type": "robot", "party_id": str(uuid.uuid4())},
    {"party_type": "person"},
    {"owner_id": str(uuid.uuid4()), "on": "2026-11-01"},
    {"party_type": "person", "party_id": str(uuid.uuid4()), "on": "someday"},
])
async def test_query_tasks_bad_input_is_invalid(router, client, kwargs):
    await _invalid(router, client, query_tasks(**kwargs))


async def test_query_bids_filters_and_lines(router, client, world):
    awarded = await _create(router, client, "bid", {
        "version": 2, "currency": "usd", "is_active": True, "is_awarded": True,
    }, world["project"])

    all_bids = await _ok(router, client, query_bids(world["project"]))
    assert [b["id"] for b in all_bids["bids"]] == [world["bid"], awarded]
    assert "lines" not in all_bids["bids"][0]

    only_awarded = await _ok(router, client, query_bids(world["project"], awarded=True))
    assert [b["id"] for b in only_awarded["bids"]] == [awarded]
    inactive = await _ok(router, client, query_bids(world["project"], active=False))
    assert [b["id"] for b in inactive["bids"]] == [world["bid"]]

    with_lines = await _ok(router, client, query_bids(world["project"], include_lines=True))
    lines = {b["id"]: b["lines"] for b in with_lines["bids"]}
    assert [line["id"] for line in lines[world["bid"]]] == [world["bid_line"]]
    assert lines[world["bid"]][0]["rate"] == "650.00"
    assert lines[awarded] == []

    await _invalid(router, client, query_bids(world["project"], active="yes"))
    await _invalid(router, client, query_bids("nope"))


async def test_query_person_by_username(router, client, world):
    hit = await _ok(router, client, query_person_by_username("ada"))
    assert hit["person"]["id"] == world["person"]
    assert hit["resource_id"] == world["facet"]

    miss = await _ok(router, client, query_person_by_username("nobody"))
    assert miss == {"person": None, "resource_id": None}

    await _invalid(router, client, query_person_by_username(""))


# ─────────────────────────────────────────────────────────────
# wire builders
# ─────────────────────────────────────────────────────────────

def test_builders_omit_absent_optional_fields():
    assert "project_id" not in entity_list("person")
    assert entity_list("shot", "p-1")["project_id"] == "p-1"
    assert "lifecycle_state" not in project_create("P", "C")
    assert "lifecycle_state" not in project_list()
    assert set(project_update("p-1")) == {"type", "id", "project_id"}
    upd = project_update("p-1", lifecycle_state="on_hold")
    assert set(upd) == {"type", "id", "project_id", "lifecycle_state"}
    bookings = query_bookings(project_id="p-1")
    assert set(bookings) == {"type", "id", "project_id"}
    ranged = query_bookings(resource_ids=["r"], from_="a", to="b")
    assert (ranged["resource_ids"], ranged["from"], ranged["to"]) == (["r"], "a", "b")
    assert set(query_tasks(owner_id="o")) == {"type", "id", "owner_id"}
    assert query_bids("p-1")["include_lines"] is False
    assert query_person_by_username("ada")["username"] == "ada"
