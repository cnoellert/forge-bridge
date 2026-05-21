"""Topology-expanding foreach graph primitive.

Phase N initial scope is one body step. The body text is a normal chain step
dispatched through the existing pipeline with iteration-scoped context.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, ClassVar

from forge_bridge.graph.ports import PortContract, PortTopology


_FOREACH_INTENT_RE = re.compile(r"^\s*foreach\s*\(", re.IGNORECASE)


class ForeachParseError(ValueError):
    """Raised when a foreach step cannot be parsed within Phase N scope."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ForeachInputError(ValueError):
    """Raised when foreach receives unsupported input topology."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class IterationResult:
    """Single iteration result emitted by ForEachNode."""

    index: int
    item: dict[str, Any]
    result: dict[str, Any]
    emitted_topology: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "item": self.item,
            "result": self.result,
            "emitted_topology": self.emitted_topology,
        }


def is_foreach_step(text: str) -> bool:
    """Return true when a chain step is a foreach graph node."""
    return bool(isinstance(text, str) and _FOREACH_INTENT_RE.search(text))


def parse_foreach_step(text: str) -> str:
    """Extract the single body step from ``foreach(<step>)``."""
    if not is_foreach_step(text):
        raise ForeachParseError("NOT_FOREACH_STEP", "Step is not a foreach node.")

    stripped = text.strip()
    open_index = stripped.find("(")
    if open_index < 0 or not stripped.endswith(")"):
        raise ForeachParseError(
            "INVALID_FOREACH_BODY",
            "foreach requires a parenthesized body step.",
        )

    depth = 0
    close_index = None
    for index, char in enumerate(stripped[open_index:], start=open_index):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                close_index = index
                break
        if depth < 0:
            break

    if close_index is None or stripped[close_index + 1:].strip():
        raise ForeachParseError(
            "INVALID_FOREACH_BODY",
            "foreach body parentheses are unbalanced.",
        )

    body = stripped[open_index + 1:close_index].strip()
    if not body:
        raise ForeachParseError("EMPTY_FOREACH_BODY", "foreach body is required.")
    if "->" in body:
        raise ForeachParseError(
            "FOREACH_CHAIN_BODY_NOT_SUPPORTED",
            "Phase N foreach accepts one body step only.",
        )
    return body


@dataclass(frozen=True)
class ForEachNode:
    """Prepare iteration inputs and wrap body outputs as IterationResult."""

    body_step: str

    port_contract: ClassVar[PortContract] = PortContract(
        (PortTopology.list_of("item"),),
        PortTopology.iteration_results(),
    )

    def items(self, data: Any) -> list[dict[str, Any]]:
        _key, items = _extract_collection(data)
        return items

    def iteration_payload(self, data: Any, item: dict[str, Any]) -> Any:
        key, _items = _extract_collection(data)
        if _looks_like_manifest(item):
            return dict(item)
        if key is None:
            return [dict(item)]
        if isinstance(data, dict):
            payload = dict(data)
            payload[key] = [dict(item)]
            if isinstance(payload.get("count"), int):
                payload["count"] = 1
            return payload
        return [dict(item)]

    def wrap_result(
        self,
        *,
        index: int,
        item: dict[str, Any],
        result: dict[str, Any],
        emitted_topology: dict[str, str],
    ) -> IterationResult:
        return IterationResult(
            index=index,
            item=dict(item),
            result=dict(result),
            emitted_topology=emitted_topology,
        )

    def envelope(self, iterations: list[IterationResult]) -> dict[str, Any]:
        return {
            "iterations": [iteration.to_dict() for iteration in iterations],
            "foreach": {
                "body": self.body_step,
                "input_count": len(iterations),
                "output_count": len(iterations),
            },
            "count": len(iterations),
        }


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
    "collection",
)
_MANIFEST_MARKERS = frozenset({
    "applied",
    "changes",
    "deleted",
    "disconnected",
    "dry_run",
    "errors",
    "execution_state",
    "if_gate",
    "opened",
    "previous",
    "proposed_changes",
    "propagated",
    "renamed",
    "shots_assigned",
    "skipped",
    "skipped_step",
})


def _extract_collection(data: Any) -> tuple[str | None, list[dict[str, Any]]]:
    if isinstance(data, list):
        if all(isinstance(item, dict) for item in data):
            return None, data
        raise ForeachInputError(
            "INVALID_FOREACH_INPUT",
            "ForEachNode requires list[dict] collection input.",
        )
    if not isinstance(data, dict):
        raise ForeachInputError(
            "INVALID_FOREACH_INPUT",
            "ForEachNode requires collection-shaped graph input.",
        )

    for key in _PREFERRED_COLLECTION_KEYS:
        value = data.get(key)
        if isinstance(value, list) and all(isinstance(item, dict) for item in value):
            return key, value

    list_keys = [
        key for key, value in data.items()
        if isinstance(value, list)
        and all(isinstance(item, dict) for item in value)
    ]
    if len(list_keys) == 1:
        key = list_keys[0]
        return key, data[key]

    raise ForeachInputError(
        "INVALID_FOREACH_INPUT",
        "ForEachNode could not find a single list[dict] collection.",
    )


def _looks_like_manifest(item: dict[str, Any]) -> bool:
    return bool(_MANIFEST_MARKERS & set(item))
