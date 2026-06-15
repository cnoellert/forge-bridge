"""Human-review staging graph primitive.

StageNode is a routing terminus: it collapses a deterministic assessment into a
staged human-review item. It never emits a mutation manifest and never implies
that approval will trigger downstream action.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, ClassVar

from forge_bridge.graph.filter import GraphInputError
from forge_bridge.graph.ports import PortContract
from forge_bridge.store.staged_operations import StagedOpRepo


_STAGE_INTENT_RE = re.compile(r"^\s*stage\s*\(", re.IGNORECASE)
_STAGE_CALL_RE = re.compile(
    r"^\s*stage\s*\(\s*(?P<kind>[A-Za-z0-9_]+)\s*\)\s*$",
    re.IGNORECASE,
)
_REVIEW_OPERATION = {
    "ee_drift_review": "ee_review.drifted",
    "ee_needs_human_look": "ee_review.needs_human_look",
}
_PROPOSER = "bridge.ee_routing"
_TERMINUS = "human_review_only — no downstream action fires on approval (action-real deferred)"


class StageError(ValueError):
    """Raised when a stage graph step cannot proceed deterministically."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def is_stage_step(text: str) -> bool:
    """Return true when a chain step is a stage graph node."""
    return bool(isinstance(text, str) and _STAGE_INTENT_RE.search(text))


def parse_stage_step(text: str) -> str:
    """Parse a closed-vocabulary human-review stage step."""
    if not is_stage_step(text):
        raise StageError("NOT_STAGE_STEP", "Step is not a stage graph node.")

    match = _STAGE_CALL_RE.match(text.strip())
    review_kind = match.group("kind") if match else ""
    if review_kind not in _REVIEW_OPERATION:
        raise StageError(
            "UNKNOWN_STAGE_KIND",
            f"Unsupported stage review kind: {review_kind!r}.",
        )
    return review_kind


def _ee_assessment_to_staged_params(assessment: dict[str, Any]) -> dict[str, Any]:
    """Project an EE assessment into the staged-operation parameter contract."""
    artifact = assessment["artifact"]
    return {
        "assessment_reason": artifact["assessment_reason"],
        "disposition": assessment["disposition"],
        "source_characterization_id": artifact["source_characterization_id"],
        "comp_characterization_id": artifact["comp_characterization_id"],
        "terminus": _TERMINUS,
    }


@dataclass(frozen=True)
class StageNode:
    """Collapse a gated assessment into a staged human-review operation."""

    port_contract: ClassVar[PortContract] = PortContract.manifest_gate()

    review_kind: str

    def parameters(self, assessment: Any) -> dict[str, Any]:
        if not isinstance(assessment, dict):
            raise GraphInputError(
                "invalid_assessment",
                "StageNode requires a previous assessment manifest.",
            )
        try:
            # Deliberately exclude top-level ``verdict`` from the human-review
            # parameters: presenting a verdict pre-empts the human authority this
            # stage exists to preserve.
            return _ee_assessment_to_staged_params(assessment)
        except (KeyError, TypeError) as exc:
            raise GraphInputError(
                "invalid_assessment",
                f"StageNode assessment is missing required field: {exc}",
            ) from exc

    async def run(self, assessment: Any, *, session: Any) -> dict[str, Any]:
        if self.review_kind not in _REVIEW_OPERATION:
            raise StageError(
                "UNKNOWN_STAGE_KIND",
                f"Unsupported stage review kind: {self.review_kind!r}.",
            )

        params = self.parameters(assessment)
        repo = StagedOpRepo(session)
        op = await repo.propose(
            operation=_REVIEW_OPERATION[self.review_kind],
            proposer=_PROPOSER,
            parameters=params,
        )
        return {
            "type": "staged_for_review",
            "staged_operation_id": str(op.id),
            "disposition": params["disposition"],
            "review_kind": self.review_kind,
        }

    @property
    def operation(self) -> str:
        return _REVIEW_OPERATION[self.review_kind]

    @property
    def proposer(self) -> str:
        return _PROPOSER
