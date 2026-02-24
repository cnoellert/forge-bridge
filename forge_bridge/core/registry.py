"""
forge-bridge registry system.

THREE DISTINCT CONCEPTS — this is the core design invariant:

    name   — the canonical string identifier a pipeline uses in code and config.
              ("primary", "member_of", "my_custom_role")
              Names are stable by convention, not enforcement. You can rename
              a name by reassigning via rename(), which calls migrate() under
              the hood.

    key    — a UUID. The only identifier stored inside entities and
              relationships. Never changes, even across renames. Safe to
              serialize, deserialize, diff, and compare across time.
              Standard types have well-known sequential UUIDs defined in
              traits.py so they survive upgrades.

    label  — the human-readable display string shown in UIs and logs.
              Freely mutable at any time. Changing a label never touches
              any entity or relationship.

The relationship between them:
    name  ──→  key (UUID)  ──→  label + definition

Orphan protection:
    The registry tracks every entity/relationship that holds a key.
    You cannot delete a key while anything references it — unless you
    provide a migrate_to name, which reassigns all references first.
    Protected entries (built-in system types) cannot be deleted at all.

Usage:
    registry = Registry.default()

    # Register a custom role
    registry.roles.register("hero", label="Hero Layer")

    # Create a layer — internally stores the UUID key
    layer = Layer(role="hero", registry=registry)

    # Rename the label — layer is immediately affected (live lookup)
    registry.roles.rename_label("hero", "Protagonist")

    # Rename the name itself — all entities see it immediately
    registry.roles.rename("hero", "protagonist")

    # Delete with migration
    registry.roles.delete("hero", migrate_to="primary")

    # Inspect
    registry.roles.ref_count("primary")  # → 1
    registry.summary()
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from forge_bridge.core.traits import SYSTEM_REL_KEYS, _SYSTEM_REL_NAMES
from forge_bridge.core.vocabulary import Role, STANDARD_ROLES


# Well-known UUIDs for standard roles — parallel to SYSTEM_REL_KEYS.
# These are permanent. Do not change them between versions.
STANDARD_ROLE_KEYS: dict[str, uuid.UUID] = {
    "primary":    uuid.UUID("10000000-0000-0000-0000-000000000001"),
    "reference":  uuid.UUID("10000000-0000-0000-0000-000000000002"),
    "matte":      uuid.UUID("10000000-0000-0000-0000-000000000003"),
    "background": uuid.UUID("10000000-0000-0000-0000-000000000004"),
    "foreground": uuid.UUID("10000000-0000-0000-0000-000000000005"),
    "color":      uuid.UUID("10000000-0000-0000-0000-000000000006"),
    "audio":      uuid.UUID("10000000-0000-0000-0000-000000000007"),
}
_STANDARD_ROLE_NAMES: dict[uuid.UUID, str] = {v: k for k, v in STANDARD_ROLE_KEYS.items()}


# ─────────────────────────────────────────────────────────────
# Exceptions
# ─────────────────────────────────────────────────────────────

class RegistryError(Exception):
    """Raised when a registry operation would leave entities in an invalid state."""


class OrphanError(RegistryError):
    """Raised when a delete would leave entities with a dangling key."""

    def __init__(self, name: str, ref_count: int, entity_ids: list[uuid.UUID]):
        self.name = name
        self.ref_count = ref_count
        self.entity_ids = entity_ids
        super().__init__(
            f"Cannot delete '{name}': {ref_count} "
            f"entit{'y' if ref_count == 1 else 'ies'} still reference it. "
            f"Pass migrate_to='<name>' to reassign them first, "
            f"or call registry.roles.release(key, entity_id) on each manually.\n"
            f"Referencing entity IDs: {[str(eid) for eid in entity_ids[:5]]}"
            f"{'...' if len(entity_ids) > 5 else ''}"
        )


class ProtectedEntryError(RegistryError):
    """Raised when attempting to delete a protected entry."""

    def __init__(self, name: str):
        self.name = name
        super().__init__(
            f"'{name}' is a protected (built-in) entry and cannot be deleted. "
            f"You can rename its label: registry.roles.rename_label('{name}', 'New Label')"
        )


class UnknownNameError(RegistryError, KeyError):
    """Raised when a name is not in the registry."""

    def __init__(self, name: str, registry_name: str = "registry"):
        self.name = name
        super().__init__(f"No entry named '{name}' in {registry_name}.")


class UnknownKeyError(RegistryError, KeyError):
    """Raised when a UUID key is not in the registry."""

    def __init__(self, key: uuid.UUID, registry_name: str = "registry"):
        self.key = key
        super().__init__(f"No entry with key {key} in {registry_name}.")


# ─────────────────────────────────────────────────────────────
# Internal entry
# ─────────────────────────────────────────────────────────────

@dataclass
class _Entry:
    """Internal registry record — wraps the definition with ref tracking."""
    key:       uuid.UUID       # stable UUID — never changes
    name:      str             # current canonical name (mutable via rename)
    obj:       Any             # Role or RelationshipTypeDef
    protected: bool = False
    _refs:     dict[uuid.UUID, str] = field(default_factory=dict)
    # _refs maps holder_id → human label (for error messages)

    @property
    def ref_count(self) -> int:
        return len(self._refs)

    @property
    def referencing_ids(self) -> list[uuid.UUID]:
        return list(self._refs.keys())

    def acquire(self, holder_id: uuid.UUID, label: str = "entity") -> None:
        self._refs[holder_id] = label

    def release(self, holder_id: uuid.UUID) -> None:
        self._refs.pop(holder_id, None)

    def transfer(self, holder_id: uuid.UUID, target: "_Entry") -> None:
        label = self._refs.pop(holder_id, "entity")
        target.acquire(holder_id, label)


# ─────────────────────────────────────────────────────────────
# Role definition (stored in registry — wraps vocabulary.Role)
# ─────────────────────────────────────────────────────────────

@dataclass
class RoleDefinition:
    """A role definition as stored in the registry.

    The vocabulary.Role object is the display/config surface.
    This wrapper adds the stable UUID key.
    """
    key:   uuid.UUID
    role:  Role

    @property
    def name(self) -> str:
        return self.role.name

    @property
    def label(self) -> str:
        return self.role.label

    @label.setter
    def label(self, value: str) -> None:
        self.role.label = value


# ─────────────────────────────────────────────────────────────
# Relationship type definition
# ─────────────────────────────────────────────────────────────

@dataclass
class RelationshipTypeDef:
    """Definition of a relationship type."""
    key:            uuid.UUID
    name:           str
    label:          str
    description:    str = ""
    directionality: str = "→"   # "→" "←" "↔"


# ─────────────────────────────────────────────────────────────
# RoleRegistry
# ─────────────────────────────────────────────────────────────

class RoleRegistry:
    """Manages roles. See module docstring for the full design."""

    def __init__(self):
        self._by_key:  dict[uuid.UUID, _Entry] = {}
        self._by_name: dict[str, uuid.UUID] = {}          # name → key
        self._migration_callbacks: list[Callable[[uuid.UUID, uuid.UUID, uuid.UUID], None]] = []
        # migration callback: (holder_id, old_key, new_key)

    # ── Registration ──────────────────────────────────────────

    def register(
        self,
        name:          str,
        *,
        label:         Optional[str] = None,
        order:         int = 0,
        path_template: Optional[str] = None,
        aliases:       Optional[dict[str, str]] = None,
        key:           Optional[uuid.UUID] = None,
        role:          Optional[Role] = None,
        protected:     bool = False,
    ) -> RoleDefinition:
        """Register a new role.

        Args:
            name:          Canonical string name. Used in code and config.
            label:         Display name shown in UIs (defaults to title-cased name).
            order:         Default stack position.
            path_template: Folder path pattern with {tokens}.
            aliases:       Endpoint-specific names e.g. {"flame": "L01"}.
            key:           Explicit UUID to use (auto-generated if not provided).
                           Use a fixed UUID for standard roles that must survive upgrades.
            role:          Pre-built Role object (overrides label/order/etc.).
            protected:     If True, cannot be deleted — only renamed.

        Returns:
            RoleDefinition wrapping the registered role.

        Raises:
            RegistryError: If name or key is already registered.
        """
        if name in self._by_name:
            raise RegistryError(f"Role name '{name}' is already registered.")

        if role is None:
            role = Role(
                name=name,
                label=label,
                order=order,
                path_template=path_template,
                aliases=aliases or {},
            )
        else:
            role.name = name

        rkey = key or uuid.uuid4()
        if rkey in self._by_key:
            raise RegistryError(f"Role key {rkey} is already registered.")

        defn = RoleDefinition(key=rkey, role=role)
        entry = _Entry(key=rkey, name=name, obj=defn, protected=protected)
        self._by_key[rkey] = entry
        self._by_name[name] = rkey
        return defn

    # ── Lookup ────────────────────────────────────────────────

    def get_key(self, name: str) -> uuid.UUID:
        """Return the UUID key for a name.

        Raises:
            UnknownNameError: If the name is not registered.
        """
        if name not in self._by_name:
            raise UnknownNameError(name, "role")
        return self._by_name[name]

    def get_by_key(self, key: uuid.UUID) -> RoleDefinition:
        """Return the RoleDefinition for a UUID key.

        Raises:
            UnknownKeyError: If the key is not registered.
        """
        if key not in self._by_key:
            raise UnknownKeyError(key, "role")
        return self._by_key[key].obj

    def get_by_name(self, name: str) -> RoleDefinition:
        """Return the RoleDefinition for a name."""
        return self.get_by_key(self.get_key(name))

    def __contains__(self, name: str) -> bool:
        return name in self._by_name

    def names(self) -> list[str]:
        return list(self._by_name.keys())

    # ── Mutation ──────────────────────────────────────────────

    def rename_label(self, name: str, new_label: str) -> None:
        """Change the display label for a role.

        Purely cosmetic — the name and UUID key are unchanged.
        All live lookups immediately reflect the new label.

        Raises:
            UnknownNameError: If the name is not registered.
        """
        if name not in self._by_name:
            raise UnknownNameError(name, "role")
        self._by_key[self._by_name[name]].obj.label = new_label

    def rename(self, old_name: str, new_name: str) -> None:
        """Rename a role's canonical name.

        The UUID key is unchanged — entities storing the key are
        completely unaffected. Only the name → key lookup changes.

        Raises:
            UnknownNameError: If old_name is not registered.
            RegistryError:    If new_name is already taken.
        """
        if old_name not in self._by_name:
            raise UnknownNameError(old_name, "role")
        if new_name in self._by_name:
            raise RegistryError(
                f"Cannot rename '{old_name}' to '{new_name}': "
                f"'{new_name}' is already registered."
            )
        key = self._by_name.pop(old_name)
        entry = self._by_key[key]
        entry.name = new_name
        entry.obj.role.name = new_name
        self._by_name[new_name] = key

    def update(
        self,
        name:          str,
        *,
        label:         Optional[str] = None,
        order:         Optional[int] = None,
        path_template: Optional[str] = None,
        aliases:       Optional[dict[str, str]] = None,
    ) -> RoleDefinition:
        """Update role attributes (None = unchanged).

        Raises:
            UnknownNameError: If the name is not registered.
        """
        if name not in self._by_name:
            raise UnknownNameError(name, "role")
        role = self._by_key[self._by_name[name]].obj.role
        if label is not None:
            role.label = label
        if order is not None:
            role.order = order
        if path_template is not None:
            role.path_template = path_template
        if aliases is not None:
            role.aliases.update(aliases)
        return self._by_key[self._by_name[name]].obj

    def delete(self, name: str, migrate_to: Optional[str] = None) -> int:
        """Delete a role.

        With refs and migrate_to:  all references reassigned, then deleted.
        With refs and no migrate_to: raises OrphanError.
        Protected entries: raises ProtectedEntryError always.

        Returns:
            Number of entities migrated.
        """
        if name not in self._by_name:
            raise UnknownNameError(name, "role")

        key = self._by_name[name]
        entry = self._by_key[key]

        if entry.protected:
            raise ProtectedEntryError(name)

        migrated = 0
        if entry.ref_count > 0:
            if migrate_to is None:
                raise OrphanError(name, entry.ref_count, entry.referencing_ids)
            if migrate_to not in self._by_name:
                raise UnknownNameError(migrate_to, "role")

            target_key   = self._by_name[migrate_to]
            target_entry = self._by_key[target_key]

            for holder_id in list(entry.referencing_ids):
                entry.transfer(holder_id, target_entry)
                for cb in self._migration_callbacks:
                    cb(holder_id, key, target_key)
                migrated += 1

        del self._by_key[key]
        del self._by_name[name]
        return migrated

    # ── Reference tracking ────────────────────────────────────

    def register_usage(self, key: uuid.UUID, holder_id: uuid.UUID, label: str = "entity") -> None:
        """Record that holder_id now references this role key.

        Called automatically by Layer on construction and role change.
        """
        if key not in self._by_key:
            raise UnknownKeyError(key, "role")
        self._by_key[key].acquire(holder_id, label)

    def unregister_usage(self, key: uuid.UUID, holder_id: uuid.UUID) -> None:
        """Remove holder_id's reference to this role key.

        Safe to call even if the key no longer exists.
        """
        if key in self._by_key:
            self._by_key[key].release(holder_id)

    def ref_count(self, name: str) -> int:
        if name not in self._by_name:
            raise UnknownNameError(name, "role")
        return self._by_key[self._by_name[name]].ref_count

    def who_references(self, name: str) -> list[uuid.UUID]:
        if name not in self._by_name:
            raise UnknownNameError(name, "role")
        return self._by_key[self._by_name[name]].referencing_ids

    def on_migration(self, callback: Callable[[uuid.UUID, uuid.UUID, uuid.UUID], None]) -> None:
        """Register a callback invoked when a delete+migrate reassigns references.

        Callback: (holder_id: UUID, old_key: UUID, new_key: UUID) → None
        Layer uses this to update its internal role_key field automatically.
        """
        self._migration_callbacks.append(callback)


# ─────────────────────────────────────────────────────────────
# RelationshipTypeRegistry
# ─────────────────────────────────────────────────────────────

class RelationshipTypeRegistry:
    """Manages relationship types.

    Built-in types (member_of, version_of, etc.) are protected.
    They can be renamed (label only) but never deleted.
    Custom types have full orphan-protected lifecycle.

    Unlike roles, relationship usage is tracked per (source, target) pair
    so the registry knows exactly which edges use a given type.
    """

    def __init__(self):
        self._by_key:  dict[uuid.UUID, _Entry] = {}
        self._by_name: dict[str, uuid.UUID] = {}
        self._migration_callbacks: list[Callable[[tuple, uuid.UUID, uuid.UUID], None]] = []
        # migration callback: (edge_id: tuple, old_key: UUID, new_key: UUID)

    # ── Registration ──────────────────────────────────────────

    def register(
        self,
        name:           str,
        *,
        label:          Optional[str] = None,
        description:    str = "",
        directionality: str = "→",
        key:            Optional[uuid.UUID] = None,
        protected:      bool = False,
    ) -> RelationshipTypeDef:
        if name in self._by_name:
            raise RegistryError(f"Relationship type '{name}' is already registered.")

        rkey = key or uuid.uuid4()
        if rkey in self._by_key:
            raise RegistryError(f"Relationship type key {rkey} is already registered.")

        typedef = RelationshipTypeDef(
            key=rkey,
            name=name,
            label=label or name.replace("_", " "),
            description=description,
            directionality=directionality,
        )
        entry = _Entry(key=rkey, name=name, obj=typedef, protected=protected)
        self._by_key[rkey] = entry
        self._by_name[name] = rkey
        return typedef

    # ── Lookup ────────────────────────────────────────────────

    def get_key(self, name: str) -> uuid.UUID:
        if name not in self._by_name:
            raise UnknownNameError(name, "relationship_type")
        return self._by_name[name]

    def get_by_key(self, key: uuid.UUID) -> RelationshipTypeDef:
        if key not in self._by_key:
            raise UnknownKeyError(key, "relationship_type")
        return self._by_key[key].obj

    def get_by_name(self, name: str) -> RelationshipTypeDef:
        return self.get_by_key(self.get_key(name))

    def __contains__(self, name: str) -> bool:
        return name in self._by_name

    def names(self) -> list[str]:
        return list(self._by_name.keys())

    # ── Mutation ──────────────────────────────────────────────

    def rename_label(self, name: str, new_label: str) -> None:
        """Change the display label only. Name and key unchanged."""
        if name not in self._by_name:
            raise UnknownNameError(name, "relationship_type")
        self._by_key[self._by_name[name]].obj.label = new_label

    def rename(self, old_name: str, new_name: str) -> None:
        """Rename the canonical name. UUID key unchanged. No entity updates needed."""
        if old_name not in self._by_name:
            raise UnknownNameError(old_name, "relationship_type")
        if new_name in self._by_name:
            raise RegistryError(f"Cannot rename: '{new_name}' is already registered.")
        key = self._by_name.pop(old_name)
        entry = self._by_key[key]
        entry.name = new_name
        entry.obj.name = new_name
        self._by_name[new_name] = key

    def delete(self, name: str, migrate_to: Optional[str] = None) -> int:
        """Delete a custom relationship type.

        Built-in types cannot be deleted.
        """
        if name not in self._by_name:
            raise UnknownNameError(name, "relationship_type")

        key   = self._by_name[name]
        entry = self._by_key[key]

        if entry.protected:
            raise ProtectedEntryError(name)

        migrated = 0
        if entry.ref_count > 0:
            if migrate_to is None:
                raise OrphanError(name, entry.ref_count, entry.referencing_ids)
            if migrate_to not in self._by_name:
                raise UnknownNameError(migrate_to, "relationship_type")

            target_key   = self._by_name[migrate_to]
            target_entry = self._by_key[target_key]

            for edge_id in list(entry.referencing_ids):
                entry.transfer(edge_id, target_entry)
                for cb in self._migration_callbacks:
                    cb(edge_id, key, target_key)
                migrated += 1

        del self._by_key[key]
        del self._by_name[name]
        return migrated

    # ── Reference tracking ────────────────────────────────────

    def register_usage(
        self,
        key:       uuid.UUID,
        source_id: uuid.UUID,
        target_id: uuid.UUID,
    ) -> None:
        """Record that an edge (source→target) uses this relationship type key."""
        if key not in self._by_key:
            # Unknown key — don't crash entity construction, just skip
            return
        edge_id = (source_id, target_id)
        self._by_key[key].acquire(edge_id, f"{source_id!s:.8}→{target_id!s:.8}")

    def unregister_usage(
        self,
        key:       uuid.UUID,
        source_id: uuid.UUID,
        target_id: uuid.UUID,
    ) -> None:
        """Remove an edge's reference to this relationship type key."""
        if key in self._by_key:
            edge_id = (source_id, target_id)
            self._by_key[key].release(edge_id)

    def ref_count(self, name: str) -> int:
        if name not in self._by_name:
            raise UnknownNameError(name, "relationship_type")
        return self._by_key[self._by_name[name]].ref_count

    def on_migration(
        self,
        callback: Callable[[tuple, uuid.UUID, uuid.UUID], None]
    ) -> None:
        """Register a callback invoked when delete+migrate reassigns relationship edges.

        Callback: (edge_id: tuple(source_id, target_id), old_key: UUID, new_key: UUID)
        The dependency graph uses this to update Relationship.rel_key in memory.
        """
        self._migration_callbacks.append(callback)


# ─────────────────────────────────────────────────────────────
# Registry — top-level object
# ─────────────────────────────────────────────────────────────

class Registry:
    """The single registry for a bridge session.

    Holds:
        .roles              — RoleRegistry
        .relationships      — RelationshipTypeRegistry

    Typical usage:
        registry = Registry.default()    # seeded with standard roles + types
        registry.roles.register("hero", label="Hero Layer")
        registry.relationship_types.register("approved_by")
    """

    def __init__(self, seed_defaults: bool = True):
        self.roles         = RoleRegistry()
        self.relationships = RelationshipTypeRegistry()
        if seed_defaults:
            self._seed()

    @classmethod
    def default(cls) -> "Registry":
        """Create a Registry seeded with standard roles and built-in relationship types."""
        return cls(seed_defaults=True)

    def _seed(self) -> None:
        """Populate with defaults."""
        # Standard roles with well-known UUIDs
        for name, role in STANDARD_ROLES.items():
            key = STANDARD_ROLE_KEYS.get(name, uuid.uuid4())
            self.roles.register(
                name,
                role=role,
                key=key,
                protected=True,
            )

        # Built-in relationship types with well-known UUIDs from traits.py
        _builtin_rel_types = {
            "member_of":    ("member of",    "Entity belongs to a collection",        "→"),
            "version_of":   ("version of",   "Entity is an iteration of another",     "→"),
            "derived_from": ("derived from", "Entity was produced from another",       "→"),
            "references":   ("references",   "Entity uses another without ownership",  "→"),
            "peer_of":      ("peer of",      "Entities related at the same level",     "↔"),
        }
        for name, (label, description, direction) in _builtin_rel_types.items():
            key = SYSTEM_REL_KEYS[name]
            self.relationships.register(
                name,
                label=label,
                description=description,
                directionality=direction,
                key=key,
                protected=True,
            )


    @classmethod
    def from_dict(cls, data: dict) -> "Registry":
        """Restore a Registry from a dict produced by to_dict() / summary().

        Re-registers all roles and relationship types. Standard entries
        with well-known UUIDs are matched by key so renames survive the
        roundtrip (e.g. "primary" renamed to "hero" is restored correctly).
        """
        r = cls(seed_defaults=False)  # Empty registry — we rebuild from data

        # Restore roles
        for name, info in data.get("roles", {}).items():
            key = uuid.UUID(info["key"])
            role = Role(
                name=name,
                label=info.get("label"),
                order=info.get("order", 0),
                path_template=info.get("path_template"),
                aliases=info.get("aliases", {}),
            )
            protected = info.get("protected", False)
            r.roles.register(name, role=role, key=key, protected=protected)

        # Restore relationship types
        for name, info in data.get("relationship_types", {}).items():
            key = uuid.UUID(info["key"])
            protected = info.get("protected", False)
            r.relationships.register(
                name,
                label=info.get("label", name),
                description=info.get("description", ""),
                directionality=info.get("directionality", "→"),
                key=key,
                protected=protected,
            )

        return r

    def to_dict(self) -> dict:
        """Alias for summary() — serialize the registry state to a dict."""
        return self.summary()

    def summary(self) -> dict:
        """Return a serializable summary of the registry state.

        The returned dict can be passed to Registry.from_dict() to restore
        the registry with all custom roles and relationship types intact.
        Ref counts are included for inspection but are not restored on load.
        """
        roles_dict = {}
        for entry in self.roles._by_key.values():
            role = entry.obj.role
            roles_dict[entry.name] = {
                "key":           str(entry.key),
                "label":         role.label,
                "order":         role.order,
                "path_template": role.path_template,
                "aliases":       dict(role.aliases),
                "protected":     entry.protected,
                "ref_count":     entry.ref_count,
            }

        rels_dict = {}
        for entry in self.relationships._by_key.values():
            defn = entry.obj
            rels_dict[entry.name] = {
                "key":            str(entry.key),
                "label":          defn.label,
                "description":    defn.description,
                "directionality": defn.directionality,
                "protected":      entry.protected,
                "ref_count":      entry.ref_count,
            }

        return {"roles": roles_dict, "relationship_types": rels_dict}


# ─────────────────────────────────────────────────────────────
# Convenience aliases (test-friendly API surface)
# ─────────────────────────────────────────────────────────────

def _add_aliases():
    """Add convenience aliases to RoleRegistry and RelationshipTypeRegistry.

    These provide shorter names for common operations, making test code
    and interactive use cleaner.
    """
    # RoleRegistry aliases
    RoleRegistry.add      = RoleRegistry.register   # .add() → .register()
    RoleRegistry.exists   = lambda self, name: name in self._by_name
    RoleRegistry.usage_count = RoleRegistry.ref_count

    # Proxy get_alias through RoleDefinition
    RoleDefinition.get_alias = lambda self, endpoint: self.role.get_alias(endpoint)

    # RelationshipTypeRegistry aliases
    RelationshipTypeRegistry.add    = RelationshipTypeRegistry.register
    RelationshipTypeRegistry.exists = lambda self, name: name in self._by_name


_add_aliases()


# Alias on OrphanError so tests and error handling code can use either name
OrphanError.usage_count = property(lambda self: self.ref_count)
