"""Role class discriminator, media lineage roles, process graph relationships.

Revision ID: 0002
Revises: 0001
Create Date: 2026-02-27

Changes:
  registry_roles
    - Add role_class column (VARCHAR 32, NOT NULL, DEFAULT 'track')
    - Seed media lineage roles: raw, grade, denoise, prep, roto, comp

  registry_relationship_types
    - Seed consumes (UUID 00000000-…-0006) and produces (UUID 00000000-…-0007)

  locations
    - Extend storage_type CHECK constraint to include 'clip'
      (openClip and batchOpenClip are locations with storage_type='clip',
       not separate entity types)

Design notes:
  role_class = 'track'
    Compositional function within a shot Version — what the media *does*
    in a specific comp stack. Carried as edge attribute on consumes edges.
    Existing roles (primary/reference/matte/background/foreground/color/audio)
    are track roles.

  role_class = 'media'
    Pipeline stage that *produced* the media atom — what happened to the
    media to create it. Travels with media.attributes.role.
    Generation semantics: raw=0, all others=1+.
    raw:     camera source, axiomatically generation 0, no producing Version
    grade:   colour graded plate
    denoise: noise reduction pass
    prep:    paint / cleanup / rig removal
    roto:    rotoscope delivery
    comp:    composite render output

  consumes: Version → Media
    This media entity was an input to this Version (comp/process).
    Edge attributes carry track_role and layer_index when relevant.

  produces: Version → Media
    This media entity was created as output of this Version.
"""

import uuid
import sqlalchemy as sa
from alembic import op


# revision identifiers
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

# ── Well-known UUIDs ──────────────────────────────────────────────────────────
# These match SYSTEM_REL_KEYS in forge_bridge/core/traits.py exactly.
# Do not change them.

_CONSUMES_KEY = uuid.UUID("00000000-0000-0000-0000-000000000006")
_PRODUCES_KEY = uuid.UUID("00000000-0000-0000-0000-000000000007")

# Media role well-known UUIDs — stable across upgrades
_MEDIA_ROLE_KEYS = {
    "raw":     uuid.UUID("00000000-0000-0000-0010-000000000001"),
    "grade":   uuid.UUID("00000000-0000-0000-0010-000000000002"),
    "denoise": uuid.UUID("00000000-0000-0000-0010-000000000003"),
    "prep":    uuid.UUID("00000000-0000-0000-0010-000000000004"),
    "roto":    uuid.UUID("00000000-0000-0000-0010-000000000005"),
    "comp":    uuid.UUID("00000000-0000-0000-0010-000000000006"),
}

# ── Upgrade ───────────────────────────────────────────────────────────────────

def upgrade() -> None:
    # ── 1. Add role_class to registry_roles ──────────────────────────────────
    op.add_column(
        "registry_roles",
        sa.Column(
            "role_class",
            sa.String(32),
            nullable=False,
            server_default="track",
        ),
    )
    # Remove server_default — we only needed it for the backfill
    op.alter_column("registry_roles", "role_class", server_default=None)

    op.create_index(
        "ix_registry_roles_class",
        "registry_roles",
        ["role_class"],
    )

    # ── 2. Extend storage_type constraint to include 'clip' ───────────────────
    # Drop existing CHECK, recreate with 'clip' added
    op.drop_constraint("ck_locations_storage_type", "locations", type_="check")
    op.create_check_constraint(
        "ck_locations_storage_type",
        "locations",
        "storage_type IN ('local', 'network', 'cloud', 'archive', 'clip')",
    )

    # ── 3. Seed consumes and produces relationship types ──────────────────────
    rel_table = sa.table(
        "registry_relationship_types",
        sa.column("key",           sa.dialects.postgresql.UUID(as_uuid=True)),
        sa.column("name",          sa.String),
        sa.column("label",         sa.String),
        sa.column("description",   sa.Text),
        sa.column("directionality",sa.String),
        sa.column("protected",     sa.Boolean),
    )
    op.bulk_insert(rel_table, [
        {
            "key":            _CONSUMES_KEY,
            "name":           "consumes",
            "label":          "consumes",
            "description":    (
                "Version took this media as input. "
                "Edge attributes carry track_role and layer_index when relevant."
            ),
            "directionality": "→",
            "protected":      True,
        },
        {
            "key":            _PRODUCES_KEY,
            "name":           "produces",
            "label":          "produces",
            "description":    "Version created this media as output.",
            "directionality": "→",
            "protected":      True,
        },
    ])

    # ── 4. Seed media lineage roles ───────────────────────────────────────────
    role_table = sa.table(
        "registry_roles",
        sa.column("key",        sa.dialects.postgresql.UUID(as_uuid=True)),
        sa.column("name",       sa.String),
        sa.column("label",      sa.String),
        sa.column("role_class", sa.String),
        sa.column("order",      sa.Integer),
        sa.column("protected",  sa.Boolean),
        sa.column("attributes", sa.dialects.postgresql.JSONB),
    )
    media_roles = [
        ("raw",     "Raw",     10, {"generation_floor": 0,
                                    "description": "Camera source — generation 0, no producing Version"}),
        ("grade",   "Grade",   11, {"generation_floor": 1,
                                    "description": "Colour graded plate"}),
        ("denoise", "Denoise", 12, {"generation_floor": 1,
                                    "description": "Noise reduction pass"}),
        ("prep",    "Prep",    13, {"generation_floor": 1,
                                    "description": "Paint / cleanup / rig removal"}),
        ("roto",    "Roto",    14, {"generation_floor": 1,
                                    "description": "Rotoscope delivery"}),
        ("comp",    "Comp",    15, {"generation_floor": 1,
                                    "description": "Composite render output"}),
    ]
    op.bulk_insert(role_table, [
        {
            "key":        _MEDIA_ROLE_KEYS[name],
            "name":       name,
            "label":      label,
            "role_class": "media",
            "order":      order,
            "protected":  True,
            "attributes": attrs,
        }
        for name, label, order, attrs in media_roles
    ])


# ── Downgrade ─────────────────────────────────────────────────────────────────

def downgrade() -> None:
    # Remove media roles
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM registry_roles WHERE role_class = 'media'")
    )

    # Remove consumes + produces relationship types
    conn.execute(
        sa.text(
            "DELETE FROM registry_relationship_types WHERE key IN (:c, :p)"
        ),
        {"c": str(_CONSUMES_KEY), "p": str(_PRODUCES_KEY)},
    )

    # Restore original storage_type constraint
    op.drop_constraint("ck_locations_storage_type", "locations", type_="check")
    op.create_check_constraint(
        "ck_locations_storage_type",
        "locations",
        "storage_type IN ('local', 'network', 'cloud', 'archive')",
    )

    # Drop role_class index and column
    op.drop_index("ix_registry_roles_class", table_name="registry_roles")
    op.drop_column("registry_roles", "role_class")
