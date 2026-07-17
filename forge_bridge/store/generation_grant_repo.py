"""GenerationGrant repository — the generation spend-gate (#146).

Composes the generic ContentAddressedRepo base for content-hash identity +
idempotent insert + immutability discipline on the terms body, AND composes
EventRepo for atomic audit-event emission on every state transition. This is
the AssentRecordRepo *lineage* (immutable-terms + mutable state-machine),
copied deliberately — a grant that transitions state (and later carries #142's
budget decrement) cannot live on the raise-on-update PipelineRunRepo.

State machine:
    (None)   -> proposed   (via propose())
    proposed -> ratified   (via ratify() — pure state transition, no apply/replay)
    ratified -> consumed   (via consume_atomic() — the CAS spend-flip)
    proposed -> revoked | proposed -> failed
    ratified -> revoked | ratified -> failed
    Terminals: consumed, revoked, failed.

CONSUME IS ATOMIC (load-bearing correctness):
    ``consume_atomic`` is a single conditional SQL UPDATE
    ``... WHERE status='ratified' RETURNING`` — NOT the base ``_transition``
    read-check-write. Under session-per-request two concurrent submits would
    both pass a read-check and double-spend. The DB-level conditional flip
    guarantees exactly one submit consumes the grant; the loser gets a refusal.
    That is single-grant replay defense; #141 separately deduplicates retries
    carrying different grants through the generation idempotency ledger.

Immutability composition:
    The CAR base's update() / delete() remain raising — the terms body +
    content_hash are immutable post-insert. State transitions update
    DBEntity.status + DBEntity.attributes in place; the terms body keys
    (operator_id, backend_identity_triple, estimated_cost, nonce, run_kind) are
    never in attribute_updates.

Atomicity guarantee:
    Status update and audit-event append share the same AsyncSession. They
    either both commit or both rollback; callers own transaction boundaries.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import cast, func, literal, select, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from forge_bridge.core.generation_grant import GenerationGrant
from forge_bridge.store.content_addressed_repo import ContentAddressedRepo
from forge_bridge.store.models import DBEntity
from forge_bridge.store.repo import EventRepo


class GenerationGrantLifecycleError(Exception):
    """Raised when a GenerationGrant transition is not permitted."""

    def __init__(
        self,
        from_status: Optional[str],
        to_status: str,
        record_id: uuid.UUID,
        grant_id: Optional[str] = None,
    ):
        self.from_status = from_status
        self.to_status = to_status
        self.record_id = record_id
        self.grant_id = grant_id
        super().__init__(
            f"Illegal transition from {from_status!r} to {to_status!r} "
            f"for generation_grant {record_id}"
            + (f" (grant_id={grant_id})" if grant_id else "")
        )


class GenerationGrantNotFound(Exception):
    """Raised when no GenerationGrant resolves for a grant_id."""

    def __init__(self, grant_id: str):
        self.grant_id = grant_id
        super().__init__(f"GenerationGrant not found for grant_id={grant_id!r}")


class GenerationGrantRepo(ContentAddressedRepo[GenerationGrant]):
    """Persist GenerationGrant rows and enforce the spend state machine.

    The SOLE sanctioned write path for generation_grant rows. Direct
    ``session.add(DBEntity(entity_type='generation_grant', ...))`` is prohibited
    (mirror of assent.py:40) — it bypasses audit emission, content-hash
    idempotency, and the atomic CAS consume that prevents double-spend.
    """

    __entity_type__ = "generation_grant"
    __model__ = GenerationGrant

    _ALLOWED_TRANSITIONS: frozenset[tuple[Optional[str], str]] = frozenset({
        (None, "proposed"),
        ("proposed", "ratified"),
        ("proposed", "revoked"),
        ("proposed", "failed"),
        ("ratified", "revoked"),
        ("ratified", "failed"),
        # ("ratified", "consumed") is deliberately absent here — consume is the
        # atomic CAS path (consume_atomic), never the read-check-write _transition.
    })

    _TRANSITION_EVENTS: dict[tuple[Optional[str], str], str] = {
        (None, "proposed"): "generation_grant.proposed",
        ("proposed", "ratified"): "generation_grant.ratified",
        ("proposed", "revoked"): "generation_grant.revoked",
        ("proposed", "failed"): "generation_grant.failed",
        ("ratified", "revoked"): "generation_grant.revoked",
        ("ratified", "failed"): "generation_grant.failed",
    }

    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self._events = EventRepo(session)

    @classmethod
    def _default_status(cls, body: dict[str, Any]) -> str:
        _ = body
        return "proposed"

    async def propose(
        self,
        *,
        operator_id: str,
        backend_identity_triple: dict[str, Any],
        estimated_cost: dict[str, Any],
        run_kind: str,
        nonce: Optional[str] = None,
        project_id: Optional[uuid.UUID] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> GenerationGrant:
        """Mint a proposed grant. A free quote — reversible, no spend.

        ``nonce`` defaults to a fresh uuid so every mint is content-unique;
        two identical-cost quotes therefore never collapse onto one row (and
        can never resurrect a revoked/consumed grant).
        """
        body: dict[str, Any] = {
            "operator_id": operator_id,
            "backend_identity_triple": dict(backend_identity_triple),
            "estimated_cost": dict(estimated_cost),
            "run_kind": run_kind,
            "nonce": nonce or uuid.uuid4().hex,
        }
        if metadata is not None:
            body["metadata"] = dict(metadata)
        content_hash = self._canonical_hash(body)
        existing = await self.get_by_content_hash(content_hash)
        if existing is not None:
            return existing

        record = await self.insert_if_absent(body, project_id=project_id)
        db_entity = await self.session.get(DBEntity, record.id)
        if db_entity is None:
            raise GenerationGrantNotFound(content_hash[:12])
        db_entity.name = f"generation_grant:{content_hash[:12]}"

        await self._append_event(
            record_id=record.id,
            old_status=None,
            new_status="proposed",
            actor="bridge",
            grant_id=content_hash[:12],
            project_id=project_id,
            extra_payload={
                "estimated_cost": dict(estimated_cost),
                "run_kind": run_kind,
                "requires_ratification": True,
            },
        )
        return GenerationGrant.from_entity(db_entity)

    async def ratify(self, grant_id: str, actor: str) -> GenerationGrant:
        """Advance proposed -> ratified and record operator assent.

        A pure proposed->ratified state transition. There is NOTHING to apply
        or replay (unlike AssentRecordRepo.mark_applied) — the *runs* spend, the
        grant only authorizes.
        """
        decided_at = datetime.now(timezone.utc)
        return await self._transition(
            grant_id=grant_id,
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

    async def revoke(self, grant_id: str, actor: str = "operator") -> GenerationGrant:
        """Advance proposed|ratified -> revoked."""
        return await self._transition(
            grant_id=grant_id,
            new_status="revoked",
            actor=actor,
            attribute_updates={"failure_reason": "revoked"},
            event_payload={"actor": actor},
        )

    async def consume_atomic(self, grant_id: str) -> Optional[GenerationGrant]:
        """Atomically consume a ratified grant (the spend-flip).

        Single conditional UPDATE ``WHERE status='ratified' RETURNING`` — the
        DB guarantees exactly one caller wins the ratified->consumed flip. On
        success returns the consumed grant; on refusal (grant absent, not
        ratified, or already consumed) returns ``None``. Callers own the
        transaction boundary.
        """
        consumed_at = datetime.now(timezone.utc)
        patch = json.dumps({
            "status": "consumed",
            "consumed_at": consumed_at.isoformat(),
        })
        stmt = (
            update(DBEntity)
            .where(
                DBEntity.entity_type == self.__entity_type__,
                DBEntity.content_hash.like(f"{grant_id}%"),
                DBEntity.status == "ratified",
            )
            .values(
                status="consumed",
                attributes=DBEntity.attributes.op("||")(cast(literal(patch), JSONB)),
            )
            .returning(DBEntity.id)
        )
        result = await self.session.execute(stmt)
        row_id = result.scalar_one_or_none()
        if row_id is None:
            return None

        await self._append_event(
            record_id=row_id,
            old_status="ratified",
            new_status="consumed",
            actor="bridge",
            grant_id=grant_id,
            project_id=None,
            extra_payload={"consumed_at": consumed_at.isoformat()},
        )
        # Fresh read: this session never loaded the row before the core UPDATE,
        # so get() queries and returns the post-flip state.
        db_entity = await self.session.get(DBEntity, row_id)
        return GenerationGrant.from_entity(db_entity)

    async def get_by_grant_id(self, grant_id: str) -> Optional[GenerationGrant]:
        """Lookup by 12-char grant_id prefix (content_hash prefix)."""
        result = await self.session.execute(
            select(DBEntity)
            .where(
                DBEntity.entity_type == self.__entity_type__,
                DBEntity.content_hash.like(f"{grant_id}%"),
            )
            .order_by(DBEntity.created_at.desc())
            .limit(1)
        )
        entity = result.scalar_one_or_none()
        if entity is None:
            return None
        return GenerationGrant.from_entity(entity)

    async def list_grants(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[GenerationGrant], int]:
        """List grants optionally filtered by status."""
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
        return [GenerationGrant.from_entity(r) for r in result.scalars()], total

    async def _transition(
        self,
        grant_id: str,
        new_status: str,
        actor: str,
        attribute_updates: dict[str, Any],
        event_payload: dict[str, Any],
    ) -> GenerationGrant:
        grant = await self.get_by_grant_id(grant_id)
        if grant is None:
            raise GenerationGrantNotFound(grant_id)

        db_entity = await self.session.get(DBEntity, grant.id)
        if db_entity is None:
            raise GenerationGrantNotFound(grant_id)
        old_status = db_entity.status
        if (old_status, new_status) not in self._ALLOWED_TRANSITIONS:
            raise GenerationGrantLifecycleError(
                old_status, new_status, db_entity.id, grant_id,
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
            grant_id=grant_id,
            project_id=db_entity.project_id,
            extra_payload=event_payload,
        )
        return GenerationGrant.from_entity(db_entity)

    async def _append_event(
        self,
        record_id: uuid.UUID,
        old_status: Optional[str],
        new_status: str,
        actor: str,
        grant_id: str,
        project_id: Optional[uuid.UUID],
        extra_payload: dict[str, Any],
    ) -> None:
        event_type = self._TRANSITION_EVENTS.get(
            (old_status, new_status), "generation_grant.consumed",
        )
        payload = {
            "old_status": old_status,
            "new_status": new_status,
            "actor": actor,
            "operation": "generation_grant",
            "transition_at": datetime.now(timezone.utc).isoformat(),
            "grant_id": grant_id,
        }
        payload.update(extra_payload)
        await self._events.append(
            event_type=event_type,
            payload=payload,
            client_name=actor,
            project_id=project_id,
            entity_id=record_id,
        )


__all__ = [
    "GenerationGrantRepo",
    "GenerationGrantLifecycleError",
    "GenerationGrantNotFound",
]
