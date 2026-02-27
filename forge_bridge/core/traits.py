"""
forge-bridge core traits.

Traits are cross-cutting capabilities that any entity can possess.

Key design principle: entities store stable UUIDs (rel_key, role_key),
NOT names or enum values. Names are display artifacts looked up through
the registry at read time. This means:

  - Renaming a role/relationship type never breaks existing entities
  - The registry can track every reference and block orphaning deletions
  - No stale copies: there is one source of truth

System relationship type keys are constants defined here so both
traits.py and registry.py can import them without circular deps.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from forge_bridge.core.registry import Registry


# ─────────────────────────────────────────────────────────────
# System relationship type keys
# These UUIDs are permanent — do not change them between versions.
# registry.py imports these rather than redefining them.
# ─────────────────────────────────────────────────────────────

SYSTEM_REL_KEYS: dict[str, uuid.UUID] = {
    "member_of":    uuid.UUID("00000000-0000-0000-0000-000000000001"),
    "version_of":   uuid.UUID("00000000-0000-0000-0000-000000000002"),
    "derived_from": uuid.UUID("00000000-0000-0000-0000-000000000003"),
    "references":   uuid.UUID("00000000-0000-0000-0000-000000000004"),
    "peer_of":      uuid.UUID("00000000-0000-0000-0000-000000000005"),
    # Process graph — Version ↔ Media axes
    # consumes: Version → Media  (this media was an input to this process)
    # produces: Version → Media  (this media was created by this process)
    # The edge attributes carry compositional role when relevant:
    #   consumes.attributes = {"track_role": "primary", "layer_index": "L01"}
    "consumes":     uuid.UUID("00000000-0000-0000-0000-000000000006"),
    "produces":     uuid.UUID("00000000-0000-0000-0000-000000000007"),
}

# Reverse map for fallback name resolution without a registry
_SYSTEM_REL_NAMES: dict[uuid.UUID, str] = {v: k for k, v in SYSTEM_REL_KEYS.items()}


def _resolve_rel_key(name_or_key: str | uuid.UUID) -> uuid.UUID:
    """Resolve a name or UUID to a stable relationship type key.

    Accepts:
      - UUID instance              → returned as-is
      - UUID string                → parsed to UUID
      - System type name string    → looked up in SYSTEM_REL_KEYS

    For custom types, pass the UUID key directly or call
    registry.relationships.get_key("custom_name").
    """
    if isinstance(name_or_key, uuid.UUID):
        return name_or_key
    try:
        return uuid.UUID(name_or_key)
    except ValueError:
        pass
    key = SYSTEM_REL_KEYS.get(name_or_key)
    if key is None:
        raise ValueError(
            f"'{name_or_key}' is not a system relationship type. "
            f"For custom types pass the UUID key directly or use "
            f"registry.relationships.get_key('{name_or_key}')."
        )
    return key


# ─────────────────────────────────────────────────────────────
# Module-level default registry
# ─────────────────────────────────────────────────────────────

_default_registry: Optional[Registry] = None


def get_default_registry() -> Registry:
    """Return the module-level default registry, creating it if needed."""
    global _default_registry
    if _default_registry is None:
        from forge_bridge.core.registry import Registry
        _default_registry = Registry.default()
    return _default_registry


def set_default_registry(registry: Registry) -> None:
    """Replace the module-level default registry.

    Call at pipeline startup to use a configured registry (custom roles,
    renamed types, path templates, etc.) rather than built-in defaults.
    """
    global _default_registry
    _default_registry = registry


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

    A single entity may have multiple Locations (local, network, cloud)
    all pointing at the same underlying media.
    """
    path:         str
    storage_type: StorageType = StorageType.LOCAL
    exists:       Optional[bool] = None   # None = not yet checked
    priority:     int = 0                 # higher = preferred
    metadata:     dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.storage_type, str):
            self.storage_type = StorageType(self.storage_type)

    def check_exists(self) -> bool:
        import os
        self.exists = os.path.exists(self.path)
        return self.exists

    def to_dict(self) -> dict:
        return {
            "path":         self.path,
            "storage_type": self.storage_type.value,
            "exists":       self.exists,
            "priority":     self.priority,
            "metadata":     self.metadata,
        }


# ─────────────────────────────────────────────────────────────
# Relationship
# ─────────────────────────────────────────────────────────────

@dataclass
class Relationship:
    """A directed relationship between two entities.

    Stores rel_key (UUID) — the stable key into the relationship
    type registry — NOT the display name. This means renaming a
    relationship type in the registry never invalidates existing
    Relationship instances.

    To get the display name:
        rel.type_name()                          # uses default registry
        rel.type_name(registry=my_registry)      # uses specific registry
    """
    source_id:  uuid.UUID
    target_id:  uuid.UUID
    rel_key:    uuid.UUID
    metadata:   dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        if isinstance(self.source_id, str):
            self.source_id = uuid.UUID(self.source_id)
        if isinstance(self.target_id, str):
            self.target_id = uuid.UUID(self.target_id)
        if isinstance(self.rel_key, (str, uuid.UUID)):
            self.rel_key = _resolve_rel_key(self.rel_key)

    def type_name(self, registry: Optional[Registry] = None) -> str:
        """Return the current display name of this relationship type."""
        reg = registry or get_default_registry()
        try:
            return reg.relationships.get_by_key(self.rel_key).name
        except Exception:
            return _SYSTEM_REL_NAMES.get(self.rel_key, str(self.rel_key))

    def to_dict(self, registry: Optional[Registry] = None) -> dict:
        return {
            "source_id":  str(self.source_id),
            "target_id":  str(self.target_id),
            "rel_key":    str(self.rel_key),
            "type_name":  self.type_name(registry),
            "metadata":   self.metadata,
            "created_at": self.created_at.isoformat(),
        }


# ─────────────────────────────────────────────────────────────
# Traits
# ─────────────────────────────────────────────────────────────

class Versionable:
    """Trait: entity can exist as a series of discrete iterations."""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

    @property
    def is_versionable(self) -> bool:
        return True


class Locatable:
    """Trait: entity has one or more path-based addresses."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hasattr(self, "_locations"):
            self._locations: list[Location] = []

    @property
    def is_locatable(self) -> bool:
        return True

    def add_location(
        self,
        path:         str,
        storage_type: StorageType | str = StorageType.LOCAL,
        priority:     int = 0,
        **metadata,
    ) -> Location:
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
        return list(self._locations)

    def get_primary_location(self) -> Optional[Location]:
        return self._locations[0] if self._locations else None

    def resolve_path(self) -> Optional[str]:
        """Return the best available path, checking existence in priority order."""
        for loc in self._locations:
            if loc.check_exists():
                return loc.path
        primary = self.get_primary_location()
        return primary.path if primary else None

    def get_location_dicts(self) -> list[dict]:
        return [loc.to_dict() for loc in self._locations]


class Relational:
    """Trait: entity can declare and traverse relationships.

    Relationships are stored as Relationship(rel_key=UUID) — the key
    is stable even if the type is renamed. Usage is auto-registered
    with the default registry so orphan protection works automatically.

    For system types, use the name string directly:
        entity.add_relationship(target_id, "member_of")

    For custom types, get the key from the registry first:
        key = registry.relationships.get_key("my_custom_type")
        entity.add_relationship(target_id, key)
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
        rel_type:  uuid.UUID | str,
        registry:  Optional[Registry] = None,
        **metadata,
    ) -> Relationship:
        """Declare a relationship and register its usage.

        rel_type: system name ("member_of"), UUID string, or UUID instance.
        For custom types: registry.relationships.get_key("name").
        """
        entity_id = getattr(self, "id", None)
        if entity_id is None:
            raise ValueError("Entity must have an id to declare relationships")

        rel_key = _resolve_rel_key(rel_type)
        tgt     = uuid.UUID(str(target_id)) if isinstance(target_id, str) else target_id

        rel = Relationship(
            source_id=entity_id,
            target_id=tgt,
            rel_key=rel_key,
            metadata=metadata,
        )
        self._relationships.append(rel)

        # Auto-register usage → enables orphan protection in registry
        try:
            reg = registry or get_default_registry()
            reg.relationships.register_usage(rel_key, entity_id, tgt)
        except Exception:
            pass  # Never let bookkeeping break entity construction

        return rel

    def remove_relationship(
        self,
        target_id: uuid.UUID | str,
        rel_type:  uuid.UUID | str,
        registry:  Optional[Registry] = None,
    ) -> bool:
        """Remove a relationship and unregister its usage.

        Returns True if found and removed, False if not found.
        """
        entity_id = getattr(self, "id", None)
        tgt     = uuid.UUID(str(target_id)) if isinstance(target_id, str) else target_id
        rel_key = _resolve_rel_key(rel_type)

        before = len(self._relationships)
        self._relationships = [
            r for r in self._relationships
            if not (r.target_id == tgt and r.rel_key == rel_key)
        ]
        removed = len(self._relationships) < before

        if removed and entity_id:
            try:
                reg = registry or get_default_registry()
                reg.relationships.unregister_usage(rel_key, entity_id, tgt)
            except Exception:
                pass

        return removed

    def get_relationships(
        self,
        rel_type: Optional[uuid.UUID | str] = None,
    ) -> list[Relationship]:
        """Return relationships, optionally filtered by type.

        rel_type: system name string, UUID string, UUID instance, or None for all.
        """
        if rel_type is None:
            return list(self._relationships)
        key = _resolve_rel_key(rel_type)
        return [r for r in self._relationships if r.rel_key == key]

    def get_relationship_dicts(self, registry: Optional[Registry] = None) -> list[dict]:
        return [r.to_dict(registry) for r in self._relationships]
