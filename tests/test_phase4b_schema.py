"""Phase 4B schema tests — migrations 0004 through 0008."""

from __future__ import annotations

import json
import os
import socket
import uuid
from datetime import datetime, timedelta, timezone
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
    """Fresh Postgres database migrated to Alembic head (0004–0008)."""
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
    """upgrade head → downgrade -3 → -1 → -1 → upgrade head lands at same state."""
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

        lifecycle_table = session.execute(
            text(
                """
                SELECT tablename FROM pg_tables
                WHERE tablename = 'orchestration_lifecycle_state'
                """
            )
        ).one()
        assert lifecycle_table.tablename == "orchestration_lifecycle_state"

    command.downgrade(alembic_cfg, "-3")
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

        operational_tables = conn.execute(
            text(
                """
                SELECT tablename FROM pg_tables
                WHERE tablename IN (
                    'orchestration_lifecycle_state',
                    'orchestration_promotion_ledger',
                    'orchestration_compromise_ledger'
                )
                """
            )
        ).all()
        assert operational_tables == []

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

        lifecycle_table = session.execute(
            text(
                """
                SELECT tablename FROM pg_tables
                WHERE tablename = 'orchestration_lifecycle_state'
                """
            )
        ).one()
        assert lifecycle_table.tablename == "orchestration_lifecycle_state"


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


def _insert_pipeline_run(session, run_id: uuid.UUID | None = None) -> uuid.UUID:
    run_id = run_id or uuid.uuid4()
    _insert_entity(
        session,
        entity_type="orch_pipeline_run",
        content_hash=f"run-{run_id.hex}",
        entity_id=run_id,
    )
    return run_id


def _insert_lifecycle_state(
    session,
    *,
    run_id: uuid.UUID,
    shot_id: uuid.UUID,
    current_stage: str = "ingest",
    status: str = "active",
    block: dict | None = None,
    stage_entered_at: datetime | None = None,
) -> None:
    session.execute(
        text(
            """
            INSERT INTO orchestration_lifecycle_state (
                run_id, shot_id, current_stage, stage_entered_at,
                status, block, created_at, updated_at
            )
            VALUES (
                :run_id, :shot_id, :current_stage, :stage_entered_at,
                :status, CAST(:block AS jsonb), now(), now()
            )
            """
        ),
        {
            "run_id": str(run_id),
            "shot_id": str(shot_id),
            "current_stage": current_stage,
            "stage_entered_at": stage_entered_at or datetime.now(timezone.utc),
            "status": status,
            "block": json.dumps(block) if block is not None else None,
        },
    )
    session.commit()


def test_orchestration_lifecycle_state_insert_roundtrip(alembic_db) -> None:
    session_factory, _, _ = alembic_db
    run_id = uuid.uuid4()
    shot_id = uuid.uuid4()

    with session_factory() as session:
        _insert_pipeline_run(session, run_id)
        _insert_lifecycle_state(session, run_id=run_id, shot_id=shot_id)

        row = session.execute(
            text(
                """
                SELECT run_id, shot_id, current_stage, status
                FROM orchestration_lifecycle_state
                WHERE run_id = :run_id
                """
            ),
            {"run_id": str(run_id)},
        ).one()
        assert row.run_id == run_id
        assert row.shot_id == shot_id
        assert row.current_stage == "ingest"
        assert row.status == "active"


def test_orchestration_lifecycle_state_rejects_invalid_stage(alembic_db) -> None:
    session_factory, _, _ = alembic_db

    with session_factory() as session:
        run_id = _insert_pipeline_run(session)
        with pytest.raises(IntegrityError):
            _insert_lifecycle_state(
                session,
                run_id=run_id,
                shot_id=uuid.uuid4(),
                current_stage="invalid_stage",
            )
        session.rollback()


def test_orchestration_lifecycle_state_rejects_invalid_status(alembic_db) -> None:
    session_factory, _, _ = alembic_db

    with session_factory() as session:
        run_id = _insert_pipeline_run(session)
        with pytest.raises(IntegrityError):
            _insert_lifecycle_state(
                session,
                run_id=run_id,
                shot_id=uuid.uuid4(),
                status="invalid_status",
            )
        session.rollback()


def test_orchestration_lifecycle_state_paused_has_block(alembic_db) -> None:
    session_factory, _, _ = alembic_db

    with session_factory() as session:
        shot_id = uuid.uuid4()

        run_id = _insert_pipeline_run(session)
        with pytest.raises(IntegrityError):
            _insert_lifecycle_state(
                session,
                run_id=run_id,
                shot_id=shot_id,
                status="paused",
                block=None,
            )
        session.rollback()

        run_id_2 = _insert_pipeline_run(session)
        with pytest.raises(IntegrityError):
            _insert_lifecycle_state(
                session,
                run_id=run_id_2,
                shot_id=shot_id,
                status="active",
                block={"reason": "should-not-be-set"},
            )
        session.rollback()

        run_id_3 = _insert_pipeline_run(session)
        _insert_lifecycle_state(
            session,
            run_id=run_id_3,
            shot_id=shot_id,
            status="paused",
            block={"kind": "awaiting_input"},
        )


def test_orchestration_lifecycle_state_active_partial_index_allows_duplicates(
    alembic_db,
) -> None:
    session_factory, _, _ = alembic_db
    shot_id = uuid.uuid4()

    with session_factory() as session:
        run_a = _insert_pipeline_run(session)
        run_b = _insert_pipeline_run(session)
        _insert_lifecycle_state(session, run_id=run_a, shot_id=shot_id, status="active")
        _insert_lifecycle_state(session, run_id=run_b, shot_id=shot_id, status="active")

        count = session.execute(
            text(
                """
                SELECT count(*) FROM orchestration_lifecycle_state
                WHERE shot_id = :shot_id AND status = 'active'
                """
            ),
            {"shot_id": str(shot_id)},
        ).scalar_one()
        assert count == 2

        index_row = session.execute(
            text(
                """
                SELECT indexdef FROM pg_indexes
                WHERE indexname = 'ix_orchestration_lifecycle_state_shot_id_active'
                """
            )
        ).one()
        assert "WHERE (status = 'active'::text)" in index_row.indexdef
        assert "UNIQUE" not in index_row.indexdef.upper()


def test_orchestration_promotion_ledger_insert_roundtrip(alembic_db) -> None:
    session_factory, _, _ = alembic_db
    promotion_id = uuid.uuid4()

    with session_factory() as session:
        session.execute(
            text(
                """
                INSERT INTO orchestration_promotion_ledger (
                    promotion_id, shot_id, promoted_artifact_id,
                    promoted_by, rationale
                )
                VALUES (
                    :promotion_id, :shot_id, :promoted_artifact_id,
                    :promoted_by, :rationale
                )
                """
            ),
            {
                "promotion_id": str(promotion_id),
                "shot_id": str(uuid.uuid4()),
                "promoted_artifact_id": str(uuid.uuid4()),
                "promoted_by": "policy-driven",
                "rationale": "audit pass",
            },
        )
        session.commit()

        row = session.execute(
            text(
                """
                SELECT promotion_id, promoted_by, rationale
                FROM orchestration_promotion_ledger
                WHERE promotion_id = :promotion_id
                """
            ),
            {"promotion_id": str(promotion_id)},
        ).one()
        assert row.promotion_id == promotion_id
        assert row.promoted_by == "policy-driven"
        assert row.rationale == "audit pass"


def test_orchestration_promotion_ledger_canonical_resolution_query(alembic_db) -> None:
    session_factory, _, _ = alembic_db
    shot_id = uuid.uuid4()
    older_artifact = uuid.uuid4()
    newer_artifact = uuid.uuid4()
    base_time = datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc)

    with session_factory() as session:
        session.execute(
            text(
                """
                INSERT INTO orchestration_promotion_ledger (
                    promotion_id, shot_id, promoted_artifact_id,
                    promoted_at, promoted_by, rationale
                )
                VALUES (
                    :promotion_id, :shot_id, :promoted_artifact_id,
                    :promoted_at, :promoted_by, :rationale
                )
                """
            ),
            {
                "promotion_id": str(uuid.uuid4()),
                "shot_id": str(shot_id),
                "promoted_artifact_id": str(older_artifact),
                "promoted_at": base_time,
                "promoted_by": "operator",
                "rationale": "first promotion",
            },
        )
        session.execute(
            text(
                """
                INSERT INTO orchestration_promotion_ledger (
                    promotion_id, shot_id, promoted_artifact_id,
                    promoted_at, promoted_by, rationale
                )
                VALUES (
                    :promotion_id, :shot_id, :promoted_artifact_id,
                    :promoted_at, :promoted_by, :rationale
                )
                """
            ),
            {
                "promotion_id": str(uuid.uuid4()),
                "shot_id": str(shot_id),
                "promoted_artifact_id": str(newer_artifact),
                "promoted_at": base_time + timedelta(hours=1),
                "promoted_by": "operator",
                "rationale": "superseding promotion",
            },
        )
        session.commit()

        row = session.execute(
            text(
                """
                SELECT promoted_artifact_id
                FROM orchestration_promotion_ledger
                WHERE shot_id = :shot_id
                ORDER BY promoted_at DESC
                LIMIT 1
                """
            ),
            {"shot_id": str(shot_id)},
        ).one()
        assert row.promoted_artifact_id == newer_artifact


def test_orchestration_compromise_ledger_insert_roundtrip(alembic_db) -> None:
    session_factory, _, _ = alembic_db
    entry_id = uuid.uuid4()

    with session_factory() as session:
        for side in ("planned_predicted", "audit_actual"):
            session.execute(
                text(
                    """
                    INSERT INTO orchestration_compromise_ledger (
                        entry_id, intent_id, run_id, criterion_id,
                        dimension, side, magnitude
                    )
                    VALUES (
                        :entry_id, :intent_id, :run_id, :criterion_id,
                        :dimension, :side, CAST(:magnitude AS jsonb)
                    )
                    """
                ),
                {
                    "entry_id": str(uuid.uuid4()),
                    "intent_id": str(uuid.uuid4()),
                    "run_id": str(uuid.uuid4()),
                    "criterion_id": "motion_arc",
                    "dimension": "dynamic_range",
                    "side": side,
                    "magnitude": json.dumps(
                        {"scalar": 0.4 if side == "planned_predicted" else 0.6}
                    ),
                },
            )
        session.execute(
            text(
                """
                INSERT INTO orchestration_compromise_ledger (
                    entry_id, intent_id, run_id, criterion_id,
                    dimension, side, magnitude
                )
                VALUES (
                    :entry_id, :intent_id, :run_id, :criterion_id,
                    :dimension, :side, CAST(:magnitude AS jsonb)
                )
                """
            ),
            {
                "entry_id": str(entry_id),
                "intent_id": str(uuid.uuid4()),
                "run_id": str(uuid.uuid4()),
                "criterion_id": "timing",
                "dimension": "beat_alignment",
                "side": "audit_actual",
                "magnitude": json.dumps({"scalar": 0.2}),
            },
        )
        session.commit()

        row = session.execute(
            text(
                """
                SELECT entry_id, side, magnitude
                FROM orchestration_compromise_ledger
                WHERE entry_id = :entry_id
                """
            ),
            {"entry_id": str(entry_id)},
        ).one()
        assert row.entry_id == entry_id
        assert row.side == "audit_actual"
        assert row.magnitude == {"scalar": 0.2}


def test_orchestration_compromise_ledger_rejects_invalid_side(alembic_db) -> None:
    session_factory, _, _ = alembic_db

    with session_factory() as session:
        with pytest.raises(IntegrityError):
            session.execute(
                text(
                    """
                    INSERT INTO orchestration_compromise_ledger (
                        entry_id, intent_id, run_id, criterion_id,
                        dimension, side, magnitude
                    )
                    VALUES (
                        :entry_id, :intent_id, :run_id, :criterion_id,
                        :dimension, :side, CAST(:magnitude AS jsonb)
                    )
                    """
                ),
                {
                    "entry_id": str(uuid.uuid4()),
                    "intent_id": str(uuid.uuid4()),
                    "run_id": str(uuid.uuid4()),
                    "criterion_id": "motion_arc",
                    "dimension": "dynamic_range",
                    "side": "invalid_side",
                    "magnitude": json.dumps({"scalar": 0.1}),
                },
            )
            session.commit()
        session.rollback()


def test_orchestration_compromise_ledger_aggregation_query(alembic_db) -> None:
    session_factory, _, _ = alembic_db
    intent_id = uuid.uuid4()
    run_a = uuid.uuid4()
    run_b = uuid.uuid4()
    criterion_id = "motion_arc"
    dimension = "dynamic_range"
    magnitudes = [0.2, 0.15, 0.25]

    with session_factory() as session:
        for run_id, magnitude in zip((run_a, run_b, run_a), magnitudes):
            session.execute(
                text(
                    """
                    INSERT INTO orchestration_compromise_ledger (
                        entry_id, intent_id, run_id, criterion_id,
                        dimension, side, magnitude
                    )
                    VALUES (
                        :entry_id, :intent_id, :run_id, :criterion_id,
                        :dimension, :side, CAST(:magnitude AS jsonb)
                    )
                    """
                ),
                {
                    "entry_id": str(uuid.uuid4()),
                    "intent_id": str(intent_id),
                    "run_id": str(run_id),
                    "criterion_id": criterion_id,
                    "dimension": dimension,
                    "side": "audit_actual",
                    "magnitude": json.dumps({"scalar": magnitude}),
                },
            )
        session.commit()

        rows = session.execute(
            text(
                """
                SELECT run_id, magnitude
                FROM orchestration_compromise_ledger
                WHERE intent_id = :intent_id
                  AND criterion_id = :criterion_id
                  AND dimension = :dimension
                ORDER BY recorded_at
                """
            ),
            {
                "intent_id": str(intent_id),
                "criterion_id": criterion_id,
                "dimension": dimension,
            },
        ).all()

        assert len(rows) == 3
        assert {row.run_id for row in rows} == {run_a, run_b}
        total = sum(row.magnitude["scalar"] for row in rows)
        assert total == pytest.approx(0.6)
