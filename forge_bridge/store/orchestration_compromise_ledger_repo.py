"""Orchestration compromise ledger repository — append-only."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import ClassVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from forge_bridge.store.errors import AppendOnlyLedgerError
from forge_bridge.store.models import DBOrchestrationCompromiseLedger

_TABLE = "orchestration_compromise_ledger"


class OrchestrationCompromiseLedgerRepo:
    """Append-only compromise ledger."""

    SIDES: ClassVar[frozenset[str]] = frozenset({"planned_predicted", "audit_actual"})

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _validate_side(self, side: str) -> None:
        if side not in self.SIDES:
            raise ValueError(
                f"Invalid compromise ledger side {side!r}; expected one of {sorted(self.SIDES)}"
            )

    async def _insert_entry(
        self,
        *,
        intent_id: uuid.UUID,
        run_id: uuid.UUID,
        criterion_id: str,
        dimension: str,
        side: str,
        magnitude: dict,
        plan_id: uuid.UUID | None = None,
        artifact_id: uuid.UUID | None = None,
        entry_id: uuid.UUID | None = None,
        recorded_at: datetime | None = None,
    ) -> DBOrchestrationCompromiseLedger:
        self._validate_side(side)
        row = DBOrchestrationCompromiseLedger(
            entry_id=entry_id or uuid.uuid4(),
            intent_id=intent_id,
            run_id=run_id,
            plan_id=plan_id,
            artifact_id=artifact_id,
            criterion_id=criterion_id,
            dimension=dimension,
            side=side,
            magnitude=magnitude,
        )
        if recorded_at is not None:
            row.recorded_at = recorded_at
        self.session.add(row)
        await self.session.flush()
        return row

    async def insert_planned_predicted(
        self,
        *,
        intent_id: uuid.UUID,
        run_id: uuid.UUID,
        plan_id: uuid.UUID,
        criterion_id: str,
        dimension: str,
        magnitude: dict,
        entry_id: uuid.UUID | None = None,
        recorded_at: datetime | None = None,
    ) -> DBOrchestrationCompromiseLedger:
        return await self._insert_entry(
            intent_id=intent_id,
            run_id=run_id,
            plan_id=plan_id,
            criterion_id=criterion_id,
            dimension=dimension,
            side="planned_predicted",
            magnitude=magnitude,
            entry_id=entry_id,
            recorded_at=recorded_at,
        )

    async def insert_audit_actual(
        self,
        *,
        intent_id: uuid.UUID,
        run_id: uuid.UUID,
        artifact_id: uuid.UUID,
        criterion_id: str,
        dimension: str,
        magnitude: dict,
        entry_id: uuid.UUID | None = None,
        recorded_at: datetime | None = None,
    ) -> DBOrchestrationCompromiseLedger:
        return await self._insert_entry(
            intent_id=intent_id,
            run_id=run_id,
            artifact_id=artifact_id,
            criterion_id=criterion_id,
            dimension=dimension,
            side="audit_actual",
            magnitude=magnitude,
            entry_id=entry_id,
            recorded_at=recorded_at,
        )

    async def get_entries(
        self,
        intent_id: uuid.UUID,
        *,
        criterion_id: str | None = None,
        dimension: str | None = None,
        side: str | None = None,
    ) -> list[DBOrchestrationCompromiseLedger]:
        if side is not None:
            self._validate_side(side)

        query = select(DBOrchestrationCompromiseLedger).where(
            DBOrchestrationCompromiseLedger.intent_id == intent_id
        )
        if criterion_id is not None:
            query = query.where(
                DBOrchestrationCompromiseLedger.criterion_id == criterion_id
            )
        if dimension is not None:
            query = query.where(DBOrchestrationCompromiseLedger.dimension == dimension)
        if side is not None:
            query = query.where(DBOrchestrationCompromiseLedger.side == side)

        query = query.order_by(DBOrchestrationCompromiseLedger.recorded_at.asc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, entry_id: uuid.UUID, **kwargs: object) -> None:
        _ = (entry_id, kwargs)
        raise AppendOnlyLedgerError(_TABLE, "update")

    async def delete(self, entry_id: uuid.UUID) -> None:
        _ = entry_id
        raise AppendOnlyLedgerError(_TABLE, "delete")
