"""#274 — migration 0017 (scheduling foundation) shape.

Static assertions follow the 0009/0014/0016 idiom (import the module, pin the
revision chain, the CHECK tuples and index identities). Because the repo-level
``session_factory`` fixture builds schemas with ``Base.metadata.create_all``
rather than Alembic, the live test below also compares the migrated schema with
the ORM models so the two cannot drift silently. Live tests use the throwaway
``alembic_db`` database from ``tests/test_phase4b_schema.py`` and skip without
Postgres.
"""

from __future__ import annotations

import importlib
import re
import uuid

import pytest
from alembic import command
from forge_contracts.scheduling import KNOWN_SCHEDULING_KINDS
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import text

from forge_bridge.core.scheduling import SCHEDULING_CLASSES
from forge_bridge.store.models import Base, ENTITY_TYPES
from tests.test_phase4b_schema import alembic_db  # noqa: F401  (fixture)


def _migration():
    return importlib.import_module(
        "forge_bridge.store.migrations.versions.0017_scheduling_foundation"
    )


def _quoted_types(check: str) -> list[str]:
    return re.findall(r"'([^']+)'", check)


# --------------------------------------------------------------------------- #
# Static shape
# --------------------------------------------------------------------------- #
def test_migration_0017_revision_chain() -> None:
    migration = _migration()
    assert migration.revision == "0017"
    assert migration.down_revision == "0016"


def test_migration_0017_post_tuple_matches_the_orm_entity_types() -> None:
    migration = _migration()
    assert set(migration._POST_274_ENTITY_TYPES) == set(ENTITY_TYPES)
    assert list(migration._POST_274_ENTITY_TYPES) == sorted(
        migration._POST_274_ENTITY_TYPES
    )


def test_migration_0017_adds_exactly_the_nine_scheduling_kinds() -> None:
    migration = _migration()
    pre = _quoted_types(migration._entity_type_check(migration._PRE_274_ENTITY_TYPES))
    post = _quoted_types(migration._entity_type_check(migration._POST_274_ENTITY_TYPES))

    added = set(post) - set(pre)
    assert added == set(migration.SCHEDULING_ENTITY_TYPES)
    assert added == set(KNOWN_SCHEDULING_KINDS)
    assert added == set(SCHEDULING_CLASSES)
    assert len(post) == len(pre) + 9
    # Every type fits the entities.entity_type String(32) column.
    assert max(len(t) for t in post) <= 32


def test_migration_0017_pre_tuple_is_0016_post_tuple() -> None:
    previous = importlib.import_module(
        "forge_bridge.store.migrations.versions.0016_orch_workflow_record"
    )
    assert set(_migration()._PRE_274_ENTITY_TYPES) == set(
        previous._POST_242_ENTITY_TYPES
    )


def test_migration_0017_index_identities() -> None:
    migration = _migration()
    assert migration.PERSON_EMAIL_INDEX == "uq_entities_person_email_lower"
    assert migration.PERSON_EMAIL_EXPRESSION == "lower(attributes ->> 'email')"
    assert migration.PERSON_EMAIL_PREDICATE == "entity_type = 'person'"
    assert migration.RESOURCE_PERSON_INDEX == "uq_entities_resource_person_id"
    assert migration.RESOURCE_PERSON_EXPRESSION == "(attributes ->> 'person_id')"
    assert migration.RESOURCE_PERSON_PREDICATE == "entity_type = 'resource'"
    assert migration.BOOKING_RESOURCE_INDEXES == {
        "ix_booking_resource_resource_starts": ("resource_id", "starts_at"),
        "ix_booking_resource_project_starts": ("project_id", "starts_at"),
    }
    assert migration.PERSON_USERNAME_INDEX == "ix_person_username_person_id"


def test_migration_0017_index_names_match_the_orm() -> None:
    migration = _migration()
    tables = Base.metadata.tables
    entity_indexes = {i.name for i in tables["entities"].indexes}
    assert {migration.PERSON_EMAIL_INDEX, migration.RESOURCE_PERSON_INDEX} <= entity_indexes
    assert {i.name for i in tables["booking_resource"].indexes} == set(
        migration.BOOKING_RESOURCE_INDEXES
    )
    assert {i.name for i in tables["person_username"].indexes} == {
        migration.PERSON_USERNAME_INDEX
    }


# --------------------------------------------------------------------------- #
# Live (throwaway database)
# --------------------------------------------------------------------------- #
_NEW_TABLES = ("booking_resource", "person_username")


def test_migration_0017_live_schema_matches_the_orm(alembic_db) -> None:  # noqa: F811
    _, _, engine = alembic_db
    inspector = sa_inspect(engine)

    for table in _NEW_TABLES:
        orm = Base.metadata.tables[table]
        live_cols = {c["name"]: c for c in inspector.get_columns(table)}
        assert set(live_cols) == {c.name for c in orm.columns}
        for column in orm.columns:
            assert live_cols[column.name]["nullable"] == column.nullable, column.name
        assert set(inspector.get_pk_constraint(table)["constrained_columns"]) == {
            c.name for c in orm.primary_key.columns
        }
        live_fks = {
            fk["name"]: (fk["referred_table"], fk["options"].get("ondelete"))
            for fk in inspector.get_foreign_keys(table)
        }
        orm_fks = {
            fk.name: (fk.column.table.name, fk.ondelete)
            for fk in orm.foreign_keys
        }
        assert live_fks == orm_fks
        assert {i["name"] for i in inspector.get_indexes(table)} == {
            i.name for i in orm.indexes
        }

    # Only 0017's entities indexes: the ORM's ``index=True`` on project_id
    # (ix_entities_project_id) predates 0017 and was never in a revision.
    migration = _migration()
    live_entity_indexes = {i["name"] for i in inspector.get_indexes("entities")}
    assert {migration.PERSON_EMAIL_INDEX, migration.RESOURCE_PERSON_INDEX} <= (
        live_entity_indexes
    )

    lifecycle = {c["name"]: c for c in inspector.get_columns("projects")}["lifecycle_state"]
    assert lifecycle["nullable"] is False
    assert "active" in str(lifecycle["default"])


def test_migration_0017_live_partial_unique_predicates(alembic_db) -> None:  # noqa: F811
    session_factory, _, _ = alembic_db
    with session_factory() as session:
        rows = dict(
            session.execute(
                text(
                    "SELECT indexname, indexdef FROM pg_indexes "
                    "WHERE indexname IN ('uq_entities_person_email_lower', "
                    "'uq_entities_resource_person_id')"
                )
            ).all()
        )
    email = rows["uq_entities_person_email_lower"]
    assert "UNIQUE" in email and "lower((attributes ->> 'email'::text))" in email
    assert "WHERE ((entity_type)::text = 'person'::text)" in email
    person = rows["uq_entities_resource_person_id"]
    assert "UNIQUE" in person and "(attributes ->> 'person_id'::text)" in person
    assert "WHERE ((entity_type)::text = 'resource'::text)" in person


def test_migration_0017_live_backfills_lifecycle_and_round_trips(alembic_db) -> None:  # noqa: F811
    session_factory, alembic_cfg, engine = alembic_db

    command.downgrade(alembic_cfg, "0016")
    with engine.begin() as conn:
        assert "booking_resource" not in sa_inspect(conn).get_table_names()
        conn.execute(
            text(
                "INSERT INTO projects (id, name, code, attributes) "
                "VALUES (:id, 'pre', 'PRE', '{}'::jsonb)"
            ),
            {"id": str(uuid.uuid4())},
        )

    command.upgrade(alembic_cfg, "head")
    with session_factory() as session:
        assert session.execute(
            text("SELECT lifecycle_state FROM projects WHERE code = 'PRE'")
        ).scalar_one() == "active"


def test_migration_0017_downgrade_refuses_while_scheduling_rows_exist(
    alembic_db,  # noqa: F811
) -> None:
    session_factory, alembic_cfg, _ = alembic_db
    with session_factory() as session:
        session.execute(
            text(
                "INSERT INTO entities (id, entity_type, attributes) "
                "VALUES (:id, 'vendor', '{}'::jsonb)"
            ),
            {"id": str(uuid.uuid4())},
        )
        session.commit()

    with pytest.raises(Exception, match="ck_entities_type"):
        command.downgrade(alembic_cfg, "0016")
