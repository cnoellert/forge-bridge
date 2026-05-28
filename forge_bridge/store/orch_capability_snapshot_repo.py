"""Capability snapshot repository."""

from __future__ import annotations

from forge_bridge.store.content_addressed_repo import ContentAddressedRepo
from forge_bridge.store.orch_entity_views import DBOrchCapabilitySnapshot


class CapabilitySnapshotRepo(ContentAddressedRepo[DBOrchCapabilitySnapshot]):
    __entity_type__ = "orch_capability_snapshot"
    __model__ = DBOrchCapabilitySnapshot
