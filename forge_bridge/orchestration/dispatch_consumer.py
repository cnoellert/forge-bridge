"""Dispatch consumer for execution-stage entry events (Phase 7 V2)."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from forge_bridge.orchestration.dispatcher import dispatch_plan
from forge_bridge.orchestration.drivers import GenerationDriverRegistry
from forge_bridge.store.models import DBEvent
from forge_bridge.store.orch_execution_plan_repo import ExecutionPlanRepo
from forge_bridge.store.orchestration_lifecycle_state_repo import (
    OrchestrationLifecycleStateRepo,
)
from forge_bridge.store.repo import EventRepo

DispatchConsumerAction = Literal[
    "dispatched",
    "refused",
    "skipped_not_execution",
    "skipped_missing_lifecycle",
    "skipped_missing_plan",
]


@dataclass(frozen=True)
class DispatchConsumerProcessResult:
    event_id: uuid.UUID
    run_id: uuid.UUID | None
    action: DispatchConsumerAction
    artifact_id: uuid.UUID | None = None
    refusal_code: str | None = None


class DispatchOnExecutionEntryConsumer:
    """Consumes stage_advanced events whose destination stage is execution."""

    EXECUTION_ENTRY_EVENT_TYPE = "stage_advanced"

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        driver_registry: GenerationDriverRegistry,
    ) -> None:
        self._session_factory = session_factory
        self._driver_registry = driver_registry

    async def process_execution_entry_event(
        self,
        event: DBEvent,
    ) -> DispatchConsumerProcessResult:
        payload = event.payload if isinstance(event.payload, dict) else {}
        run_raw = payload.get("run_id")
        run_id = uuid.UUID(str(run_raw)) if run_raw is not None else None
        if event.event_type != self.EXECUTION_ENTRY_EVENT_TYPE or payload.get(
            "to_stage"
        ) != "execution":
            await self._emit(
                "dispatch_skipped",
                {
                    "event_id": str(event.id),
                    "run_id": str(run_id) if run_id is not None else None,
                    "reason": "not_execution_entry",
                },
                entity_id=run_id,
            )
            return DispatchConsumerProcessResult(
                event_id=event.id,
                run_id=run_id,
                action="skipped_not_execution",
            )

        if run_id is None:
            await self._emit(
                "dispatch_skipped",
                {
                    "event_id": str(event.id),
                    "run_id": None,
                    "reason": "missing_run_id",
                },
            )
            return DispatchConsumerProcessResult(
                event_id=event.id,
                run_id=None,
                action="skipped_missing_lifecycle",
            )

        async with self._session_factory() as session:
            lifecycle = await OrchestrationLifecycleStateRepo(session).get_by_run_id(
                run_id
            )
            if lifecycle is None:
                await self._emit(
                    "dispatch_skipped",
                    {
                        "event_id": str(event.id),
                        "run_id": str(run_id),
                        "reason": "run_not_found",
                    },
                    entity_id=run_id,
                )
                return DispatchConsumerProcessResult(
                    event_id=event.id,
                    run_id=run_id,
                    action="skipped_missing_lifecycle",
                )

            if lifecycle.current_stage != "execution":
                await self._emit(
                    "dispatch_skipped",
                    {
                        "event_id": str(event.id),
                        "run_id": str(run_id),
                        "reason": "already_past_execution",
                        "current_stage": lifecycle.current_stage,
                    },
                    entity_id=run_id,
                )
                return DispatchConsumerProcessResult(
                    event_id=event.id,
                    run_id=run_id,
                    action="skipped_not_execution",
                )

            if lifecycle.plan_id is None:
                await self._emit(
                    "dispatch_skipped",
                    {
                        "event_id": str(event.id),
                        "run_id": str(run_id),
                        "reason": "missing_plan_id",
                    },
                    entity_id=run_id,
                )
                return DispatchConsumerProcessResult(
                    event_id=event.id,
                    run_id=run_id,
                    action="skipped_missing_plan",
                )

            plan = await ExecutionPlanRepo(session).get_by_id(lifecycle.plan_id)
            if plan is None:
                await self._emit(
                    "dispatch_skipped",
                    {
                        "event_id": str(event.id),
                        "run_id": str(run_id),
                        "plan_id": str(lifecycle.plan_id),
                        "reason": "plan_not_found",
                    },
                    entity_id=run_id,
                )
                return DispatchConsumerProcessResult(
                    event_id=event.id,
                    run_id=run_id,
                    action="skipped_missing_plan",
                )

        dispatch = await dispatch_plan(
            plan,
            driver_registry=self._driver_registry,
            session_factory=self._session_factory,
            event_appender=self._append_event,
            run_id=run_id,
        )
        action: DispatchConsumerAction = (
            "dispatched"
            if dispatch.status in {"submitted", "completed"}
            else "refused"
        )
        await self._emit(
            "dispatch_consumed",
            {
                "event_id": str(event.id),
                "run_id": str(run_id),
                "plan_id": str(plan.id),
                "status": dispatch.status,
                "artifact_id": str(dispatch.artifact_id)
                if dispatch.artifact_id is not None
                else None,
                "refusal_code": dispatch.refusal_code,
            },
            entity_id=run_id,
        )
        return DispatchConsumerProcessResult(
            event_id=event.id,
            run_id=run_id,
            action=action,
            artifact_id=dispatch.artifact_id,
            refusal_code=dispatch.refusal_code,
        )

    async def process_pending(
        self,
        *,
        after_event_id: uuid.UUID | None = None,
    ) -> list[DispatchConsumerProcessResult]:
        stmt = (
            select(DBEvent)
            .where(DBEvent.event_type == self.EXECUTION_ENTRY_EVENT_TYPE)
            .where(DBEvent.payload["to_stage"].as_string() == "execution")
            .order_by(DBEvent.occurred_at.asc(), DBEvent.id.asc())
        )
        if after_event_id is not None:
            async with self._session_factory() as session:
                anchor = await session.get(DBEvent, after_event_id)
                if anchor is not None:
                    stmt = stmt.where(
                        (DBEvent.occurred_at > anchor.occurred_at)
                        | (
                            (DBEvent.occurred_at == anchor.occurred_at)
                            & (DBEvent.id > anchor.id)
                        )
                    )

        async with self._session_factory() as session:
            result = await session.execute(stmt)
            events = list(result.scalars().all())

        results: list[DispatchConsumerProcessResult] = []
        for event in events:
            results.append(await self.process_execution_entry_event(event))
        return results

    async def run_forever(
        self,
        *,
        poll_interval_seconds: float = 1.0,
        shutdown_event: asyncio.Event | None = None,
    ) -> None:
        last_event_id: uuid.UUID | None = None
        while True:
            results = await self.process_pending(after_event_id=last_event_id)
            if results:
                last_event_id = results[-1].event_id
            if shutdown_event is not None and shutdown_event.is_set():
                return
            await asyncio.sleep(poll_interval_seconds)

    async def _append_event(self, event_type: str, payload: dict) -> None:
        await self._emit(event_type, payload)

    async def _emit(
        self,
        event_type: str,
        payload: dict,
        *,
        entity_id: uuid.UUID | None = None,
    ) -> None:
        async with self._session_factory() as session:
            await EventRepo(session).append(event_type, payload, entity_id=entity_id)
            await session.commit()
