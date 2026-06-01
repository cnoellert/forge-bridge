"""Dispatch authority classification for console routing edges."""
from __future__ import annotations

from typing import Any

_BLOCK_TEMPLATE = (
    "Request stopped before execution. Tool: `{tool_name}`. "
    "Classification: mutating. This path permits read operations only. "
    "Use a ratified operation if you intend to modify project state."
)


def dispatch_authority(tool: Any) -> bool:
    """Return True when a tool must be treated as mutating.

    Fail closed: only ``annotations.readOnlyHint is True`` is read authority.
    Missing annotations, False, or any unknown shape is mutating.
    """
    annotations = getattr(tool, "annotations", None)
    return getattr(annotations, "readOnlyHint", None) is not True


def dispatch_block_message(tool_name: str) -> str:
    """Deterministic operator message for unratified mutation blocks."""
    return _BLOCK_TEMPLATE.format(tool_name=tool_name)
