"""
forge-bridge core traits.

Traits are cross-cutting capabilities that any entity can possess.
Rather than baking versioning or pathing into specific entity types,
those behaviors are defined here once. Any entity that needs them
declares that it carries the trait and gets the behavior for free.

Traits:
    Versionable  — entity can exist as a series of discrete iterations
    Locatable    — entity has one or more path-based addresses
    Relational   — entity can declare and traverse relationships
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from forge_bridge.core.entities import BridgeEntity


# ─────────────────────────────────────────────────────────────
# Location
# ─────────────────────────────────────────────────────────────

class StorageType(str, Enum):
    LOCAL   = "local"
    NETWORK = "network"
    CLOUD   = "cloud"
    ARCHIVE = "archive"


@dataclass
class Location:
    """A path-based address for a Locatable entity.

    A single entity may have multiple Locations — a local cache path,
    a network share path, and a cloud bucket path all pointing at the
    same underlying media. Bridge tracks all of them.
    """
    path: str
    storage_type: StorageType = StorageType.LOCAL
    exists: Optional[bool] = None        # None = not yet checked
    priority: int = 0                    # higher = more preferred
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.storage_type, str):
            self.storage_type = StorageType(self.storage_type)

    def check_exists(self) -> bool:
        """Check whether the path currently exists on disk."""
        import os
        self.exists = os.path.exists(self.path)
        return self.exists

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "storage_type": self.storage_type.value,
            "exists": self.exists,
            "priority": self.priority,
            "metadata": self.metadata,
        }


# ─────────────────────────────────────────────────────────────
# Relationship
# ─────────────────────────────────────────────────────────────

class RelationshipType(str, Enum):
    MEMBER_OF    = "member_of"      # Shot member_of Sequence
    VERSION_OF   = "version_of"     # Version version_of Shot
    DERIVED_FROM = "derived_from"   # Render derived_from source plate
    REFERENCES   = "references"     # Layer references Version
    PEER_OF      = "peer_of"        # Layer peer_of Layer (within Stack)


@dataclass
class Relationship:
    """A declared relationship between two entities.

    Relationships are directional: source → target.
    The type describes the nature of the connection.
    """
    source_id: uuid.UUID
    target_id: uuid.UUID
    relationship_type: RelationshipType
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        if isinstance(self.relationship_type, str):
            self.relationship_type = RelationshipType(self.relationship_type)
        if isinstance(self.source_id, str):
            self.source_id = uuid.UUID(self.source_id)
        if isinstance(self.target_id, str):
            self.target_id = uuid.UUID(self.target_id)

    def to_dict(self) -> dict:
        return {
            "source_id": str(self.source_id),
            "target_id": str(self.target_id),
            "relationship_type": self.relationship_type.value,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


# ─────────────────────────────────────────────────────────────
# Traits (mixin classes)
# ─────────────────────────────────────────────────────────────

class Versionable:
    """Trait: this entity can exist as a series of discrete iterations.

    Any Versionable entity tracks its own version history.
    Version numbers are monotonically increasing integers.
    """

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

    @property
    def is_versionable(self) -> bool:
        return True

    def get_version_info(self) -> dict:
        """Return version metadata for this entity."""
        return {
            "version_number": getattr(self, "version_number", None),
            "is_latest": getattr(self, "is_latest", None),
        }


class Locatable:
    """Trait: this entity has one or more path-based addresses.

    A single Locatable entity may have multiple simultaneous Locations
    — local cache, network share, cloud bucket. Bridge tracks all of them.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hasattr(self, "_locations"):
            self._locations: list[Location] = []

    @property
    def is_locatable(self) -> bool:
        return True

    def add_location(
        self,
        path: str,
        storage_type: StorageType | str = StorageType.LOCAL,
        priority: int = 0,
        **metadata,
    ) -> Location:
        """Register a new location for this entity."""
        loc = Location(
            path=path,
            storage_type=StorageType(storage_type) if isinstance(storage_type, str) else storage_type,
            priority=priority,
            metadata=metadata,
        )
        self._locations.append(loc)
        self._locations.sort(key=lambda l: l.priority, reverse=True)
        return loc

    def get_locations(self) -> list[Location]:
        """Return all known locations, highest priority first."""
        return list(self._locations)

    def get_primary_location(self) -> Optional[Location]:
        """Return the highest-priority location, or None if none registered."""
        return self._locations[0] if self._locations else None

    def resolve_path(self) -> Optional[str]:
        """Return the best available path given current system state.

        Checks existence in priority order and returns the first
        path that actually exists. Falls back to the highest-priority
        path if none are confirmed to exist.
        """
        for loc in self._locations:
            if loc.check_exists():
                return loc.path
        # Nothing confirmed — return primary path anyway (may be offline/archive)
        primary = self.get_primary_location()
        return primary.path if primary else None

    def get_location_dicts(self) -> list[dict]:
        return [loc.to_dict() for loc in self._locations]


class Relational:
    """Trait: this entity can declare and traverse relationships.

    The dependency graph is built from these relationships. Bridge
    parses incoming data and creates relationships automatically from
    the natural structure of the data — no manual declaration needed.
    Manual declaration is also supported for cases where explicit
    relationships need to be asserted.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hasattr(self, "_relationships"):
            self._relationships: list[Relationship] = []

    @property
    def is_relational(self) -> bool:
        return True

    def add_relationship(
        self,
        target_id: uuid.UUID | str,
        relationship_type: RelationshipType | str,
        **metadata,
    ) -> Relationship:
        """Declare a relationship from this entity to another."""
        entity_id = getattr(self, "id", None)
        if entity_id is None:
            raise ValueError("Entity must have an id to declare relationships")

        rel = Relationship(
            source_id=entity_id,
            target_id=uuid.UUID(str(target_id)) if isinstance(target_id, str) else target_id,
            relationship_type=relationship_type,
            metadata=metadata,
        )
        self._relationships.append(rel)
        return rel

    def get_relationships(
        self,
        relationship_type: Optional[RelationshipType | str] = None,
    ) -> list[Relationship]:
        """Return relationships, optionally filtered by type."""
        if relationship_type is None:
            return list(self._relationships)
        rtype = RelationshipType(relationship_type) if isinstance(relationship_type, str) else relationship_type
        return [r for r in self._relationships if r.relationship_type == rtype]

    def get_relationship_dicts(self) -> list[dict]:
        return [r.to_dict() for r in self._relationships]
