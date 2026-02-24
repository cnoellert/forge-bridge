"""
forge-bridge core vocabulary.

    from forge_bridge.core import (
        # Entities
        Project, Sequence, Shot, Asset, Version, Media, Stack, Layer,
        # Traits
        Versionable, Locatable, Relational,
        # Relationship primitives
        Relationship, SYSTEM_REL_KEYS,
        # Supporting types
        Role, STANDARD_ROLES, Status, Timecode, FrameRange,
        Location, StorageType,
        # Registry
        Registry, RoleRegistry, RelationshipTypeRegistry,
        RoleDefinition, RelationshipTypeDef,
        RegistryError, OrphanError, ProtectedEntryError,
        UnknownNameError, UnknownKeyError,
        STANDARD_ROLE_KEYS,
        get_default_registry, set_default_registry,
    )
"""

from forge_bridge.core.entities import (
    Asset,
    BridgeEntity,
    Layer,
    Media,
    Project,
    Sequence,
    Shot,
    Stack,
    Version,
)
from forge_bridge.core.traits import (
    Locatable,
    Location,
    Relational,
    Relationship,
    SYSTEM_REL_KEYS,
    StorageType,
    Versionable,
    get_default_registry,
    set_default_registry,
)
from forge_bridge.core.vocabulary import (
    FrameRange,
    Role,
    STANDARD_ROLES,
    Status,
    Timecode,
)
from forge_bridge.core.registry import (
    OrphanError,
    ProtectedEntryError,
    Registry,
    RegistryError,
    RelationshipTypeDef,
    RelationshipTypeRegistry,
    RoleDefinition,
    RoleRegistry,
    STANDARD_ROLE_KEYS,
    UnknownKeyError,
    UnknownNameError,
)

__all__ = [
    # Entities
    "BridgeEntity", "Project", "Sequence", "Shot", "Asset",
    "Version", "Media", "Stack", "Layer",
    # Traits
    "Versionable", "Locatable", "Relational",
    # Relationship primitives
    "Relationship", "SYSTEM_REL_KEYS",
    # Supporting types
    "Role", "STANDARD_ROLES", "Status",
    "Timecode", "FrameRange",
    "Location", "StorageType",
    # Registry
    "Registry", "RoleRegistry", "RelationshipTypeRegistry",
    "RoleDefinition", "RelationshipTypeDef",
    "RegistryError", "OrphanError", "ProtectedEntryError",
    "UnknownNameError", "UnknownKeyError",
    "STANDARD_ROLE_KEYS",
    "get_default_registry", "set_default_registry",
]
