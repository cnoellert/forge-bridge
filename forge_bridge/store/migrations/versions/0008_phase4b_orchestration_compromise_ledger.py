"""Phase 4B orchestration compromise ledger table.

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-28

Changes:
  orchestration_compromise_ledger
    - Append-only compromise consumption records per intent/criterion/dimension

Per PHASE-4B-ORCHESTRATION-DESIGN.md §4 (orchestration_compromise_ledger).

No FKs — history-preserving, application-layer integrity.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op


revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "orchestration_compromise_ledger",
        sa.Column("entry_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("intent_id", UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", UUID(as_uuid=True), nullable=True),
        sa.Column("artifact_id", UUID(as_uuid=True), nullable=True),
        sa.Column("criterion_id", sa.Text(), nullable=False),
        sa.Column("dimension", sa.Text(), nullable=False),
        sa.Column("side", sa.Text(), nullable=False),
        sa.Column("magnitude", JSONB, nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "side IN ('planned_predicted', 'audit_actual')",
            name="ck_orchestration_compromise_ledger_side",
        ),
    )

    op.create_index(
        "ix_orchestration_compromise_ledger_intent_criterion",
        "orchestration_compromise_ledger",
        ["intent_id", "criterion_id", "dimension"],
    )
    op.create_index(
        "ix_orchestration_compromise_ledger_run_id",
        "orchestration_compromise_ledger",
        ["run_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_orchestration_compromise_ledger_run_id",
        table_name="orchestration_compromise_ledger",
    )
    op.drop_index(
        "ix_orchestration_compromise_ledger_intent_criterion",
        table_name="orchestration_compromise_ledger",
    )
    op.drop_table("orchestration_compromise_ledger")
