from __future__ import annotations

import importlib


def _migration():
    return importlib.import_module(
        "forge_bridge.store.migrations.versions.0014_generation_idempotency"
    )


def test_migration_0014_revision_chain_and_scope() -> None:
    migration = _migration()

    assert migration.revision == "0014"
    assert migration.down_revision == "0013"
    assert migration.INDEX_NAME == "uq_entities_generation_idempotency_key"
    assert migration.INDEX_EXPRESSION == "(attributes ->> 'idempotency_key')"
    assert migration.INDEX_PREDICATE == (
        "entity_type = 'orch_generation_artifact' "
        "AND attributes ? 'idempotency_key'"
    )
