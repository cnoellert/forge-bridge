"""GraphEngine — atomic lifecycle transitions + events (Phase 4B §6)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, ClassVar

from sqlalchemy.ext.asyncio import AsyncSession

from forge_bridge.orchestration.errors import (
    DecisionNotAllowedAtStageError,
    InvalidStageTransitionError,
    InvalidStatusTransitionError,
    LifecycleStateAlreadyExistsError,
    LifecycleStateNotFoundError,
    UnknownDecisionEventError,
)
from forge_bridge.store.models import DBOrchestrationLifecycleState
from forge_bridge.store.orchestration_lifecycle_state_repo import (
    OrchestrationLifecycleStateRepo,
    _UNSET,
)
from forge_bridge.store.repo import EventRepo

UNSET = _UNSET

_LEGAL_STAGE_TRANSITIONS: frozenset[tuple[str, str]] = frozenset(
    {
        ("ingest", "spec_convergence"),
        ("spec_convergence", "routing"),
        ("routing", "execution"),
        ("execution", "audit"),
        ("audit", "promotion"),
        ("promotion", "publish"),
    }
)


class GraphEngine:
    """Atomic-transition service over orchestration_lifecycle_state + events.

    The engine is the SOLE writer to orchestration_lifecycle_state.
    Composes OrchestrationLifecycleStateRepo + EventRepo within one session;
    caller owns the transaction (per forge-bridge convention; engine does not commit).

    Per PHASE-4B-ORCHESTRATION-DESIGN.md §6.
    """

    VALID_STAGES: ClassVar[tuple[str, ...]] = (
        "ingest",
        "spec_convergence",
        "routing",
        "execution",
        "audit",
        "promotion",
        "publish",
    )
    VALID_STATUSES: ClassVar[tuple[str, ...]] = (
        "active",
        "paused",
        "completed",
        "failed",
        "cancelled",
    )
    DECISION_EVENT_TYPES: ClassVar[frozenset[str]] = frozenset(
        {"lock_intent", "approve_remediation", "promote_candidate", "cancel_run"}
    )

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._lifecycle = OrchestrationLifecycleStateRepo(session)
        self._events = EventRepo(session)

    async def create_run(
        self,
        *,
        run_id: uuid.UUID,
        shot_id: uuid.UUID,
        initial_stage: str = "ingest",
        initial_status: str = "active",
        intent_id: uuid.UUID | None = None,
        session_id: uuid.UUID | None = None,
        client_name: str | None = None,
    ) -> DBOrchestrationLifecycleState:
        existing = await self._lifecycle.get_by_run_id(run_id)
        if existing is not None:
            raise LifecycleStateAlreadyExistsError(run_id)

        row = await self._lifecycle.insert(
            run_id=run_id,
            shot_id=shot_id,
            current_stage=initial_stage,
            status=initial_status,
            intent_id=intent_id,
        )
        event = await self._events.append(
            "run_created",
            {
                "run_id": str(run_id),
                "shot_id": str(shot_id),
                "initial_stage": initial_stage,
                "initial_status": initial_status,
            },
            session_id=session_id,
            client_name=client_name,
            entity_id=run_id,
        )
        await self._session.flush()
        return await self._lifecycle.update_state(
            run_id,
            last_event_id=event.id,
        )

    async def transition(
        self,
        run_id: uuid.UUID,
        *,
        to_stage: str | None = None,
        to_status: str | None = None,
        intent_id: uuid.UUID | None | object = UNSET,
        plan_id: uuid.UUID | None | object = UNSET,
        current_canonical: uuid.UUID | None | object = UNSET,
        block: dict | None | object = UNSET,
        clear_block: bool = False,
        last_event_id: uuid.UUID | None = None,
        event_payload: dict | None = None,
        session_id: uuid.UUID | None = None,
        client_name: str | None = None,
    ) -> DBOrchestrationLifecycleState:
        current = await self._require_state(run_id)
        from_stage = current.current_stage
        from_status = current.status

        next_stage = to_stage if to_stage is not None else from_stage
        next_status = to_status if to_status is not None else from_status

        self._validate_transition_request(
            current=current,
            next_stage=next_stage,
            next_status=next_status,
            to_stage=to_stage,
            to_status=to_status,
            block=block,
            clear_block=clear_block,
            intent_id=intent_id,
            plan_id=plan_id,
            current_canonical=current_canonical,
        )

        update_kwargs: dict[str, Any] = {
            "intent_id": intent_id,
            "plan_id": plan_id,
            "current_canonical": current_canonical,
            "block": block,
            "clear_block": clear_block,
        }
        if next_stage != from_stage:
            update_kwargs["current_stage"] = next_stage
            update_kwargs["stage_entered_at"] = datetime.now(timezone.utc)
        if next_status != from_status:
            update_kwargs["status"] = next_status

        updated = await self._lifecycle.update_state(run_id, **update_kwargs)

        event_type = self._event_type_for_transition(
            from_stage=from_stage,
            to_stage=next_stage,
            from_status=from_status,
            to_status=next_status,
        )
        payload: dict[str, Any] = {
            "run_id": str(run_id),
            "from_stage": from_stage,
            "to_stage": next_stage,
            "from_status": from_status,
            "to_status": next_status,
            "block_kind": (
                updated.block.get("kind")
                if isinstance(updated.block, dict)
                else None
            ),
        }
        if event_payload:
            payload.update(event_payload)

        event = await self._events.append(
            event_type,
            payload,
            session_id=session_id,
            client_name=client_name,
            entity_id=run_id,
        )
        await self._session.flush()
        anchor = last_event_id if last_event_id is not None else event.id
        return await self._lifecycle.update_state(
            run_id,
            last_event_id=anchor,
        )

    async def apply_decision_event(
        self,
        run_id: uuid.UUID,
        decision_type: str,
        payload: dict,
        *,
        session_id: uuid.UUID | None = None,
        client_name: str | None = None,
    ) -> DBOrchestrationLifecycleState:
        if decision_type not in self.DECISION_EVENT_TYPES:
            raise UnknownDecisionEventError(decision_type)

        current = await self._require_state(run_id)
        self._validate_decision_allowed(decision_type, current)

        event = await self._events.append(
            decision_type,
            payload,
            session_id=session_id,
            client_name=client_name,
            entity_id=run_id,
        )
        await self._session.flush()

        if decision_type == "approve_remediation":
            return await self._lifecycle.update_state(
                run_id,
                last_event_id=event.id,
            )

        if decision_type == "lock_intent":
            intent_raw = payload.get("intent_id")
            parsed_intent = (
                uuid.UUID(str(intent_raw)) if intent_raw is not None else None
            )
            return await self._apply_lifecycle_after_decision(
                run_id,
                current=current,
                event_id=event.id,
                to_stage="routing",
                intent_id=parsed_intent if parsed_intent is not None else UNSET,
            )

        if decision_type == "promote_candidate":
            promoted = payload.get("promoted_artifact_id")
            parsed_canonical = (
                uuid.UUID(str(promoted)) if promoted is not None else None
            )
            return await self._apply_lifecycle_after_decision(
                run_id,
                current=current,
                event_id=event.id,
                to_stage="promotion",
                current_canonical=parsed_canonical
                if parsed_canonical is not None
                else UNSET,
            )

        if decision_type == "cancel_run":
            return await self._apply_lifecycle_after_decision(
                run_id,
                current=current,
                event_id=event.id,
                to_status="cancelled",
            )

        raise UnknownDecisionEventError(decision_type)

    async def _require_state(
        self,
        run_id: uuid.UUID,
    ) -> DBOrchestrationLifecycleState:
        row = await self._lifecycle.get_by_run_id(run_id)
        if row is None:
            raise LifecycleStateNotFoundError(run_id)
        return row

    async def _apply_lifecycle_after_decision(
        self,
        run_id: uuid.UUID,
        *,
        current: DBOrchestrationLifecycleState,
        event_id: uuid.UUID,
        to_stage: str | None = None,
        to_status: str | None = None,
        intent_id: uuid.UUID | None | object = UNSET,
        current_canonical: uuid.UUID | None | object = UNSET,
    ) -> DBOrchestrationLifecycleState:
        next_stage = to_stage if to_stage is not None else current.current_stage
        next_status = to_status if to_status is not None else current.status
        self._validate_transition_request(
            current=current,
            next_stage=next_stage,
            next_status=next_status,
            to_stage=to_stage,
            to_status=to_status,
            block=UNSET,
            clear_block=False,
            intent_id=intent_id,
            plan_id=UNSET,
            current_canonical=current_canonical,
        )

        update_kwargs: dict[str, Any] = {
            "intent_id": intent_id,
            "current_canonical": current_canonical,
            "last_event_id": event_id,
        }
        if to_stage is not None:
            update_kwargs["current_stage"] = to_stage
            update_kwargs["stage_entered_at"] = datetime.now(timezone.utc)
        if to_status is not None:
            update_kwargs["status"] = to_status

        return await self._lifecycle.update_state(run_id, **update_kwargs)

    def _validate_decision_allowed(
        self,
        decision_type: str,
        current: DBOrchestrationLifecycleState,
    ) -> None:
        if decision_type == "lock_intent" and current.current_stage != "spec_convergence":
            raise DecisionNotAllowedAtStageError(decision_type, current.current_stage)
        if decision_type == "promote_candidate" and current.current_stage != "audit":
            raise DecisionNotAllowedAtStageError(decision_type, current.current_stage)
        if decision_type == "cancel_run":
            if current.status not in {"active", "paused"}:
                raise InvalidStatusTransitionError(
                    current.status,
                    "cancelled",
                    current.current_stage,
                )
        if decision_type == "approve_remediation" and current.status != "paused":
            raise DecisionNotAllowedAtStageError(decision_type, current.current_stage)

    def _validate_transition_request(
        self,
        *,
        current: DBOrchestrationLifecycleState,
        next_stage: str,
        next_status: str,
        to_stage: str | None,
        to_status: str | None,
        block: dict | None | object,
        clear_block: bool,
        intent_id: object,
        plan_id: object,
        current_canonical: object,
    ) -> None:
        from_stage = current.current_stage
        from_status = current.status

        if next_stage not in self.VALID_STAGES:
            raise InvalidStageTransitionError(from_stage, next_stage)
        if next_status not in self.VALID_STATUSES:
            raise InvalidStatusTransitionError(from_status, next_status, from_stage)

        if next_stage != from_stage:
            if (from_stage, next_stage) not in _LEGAL_STAGE_TRANSITIONS:
                raise InvalidStageTransitionError(from_stage, next_stage)
        else:
            changed = (
                (to_status is not None and next_status != from_status)
                or block is not UNSET
                or clear_block
                or intent_id is not UNSET
                or plan_id is not UNSET
                or current_canonical is not UNSET
            )
            if not changed:
                raise InvalidStageTransitionError(from_stage, next_stage)

        self._validate_status_change(
            from_status=from_status,
            to_status=next_status,
            current_stage=from_stage,
        )

    def _validate_status_change(
        self,
        *,
        from_status: str,
        to_status: str,
        current_stage: str,
    ) -> None:
        if to_status == from_status:
            return

        if to_status == "completed" and current_stage != "publish":
            raise InvalidStatusTransitionError(
                from_status, to_status, current_stage
            )

        if to_status in {"failed", "cancelled"} and from_status not in {
            "active",
            "paused",
        }:
            raise InvalidStatusTransitionError(
                from_status, to_status, current_stage
            )

        terminal = {"completed", "failed", "cancelled"}
        if from_status in terminal and to_status != from_status:
            raise InvalidStatusTransitionError(
                from_status, to_status, current_stage
            )

    @staticmethod
    def _event_type_for_transition(
        *,
        from_stage: str,
        to_stage: str,
        from_status: str,
        to_status: str,
    ) -> str:
        if to_stage != from_stage:
            return "stage_advanced"
        if to_status != from_status:
            return "status_changed"
        return "lifecycle_updated"
