"""Execution plan repository."""

from __future__ import annotations

from typing import Any

from forge_bridge.store.content_addressed_repo import ContentAddressedRepo
from forge_bridge.store.orch_entity_views import DBOrchExecutionPlan


class ExecutionPlanRepo(ContentAddressedRepo[DBOrchExecutionPlan]):
    __entity_type__ = "orch_execution_plan"
    __model__ = DBOrchExecutionPlan

    @classmethod
    def _default_status(cls, body: dict[str, Any]) -> str:
        if body.get("status") is not None:
            return str(body["status"])
        verdict = body.get("feasibility_verdict")
        if verdict is None:
            raise ValueError("orch_execution_plan body requires feasibility_verdict")
        return str(verdict)
