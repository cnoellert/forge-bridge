"""Authority-transition commit graph primitive.

CommitNode is the substrate's first host-mutating primitive: it is the
operator-ratified boundary where a previewed mutation may become an applied
one. It orchestrates the preview->apply authority transition by verifying a
held mutation manifest against a freshly recomputed one before the underlying
mutation tool is allowed to apply.

Commit does not define the mutation tool's discover, verify, or apply modes;
those modes live on the tool underneath, such as flame_rename_shots. Commit's
role is to ratify that the previewed plan still matches the fresh plan at the
moment authority crosses from inspection to host mutation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, Optional

from forge_bridge.graph.mutation import MutationManifest
from forge_bridge.graph.ports import PortContract, PortTopology

if TYPE_CHECKING:
    from forge_bridge.core.assent import AssentRecord


_COMMIT_INTENT_RE = re.compile(r"^\s*commit\s*$", re.IGNORECASE)


class CommitError(ValueError):
    """Raised when commit verification cannot proceed."""

    MUTATION_MANIFEST_INVALID = "MUTATION_MANIFEST_INVALID"
    APPLY_COUNTERPART_NOT_DECLARED = "APPLY_COUNTERPART_NOT_DECLARED"
    PLAN_STATE_DRIFT = "PLAN_STATE_DRIFT"
    ASSENT_INVALID = "ASSENT_INVALID"
    APPLY_FAILED = "APPLY_FAILED"

    def __init__(
        self,
        code: str,
        message: str,
        *,
        step_index: int | str | None = None,
        step_text: str | None = None,
        drift_count: int | None = None,
        first_drift_index: int | None = None,
        graph_intent_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.step_index = step_index
        self.step_text = step_text
        self.drift_count = drift_count
        self.first_drift_index = first_drift_index
        self.graph_intent_id = graph_intent_id

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
        if self.code == self.ASSENT_INVALID and self.graph_intent_id is not None:
            error["graph_intent_id"] = self.graph_intent_id
        return error


def is_commit_step(text: str) -> bool:
    """Return true when a chain step is a commit graph node."""
    return bool(isinstance(text, str) and _COMMIT_INTENT_RE.match(text))


def parse_commit_step(text: str) -> None:
    """Validate commit step syntax.

    The syntax is exactly the bare word ``commit``: no arguments, no inline
    body. The parser accepts it case-insensitively with surrounding whitespace
    allowed, and rejects every other shape before host-mutation authority can
    proceed.
    """
    if not is_commit_step(text):
        raise CommitError("NOT_COMMIT_STEP", "Step is not a commit node.")
    return None


def graph_contains_commit_node(steps: list[str]) -> bool:
    """Return true when any chain step is a commit graph node."""
    return any(is_commit_step(step) for step in steps)


@dataclass(frozen=True)
class CommitVerification:
    matched: bool
    drift_count: int = 0
    first_drift_index: int | None = None
    assent_valid: bool = True
    assent_record: Optional["AssentRecord"] = None


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
        assent: Optional["AssentRecord"] = None,
    ) -> CommitVerification:
        if assent is not None:
            from forge_bridge.core.assent import AssentRecord

            if not isinstance(assent, AssentRecord):
                raise TypeError(
                    f"assent must be AssentRecord or None, got {type(assent)!r}"
                )
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
            assent_valid=assent is None or assent.status == "ratified",
            assent_record=assent,
        )
