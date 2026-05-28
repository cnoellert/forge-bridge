"""Phase 4B Step 1 schema tests — migrations 0004 + 0005."""

from __future__ import annotations

import os
import socket
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from forge_bridge.store.models import ENTITY_TYPES


_REPO_ROOT = Path(__file__).resolve().parents[1]

_PHASE4B_RELATIONSHIP_NAMES = (
    "content_source",
    "anchored_to",
    "remediated_from",
    "superseded_by",
    "replays_run",
    "remediates_run",
    "amends_run",
    "reference_structural",
    "reference_editorial",
    "reference_identity",
    "reference_motion",
    "reference_depth",
    "reference_compositional_anchor",
    "reference_source_truth_anchor",
)

_ORCH_ENTITY_TYPES = tuple(
    sorted(t for t in ENTITY_TYPES if t.startswith("orch_"))
)


def _postgres_available() -> bool:
    base_url = os.environ.get(
        "FORGE_DB_URL",
        "postgresql+asyncpg://forge:forge@localhost:5432/forge_bridge",
    )
    host = "localhost"
    port = 5432
    if "@" in base_url:
        host_port = base_url.rsplit("@", 1)[-1].split("/", 1)[0]
        if ":" in host_port:
            host, port_str = host_port.rsplit(":", 1)
            port = int(port_str)
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


def _admin_url() -> str:
    base_url = os.environ.get(
        "FORGE_DB_URL",
        "postgresql+asyncpg://forge:forge@localhost:5432/forge_bridge",
    )
    scheme_and_host, _, _ = base_url.rpartition("/")
    return scheme_and_host.replace("+asyncpg", "+psycopg2") + "/postgres"


def _sync_test_db_url(db_name: str) -> str:
    base_url = os.environ.get(
        "FORGE_DB_URL",
        "postgresql+asyncpg://forge:forge@localhost:5432/forge_bridge",
    )
    scheme_and_host, _, _ = base_url.rpartition("/")
    return scheme_and_host.replace("+asyncpg", "+psycopg2") + f"/{db_name}"


def _alembic_config(db_url: str) -> Config:
    cfg = Config(str(_REPO_ROOT / "alembic.ini"))
    cfg.set_main_option(
        "script_location",
        str(_REPO_ROOT / "forge_bridge" / "store" / "migrations"),
    )
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


@pytest.fixture
def alembic_db(monkeypatch):
    """Fresh Postgres database migrated to Alembic head via 0004 + 0005."""
    if not _postgres_available():
        pytest.skip("Postgres at localhost:5432 unreachable — skipping migration test")

    db_name = f"forge_bridge_test_{uuid.uuid4().hex[:8]}"
    admin_engine = create_engine(_admin_url(), isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    admin_engine.dispose()

    db_url = _sync_test_db_url(db_name)
    test_async_url = db_url.replace("+psycopg2", "+asyncpg")
    monkeypatch.setenv("FORGE_DB_URL", test_async_url)

    alembic_cfg = _alembic_config(db_url)
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(db_url)
    session_factory = sessionmaker(bind=engine)

    try:
        yield session_factory, alembic_cfg, engine
    finally:
        engine.dispose()
        admin_engine = create_engine(_admin_url(), isolation_level="AUTOCOMMIT")
        with admin_engine.connect() as conn:
            try:
                conn.execute(
                    text(
                        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                        f"WHERE datname = '{db_name}' AND pid <> pg_backend_pid()"
                    )
                )
            except Exception:
                pass
            conn.execute(text(f'DROP DATABASE "{db_name}"'))
        admin_engine.dispose()


def _insert_entity(
    session,
    *,
    entity_type: str,
    content_hash: str | None,
    entity_id: uuid.UUID | None = None,
) -> uuid.UUID:
    entity_id = entity_id or uuid.uuid4()
    session.execute(
        text(
            """
            INSERT INTO entities (id, entity_type, content_hash, attributes, created_at, updated_at)
            VALUES (:id, :entity_type, :content_hash, '{}'::jsonb, now(), now())
            """
        ),
        {
            "id": str(entity_id),
            "entity_type": entity_type,
            "content_hash": content_hash,
        },
    )
    session.commit()
    return entity_id


def test_phase4b_migrations_roundtrip(alembic_db) -> None:
    """upgrade head → downgrade -1 ×2 → upgrade head lands at same state."""
    session_factory, alembic_cfg, engine = alembic_db

    with session_factory() as session:
        for name in _PHASE4B_RELATIONSHIP_NAMES:
            row = session.execute(
                text(
                    "SELECT name FROM registry_relationship_types WHERE name = :name"
                ),
                {"name": name},
            ).one()
            assert row.name == name

        index_row = session.execute(
            text(
                """
                SELECT indexname FROM pg_indexes
                WHERE tablename = 'entities'
                  AND indexname = 'ix_entities_content_hash_orch'
                """
            )
        ).one()
        assert index_row.indexname == "ix_entities_content_hash_orch"

    command.downgrade(alembic_cfg, "-1")
    command.downgrade(alembic_cfg, "-1")

    with engine.connect() as conn:
        for name in _PHASE4B_RELATIONSHIP_NAMES:
            count = conn.execute(
                text(
                    "SELECT count(*) FROM registry_relationship_types WHERE name = :name"
                ),
                {"name": name},
            ).scalar_one()
            assert count == 0

        columns = {
            row.column_name
            for row in conn.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'entities'
                    """
                )
            )
        }
        assert "content_hash" not in columns

    command.upgrade(alembic_cfg, "head")

    with session_factory() as session:
        for name in _PHASE4B_RELATIONSHIP_NAMES:
            row = session.execute(
                text(
                    "SELECT name FROM registry_relationship_types WHERE name = :name"
                ),
                {"name": name},
            ).one()
            assert row.name == name


def test_content_hash_partial_unique_on_orch_entities(alembic_db) -> None:
    session_factory, _, _ = alembic_db
    shared_hash = "a" * 64

    with session_factory() as session:
        _insert_entity(
            session,
            entity_type="orch_locked_intent",
            content_hash=shared_hash,
        )
        with pytest.raises(IntegrityError):
            _insert_entity(
                session,
                entity_type="orch_locked_intent",
                content_hash=shared_hash,
            )
        session.rollback()

        _insert_entity(session, entity_type="shot", content_hash=shared_hash)
        _insert_entity(session, entity_type="shot", content_hash=shared_hash)


def test_orch_entity_types_accept_content_hash(alembic_db) -> None:
    session_factory, _, _ = alembic_db

    with session_factory() as session:
        for entity_type in _ORCH_ENTITY_TYPES:
            _insert_entity(
                session,
                entity_type=entity_type,
                content_hash=f"{entity_type}-hash",
            )


def test_orch_entity_types_allow_null_content_hash_at_db_layer(alembic_db) -> None:
    session_factory, _, _ = alembic_db

    with session_factory() as session:
        for entity_type in _ORCH_ENTITY_TYPES:
            _insert_entity(session, entity_type=entity_type, content_hash=None)


@pytest.mark.parametrize("name", _PHASE4B_RELATIONSHIP_NAMES)
def test_phase4b_relationship_types_queryable_by_name(alembic_db, name: str) -> None:
    session_factory, _, _ = alembic_db

    with session_factory() as session:
        row = session.execute(
            text(
                """
                SELECT name, protected, directionality
                FROM registry_relationship_types
                WHERE name = :name
                """
            ),
            {"name": name},
        ).one()
        assert row.name == name
        assert row.protected is True
        assert row.directionality == "→"
