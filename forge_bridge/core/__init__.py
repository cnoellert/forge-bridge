"""
forge-bridge core vocabulary.

This package implements the canonical language that bridge speaks.
Import from here for all entity types, traits, and vocabulary types.

    from forge_bridge.core import (
        Project, Sequence, Shot, Asset, Version, Media,
        Stack, Layer, Role, Status, Timecode, FrameRange,
        Locatable, Versionable, Relational,
        RelationshipType, StorageType, Location,
        STANDARD_ROLES,
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
    RelationshipType,
    StorageType,
    Versionable,
)
from forge_bridge.core.vocabulary import (
    FrameRange,
    Role,
    STANDARD_ROLES,
    Status,
    Timecode,
)

__all__ = [
    # Entities
    "BridgeEntity",
    "Project",
    "Sequence",
    "Shot",
    "Asset",
    "Version",
    "Media",
    "Stack",
    "Layer",
    # Traits
    "Versionable",
    "Locatable",
    "Relational",
    # Supporting types
    "Role",
    "STANDARD_ROLES",
    "Status",
    "Timecode",
    "FrameRange",
    "Location",
    "StorageType",
    "Relationship",
    "RelationshipType",
]
