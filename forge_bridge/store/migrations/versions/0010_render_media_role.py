"""Add the `render` media role (DCC render output).

Blender is the first DCC to emit a media classification we call `render`
(Flame renders remain `comp`). Per the room ruling, render is a media ROLE on the
node — render media is `member_of` its Shot — not a `render_of` relationship type.
Seeds one row into registry_roles, mirroring the media roles from migration 0002.

Revision ID: 0010
Revises: 0009
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

_RENDER_KEY = uuid.UUID("00000000-0000-0000-0010-000000000007")


def _role_table() -> sa.Table:
    return sa.table(
        "registry_roles",
        sa.column("key", sa.dialects.postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String),
        sa.column("label", sa.String),
        sa.column("role_class", sa.String),
        sa.column("order", sa.Integer),
        sa.column("protected", sa.Boolean),
        sa.column("attributes", sa.dialects.postgresql.JSONB),
    )


def upgrade() -> None:
    op.bulk_insert(
        _role_table(),
        [
            {
                "key": _RENDER_KEY,
                "name": "render",
                "label": "Render",
                "role_class": "media",
                "order": 16,
                "protected": True,
                "attributes": {
                    "generation_floor": 1,
                    "description": "DCC render output (e.g. Blender) — generation 1",
                },
            }
        ],
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM registry_roles WHERE key = :k").bindparams(
            k=str(_RENDER_KEY)
        )
    )
