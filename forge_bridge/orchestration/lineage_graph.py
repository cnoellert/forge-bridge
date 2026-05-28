"""Lineage graph protocol and v0.1 in-memory implementation (Phase 4B §5)."""

from __future__ import annotations

import uuid
from typing import Protocol


class LineageGraphProtocol(Protocol):
    async def chain_depth_from(self, artifact_id: uuid.UUID) -> int: ...

    async def anchors_of(self, artifact_id: uuid.UUID) -> list[uuid.UUID]: ...

    async def would_violate_anchor_lineage(
        self,
        operator_sequence: list[dict],
    ) -> bool: ...


class InMemoryLineageGraph:
    """v0.1 stub — configurable depths for ranking and rule tests."""

    def __init__(
        self,
        *,
        default_depth: int = 0,
        depths: dict[uuid.UUID, int] | None = None,
        violate_anchor: bool = False,
    ) -> None:
        self._default_depth = default_depth
        self._depths = depths or {}
        self._violate_anchor = violate_anchor

    def set_depth(self, artifact_id: uuid.UUID, depth: int) -> None:
        self._depths[artifact_id] = depth

    def set_violate_anchor(self, violate: bool) -> None:
        self._violate_anchor = violate

    async def chain_depth_from(self, artifact_id: uuid.UUID) -> int:
        return self._depths.get(artifact_id, self._default_depth)

    async def anchors_of(self, artifact_id: uuid.UUID) -> list[uuid.UUID]:
        return []

    async def would_violate_anchor_lineage(
        self,
        operator_sequence: list[dict],
    ) -> bool:
        if self._violate_anchor:
            return True

        output_ids = {
            entry.get("output_artifact_id")
            for entry in operator_sequence
            if entry.get("output_artifact_id")
        }
        for entry in operator_sequence:
            for input_ref in entry.get("inputs", []):
                source = input_ref.get("source_artifact_id")
                if source in output_ids:
                    return True
        return False
