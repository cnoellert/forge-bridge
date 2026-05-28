"""GraphEngine exceptions (Phase 4B §6)."""

from __future__ import annotations

import uuid


class LifecycleStateNotFoundError(Exception):
    def __init__(self, run_id: uuid.UUID) -> None:
        self.run_id = run_id
        super().__init__(f"No orchestration lifecycle state for run_id={run_id}")


class LifecycleStateAlreadyExistsError(Exception):
    def __init__(self, run_id: uuid.UUID) -> None:
        self.run_id = run_id
        super().__init__(f"Orchestration lifecycle state already exists for run_id={run_id}")


class InvalidStageTransitionError(Exception):
    def __init__(self, from_stage: str, to_stage: str) -> None:
        self.from_stage = from_stage
        self.to_stage = to_stage
        super().__init__(
            f"Invalid stage transition: {from_stage!r} -> {to_stage!r}"
        )


class InvalidStatusTransitionError(Exception):
    def __init__(self, from_status: str, to_status: str, at_stage: str) -> None:
        self.from_status = from_status
        self.to_status = to_status
        self.at_stage = at_stage
        super().__init__(
            f"Invalid status transition at stage {at_stage!r}: "
            f"{from_status!r} -> {to_status!r}"
        )


class UnknownDecisionEventError(Exception):
    def __init__(self, decision_type: str) -> None:
        self.decision_type = decision_type
        super().__init__(f"Unknown decision event type: {decision_type!r}")


class DecisionNotAllowedAtStageError(Exception):
    def __init__(self, decision_type: str, current_stage: str) -> None:
        self.decision_type = decision_type
        self.current_stage = current_stage
        super().__init__(
            f"Decision {decision_type!r} is not allowed at stage {current_stage!r}"
        )
