"""Orchestration exceptions (Phase 4B §6, §9)."""

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


class PlannerRefusalError(Exception):
    def __init__(self, refusal_code: str, explanation: str) -> None:
        self.refusal_code = refusal_code
        self.explanation = explanation
        super().__init__(f"Planner refused ({refusal_code}): {explanation}")


class InvalidReconstructionRequestError(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Invalid reconstruction request: {reason}")


class ReplayRefusalError(Exception):
    def __init__(self, refusal_code: str, explanation: str) -> None:
        self.refusal_code = refusal_code
        self.explanation = explanation
        super().__init__(f"Replay refused ({refusal_code}): {explanation}")


class AmendedIntentLineageError(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Amended intent lineage error: {reason}")


class InvalidManifestRequestError(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Invalid manifest request: {reason}")


class ManifestPreconditionError(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Manifest precondition failed: {reason}")


class DuplicateToolIdError(Exception):
    def __init__(self, tool_id: str) -> None:
        self.tool_id = tool_id
        super().__init__(f"Duplicate tool_id registration: {tool_id!r}")


class InvalidGenerationDriverError(Exception):
    def __init__(self, tool_id: str, reason: str) -> None:
        self.tool_id = tool_id
        self.reason = reason
        super().__init__(
            f"Invalid generation driver for tool_id={tool_id!r}: {reason}"
        )


class GenerationDriverRegistrationError(Exception):
    """Base class for generation driver registry rejection."""


class DuplicateGenerationDriverError(GenerationDriverRegistrationError):
    def __init__(self, backend_id: str) -> None:
        self.backend_id = backend_id
        super().__init__(f"Duplicate generation driver backend_id: {backend_id!r}")


class GenerationDriverBackendIdMismatchError(GenerationDriverRegistrationError):
    def __init__(self, triple_backend_id: str, driver_backend_id: str) -> None:
        self.triple_backend_id = triple_backend_id
        self.driver_backend_id = driver_backend_id
        super().__init__(
            "Generation driver backend_id mismatch: "
            f"backend_identity_triple resolves to {triple_backend_id!r}, "
            f"driver.backend_id is {driver_backend_id!r}"
        )


class MissingGenerationDriverBackendIdError(GenerationDriverRegistrationError):
    def __init__(self) -> None:
        super().__init__(
            "Generation driver must provide a resolvable backend_identity_triple "
            "or a backend_id"
        )
