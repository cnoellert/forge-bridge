"""Initial schema — create all forge-bridge tables.

Revision ID: 0001
Revises: (none)
Create Date: 2026-02-24

Tables created:
  registry_roles
  registry_relationship_types
  projects
  entities
  locations
  relationships
  events
  sessions
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── registry_roles ────────────────────────────────────────
    op.create_table(
        "registry_roles",
        sa.Column("key",       UUID(as_uuid=True), primary_key=True),
        sa.Column("name",      sa.String(128),  nullable=False, unique=True),
        sa.Column("label",     sa.String(256),  nullable=False),
        sa.Column("order",     sa.Integer(),    nullable=False, server_default="0"),
        sa.Column("protected", sa.Boolean(),    nullable=False, server_default="false"),
        sa.Column("attributes", JSONB,          nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_registry_roles_name", "registry_roles", ["name"])

    # ── registry_relationship_types ───────────────────────────
    op.create_table(
        "registry_relationship_types",
        sa.Column("key",            UUID(as_uuid=True), primary_key=True),
        sa.Column("name",           sa.String(128),  nullable=False, unique=True),
        sa.Column("label",          sa.String(256),  nullable=False),
        sa.Column("description",    sa.Text(),       nullable=False, server_default=""),
        sa.Column("directionality", sa.String(4),    nullable=False, server_default="→"),
        sa.Column("protected",      sa.Boolean(),    nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_registry_rel_types_name", "registry_relationship_types", ["name"])

    # ── projects ──────────────────────────────────────────────
    op.create_table(
        "projects",
        sa.Column("id",         UUID(as_uuid=True), primary_key=True),
        sa.Column("name",       sa.String(256),  nullable=False),
        sa.Column("code",       sa.String(64),   nullable=False),
        sa.Column("attributes", JSONB,           nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("code", name="uq_projects_code"),
    )
    op.create_index("ix_projects_code", "projects", ["code"])

    # ── entities ──────────────────────────────────────────────
    op.create_table(
        "entities",
        sa.Column("id",          UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_type", sa.String(32),   nullable=False),
        sa.Column("project_id",  UUID(as_uuid=True),
                  sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=True),
        sa.Column("name",        sa.String(256),  nullable=True),
        sa.Column("status",      sa.String(64),   nullable=True),
        sa.Column("attributes",  JSONB,           nullable=False, server_default="{}"),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at",  sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "entity_type IN ('asset', 'layer', 'media', 'sequence', 'shot', 'stack', 'version')",
            name="ck_entities_type",
        ),
    )
    op.create_index("ix_entities_project_type", "entities", ["project_id", "entity_type"])
    op.create_index("ix_entities_type_name",    "entities", ["entity_type", "name"])
    op.create_index("ix_entities_status",       "entities", ["status"])
    op.create_index("ix_entities_attributes",   "entities", ["attributes"],
                    postgresql_using="gin")

    # ── locations ─────────────────────────────────────────────
    op.create_table(
        "locations",
        sa.Column("id",           UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id",   UUID(as_uuid=True),
                  sa.ForeignKey("projects.id",  ondelete="CASCADE"), nullable=True),
        sa.Column("entity_id",    UUID(as_uuid=True),
                  sa.ForeignKey("entities.id",  ondelete="CASCADE"), nullable=True),
        sa.Column("path",         sa.Text(),   nullable=False),
        sa.Column("storage_type", sa.String(32), nullable=False, server_default="local"),
        sa.Column("priority",     sa.Integer(), nullable=False, server_default="0"),
        sa.Column("exists",       sa.Boolean(), nullable=True),
        sa.Column("attributes",   JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at",   sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("checked_at",   sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "(project_id IS NOT NULL)::int + (entity_id IS NOT NULL)::int = 1",
            name="ck_locations_owner",
        ),
        sa.CheckConstraint(
            "storage_type IN ('local', 'network', 'cloud', 'archive')",
            name="ck_locations_storage_type",
        ),
    )
    op.create_index("ix_locations_path",     "locations", ["path"])
    op.create_index("ix_locations_priority", "locations", ["entity_id", "priority"])

    # ── relationships ─────────────────────────────────────────
    op.create_table(
        "relationships",
        sa.Column("id",           UUID(as_uuid=True), primary_key=True),
        sa.Column("source_id",    UUID(as_uuid=True),
                  sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_id",    UUID(as_uuid=True),
                  sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rel_type_key", UUID(as_uuid=True), nullable=False),
        sa.Column("attributes",   JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at",   sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("source_id", "target_id", "rel_type_key",
                            name="uq_relationships_edge"),
    )
    op.create_index("ix_relationships_source_type", "relationships", ["source_id", "rel_type_key"])
    op.create_index("ix_relationships_target_type", "relationships", ["target_id", "rel_type_key"])

    # ── events ────────────────────────────────────────────────
    op.create_table(
        "events",
        sa.Column("id",          UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type",  sa.String(64),  nullable=False),
        sa.Column("session_id",  UUID(as_uuid=True), nullable=True),
        sa.Column("client_name", sa.String(128), nullable=True),
        sa.Column("project_id",  UUID(as_uuid=True), nullable=True),
        sa.Column("entity_id",   UUID(as_uuid=True), nullable=True),
        sa.Column("payload",     JSONB, nullable=False, server_default="{}"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
    )
    op.create_index("ix_events_type_time",    "events", ["event_type",  "occurred_at"])
    op.create_index("ix_events_project_time", "events", ["project_id",  "occurred_at"])
    op.create_index("ix_events_entity_time",  "events", ["entity_id",   "occurred_at"])
    op.create_index("ix_events_session",      "events", ["session_id"])

    # ── sessions ──────────────────────────────────────────────
    op.create_table(
        "sessions",
        sa.Column("id",              UUID(as_uuid=True), primary_key=True),
        sa.Column("client_name",     sa.String(128), nullable=False),
        sa.Column("endpoint_type",   sa.String(64),  nullable=True),
        sa.Column("host",            sa.String(256), nullable=True),
        sa.Column("capabilities",    JSONB, nullable=False, server_default="{}"),
        sa.Column("connected_at",    sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("disconnected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at",    sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_sessions_client",       "sessions", ["client_name"])
    op.create_index("ix_sessions_connected_at", "sessions", ["connected_at"])


def downgrade() -> None:
    op.drop_table("sessions")
    op.drop_table("events")
    op.drop_table("relationships")
    op.drop_table("locations")
    op.drop_table("entities")
    op.drop_table("projects")
    op.drop_table("registry_relationship_types")
    op.drop_table("registry_roles")
