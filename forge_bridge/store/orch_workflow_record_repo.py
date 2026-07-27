"""forge-bridge #242 — generic durable product-workflow record repository.

ONE row in the shared ``entities`` table, discriminated by
``entity_type='orch_workflow_record'``, with a ``kind`` discriminator inside
the JSONB ``attributes`` dict so several workflow families share the row family
without another migration. Every field lives in ``attributes``; the current
lifecycle status is promoted to the ``status`` column. It is looked up directly
by ``(kind, proposal_id)`` — never reconstructed from client data.

This is the same shape as ``EditorialEditWorkflowRepo`` (#235) minus that repo's
single-workflow assumption. #235's shipped repo and its ``0015`` migration are
deliberately left alone: they carry live rows and need no data migration.

Like #235's row, this one is MUTABLE — propose creates it, then ratify/apply,
replay, and the recovery rail patch its attributes in place. It therefore does
NOT compose ``ContentAddressedRepo`` (whose ``update`` is disabled).

Repos never call ``session.commit()`` — transaction boundaries are owned by the
caller (the workflow API's store adapter opens/commits the session).
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from forge_bridge.store.models import DBEntity


ENTITY_TYPE = "orch_workflow_record"


class OrchWorkflowRecordRepo:
    """Persist and mutate one durable workflow correlation row of one kind."""

    __entity_type__ = ENTITY_TYPE

    def __init__(
        self,
        session: AsyncSession,
        *,
        kind: str,
        authority_field: str = "authority_fingerprint",
    ) -> None:
        if not str(kind).strip():
            raise ValueError("orch_workflow_record repo requires a kind")
        self.session = session
        self.kind = str(kind)
        # The ONE upstream authority fingerprint this workflow family binds
        # exclusively, so a second proposal cannot rebind it.
        self.authority_field = authority_field

    async def create(self, record: dict[str, Any]) -> dict[str, Any]:
        """Insert a new workflow row. Fails closed if proposal_id already exists.

        The DB partial-unique index on ``(kind, proposal_id)`` is the backstop;
        this pre-check keeps the error typed for the API layer.
        """
        proposal_id = _require_proposal_id(record)
        existing = await self.get_by_proposal_id(proposal_id)
        if existing is not None:
            raise OrchWorkflowRecordExists(self.kind, proposal_id)
        attributes = dict(record)
        attributes["kind"] = self.kind
        entity = DBEntity(
            id=uuid.uuid4(),
            entity_type=self.__entity_type__,
            project_id=None,
            name=f"{self.kind}:{proposal_id}",
            status=str(record.get("status") or "proposed"),
            content_hash=None,
            attributes=attributes,
        )
        self.session.add(entity)
        await self.session.flush()
        return dict(entity.attributes)

    async def get_by_proposal_id(
        self, proposal_id: str
    ) -> Optional[dict[str, Any]]:
        entity = await self._entity_by_proposal_id(proposal_id)
        return dict(entity.attributes) if entity is not None else None

    async def get_by_authority_fingerprint(
        self, fingerprint: str
    ) -> Optional[dict[str, Any]]:
        result = await self.session.execute(
            select(DBEntity)
            .where(
                DBEntity.entity_type == self.__entity_type__,
                DBEntity.attributes["kind"].astext == self.kind,
                DBEntity.attributes[self.authority_field].astext == fingerprint,
            )
            .order_by(DBEntity.created_at.desc())
            .limit(1)
        )
        entity = result.scalar_one_or_none()
        return dict(entity.attributes) if entity is not None else None

    async def update(
        self, proposal_id: str, record: dict[str, Any]
    ) -> dict[str, Any]:
        """Replace the stored workflow attributes and status in place."""
        entity = await self._entity_by_proposal_id(proposal_id)
        if entity is None:
            raise OrchWorkflowRecordNotFound(self.kind, proposal_id)
        merged = dict(entity.attributes or {})
        merged.update(record)
        # The discriminator is repo-owned; a patch never re-homes the row.
        merged["kind"] = self.kind
        entity.attributes = merged
        entity.status = str(merged.get("status") or entity.status)
        await self.session.flush()
        return dict(entity.attributes)

    async def _entity_by_proposal_id(
        self, proposal_id: str
    ) -> Optional[DBEntity]:
        result = await self.session.execute(
            select(DBEntity)
            .where(
                DBEntity.entity_type == self.__entity_type__,
                DBEntity.attributes["kind"].astext == self.kind,
                DBEntity.attributes["proposal_id"].astext == proposal_id,
            )
            .order_by(DBEntity.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


class OrchWorkflowRecordExists(Exception):
    def __init__(self, kind: str, proposal_id: str) -> None:
        self.kind = kind
        self.proposal_id = proposal_id
        super().__init__(
            f"orch_workflow_record row already exists for kind={kind!r} "
            f"proposal_id={proposal_id!r}"
        )


class OrchWorkflowRecordNotFound(Exception):
    def __init__(self, kind: str, proposal_id: str) -> None:
        self.kind = kind
        self.proposal_id = proposal_id
        super().__init__(
            f"orch_workflow_record row not found for kind={kind!r} "
            f"proposal_id={proposal_id!r}"
        )


def _require_proposal_id(record: dict[str, Any]) -> str:
    proposal_id = str(record.get("proposal_id") or "").strip()
    if not proposal_id:
        raise ValueError("orch_workflow_record record has no proposal_id")
    return proposal_id


__all__ = [
    "ENTITY_TYPE",
    "OrchWorkflowRecordExists",
    "OrchWorkflowRecordNotFound",
    "OrchWorkflowRecordRepo",
]
