"""
forge-bridge registry system.

The registry is the single source of truth for role definitions and
relationship type definitions. It governs what names mean and enforces
the invariant that no entity is ever orphaned by a deletion.

Design rules:
  - Names are mutable display artifacts. Always rename-safe.
  - Keys (UUIDs) are permanent. Entities hold keys, never names.
  - Deletion is blocked if any entity holds the key (OrphanError).
  - System relationship types can be renamed but never deleted —
    they are the structural grammar of the dependency graph.

Usage:
    registry = Registry.default()           # standard pipeline setup

    # Rename a role — safe, all entities auto-reflect new name
    registry.roles.rename("primary", "hero")

    # Add a custom role
    registry.roles.add("paint", label="Paint Pass", order=7)

    # Delete a role — blocked if any Layer holds its key
    registry.roles.delete("paint")          # raises OrphanError if in use

    # Rename a system relationship type — safe
    registry.relationships.rename("member_of", "belongs_to")

    # Delete a custom relationship type — blocked if in use
    registry.relationships.delete("my_custom_type")

    # Apply as pipeline default so all entities use it automatically
    from forge_bridge.core.traits import set_default_registry
    set_default_registry(registry)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

# Import system keys from traits — single definition, no circular deps
from forge_bridge.core.traits import SYSTEM_REL_KEYS
from forge_bridge.core.vocabulary import Role, STANDARD_ROLES


# ─────────────────────────────────────────────────────────────
# Exceptions
# ─────────────────────────────────────────────────────────────

class RegistryError(Exception):
    """Base class for registry violations."""
    pass


class OrphanError(RegistryError):
    """Raised when a deletion would leave entities with a dangling key."""

    def __init__(self, key: uuid.UUID, name: str, usage_count: int):
        self.key         = key
        self.name        = name
        self.usage_count = usage_count
        super().__init__(
            f"Cannot delete '{name}' — {usage_count} "
            f"{'entity' if usage_count == 1 else 'entities'} still reference it. "
            f"Reassign or remove those entities first."
        )


class SystemProtectedError(RegistryError):
    """Raised when attempting to delete a system-protected definition."""

    def __init__(self, name: str):
        super().__init__(
            f"'{name}' is a system relationship type and cannot be deleted. "
            f"System types can be renamed but not removed."
        )


class NotFoundError(RegistryError):
    """Raised when a name or key is not in the registry."""
    pass


class DuplicateError(RegistryError):
    """Raised when adding something that already exists."""
    pass


# ─────────────────────────────────────────────────────────────
# Role definition
# ─────────────────────────────────────────────────────────────

@dataclass
class RoleDefinition:
    """A role with a stable key and a mutable display name.

    Entities (Layer) hold role_key. The name can change freely.
    """
    key:           uuid.UUID
    name:          str
    label:         Optional[str] = None
    path_template: Optional[str] = None
    order:         int = 0
    aliases:       dict[str, str] = field(default_factory=dict)
    metadata:      dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.label is None:
            self.label = self.name.replace("_", " ").title()

    def to_role(self) -> Role:
        return Role(
            name=self.name,
            label=self.label,
            path_template=self.path_template,
            order=self.order,
            aliases=dict(self.aliases),
            metadata=dict(self.metadata),
        )

    def get_alias(self, endpoint: str) -> str:
        return self.aliases.get(endpoint, self.name)

    def to_dict(self) -> dict:
        return {
            "key":           str(self.key),
            "name":          self.name,
            "label":         self.label,
            "path_template": self.path_template,
            "order":         self.order,
            "aliases":       self.aliases,
        }


# ─────────────────────────────────────────────────────────────
# Relationship type definition
# ─────────────────────────────────────────────────────────────

@dataclass
class RelationshipDefinition:
    """A relationship type with a stable key and a mutable display name.

    system=True types cannot be deleted — only renamed.
    """
    key:         uuid.UUID
    name:        str
    label:       Optional[str] = None
    system:      bool = False
    description: Optional[str] = None
    metadata:    dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.label is None:
            self.label = self.name.replace("_", " ").title()

    def to_dict(self) -> dict:
        return {
            "key":    str(self.key),
            "name":   self.name,
            "label":  self.label,
            "system": self.system,
        }


# ─────────────────────────────────────────────────────────────
# RoleRegistry
# ─────────────────────────────────────────────────────────────

class RoleRegistry:
    """Manages roles with rename/delete safety.

    Rename: always safe — key unchanged, all entities see new name.
    Delete: blocked if any entity holds the key (OrphanError).
    """

    def __init__(self):
        self._by_key:  dict[uuid.UUID, RoleDefinition] = {}
        self._by_name: dict[str, uuid.UUID] = {}
        # usage: role_key → set of entity_ids that hold it
        self._usage:   dict[uuid.UUID, set[uuid.UUID]] = {}

    # ── Query ─────────────────────────────────────────────────

    def get_by_key(self, key: uuid.UUID) -> RoleDefinition:
        defn = self._by_key.get(key)
        if defn is None:
            raise NotFoundError(f"No role with key {str(key)[:8]}...")
        return defn

    def get_by_name(self, name: str) -> RoleDefinition:
        key = self._by_name.get(name)
        if key is None:
            raise NotFoundError(f"No role named '{name}'")
        return self._by_key[key]

    def get_key(self, name: str) -> uuid.UUID:
        return self.get_by_name(name).key

    def all(self) -> list[RoleDefinition]:
        return sorted(self._by_key.values(), key=lambda r: r.order)

    def exists(self, name: str) -> bool:
        return name in self._by_name

    # ── Mutation ──────────────────────────────────────────────

    def add(
        self,
        name:          str,
        label:         Optional[str] = None,
        path_template: Optional[str] = None,
        order:         int = 0,
        aliases:       Optional[dict[str, str]] = None,
        key:           Optional[uuid.UUID] = None,
        **metadata,
    ) -> RoleDefinition:
        if name in self._by_name:
            raise DuplicateError(f"Role '{name}' already exists. Use rename() to change it.")
        role_key = key or uuid.uuid4()
        defn = RoleDefinition(
            key=role_key, name=name, label=label,
            path_template=path_template, order=order,
            aliases=aliases or {}, metadata=metadata,
        )
        self._by_key[role_key]  = defn
        self._by_name[name]     = role_key
        self._usage[role_key]   = set()
        return defn

    def rename(self, old_name: str, new_name: str) -> RoleDefinition:
        """Rename a role. Always safe — key is unchanged."""
        defn = self.get_by_name(old_name)
        if new_name in self._by_name and self._by_name[new_name] != defn.key:
            raise DuplicateError(f"Cannot rename to '{new_name}': name already in use.")
        del self._by_name[old_name]
        # Update label only if it was the auto-generated default
        if defn.label == old_name.replace("_", " ").title():
            defn.label = new_name.replace("_", " ").title()
        defn.name = new_name
        self._by_name[new_name] = defn.key
        return defn

    def delete(self, name: str) -> None:
        """Delete a role. Blocked if any entity holds its key."""
        defn  = self.get_by_name(name)
        usage = self._usage.get(defn.key, set())
        if usage:
            raise OrphanError(defn.key, name, len(usage))
        del self._by_name[name]
        del self._by_key[defn.key]
        del self._usage[defn.key]

    def update_alias(self, name: str, endpoint: str, alias: str) -> None:
        self.get_by_name(name).aliases[endpoint] = alias

    def update_path_template(self, name: str, template: str) -> None:
        self.get_by_name(name).path_template = template

    # ── Usage tracking ────────────────────────────────────────

    def register_usage(self, role_key: uuid.UUID, entity_id: uuid.UUID) -> None:
        self._usage.setdefault(role_key, set()).add(entity_id)

    def unregister_usage(self, role_key: uuid.UUID, entity_id: uuid.UUID) -> None:
        if role_key in self._usage:
            self._usage[role_key].discard(entity_id)

    def usage_count(self, name: str) -> int:
        return len(self._usage.get(self.get_key(name), set()))

    def entity_ids_using(self, name: str) -> set[uuid.UUID]:
        return set(self._usage.get(self.get_key(name), set()))

    # ── Serialization ─────────────────────────────────────────

    def to_dict(self) -> dict:
        return {"roles": [d.to_dict() for d in self.all()]}

    @classmethod
    def from_dict(cls, data: dict) -> RoleRegistry:
        r = cls()
        for entry in data.get("roles", []):
            r.add(
                name=entry["name"], label=entry.get("label"),
                path_template=entry.get("path_template"),
                order=entry.get("order", 0),
                aliases=entry.get("aliases", {}),
                key=uuid.UUID(entry["key"]),
            )
        return r


# ─────────────────────────────────────────────────────────────
# RelationshipRegistry
# ─────────────────────────────────────────────────────────────

class RelationshipRegistry:
    """Manages relationship types with rename/delete safety.

    System types: rename ✓  delete ✗  (structural grammar of the graph)
    Custom types: rename ✓  delete only when usage == 0
    """

    def __init__(self):
        self._by_key:  dict[uuid.UUID, RelationshipDefinition] = {}
        self._by_name: dict[str, uuid.UUID] = {}
        # usage: rel_key → set of (source_id, target_id) tuples
        self._usage:   dict[uuid.UUID, set[tuple[uuid.UUID, uuid.UUID]]] = {}

    # ── Query ─────────────────────────────────────────────────

    def get_by_key(self, key: uuid.UUID) -> RelationshipDefinition:
        defn = self._by_key.get(key)
        if defn is None:
            raise NotFoundError(f"No relationship type with key {str(key)[:8]}...")
        return defn

    def get_by_name(self, name: str) -> RelationshipDefinition:
        key = self._by_name.get(name)
        if key is None:
            raise NotFoundError(f"No relationship type named '{name}'")
        return self._by_key[key]

    def get_key(self, name: str) -> uuid.UUID:
        return self.get_by_name(name).key

    def all(self) -> list[RelationshipDefinition]:
        return list(self._by_key.values())

    def system_types(self) -> list[RelationshipDefinition]:
        return [d for d in self._by_key.values() if d.system]

    def custom_types(self) -> list[RelationshipDefinition]:
        return [d for d in self._by_key.values() if not d.system]

    def exists(self, name: str) -> bool:
        return name in self._by_name

    # ── Mutation ──────────────────────────────────────────────

    def add(
        self,
        name:        str,
        label:       Optional[str] = None,
        system:      bool = False,
        description: Optional[str] = None,
        key:         Optional[uuid.UUID] = None,
        **metadata,
    ) -> RelationshipDefinition:
        if name in self._by_name:
            raise DuplicateError(f"Relationship type '{name}' already exists.")
        rel_key = key or uuid.uuid4()
        defn = RelationshipDefinition(
            key=rel_key, name=name, label=label,
            system=system, description=description, metadata=metadata,
        )
        self._by_key[rel_key]  = defn
        self._by_name[name]    = rel_key
        self._usage[rel_key]   = set()
        return defn

    def rename(self, old_name: str, new_name: str) -> RelationshipDefinition:
        """Rename a relationship type. Always safe for both system and custom."""
        defn = self.get_by_name(old_name)
        if new_name in self._by_name and self._by_name[new_name] != defn.key:
            raise DuplicateError(f"Cannot rename to '{new_name}': name already in use.")
        del self._by_name[old_name]
        if defn.label == old_name.replace("_", " ").title():
            defn.label = new_name.replace("_", " ").title()
        defn.name = new_name
        self._by_name[new_name] = defn.key
        return defn

    def delete(self, name: str) -> None:
        """Delete a custom relationship type.

        Raises SystemProtectedError for system types.
        Raises OrphanError if any relationships use this type.
        """
        defn = self.get_by_name(name)
        if defn.system:
            raise SystemProtectedError(name)
        usage = self._usage.get(defn.key, set())
        if usage:
            raise OrphanError(defn.key, name, len(usage))
        del self._by_name[name]
        del self._by_key[defn.key]
        del self._usage[defn.key]

    # ── Usage tracking ────────────────────────────────────────

    def register_usage(
        self,
        rel_key:   uuid.UUID,
        source_id: uuid.UUID,
        target_id: uuid.UUID,
    ) -> None:
        self._usage.setdefault(rel_key, set()).add((source_id, target_id))

    def unregister_usage(
        self,
        rel_key:   uuid.UUID,
        source_id: uuid.UUID,
        target_id: uuid.UUID,
    ) -> None:
        if rel_key in self._usage:
            self._usage[rel_key].discard((source_id, target_id))

    def usage_count(self, name: str) -> int:
        return len(self._usage.get(self.get_key(name), set()))

    # ── System type seeding ───────────────────────────────────

    def _seed_system_types(self) -> None:
        """Register built-in system relationship types."""
        defs = [
            ("member_of",    "Member Of",    "Source belongs to target collection"),
            ("version_of",   "Version Of",   "Source is an iteration of the target"),
            ("derived_from", "Derived From", "Source was produced from target"),
            ("references",   "References",   "Source uses target without ownership"),
            ("peer_of",      "Peer Of",      "Source and target are at the same level"),
        ]
        for name, label, desc in defs:
            key = SYSTEM_REL_KEYS[name]   # imported from traits — single definition
            defn = RelationshipDefinition(
                key=key, name=name, label=label,
                system=True, description=desc,
            )
            self._by_key[key]   = defn
            self._by_name[name] = key
            self._usage[key]    = set()

    # ── Serialization ─────────────────────────────────────────

    def to_dict(self) -> dict:
        return {"relationship_types": [d.to_dict() for d in self.all()]}

    @classmethod
    def from_dict(cls, data: dict) -> RelationshipRegistry:
        r = cls()
        r._seed_system_types()
        for entry in data.get("relationship_types", []):
            key = uuid.UUID(entry["key"])
            if key in r._by_key:
                continue  # already seeded as system type
            r.add(
                name=entry["name"], label=entry.get("label"),
                system=entry.get("system", False),
                key=key,
            )
        return r


# ─────────────────────────────────────────────────────────────
# Registry — top-level container
# ─────────────────────────────────────────────────────────────

class Registry:
    """Top-level registry for a forge-bridge pipeline instance.

    Holds both the role registry and the relationship type registry.
    Pass this around or set it as the pipeline default.

    Quick start:
        registry = Registry.default()
        set_default_registry(registry)   # all entities use it automatically
    """

    # Deterministic keys for standard roles (survive serialization)
    _STANDARD_ROLE_KEYS = {
        "primary":    uuid.UUID("10000000-0000-0000-0000-000000000001"),
        "reference":  uuid.UUID("10000000-0000-0000-0000-000000000002"),
        "matte":      uuid.UUID("10000000-0000-0000-0000-000000000003"),
        "background": uuid.UUID("10000000-0000-0000-0000-000000000004"),
        "foreground": uuid.UUID("10000000-0000-0000-0000-000000000005"),
        "color":      uuid.UUID("10000000-0000-0000-0000-000000000006"),
        "audio":      uuid.UUID("10000000-0000-0000-0000-000000000007"),
    }

    def __init__(self):
        self.roles:         RoleRegistry         = RoleRegistry()
        self.relationships: RelationshipRegistry = RelationshipRegistry()

    @classmethod
    def default(cls) -> Registry:
        """Create a registry with standard roles and all system relationship types."""
        r = cls()
        r.relationships._seed_system_types()
        for name, role in STANDARD_ROLES.items():
            r.roles.add(
                name=name, label=role.label,
                path_template=role.path_template,
                order=role.order, aliases=dict(role.aliases),
                key=cls._STANDARD_ROLE_KEYS[name],
            )
        return r

    @classmethod
    def empty(cls) -> Registry:
        """Create a registry with system relationship types only, no roles."""
        r = cls()
        r.relationships._seed_system_types()
        return r

    def to_dict(self) -> dict:
        return {
            "roles":         self.roles.to_dict(),
            "relationships": self.relationships.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> Registry:
        r = cls()
        r.roles         = RoleRegistry.from_dict(data.get("roles", {}))
        r.relationships = RelationshipRegistry.from_dict(data.get("relationships", {}))
        return r
