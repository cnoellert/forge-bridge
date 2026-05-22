"""Commit graph primitive."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, ClassVar

from forge_bridge.graph.mutation import MutationManifest
from forge_bridge.graph.ports import PortContract, PortTopology


_COMMIT_INTENT_RE = re.compile(r"^\s*commit\s*$", re.IGNORECASE)


class CommitError(ValueError):
    """Raised when commit verification cannot proceed."""

    MUTATION_MANIFEST_INVALID = "MUTATION_MANIFEST_INVALID"
    APPLY_COUNTERPART_NOT_DECLARED = "APPLY_COUNTERPART_NOT_DECLARED"
    PLAN_STATE_DRIFT = "PLAN_STATE_DRIFT"

    def __init__(
        self,
        code: str,
        message: str,
        *,
        step_index: int | str | None = None,
        step_text: str | None = None,
        drift_count: int | None = None,
        first_drift_index: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.step_index = step_index
        self.step_text = step_text
        self.drift_count = drift_count
        self.first_drift_index = first_drift_index

    def to_error(self) -> dict[str, Any]:
        error: dict[str, Any] = {
            "type": self.code,
            "message": self.message,
        }
        if self.step_index is not None:
            error["step_index"] = self.step_index
        if self.step_text is not None:
            error["step"] = self.step_text
        if self.code == self.PLAN_STATE_DRIFT:
            error["drift_count"] = int(self.drift_count or 0)
            error["first_drift_index"] = int(self.first_drift_index or 0)
        return error


def is_commit_step(text: str) -> bool:
    """Return true when a chain step is a commit graph node."""
    return bool(isinstance(text, str) and _COMMIT_INTENT_RE.match(text))


def parse_commit_step(text: str) -> None:
    """Validate commit step syntax."""
    if not is_commit_step(text):
        raise CommitError("NOT_COMMIT_STEP", "Step is not a commit node.")
    return None


@dataclass(frozen=True)
class CommitVerification:
    matched: bool
    drift_count: int = 0
    first_drift_index: int | None = None


@dataclass(frozen=True)
class CommitNode:
    """Verify a held mutation manifest against a fresh one."""

    port_contract: ClassVar[PortContract] = PortContract(
        (PortTopology.manifest(),),
        PortTopology.manifest(),
    )

    def verify(
        self,
        held: MutationManifest,
        fresh: MutationManifest,
    ) -> CommitVerification:
        held_plan = held.resolved_plan
        fresh_plan = fresh.resolved_plan
        max_len = max(len(held_plan), len(fresh_plan))
        drift_count = 0
        first_drift_index: int | None = None

        for index in range(max_len):
            held_item = held_plan[index] if index < len(held_plan) else None
            fresh_item = fresh_plan[index] if index < len(fresh_plan) else None
            if held_item == fresh_item:
                continue
            drift_count += 1
            if first_drift_index is None:
                first_drift_index = index

        return CommitVerification(
            matched=drift_count == 0,
            drift_count=drift_count,
            first_drift_index=first_drift_index,
        )
