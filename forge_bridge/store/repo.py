"""
forge-bridge repository layer.

All database reads and writes go through Repository classes.
Nothing outside this module writes SQL directly.

The repository pattern gives us:
  - One place to change query strategy (indexes, caching, etc.)
  - Clean separation between domain objects (core/) and persistence (store/)
  - Testability — repositories can be swapped for in-memory fakes in tests

Each repository takes an AsyncSession and operates within whatever
transaction the caller manages. The server wraps calls in sessions
via store.session.get_session().

Repositories translate between:
  - DB models    (store/models.py  — what Postgres stores)
  - Core objects (core/entities.py — what the rest of the system uses)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional, Sequence

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from forge_bridge.core.entities import (
    Asset, BridgeEntity, Layer, Media, Project as CoreProject,
    Sequence as CoreSequence, Shot, Stack, Version,
)
from forge_bridge.core.registry import Registry, RoleDefinition, RelationshipTypeDef
from forge_bridge.core.traits import Relationship
from forge_bridge.core.vocabulary import FrameRange, Role, Status, Timecode
from forge_bridge.store.models import (
    DBEntity, DBEvent, DBLocation, DBProject,
    DBRelationship, DBRelationshipType, DBRole, DBSession,
)

from fractions import Fraction


# ─────────────────────────────────────────────────────────────
# Registry Repository
# ─────────────────────────────────────────────────────────────

class RegistryRepo:
    """Persist and load the bridge registry (roles + relationship types).

    The registry is loaded once at server startup and kept in memory.
    Changes are written through to Postgres and broadcast as events.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    # ── Roles ─────────────────────────────────────────────────

    async def save_role(self, role_def: RoleDefinition) -> DBRole:
        """Insert or update a role record."""
        existing = await self.session.get(DBRole, role_def.key)
        role = role_def.role

        attrs = {
            "path_template": role.path_template,
            "aliases":       dict(role.aliases),
        }

        if existing:
            existing.name      = role.name
            existing.label     = role.label or role.name
            existing.order     = role.order
            existing.attributes = attrs
            return existing
        else:
            db_role = DBRole(
                key=role_def.key,
                name=role.name,
                label=role.label or role.name,
                order=role.order,
                attributes=attrs,
            )
            self.session.add(db_role)
            return db_role

    async def delete_role(self, key: uuid.UUID) -> None:
        await self.session.execute(
            delete(DBRole).where(DBRole.key == key)
        )

    async def load_all_roles(self) -> list[DBRole]:
        result = await self.session.execute(select(DBRole).order_by(DBRole.order))
        return list(result.scalars().all())

    async def get_role(self, key: uuid.UUID) -> DBRole | None:
        return await self.session.get(DBRole, key)

    # ── Relationship types ────────────────────────────────────

    async def save_relationship_type(self, typedef: RelationshipTypeDef) -> DBRelationshipType:
        existing = await self.session.get(DBRelationshipType, typedef.key)

        if existing:
            existing.name          = typedef.name
            existing.label         = typedef.label
            existing.description   = typedef.description
            existing.directionality = typedef.directionality
            return existing
        else:
            db_type = DBRelationshipType(
                key=typedef.key,
                name=typedef.name,
                label=typedef.label,
                description=typedef.description,
                directionality=typedef.directionality,
            )
            self.session.add(db_type)
            return db_type

    async def delete_relationship_type(self, key: uuid.UUID) -> None:
        await self.session.execute(
            delete(DBRelationshipType).where(DBRelationshipType.key == key)
        )

    async def load_all_relationship_types(self) -> list[DBRelationshipType]:
        result = await self.session.execute(select(DBRelationshipType))
        return list(result.scalars().all())

    async def restore_registry(self) -> Registry:
        """Load the full registry state from Postgres.

        Called at server startup to restore custom roles and relationship
        types that were registered in previous sessions.
        """
        registry = Registry(seed_defaults=False)

        # Restore roles
        roles = await self.load_all_roles()
        for db_role in roles:
            attrs = db_role.attributes or {}
            role = Role(
                name=db_role.name,
                label=db_role.label,
                order=db_role.order,
                path_template=attrs.get("path_template"),
                aliases=attrs.get("aliases", {}),
            )
            registry.roles.register(
                db_role.name,
                role=role,
                key=db_role.key,
                protected=db_role.protected,
            )

        # Restore relationship types
        rel_types = await self.load_all_relationship_types()
        for db_type in rel_types:
            registry.relationships.register(
                db_type.name,
                label=db_type.label,
                description=db_type.description,
                directionality=db_type.directionality,
                key=db_type.key,
                protected=db_type.protected,
            )

        return registry


# ─────────────────────────────────────────────────────────────
# Project Repository
# ─────────────────────────────────────────────────────────────

class ProjectRepo:
    """Persist and load Project entities."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, project: CoreProject) -> DBProject:
        existing = await self.session.get(DBProject, project.id)

        if existing:
            existing.name       = project.name
            existing.code       = project.code
            existing.attributes = project.metadata
            return existing
        else:
            db_proj = DBProject(
                id=project.id,
                name=project.name,
                code=project.code,
                attributes=project.metadata,
            )
            self.session.add(db_proj)
            return db_proj

    async def get(self, project_id: uuid.UUID) -> CoreProject | None:
        db_proj = await self.session.get(DBProject, project_id)
        if db_proj is None:
            return None
        return self._to_core(db_proj)

    async def get_by_code(self, code: str) -> CoreProject | None:
        result = await self.session.execute(
            select(DBProject).where(DBProject.code == code)
        )
        db_proj = result.scalar_one_or_none()
        return self._to_core(db_proj) if db_proj else None

    async def list_all(self) -> list[CoreProject]:
        result = await self.session.execute(
            select(DBProject).order_by(DBProject.name)
        )
        return [self._to_core(p) for p in result.scalars().all()]

    async def delete(self, project_id: uuid.UUID) -> None:
        await self.session.execute(
            delete(DBProject).where(DBProject.id == project_id)
        )

    @staticmethod
    def _to_core(db: DBProject) -> CoreProject:
        p = CoreProject.__new__(CoreProject)
        BridgeEntity.__init__(p, id=db.id, metadata=db.attributes or {})
        p.name = db.name
        p.code = db.code
        return p


# ─────────────────────────────────────────────────────────────
# Entity Repository
# ─────────────────────────────────────────────────────────────

class EntityRepo:
    """Persist and load all non-project entities.

    Translates between core entity objects and the single DBEntity table.
    Entity-specific attributes are serialized to/from the JSONB column.
    """

    def __init__(self, session: AsyncSession, registry: Registry):
        self.session  = session
        self.registry = registry

    async def save(
        self,
        entity: BridgeEntity,
        project_id: uuid.UUID | None = None,
    ) -> DBEntity:
        """Insert or update an entity record."""
        entity_type = entity.entity_type
        attrs       = self._attrs_to_dict(entity)
        name        = getattr(entity, "name", None)
        status_val  = None

        if hasattr(entity, "status"):
            status_val = entity.status.value if hasattr(entity.status, "value") else str(entity.status)

        existing = await self.session.get(DBEntity, entity.id)

        if existing:
            existing.name       = name
            existing.status     = status_val
            existing.attributes = attrs
            if project_id:
                existing.project_id = project_id
            return existing
        else:
            db_entity = DBEntity(
                id=entity.id,
                entity_type=entity_type,
                project_id=project_id,
                name=name,
                status=status_val,
                attributes=attrs,
            )
            self.session.add(db_entity)
            return db_entity

    async def get(self, entity_id: uuid.UUID) -> BridgeEntity | None:
        db_entity = await self.session.get(DBEntity, entity_id)
        if db_entity is None:
            return None
        return self._to_core(db_entity)

    async def list_by_type(
        self,
        entity_type: str,
        project_id: uuid.UUID | None = None,
    ) -> list[BridgeEntity]:
        stmt = select(DBEntity).where(DBEntity.entity_type == entity_type)
        if project_id:
            stmt = stmt.where(DBEntity.project_id == project_id)
        stmt = stmt.order_by(DBEntity.name)
        result = await self.session.execute(stmt)
        return [self._to_core(e) for e in result.scalars().all()]

    async def find_by_attribute(
        self,
        entity_type: str,
        attribute_filter: dict,
        project_id: uuid.UUID | None = None,
    ) -> list[BridgeEntity]:
        """Find entities matching a JSONB attribute filter.

        Example:
            await repo.find_by_attribute(
                "layer",
                {"role_key": str(primary_role_key)},
                project_id=project.id,
            )
        """
        from sqlalchemy import cast
        from sqlalchemy.dialects.postgresql import JSONB as PGJSONB
        stmt = (
            select(DBEntity)
            .where(DBEntity.entity_type == entity_type)
            .where(DBEntity.attributes.contains(attribute_filter))
        )
        if project_id:
            stmt = stmt.where(DBEntity.project_id == project_id)
        result = await self.session.execute(stmt)
        return [self._to_core(e) for e in result.scalars().all()]

    async def delete(self, entity_id: uuid.UUID) -> None:
        await self.session.execute(
            delete(DBEntity).where(DBEntity.id == entity_id)
        )

    # ── Serialization ─────────────────────────────────────────

    def _attrs_to_dict(self, entity: BridgeEntity) -> dict:
        """Extract type-specific attributes for JSONB storage.

        Typed fields are extracted from the entity's formal properties.
        entity.metadata (the open key/value store) is merged on top so
        arbitrary pipeline attributes (kind, colour_space, tape_name, etc.)
        survive the round-trip without requiring schema changes.
        """
        t = entity.entity_type
        # Start with metadata so typed fields win on collision
        a = dict(entity.metadata or {})

        if t == "sequence":
            seq = entity
            a["frame_rate"]  = str(getattr(seq, "frame_rate", "24"))
            a["duration_tc"] = str(seq.duration) if getattr(seq, "duration", None) else None

        elif t == "shot":
            shot = entity
            a["cut_in"]      = str(shot.cut_in)  if getattr(shot, "cut_in",  None) else None
            a["cut_out"]     = str(shot.cut_out) if getattr(shot, "cut_out", None) else None
            a["sequence_id"] = str(shot.sequence_id) if getattr(shot, "sequence_id", None) else None

        elif t == "asset":
            a["asset_type"] = getattr(entity, "asset_type", "generic")

        elif t == "version":
            v = entity
            a["version_number"] = v.version_number
            a["parent_id"]      = str(v.parent_id)  if getattr(v, "parent_id",  None) else None
            a["parent_type"]    = getattr(v, "parent_type", "shot")
            a["created_by"]     = getattr(v, "created_by", None)

        elif t == "media":
            m = entity
            a["format"]     = m.format
            a["resolution"] = getattr(m, "resolution", None)
            a["colorspace"] = getattr(m, "colorspace", None)
            a["bit_depth"]  = getattr(m, "bit_depth",  None)
            a["version_id"] = str(m.version_id) if getattr(m, "version_id", None) else None
            if getattr(m, "frame_range", None):
                a["frame_range"] = m.frame_range.to_dict()

        elif t == "layer":
            lay = entity
            a["role_key"]   = str(lay.role_key)
            a["order"]      = lay.order
            a["stack_id"]   = str(lay.stack_id)   if getattr(lay, "stack_id",   None) else None
            a["version_id"] = str(lay.version_id) if getattr(lay, "version_id", None) else None

        elif t == "stack":
            stk = entity
            a["shot_id"] = str(stk.shot_id) if getattr(stk, "shot_id", None) else None

        return a

    def _to_core(self, db: DBEntity) -> BridgeEntity:
        """Reconstruct a core entity from a DB record."""
        t = db.entity_type
        a = db.attributes or {}

        if t == "sequence":
            e = CoreSequence.__new__(CoreSequence)
            BridgeEntity.__init__(e, id=db.id, metadata={})
            e.name       = db.name
            e.project_id = db.project_id
            e.frame_rate = Fraction(a.get("frame_rate", "24"))
            e.duration   = (
                Timecode.from_string(a["duration_tc"])
                if a.get("duration_tc") else None
            )

        elif t == "shot":
            e = Shot.__new__(Shot)
            BridgeEntity.__init__(e, id=db.id, metadata={})
            e.name        = db.name
            e.sequence_id = uuid.UUID(a["sequence_id"]) if a.get("sequence_id") else None
            e.cut_in  = Timecode.from_string(a["cut_in"])  if a.get("cut_in")  else None
            e.cut_out = Timecode.from_string(a["cut_out"]) if a.get("cut_out") else None
            e.status  = Status.from_string(db.status) if db.status else Status.PENDING

        elif t == "asset":
            e = Asset.__new__(Asset)
            BridgeEntity.__init__(e, id=db.id, metadata={})
            e.name       = db.name
            e.asset_type = a.get("asset_type", "generic")
            e.project_id = db.project_id
            e.status     = Status.from_string(db.status) if db.status else Status.PENDING

        elif t == "version":
            e = Version.__new__(Version)
            BridgeEntity.__init__(e, id=db.id, metadata={})
            e.version_number = a.get("version_number", 0)
            e.parent_id  = uuid.UUID(a["parent_id"])  if a.get("parent_id")  else None
            e.parent_type = a.get("parent_type", "shot")
            e.created_by  = a.get("created_by")
            e.status      = Status.from_string(db.status) if db.status else Status.PENDING

        elif t == "media":
            e = Media.__new__(Media)
            BridgeEntity.__init__(e, id=db.id, metadata={})
            e.format     = a.get("format", "unknown")
            e.resolution = a.get("resolution")
            e.colorspace = a.get("colorspace")
            e.bit_depth  = a.get("bit_depth")
            e.version_id = uuid.UUID(a["version_id"]) if a.get("version_id") else None
            fr_data      = a.get("frame_range")
            e.frame_range = (
                FrameRange(fr_data["start"], fr_data["end"], Fraction(fr_data["fps"]))
                if fr_data else None
            )
            e.status     = Status.from_string(db.status) if db.status else Status.PENDING

        elif t == "layer":
            from forge_bridge.core.traits import get_default_registry
            reg = self.registry or get_default_registry()
            e = Layer.__new__(Layer)
            BridgeEntity.__init__(e, id=db.id, metadata={})
            e._registry = reg
            # Store raw UUID — don't trigger registry lookup during deserialization
            e.role_key   = uuid.UUID(a["role_key"]) if a.get("role_key") else None
            e.order      = a.get("order", 0)
            e.stack_id   = uuid.UUID(a["stack_id"])   if a.get("stack_id")   else None
            e.version_id = uuid.UUID(a["version_id"]) if a.get("version_id") else None

        elif t == "stack":
            e = Stack.__new__(Stack)
            BridgeEntity.__init__(e, id=db.id, metadata={})
            e.shot_id  = uuid.UUID(a["shot_id"]) if a.get("shot_id") else None
            e._layers  = []

        else:
            e = BridgeEntity.__new__(BridgeEntity)
            BridgeEntity.__init__(e, id=db.id, metadata=a)

        return e


# ─────────────────────────────────────────────────────────────
# Location Repository
# ─────────────────────────────────────────────────────────────

class LocationRepo:
    """Persist and load file path locations for entities and projects."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_entity_locations(self, entity: BridgeEntity) -> None:
        """Write all locations for an entity, replacing existing records."""
        await self.session.execute(
            delete(DBLocation).where(DBLocation.entity_id == entity.id)
        )
        for loc in entity.get_locations():
            db_loc = DBLocation(
                entity_id=entity.id,
                path=loc.path,
                storage_type=loc.storage_type.value,
                priority=loc.priority,
                exists=loc.exists,
                attributes=loc.metadata,
            )
            self.session.add(db_loc)

    async def get_entity_locations(self, entity_id: uuid.UUID) -> list[DBLocation]:
        result = await self.session.execute(
            select(DBLocation)
            .where(DBLocation.entity_id == entity_id)
            .order_by(DBLocation.priority.desc())
        )
        return list(result.scalars().all())


# ─────────────────────────────────────────────────────────────
# Relationship Repository
# ─────────────────────────────────────────────────────────────

class RelationshipRepo:
    """Persist and load dependency graph edges."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, rel: Relationship) -> DBRelationship:
        """Insert a relationship edge if it doesn't already exist."""
        result = await self.session.execute(
            select(DBRelationship).where(
                DBRelationship.source_id    == rel.source_id,
                DBRelationship.target_id    == rel.target_id,
                DBRelationship.rel_type_key == rel.rel_key,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        db_rel = DBRelationship(
            source_id=rel.source_id,
            target_id=rel.target_id,
            rel_type_key=rel.rel_key,
            attributes=rel.metadata,
        )
        self.session.add(db_rel)
        return db_rel

    async def get_outgoing(
        self,
        source_id: uuid.UUID,
        rel_type_key: uuid.UUID | None = None,
    ) -> list[DBRelationship]:
        """Return all edges leaving source_id, optionally filtered by type."""
        stmt = select(DBRelationship).where(DBRelationship.source_id == source_id)
        if rel_type_key:
            stmt = stmt.where(DBRelationship.rel_type_key == rel_type_key)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_incoming(
        self,
        target_id: uuid.UUID,
        rel_type_key: uuid.UUID | None = None,
    ) -> list[DBRelationship]:
        """Return all edges arriving at target_id, optionally filtered by type."""
        stmt = select(DBRelationship).where(DBRelationship.target_id == target_id)
        if rel_type_key:
            stmt = stmt.where(DBRelationship.rel_type_key == rel_type_key)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_dependents(self, entity_id: uuid.UUID) -> list[uuid.UUID]:
        """Return IDs of all entities that have a relationship pointing TO entity_id.

        This is the blast radius query — "what depends on this?"
        """
        result = await self.session.execute(
            select(DBRelationship.source_id)
            .where(DBRelationship.target_id == entity_id)
        )
        return [row[0] for row in result.all()]

    async def get_dependencies(self, entity_id: uuid.UUID) -> list[uuid.UUID]:
        """Return IDs of all entities that entity_id points TO.

        "What does this depend on?"
        """
        result = await self.session.execute(
            select(DBRelationship.target_id)
            .where(DBRelationship.source_id == entity_id)
        )
        return [row[0] for row in result.all()]

    async def delete(
        self,
        source_id: uuid.UUID,
        target_id: uuid.UUID,
        rel_type_key: uuid.UUID,
    ) -> None:
        await self.session.execute(
            delete(DBRelationship).where(
                DBRelationship.source_id    == source_id,
                DBRelationship.target_id    == target_id,
                DBRelationship.rel_type_key == rel_type_key,
            )
        )


# ─────────────────────────────────────────────────────────────
# Event Repository
# ─────────────────────────────────────────────────────────────

class EventRepo:
    """Append-only event log. Nothing here updates or deletes records."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def append(
        self,
        event_type: str,
        payload: dict,
        *,
        session_id: uuid.UUID | None = None,
        client_name: str | None = None,
        project_id: uuid.UUID | None = None,
        entity_id: uuid.UUID | None = None,
    ) -> DBEvent:
        event = DBEvent(
            event_type=event_type,
            session_id=session_id,
            client_name=client_name,
            project_id=project_id,
            entity_id=entity_id,
            payload=payload,
        )
        self.session.add(event)
        return event

    async def get_recent(
        self,
        limit: int = 100,
        event_type: str | None = None,
        project_id: uuid.UUID | None = None,
        entity_id: uuid.UUID | None = None,
        since: datetime | None = None,
    ) -> list[DBEvent]:
        stmt = select(DBEvent).order_by(DBEvent.occurred_at.desc())
        if event_type:
            stmt = stmt.where(DBEvent.event_type == event_type)
        if project_id:
            stmt = stmt.where(DBEvent.project_id == project_id)
        if entity_id:
            stmt = stmt.where(DBEvent.entity_id == entity_id)
        if since:
            stmt = stmt.where(DBEvent.occurred_at >= since)
        stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_since_sequence(
        self,
        last_event_id: uuid.UUID,
        limit: int = 500,
    ) -> list[DBEvent]:
        """Return events that occurred after the given event ID.

        Used by clients reconnecting after a disconnect to catch up on
        missed events without replaying the entire log.
        """
        anchor = await self.session.get(DBEvent, last_event_id)
        if anchor is None:
            return []
        stmt = (
            select(DBEvent)
            .where(DBEvent.occurred_at > anchor.occurred_at)
            .order_by(DBEvent.occurred_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


# ─────────────────────────────────────────────────────────────
# Session Repository (connected clients)
# ─────────────────────────────────────────────────────────────

class ClientSessionRepo:
    """Track connected client sessions."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def open(
        self,
        client_name: str,
        endpoint_type: str | None = None,
        host: str | None = None,
        capabilities: dict | None = None,
    ) -> DBSession:
        db_session = DBSession(
            client_name=client_name,
            endpoint_type=endpoint_type,
            host=host,
            capabilities=capabilities or {},
        )
        self.session.add(db_session)
        await self.session.flush()
        return db_session

    async def close(self, session_id: uuid.UUID) -> None:
        db_session = await self.session.get(DBSession, session_id)
        if db_session:
            db_session.disconnected_at = datetime.now(timezone.utc)

    async def heartbeat(self, session_id: uuid.UUID) -> None:
        db_session = await self.session.get(DBSession, session_id)
        if db_session:
            db_session.last_seen_at = datetime.now(timezone.utc)

    async def get_active(self) -> list[DBSession]:
        result = await self.session.execute(
            select(DBSession)
            .where(DBSession.disconnected_at.is_(None))
            .order_by(DBSession.connected_at)
        )
        return list(result.scalars().all())
