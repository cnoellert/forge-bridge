"""Retention and two-phase collection for registry-owned fitted models.

Bridge owns lifecycle state and audit. Storage plugins own deletion of the
actual weights bytes. Collection therefore has two explicit phases: Bridge
marks an expired, idle model and returns its locations; a storage executor
deletes those locations and returns receipts; Bridge then archives the model
aggregate while preserving locators and lineage for archaeology.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from forge_bridge.store.models import DBEntity, DBLocation
from forge_bridge.store.repo import EventRepo


FITTED_MODEL_ASSET_TYPE = "fitted-model"
GC_ACTIVE = "active"
GC_MARKED = "marked"
GC_COLLECTED = "collected"


class FittedModelLifecycleError(ValueError):
    """A fitted-model lifecycle transition is invalid or unsafe."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class FittedModelLocation:
    location_id: uuid.UUID
    entity_id: uuid.UUID
    path: str
    storage_type: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "location_id": str(self.location_id),
            "entity_id": str(self.entity_id),
            "path": self.path,
            "storage_type": self.storage_type,
        }


@dataclass(frozen=True)
class FittedModelGcCandidate:
    asset_id: uuid.UUID
    name: str | None
    retention_until: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None
    locations: tuple[FittedModelLocation, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_id": str(self.asset_id),
            "name": self.name,
            "retention_until": self.retention_until.isoformat(),
            "last_used_at": (
                self.last_used_at.isoformat() if self.last_used_at else None
            ),
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "locations": [location.to_dict() for location in self.locations],
        }


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | str, *, field: str) -> datetime:
    try:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise FittedModelLifecycleError(
            "invalid_datetime", f"{field} must be an ISO-8601 datetime"
        ) from exc
    if parsed.tzinfo is None:
        raise FittedModelLifecycleError(
            "invalid_datetime", f"{field} must include a timezone"
        )
    return parsed.astimezone(timezone.utc)


def _optional_datetime(value: Any, *, field: str) -> datetime | None:
    if value is None:
        return None
    return _as_utc(value, field=field)


def _gc_state(entity: DBEntity) -> str:
    return str((entity.attributes or {}).get("gc_state") or GC_ACTIVE)


def _validate_fitted_model(entity: DBEntity | None, asset_id: uuid.UUID) -> DBEntity:
    if entity is None or entity.entity_type != "asset":
        raise FittedModelLifecycleError(
            "model_not_found", f"fitted-model asset not found: {asset_id}"
        )
    if (entity.attributes or {}).get("asset_type") != FITTED_MODEL_ASSET_TYPE:
        raise FittedModelLifecycleError(
            "model_not_found", f"entity is not a fitted-model asset: {asset_id}"
        )
    return entity


def _availability_refusal(entity: DBEntity) -> str | None:
    attrs = entity.attributes or {}
    if attrs.get("revoked_at") is not None:
        return "model_revoked"
    state = _gc_state(entity)
    if state == GC_MARKED:
        return "model_gc_pending"
    if state == GC_COLLECTED:
        return "model_collected"
    if state != GC_ACTIVE:
        return "model_lifecycle_invalid"
    return None


class FittedModelLifecycleRepo:
    """Own fitted-model retention, use latching, and collection state."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._events = EventRepo(session)

    async def lock_for_inference(
        self,
        asset_id: uuid.UUID,
    ) -> tuple[DBEntity | None, str | None]:
        result = await self.session.execute(
            select(DBEntity).where(DBEntity.id == asset_id).with_for_update()
        )
        entity = result.scalar_one_or_none()
        try:
            entity = _validate_fitted_model(entity, asset_id)
        except FittedModelLifecycleError as exc:
            return None, exc.code
        return entity, _availability_refusal(entity)

    async def record_use(
        self,
        entity: DBEntity,
        *,
        operator_id: str,
        request_id: str,
        used_at: datetime | None = None,
    ) -> None:
        _validate_fitted_model(entity, entity.id)
        refusal = _availability_refusal(entity)
        if refusal is not None:
            raise FittedModelLifecycleError(
                refusal, f"fitted-model is not available for inference: {refusal}"
            )
        timestamp = (
            _as_utc(used_at, field="used_at") if used_at is not None else _utc_now()
        )
        attrs = dict(entity.attributes or {})
        attrs["last_used_at"] = timestamp.isoformat()
        entity.attributes = attrs
        await self._events.append(
            event_type="fitted_model.used",
            payload={
                "asset_id": str(entity.id),
                "used_at": timestamp.isoformat(),
                "operator_id": operator_id,
                "request_id": request_id,
            },
            client_name="bridge",
            project_id=entity.project_id,
            entity_id=entity.id,
        )

    async def set_retention(
        self,
        asset_id: uuid.UUID,
        *,
        retention_until: datetime | str,
        actor: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        entity = await self._lock_asset(asset_id)
        if _gc_state(entity) == GC_COLLECTED:
            raise FittedModelLifecycleError(
                "model_collected", "a collected fitted-model cannot be retained again"
            )
        retain_until = _as_utc(retention_until, field="retention_until")
        attrs = dict(entity.attributes or {})
        prior = attrs.get("retention_until")
        was_marked = _gc_state(entity) == GC_MARKED
        attrs["retention_until"] = retain_until.isoformat()
        attrs["retention_set_by"] = actor
        attrs["retention_set_at"] = _utc_now().isoformat()
        attrs["retention_reason"] = reason
        if was_marked:
            attrs["gc_state"] = GC_ACTIVE
            for key in ("gc_marked_at", "gc_marked_by", "gc_collect_after"):
                attrs.pop(key, None)
        entity.attributes = attrs
        await self._events.append(
            event_type="fitted_model.retention_set",
            payload={
                "asset_id": str(asset_id),
                "prior_retention_until": prior,
                "retention_until": retain_until.isoformat(),
                "actor": actor,
                "reason": reason,
                "gc_mark_cancelled": was_marked,
            },
            client_name=actor,
            project_id=entity.project_id,
            entity_id=asset_id,
        )
        return self._state(entity)

    async def list_gc_candidates(
        self,
        *,
        as_of: datetime | str | None = None,
    ) -> list[FittedModelGcCandidate]:
        instant = _as_utc(as_of, field="as_of") if as_of is not None else _utc_now()
        result = await self.session.execute(
            select(DBEntity)
            .where(
                DBEntity.entity_type == "asset",
                DBEntity.attributes.contains({"asset_type": FITTED_MODEL_ASSET_TYPE}),
            )
            .order_by(DBEntity.created_at.asc(), DBEntity.id.asc())
        )
        candidates: list[FittedModelGcCandidate] = []
        for entity in result.scalars().all():
            if not self._is_candidate(entity, instant):
                continue
            candidates.append(await self._candidate(entity))
        return candidates

    async def mark_gc(
        self,
        asset_id: uuid.UUID,
        *,
        collect_after: datetime | str,
        actor: str,
        as_of: datetime | str | None = None,
    ) -> dict[str, Any]:
        instant = _as_utc(as_of, field="as_of") if as_of is not None else _utc_now()
        collection_deadline = _as_utc(collect_after, field="collect_after")
        if collection_deadline <= instant:
            raise FittedModelLifecycleError(
                "invalid_grace_period", "collect_after must be later than as_of"
            )
        entity = await self._lock_asset(asset_id)
        if _gc_state(entity) != GC_ACTIVE:
            raise FittedModelLifecycleError(
                "illegal_gc_state", "only an active fitted-model can be marked"
            )
        if not self._is_candidate(entity, instant):
            raise FittedModelLifecycleError(
                "model_not_gc_eligible",
                "fitted-model retention has not expired or it was used after expiry",
            )
        candidate = await self._candidate(entity)
        attrs = dict(entity.attributes or {})
        attrs.update({
            "gc_state": GC_MARKED,
            "gc_marked_at": instant.isoformat(),
            "gc_marked_by": actor,
            "gc_collect_after": collection_deadline.isoformat(),
        })
        entity.attributes = attrs
        await self._events.append(
            event_type="fitted_model.gc_marked",
            payload={
                "asset_id": str(asset_id),
                "gc_marked_at": instant.isoformat(),
                "gc_collect_after": collection_deadline.isoformat(),
                "actor": actor,
                "locations": [location.to_dict() for location in candidate.locations],
            },
            client_name=actor,
            project_id=entity.project_id,
            entity_id=asset_id,
        )
        state = self._state(entity)
        state["locations"] = [location.to_dict() for location in candidate.locations]
        return state

    async def finalize_gc(
        self,
        asset_id: uuid.UUID,
        *,
        deletion_receipts: Iterable[dict[str, Any]],
        actor: str,
        as_of: datetime | str | None = None,
    ) -> dict[str, Any]:
        instant = _as_utc(as_of, field="as_of") if as_of is not None else _utc_now()
        entity = await self._lock_asset(asset_id)
        attrs = dict(entity.attributes or {})
        if _gc_state(entity) != GC_MARKED:
            raise FittedModelLifecycleError(
                "illegal_gc_state", "fitted-model must be marked before collection"
            )
        collect_after = _optional_datetime(
            attrs.get("gc_collect_after"), field="gc_collect_after"
        )
        if collect_after is None or instant < collect_after:
            raise FittedModelLifecycleError(
                "gc_grace_active", "fitted-model collection grace period has not elapsed"
            )
        marked_at = _optional_datetime(attrs.get("gc_marked_at"), field="gc_marked_at")
        last_used = _optional_datetime(attrs.get("last_used_at"), field="last_used_at")
        if marked_at is None or (last_used is not None and last_used > marked_at):
            raise FittedModelLifecycleError(
                "model_used_after_gc_mark",
                "fitted-model was used after the GC mark and must be reviewed again",
            )

        aggregate, locations = await self._aggregate(entity)
        receipts = self._validate_receipts(locations, deletion_receipts)
        collected_at = instant.isoformat()
        for location in locations:
            receipt = receipts[location.id]
            location.exists = False
            location.checked_at = instant
            location_attrs = dict(location.attributes or {})
            location_attrs["gc_deletion_receipt"] = receipt
            location.attributes = location_attrs
        for member in aggregate:
            member_attrs = dict(member.attributes or {})
            member_attrs["gc_collected_at"] = collected_at
            member_attrs["gc_collected_by"] = actor
            if member.id == asset_id:
                member_attrs["gc_state"] = GC_COLLECTED
            member.attributes = member_attrs
            member.status = "archived"

        await self._events.append(
            event_type="fitted_model.gc_collected",
            payload={
                "asset_id": str(asset_id),
                "gc_collected_at": collected_at,
                "actor": actor,
                "aggregate_entity_ids": [str(member.id) for member in aggregate],
                "deletion_receipts": list(receipts.values()),
            },
            client_name=actor,
            project_id=entity.project_id,
            entity_id=asset_id,
        )
        state = self._state(entity)
        state["archived_entity_ids"] = [str(member.id) for member in aggregate]
        state["deletion_receipts"] = list(receipts.values())
        return state

    async def _lock_asset(self, asset_id: uuid.UUID) -> DBEntity:
        result = await self.session.execute(
            select(DBEntity).where(DBEntity.id == asset_id).with_for_update()
        )
        return _validate_fitted_model(result.scalar_one_or_none(), asset_id)

    def _is_candidate(self, entity: DBEntity, as_of: datetime) -> bool:
        attrs = entity.attributes or {}
        if _gc_state(entity) != GC_ACTIVE:
            return False
        retention_until = _optional_datetime(
            attrs.get("retention_until"), field="retention_until"
        )
        if retention_until is None or retention_until > as_of:
            return False
        last_used = _optional_datetime(attrs.get("last_used_at"), field="last_used_at")
        return last_used is None or last_used <= retention_until

    async def _candidate(self, entity: DBEntity) -> FittedModelGcCandidate:
        attrs = entity.attributes or {}
        retention_until = _optional_datetime(
            attrs.get("retention_until"), field="retention_until"
        )
        assert retention_until is not None
        _aggregate, locations = await self._aggregate(entity)
        return FittedModelGcCandidate(
            asset_id=entity.id,
            name=entity.name,
            retention_until=retention_until,
            last_used_at=_optional_datetime(attrs.get("last_used_at"), field="last_used_at"),
            revoked_at=_optional_datetime(attrs.get("revoked_at"), field="revoked_at"),
            locations=tuple(
                FittedModelLocation(
                    location_id=location.id,
                    entity_id=location.entity_id,
                    path=location.path,
                    storage_type=location.storage_type,
                )
                for location in locations
            ),
        )

    async def _aggregate(
        self,
        asset: DBEntity,
    ) -> tuple[list[DBEntity], list[DBLocation]]:
        versions_result = await self.session.execute(
            select(DBEntity).where(
                DBEntity.entity_type == "version",
                DBEntity.attributes.contains({
                    "parent_id": str(asset.id),
                    "parent_type": "asset",
                }),
            )
        )
        versions = list(versions_result.scalars().all())
        media: list[DBEntity] = []
        if versions:
            media_result = await self.session.execute(
                select(DBEntity).where(
                    DBEntity.entity_type == "media",
                    or_(*[
                        DBEntity.attributes.contains({"version_id": str(version.id)})
                        for version in versions
                    ]),
                )
            )
            media = list(media_result.scalars().all())
        aggregate = [asset, *versions, *media]
        locations_result = await self.session.execute(
            select(DBLocation)
            .where(DBLocation.entity_id.in_([member.id for member in aggregate]))
            .order_by(DBLocation.path.asc(), DBLocation.id.asc())
        )
        return aggregate, list(locations_result.scalars().all())

    @staticmethod
    def _validate_receipts(
        locations: list[DBLocation],
        deletion_receipts: Iterable[dict[str, Any]],
    ) -> dict[uuid.UUID, dict[str, Any]]:
        expected = {location.id: location for location in locations}
        actual: dict[uuid.UUID, dict[str, Any]] = {}
        for raw in deletion_receipts:
            if not isinstance(raw, dict):
                raise FittedModelLifecycleError(
                    "invalid_deletion_receipt", "each deletion receipt must be an object"
                )
            try:
                location_id = uuid.UUID(str(raw.get("location_id")))
            except (TypeError, ValueError) as exc:
                raise FittedModelLifecycleError(
                    "invalid_deletion_receipt", "receipt location_id must be a UUID"
                ) from exc
            if location_id in actual:
                raise FittedModelLifecycleError(
                    "invalid_deletion_receipt", f"duplicate receipt for {location_id}"
                )
            location = expected.get(location_id)
            if location is None:
                raise FittedModelLifecycleError(
                    "invalid_deletion_receipt", f"unexpected location {location_id}"
                )
            if raw.get("deleted") is not True or raw.get("path") != location.path:
                raise FittedModelLifecycleError(
                    "deletion_unproven",
                    f"receipt does not prove deletion for {location.path!r}",
                )
            actual[location_id] = dict(raw)
        missing = set(expected) - set(actual)
        if missing:
            raise FittedModelLifecycleError(
                "deletion_unproven",
                "missing deletion receipts for locations: "
                + ", ".join(str(location_id) for location_id in sorted(missing)),
            )
        return actual

    @staticmethod
    def _state(entity: DBEntity) -> dict[str, Any]:
        attrs = entity.attributes or {}
        return {
            "asset_id": str(entity.id),
            "name": entity.name,
            "asset_type": attrs.get("asset_type"),
            "status": entity.status,
            "retention_until": attrs.get("retention_until"),
            "retention_reason": attrs.get("retention_reason"),
            "retention_set_by": attrs.get("retention_set_by"),
            "retention_set_at": attrs.get("retention_set_at"),
            "last_used_at": attrs.get("last_used_at"),
            "revoked_at": attrs.get("revoked_at"),
            "gc_state": _gc_state(entity),
            "gc_marked_at": attrs.get("gc_marked_at"),
            "gc_marked_by": attrs.get("gc_marked_by"),
            "gc_collect_after": attrs.get("gc_collect_after"),
            "gc_collected_at": attrs.get("gc_collected_at"),
            "gc_collected_by": attrs.get("gc_collected_by"),
        }


__all__ = [
    "FITTED_MODEL_ASSET_TYPE",
    "GC_ACTIVE",
    "GC_COLLECTED",
    "GC_MARKED",
    "FittedModelGcCandidate",
    "FittedModelLifecycleError",
    "FittedModelLifecycleRepo",
    "FittedModelLocation",
]
