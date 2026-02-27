"""
forge-bridge database schema.

Table design principles:

  1. UUIDs everywhere as primary keys — matches the core vocabulary design
     where every entity already carries a UUID. No integer sequences.

  2. Separate tables per concern — registry, entities, graph, events.
     No polymorphic "everything in one table" shortcuts.

  3. entity_type column on every entity record — lets us query "all shots"
     or "all versions" without joins across type tables. A single entities
     table with a type discriminator rather than one table per entity type.
     Entity-specific columns live in a JSONB `attributes` column.

  4. Append-only events table — never updated, never deleted. The full
     history of every change is preserved. State is reconstructed by
     replaying or by querying the current-state tables directly.

  5. All times in UTC, stored as TIMESTAMP WITH TIME ZONE.

  6. No application-level foreign key enforcement in JSONB columns —
     the relationship graph handles referential integrity at the
     application layer, not the DB layer. Structured columns (entity_id,
     project_id, etc.) do have FK constraints.

Schema overview:

  registry_roles                  — role definitions
  registry_relationship_types     — relationship type definitions

  projects                        — top-level containers
  entities                        — all non-project entities (sequence,
                                    shot, asset, version, media, layer, stack)
  locations                       — file path records (1..n per entity)
  relationships                   — directed edges in the dependency graph

  events                          — append-only audit + change log
  sessions                        — connected client tracking (server-managed)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


# ─────────────────────────────────────────────────────────────
# Base
# ─────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


# ─────────────────────────────────────────────────────────────
# Registry tables
# ─────────────────────────────────────────────────────────────

class DBRole(Base):
    """A role definition in the registry.

    key        — stable UUID. Stored in Layer.role_key. Never changes.
    name       — canonical string name. Can change via rename.
    label      — display name. Can change freely.
    role_class — "track" or "media":
                   track  → compositional function within a shot Version
                            (primary/matte/background etc., L01/L02/L03 in Flame)
                   media  → pipeline stage that produced the media atom
                            (raw/grade/denoise/prep/roto/comp)
    """
    __tablename__ = "registry_roles"

    key        = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name       = Column(String(128), nullable=False, unique=True)
    label      = Column(String(256), nullable=False)
    role_class = Column(String(32),  nullable=False, default="track")
    order      = Column(Integer, nullable=False, default=0)
    protected  = Column(Boolean, nullable=False, default=False)

    # Flexible storage for path_template, aliases, and future fields
    attributes = Column(JSONB, nullable=False, default=dict)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("ix_registry_roles_name", "name"),
    )

    def __repr__(self) -> str:
        return f"<DBRole {self.name!r} key={self.key!s:.8}...>"


class DBRelationshipType(Base):
    """A relationship type definition in the registry.

    key   — stable UUID. Stored in Relationship.rel_key. Never changes.
    name  — canonical string name. Can be renamed.
    label — display name. Can change freely.
    """
    __tablename__ = "registry_relationship_types"

    key           = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name          = Column(String(128), nullable=False, unique=True)
    label         = Column(String(256), nullable=False)
    description   = Column(Text, nullable=False, default="")
    directionality = Column(String(4), nullable=False, default="→")
    protected     = Column(Boolean, nullable=False, default=False)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("ix_registry_rel_types_name", "name"),
    )

    def __repr__(self) -> str:
        return f"<DBRelationshipType {self.name!r} key={self.key!s:.8}...>"


# ─────────────────────────────────────────────────────────────
# Projects (top-level containers — separate table for fast lookup)
# ─────────────────────────────────────────────────────────────

class DBProject(Base):
    """Top-level project container.

    Separate from the general entities table because every query touches
    project context. Worth the fast path.
    """
    __tablename__ = "projects"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name       = Column(String(256), nullable=False)
    code       = Column(String(64),  nullable=False)
    attributes = Column(JSONB, nullable=False, default=dict)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    entities  = relationship("DBEntity",   back_populates="project", lazy="dynamic")
    locations = relationship("DBLocation", back_populates="project", lazy="dynamic")

    __table_args__ = (
        Index("ix_projects_code", "code"),
        UniqueConstraint("code", name="uq_projects_code"),
    )

    def __repr__(self) -> str:
        return f"<DBProject {self.name!r} ({self.code})>"


# ─────────────────────────────────────────────────────────────
# Entities (all non-project entity types in one table)
# ─────────────────────────────────────────────────────────────

ENTITY_TYPES = frozenset({
    "sequence", "shot", "asset", "version", "media", "layer", "stack"
})


class DBEntity(Base):
    """All non-project entity types in a single table.

    entity_type discriminates: sequence, shot, asset, version, media,
    layer, stack.

    Type-specific fields live in the JSONB `attributes` column rather
    than per-type tables. This keeps the schema simple while retaining
    full queryability via Postgres JSONB operators.

    Common structured fields that are queried frequently (name, status,
    project_id) are promoted to real columns with indexes.

    Attributes column contents by entity_type:

      sequence:  frame_rate, duration_tc

      shot:      cut_in, cut_out, sequence_id

      asset:     asset_type

      version:   The process/event record — equivalent to a git commit.
                 The batch file IS the version; its location is the .batch file.
                 Fields: version_number (iteration counter, 1-based for published
                 comps), published_at, published_by, shot_id, sequence_name.
                 NOT: plate metadata — that belongs on media entities.

      media:     The atomic content unit — immutable once created.
                 Fields: role (media role: raw/grade/denoise/prep/roto/comp),
                 generation (0=raw, 1+=derived), kind (plate/render/clip/batch),
                 format, colorspace, bit_depth, width, height, fps,
                 frame_range {start, end}, tape_name, source_tc_in, source_tc_out.
                 Does NOT carry version_id — the relationship graph owns that link
                 via consumes/produces edges on the Version entity.

      layer:     role_key, order, stack_id, version_id

      stack:     shot_id
    """
    __tablename__ = "entities"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    entity_type = Column(String(32), nullable=False)
    project_id  = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,   # Some entities (loose versions) may not have project context
        index=True,
    )
    name        = Column(String(256), nullable=True)   # Not all entities have names
    status      = Column(String(64), nullable=True)
    attributes  = Column(JSONB, nullable=False, default=dict)

    created_at  = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at  = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    project        = relationship("DBProject",  back_populates="entities")
    locations_fk   = relationship("DBLocation", back_populates="entity",  lazy="dynamic",
                                  foreign_keys="DBLocation.entity_id")
    relationships_as_source = relationship(
        "DBRelationship", back_populates="source",
        foreign_keys="DBRelationship.source_id",
        lazy="dynamic",
    )
    relationships_as_target = relationship(
        "DBRelationship", back_populates="target",
        foreign_keys="DBRelationship.target_id",
        lazy="dynamic",
    )

    __table_args__ = (
        CheckConstraint(
            f"entity_type IN ({', '.join(repr(t) for t in sorted(ENTITY_TYPES))})",
            name="ck_entities_type",
        ),
        Index("ix_entities_project_type",  "project_id", "entity_type"),
        Index("ix_entities_type_name",     "entity_type", "name"),
        Index("ix_entities_status",        "status"),
        # GIN index on JSONB attributes for fast containment queries
        # e.g. WHERE attributes @> '{"sequence_id": "..."}'
        Index("ix_entities_attributes",    "attributes", postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        return f"<DBEntity {self.entity_type} {self.name or self.id!s:.8}...>"


# ─────────────────────────────────────────────────────────────
# Locations
# ─────────────────────────────────────────────────────────────

class DBLocation(Base):
    """A path-based address for a project or entity.

    Multiple locations per entity are supported — local, network, cloud,
    archive all pointing at the same media.
    """
    __tablename__ = "locations"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)

    # Owner — either a project or an entity, never both
    project_id   = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    entity_id    = Column(
        UUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    path         = Column(Text, nullable=False)
    storage_type = Column(String(32), nullable=False, default="local")
    priority     = Column(Integer, nullable=False, default=0)
    exists       = Column(Boolean, nullable=True)   # None = unchecked
    attributes   = Column(JSONB, nullable=False, default=dict)

    created_at   = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    checked_at   = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    project = relationship("DBProject", back_populates="locations")
    entity  = relationship("DBEntity",  back_populates="locations_fk",
                           foreign_keys=[entity_id])

    __table_args__ = (
        CheckConstraint(
            "(project_id IS NOT NULL)::int + (entity_id IS NOT NULL)::int = 1",
            name="ck_locations_owner",
        ),
        CheckConstraint(
            "storage_type IN ('local', 'network', 'cloud', 'archive', 'clip')",
            name="ck_locations_storage_type",
        ),
        Index("ix_locations_path",     "path"),
        Index("ix_locations_priority", "entity_id", "priority"),
    )

    def __repr__(self) -> str:
        return f"<DBLocation {self.storage_type} {self.path!r}>"


# ─────────────────────────────────────────────────────────────
# Relationships (dependency graph edges)
# ─────────────────────────────────────────────────────────────

class DBRelationship(Base):
    """A directed edge in the dependency graph.

    source → target via rel_type_key.

    rel_type_key references registry_relationship_types.key.
    Not a FK constraint because the registry table is managed
    separately and we don't want cascade deletes killing graph edges.
    Application-layer orphan protection handles this.
    """
    __tablename__ = "relationships"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    source_id    = Column(
        UUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_id    = Column(
        UUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rel_type_key = Column(UUID(as_uuid=True), nullable=False, index=True)
    attributes   = Column(JSONB, nullable=False, default=dict)

    created_at   = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships (ORM)
    source = relationship(
        "DBEntity", back_populates="relationships_as_source",
        foreign_keys=[source_id],
    )
    target = relationship(
        "DBEntity", back_populates="relationships_as_target",
        foreign_keys=[target_id],
    )

    __table_args__ = (
        # Prevent duplicate edges of the same type between the same pair
        UniqueConstraint("source_id", "target_id", "rel_type_key",
                         name="uq_relationships_edge"),
        # Composite index for graph traversal queries
        Index("ix_relationships_source_type", "source_id", "rel_type_key"),
        Index("ix_relationships_target_type", "target_id", "rel_type_key"),
    )

    def __repr__(self) -> str:
        return (
            f"<DBRelationship "
            f"{self.source_id!s:.8}... → {self.target_id!s:.8}... "
            f"({self.rel_type_key!s:.8}...)>"
        )


# ─────────────────────────────────────────────────────────────
# Events (append-only audit + change log)
# ─────────────────────────────────────────────────────────────

EVENT_TYPES = frozenset({
    # Registry events
    "role.registered", "role.renamed", "role.label_changed",
    "role.updated", "role.deleted", "role.migrated",
    "relationship_type.registered", "relationship_type.renamed",
    "relationship_type.deleted", "relationship_type.migrated",
    # Entity lifecycle
    "project.created", "project.updated",
    "entity.created", "entity.updated", "entity.status_changed",
    # Graph events
    "location.added", "location.updated", "location.removed",
    "relationship.created", "relationship.removed",
    # Pipeline events
    "version.published",     # A Version (comp/batch) was published to a Shot
    "media.ingested",        # A raw media atom arrived via ingest
    "media.derived",         # A media atom was derived from another (lineage hop)
    "media.registered",      # A media atom was registered from a publish hook
    "entity.deleted",
    "client.connected", "client.disconnected",
})


class DBEvent(Base):
    """Append-only event log.

    Every state change produces an event. Events are never updated or
    deleted. This provides:
      - Full audit trail ("who changed this shot status and when?")
      - Replay capability (reconstruct state at any point in time)
      - Change propagation (server reads new events and notifies subscribers)
      - Debugging ("what happened in the last 10 minutes?")

    payload is the complete event data — enough to reconstruct the change
    without needing to join other tables.
    """
    __tablename__ = "events"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    event_type  = Column(String(64), nullable=False)

    # Who/what caused this event
    session_id  = Column(UUID(as_uuid=True), nullable=True, index=True)
    client_name = Column(String(128), nullable=True)  # "flame_a", "mcp_claude", etc.

    # What was affected
    project_id  = Column(UUID(as_uuid=True), nullable=True, index=True)
    entity_id   = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Full event data
    payload     = Column(JSONB, nullable=False, default=dict)

    occurred_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    __table_args__ = (
        Index("ix_events_type_time",    "event_type", "occurred_at"),
        Index("ix_events_project_time", "project_id", "occurred_at"),
        Index("ix_events_entity_time",  "entity_id",  "occurred_at"),
    )

    def __repr__(self) -> str:
        return f"<DBEvent {self.event_type} at {self.occurred_at}>"


# ─────────────────────────────────────────────────────────────
# Sessions (connected client tracking — server-managed)
# ─────────────────────────────────────────────────────────────

class DBSession(Base):
    """A period of active connection for a client endpoint.

    Written by the server when a client connects/disconnects.
    Used for audit, debugging, and understanding who is currently online.
    """
    __tablename__ = "sessions"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    client_name  = Column(String(128), nullable=False)
    endpoint_type = Column(String(64), nullable=True)  # "flame", "mcp", "maya", etc.
    host         = Column(String(256), nullable=True)
    capabilities = Column(JSONB, nullable=False, default=dict)

    connected_at    = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    disconnected_at = Column(DateTime(timezone=True), nullable=True)
    last_seen_at    = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_sessions_client",       "client_name"),
        Index("ix_sessions_connected_at", "connected_at"),
    )

    @property
    def is_active(self) -> bool:
        return self.disconnected_at is None

    def __repr__(self) -> str:
        status = "active" if self.is_active else "closed"
        return f"<DBSession {self.client_name!r} [{status}]>"
