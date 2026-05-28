"""Phase 4B entity discriminators + content_hash column.

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-28

Changes:
  entities
    - ADD COLUMN content_hash text NULL
    - CREATE UNIQUE INDEX ix_entities_content_hash_orch partial
      WHERE entity_type LIKE 'orch_%' AND content_hash IS NOT NULL
    - Extend ck_entities_type CHECK with twelve orch_* discriminators

Per PHASE-4B-ORCHESTRATION-DESIGN.md §4 (Entity types) and §3 (Storage doctrine).
Repository layer enforces content_hash presence on orch_* inserts in Step 3+;
the column remains nullable at the DB layer.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


# Pre-0005 entity types (0003_staged_operation.py)
_PRE_ORCH_ENTITY_TYPES = (
    "asset",
    "layer",
    "media",
    "sequence",
    "shot",
    "stack",
    "staged_operation",
    "version",
)

# Per PHASE-4B-ORCHESTRATION-DESIGN.md §4
_ORCH_ENTITY_TYPES = (
    "orch_audit_report",
    "orch_capability_snapshot",
    "orch_execution_plan",
    "orch_generation_artifact",
    "orch_inputs_catalog",
    "orch_locked_intent",
    "orch_partial_fidelity_snapshot",
    "orch_pipeline_run",
    "orch_provenance_manifest",
    "orch_rule_snapshot",
    "orch_spec_convergence_trace",
    "orch_validation_report",
)

_ALL_ENTITY_TYPES = tuple(sorted(_PRE_ORCH_ENTITY_TYPES + _ORCH_ENTITY_TYPES))


def _entity_type_check(types: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{t}'" for t in types)
    return f"entity_type IN ({quoted})"


def upgrade() -> None:
    op.add_column("entities", sa.Column("content_hash", sa.Text(), nullable=True))

    op.create_index(
        "ix_entities_content_hash_orch",
        "entities",
        ["content_hash"],
        unique=True,
        postgresql_where=sa.text(
            "entity_type LIKE 'orch_%' AND content_hash IS NOT NULL"
        ),
    )

    op.drop_constraint("ck_entities_type", "entities", type_="check")
    op.create_check_constraint(
        "ck_entities_type",
        "entities",
        _entity_type_check(_ALL_ENTITY_TYPES),
    )


def downgrade() -> None:
    op.drop_constraint("ck_entities_type", "entities", type_="check")
    op.create_check_constraint(
        "ck_entities_type",
        "entities",
        _entity_type_check(_PRE_ORCH_ENTITY_TYPES),
    )

    op.drop_index("ix_entities_content_hash_orch", table_name="entities")
    op.drop_column("entities", "content_hash")
