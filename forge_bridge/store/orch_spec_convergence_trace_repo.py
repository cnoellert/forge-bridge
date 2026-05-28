"""Spec convergence trace repository."""

from __future__ import annotations

from typing import Any

from forge_bridge.store.content_addressed_repo import ContentAddressedRepo
from forge_bridge.store.orch_entity_views import DBOrchSpecConvergenceTrace


class SpecConvergenceTraceRepo(ContentAddressedRepo[DBOrchSpecConvergenceTrace]):
    __entity_type__ = "orch_spec_convergence_trace"
    __model__ = DBOrchSpecConvergenceTrace

    @classmethod
    def _default_status(cls, body: dict[str, Any]) -> str:
        if body.get("status") is not None:
            return str(body["status"])
        return "locked" if body.get("lock_event") is not None else "open"
