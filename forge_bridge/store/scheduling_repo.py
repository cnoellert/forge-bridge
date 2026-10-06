"""Scheduling read queries + derived-index sync (#274).

The scheduling records themselves are ordinary ``entities`` rows written by
``EntityRepo.save`` (the single write path for WS and for Pipeline's in-process
adapter). Two derived side tables make the hot lookups plain btree queries:

    booking_resource — one row per (booking, resource): interval, state, qty
    person_username  — username → person

``sync_scheduling_index`` rewrites them (delete + insert, like
``LocationRepo.save_entity_locations``) and is called ONLY from
``EntityRepo.save``. Nothing else writes those tables, so they always agree
with the entity row's JSONB attributes.

``SchedulingRepo`` holds the read queries Pipeline needs plus the person
helper that creates a person and its bookable resource facet together. It
decides nothing: conflict detection, dependency filling and lifecycle rules
are Pipeline's.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Iterable, Optional

from forge_contracts.scheduling import (
    CAPACITY_KIND_EXCLUSIVE,
    KNOWN_RESPONSIBILITY_PARTIES,
    RESOURCE_KIND_PERSON,
    SCHEDULING_KIND_BID,
    SCHEDULING_KIND_BOOKING,
    SCHEDULING_KIND_RESOURCE,
    SCHEDULING_KIND_RESPONSIBILITY,
    SCHEDULING_KIND_TASK,
)
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from forge_bridge.core.entities import BridgeEntity
from forge_bridge.core.registry import Registry
from forge_bridge.core.scheduling import (
    Bid,
    Booking,
    Person,
    Resource,
    Task,
    _aware,
    _closed,
)
from forge_bridge.store.models import DBBookingResource, DBEntity, DBPersonUsername


# ─────────────────────────────────────────────────────────────
# Derived-index sync (called only by EntityRepo.save)
# ─────────────────────────────────────────────────────────────

async def sync_scheduling_index(session: AsyncSession, entity: BridgeEntity) -> None:
    """Rewrite the derived index rows for one saved scheduling record.

    No-op for kinds without a side table. Flushes first so the entity row
    exists before its index rows reference it (and so a unique-index
    violation surfaces at the save that caused it).
    """
    if isinstance(entity, Booking):
        await session.flush()
        await _sync_booking(session, entity)
    elif isinstance(entity, Person):
        await session.flush()
        await _sync_person(session, entity)
    elif isinstance(entity, Resource):
        # Surface the one-facet-per-person unique index at save time.
        await session.flush()


async def _sync_booking(session: AsyncSession, booking: Booking) -> None:
    resource_ids = booking.resource_ids
    found = set(
        (await session.execute(
            select(DBEntity.id)
            .where(DBEntity.id.in_(resource_ids))
            .where(DBEntity.entity_type == SCHEDULING_KIND_RESOURCE)
        )).scalars().all()
    )
    missing = [str(rid) for rid in resource_ids if rid not in found]
    if missing:
        raise ValueError(f"booking references unknown resources: {missing}")

    await session.execute(
        delete(DBBookingResource).where(DBBookingResource.booking_id == booking.id)
    )
    for entry in booking.resources:
        session.add(DBBookingResource(
            booking_id=booking.id,
            resource_id=uuid.UUID(entry["resource_id"]),
            project_id=booking.project_id,
            starts_at=booking.starts_at,
            ends_at=booking.ends_at,
            state=booking.status,
            quantity=entry["quantity"],
        ))
    await session.flush()


async def _sync_person(session: AsyncSession, person: Person) -> None:
    await session.execute(
        delete(DBPersonUsername).where(DBPersonUsername.person_id == person.id)
    )
    for username in person.usernames:
        session.add(DBPersonUsername(username=username, person_id=person.id))
    await session.flush()


# ─────────────────────────────────────────────────────────────
# Read queries + person helper
# ─────────────────────────────────────────────────────────────

class SchedulingRepo:
    """Scheduling queries over entities + the derived side tables.

    Operates within the caller's transaction (repo convention).
    """

    def __init__(self, session: AsyncSession, registry: Optional[Registry] = None):
        from forge_bridge.store.repo import EntityRepo

        self.session = session
        self.entities = EntityRepo(session, registry)

    async def sync_index(self, entity: BridgeEntity) -> None:
        """Rewrite the derived index rows for ``entity`` (EntityRepo.save does
        this on every save; exposed for repair tooling)."""
        await sync_scheduling_index(self.session, entity)

    async def create_person(
        self,
        person: Person,
        *,
        bookable: bool = True,
        resource_name: Optional[str] = None,
        resource_type: Optional[str] = None,
    ) -> tuple[Person, Optional[Resource]]:
        """Save a person and (by default) its one bookable resource facet.

        Both rows are written inside a SAVEPOINT: if either fails (duplicate
        email, duplicate username, ...) neither is kept and the caller's
        transaction stays usable.
        """
        resource: Optional[Resource] = None
        if bookable:
            resource = Resource(
                name=resource_name or person.name,
                resource_kind=RESOURCE_KIND_PERSON,
                capacity_kind=CAPACITY_KIND_EXCLUSIVE,
                resource_type=resource_type,
                person_id=person.id,
            )
        async with self.session.begin_nested():
            await self.entities.save(person)
            if resource is not None:
                await self.entities.save(resource)
        return person, resource

    async def person_resource(self, person_id: uuid.UUID) -> Optional[Resource]:
        """The bookable facet of ``person_id``, if it has one."""
        rows = await self._entities(
            select(DBEntity)
            .where(DBEntity.entity_type == SCHEDULING_KIND_RESOURCE)
            .where(DBEntity.attributes["person_id"].astext == str(person_id))
        )
        return rows[0] if rows else None

    async def person_by_username(self, username: str) -> Optional[Person]:
        rows = await self._entities(
            select(DBEntity)
            .join(DBPersonUsername, DBPersonUsername.person_id == DBEntity.id)
            .where(DBPersonUsername.username == username)
        )
        return rows[0] if rows else None

    async def bookings_in_range(
        self,
        resource_ids: Iterable[uuid.UUID | str],
        from_: datetime | str,
        to: datetime | str,
        states: Optional[Iterable[str]] = None,
    ) -> list[Booking]:
        """Bookings on any of ``resource_ids`` overlapping ``[from_, to)``.

        Overlap is half-open: ``starts_at < to AND ends_at > from_`` — a
        booking that ends exactly at ``from_`` (or starts exactly at ``to``)
        does not overlap. ``states`` filters on the booking state (raw).
        """
        ids = [uuid.UUID(str(rid)) for rid in resource_ids]
        start = _aware(from_, "from_")
        end = _aware(to, "to")
        if not ids:
            return []
        stmt = (
            select(DBBookingResource.booking_id)
            .where(DBBookingResource.resource_id.in_(ids))
            .where(DBBookingResource.starts_at < end)
            .where(DBBookingResource.ends_at > start)
        )
        if states is not None:
            stmt = stmt.where(DBBookingResource.state.in_(list(states)))
        booking_ids = set((await self.session.execute(stmt)).scalars().all())
        if not booking_ids:
            return []
        bookings = await self._entities(
            select(DBEntity).where(DBEntity.id.in_(booking_ids))
        )
        return sorted(bookings, key=lambda b: (b.starts_at, str(b.id)))

    async def bookings_for_project(
        self,
        project_id: uuid.UUID,
        states: Optional[Iterable[str]] = None,
    ) -> list[Booking]:
        stmt = (
            select(DBEntity)
            .where(DBEntity.entity_type == SCHEDULING_KIND_BOOKING)
            .where(DBEntity.project_id == project_id)
        )
        if states is not None:
            stmt = stmt.where(DBEntity.status.in_(list(states)))
        bookings = await self._entities(stmt)
        return sorted(bookings, key=lambda b: (b.starts_at, str(b.id)))

    async def tasks_for_party(
        self,
        party_type: str,
        party_id: uuid.UUID | str,
        *,
        on: Optional[date] = None,
    ) -> list[Task]:
        """Tasks a person or vendor is responsible for (via responsibility).

        ``on`` keeps only responsibilities effective on that date.
        """
        party_type = _closed(party_type, "party_type", KNOWN_RESPONSIBILITY_PARTIES)
        responsibilities = await self._entities(
            select(DBEntity)
            .where(DBEntity.entity_type == SCHEDULING_KIND_RESPONSIBILITY)
            .where(DBEntity.attributes.contains({
                "party_type": party_type,
                "party_id": str(uuid.UUID(str(party_id))),
            }))
        )
        if on is not None:
            responsibilities = [
                r for r in responsibilities
                if r.effective_from <= on
                and (r.effective_until is None or on <= r.effective_until)
            ]
        task_ids = {r.task_id for r in responsibilities}
        if not task_ids:
            return []
        tasks = await self._entities(
            select(DBEntity)
            .where(DBEntity.entity_type == SCHEDULING_KIND_TASK)
            .where(DBEntity.id.in_(task_ids))
        )
        return sorted(tasks, key=lambda t: (t.task_type, str(t.id)))

    async def bids_for_project(
        self,
        project_id: uuid.UUID,
        active: Optional[bool] = None,
        awarded: Optional[bool] = None,
    ) -> list[Bid]:
        stmt = (
            select(DBEntity)
            .where(DBEntity.entity_type == SCHEDULING_KIND_BID)
            .where(DBEntity.project_id == project_id)
        )
        flags = {}
        if active is not None:
            flags["is_active"] = active
        if awarded is not None:
            flags["is_awarded"] = awarded
        if flags:
            stmt = stmt.where(DBEntity.attributes.contains(flags))
        bids = await self._entities(stmt)
        return sorted(bids, key=lambda b: (b.version, str(b.id)))

    async def _entities(self, stmt) -> list:
        rows = (await self.session.execute(stmt)).scalars().all()
        return [self.entities._to_core(row) for row in rows]


__all__ = ["SchedulingRepo", "sync_scheduling_index"]
