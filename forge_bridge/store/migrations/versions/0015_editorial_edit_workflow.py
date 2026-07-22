"""Add editorial_edit_workflow entity discriminator (#235).

Revision ID: 0015
Revises: 0014
Create Date: 2026-07-22

Changes:
  entities
    - Extend ck_entities_type CHECK by adding 'editorial_edit_workflow' (the
      durable Phase 149 editorial-edit workflow correlation). A new entity type
      is ONE CHECK-enum add, NOT a new table — the workflow is a row in the
      shared entities table, discriminated by entity_type, every field in the
      JSONB attributes dict (the 0009/0012/0013 pattern).
    - Add a partial unique index on ``attributes ->> 'proposal_id'`` so the
      workflow is directly lookup-able by proposal_id and a duplicate proposal
      cannot create two authority rows (the 0014 partial-index pattern).

Notes:
  EVENT_TYPES additions for editorial_edit_workflow.* are Python-side only —
  the events table has no CHECK constraint on event_type.

  No data backfill — editorial_edit_workflow is a new entity type with zero
  existing rows.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


# Pre-#235 entity types = the post-0013 (post-#161) set. Kept explicit so the
# drop+recreate is self-contained.
_PRE_235_ENTITY_TYPES = (
    "asset",
    "layer",
    "media",
    "sequence",
    "shot",
    "stack",
    "staged_operation",
    "version",
    "assent_record",
    "consent_grant",
    "generation_grant",
    "orch_audit_report",
    "orch_capability_snapshot",
    "orch_execution_plan",
    "orch_execution_result",
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

_POST_235_ENTITY_TYPES = tuple(
    sorted(_PRE_235_ENTITY_TYPES + ("editorial_edit_workflow",))
)

_INDEX_NAME = "uq_entities_editorial_edit_workflow_proposal_id"
_INDEX_EXPRESSION = "(attributes ->> 'proposal_id')"
_INDEX_PREDICATE = (
    "entity_type = 'editorial_edit_workflow' "
    "AND attributes ? 'proposal_id'"
)


def _entity_type_check(types: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{t}'" for t in types)
    return f"entity_type IN ({quoted})"


def upgrade() -> None:
    op.drop_constraint("ck_entities_type", "entities", type_="check")
    op.create_check_constraint(
        "ck_entities_type",
        "entities",
        _entity_type_check(_POST_235_ENTITY_TYPES),
    )
    op.create_index(
        _INDEX_NAME,
        "entities",
        [sa.text(_INDEX_EXPRESSION)],
        unique=True,
        postgresql_where=sa.text(_INDEX_PREDICATE),
    )


def downgrade() -> None:
    op.drop_index(_INDEX_NAME, table_name="entities")
    op.drop_constraint("ck_entities_type", "entities", type_="check")
    op.create_check_constraint(
        "ck_entities_type",
        "entities",
        _entity_type_check(_PRE_235_ENTITY_TYPES),
    )
