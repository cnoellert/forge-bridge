"""#274 slice 1 — scheduling records, derived indexes and queries.

Pure constructor-validation tests run anywhere; the rest need live Postgres via
the per-test ``session_factory`` fixture (ORM ``create_all``; migration parity is
pinned separately in ``test_migration_0017.py``) and skip without it.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from forge_contracts.scheduling import (
    BID_LINE_KIND_LABOUR,
    BOOKING_STATE_CANCELLED,
    BOOKING_STATE_CONFIRMED,
    BOOKING_STATE_PENCIL,
    CAPACITY_KIND_COUNTED,
    PROJECT_STATE_ON_HOLD,
    RESOURCE_KIND_LICENCE,
    RESOURCE_KIND_PERSON,
    RESOURCE_KIND_ROOM,
    RESPONSIBILITY_PARTY_PERSON,
    RESPONSIBILITY_PARTY_VENDOR,
    TASK_SOURCING_INTERNAL,
    TASK_SOURCING_OUTSOURCE,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from forge_bridge.core.entities import Project as CoreProject
from forge_bridge.core.scheduling import (
    SCHEDULING_CLASSES,
    Bid,
    BidLine,
    Booking,
    Person,
    Resource,
    ResourceDependency,
    Responsibility,
    Task,
    Vendor,
)
from forge_bridge.store.models import DBBookingResource, DBEntity, DBPersonUsername, DBProject
from forge_bridge.store.repo import EntityRepo, ProjectRepo
from forge_bridge.store.scheduling_repo import SchedulingRepo


T0 = datetime(2026, 11, 2, 9, 0, tzinfo=timezone.utc)


def _h(hours: float) -> datetime:
    return T0 + timedelta(hours=hours)


def _task(project_id, **kw) -> Task:
    base = dict(
        owner_id=uuid.uuid4(), owner_type="shot", task_type="comp",
        sourcing=TASK_SOURCING_INTERNAL, project_id=project_id,
    )
    base.update(kw)
    return Task(**base)


def _room(name="Suite 1", **kw) -> Resource:
    return Resource(name=name, resource_kind=RESOURCE_KIND_ROOM, **kw)


def _booking(project_id, resources, start=0, end=4, **kw) -> Booking:
    return Booking(
        project_id=project_id,
        starts_at=_h(start),
        ends_at=_h(end),
        resources=[
            r if isinstance(r, dict) else {"resource_id": r.id} for r in resources
        ],
        **kw,
    )


# --------------------------------------------------------------------------- #
# Constructor validation (no database)
# --------------------------------------------------------------------------- #
def test_every_kind_has_an_explicit_entity_type() -> None:
    for entity_type, cls in SCHEDULING_CLASSES.items():
        assert cls.ENTITY_TYPE == entity_type
    # The BridgeEntity default (class name lowercased) would be wrong here.
    dep = ResourceDependency(resource_type="suite", requires_type="nuke")
    assert dep.entity_type == "resource_dependency"
    line = BidLine(bid_id=uuid.uuid4(), kind="labour", qty="1", rate="1",
                   project_id=uuid.uuid4())
    assert line.entity_type == "bid_line"


@pytest.mark.parametrize(
    "factory",
    [
        lambda p: _task(p, sourcing="freelance"),
        lambda p: _task(p, owner_type="sequence"),
        lambda p: Responsibility(
            party_type="contractor", party_id=uuid.uuid4(), task_id=uuid.uuid4(),
            responsibility_type="artist", effective_from="2026-11-01", project_id=p,
        ),
        lambda p: Resource(name="x", resource_kind=RESOURCE_KIND_ROOM, capacity_kind="shared"),
    ],
    ids=["sourcing", "owner_type", "party", "capacity"],
)
def test_closed_sets_are_rejected(factory) -> None:
    with pytest.raises(ValueError):
        factory(uuid.uuid4())


@pytest.mark.parametrize(
    "factory",
    [
        lambda p: _task(p, estimate=1.5),
        lambda p: BidLine(bid_id=uuid.uuid4(), kind="labour", qty=2.0, rate="10", project_id=p),
        lambda p: Bid(version=1, currency="CAD", is_active="yes", project_id=p),
    ],
    ids=["float-estimate", "float-qty", "non-bool-flag"],
)
def test_type_errors(factory) -> None:
    with pytest.raises(TypeError):
        factory(uuid.uuid4())


@pytest.mark.parametrize(
    "factory",
    [
        lambda p: Booking(project_id=p, starts_at=_h(2), ends_at=_h(2),
                          resources=[{"resource_id": uuid.uuid4()}]),
        lambda p: Booking(project_id=p, starts_at="2026-11-02T09:00:00",
                          ends_at=_h(2), resources=[{"resource_id": uuid.uuid4()}]),
        lambda p: Booking(project_id=p, starts_at=_h(0), ends_at=_h(2), resources=[]),
        lambda p: Bid(version=1, currency="dollars", project_id=p),
        lambda p: Resource(name="x", resource_kind=RESOURCE_KIND_PERSON),
        lambda p: _room(person_id=uuid.uuid4()),
        lambda p: _room(availability=[{"kind": "downtime", "from": "2026-11-05",
                                       "until": "2026-11-04"}]),
        lambda p: Task(owner_id=uuid.uuid4(), owner_type="shot", task_type="comp",
                       sourcing=TASK_SOURCING_INTERNAL),
        lambda p: Vendor(name="Outsourcer", project_id=p),
        lambda p: ResourceDependency(resource_type="suite", requires_type="licence",
                                     quantity=0),
    ],
    ids=["empty-interval", "naive", "no-resources", "currency", "person-without-id",
         "room-with-person", "availability-order", "task-needs-project",
         "vendor-is-studio", "dependency-qty"],
)
def test_value_errors(factory) -> None:
    with pytest.raises(ValueError):
        factory(uuid.uuid4())


def test_open_sets_accept_unknown_members() -> None:
    project_id = uuid.uuid4()
    node = Resource(name="rn-01", resource_kind="render_node", capacity_kind=CAPACITY_KIND_COUNTED)
    assert node.resource_kind == "render_node"
    line = BidLine(bid_id=uuid.uuid4(), kind="fixed_fee", qty="1", rate="2500.00",
                   project_id=project_id)
    assert line.kind == "fixed_fee"
    assert _task(project_id, status="blocked_on_client").status == "blocked_on_client"


# --------------------------------------------------------------------------- #
# Live Postgres
# --------------------------------------------------------------------------- #
async def _project(session, code="SCH") -> uuid.UUID:
    proj = DBProject(name=f"proj-{code}", code=code)
    session.add(proj)
    await session.flush()
    return proj.id


@pytest.mark.asyncio
async def test_round_trip_every_kind_with_residual_metadata(session_factory) -> None:
    async with session_factory() as session:
        pid = await _project(session)
        repo = EntityRepo(session, None)
        sched = SchedulingRepo(session)

        person, facet = await sched.create_person(
            Person(name="Ada Artist", email="Ada@Studio.test", usernames=["ada"],
                   external_user_id="okta|1", metadata={"dept": "comp"})
        )
        vendor = Vendor(name="Outsource Co", contacts=[{"name": "Bo", "email": "bo@x.test"}],
                        metadata={"tier": "a"})
        licence = Resource(
            name="Nuke pool", resource_kind=RESOURCE_KIND_LICENCE,
            capacity_kind=CAPACITY_KIND_COUNTED, resource_type="nuke",
            availability=[
                {"kind": "pool_size", "from": "2026-11-01", "quantity": 5},
                {"kind": "downtime", "from": "2026-12-24T00:00:00+00:00",
                 "until": "2026-12-27T00:00:00+00:00"},
            ],
            metadata={"vendor": "foundry"},
        )
        dep = ResourceDependency(resource_type="suite", requires_type="nuke", quantity=2,
                                 metadata={"note": "per suite"})
        task = _task(pid, status="in_progress", estimate="12.50",
                     target_date=date(2026, 11, 20), due_date="2026-11-30",
                     metadata={"priority": "high"})
        resp = Responsibility(party_type=RESPONSIBILITY_PARTY_PERSON, party_id=person.id,
                              task_id=task.id, responsibility_type="artist",
                              effective_from="2026-11-01", project_id=pid,
                              metadata={"source": "pipeline"})
        bid = Bid(version=2, currency="cad", is_active=True, project_id=pid,
                  name="Bid v2", metadata={"author": "producer"})
        line = BidLine(bid_id=bid.id, kind=BID_LINE_KIND_LABOUR, qty=Decimal("40"),
                       rate="95.00", task_type="comp", section="Comp",
                       vendor_id=vendor.id, project_id=pid, metadata={"row": 3})
        for record in (vendor, licence, dep, task, resp, bid, line):
            await repo.save(record)
        booking = _booking(pid, [facet, {"resource_id": licence.id, "quantity": 2}],
                           task_id=task.id, bid_line_id=line.id, label="Comp day 1",
                           metadata={"color": "amber"})
        await repo.save(booking)
        await session.commit()

    originals = [person, facet, vendor, licence, dep, task, resp, bid, line, booking]
    async with session_factory() as session:
        repo = EntityRepo(session, None)
        for original in originals:
            loaded = await repo.get(original.id)
            assert type(loaded) is type(original)
            assert loaded.to_attributes() == original.to_attributes()
            assert loaded.metadata == original.metadata
            assert loaded.name == original.name
            assert loaded.project_id == original.project_id

        loaded_bid = await repo.get(bid.id)
        assert loaded_bid.currency == "CAD"
        loaded_line = await repo.get(line.id)
        assert (loaded_line.qty, loaded_line.rate) == ("40", "95.00")
        loaded_booking = await repo.get(booking.id)
        assert loaded_booking.label == "Comp day 1"
        assert loaded_booking.status == "planning"
        assert loaded_booking.starts_at == T0
        assert (await repo.get(task.id)).estimate == "12.50"


@pytest.mark.asyncio
async def test_task_state_is_stored_raw(session_factory) -> None:
    async with session_factory() as session:
        pid = await _project(session)
        repo = EntityRepo(session, None)
        on_hold = _task(pid, status="on_hold")
        done = _task(pid, status="complete")
        await repo.save(on_hold)
        await repo.save(done)
        await session.commit()

        rows = dict((await session.execute(
            select(DBEntity.id, DBEntity.status).where(DBEntity.entity_type == "task")
        )).all())
        assert rows[on_hold.id] == "on_hold"
        assert rows[done.id] == "complete"
        assert (await repo.get(done.id)).status == "complete"


@pytest.mark.asyncio
async def test_project_lifecycle_state(session_factory) -> None:
    async with session_factory() as session:
        repo = ProjectRepo(session)
        project = CoreProject(name="Lifecycle", code="LIFE")
        await repo.save(project)
        await session.commit()
        assert (await repo.get(project.id)).lifecycle_state == "active"

        await repo.save(CoreProject(name="Lifecycle", code="LIFE", id=project.id,
                                    lifecycle_state=PROJECT_STATE_ON_HOLD))
        await session.commit()
        assert (await repo.get(project.id)).lifecycle_state == "on_hold"

        # A writer that rebuilds the project from name/code alone must not
        # clobber the stored lifecycle (Pipeline's catalog binding).
        await repo.save(CoreProject(name="Lifecycle renamed", code="LIFE", id=project.id))
        await session.commit()
        loaded = await repo.get(project.id)
        assert loaded.lifecycle_state == "on_hold"
        assert loaded.name == "Lifecycle renamed"
        assert loaded.to_dict()["lifecycle_state"] == "on_hold"

        fresh = CoreProject(name="Bidding", code="BID", lifecycle_state="bidding")
        await repo.save(fresh)
        await session.commit()
        assert (await repo.get(fresh.id)).lifecycle_state == "bidding"


@pytest.mark.asyncio
async def test_bookings_in_range_overlap_edges(session_factory) -> None:
    async with session_factory() as session:
        pid = await _project(session)
        repo = EntityRepo(session, None)
        sched = SchedulingRepo(session)
        suite, other = _room("Suite 1"), _room("Suite 2")
        await repo.save(suite)
        await repo.save(other)

        before = _booking(pid, [suite], 0, 2)                         # ends at 2
        inside = _booking(pid, [suite], 3, 5, status=BOOKING_STATE_CONFIRMED)
        after = _booking(pid, [suite], 6, 8, status=BOOKING_STATE_PENCIL)  # starts at 6
        both = _booking(pid, [suite, other], 4, 7, status=BOOKING_STATE_CANCELLED)
        elsewhere = _booking(pid, [other], 2, 6)
        for b in (before, inside, after, both, elsewhere):
            await repo.save(b)
        await session.commit()

        got = await sched.bookings_in_range([suite.id], _h(2), _h(6))
        assert [b.id for b in got] == [inside.id, both.id]

        # Touching either boundary is not an overlap; one tick inside is.
        assert before.id in {b.id for b in await sched.bookings_in_range([suite.id], _h(1.99), _h(6))}
        assert after.id in {b.id for b in await sched.bookings_in_range([suite.id], _h(2), _h(6.01))}

        got = await sched.bookings_in_range([suite.id, other.id], _h(2), _h(6))
        assert {b.id for b in got} == {inside.id, both.id, elsewhere.id}

        got = await sched.bookings_in_range(
            [suite.id, other.id], _h(0), _h(10), states=[BOOKING_STATE_CONFIRMED],
        )
        assert [b.id for b in got] == [inside.id]
        assert await sched.bookings_in_range([], _h(0), _h(10)) == []


@pytest.mark.asyncio
async def test_bookings_for_project(session_factory) -> None:
    async with session_factory() as session:
        pid = await _project(session, "A")
        other_pid = await _project(session, "B")
        repo = EntityRepo(session, None)
        suite = _room()
        await repo.save(suite)
        late = _booking(pid, [suite], 5, 6, status=BOOKING_STATE_CONFIRMED)
        early = _booking(pid, [suite], 0, 1)
        foreign = _booking(other_pid, [suite], 2, 3)
        for b in (late, early, foreign):
            await repo.save(b)
        await session.commit()

        sched = SchedulingRepo(session)
        assert [b.id for b in await sched.bookings_for_project(pid)] == [early.id, late.id]
        assert [b.id for b in await sched.bookings_for_project(
            pid, states=[BOOKING_STATE_CONFIRMED])] == [late.id]


@pytest.mark.asyncio
async def test_booking_update_rewrites_index_and_index_agrees(session_factory) -> None:
    async with session_factory() as session:
        pid = await _project(session)
        repo = EntityRepo(session, None)
        a, b, c = _room("A"), _room("B"), _room("C")
        for r in (a, b, c):
            await repo.save(r)
        booking = _booking(pid, [a, b], 0, 4)
        await repo.save(booking)
        await session.commit()

        updated = Booking(
            id=booking.id, project_id=pid, starts_at=_h(10), ends_at=_h(12),
            status=BOOKING_STATE_CONFIRMED,
            resources=[{"resource_id": c.id, "quantity": 3}, {"resource_id": a.id}],
        )
        await repo.save(updated)
        await session.commit()

        rows = (await session.execute(
            select(DBBookingResource).where(DBBookingResource.booking_id == booking.id)
        )).scalars().all()
        assert {(r.resource_id, r.quantity) for r in rows} == {(c.id, 3), (a.id, 1)}
        for r in rows:
            assert (r.starts_at, r.ends_at, r.state, r.project_id) == (
                _h(10), _h(12), BOOKING_STATE_CONFIRMED, pid,
            )
        loaded = await repo.get(booking.id)
        assert {(uuid.UUID(e["resource_id"]), e["quantity"]) for e in loaded.resources} == {
            (r.resource_id, r.quantity) for r in rows
        }


@pytest.mark.asyncio
async def test_booking_must_reference_resource_rows(session_factory) -> None:
    async with session_factory() as session:
        pid = await _project(session)
        repo = EntityRepo(session, None)
        person = Person(name="No Facet", email="nf@studio.test")
        await repo.save(person)
        with pytest.raises(ValueError, match="unknown resources"):
            await repo.save(_booking(pid, [{"resource_id": person.id}]))


@pytest.mark.asyncio
async def test_delete_booking_cascades_and_booked_resource_is_restricted(session_factory) -> None:
    async with session_factory() as session:
        pid = await _project(session)
        repo = EntityRepo(session, None)
        suite = _room()
        await repo.save(suite)
        booking = _booking(pid, [suite])
        await repo.save(booking)
        await session.commit()

        with pytest.raises(IntegrityError):
            await repo.delete(suite.id)
            await session.flush()
        await session.rollback()

        await repo.delete(booking.id)
        await session.commit()
        remaining = (await session.execute(select(DBBookingResource))).scalars().all()
        assert remaining == []
        await repo.delete(suite.id)
        await session.commit()
        assert await repo.get(suite.id) is None


@pytest.mark.asyncio
async def test_person_facet_is_unique_and_immutable(session_factory) -> None:
    async with session_factory() as session:
        repo = EntityRepo(session, None)
        sched = SchedulingRepo(session)
        person, facet = await sched.create_person(Person(name="Pat", email="pat@studio.test"))
        await session.commit()
        assert facet.resource_kind == RESOURCE_KIND_PERSON
        assert (await sched.person_resource(person.id)).id == facet.id

        with pytest.raises(IntegrityError):
            await repo.save(Resource(name="Pat again", resource_kind=RESOURCE_KIND_PERSON,
                                     person_id=person.id))
        await session.rollback()

        other = Person(name="Quinn", email="quinn@studio.test")
        await repo.save(other)
        with pytest.raises(ValueError, match="immutable"):
            await repo.save(Resource(id=facet.id, name="Pat", resource_kind=RESOURCE_KIND_PERSON,
                                     person_id=other.id))
        await session.rollback()

        _, none = await sched.create_person(
            Person(name="Freelancer", email="free@studio.test"), bookable=False,
        )
        assert none is None
        await session.commit()


@pytest.mark.asyncio
async def test_duplicate_email_rejected_case_insensitively(session_factory) -> None:
    async with session_factory() as session:
        sched = SchedulingRepo(session)
        await sched.create_person(Person(name="Ada", email="ada@studio.test"))
        await session.commit()
        with pytest.raises(IntegrityError):
            await sched.create_person(Person(name="Ada 2", email="ADA@Studio.Test"))
        # The savepoint kept the outer transaction usable and left no facet.
        resources = (await session.execute(
            select(DBEntity).where(DBEntity.entity_type == "resource")
        )).scalars().all()
        assert len(resources) == 1


@pytest.mark.asyncio
async def test_usernames_are_unique_and_looked_up(session_factory) -> None:
    async with session_factory() as session:
        repo = EntityRepo(session, None)
        sched = SchedulingRepo(session)
        ada = Person(name="Ada", email="ada@studio.test", usernames=["ada", "alovelace"])
        await repo.save(ada)
        await session.commit()
        assert (await sched.person_by_username("alovelace")).id == ada.id
        assert await sched.person_by_username("nobody") is None

        with pytest.raises(IntegrityError):
            await repo.save(Person(name="Imposter", email="imp@studio.test", usernames=["ada"]))
        await session.rollback()

        # Rewriting the person rewrites its username rows.
        await repo.save(Person(id=ada.id, name="Ada", email="ada@studio.test", usernames=["ada2"]))
        await session.commit()
        names = (await session.execute(
            select(DBPersonUsername.username).where(DBPersonUsername.person_id == ada.id)
        )).scalars().all()
        assert names == ["ada2"]
        assert await sched.person_by_username("ada") is None


@pytest.mark.asyncio
async def test_tasks_for_party_via_responsibility(session_factory) -> None:
    async with session_factory() as session:
        pid = await _project(session)
        repo = EntityRepo(session, None)
        person = Person(name="Ada", email="ada@studio.test")
        vendor = Vendor(name="Outsource Co")
        comp, roto, paint = (_task(pid, task_type=t) for t in ("comp", "roto", "paint"))
        roto.sourcing = TASK_SOURCING_OUTSOURCE
        for record in (person, vendor, comp, roto, paint):
            await repo.save(record)

        def resp(party_type, party, task, start="2026-11-01", until=None):
            return Responsibility(party_type=party_type, party_id=party.id, task_id=task.id,
                                  responsibility_type="artist", effective_from=start,
                                  effective_until=until, project_id=pid)

        await repo.save(resp(RESPONSIBILITY_PARTY_PERSON, person, comp))
        await repo.save(resp(RESPONSIBILITY_PARTY_PERSON, person, paint, until="2026-11-10"))
        await repo.save(resp(RESPONSIBILITY_PARTY_VENDOR, vendor, roto))
        await session.commit()

        sched = SchedulingRepo(session)
        assert [t.id for t in await sched.tasks_for_party("person", person.id)] == [
            comp.id, paint.id,
        ]
        assert [t.id for t in await sched.tasks_for_party(
            "person", person.id, on=date(2026, 11, 15))] == [comp.id]
        assert [t.id for t in await sched.tasks_for_party("vendor", vendor.id)] == [roto.id]
        assert await sched.tasks_for_party("vendor", person.id) == []
        with pytest.raises(ValueError):
            await sched.tasks_for_party("contractor", person.id)


@pytest.mark.asyncio
async def test_bids_for_project_filters_and_allows_multiple_awarded(session_factory) -> None:
    async with session_factory() as session:
        pid = await _project(session, "A")
        other_pid = await _project(session, "B")
        repo = EntityRepo(session, None)
        v1 = Bid(version=1, currency="USD", is_awarded=True, project_id=pid)
        v2 = Bid(version=2, currency="USD", is_awarded=True, is_active=True, project_id=pid)
        v3 = Bid(version=3, currency="USD", is_active=True, project_id=pid)
        foreign = Bid(version=1, currency="USD", is_awarded=True, project_id=other_pid)
        for b in (v3, v1, v2, foreign):
            await repo.save(b)
        await session.commit()

        sched = SchedulingRepo(session)
        assert [b.version for b in await sched.bids_for_project(pid)] == [1, 2, 3]
        assert [b.id for b in await sched.bids_for_project(pid, awarded=True)] == [v1.id, v2.id]
        assert [b.id for b in await sched.bids_for_project(pid, active=True)] == [v2.id, v3.id]
        assert [b.id for b in await sched.bids_for_project(
            pid, active=True, awarded=True)] == [v2.id]
        assert [b.id for b in await sched.bids_for_project(pid, awarded=False)] == [v3.id]


@pytest.mark.asyncio
async def test_open_set_values_persist(session_factory) -> None:
    async with session_factory() as session:
        pid = await _project(session)
        repo = EntityRepo(session, None)
        node = Resource(name="rn-01", resource_kind="render_node",
                        capacity_kind=CAPACITY_KIND_COUNTED)
        bid = Bid(version=1, currency="EUR", project_id=pid)
        fee = BidLine(bid_id=bid.id, kind="fixed_fee", qty="1", rate="2500", project_id=pid)
        for record in (node, bid, fee):
            await repo.save(record)
        await session.commit()
        assert (await repo.get(node.id)).resource_kind == "render_node"
        assert (await repo.get(fee.id)).kind == "fixed_fee"


@pytest.mark.asyncio
async def test_scope_is_enforced_at_save(session_factory) -> None:
    async with session_factory() as session:
        pid = await _project(session)
        repo = EntityRepo(session, None)
        with pytest.raises(ValueError, match="studio-scoped"):
            await repo.save(Vendor(name="V"), project_id=pid)
        task = _task(pid)
        await repo.save(task)
        row = await session.get(DBEntity, task.id)
        assert row.project_id == pid
