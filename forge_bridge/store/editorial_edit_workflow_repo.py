"""forge-bridge #235 / Phase 149 — durable editorial-edit workflow repository.

The workflow correlation is ONE row in the shared ``entities`` table,
discriminated by ``entity_type='editorial_edit_workflow'``, with every field in
the JSONB ``attributes`` dict and the current lifecycle status promoted to the
``status`` column. It is looked up directly by ``proposal_id`` — never
reconstructed from client data (handoff §6).

Unlike ``AssentRecordRepo`` this row is MUTABLE: propose creates it, then
ratify/apply, replay, and restore patch its attributes in place. It therefore
does NOT compose ``ContentAddressedRepo`` (whose ``update`` is disabled) — it is
a small, explicit repo over ``DBEntity``.

Repos never call ``session.commit()`` — transaction boundaries are owned by the
caller (the EditorialEditWorkflowAPI store adapter opens/commits the session).
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from forge_bridge.store.models import DBEntity


ENTITY_TYPE = "editorial_edit_workflow"


class EditorialEditWorkflowRepo:
    """Persist and mutate the durable editorial-edit workflow correlation row."""

    __entity_type__ = ENTITY_TYPE

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, record: dict[str, Any]) -> dict[str, Any]:
        """Insert a new workflow row. Fails closed if proposal_id already exists.

        The DB partial-unique index on ``attributes ->> 'proposal_id'`` is the
        backstop; this pre-check keeps the error typed for the API layer.
        """
        proposal_id = _require_proposal_id(record)
        existing = await self.get_by_proposal_id(proposal_id)
        if existing is not None:
            raise EditorialEditWorkflowRowExists(proposal_id)
        entity = DBEntity(
            id=uuid.uuid4(),
            entity_type=self.__entity_type__,
            project_id=None,
            name=f"{self.__entity_type__}:{proposal_id}",
            status=str(record.get("status") or "proposed"),
            content_hash=None,
            attributes=dict(record),
        )
        self.session.add(entity)
        await self.session.flush()
        return dict(entity.attributes)

    async def get_by_proposal_id(
        self, proposal_id: str
    ) -> Optional[dict[str, Any]]:
        entity = await self._entity_by_proposal_id(proposal_id)
        return dict(entity.attributes) if entity is not None else None

    async def get_by_preview_authority_fingerprint(
        self, fingerprint: str
    ) -> Optional[dict[str, Any]]:
        result = await self.session.execute(
            select(DBEntity)
            .where(
                DBEntity.entity_type == self.__entity_type__,
                DBEntity.attributes["preview_authority_fingerprint"].astext
                == fingerprint,
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
            raise EditorialEditWorkflowRowNotFound(proposal_id)
        merged = dict(entity.attributes or {})
        merged.update(record)
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
                DBEntity.attributes["proposal_id"].astext == proposal_id,
            )
            .order_by(DBEntity.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


class EditorialEditWorkflowRowExists(Exception):
    def __init__(self, proposal_id: str) -> None:
        self.proposal_id = proposal_id
        super().__init__(
            f"editorial_edit_workflow row already exists for "
            f"proposal_id={proposal_id!r}"
        )


class EditorialEditWorkflowRowNotFound(Exception):
    def __init__(self, proposal_id: str) -> None:
        self.proposal_id = proposal_id
        super().__init__(
            f"editorial_edit_workflow row not found for "
            f"proposal_id={proposal_id!r}"
        )


def _require_proposal_id(record: dict[str, Any]) -> str:
    proposal_id = str(record.get("proposal_id") or "").strip()
    if not proposal_id:
        raise ValueError("editorial_edit_workflow record has no proposal_id")
    return proposal_id
