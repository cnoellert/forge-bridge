"""Phase 4B orchestration promotion ledger table.

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-28

Changes:
  orchestration_promotion_ledger
    - Append-only canonical promotion history per shot

Per PHASE-4B-ORCHESTRATION-DESIGN.md §4 (orchestration_promotion_ledger).

No FKs — history-preserving, application-layer integrity (same precedent as
events.project_id / events.entity_id).
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op


revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "orchestration_promotion_ledger",
        sa.Column("promotion_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("shot_id", UUID(as_uuid=True), nullable=False),
        sa.Column("promoted_artifact_id", UUID(as_uuid=True), nullable=False),
        sa.Column("superseded_id", UUID(as_uuid=True), nullable=True),
        sa.Column("audit_report_id", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "promoted_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("promoted_by", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
    )

    op.create_index(
        "ix_orchestration_promotion_ledger_shot_id_promoted_at",
        "orchestration_promotion_ledger",
        ["shot_id", "promoted_at"],
        postgresql_ops={"promoted_at": "DESC"},
    )
    op.create_index(
        "ix_orchestration_promotion_ledger_promoted_artifact_id",
        "orchestration_promotion_ledger",
        ["promoted_artifact_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_orchestration_promotion_ledger_promoted_artifact_id",
        table_name="orchestration_promotion_ledger",
    )
    op.drop_index(
        "ix_orchestration_promotion_ledger_shot_id_promoted_at",
        table_name="orchestration_promotion_ledger",
    )
    op.drop_table("orchestration_promotion_ledger")
