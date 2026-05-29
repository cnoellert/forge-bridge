from __future__ import annotations

import importlib
import re


def _migration():
    return importlib.import_module(
        "forge_bridge.store.migrations.versions.0009_assent_record"
    )


def _quoted_types(check: str) -> list[str]:
    return re.findall(r"'([^']+)'", check)


def test_migration_0009_revision_chain():
    migration = _migration()

    assert migration.revision == "0009"
    assert migration.down_revision == "0008"


def test_migration_0009_extends_entity_type_check_to_assent_record():
    migration = _migration()

    pre_check = migration._entity_type_check(migration._PRE_A2_ENTITY_TYPES)
    post_check = migration._entity_type_check(migration._POST_A2_ENTITY_TYPES)

    assert len(migration._PRE_A2_ENTITY_TYPES) == 20
    assert len(migration._POST_A2_ENTITY_TYPES) == 21
    assert "assent_record" not in _quoted_types(pre_check)
    assert "assent_record" in _quoted_types(post_check)
    assert len(_quoted_types(pre_check)) == 20
    assert len(_quoted_types(post_check)) == 21
    assert _quoted_types(post_check) == sorted(_quoted_types(post_check))


def test_migration_0009_constraint_string_shape():
    migration = _migration()

    check = migration._entity_type_check(("asset", "assent_record", "layer"))

    assert check == "entity_type IN ('asset', 'assent_record', 'layer')"
