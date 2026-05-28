"""Audit report repository."""

from __future__ import annotations

from typing import Any

from forge_bridge.store.content_addressed_repo import ContentAddressedRepo
from forge_bridge.store.orch_entity_views import DBOrchAuditReport


class AuditReportRepo(ContentAddressedRepo[DBOrchAuditReport]):
    __entity_type__ = "orch_audit_report"
    __model__ = DBOrchAuditReport

    @classmethod
    def _default_status(cls, body: dict[str, Any]) -> str:
        if body.get("status") is not None:
            return str(body["status"])
        summary = body.get("cross_criterion_summary") or {}
        verdict = summary.get("overall_verdict") if isinstance(summary, dict) else None
        if verdict is None:
            raise ValueError(
                "orch_audit_report body requires cross_criterion_summary.overall_verdict"
            )
        return str(verdict)
