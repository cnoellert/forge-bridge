"""Pipeline run repository."""

from __future__ import annotations

from typing import Any

from forge_bridge.store.content_addressed_repo import ContentAddressedRepo
from forge_bridge.store.orch_entity_views import DBOrchPipelineRun


class PipelineRunRepo(ContentAddressedRepo[DBOrchPipelineRun]):
    __entity_type__ = "orch_pipeline_run"
    __model__ = DBOrchPipelineRun

    @classmethod
    def _default_status(cls, body: dict[str, Any]) -> str:
        if body.get("status") is not None:
            return str(body["status"])
        return "active"
