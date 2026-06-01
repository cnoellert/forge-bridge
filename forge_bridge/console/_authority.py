"""Dispatch authority classification for console routing edges."""
from __future__ import annotations

from typing import Any


def dispatch_authority(tool: Any) -> bool:
    """Return True when a tool must be treated as mutating.

    Fail closed: only ``annotations.readOnlyHint is True`` is read authority.
    Missing annotations, False, or any unknown shape is mutating.
    """
    annotations = getattr(tool, "annotations", None)
    return getattr(annotations, "readOnlyHint", None) is not True
