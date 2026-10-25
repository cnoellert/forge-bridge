"""Add the plate entity kind (forge-contracts v0.12).

Revision ID: 0018
Revises: 0017
Create Date: 2026-10-24

Changes:
  entities
    - Extend ck_entities_type CHECK by adding 'plate': a timed piece of a
      source, a context beside shot and asset that owns its own Versions and
      Tasks (forge-pipeline ADR-012). Typed field shot_id (the home shot) and
      open metadata live in the JSONB attributes dict. One CHECK-enum add,
      NOT a new table (the 0009/0012/0013/0015/0016/0017 pattern).

Notes:
  No data backfill — plate is a new entity type with zero existing rows.

Downgrade:
  FAILS while any plate rows exist: recreating the pre-0018 CHECK rejects
  them. Delete the plate rows first if a downgrade is really intended.
"""

from __future__ import annotations

from alembic import op


revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


# Pre-0018 entity types = the post-0017 (post-#274) set. Kept explicit (and as
# literals, not contract imports) so the drop+recreate is self-contained.
_PRE_0018_ENTITY_TYPES = (
    "asset",
    "assent_record",
    "bid",
    "bid_line",
    "booking",
    "consent_grant",
    "editorial_edit_workflow",
    "generation_grant",
    "layer",
    "media",
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
    "orch_workflow_record",
    "person",
    "resource",
    "resource_dependency",
    "responsibility",
    "sequence",
    "shot",
    "stack",
    "staged_operation",
    "task",
    "vendor",
    "version",
)

PLATE_ENTITY_TYPE = "plate"

_POST_0018_ENTITY_TYPES = tuple(
    sorted(_PRE_0018_ENTITY_TYPES + (PLATE_ENTITY_TYPE,))
)


def _entity_type_check(types: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{t}'" for t in types)
    return f"entity_type IN ({quoted})"


def upgrade() -> None:
    op.drop_constraint("ck_entities_type", "entities", type_="check")
    op.create_check_constraint(
        "ck_entities_type",
        "entities",
        _entity_type_check(_POST_0018_ENTITY_TYPES),
    )


def downgrade() -> None:
    op.drop_constraint("ck_entities_type", "entities", type_="check")
    op.create_check_constraint(
        "ck_entities_type",
        "entities",
        _entity_type_check(_PRE_0018_ENTITY_TYPES),
    )
