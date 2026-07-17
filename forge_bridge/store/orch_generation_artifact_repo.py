"""Generation artifact repository — hybrid lifecycle carve-out (Phase 4B §6).

orch_generation_artifact does NOT inherit ContentAddressedRepo. During
lifecycle, lifecycle_state (status column) and polling_history mutate; once
terminal, content_hash is sealed and the row becomes immutable.

See PHASE-4B-ORCHESTRATION-DESIGN.md §6 worker contract.
"""

from __future__ import annotations

import copy
import uuid
from typing import Any, ClassVar

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from forge_bridge.store.content_addressed_repo import (
    ContentAddressedRepo,
    ImmutableArtifactError,
)
from forge_bridge.store.models import DBEntity
from forge_bridge.store.orch_entity_views import DBOrchGenerationArtifact


class InvalidTransitionError(Exception):
    """Raised when a lifecycle transition target is not permitted."""

    def __init__(
        self,
        artifact_id: uuid.UUID,
        from_state: str | None,
        to_state: str,
    ) -> None:
        self.artifact_id = artifact_id
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(
            f"Invalid lifecycle transition for orch_generation_artifact "
            f"{artifact_id}: {from_state!r} -> {to_state!r}"
        )


class GenerationArtifactRepo:
    """Hybrid repo: mutable during lifecycle, content-addressed at terminal."""

    __entity_type__: ClassVar[str] = "orch_generation_artifact"
    __model__: ClassVar[type[DBOrchGenerationArtifact]] = DBOrchGenerationArtifact

    TERMINAL_STATES: ClassVar[frozenset[str]] = frozenset(
        {"complete", "partial", "failed", "cancelled"}
    )
    NON_TERMINAL_STATES: ClassVar[frozenset[str]] = frozenset({"submitted", "polling"})
    ALL_STATES: ClassVar[frozenset[str]] = TERMINAL_STATES | NON_TERMINAL_STATES

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def insert_submitted(
        self,
        body: dict[str, Any],
        *,
        project_id: uuid.UUID | None = None,
    ) -> DBOrchGenerationArtifact:
        """Create row with lifecycle_state='submitted', content_hash NULL."""
        attributes = copy.deepcopy(body)
        attributes.pop("lifecycle_state", None)
        attributes.setdefault("polling_history", [])

        entity = DBEntity(
            id=uuid.uuid4(),
            entity_type=self.__entity_type__,
            project_id=project_id,
            name=attributes.get("name")
            or f"{self.__entity_type__}:submitted:{uuid.uuid4().hex[:8]}",
            status="submitted",
            content_hash=None,
            attributes=attributes,
        )
        self.session.add(entity)
        await self.session.flush()
        return self.__model__.from_entity(entity)

    async def transition(
        self,
        artifact_id: uuid.UUID,
        new_state: str,
        polling_event: dict[str, Any] | None = None,
        terminal_provenance: dict[str, Any] | None = None,
        partial_fidelity_report: dict[str, Any] | None = None,
    ) -> DBOrchGenerationArtifact:
        """Advance lifecycle_state; seal content_hash on terminal transition."""
        if new_state not in self.ALL_STATES:
            raise InvalidTransitionError(artifact_id, None, new_state)

        entity = await self.session.get(DBEntity, artifact_id)
        if entity is None or entity.entity_type != self.__entity_type__:
            raise InvalidTransitionError(artifact_id, None, new_state)

        current_state = entity.status
        if current_state in self.TERMINAL_STATES:
            raise ImmutableArtifactError(self.__entity_type__, "transition")

        if new_state not in self.ALL_STATES:
            raise InvalidTransitionError(artifact_id, current_state, new_state)

        attributes = copy.deepcopy(entity.attributes)
        if polling_event is not None:
            history = attributes.get("polling_history")
            if not isinstance(history, list):
                history = []
            history = list(history)
            history.append(polling_event)
            attributes["polling_history"] = history

        if terminal_provenance is not None:
            existing_provenance = attributes.get("execution_provenance")
            if isinstance(existing_provenance, dict):
                merged = copy.deepcopy(existing_provenance)
                merged.update(terminal_provenance)
                attributes["execution_provenance"] = merged
            else:
                attributes["execution_provenance"] = copy.deepcopy(terminal_provenance)

        if partial_fidelity_report is not None:
            attributes["partial_fidelity_report"] = copy.deepcopy(
                partial_fidelity_report
            )

        attributes.pop("lifecycle_state", None)
        entity.attributes = attributes
        entity.status = new_state

        if new_state in self.TERMINAL_STATES:
            entity.content_hash = ContentAddressedRepo._canonical_hash(attributes)

        await self.session.flush()
        return self.__model__.from_entity(entity)

    async def get_by_id(self, artifact_id: uuid.UUID) -> DBOrchGenerationArtifact | None:
        entity = await self.session.get(DBEntity, artifact_id)
        if entity is None or entity.entity_type != self.__entity_type__:
            return None
        return self.__model__.from_entity(entity)

    async def get_by_content_hash(
        self,
        content_hash: str,
    ) -> DBOrchGenerationArtifact | None:
        """Return terminal artifact by hash; non-terminal rows have NULL hash."""
        result = await self.session.execute(
            select(DBEntity).where(
                DBEntity.entity_type == self.__entity_type__,
                DBEntity.content_hash == content_hash,
            )
        )
        entity = result.scalar_one_or_none()
        if entity is None:
            return None
        return self.__model__.from_entity(entity)

    async def lock_idempotency_key(self, idempotency_key: str) -> None:
        """Serialize one generation key for this transaction.

        The lock must be acquired before lookup and held through submit plus
        artifact insert. PostgreSQL releases it automatically on transaction
        end, including refusal and exception paths.
        """
        await self.session.execute(
            text(
                "SELECT pg_advisory_xact_lock("
                "hashtextextended('forge-generation:' || :key, 0))"
            ),
            {"key": idempotency_key},
        )

    async def get_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> DBOrchGenerationArtifact | None:
        result = await self.session.execute(
            select(DBEntity).where(
                DBEntity.entity_type == self.__entity_type__,
                DBEntity.attributes.contains({
                    "idempotency_key": idempotency_key,
                }),
            )
        )
        entity = result.scalar_one_or_none()
        if entity is None:
            return None
        return self.__model__.from_entity(entity)

    async def find_non_terminal(self) -> list[DBOrchGenerationArtifact]:
        result = await self.session.execute(
            select(DBEntity)
            .where(
                DBEntity.entity_type == self.__entity_type__,
                DBEntity.status.in_(tuple(self.NON_TERMINAL_STATES)),
            )
            .order_by(DBEntity.created_at.asc())
        )
        return [self.__model__.from_entity(row) for row in result.scalars().all()]
