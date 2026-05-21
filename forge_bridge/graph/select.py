"""Deterministic identity-selection graph primitive.

SelectNode is topology-preserving: it narrows list[X] to list[X] by exact
identity match. It is not retrieval, ranking, fuzzy matching, or semantic
lookup. Zero and multiple matches are structured failures because SelectNode
does not guess.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from forge_bridge.graph.filter import GraphInputError


_SELECT_INTENT_RE = re.compile(r"^\s*select\s+", re.IGNORECASE)
_SELECT_CALL_RE = re.compile(r"^\s*select\s+(?P<target>.+?)\s*$", re.IGNORECASE)
_IDENTITY_FIELDS = (
    "seg_name",
    "shot_name",
    "sequence_name",
    "node_name",
    "clip_name",
    "name",
    "segment",
    "proposed",
)
_PREFERRED_COLLECTION_KEYS = (
    "proposed_changes",
    "segments",
    "clips",
    "reels",
    "items",
    "iterations",
    "nodes",
    "projects",
    "shots",
    "versions",
    "results",
)


class SelectError(ValueError):
    """Raised when select identity resolution cannot proceed deterministically."""

    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


@dataclass(frozen=True)
class SelectIdentity:
    """Identity target consumed by SelectNode."""

    target: str

    def to_dict(self) -> dict[str, str]:
        return {"target": self.target}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SelectIdentity":
        target = data.get("target")
        if not isinstance(target, str) or not target:
            raise SelectError("INVALID_SELECT_IDENTITY", "Select identity target is required.")
        return cls(target=target)


def is_select_step(text: str) -> bool:
    """Return true when a chain step is a select graph node."""
    return bool(isinstance(text, str) and _SELECT_INTENT_RE.search(text))


def parse_select_step(text: str) -> SelectIdentity:
    """Parse a select step into an exact identity target."""
    if not is_select_step(text):
        raise SelectError("NOT_SELECT_STEP", "Step is not a select graph node.")
    match = _SELECT_CALL_RE.match(text.strip())
    target = match.group("target").strip().strip("\"'") if match else ""
    if not target:
        raise SelectError("INVALID_SELECT_IDENTITY", "Select identity target is required.")
    return SelectIdentity(target=target)


@dataclass(frozen=True)
class SelectNode:
    """Generic select node over collection-shaped graph data."""

    identity: SelectIdentity

    def run(self, data: Any) -> dict[str, Any]:
        key, collection = _extract_select_collection(data)
        matches = [item for item in collection if _matches_identity(item, self.identity.target)]
        if not matches:
            raise SelectError(
                "IDENTITY_NOT_FOUND",
                f"Identity not found: {self.identity.target}",
                details={"target": self.identity.target},
            )
        if len(matches) > 1:
            raise SelectError(
                "IDENTITY_AMBIGUOUS",
                f"Identity is ambiguous: {self.identity.target}",
                details={"target": self.identity.target, "matches": len(matches)},
            )

        selected = matches
        if key is None:
            return {
                "collection": selected,
                "count": len(selected),
                "select": {
                    "target": self.identity.target,
                    "output_count": len(selected),
                },
            }

        result = dict(data)
        result[key] = selected
        if isinstance(result.get("count"), int):
            result["count"] = len(selected)
        result["select"] = {
            "collection": key,
            "target": self.identity.target,
            "output_count": len(selected),
        }
        return result

    def selected_collection(self, data: Any) -> list[dict[str, Any]]:
        key, collection = _extract_select_collection(data)
        matches = [item for item in collection if _matches_identity(item, self.identity.target)]
        if len(matches) != 1:
            self.run(data)
        return matches


def _extract_select_collection(data: Any) -> tuple[str | None, list[dict[str, Any]]]:
    if isinstance(data, list):
        if all(isinstance(item, dict) for item in data):
            return None, data
        raise GraphInputError("invalid_collection", "SelectNode requires list[dict] collection input.")

    if not isinstance(data, dict):
        raise GraphInputError("invalid_collection", "SelectNode requires collection-shaped graph input.")

    for key in _PREFERRED_COLLECTION_KEYS:
        value = data.get(key)
        if isinstance(value, list) and all(isinstance(item, dict) for item in value):
            return key, value

    list_keys = [
        key for key, value in data.items()
        if isinstance(value, list) and all(isinstance(item, dict) for item in value)
    ]
    if len(list_keys) == 1:
        key = list_keys[0]
        return key, data[key]

    raise GraphInputError("invalid_collection", "SelectNode could not find a single list[dict] collection.")


def _matches_identity(item: dict[str, Any], target: str) -> bool:
    for field in _IDENTITY_FIELDS:
        value = item.get(field)
        if value not in (None, ""):
            return str(value) == target
    return False
