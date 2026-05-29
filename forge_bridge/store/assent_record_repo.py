"""forge-bridge Phase A.2 — AssentRecord repository.

Composes the generic ContentAddressedRepo base for content-hash identity +
idempotent insert + immutability discipline on the graph-intent body, AND
composes EventRepo for atomic audit-event emission on every state transition.

State machine:
    (None)   -> proposed   (via propose())
    proposed -> ratified   (via ratify())
    ratified -> applied    (via mark_applied())
    ratified -> failed     (via mark_failed())
    Terminals: applied, failed. Any other transition raises
    AssentRecordLifecycleError.

Immutability composition:
    The CAR base's update() / delete() remain raising -- the chain_steps body +
    content_hash are immutable post-insert. State-machine transitions update
    DBEntity.status + DBEntity.attributes directly on the same row via
    _transition; chain_steps is never in attribute_updates.

Atomicity guarantee:
    Status update and audit-event append share the same AsyncSession. They
    either both commit or both rollback; callers own transaction boundaries.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from forge_bridge.core.assent import AssentRecord
from forge_bridge.store.content_addressed_repo import ContentAddressedRepo
from forge_bridge.store.models import DBEntity
from forge_bridge.store.repo import EventRepo


class AssentRecordLifecycleError(Exception):
    """Raised when an AssentRecord transition is not permitted."""

    def __init__(
        self,
        from_status: Optional[str],
        to_status: str,
        record_id: uuid.UUID,
        graph_intent_id: Optional[str] = None,
    ):
        self.from_status = from_status
        self.to_status = to_status
        self.record_id = record_id
        self.graph_intent_id = graph_intent_id
        super().__init__(
            f"Illegal transition from {from_status!r} to {to_status!r} "
            f"for assent_record {record_id}"
            + (
                f" (graph_intent_id={graph_intent_id})"
                if graph_intent_id else ""
            )
        )


class AssentRecordNotFound(Exception):
    """Raised when no AssentRecord resolves for a graph_intent_id."""

    def __init__(self, graph_intent_id: str):
        self.graph_intent_id = graph_intent_id
        super().__init__(
            f"AssentRecord not found for graph_intent_id={graph_intent_id!r}"
        )


class AssentRecordRepo(ContentAddressedRepo[AssentRecord]):
    """Persist AssentRecord rows and enforce the ratification state machine."""

    __entity_type__ = "assent_record"
    __model__ = AssentRecord

    _ALLOWED_TRANSITIONS: frozenset[tuple[Optional[str], str]] = frozenset({
        (None, "proposed"),
        ("proposed", "ratified"),
        ("ratified", "applied"),
        ("ratified", "failed"),
    })

    _TRANSITION_EVENTS: dict[tuple[Optional[str], str], str] = {
        (None, "proposed"): "assent.proposed",
        ("proposed", "ratified"): "assent.ratified",
        ("ratified", "applied"): "assent.applied",
        ("ratified", "failed"): "assent.failed",
    }

    _ALLOWED_FAILURE_REASONS = frozenset({
        "drift_invalid",
        "chain_aborted",
        "assent_invalid",
    })

    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self._events = EventRepo(session)

    @classmethod
    def _default_status(cls, body: dict[str, Any]) -> str:
        _ = body
        return "proposed"

    async def propose(
        self,
        chain_steps: list[str],
        project_id: Optional[uuid.UUID] = None,
    ) -> AssentRecord:
        """Create or return the proposed AssentRecord for chain_steps."""
        body = {"chain_steps": list(chain_steps)}
        content_hash = self._canonical_hash(body)
        existing = await self.get_by_content_hash(content_hash)
        if existing is not None:
            return existing

        record = await self.insert_if_absent(body, project_id=project_id)
        db_entity = await self.session.get(DBEntity, record.id)
        if db_entity is None:
            raise AssentRecordNotFound(content_hash[:12])
        db_entity.name = f"assent_record:{content_hash[:12]}"

        await self._append_event(
            record_id=record.id,
            old_status=None,
            new_status="proposed",
            actor="bridge",
            graph_intent_id=content_hash[:12],
            project_id=project_id,
            extra_payload={
                "chain_step_count": len(chain_steps),
                "requires_ratification": True,
            },
        )
        return self._to_assent_record(db_entity)

    async def ratify(
        self,
        graph_intent_id: str,
        actor: str,
    ) -> AssentRecord:
        """Advance proposed -> ratified and record operator assent."""
        decided_at = datetime.now(timezone.utc)
        return await self._transition(
            graph_intent_id=graph_intent_id,
            new_status="ratified",
            actor=actor,
            attribute_updates={
                "decided_by": actor,
                "decided_at": decided_at.isoformat(),
            },
            event_payload={
                "decided_by": actor,
                "decided_at": decided_at.isoformat(),
            },
        )

    async def mark_applied(
        self,
        graph_intent_id: str,
        result: dict[str, Any],
    ) -> AssentRecord:
        """Advance ratified -> applied and record the apply result."""
        applied_at = datetime.now(timezone.utc)
        return await self._transition(
            graph_intent_id=graph_intent_id,
            new_status="applied",
            actor="bridge",
            attribute_updates={
                "applied_at": applied_at.isoformat(),
                "apply_result": result,
            },
            event_payload={
                "applied_at": applied_at.isoformat(),
                "result_summary": result,
            },
        )

    async def mark_failed(
        self,
        graph_intent_id: str,
        reason: str,
        result: Optional[dict[str, Any]] = None,
    ) -> AssentRecord:
        """Advance ratified -> failed and record the failure reason."""
        if reason not in self._ALLOWED_FAILURE_REASONS:
            raise ValueError(f"Unknown assent failure reason: {reason!r}")
        applied_at = datetime.now(timezone.utc)
        updates: dict[str, Any] = {
            "applied_at": applied_at.isoformat(),
            "apply_failure_reason": reason,
        }
        if result is not None:
            updates["apply_result"] = result
        return await self._transition(
            graph_intent_id=graph_intent_id,
            new_status="failed",
            actor="bridge",
            attribute_updates=updates,
            event_payload={
                "applied_at": applied_at.isoformat(),
                "failure_reason": reason,
            },
        )

    async def get_by_graph_intent_id(
        self,
        graph_intent_id: str,
    ) -> Optional[AssentRecord]:
        """Lookup by 12-char graph-intent id prefix."""
        result = await self.session.execute(
            select(DBEntity)
            .where(
                DBEntity.entity_type == self.__entity_type__,
                DBEntity.content_hash.like(f"{graph_intent_id}%"),
            )
            .order_by(DBEntity.created_at.desc())
            .limit(1)
        )
        entity = result.scalar_one_or_none()
        if entity is None:
            return None
        return self._to_assent_record(entity)

    async def list_pending(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AssentRecord], int]:
        """List records optionally filtered by status."""
        filters = [DBEntity.entity_type == self.__entity_type__]
        if status is not None:
            filters.append(DBEntity.status == status)

        total = (
            await self.session.execute(
                select(func.count()).select_from(DBEntity).where(*filters)
            )
        ).scalar_one()
        result = await self.session.execute(
            select(DBEntity)
            .where(*filters)
            .order_by(DBEntity.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [self._to_assent_record(row) for row in result.scalars()], total

    async def _transition(
        self,
        graph_intent_id: str,
        new_status: str,
        actor: str,
        attribute_updates: dict[str, Any],
        event_payload: dict[str, Any],
    ) -> AssentRecord:
        record = await self.get_by_graph_intent_id(graph_intent_id)
        if record is None:
            raise AssentRecordNotFound(graph_intent_id)

        db_entity = await self.session.get(DBEntity, record.id)
        if db_entity is None:
            raise AssentRecordNotFound(graph_intent_id)
        old_status = db_entity.status
        if (old_status, new_status) not in self._ALLOWED_TRANSITIONS:
            raise AssentRecordLifecycleError(
                old_status,
                new_status,
                db_entity.id,
                graph_intent_id,
            )

        db_entity.status = new_status
        attrs = dict(db_entity.attributes or {})
        attrs.update(attribute_updates)
        db_entity.attributes = attrs

        await self._append_event(
            record_id=db_entity.id,
            old_status=old_status,
            new_status=new_status,
            actor=actor,
            graph_intent_id=graph_intent_id,
            project_id=db_entity.project_id,
            extra_payload=event_payload,
        )
        return self._to_assent_record(db_entity)

    async def _append_event(
        self,
        record_id: uuid.UUID,
        old_status: Optional[str],
        new_status: str,
        actor: str,
        graph_intent_id: str,
        project_id: Optional[uuid.UUID],
        extra_payload: dict[str, Any],
    ) -> None:
        event_type = self._TRANSITION_EVENTS[(old_status, new_status)]
        payload = {
            "old_status": old_status,
            "new_status": new_status,
            "actor": actor,
            "operation": "assent_record",
            "transition_at": datetime.now(timezone.utc).isoformat(),
            "graph_intent_id": graph_intent_id,
        }
        payload.update(extra_payload)
        await self._events.append(
            event_type=event_type,
            payload=payload,
            client_name=actor,
            project_id=project_id,
            entity_id=record_id,
        )

    @staticmethod
    def _to_assent_record(db: DBEntity) -> AssentRecord:
        return AssentRecord.from_entity(db)
