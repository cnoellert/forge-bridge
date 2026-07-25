"""Add orch_workflow_record entity discriminator (#242).

Revision ID: 0016
Revises: 0015
Create Date: 2026-07-25

Changes:
  entities
    - Extend ck_entities_type CHECK by adding 'orch_workflow_record' — ONE
      generic durable product-workflow correlation type, carrying a ``kind``
      discriminator inside the JSONB attributes dict so a second workflow
      family (e.g. #241) reuses this row family with NO further migration.
      A new entity type is ONE CHECK-enum add, NOT a new table (the
      0009/0012/0013/0015 pattern).
    - Add a partial unique index on
      ``(attributes ->> 'kind', attributes ->> 'proposal_id')`` so a workflow
      is directly lookup-able by (kind, proposal_id) and a duplicate proposal
      cannot create two authority rows within one kind (the 0014/0015 partial
      index pattern). The pair — not proposal_id alone — is the key, because
      the ``kind`` column is precisely what makes the row family shared.

Notes:
  0015 (editorial_edit_workflow) is deliberately left untouched. It is a
  shipped table with live rows; there is no data migration and no backfill
  here. The two entity types coexist.

  No data backfill — orch_workflow_record is a new entity type with zero
  existing rows.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


# Pre-#242 entity types = the post-0015 (post-#235) set. Kept explicit so the
# drop+recreate is self-contained.
_PRE_242_ENTITY_TYPES = (
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
    "editorial_edit_workflow",
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

_POST_242_ENTITY_TYPES = tuple(
    sorted(_PRE_242_ENTITY_TYPES + ("orch_workflow_record",))
)

INDEX_NAME = "uq_entities_orch_workflow_record_kind_proposal_id"
INDEX_EXPRESSIONS = (
    "(attributes ->> 'kind')",
    "(attributes ->> 'proposal_id')",
)
INDEX_PREDICATE = (
    "entity_type = 'orch_workflow_record' "
    "AND attributes ? 'kind' "
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
        _entity_type_check(_POST_242_ENTITY_TYPES),
    )
    op.create_index(
        INDEX_NAME,
        "entities",
        [sa.text(expression) for expression in INDEX_EXPRESSIONS],
        unique=True,
        postgresql_where=sa.text(INDEX_PREDICATE),
    )


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="entities")
    op.drop_constraint("ck_entities_type", "entities", type_="check")
    op.create_check_constraint(
        "ck_entities_type",
        "entities",
        _entity_type_check(_PRE_242_ENTITY_TYPES),
    )
