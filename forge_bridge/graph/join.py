"""Deterministic attribute-match fan-in graph primitive.

JoinNode pairs each item of a ``left`` collection with the one item of a
``right`` collection whose attribute value matches (name-match). It is pure,
reads-only, and applies no host mutation: it emits the left collection enriched
with its matched right item nested under a key. It is the fan-in primitive
behind the slate-insert editorial vertical.

Matching is exact string equality by default; an optional casefold+strip
normalization applies only when explicitly requested. Zero and multiple matches
are structured failures because JoinNode does not guess, and a nesting-key
collision fails closed rather than clobbering the left item.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from forge_bridge.graph.ports import PortContract, PortTopology


_PREFERRED_COLLECTION_KEYS = (
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


class JoinError(ValueError):
    """Raised when join pairing cannot proceed deterministically."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class JoinSpec:
    """Attribute-match pairing target consumed by JoinNode."""

    left_key: str
    right_key: str = ""      # empty → use left_key
    into: str = "joined"
    normalize: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "left_key": self.left_key,
            "right_key": self.right_key,
            "into": self.into,
            "normalize": self.normalize,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JoinSpec":
        left_key = data.get("left_key")
        if not isinstance(left_key, str) or not left_key:
            raise JoinError("join_invalid_spec", "Join left_key is required.")
        return cls(
            left_key=left_key,
            right_key=data.get("right_key", "") or "",
            into=data.get("into", "joined") or "joined",
            normalize=bool(data.get("normalize", False)),
        )


@dataclass(frozen=True)
class JoinNode:
    """Generic attribute-match join node over two collection-shaped graph inputs."""

    port_contract: ClassVar[PortContract] = PortContract(
        (PortTopology.list_of("item"),),
        PortTopology.list_of("item"),
    )

    spec: JoinSpec

    def run(self, left: Any, right: Any) -> dict[str, Any]:
        left_container_key, left_collection = _extract_collection(left, "left")
        _, right_collection = _extract_collection(right, "right")

        left_attr = self.spec.left_key
        right_attr = self.spec.right_key or self.spec.left_key

        index: dict[Any, list[dict[str, Any]]] = {}
        for item in right_collection:
            if right_attr not in item:
                raise JoinError(
                    "join_key_missing",
                    f"right item is missing join key '{right_attr}'",
                )
            index.setdefault(self._norm(item[right_attr]), []).append(item)

        joined: list[dict[str, Any]] = []
        for item in left_collection:
            if left_attr not in item:
                raise JoinError(
                    "join_key_missing",
                    f"left item is missing join key '{left_attr}'",
                )
            value = item[left_attr]
            matches = index.get(self._norm(value), [])
            if not matches:
                raise JoinError("join_miss", f"left key '{value}' had no right match")
            if len(matches) > 1:
                raise JoinError(
                    "join_ambiguous",
                    f"left key '{value}' matched {len(matches)} right items",
                )
            if self.spec.into in item:
                raise JoinError(
                    "join_collision",
                    f"left item already has key '{self.spec.into}'",
                )
            joined.append({**item, self.spec.into: matches[0]})

        provenance = {
            "left_count": len(left_collection),
            "right_count": len(right_collection),
            "matched": len(joined),
            "left_key": left_attr,
            "right_key": right_attr,
            "normalize": self.spec.normalize,
        }

        if left_container_key is None:
            return {
                "collection": joined,
                "count": len(joined),
                "join": provenance,
            }

        result = dict(left)
        result[left_container_key] = joined
        if isinstance(result.get("count"), int):
            result["count"] = len(joined)
        result["join"] = provenance
        return result

    def _norm(self, value: Any) -> Any:
        if self.spec.normalize:
            return str(value).casefold().strip()
        return value


def _extract_collection(data: Any, side: str) -> tuple[str | None, list[dict[str, Any]]]:
    if isinstance(data, list):
        if all(isinstance(item, dict) for item in data):
            return None, data
        raise JoinError("join_invalid_input", f"JoinNode requires list[dict] {side} collection input.")

    if not isinstance(data, dict):
        raise JoinError("join_invalid_input", f"JoinNode requires a {side} collection.")

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

    raise JoinError("join_invalid_input", f"JoinNode could not find a single list[dict] {side} collection.")
