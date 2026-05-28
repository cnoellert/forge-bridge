"""Provenance manifest repository."""

from __future__ import annotations

from forge_bridge.store.content_addressed_repo import ContentAddressedRepo
from forge_bridge.store.orch_entity_views import DBOrchProvenanceManifest


class ProvenanceManifestRepo(ContentAddressedRepo[DBOrchProvenanceManifest]):
    __entity_type__ = "orch_provenance_manifest"
    __model__ = DBOrchProvenanceManifest
