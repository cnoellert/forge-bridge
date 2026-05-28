"""Rule snapshot repository."""

from __future__ import annotations

from forge_bridge.store.content_addressed_repo import ContentAddressedRepo
from forge_bridge.store.orch_entity_views import DBOrchRuleSnapshot


class RuleSnapshotRepo(ContentAddressedRepo[DBOrchRuleSnapshot]):
    __entity_type__ = "orch_rule_snapshot"
    __model__ = DBOrchRuleSnapshot
