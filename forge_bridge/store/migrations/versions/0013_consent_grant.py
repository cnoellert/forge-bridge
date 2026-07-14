"""Add consent_grant entity discriminator (#161).

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-14

Changes:
  entities
    - Extend ck_entities_type CHECK by adding 'consent_grant' (the fitted-model
      consent latch). A new entity type is ONE CHECK-enum add, NOT a new table
      — the grant is a row in the shared entities table, discriminated by
      entity_type, every field in the JSONB attributes dict (the 0009/0011/0012
      pattern).

Notes:
  EVENT_TYPES additions for consent_grant.proposed/ratified/bound/withdrawn are
  Python-side only — the events table has no CHECK constraint on event_type.

  No data backfill — consent_grant is a new entity type with zero existing rows.

  ``fitted_model_asset_id`` is mutable JSONB state bound at fit-time, NOT part of
  the content-hashed terms body — no schema column, it lives in attributes.
"""

from __future__ import annotations

from alembic import op


revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


# Pre-#161 entity types = the post-0012 (post-#146) set: the pre-#146 list PLUS
# 'generation_grant'. Kept explicit so the drop+recreate is self-contained.
_PRE_161_ENTITY_TYPES = (
    "asset",
    "layer",
    "media",
    "sequence",
    "shot",
    "stack",
    "staged_operation",
    "version",
    "assent_record",
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

_POST_161_ENTITY_TYPES = tuple(
    sorted(_PRE_161_ENTITY_TYPES + ("consent_grant",))
)


def _entity_type_check(types: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{t}'" for t in types)
    return f"entity_type IN ({quoted})"


def upgrade() -> None:
    op.drop_constraint("ck_entities_type", "entities", type_="check")
    op.create_check_constraint(
        "ck_entities_type",
        "entities",
        _entity_type_check(_POST_161_ENTITY_TYPES),
    )


def downgrade() -> None:
    op.drop_constraint("ck_entities_type", "entities", type_="check")
    op.create_check_constraint(
        "ck_entities_type",
        "entities",
        _entity_type_check(_PRE_161_ENTITY_TYPES),
    )
