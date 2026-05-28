"""Validation report repository."""

from __future__ import annotations

from typing import Any

from forge_bridge.store.content_addressed_repo import ContentAddressedRepo
from forge_bridge.store.orch_entity_views import DBOrchValidationReport


class ValidationReportRepo(ContentAddressedRepo[DBOrchValidationReport]):
    __entity_type__ = "orch_validation_report"
    __model__ = DBOrchValidationReport

    @classmethod
    def _default_status(cls, body: dict[str, Any]) -> str:
        if body.get("status") is not None:
            return str(body["status"])
        verdict = body.get("verdict")
        if verdict is None:
            raise ValueError("orch_validation_report body requires verdict")
        return str(verdict)
