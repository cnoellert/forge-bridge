"""Partial fidelity snapshot repository."""

from __future__ import annotations

from forge_bridge.store.content_addressed_repo import ContentAddressedRepo
from forge_bridge.store.orch_entity_views import DBOrchPartialFidelitySnapshot


class PartialFidelitySnapshotRepo(ContentAddressedRepo[DBOrchPartialFidelitySnapshot]):
    __entity_type__ = "orch_partial_fidelity_snapshot"
    __model__ = DBOrchPartialFidelitySnapshot
