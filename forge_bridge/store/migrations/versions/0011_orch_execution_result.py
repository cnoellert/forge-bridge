"""Add orch_execution_result entity discriminator.

Revision ID: 0011
Revises: 0010
"""

from __future__ import annotations

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


_PRE_V4_ENTITY_TYPES = (
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

_POST_V4_ENTITY_TYPES = tuple(
    sorted(_PRE_V4_ENTITY_TYPES + ("orch_execution_result",))
)


def _entity_type_check(types: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{t}'" for t in types)
    return f"entity_type IN ({quoted})"


def upgrade() -> None:
    op.drop_constraint("ck_entities_type", "entities", type_="check")
    op.create_check_constraint(
        "ck_entities_type",
        "entities",
        _entity_type_check(_POST_V4_ENTITY_TYPES),
    )


def downgrade() -> None:
    op.drop_constraint("ck_entities_type", "entities", type_="check")
    op.create_check_constraint(
        "ck_entities_type",
        "entities",
        _entity_type_check(_PRE_V4_ENTITY_TYPES),
    )
