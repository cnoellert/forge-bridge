"""GraphEngine event consumer for generation_artifact_terminal (Phase 4B §6)."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from forge_bridge.orchestration.engine import GraphEngine
from forge_bridge.store.models import DBEntity, DBEvent
from forge_bridge.store.orch_generation_artifact_repo import GenerationArtifactRepo
from forge_bridge.store.orchestration_lifecycle_state_repo import (
    OrchestrationLifecycleStateRepo,
)
from forge_bridge.store.repo import EventRepo

ConsumerAction = Literal[
    "no_op_already_advanced",
    "waiting_on_more_artifacts",
    "advanced_to_audit",
    "paused_zero_candidates",
]


@dataclass(frozen=True)
class ConsumerProcessResult:
    event_id: uuid.UUID
    run_id: uuid.UUID
    action: ConsumerAction
    candidates_count: int
    diagnostics_count: int
    in_flight_count: int


class GraphEngineEventConsumer:
    """Processes generation_artifact_terminal events and advances runs."""

    TERMINAL_EVENT_TYPE = "generation_artifact_terminal"

    def __init__(
        self,
        session: AsyncSession,
        *,
        graph_engine: GraphEngine,
    ) -> None:
        self.session = session
        self.graph_engine = graph_engine
        self._events = EventRepo(session)

    async def process_terminal_event(self, event: DBEvent) -> ConsumerProcessResult:
        if event.event_type != self.TERMINAL_EVENT_TYPE:
            raise ValueError(
                f"Expected {self.TERMINAL_EVENT_TYPE!r}, got {event.event_type!r}"
            )

        payload = event.payload if isinstance(event.payload, dict) else {}
        run_raw = payload.get("run_id")
        if run_raw is None:
            raise ValueError("generation_artifact_terminal missing run_id")
        run_id = uuid.UUID(str(run_raw))

        lifecycle = await OrchestrationLifecycleStateRepo(self.session).get_by_run_id(
            run_id
        )
        if lifecycle is None:
            result = ConsumerProcessResult(
                event_id=event.id,
                run_id=run_id,
                action="no_op_already_advanced",
                candidates_count=0,
                diagnostics_count=0,
                in_flight_count=0,
            )
            await self._emit_no_op(event.id, run_id, "run_not_found")
            return result

        if lifecycle.current_stage != "execution":
            result = ConsumerProcessResult(
                event_id=event.id,
                run_id=run_id,
                action="no_op_already_advanced",
                candidates_count=0,
                diagnostics_count=0,
                in_flight_count=0,
            )
            await self._emit_no_op(event.id, run_id, "already_past_execution")
            return result

        counts = await self._partition_run_artifacts(run_id)
        if counts["in_flight"] > 0:
            result = ConsumerProcessResult(
                event_id=event.id,
                run_id=run_id,
                action="waiting_on_more_artifacts",
                candidates_count=counts["candidates"],
                diagnostics_count=counts["diagnostics"],
                in_flight_count=counts["in_flight"],
            )
            await self._emit_no_op(event.id, run_id, "waiting_on_more_artifacts")
            return result

        if counts["candidates"] > 0:
            await self.graph_engine.transition(
                run_id,
                to_stage="audit",
                event_payload={
                    "candidate_count": counts["candidates"],
                    "diagnostic_count": counts["diagnostics"],
                    "source_event_id": str(event.id),
                },
            )
            await self._events.append(
                "engine_consumer_advanced",
                {
                    "event_id": str(event.id),
                    "run_id": str(run_id),
                    "new_stage": "audit",
                    "candidates_count": counts["candidates"],
                    "diagnostics_count": counts["diagnostics"],
                },
                entity_id=run_id,
            )
            return ConsumerProcessResult(
                event_id=event.id,
                run_id=run_id,
                action="advanced_to_audit",
                candidates_count=counts["candidates"],
                diagnostics_count=counts["diagnostics"],
                in_flight_count=0,
            )

        block = {
            "kind": "awaiting_decision",
            "decision_type": "approve_remediation",
            "reason": "execution_zero_candidates",
            "set_at": datetime.now(timezone.utc).isoformat(),
        }
        await self.graph_engine.transition(
            run_id,
            to_status="paused",
            block=block,
        )
        await self._events.append(
            "engine_consumer_paused",
            {
                "event_id": str(event.id),
                "run_id": str(run_id),
                "decision_type": "approve_remediation",
                "reason": "execution_zero_candidates",
            },
            entity_id=run_id,
        )
        return ConsumerProcessResult(
            event_id=event.id,
            run_id=run_id,
            action="paused_zero_candidates",
            candidates_count=0,
            diagnostics_count=counts["diagnostics"],
            in_flight_count=0,
        )

    async def process_pending(
        self,
        *,
        after_event_id: uuid.UUID | None = None,
    ) -> list[ConsumerProcessResult]:
        stmt = (
            select(DBEvent)
            .where(DBEvent.event_type == self.TERMINAL_EVENT_TYPE)
            .order_by(DBEvent.occurred_at.asc(), DBEvent.id.asc())
        )
        if after_event_id is not None:
            anchor = await self.session.get(DBEvent, after_event_id)
            if anchor is not None:
                stmt = stmt.where(
                    (DBEvent.occurred_at > anchor.occurred_at)
                    | (
                        (DBEvent.occurred_at == anchor.occurred_at)
                        & (DBEvent.id > anchor.id)
                    )
                )
        result = await self.session.execute(stmt)
        events = list(result.scalars().all())
        return [await self.process_terminal_event(event) for event in events]

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

    async def _partition_run_artifacts(self, run_id: uuid.UUID) -> dict[str, int]:
        run_str = str(run_id)
        result = await self.session.execute(
            select(DBEntity).where(DBEntity.entity_type == "orch_generation_artifact")
        )
        in_flight = 0
        candidates = 0
        diagnostics = 0
        for entity in result.scalars().all():
            attrs = entity.attributes if isinstance(entity.attributes, dict) else {}
            if str(attrs.get("run_id")) != run_str:
                continue
            state = entity.status or ""
            if state in GenerationArtifactRepo.NON_TERMINAL_STATES:
                in_flight += 1
            elif state in {"complete", "partial"}:
                candidates += 1
            elif state in {"failed", "cancelled"}:
                diagnostics += 1
        return {
            "in_flight": in_flight,
            "candidates": candidates,
            "diagnostics": diagnostics,
        }

    async def _emit_no_op(
        self,
        event_id: uuid.UUID,
        run_id: uuid.UUID,
        reason: str,
    ) -> None:
        await self._events.append(
            "engine_consumer_no_op",
            {
                "event_id": str(event_id),
                "run_id": str(run_id),
                "reason": reason,
            },
            entity_id=run_id,
        )
