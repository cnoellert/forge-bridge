"""Orchestration promotion ledger repository — append-only."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from forge_bridge.store.errors import AppendOnlyLedgerError
from forge_bridge.store.models import DBOrchestrationPromotionLedger

_TABLE = "orchestration_promotion_ledger"


class OrchestrationPromotionLedgerRepo:
    """Append-only promotion ledger. Insert-only discipline."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def insert_promotion(
        self,
        *,
        shot_id: uuid.UUID,
        promoted_artifact_id: uuid.UUID,
        promoted_by: str,
        rationale: str,
        superseded_id: uuid.UUID | None = None,
        audit_report_id: uuid.UUID | None = None,
        promotion_id: uuid.UUID | None = None,
        promoted_at: datetime | None = None,
    ) -> DBOrchestrationPromotionLedger:
        row = DBOrchestrationPromotionLedger(
            promotion_id=promotion_id or uuid.uuid4(),
            shot_id=shot_id,
            promoted_artifact_id=promoted_artifact_id,
            superseded_id=superseded_id,
            audit_report_id=audit_report_id,
            promoted_by=promoted_by,
            rationale=rationale,
        )
        if promoted_at is not None:
            row.promoted_at = promoted_at
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_current_canonical(
        self,
        shot_id: uuid.UUID,
    ) -> DBOrchestrationPromotionLedger | None:
        result = await self.session.execute(
            select(DBOrchestrationPromotionLedger)
            .where(DBOrchestrationPromotionLedger.shot_id == shot_id)
            .order_by(DBOrchestrationPromotionLedger.promoted_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_canonical_at(
        self,
        shot_id: uuid.UUID,
        at_timestamp: datetime,
    ) -> DBOrchestrationPromotionLedger | None:
        result = await self.session.execute(
            select(DBOrchestrationPromotionLedger)
            .where(
                DBOrchestrationPromotionLedger.shot_id == shot_id,
                DBOrchestrationPromotionLedger.promoted_at <= at_timestamp,
            )
            .order_by(DBOrchestrationPromotionLedger.promoted_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_history(
        self,
        shot_id: uuid.UUID,
    ) -> list[DBOrchestrationPromotionLedger]:
        result = await self.session.execute(
            select(DBOrchestrationPromotionLedger)
            .where(DBOrchestrationPromotionLedger.shot_id == shot_id)
            .order_by(DBOrchestrationPromotionLedger.promoted_at.desc())
        )
        return list(result.scalars().all())

    async def was_ever_canonical(
        self,
        artifact_id: uuid.UUID,
    ) -> DBOrchestrationPromotionLedger | None:
        result = await self.session.execute(
            select(DBOrchestrationPromotionLedger)
            .where(DBOrchestrationPromotionLedger.promoted_artifact_id == artifact_id)
            .order_by(DBOrchestrationPromotionLedger.promoted_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update(self, promotion_id: uuid.UUID, **kwargs: object) -> None:
        _ = (promotion_id, kwargs)
        raise AppendOnlyLedgerError(_TABLE, "update")

    async def delete(self, promotion_id: uuid.UUID) -> None:
        _ = promotion_id
        raise AppendOnlyLedgerError(_TABLE, "delete")
