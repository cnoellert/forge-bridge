"""Orchestration lifecycle state repository (Phase 4B §6)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import null as sa_null
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from forge_bridge.store.errors import LifecycleConsistencyError, MultipleActiveRunsError
from forge_bridge.store.models import DBOrchestrationLifecycleState

VALID_STAGES = frozenset(
    {
        "ingest",
        "spec_convergence",
        "routing",
        "execution",
        "audit",
        "promotion",
        "publish",
    }
)
VALID_STATUSES = frozenset({"active", "paused", "completed", "failed", "cancelled"})

_UNSET = object()


def _validate_stage(stage: str) -> None:
    if stage not in VALID_STAGES:
        raise ValueError(f"Invalid current_stage {stage!r}; expected one of {sorted(VALID_STAGES)}")


def _validate_status(status: str) -> None:
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status {status!r}; expected one of {sorted(VALID_STATUSES)}")


def _validate_paused_block(run_id: uuid.UUID, status: str, block: dict | None) -> None:
    if (status == "paused") != (block is not None):
        raise LifecycleConsistencyError(run_id, status, block is not None)


class OrchestrationLifecycleStateRepo:
    """State-machine primitives for orchestration_lifecycle_state."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def insert(
        self,
        *,
        run_id: uuid.UUID,
        shot_id: uuid.UUID,
        current_stage: str,
        status: str = "active",
        intent_id: uuid.UUID | None = None,
        plan_id: uuid.UUID | None = None,
        current_canonical: uuid.UUID | None = None,
        block: dict | None = None,
        last_event_id: uuid.UUID | None = None,
        stage_entered_at: datetime | None = None,
    ) -> DBOrchestrationLifecycleState:
        _validate_stage(current_stage)
        _validate_status(status)
        _validate_paused_block(run_id, status, block)

        row = DBOrchestrationLifecycleState(
            run_id=run_id,
            shot_id=shot_id,
            current_stage=current_stage,
            stage_entered_at=stage_entered_at or datetime.now(timezone.utc),
            intent_id=intent_id,
            plan_id=plan_id,
            current_canonical=current_canonical,
            status=status,
            last_event_id=last_event_id,
        )
        if block is not None:
            row.block = block
        self.session.add(row)
        await self.session.flush()
        return row

    async def update_state(
        self,
        run_id: uuid.UUID,
        *,
        current_stage: str | None = None,
        status: str | None = None,
        intent_id: uuid.UUID | None | object = _UNSET,
        plan_id: uuid.UUID | None | object = _UNSET,
        current_canonical: uuid.UUID | None | object = _UNSET,
        block: dict | None | object = _UNSET,
        last_event_id: uuid.UUID | None | object = _UNSET,
        clear_block: bool = False,
        stage_entered_at: datetime | None = None,
    ) -> DBOrchestrationLifecycleState:
        row = await self.session.get(DBOrchestrationLifecycleState, run_id)
        if row is None:
            raise ValueError(f"No orchestration lifecycle row for run_id={run_id}")

        effective_status = status if status is not None else row.status
        if clear_block:
            effective_block = None
        elif block is not _UNSET:
            effective_block = block  # type: ignore[assignment]
        else:
            effective_block = row.block

        if current_stage is not None:
            _validate_stage(current_stage)
        if status is not None:
            _validate_status(status)
        _validate_paused_block(run_id, effective_status, effective_block)

        if current_stage is not None:
            row.current_stage = current_stage
        if status is not None:
            row.status = status
        if intent_id is not _UNSET:
            row.intent_id = intent_id  # type: ignore[assignment]
        if plan_id is not _UNSET:
            row.plan_id = plan_id  # type: ignore[assignment]
        if current_canonical is not _UNSET:
            row.current_canonical = current_canonical  # type: ignore[assignment]
        if last_event_id is not _UNSET:
            row.last_event_id = last_event_id  # type: ignore[assignment]
        if stage_entered_at is not None:
            row.stage_entered_at = stage_entered_at

        if clear_block:
            row.block = sa_null()
        elif block is not _UNSET:
            row.block = block  # type: ignore[assignment]

        row.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def get_by_run_id(
        self,
        run_id: uuid.UUID,
    ) -> DBOrchestrationLifecycleState | None:
        return await self.session.get(DBOrchestrationLifecycleState, run_id)

    async def find_active(self) -> list[DBOrchestrationLifecycleState]:
        result = await self.session.execute(
            select(DBOrchestrationLifecycleState).where(
                DBOrchestrationLifecycleState.status == "active"
            )
        )
        return list(result.scalars().all())

    async def find_active_for_shot(
        self,
        shot_id: uuid.UUID,
    ) -> DBOrchestrationLifecycleState | None:
        result = await self.session.execute(
            select(DBOrchestrationLifecycleState).where(
                DBOrchestrationLifecycleState.shot_id == shot_id,
                DBOrchestrationLifecycleState.status == "active",
            )
        )
        rows = list(result.scalars().all())
        if len(rows) > 1:
            raise MultipleActiveRunsError(shot_id, [row.run_id for row in rows])
        return rows[0] if rows else None
