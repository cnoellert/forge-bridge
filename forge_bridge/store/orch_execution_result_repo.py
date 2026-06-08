"""Execution-result repository for synchronous orchestration steps.

These records are countable completion evidence, not generation artifacts.
They give non-generation families a family-specific home that the execution
partition can union with terminal generation artifacts.
"""

from __future__ import annotations

import copy
import uuid
from typing import Any, ClassVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from forge_bridge.store.models import DBEntity
from forge_bridge.store.orch_entity_views import DBOrchExecutionResult


class ExecutionResultRepo:
    """Persist lightweight execution-step completion records."""

    __entity_type__: ClassVar[str] = "orch_execution_result"
    __model__: ClassVar[type[DBOrchExecutionResult]] = DBOrchExecutionResult
    VALID_DISPOSITIONS: ClassVar[frozenset[str]] = frozenset(
        {"candidate", "diagnostic", "in_flight"}
    )

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def insert_result(
        self,
        *,
        run_id: uuid.UUID,
        step_id: str,
        family: str,
        disposition: str,
        result_payload: dict[str, Any] | None = None,
        result_ref: dict[str, Any] | None = None,
        project_id: uuid.UUID | None = None,
    ) -> DBOrchExecutionResult:
        if disposition not in self.VALID_DISPOSITIONS:
            raise ValueError(
                f"Invalid execution-result disposition {disposition!r}; expected "
                f"one of {sorted(self.VALID_DISPOSITIONS)}"
            )

        attributes: dict[str, Any] = {
            "run_id": str(run_id),
            "step_id": str(step_id),
            "family": str(family),
            "disposition": disposition,
        }
        if result_payload is not None:
            attributes["result_payload"] = copy.deepcopy(result_payload)
        if result_ref is not None:
            attributes["result_ref"] = copy.deepcopy(result_ref)

        entity = DBEntity(
            id=uuid.uuid4(),
            entity_type=self.__entity_type__,
            project_id=project_id,
            name=f"{self.__entity_type__}:{run_id}:{step_id}",
            status=disposition,
            content_hash=None,
            attributes=attributes,
        )
        self.session.add(entity)
        await self.session.flush()
        return self.__model__.from_entity(entity)

    async def list_for_run(
        self,
        run_id: uuid.UUID,
    ) -> list[DBOrchExecutionResult]:
        run_str = str(run_id)
        result = await self.session.execute(
            select(DBEntity)
            .where(DBEntity.entity_type == self.__entity_type__)
            .order_by(DBEntity.created_at.asc())
        )
        rows = []
        for entity in result.scalars().all():
            attrs = entity.attributes if isinstance(entity.attributes, dict) else {}
            if str(attrs.get("run_id")) == run_str:
                rows.append(self.__model__.from_entity(entity))
        return rows
