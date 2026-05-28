"""LockedIntent repository — first content-addressed orch_* repo (Phase 4B Step 3)."""

from __future__ import annotations

from forge_bridge.store.content_addressed_repo import ContentAddressedRepo
from forge_bridge.store.orch_entity_views import DBOrchLockedIntent


class LockedIntentRepo(ContentAddressedRepo[DBOrchLockedIntent]):
    __entity_type__ = "orch_locked_intent"
    __model__ = DBOrchLockedIntent
