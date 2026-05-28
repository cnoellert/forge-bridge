"""Phase 4B orchestration lifecycle state table.

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-28

Changes:
  orchestration_lifecycle_state
    - One row per pipeline run; stage + status tracking with optional block

Per PHASE-4B-ORCHESTRATION-DESIGN.md §4 (orchestration_lifecycle_state).

FK note: run_id → entities.id uses ON DELETE RESTRICT — the only FK on
Phase 4B operational tables. The run entity must exist before lifecycle
state is written; RESTRICT prevents silent orphaning if an entity row is
deleted. shot_id, intent_id, plan_id, current_canonical, and last_event_id
follow forge-bridge history-preserving precedent (application-layer integrity).
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op


revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


_LIFECYCLE_STAGES = (
    "ingest",
    "spec_convergence",
    "routing",
    "execution",
    "audit",
    "promotion",
    "publish",
)

_LIFECYCLE_STATUSES = (
    "active",
    "paused",
    "completed",
    "failed",
    "cancelled",
)


def _in_check(column: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({quoted})"


def upgrade() -> None:
    op.create_table(
        "orchestration_lifecycle_state",
        sa.Column("run_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("shot_id", UUID(as_uuid=True), nullable=False),
        sa.Column("current_stage", sa.Text(), nullable=False),
        sa.Column(
            "stage_entered_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("intent_id", UUID(as_uuid=True), nullable=True),
        sa.Column("plan_id", UUID(as_uuid=True), nullable=True),
        sa.Column("current_canonical", UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("block", JSONB, nullable=True),
        sa.Column("last_event_id", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["entities.id"],
            name="fk_orchestration_lifecycle_state_run_id",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            _in_check("current_stage", _LIFECYCLE_STAGES),
            name="ck_orchestration_lifecycle_state_current_stage",
        ),
        sa.CheckConstraint(
            _in_check("status", _LIFECYCLE_STATUSES),
            name="ck_orchestration_lifecycle_state_status",
        ),
        sa.CheckConstraint(
            "(status = 'paused') = (block IS NOT NULL)",
            name="ck_orchestration_lifecycle_state_paused_has_block",
        ),
    )

    op.create_index(
        "ix_orchestration_lifecycle_state_shot_id_active",
        "orchestration_lifecycle_state",
        ["shot_id"],
        postgresql_where=sa.text("status = 'active'"),
    )
    op.create_index(
        "ix_orchestration_lifecycle_state_current_stage",
        "orchestration_lifecycle_state",
        ["current_stage"],
    )
    op.create_index(
        "ix_orchestration_lifecycle_state_status",
        "orchestration_lifecycle_state",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_orchestration_lifecycle_state_status",
        table_name="orchestration_lifecycle_state",
    )
    op.drop_index(
        "ix_orchestration_lifecycle_state_current_stage",
        table_name="orchestration_lifecycle_state",
    )
    op.drop_index(
        "ix_orchestration_lifecycle_state_shot_id_active",
        table_name="orchestration_lifecycle_state",
    )
    op.drop_table("orchestration_lifecycle_state")
