"""Typed port compatibility contract for graph chain wiring.

Typed ports are runtime compatibility contracts between graph nodes. They are
validated locally at the dispatch edge for the next step, not during a separate
graph-construction or preflight phase.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PortTopology:
    """Minimum topology descriptor used by Phase N chain-wire validation."""

    kind: str
    item_type: str = "any"
    cardinality: str = "many"

    @classmethod
    def any(cls) -> "PortTopology":
        return cls("any")

    @classmethod
    def scalar(cls) -> "PortTopology":
        return cls("scalar")

    @classmethod
    def manifest(cls) -> "PortTopology":
        return cls("manifest")

    @classmethod
    def list_of(cls, item_type: str = "any") -> "PortTopology":
        return cls("list", item_type or "any")

    @classmethod
    def single_item(cls, item_type: str = "any") -> "PortTopology":
        return cls("list", item_type or "any", "single")

    @classmethod
    def iteration_results(cls) -> "PortTopology":
        return cls("list", "IterationResult")

    def accepts(self, actual: "PortTopology") -> bool:
        """Return true when ``actual`` can be wired into this expected port."""
        if self.kind == "any" or actual.kind == "any":
            return True
        if self.kind != actual.kind:
            return False
        if self.kind != "list":
            return True
        return self.item_type in {"any", "item"} or actual.item_type in {
            "any",
            "item",
        } or self.item_type == actual.item_type

    def to_dict(self) -> dict[str, str]:
        data = {"kind": self.kind}
        if self.kind == "list":
            data["item_type"] = self.item_type
            if self.cardinality != "many":
                data["cardinality"] = self.cardinality
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PortTopology":
        return cls(
            kind=str(data.get("kind", "any")),
            item_type=str(data.get("item_type", "any")),
            cardinality=str(data.get("cardinality", "many")),
        )


@dataclass(frozen=True)
class PortContract:
    """Input/output topology declaration for a graph step."""

    accepts: tuple[PortTopology, ...]
    emits: PortTopology

    @classmethod
    def passthrough_list(cls) -> "PortContract":
        return cls((PortTopology.list_of("item"),), PortTopology.list_of("item"))

    @classmethod
    def manifest_gate(cls) -> "PortContract":
        return cls((PortTopology.manifest(),), PortTopology.manifest())

    @classmethod
    def select(cls) -> "PortContract":
        return cls(
            (PortTopology.list_of("item"), PortTopology.manifest()),
            PortTopology.list_of("item"),
        )

    @classmethod
    def any(cls) -> "PortContract":
        return cls((PortTopology.any(),), PortTopology.any())

    def accepts_topology(self, actual: PortTopology) -> bool:
        return any(expected.accepts(actual) for expected in self.accepts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepts": [topology.to_dict() for topology in self.accepts],
            "emits": self.emits.to_dict(),
        }


class ChainWireCompatibilityError(ValueError):
    """Raised when adjacent chain steps have incompatible typed ports."""

    code = "CHAIN_WIRE_COMPATIBILITY_ERROR"

    def __init__(
        self,
        *,
        step_index: int | str,
        step_text: str,
        expected: tuple[PortTopology, ...],
        actual: PortTopology,
    ) -> None:
        self.step_index = step_index
        self.step_text = step_text
        self.expected = expected
        self.actual = actual
        message = (
            f"Step {step_index} cannot accept previous topology "
            f"{actual.to_dict()}; expected one of "
            f"{[topology.to_dict() for topology in expected]}."
        )
        super().__init__(message)
        self.message = message

    def to_error(self) -> dict[str, Any]:
        return {
            "type": self.code,
            "message": self.message,
            "step_index": self.step_index,
            "step": self.step_text,
            "expected": [topology.to_dict() for topology in self.expected],
            "actual": self.actual.to_dict(),
        }


_MANIFEST_MARKERS = frozenset({
    "applied",
    "changes",
    "collect",
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
_COLLECTION_ITEM_TYPES = {
    "clips": "clip",
    "collection": "item",
    "items": "item",
    "iterations": "IterationResult",
    "nodes": "node",
    "projects": "project",
    "reels": "reel",
    "results": "result",
    "segments": "segment",
    "shots": "shot",
    "versions": "version",
}


def infer_topology(value: Any) -> PortTopology:
    """Infer the emitted topology of a graph value at a chain boundary."""
    if isinstance(value, dict) and value.get("type") == "mutation_plan":
        return PortTopology.manifest()

    if isinstance(value, list):
        if all(isinstance(item, dict) for item in value):
            return PortTopology.list_of("item")
        return PortTopology.scalar()

    if not isinstance(value, dict):
        return PortTopology.scalar()

    if _MANIFEST_MARKERS & set(value):
        return PortTopology.manifest()

    for key, item_type in _COLLECTION_ITEM_TYPES.items():
        collection = value.get(key)
        if isinstance(collection, list) and all(
            isinstance(item, dict) for item in collection
        ):
            return PortTopology.list_of(item_type)

    list_keys = [
        key for key, collection in value.items()
        if isinstance(collection, list)
        and all(isinstance(item, dict) for item in collection)
    ]
    if len(list_keys) == 1:
        return PortTopology.list_of(_COLLECTION_ITEM_TYPES.get(list_keys[0], "item"))

    return PortTopology.manifest()


def infer_iteration_item_topology(
    *,
    item: dict[str, Any],
    collection_topology: PortTopology,
) -> PortTopology:
    """Infer the topology seen by a foreach body for one iteration item."""
    if isinstance(item, dict) and item.get("type") == "mutation_plan":
        return PortTopology.manifest()
    if _MANIFEST_MARKERS & set(item):
        return PortTopology.manifest()
    if collection_topology.kind == "list":
        return PortTopology.single_item(collection_topology.item_type)
    return PortTopology.single_item("item")


def validate_chain_wire(
    *,
    step_index: int | str,
    step_text: str,
    contract: PortContract,
    actual: PortTopology,
) -> None:
    """Validate one adjacent chain edge immediately before dispatch."""
    if not contract.accepts_topology(actual):
        raise ChainWireCompatibilityError(
            step_index=step_index,
            step_text=step_text,
            expected=contract.accepts,
            actual=actual,
        )
