"""
forge-bridge canonical entities.

These are the nouns of the bridge vocabulary. Every piece of data
that flows through bridge is ultimately an instance of one of these
entity types (or a collection of them).

Entity hierarchy:
    Project
    └── Sequence
        └── Shot
            ├── Version
            │   └── Media
            └── Stack
                └── Layer (carries a Role, references a Version)

Asset is a parallel track — not a Shot, but used in shots:
    Asset
    └── Version
        └── Media
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from fractions import Fraction
from typing import Any, Optional

from forge_bridge.core.traits import Locatable, Relational, RelationshipType, Versionable
from forge_bridge.core.vocabulary import FrameRange, Role, Status, Timecode


# ─────────────────────────────────────────────────────────────
# Base entity
# ─────────────────────────────────────────────────────────────

class BridgeEntity(Relational, Locatable):
    """Base class for all bridge entities.

    Every entity has:
        id          — canonical UUID (auto-generated if not provided)
        created_at  — creation timestamp
        metadata    — open key/value store for anything that doesn't
                      fit a formal concept

    All entities carry the Relational and Locatable traits by default.
    Subclasses add Versionable where appropriate.
    """

    def __init__(
        self,
        id: Optional[uuid.UUID | str] = None,
        created_at: Optional[datetime] = None,
        metadata: Optional[dict[str, Any]] = None,
    ):
        super().__init__()
        self.id: uuid.UUID = (
            uuid.UUID(str(id)) if id is not None else uuid.uuid4()
        )
        self.created_at: datetime = created_at or datetime.utcnow()
        self.metadata: dict[str, Any] = metadata or {}

    @property
    def entity_type(self) -> str:
        return self.__class__.__name__.lower()

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "entity_type": self.entity_type,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
            "locations": self.get_location_dicts(),
            "relationships": self.get_relationship_dicts(),
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id!s:.8}...)"


# ─────────────────────────────────────────────────────────────
# Project
# ─────────────────────────────────────────────────────────────

class Project(Versionable, BridgeEntity):
    """Top-level container. Everything in bridge lives inside a Project.

    Endpoint mappings:
        Flame:    project (flame.project.current_project)
        ShotGrid: Project entity
        ftrack:   Project
    """

    def __init__(
        self,
        name: str,
        code: Optional[str] = None,
        id: Optional[uuid.UUID | str] = None,
        metadata: Optional[dict] = None,
    ):
        super().__init__(id=id, metadata=metadata)
        self.name: str = name
        self.code: str = code or name

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({"name": self.name, "code": self.code})
        return d

    def __repr__(self) -> str:
        return f"Project(name={self.name!r}, id={self.id!s:.8}...)"


# ─────────────────────────────────────────────────────────────
# Sequence
# ─────────────────────────────────────────────────────────────

class Sequence(Versionable, BridgeEntity):
    """An ordered collection of shots.

    Could be a reel, episode, scene, or cut. Has a frame rate and
    a total duration.

    Endpoint mappings:
        Flame:    timeline / sequence
        NLE:      sequence / timeline
        ShotGrid: Sequence entity
    """

    def __init__(
        self,
        name: str,
        project_id: Optional[uuid.UUID | str] = None,
        frame_rate: Optional[Fraction | float | str] = None,
        duration: Optional[Timecode] = None,
        id: Optional[uuid.UUID | str] = None,
        metadata: Optional[dict] = None,
    ):
        super().__init__(id=id, metadata=metadata)
        self.name: str = name
        self.project_id: Optional[uuid.UUID] = (
            uuid.UUID(str(project_id)) if project_id else None
        )
        self.frame_rate: Fraction = (
            Fraction(frame_rate).limit_denominator(1001)
            if frame_rate is not None
            else Fraction(24)
        )
        self.duration: Optional[Timecode] = duration

        # Auto-declare relationship to project
        if self.project_id:
            self.add_relationship(self.project_id, RelationshipType.MEMBER_OF)

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "name": self.name,
            "project_id": str(self.project_id) if self.project_id else None,
            "frame_rate": str(self.frame_rate),
            "duration": self.duration.to_dict() if self.duration else None,
        })
        return d

    def __repr__(self) -> str:
        return f"Sequence(name={self.name!r}, id={self.id!s:.8}...)"


# ─────────────────────────────────────────────────────────────
# Shot
# ─────────────────────────────────────────────────────────────

class Shot(Versionable, BridgeEntity):
    """A discrete unit of work with a defined place in a Sequence.

    Has a name (shot code), a duration, and a position within the
    sequence expressed as cut in/out timecodes.

    Endpoint mappings:
        Flame:    segment in timeline
        ShotGrid: Shot entity
        ftrack:   Shot task container
    """

    def __init__(
        self,
        name: str,
        sequence_id: Optional[uuid.UUID | str] = None,
        cut_in: Optional[Timecode] = None,
        cut_out: Optional[Timecode] = None,
        status: Status | str = Status.PENDING,
        id: Optional[uuid.UUID | str] = None,
        metadata: Optional[dict] = None,
    ):
        super().__init__(id=id, metadata=metadata)
        self.name: str = name
        self.sequence_id: Optional[uuid.UUID] = (
            uuid.UUID(str(sequence_id)) if sequence_id else None
        )
        self.cut_in: Optional[Timecode] = cut_in
        self.cut_out: Optional[Timecode] = cut_out
        self.status: Status = (
            Status.from_string(status) if isinstance(status, str) else status
        )

        if self.sequence_id:
            self.add_relationship(self.sequence_id, RelationshipType.MEMBER_OF)

    @property
    def duration(self) -> Optional[int]:
        """Duration in frames, or None if cut points not set."""
        if self.cut_in is not None and self.cut_out is not None:
            return self.cut_out.to_frames() - self.cut_in.to_frames()
        return None

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "name": self.name,
            "sequence_id": str(self.sequence_id) if self.sequence_id else None,
            "cut_in": self.cut_in.to_dict() if self.cut_in else None,
            "cut_out": self.cut_out.to_dict() if self.cut_out else None,
            "duration_frames": self.duration,
            "status": self.status.value,
        })
        return d

    def __repr__(self) -> str:
        return f"Shot(name={self.name!r}, id={self.id!s:.8}...)"


# ─────────────────────────────────────────────────────────────
# Asset
# ─────────────────────────────────────────────────────────────

class Asset(Versionable, BridgeEntity):
    """Anything that isn't a Shot but gets used in one.

    Characters, elements, textures, audio, reference material.

    Endpoint mappings:
        ShotGrid: Asset entity
        ftrack:   Asset
        Flame:    clip in library (typically)
    """

    def __init__(
        self,
        name: str,
        asset_type: str = "generic",
        project_id: Optional[uuid.UUID | str] = None,
        status: Status | str = Status.PENDING,
        id: Optional[uuid.UUID | str] = None,
        metadata: Optional[dict] = None,
    ):
        super().__init__(id=id, metadata=metadata)
        self.name: str = name
        self.asset_type: str = asset_type
        self.project_id: Optional[uuid.UUID] = (
            uuid.UUID(str(project_id)) if project_id else None
        )
        self.status: Status = (
            Status.from_string(status) if isinstance(status, str) else status
        )

        if self.project_id:
            self.add_relationship(self.project_id, RelationshipType.MEMBER_OF)

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "name": self.name,
            "asset_type": self.asset_type,
            "project_id": str(self.project_id) if self.project_id else None,
            "status": self.status.value,
        })
        return d

    def __repr__(self) -> str:
        return f"Asset(name={self.name!r}, type={self.asset_type!r}, id={self.id!s:.8}...)"


# ─────────────────────────────────────────────────────────────
# Version
# ─────────────────────────────────────────────────────────────

class Version(BridgeEntity):
    """A specific iteration of a Shot or Asset at a point in time.

    Versions are immutable once created. A new iteration is always
    a new Version entity with a higher version_number.

    parent_type is "shot" or "asset" — determines what the version
    belongs to.
    """

    def __init__(
        self,
        version_number: int,
        parent_id: Optional[uuid.UUID | str] = None,
        parent_type: str = "shot",
        status: Status | str = Status.PENDING,
        created_by: Optional[str] = None,
        id: Optional[uuid.UUID | str] = None,
        metadata: Optional[dict] = None,
    ):
        super().__init__(id=id, metadata=metadata)
        self.version_number: int = version_number
        self.parent_id: Optional[uuid.UUID] = (
            uuid.UUID(str(parent_id)) if parent_id else None
        )
        self.parent_type: str = parent_type
        self.status: Status = (
            Status.from_string(status) if isinstance(status, str) else status
        )
        self.created_by: Optional[str] = created_by

        if self.parent_id:
            self.add_relationship(self.parent_id, RelationshipType.VERSION_OF)

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "version_number": self.version_number,
            "parent_id": str(self.parent_id) if self.parent_id else None,
            "parent_type": self.parent_type,
            "status": self.status.value,
            "created_by": self.created_by,
        })
        return d

    def __repr__(self) -> str:
        return f"Version(v{self.version_number}, parent={self.parent_id!s:.8}...)"


# ─────────────────────────────────────────────────────────────
# Media
# ─────────────────────────────────────────────────────────────

class Media(Versionable, BridgeEntity):
    """The atomic unit — the actual file or frame sequence on disk.

    Media is the terminus of every data chain. It does not carry
    meaning by itself — meaning is given to it by whatever entity
    references it.

    A single Media entity may exist at multiple Locations simultaneously
    (local cache, network share, cloud). Location is tracked via the
    Locatable trait.

    Endpoint mappings:
        Flame:    clip / media
        NLE:      source clip
        Filesystem: frame sequence or movie file
    """

    def __init__(
        self,
        format: str,
        resolution: Optional[str] = None,
        frame_range: Optional[FrameRange] = None,
        colorspace: Optional[str] = None,
        bit_depth: Optional[str] = None,
        version_id: Optional[uuid.UUID | str] = None,
        id: Optional[uuid.UUID | str] = None,
        metadata: Optional[dict] = None,
    ):
        super().__init__(id=id, metadata=metadata)
        self.format: str = format
        self.resolution: Optional[str] = resolution
        self.frame_range: Optional[FrameRange] = frame_range
        self.colorspace: Optional[str] = colorspace
        self.bit_depth: Optional[str] = bit_depth
        self.version_id: Optional[uuid.UUID] = (
            uuid.UUID(str(version_id)) if version_id else None
        )

        if self.version_id:
            self.add_relationship(self.version_id, RelationshipType.REFERENCES)

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "format": self.format,
            "resolution": self.resolution,
            "frame_range": self.frame_range.to_dict() if self.frame_range else None,
            "colorspace": self.colorspace,
            "bit_depth": self.bit_depth,
            "version_id": str(self.version_id) if self.version_id else None,
        })
        return d

    def __repr__(self) -> str:
        return f"Media(format={self.format!r}, res={self.resolution!r}, id={self.id!s:.8}...)"


# ─────────────────────────────────────────────────────────────
# Layer and Stack
# ─────────────────────────────────────────────────────────────

class Layer(BridgeEntity):
    """A single member of a Stack. Carries a Role assignment.

    In Flame terms: L01, L02, L03 are Layers within a Stack.
    The Role distinguishes them.

    Endpoint mappings:
        Flame: track in a timeline segment stack (L01/L02/L03)
    """

    def __init__(
        self,
        role: Role | str,
        stack_id: Optional[uuid.UUID | str] = None,
        order: int = 0,
        version_id: Optional[uuid.UUID | str] = None,
        id: Optional[uuid.UUID | str] = None,
        metadata: Optional[dict] = None,
    ):
        super().__init__(id=id, metadata=metadata)

        # Accept a Role object or a role name string
        if isinstance(role, str):
            from forge_bridge.core.vocabulary import STANDARD_ROLES
            self.role = STANDARD_ROLES.get(role, Role(role))
        else:
            self.role = role

        self.order: int = order
        self.stack_id: Optional[uuid.UUID] = (
            uuid.UUID(str(stack_id)) if stack_id else None
        )
        self.version_id: Optional[uuid.UUID] = (
            uuid.UUID(str(version_id)) if version_id else None
        )

        if self.stack_id:
            self.add_relationship(self.stack_id, RelationshipType.MEMBER_OF)
        if self.version_id:
            self.add_relationship(self.version_id, RelationshipType.REFERENCES)

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "role": self.role.to_dict(),
            "order": self.order,
            "stack_id": str(self.stack_id) if self.stack_id else None,
            "version_id": str(self.version_id) if self.version_id else None,
        })
        return d

    def __repr__(self) -> str:
        return f"Layer(role={self.role.name!r}, order={self.order}, id={self.id!s:.8}...)"


class Stack(BridgeEntity):
    """A collection of Layers bound together by shared shot identity.

    A Stack is a relationship pattern — it exists when multiple Layers
    all belong to the same Shot. Bridge recognizes this automatically
    from the data structure.

    In Flame: the L01/L02/L03 group for a single shot.
    """

    def __init__(
        self,
        shot_id: Optional[uuid.UUID | str] = None,
        id: Optional[uuid.UUID | str] = None,
        metadata: Optional[dict] = None,
    ):
        super().__init__(id=id, metadata=metadata)
        self.shot_id: Optional[uuid.UUID] = (
            uuid.UUID(str(shot_id)) if shot_id else None
        )
        self._layers: list[Layer] = []

        if self.shot_id:
            self.add_relationship(self.shot_id, RelationshipType.MEMBER_OF)

    def add_layer(self, layer: Layer) -> Layer:
        """Add a Layer to this Stack and set its stack_id."""
        layer.stack_id = self.id
        layer.add_relationship(self.id, RelationshipType.MEMBER_OF)
        self._layers.append(layer)
        self._layers.sort(key=lambda l: l.order)
        # Layers within a stack are peers of each other
        for existing in self._layers:
            if existing.id != layer.id:
                layer.add_relationship(existing.id, RelationshipType.PEER_OF)
        return layer

    def get_layers(self) -> list[Layer]:
        return list(self._layers)

    def get_layer_by_role(self, role_name: str) -> Optional[Layer]:
        for layer in self._layers:
            if layer.role.name == role_name:
                return layer
        return None

    @property
    def depth(self) -> int:
        return len(self._layers)

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "shot_id": str(self.shot_id) if self.shot_id else None,
            "depth": self.depth,
            "layers": [layer.to_dict() for layer in self._layers],
        })
        return d

    def __repr__(self) -> str:
        roles = [l.role.name for l in self._layers]
        return f"Stack(shot={self.shot_id!s:.8}..., layers={roles})"
