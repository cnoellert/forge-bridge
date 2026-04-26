"""Staged operation entity type — FB-A.

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-25

Changes:
  entities
    - Extend ck_entities_type CHECK to include 'staged_operation'
      (slotted alphabetically between 'stack' and 'version')

Notes:
  EVENT_TYPES additions for staged.proposed/approved/rejected/executed/failed
  are Python-side only — the events table has no CHECK constraint on
  event_type (verified against 0001_initial_schema.py and DBEvent.__table_args__).

  No data backfill — staged_operation is a new entity type with zero existing
  rows (D-16 in the FB-A context).
"""

import sqlalchemy as sa
from alembic import op


# revision identifiers
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


# ── Upgrade ───────────────────────────────────────────────────────────────────

def upgrade() -> None:
    # Extend ck_entities_type to include 'staged_operation'
    # (alphabetic between 'stack' and 'version')
    op.drop_constraint("ck_entities_type", "entities", type_="check")
    op.create_check_constraint(
        "ck_entities_type",
        "entities",
        "entity_type IN ('asset', 'layer', 'media', 'sequence', 'shot', "
        "'stack', 'staged_operation', 'version')",
    )


# ── Downgrade ─────────────────────────────────────────────────────────────────

def downgrade() -> None:
    # Restore the original seven-type CHECK from 0001_initial_schema.py
    op.drop_constraint("ck_entities_type", "entities", type_="check")
    op.create_check_constraint(
        "ck_entities_type",
        "entities",
        "entity_type IN ('asset', 'layer', 'media', 'sequence', 'shot', "
        "'stack', 'version')",
    )
