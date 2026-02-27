"""
forge-bridge vocabulary types.

Status, Role, Timecode, FrameRange — the supporting types that
entities and traits reference throughout the vocabulary.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from typing import Any, Optional


# ─────────────────────────────────────────────────────────────
# Status
# ─────────────────────────────────────────────────────────────

class Status(str, Enum):
    """Canonical lifecycle status values.

    Pipelines may use different terms (e.g. "work_in_progress" instead
    of "in_progress"). Bridge maps between endpoint-specific terms and
    these canonical values via the vocabulary translation layer.
    """
    PENDING     = "pending"
    IN_PROGRESS = "in_progress"
    REVIEW      = "review"
    APPROVED    = "approved"
    REJECTED    = "rejected"
    DELIVERED   = "delivered"
    ARCHIVED    = "archived"

    @classmethod
    def from_string(cls, value: str) -> "Status":
        """Parse a status string, with common aliases."""
        aliases = {
            "wip":              cls.IN_PROGRESS,
            "work_in_progress": cls.IN_PROGRESS,
            "ip":               cls.IN_PROGRESS,
            "pending_review":   cls.REVIEW,
            "for_review":       cls.REVIEW,
            "final":            cls.DELIVERED,
            "done":             cls.DELIVERED,
            "complete":         cls.DELIVERED,
            "omit":             cls.ARCHIVED,
        }
        normalized = value.lower().strip()
        if normalized in aliases:
            return aliases[normalized]
        try:
            return cls(normalized)
        except ValueError:
            raise ValueError(
                f"Unknown status '{value}'. Valid values: "
                f"{[s.value for s in cls]}"
            )


# ─────────────────────────────────────────────────────────────
# Role
# ─────────────────────────────────────────────────────────────

@dataclass
class Role:
    """A named function that a Layer or entity fulfills.

    Roles are the semantic translation layer. What Flame calls "L01"
    and what ShotGrid calls "primary" and what a Maya pipeline calls
    "hero" are all the same Role — bridge holds the map.

    Roles are also Locatable in a broad sense — they carry path
    template patterns describing where media for that role lives
    in the filesystem.

    Example:
        Role(
            name="primary",
            label="Primary",
            path_template="{project}/{sequence}/{shot}/plates/v{version:04d}",
        )
    """
    name: str                               # canonical name (e.g. "primary")
    label: Optional[str] = None            # display label (e.g. "Primary Plate")
    path_template: Optional[str] = None    # folder path pattern
    order: int = 0                          # default stack position (0-based)
    metadata: dict[str, Any] = field(default_factory=dict)

    # Endpoint-specific name aliases
    # e.g. {"flame": "L01", "shotgrid": "main", "ftrack": "hero"}
    aliases: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if self.label is None:
            self.label = self.name.replace("_", " ").title()

    def resolve_path(self, **tokens) -> Optional[str]:
        """Resolve the path template with given token values.

        Example:
            role.resolve_path(project="EP60", sequence="Seq01",
                              shot="EP60_010", version=4)
            # → "EP60/Seq01/EP60_010/plates/v0004"
        """
        if self.path_template is None:
            return None
        try:
            return self.path_template.format(**tokens)
        except KeyError as e:
            raise ValueError(f"Missing token {e} for role path template '{self.path_template}'")

    def get_alias(self, endpoint: str) -> str:
        """Return the name this role is known by in a specific endpoint."""
        return self.aliases.get(endpoint, self.name)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "label": self.label,
            "path_template": self.path_template,
            "order": self.order,
            "aliases": self.aliases,
            "metadata": self.metadata,
        }


# ─────────────────────────────────────────────────────────────
# Default role registry
# ─────────────────────────────────────────────────────────────
#
# Roles are split into two classes:
#
#   track  — compositional function within a shot's comp stack.
#             Describes what the media *does* in a specific Version.
#             Carried on the edge (consumes relationship attributes),
#             not on the media entity itself.
#             L01/L02/L03 are Flame's slot indices for these roles.
#
#   media  — pipeline stage that *produced* this media atom.
#             Describes what happened to the media to create it.
#             Travels with the media entity as media.attributes.role.
#             Scoped by generation: raw=0, grade/denoise/prep/roto/comp=1+
#
# The same media entity can have a different track role in every Version
# that consumes it — the media role is fixed, the track role is contextual.

STANDARD_ROLES = {
    # ── Track roles (compositional function within a shot Version) ──────────
    "primary":    Role("primary",    order=0, aliases={"flame": "L01", "role_class": "track"}),
    "reference":  Role("reference",  order=1, aliases={"flame": "L02", "role_class": "track"}),
    "matte":      Role("matte",      order=2, aliases={"flame": "L03", "role_class": "track"}),
    "background": Role("background", order=3, aliases={"role_class": "track"}),
    "foreground": Role("foreground", order=4, aliases={"role_class": "track"}),
    "color":      Role("color",      order=5, aliases={"role_class": "track"}),
    "audio":      Role("audio",      order=6, aliases={"role_class": "track"}),

    # ── Media roles (pipeline stage that produced the media) ─────────────────
    # raw: camera source — always generation 0, never produced by a process.
    #      Anything in footage/raw/ is implicitly this role.
    "raw":        Role("raw",        order=10, aliases={"role_class": "media", "generation_floor": "0"}),
    # grade: colour graded plate — generation 1+. Product of a grade process.
    "grade":      Role("grade",      order=11, aliases={"role_class": "media", "generation_floor": "1"}),
    # denoise: noise reduction pass — generation 1+.
    "denoise":    Role("denoise",    order=12, aliases={"role_class": "media", "generation_floor": "1"}),
    # prep: paint / cleanup / rig removal — generation 1+.
    "prep":       Role("prep",       order=13, aliases={"role_class": "media", "generation_floor": "1"}),
    # roto: rotoscope delivery — generation 1+.
    "roto":       Role("roto",       order=14, aliases={"role_class": "media", "generation_floor": "1"}),
    # comp: composite render output — generation 1+.
    "comp":       Role("comp",       order=15, aliases={"role_class": "media", "generation_floor": "1"}),
}


# ─────────────────────────────────────────────────────────────
# Timecode and FrameRange
# ─────────────────────────────────────────────────────────────

@dataclass
class Timecode:
    """A position expressed in hours:minutes:seconds:frames notation.

    Bridge speaks timecode natively. Given a frame rate, it can convert
    between timecode and frame numbers in either direction.

    Examples:
        Timecode(0, 0, 1, 0)          → "00:00:01:00"
        Timecode.from_string("01:02:03:12")
        Timecode.from_frames(1001, fps=Fraction(24000, 1001))
    """
    hours:   int = 0
    minutes: int = 0
    seconds: int = 0
    frames:  int = 0
    fps: Fraction = field(default_factory=lambda: Fraction(24))
    drop_frame: bool = False

    _TC_RE = re.compile(r"^(\d{2})[;:](\d{2})[;:](\d{2})[;:](\d{2})$")

    @classmethod
    def from_string(cls, tc_string: str, fps: Fraction = Fraction(24)) -> "Timecode":
        """Parse a timecode string like '01:00:00:00' or '01;00;00;00'."""
        m = cls._TC_RE.match(tc_string.strip())
        if not m:
            raise ValueError(f"Cannot parse timecode: '{tc_string}'")
        h, m_, s, f = (int(x) for x in m.groups())
        drop = ";" in tc_string
        return cls(hours=h, minutes=m_, seconds=s, frames=f, fps=fps, drop_frame=drop)

    @classmethod
    def from_frames(cls, frame_number: int, fps: Fraction = Fraction(24)) -> "Timecode":
        """Convert an absolute frame number to timecode at the given fps."""
        total_seconds, frames = divmod(frame_number, int(fps))
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return cls(hours=hours, minutes=minutes, seconds=seconds, frames=frames, fps=fps)

    def to_frames(self) -> int:
        """Convert this timecode to an absolute frame number."""
        total_seconds = self.hours * 3600 + self.minutes * 60 + self.seconds
        return int(total_seconds * self.fps) + self.frames

    def __str__(self) -> str:
        sep = ";" if self.drop_frame else ":"
        return f"{self.hours:02d}:{self.minutes:02d}:{self.seconds:02d}{sep}{self.frames:02d}"

    def __repr__(self) -> str:
        return f"Timecode('{self}')"

    def to_dict(self) -> dict:
        return {
            "timecode": str(self),
            "frames": self.to_frames(),
            "fps": str(self.fps),
            "drop_frame": self.drop_frame,
        }


@dataclass
class FrameRange:
    """A start frame, end frame, and duration.

    Bridge treats these as internally consistent — changing one
    recalculates the others. Duration is always end - start + 1
    (inclusive).

    Examples:
        FrameRange(1001, 1100)          → 100 frames
        FrameRange.from_timecodes(tc_in, tc_out, fps=Fraction(24))
    """
    start: int
    end:   int
    fps:   Fraction = field(default_factory=lambda: Fraction(24))

    def __post_init__(self):
        if self.end < self.start:
            raise ValueError(
                f"FrameRange end ({self.end}) must be >= start ({self.start})"
            )

    @classmethod
    def from_timecodes(cls, tc_in: Timecode, tc_out: Timecode) -> "FrameRange":
        """Create a FrameRange from two Timecode positions."""
        if tc_in.fps != tc_out.fps:
            raise ValueError("Timecodes must have the same fps")
        return cls(start=tc_in.to_frames(), end=tc_out.to_frames(), fps=tc_in.fps)

    @property
    def duration(self) -> int:
        """Number of frames (inclusive)."""
        return self.end - self.start + 1

    def to_timecodes(self) -> tuple[Timecode, Timecode]:
        """Return (tc_in, tc_out) as Timecode objects."""
        return (
            Timecode.from_frames(self.start, self.fps),
            Timecode.from_frames(self.end,   self.fps),
        )

    def contains(self, frame: int) -> bool:
        return self.start <= frame <= self.end

    def overlaps(self, other: "FrameRange") -> bool:
        return self.start <= other.end and self.end >= other.start

    def __str__(self) -> str:
        return f"{self.start}-{self.end} ({self.duration} frames @ {self.fps}fps)"

    def to_dict(self) -> dict:
        tc_in, tc_out = self.to_timecodes()
        return {
            "start": self.start,
            "end": self.end,
            "duration": self.duration,
            "fps": str(self.fps),
            "tc_in": str(tc_in),
            "tc_out": str(tc_out),
        }
