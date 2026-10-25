"""Migration 0018 (plate entity kind) shape.

Static assertions follow the 0016/0017 idiom: import the module, pin the
revision chain and the CHECK tuples. 0018 is a single CHECK-enum add, so
there is no live schema beyond the constraint.
"""

from __future__ import annotations

import importlib
import re

from forge_contracts import DELIVERABLE_TYPE_PLATE

from forge_bridge.store.models import ENTITY_TYPES


def _migration():
    return importlib.import_module(
        "forge_bridge.store.migrations.versions.0018_plate_entity"
    )


def _quoted_types(check: str) -> list[str]:
    return re.findall(r"'([^']+)'", check)


def test_migration_0018_revision_chain() -> None:
    migration = _migration()
    assert migration.revision == "0018"
    assert migration.down_revision == "0017"


def test_migration_0018_post_tuple_matches_the_orm_entity_types() -> None:
    migration = _migration()
    assert set(migration._POST_0018_ENTITY_TYPES) == set(ENTITY_TYPES)
    assert list(migration._POST_0018_ENTITY_TYPES) == sorted(
        migration._POST_0018_ENTITY_TYPES
    )


def test_migration_0018_adds_exactly_plate() -> None:
    migration = _migration()
    pre = _quoted_types(migration._entity_type_check(migration._PRE_0018_ENTITY_TYPES))
    post = _quoted_types(migration._entity_type_check(migration._POST_0018_ENTITY_TYPES))
    assert set(post) - set(pre) == {DELIVERABLE_TYPE_PLATE}
    assert migration.PLATE_ENTITY_TYPE == DELIVERABLE_TYPE_PLATE
    assert len(post) == len(pre) + 1


def test_migration_0018_pre_tuple_is_0017_post_tuple() -> None:
    previous = importlib.import_module(
        "forge_bridge.store.migrations.versions.0017_scheduling_foundation"
    )
    assert set(_migration()._PRE_0018_ENTITY_TYPES) == set(
        previous._POST_274_ENTITY_TYPES
    )
