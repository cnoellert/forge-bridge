"""Orchestration service layer (Phase 4B)."""

from forge_bridge.orchestration.discovery import (
    DEFAULT_CAPABILITY_KINDS,
    DEFAULT_ENTRY_POINT_GROUP,
    RegistrationOutcome,
    SiblingResolution,
    make_db_event_appender,
    register_all_siblings,
    resolve_siblings,
)
from forge_bridge.orchestration.drivers import (
    DriverPollResult,
    DriverReregisteredWarning,
    GenerationDriverProtocol,
    GenerationDriverRegistry,
    resolve_backend_id,
)
from forge_bridge.orchestration.engine import GraphEngine, UNSET
from forge_bridge.orchestration.errors import (
    DecisionNotAllowedAtStageError,
    DuplicateToolIdError,
    InvalidGenerationDriverError,
    InvalidStageTransitionError,
    InvalidStatusTransitionError,
    LifecycleStateAlreadyExistsError,
    LifecycleStateNotFoundError,
    UnknownDecisionEventError,
)
from forge_bridge.orchestration.registration import (
    BridgeRegistrationContext,
    RegisterToolCallable,
    ToolRegistration,
    ToolRegistry,
)
from forge_bridge.orchestration.worker import GenerationPoller, PollPassResult

__all__ = [
    "GraphEngine",
    "UNSET",
    "GenerationPoller",
    "PollPassResult",
    "GenerationDriverProtocol",
    "GenerationDriverRegistry",
    "DriverPollResult",
    "DriverReregisteredWarning",
    "resolve_backend_id",
    "BridgeRegistrationContext",
    "ToolRegistration",
    "ToolRegistry",
    "RegisterToolCallable",
    "SiblingResolution",
    "RegistrationOutcome",
    "resolve_siblings",
    "register_all_siblings",
    "make_db_event_appender",
    "DEFAULT_CAPABILITY_KINDS",
    "DEFAULT_ENTRY_POINT_GROUP",
    "DecisionNotAllowedAtStageError",
    "DuplicateToolIdError",
    "InvalidGenerationDriverError",
    "InvalidStageTransitionError",
    "InvalidStatusTransitionError",
    "LifecycleStateAlreadyExistsError",
    "LifecycleStateNotFoundError",
    "UnknownDecisionEventError",
]
