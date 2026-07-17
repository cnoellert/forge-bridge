"""Add unique generation idempotency-key index (#141).

Revision ID: 0014
Revises: 0013
Create Date: 2026-07-17

The key remains lifecycle data inside ``entities.attributes``. A partial
expression index gives it database-level uniqueness only for generation
artifacts that actually carry a key, preserving keyless legacy rows.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

INDEX_NAME = "uq_entities_generation_idempotency_key"
INDEX_EXPRESSION = "(attributes ->> 'idempotency_key')"
INDEX_PREDICATE = (
    "entity_type = 'orch_generation_artifact' "
    "AND attributes ? 'idempotency_key'"
)


def upgrade() -> None:
    op.create_index(
        INDEX_NAME,
        "entities",
        [sa.text(INDEX_EXPRESSION)],
        unique=True,
        postgresql_where=sa.text(INDEX_PREDICATE),
    )


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="entities")
