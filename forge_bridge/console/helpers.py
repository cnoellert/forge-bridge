"""Operator helper functions for console-side ratification inspection."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from forge_bridge.core.assent import AssentRecord
from forge_bridge.store.assent_record_repo import AssentRecordRepo
from forge_bridge.store.models import DBEntity
from forge_bridge.store.session import get_session

_DEFAULT_WINDOW = timedelta(hours=24)


async def recent_ratifications(
    window: timedelta = _DEFAULT_WINDOW,
) -> list[AssentRecord]:
    """Return assent records whose decided_at falls within window.

    Includes any state that passed through ratified: ``ratified``, ``applied``,
    or ``failed``. Proposed records are not yet ratified.
    """
    records = await _list_assent_records(statuses={"ratified", "applied", "failed"})
    return [
        record
        for record in records
        if record.decided_at is not None and _within_window(record.decided_at, window)
    ]


async def pending_assent_records() -> list[AssentRecord]:
    """Return assent records in 'proposed' state."""
    async with get_session() as session:
        repo = AssentRecordRepo(session)
        records, _ = await repo.list_pending(status="proposed")
        return records


async def recent_failed_applies(
    window: timedelta = _DEFAULT_WINDOW,
) -> list[AssentRecord]:
    """Return failed assent records whose applied_at falls within window."""
    records = await _list_assent_records(statuses={"failed"})
    return [
        record
        for record in records
        if record.applied_at is not None and _within_window(record.applied_at, window)
    ]


async def _list_assent_records(*, statuses: set[str]) -> list[AssentRecord]:
    async with get_session() as session:
        result = await session.execute(
            select(DBEntity)
            .where(
                DBEntity.entity_type == "assent_record",
                DBEntity.status.in_(sorted(statuses)),
            )
            .order_by(DBEntity.created_at.desc())
        )
        return [AssentRecord.from_entity(entity) for entity in result.scalars()]


def _within_window(value: datetime, window: timedelta) -> bool:
    now = datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value >= now - window
