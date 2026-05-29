"""Assent record entity type — Phase A.2.

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-28

Changes:
  entities
    - Extend ck_entities_type CHECK from 20 -> 21 entity_types by adding
      'assent_record' (alphabetically between 'asset' and 'layer' in the
      sorted output).

Notes:
  EVENT_TYPES additions for assent.proposed/ratified/applied/failed are
  Python-side only -- the events table has no CHECK constraint on event_type.

  No data backfill -- assent_record is a new entity type with zero existing
  rows.

  Helper pattern reused from 0005_phase4b_entity_types.py:62-64.
"""

from __future__ import annotations

from alembic import op


revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


_PRE_A2_ENTITY_TYPES = (
    "asset",
    "layer",
    "media",
    "sequence",
    "shot",
    "stack",
    "staged_operation",
    "version",
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

_POST_A2_ENTITY_TYPES = tuple(
    sorted(_PRE_A2_ENTITY_TYPES + ("assent_record",))
)


def _entity_type_check(types: tuple[str, ...]) -> str:
    """Mirror the helper at 0005_phase4b_entity_types.py:62-64."""
    quoted = ", ".join(f"'{t}'" for t in types)
    return f"entity_type IN ({quoted})"


def upgrade() -> None:
    op.drop_constraint("ck_entities_type", "entities", type_="check")
    op.create_check_constraint(
        "ck_entities_type",
        "entities",
        _entity_type_check(_POST_A2_ENTITY_TYPES),
    )


def downgrade() -> None:
    op.drop_constraint("ck_entities_type", "entities", type_="check")
    op.create_check_constraint(
        "ck_entities_type",
        "entities",
        _entity_type_check(_PRE_A2_ENTITY_TYPES),
    )
