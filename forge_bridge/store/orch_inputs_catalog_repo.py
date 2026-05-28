"""Inputs catalog repository."""

from __future__ import annotations

from forge_bridge.store.content_addressed_repo import ContentAddressedRepo
from forge_bridge.store.orch_entity_views import DBOrchInputsCatalog


class InputsCatalogRepo(ContentAddressedRepo[DBOrchInputsCatalog]):
    __entity_type__ = "orch_inputs_catalog"
    __model__ = DBOrchInputsCatalog
