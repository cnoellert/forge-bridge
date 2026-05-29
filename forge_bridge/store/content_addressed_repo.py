"""Content-addressed repository base for immutable semantic artifacts.

Used by Phase 4B orch_* repositories and by the A.2 assent_record_repo.py
substrate. Subclasses own their model conversion and may layer state-machine
metadata around an immutable content body.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any, ClassVar, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from forge_bridge.store.models import DBEntity

T = TypeVar("T")


class ImmutableArtifactError(Exception):
    """Raised when a caller attempts to mutate a content-addressed artifact."""

    def __init__(self, entity_type: str, operation: str) -> None:
        self.entity_type = entity_type
        self.operation = operation
        super().__init__(
            f"{operation}() is not supported for content-addressed entity_type="
            f"{entity_type!r}. Semantic orch_* artifacts are immutable; use "
            f"insert_if_absent() to persist new content. See "
            f"ContentAddressedRepo docstring and PHASE-4B-ORCHESTRATION-DESIGN.md §3."
        )


class ContentAddressedRepo(Generic[T]):
    """Base class for content-addressed semantic-artifact repositories.

    Discipline:
      - content_hash is computed by the repo over canonical JSON serialization
        of the body (never trusted from the caller).
      - update() is not supported. Content-addressed bodies are immutable by
        repo-layer convention; the DB column is nullable, the discipline lives
        here.
      - insert_if_absent(body) returns the existing row if its hash is already
        present, else inserts and returns the new row. Idempotent by content.

    Repos never call session.commit() — transaction boundaries are owned by
    the caller, matching EntityRepo and StagedOpRepo conventions.
    """

    __entity_type__: ClassVar[str]
    __model__: ClassVar[type[T]]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not getattr(cls, "__entity_type__", None):
            raise TypeError(f"{cls.__name__} must set __entity_type__")
        if not getattr(cls, "__model__", None):
            raise TypeError(f"{cls.__name__} must set __model__")

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _canonical_hash(body: dict[str, Any]) -> str:
        """sha256 over JSON dump with sort_keys=True, separators=(',', ':'),
        ensure_ascii=False. v0.1 canonicalization — documented choice;
        swap-out point if RFC 8785 (JCS) is later needed."""
        canonical = json.dumps(
            body,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @classmethod
    def _default_status(cls, body: dict[str, Any]) -> str:
        if body.get("status") is not None:
            return str(body["status"])
        return "locked"

    async def insert_if_absent(
        self,
        body: dict[str, Any],
        *,
        project_id: uuid.UUID | None = None,
    ) -> T:
        content_hash = self._canonical_hash(body)
        existing = await self.get_by_content_hash(content_hash)
        if existing is not None:
            return existing

        entity = DBEntity(
            id=uuid.uuid4(),
            entity_type=self.__entity_type__,
            project_id=project_id,
            name=body.get("name") or f"{self.__entity_type__}:{content_hash[:12]}",
            status=self._default_status(body),
            content_hash=content_hash,
            attributes=body,
        )
        self.session.add(entity)
        await self.session.flush()
        return self.__model__.from_entity(entity)

    async def get_by_content_hash(self, content_hash: str) -> T | None:
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

    async def get_by_id(self, entity_id: uuid.UUID) -> T | None:
        entity = await self.session.get(DBEntity, entity_id)
        if entity is None or entity.entity_type != self.__entity_type__:
            return None
        return self.__model__.from_entity(entity)

    async def update(self, entity_id: uuid.UUID, body: dict[str, Any]) -> T:
        _ = (entity_id, body)
        raise ImmutableArtifactError(self.__entity_type__, "update")

    async def delete(self, entity_id: uuid.UUID) -> None:
        _ = entity_id
        raise ImmutableArtifactError(self.__entity_type__, "delete")
