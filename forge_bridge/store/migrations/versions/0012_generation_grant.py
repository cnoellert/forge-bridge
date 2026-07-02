"""Add generation_grant entity discriminator (#146).

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-01

Changes:
  entities
    - Extend ck_entities_type CHECK by adding 'generation_grant' (the
      spend-gate entity). A new entity type is ONE CHECK-enum add, NOT a new
      table — the grant is a row in the shared entities table, discriminated by
      entity_type, every field in the JSONB attributes dict (the 0009/0011
      pattern).

Notes:
  EVENT_TYPES additions for generation_grant.proposed/ratified/consumed/
  revoked/failed are Python-side only — the events table has no CHECK
  constraint on event_type.

  No data backfill — generation_grant is a new entity type with zero existing
  rows.
"""

from __future__ import annotations

from alembic import op


revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


_PRE_146_ENTITY_TYPES = (
    "asset",
    "layer",
    "media",
    "sequence",
    "shot",
    "stack",
    "staged_operation",
    "version",
    "assent_record",
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

_POST_146_ENTITY_TYPES = tuple(
    sorted(_PRE_146_ENTITY_TYPES + ("generation_grant",))
)


def _entity_type_check(types: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{t}'" for t in types)
    return f"entity_type IN ({quoted})"


def upgrade() -> None:
    op.drop_constraint("ck_entities_type", "entities", type_="check")
    op.create_check_constraint(
        "ck_entities_type",
        "entities",
        _entity_type_check(_POST_146_ENTITY_TYPES),
    )


def downgrade() -> None:
    op.drop_constraint("ck_entities_type", "entities", type_="check")
    op.create_check_constraint(
        "ck_entities_type",
        "entities",
        _entity_type_check(_PRE_146_ENTITY_TYPES),
    )
