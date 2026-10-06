"""Scheduling records — the nine record kinds of forge-contracts v0.9 (#274).

Bridge owns the RECORDS (fields, ids, constraints); forge-pipeline owns the
BEHAVIOUR (conflict detection, dependency filling, bid-vs-booked variance,
project lifecycle transitions). Nothing in this module decides a schedule.

    task                — a task instance owned by a Shot or Asset
    responsibility      — person | vendor → task, typed, with effective dates
    person              — the scheduling identity (studio-scoped)
    vendor              — an outsourcing company with contacts (studio-scoped)
    resource            — a bookable thing (studio-scoped); a person's bookable
                          facet is one linked ``resource_kind='person'`` row
    resource_dependency — "resource type X requires N of type Y" (studio-scoped)
    booking             — resources × interval × project × state
    bid                 — project-scoped, versioned; active/awarded are flags
    bid_line            — a line keyed by classifier, never by task or shot id

Every record is one row in the shared ``entities`` table; typed fields live in
the JSONB ``attributes`` column. ``EntityRepo`` dispatches through
``SCHEDULING_CLASSES`` (one branch for all nine kinds) and calls each class's
``to_attributes()`` / ``from_record()``.

Validation follows the contracts extension rule: CLOSED sets (task sourcing,
responsibility party, capacity kind) and the ADR-008 deliverable axis are
validated by membership; every OPEN set (task state, resource kind, booking
state, bid-line kind, ...) is validated by class only — any non-empty string
passes. Constructors raise ``TypeError`` / ``ValueError`` on invalid input.

Task and booking states are stored RAW in ``entities.status``: they are not the
entity ``Status`` enum, so ``complete`` stays ``complete`` (``Status`` would
alias it to ``delivered``).

Not part of ``forge_bridge.__all__`` or ``forge_bridge.core.__all__``.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, ClassVar, Optional

from forge_contracts import KNOWN_DELIVERABLE_TYPES
from forge_contracts.scheduling import (
    BOOKING_STATE_PLANNING,
    CAPACITY_KIND_EXCLUSIVE,
    KNOWN_CAPACITY_KINDS,
    KNOWN_RESPONSIBILITY_PARTIES,
    KNOWN_TASK_SOURCINGS,
    RESOURCE_KIND_PERSON,
    SCHEDULING_KIND_BID,
    SCHEDULING_KIND_BID_LINE,
    SCHEDULING_KIND_BOOKING,
    SCHEDULING_KIND_PERSON,
    SCHEDULING_KIND_RESOURCE,
    SCHEDULING_KIND_RESOURCE_DEPENDENCY,
    SCHEDULING_KIND_RESPONSIBILITY,
    SCHEDULING_KIND_TASK,
    SCHEDULING_KIND_VENDOR,
)

from forge_bridge.core.entities import BridgeEntity

# Task state is an OPEN set (``KNOWN_TASK_STATES``); a new task starts here.
TASK_STATE_DEFAULT = "pending"


# ─────────────────────────────────────────────────────────────
# Field validators
# ─────────────────────────────────────────────────────────────

def _text(value: Any, field: str) -> str:
    """A required non-empty string (the open-set class check)."""
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string, got {type(value).__name__}")
    value = value.strip()
    if not value:
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _opt_text(value: Any, field: str) -> Optional[str]:
    return None if value is None else _text(value, field)


def _state(value: Any, field: str) -> str:
    """An open-set state: non-empty, stored raw (lowercased, never aliased)."""
    return _text(value, field).lower()


def _closed(value: Any, field: str, members: frozenset[str]) -> str:
    value = _text(value, field)
    if value not in members:
        raise ValueError(
            f"{field} must be one of {sorted(members)}, got {value!r}"
        )
    return value


def _uuid(value: Any, field: str) -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a UUID, got {type(value).__name__}")
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be a UUID, got {value!r}") from exc


def _opt_uuid(value: Any, field: str) -> Optional[uuid.UUID]:
    return None if value is None else _uuid(value, field)


def _int(value: Any, field: str, *, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field} must be an integer, got {type(value).__name__}")
    if value < minimum:
        raise ValueError(f"{field} must be >= {minimum}, got {value}")
    return value


def _bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{field} must be a bool, got {type(value).__name__}")
    return value


def _decimal(value: Any, field: str) -> str:
    """Money / quantity: a Decimal string. Floats are refused outright."""
    if isinstance(value, (bool, float)):
        raise TypeError(f"{field} must be a Decimal string, never {type(value).__name__}")
    if not isinstance(value, (Decimal, int, str)):
        raise TypeError(f"{field} must be a Decimal string, got {type(value).__name__}")
    try:
        parsed = Decimal(value.strip() if isinstance(value, str) else value)
    except InvalidOperation as exc:
        raise ValueError(f"{field} must be a decimal number, got {value!r}") from exc
    if not parsed.is_finite():
        raise ValueError(f"{field} must be finite, got {value!r}")
    return str(parsed)


def _opt_decimal(value: Any, field: str) -> Optional[str]:
    return None if value is None else _decimal(value, field)


def _date(value: Any, field: str) -> date:
    if isinstance(value, datetime):
        raise TypeError(f"{field} must be a date, not a datetime")
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise TypeError(f"{field} must be an ISO date, got {type(value).__name__}")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO date, got {value!r}") from exc


def _opt_date(value: Any, field: str) -> Optional[date]:
    return None if value is None else _date(value, field)


def _datetime(value: Any, field: str) -> datetime:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"{field} must be an ISO datetime, got {value!r}") from exc
    if not isinstance(value, datetime):
        raise TypeError(f"{field} must be a datetime, got {type(value).__name__}")
    return value


def _aware(value: Any, field: str) -> datetime:
    value = _datetime(value, field)
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return value


def _instant(value: Any, field: str) -> datetime | date:
    """An availability bound: an ISO date or datetime."""
    if isinstance(value, (date, datetime)):
        return value
    if not isinstance(value, str):
        raise TypeError(f"{field} must be an ISO date or datetime")
    try:
        return date.fromisoformat(value)
    except ValueError:
        return _datetime(value, field)


def _as_datetime(value: datetime | date) -> datetime:
    return value if isinstance(value, datetime) else datetime(value.year, value.month, value.day)


def _str_list(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        raise TypeError(f"{field} must be a list of strings")
    items = [_text(item, f"{field}[]") for item in value]
    if len(set(items)) != len(items):
        raise ValueError(f"{field} must not contain duplicates")
    return items


def _iso(value: Optional[date | datetime]) -> Optional[str]:
    return value.isoformat() if value is not None else None


def _sid(value: Optional[uuid.UUID]) -> Optional[str]:
    return str(value) if value is not None else None


# ─────────────────────────────────────────────────────────────
# Base
# ─────────────────────────────────────────────────────────────

class SchedulingRecord(BridgeEntity):
    """Shared shape for the nine scheduling kinds.

    Subclasses declare:
        ENTITY_TYPE     — the contracts record-kind name (the entities discriminator)
        TYPED_KEYS      — the JSONB keys ``to_attributes`` owns; every other key
                          in the column is open ``metadata`` (residual restore)
        PROJECT_SCOPED  — True: the row requires ``project_id``; False: the row
                          is studio-scoped and ``project_id`` must stay NULL
    and implement ``to_attributes()`` + ``_kwargs_from_record()``.
    """

    ENTITY_TYPE: ClassVar[str]
    TYPED_KEYS: ClassVar[frozenset[str]]
    PROJECT_SCOPED: ClassVar[bool]

    def __init__(
        self,
        *,
        name: Optional[str] = None,
        project_id: Optional[uuid.UUID | str] = None,
        id: Optional[uuid.UUID | str] = None,
        created_at: Optional[datetime] = None,
        metadata: Optional[dict[str, Any]] = None,
    ):
        super().__init__(id=id, created_at=created_at, metadata=metadata)
        self.name: Optional[str] = _opt_text(name, "name")
        self.project_id: Optional[uuid.UUID] = _opt_uuid(project_id, "project_id")
        if self.PROJECT_SCOPED and self.project_id is None:
            raise ValueError(f"{self.ENTITY_TYPE} is project-scoped: project_id is required")
        if not self.PROJECT_SCOPED and self.project_id is not None:
            raise ValueError(f"{self.ENTITY_TYPE} is studio-scoped: project_id must be None")

    @property
    def entity_type(self) -> str:
        return self.ENTITY_TYPE

    def to_attributes(self) -> dict[str, Any]:
        """The typed JSONB fields (keys == ``TYPED_KEYS``)."""
        raise NotImplementedError

    @classmethod
    def _kwargs_from_record(cls, attributes: dict, status: Optional[str]) -> dict[str, Any]:
        raise NotImplementedError

    @classmethod
    def from_record(
        cls,
        *,
        id: uuid.UUID,
        name: Optional[str],
        status: Optional[str],
        project_id: Optional[uuid.UUID],
        attributes: dict,
        created_at: Optional[datetime] = None,
    ) -> "SchedulingRecord":
        """Rebuild from a stored row; non-typed keys come back as metadata."""
        metadata = {k: v for k, v in attributes.items() if k not in cls.TYPED_KEYS}
        return cls(
            name=name,
            project_id=project_id,
            id=id,
            created_at=created_at,
            metadata=metadata,
            **cls._kwargs_from_record(attributes, status),
        )

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["name"] = self.name
        d["project_id"] = _sid(self.project_id)
        if hasattr(self, "status"):
            d["status"] = self.status
        d.update(self.to_attributes())
        return d

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, id={self.id!s:.8}...)"


# ─────────────────────────────────────────────────────────────
# Work plan
# ─────────────────────────────────────────────────────────────

class Task(SchedulingRecord):
    """A task instance owned by a Shot or Asset (ADR-007 polymorphic owner)."""

    ENTITY_TYPE = SCHEDULING_KIND_TASK
    TYPED_KEYS = frozenset({
        "owner_id", "owner_type", "task_type", "sourcing",
        "estimate", "target_date", "due_date",
    })
    PROJECT_SCOPED = True

    def __init__(
        self,
        *,
        owner_id: uuid.UUID | str,
        owner_type: str,
        task_type: str,
        sourcing: str,
        status: str = TASK_STATE_DEFAULT,
        estimate: Optional[Decimal | int | str] = None,
        target_date: Optional[date | str] = None,
        due_date: Optional[date | str] = None,
        **base: Any,
    ):
        super().__init__(**base)
        self.owner_id = _uuid(owner_id, "owner_id")
        self.owner_type = _closed(owner_type, "owner_type", KNOWN_DELIVERABLE_TYPES)
        self.task_type = _text(task_type, "task_type")
        self.sourcing = _closed(sourcing, "sourcing", KNOWN_TASK_SOURCINGS)
        self.status = _state(status, "status")
        self.estimate = _opt_decimal(estimate, "estimate")
        self.target_date = _opt_date(target_date, "target_date")
        self.due_date = _opt_date(due_date, "due_date")

    def to_attributes(self) -> dict[str, Any]:
        return {
            "owner_id": str(self.owner_id),
            "owner_type": self.owner_type,
            "task_type": self.task_type,
            "sourcing": self.sourcing,
            "estimate": self.estimate,
            "target_date": _iso(self.target_date),
            "due_date": _iso(self.due_date),
        }

    @classmethod
    def _kwargs_from_record(cls, a: dict, status: Optional[str]) -> dict[str, Any]:
        return {
            "owner_id": a.get("owner_id"),
            "owner_type": a.get("owner_type"),
            "task_type": a.get("task_type"),
            "sourcing": a.get("sourcing"),
            "status": status or TASK_STATE_DEFAULT,
            "estimate": a.get("estimate"),
            "target_date": a.get("target_date"),
            "due_date": a.get("due_date"),
        }


class Responsibility(SchedulingRecord):
    """A party (person | vendor) responsible for a task, with effective dates."""

    ENTITY_TYPE = SCHEDULING_KIND_RESPONSIBILITY
    TYPED_KEYS = frozenset({
        "party_type", "party_id", "task_id", "responsibility_type",
        "effective_from", "effective_until",
    })
    PROJECT_SCOPED = True

    def __init__(
        self,
        *,
        party_type: str,
        party_id: uuid.UUID | str,
        task_id: uuid.UUID | str,
        responsibility_type: str,
        effective_from: date | str,
        effective_until: Optional[date | str] = None,
        **base: Any,
    ):
        super().__init__(**base)
        self.party_type = _closed(party_type, "party_type", KNOWN_RESPONSIBILITY_PARTIES)
        self.party_id = _uuid(party_id, "party_id")
        self.task_id = _uuid(task_id, "task_id")
        self.responsibility_type = _text(responsibility_type, "responsibility_type")
        self.effective_from = _date(effective_from, "effective_from")
        self.effective_until = _opt_date(effective_until, "effective_until")
        if self.effective_until is not None and self.effective_until < self.effective_from:
            raise ValueError("effective_until must not precede effective_from")

    def to_attributes(self) -> dict[str, Any]:
        return {
            "party_type": self.party_type,
            "party_id": str(self.party_id),
            "task_id": str(self.task_id),
            "responsibility_type": self.responsibility_type,
            "effective_from": self.effective_from.isoformat(),
            "effective_until": _iso(self.effective_until),
        }

    @classmethod
    def _kwargs_from_record(cls, a: dict, status: Optional[str]) -> dict[str, Any]:
        return {key: a.get(key) for key in cls.TYPED_KEYS}


# ─────────────────────────────────────────────────────────────
# People and companies (studio-scoped)
# ─────────────────────────────────────────────────────────────

class Person(SchedulingRecord):
    """The scheduling identity. Pipeline's login account links here by id.

    ``email`` is unique case-insensitively; each of ``usernames`` maps to
    exactly one person (``person_username``). A person is bookable through ONE
    linked ``Resource(resource_kind='person', person_id=...)`` row.
    """

    ENTITY_TYPE = SCHEDULING_KIND_PERSON
    TYPED_KEYS = frozenset({"email", "usernames", "external_user_id"})
    PROJECT_SCOPED = False

    def __init__(
        self,
        *,
        name: str,
        email: str,
        usernames: Optional[list[str]] = None,
        external_user_id: Optional[str] = None,
        **base: Any,
    ):
        super().__init__(name=_text(name, "name"), **base)
        self.email = _text(email, "email")
        if "@" not in self.email:
            raise ValueError(f"email must contain '@', got {self.email!r}")
        self.usernames = _str_list(usernames, "usernames")
        self.external_user_id = _opt_text(external_user_id, "external_user_id")

    def to_attributes(self) -> dict[str, Any]:
        return {
            "email": self.email,
            "usernames": list(self.usernames),
            "external_user_id": self.external_user_id,
        }

    @classmethod
    def _kwargs_from_record(cls, a: dict, status: Optional[str]) -> dict[str, Any]:
        return {key: a.get(key) for key in cls.TYPED_KEYS}


class Vendor(SchedulingRecord):
    """An outsourcing company. Contracted via responsibility, never booked."""

    ENTITY_TYPE = SCHEDULING_KIND_VENDOR
    TYPED_KEYS = frozenset({"contacts"})
    PROJECT_SCOPED = False

    def __init__(
        self,
        *,
        name: str,
        contacts: Optional[list[dict[str, Any]]] = None,
        **base: Any,
    ):
        super().__init__(name=_text(name, "name"), **base)
        contacts = [] if contacts is None else contacts
        if not isinstance(contacts, (list, tuple)):
            raise TypeError("contacts must be a list of objects")
        for contact in contacts:
            if not isinstance(contact, dict):
                raise TypeError("each contact must be an object")
        self.contacts = [dict(c) for c in contacts]

    def to_attributes(self) -> dict[str, Any]:
        return {"contacts": [dict(c) for c in self.contacts]}

    @classmethod
    def _kwargs_from_record(cls, a: dict, status: Optional[str]) -> dict[str, Any]:
        return {"contacts": a.get("contacts")}


# ─────────────────────────────────────────────────────────────
# Resources (studio-scoped)
# ─────────────────────────────────────────────────────────────

def _availability(value: Any) -> list[dict[str, Any]]:
    """Validate ``[{kind, from, until?, quantity?}]`` (dated pool size / downtime)."""
    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        raise TypeError("availability must be a list of objects")
    out: list[dict[str, Any]] = []
    for i, entry in enumerate(value):
        field = f"availability[{i}]"
        if not isinstance(entry, dict):
            raise TypeError(f"{field} must be an object")
        unknown = set(entry) - {"kind", "from", "until", "quantity"}
        if unknown:
            raise ValueError(f"{field} has unknown keys {sorted(unknown)}")
        kind = _text(entry.get("kind"), f"{field}.kind")
        start = _instant(entry.get("from"), f"{field}.from")
        until = entry.get("until")
        until = None if until is None else _instant(until, f"{field}.until")
        if until is not None:
            try:
                ordered = _as_datetime(until) > _as_datetime(start)
            except TypeError as exc:  # naive vs aware
                raise ValueError(f"{field} mixes naive and timezone-aware bounds") from exc
            if not ordered:
                raise ValueError(f"{field}.until must be after from")
        item: dict[str, Any] = {"kind": kind, "from": start.isoformat(), "until": _iso(until)}
        if entry.get("quantity") is not None:
            item["quantity"] = _int(entry["quantity"], f"{field}.quantity", minimum=0)
        out.append(item)
    return out


class Resource(SchedulingRecord):
    """A bookable thing: room, workstation, licence pool, a person's facet, ...

    ``person_id`` is required iff ``resource_kind == 'person'`` and is immutable
    once stored (enforced by ``EntityRepo.save``); at most one resource row per
    person (partial unique index).
    """

    ENTITY_TYPE = SCHEDULING_KIND_RESOURCE
    TYPED_KEYS = frozenset({
        "resource_kind", "capacity_kind", "resource_type", "person_id", "availability",
    })
    PROJECT_SCOPED = False

    def __init__(
        self,
        *,
        name: str,
        resource_kind: str,
        capacity_kind: str = CAPACITY_KIND_EXCLUSIVE,
        resource_type: Optional[str] = None,
        person_id: Optional[uuid.UUID | str] = None,
        availability: Optional[list[dict[str, Any]]] = None,
        **base: Any,
    ):
        super().__init__(name=_text(name, "name"), **base)
        self.resource_kind = _text(resource_kind, "resource_kind")
        self.capacity_kind = _closed(capacity_kind, "capacity_kind", KNOWN_CAPACITY_KINDS)
        self.resource_type = _opt_text(resource_type, "resource_type")
        self.person_id = _opt_uuid(person_id, "person_id")
        if self.resource_kind == RESOURCE_KIND_PERSON and self.person_id is None:
            raise ValueError("a person resource requires person_id")
        if self.resource_kind != RESOURCE_KIND_PERSON and self.person_id is not None:
            raise ValueError("person_id is only valid on a person resource")
        self.availability = _availability(availability)

    def to_attributes(self) -> dict[str, Any]:
        return {
            "resource_kind": self.resource_kind,
            "capacity_kind": self.capacity_kind,
            "resource_type": self.resource_type,
            "person_id": _sid(self.person_id),
            "availability": [dict(a) for a in self.availability],
        }

    @classmethod
    def _kwargs_from_record(cls, a: dict, status: Optional[str]) -> dict[str, Any]:
        return {key: a.get(key) for key in cls.TYPED_KEYS}


class ResourceDependency(SchedulingRecord):
    """"Resource type X requires N of type Y" — declared by type, filled at booking."""

    ENTITY_TYPE = SCHEDULING_KIND_RESOURCE_DEPENDENCY
    TYPED_KEYS = frozenset({"resource_type", "requires_type", "quantity"})
    PROJECT_SCOPED = False

    def __init__(
        self,
        *,
        resource_type: str,
        requires_type: str,
        quantity: int = 1,
        **base: Any,
    ):
        super().__init__(**base)
        self.resource_type = _text(resource_type, "resource_type")
        self.requires_type = _text(requires_type, "requires_type")
        self.quantity = _int(quantity, "quantity", minimum=1)

    def to_attributes(self) -> dict[str, Any]:
        return {
            "resource_type": self.resource_type,
            "requires_type": self.requires_type,
            "quantity": self.quantity,
        }

    @classmethod
    def _kwargs_from_record(cls, a: dict, status: Optional[str]) -> dict[str, Any]:
        return {
            "resource_type": a.get("resource_type"),
            "requires_type": a.get("requires_type"),
            "quantity": a.get("quantity", 1),
        }


# ─────────────────────────────────────────────────────────────
# Booking (project-scoped)
# ─────────────────────────────────────────────────────────────

def _booking_resources(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, (list, tuple)) or not value:
        raise ValueError("resources must be a non-empty list of {resource_id, quantity}")
    out: list[dict[str, Any]] = []
    seen: set[uuid.UUID] = set()
    for i, entry in enumerate(value):
        field = f"resources[{i}]"
        if not isinstance(entry, dict):
            raise TypeError(f"{field} must be an object")
        unknown = set(entry) - {"resource_id", "quantity"}
        if unknown:
            raise ValueError(f"{field} has unknown keys {sorted(unknown)}")
        rid = _uuid(entry.get("resource_id"), f"{field}.resource_id")
        if rid in seen:
            raise ValueError(f"{field}.resource_id {rid} is listed twice")
        seen.add(rid)
        qty = entry.get("quantity", 1)
        out.append({"resource_id": str(rid), "quantity": _int(qty, f"{field}.quantity", minimum=1)})
    return out


class Booking(SchedulingRecord):
    """Resources × interval × project × state. Conflicts are Pipeline's call.

    ``label`` is stored in the ``entities.name`` column.
    """

    ENTITY_TYPE = SCHEDULING_KIND_BOOKING
    TYPED_KEYS = frozenset({"starts_at", "ends_at", "resources", "task_id", "bid_line_id"})
    PROJECT_SCOPED = True

    def __init__(
        self,
        *,
        starts_at: datetime | str,
        ends_at: datetime | str,
        resources: list[dict[str, Any]],
        status: str = BOOKING_STATE_PLANNING,
        task_id: Optional[uuid.UUID | str] = None,
        bid_line_id: Optional[uuid.UUID | str] = None,
        label: Optional[str] = None,
        **base: Any,
    ):
        if "name" in base:
            # ``label`` wins when both are given (an update renaming via label).
            name = base.pop("name")
            label = name if label is None else label
        super().__init__(name=label, **base)
        self.starts_at = _aware(starts_at, "starts_at")
        self.ends_at = _aware(ends_at, "ends_at")
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        self.status = _state(status, "status")
        self.resources = _booking_resources(resources)
        self.task_id = _opt_uuid(task_id, "task_id")
        self.bid_line_id = _opt_uuid(bid_line_id, "bid_line_id")

    @property
    def label(self) -> Optional[str]:
        return self.name

    @property
    def resource_ids(self) -> list[uuid.UUID]:
        return [uuid.UUID(r["resource_id"]) for r in self.resources]

    def to_attributes(self) -> dict[str, Any]:
        return {
            "starts_at": self.starts_at.isoformat(),
            "ends_at": self.ends_at.isoformat(),
            "resources": [dict(r) for r in self.resources],
            "task_id": _sid(self.task_id),
            "bid_line_id": _sid(self.bid_line_id),
        }

    @classmethod
    def _kwargs_from_record(cls, a: dict, status: Optional[str]) -> dict[str, Any]:
        return {
            "starts_at": a.get("starts_at"),
            "ends_at": a.get("ends_at"),
            "resources": a.get("resources"),
            "status": status or BOOKING_STATE_PLANNING,
            "task_id": a.get("task_id"),
            "bid_line_id": a.get("bid_line_id"),
        }


# ─────────────────────────────────────────────────────────────
# Bidding (project-scoped)
# ─────────────────────────────────────────────────────────────

class Bid(SchedulingRecord):
    """A project-scoped, versioned bid. ``is_active`` / ``is_awarded`` are plain
    flags: Bridge enforces no uniqueness (a project may hold several awarded
    bids); the award rules are Pipeline's."""

    ENTITY_TYPE = SCHEDULING_KIND_BID
    TYPED_KEYS = frozenset({"version", "is_active", "is_awarded", "currency"})
    PROJECT_SCOPED = True

    def __init__(
        self,
        *,
        version: int,
        currency: str,
        is_active: bool = False,
        is_awarded: bool = False,
        **base: Any,
    ):
        super().__init__(**base)
        self.version = _int(version, "version", minimum=1)
        currency = _text(currency, "currency")
        if len(currency) != 3 or not currency.isascii() or not currency.isalpha():
            raise ValueError(f"currency must be a 3-letter code, got {currency!r}")
        self.currency = currency.upper()
        self.is_active = _bool(is_active, "is_active")
        self.is_awarded = _bool(is_awarded, "is_awarded")

    def to_attributes(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "is_active": self.is_active,
            "is_awarded": self.is_awarded,
            "currency": self.currency,
        }

    @classmethod
    def _kwargs_from_record(cls, a: dict, status: Optional[str]) -> dict[str, Any]:
        return {
            "version": a.get("version"),
            "currency": a.get("currency"),
            "is_active": a.get("is_active", False),
            "is_awarded": a.get("is_awarded", False),
        }


class BidLine(SchedulingRecord):
    """A bid line keyed by classifier (task type and/or resource type), never by
    task or shot id. ``qty`` and ``rate`` are Decimal strings, never floats."""

    ENTITY_TYPE = SCHEDULING_KIND_BID_LINE
    TYPED_KEYS = frozenset({
        "bid_id", "kind", "task_type", "resource_type", "qty", "rate",
        "vendor_id", "section",
    })
    PROJECT_SCOPED = True

    def __init__(
        self,
        *,
        bid_id: uuid.UUID | str,
        kind: str,
        qty: Decimal | int | str,
        rate: Decimal | int | str,
        task_type: Optional[str] = None,
        resource_type: Optional[str] = None,
        vendor_id: Optional[uuid.UUID | str] = None,
        section: Optional[str] = None,
        **base: Any,
    ):
        super().__init__(**base)
        self.bid_id = _uuid(bid_id, "bid_id")
        self.kind = _text(kind, "kind")
        self.qty = _decimal(qty, "qty")
        self.rate = _decimal(rate, "rate")
        self.task_type = _opt_text(task_type, "task_type")
        self.resource_type = _opt_text(resource_type, "resource_type")
        self.vendor_id = _opt_uuid(vendor_id, "vendor_id")
        self.section = _opt_text(section, "section")

    def to_attributes(self) -> dict[str, Any]:
        return {
            "bid_id": str(self.bid_id),
            "kind": self.kind,
            "task_type": self.task_type,
            "resource_type": self.resource_type,
            "qty": self.qty,
            "rate": self.rate,
            "vendor_id": _sid(self.vendor_id),
            "section": self.section,
        }

    @classmethod
    def _kwargs_from_record(cls, a: dict, status: Optional[str]) -> dict[str, Any]:
        return {key: a.get(key) for key in cls.TYPED_KEYS}


# entity_type → class. EntityRepo dispatches through this map (one branch).
SCHEDULING_CLASSES: dict[str, type[SchedulingRecord]] = {
    cls.ENTITY_TYPE: cls
    for cls in (
        Task, Responsibility, Person, Vendor, Resource,
        ResourceDependency, Booking, Bid, BidLine,
    )
}
