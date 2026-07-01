"""Orchestration service layer (Phase 4B)."""

from forge_bridge.orchestration.discovery import (
    DEFAULT_ENTRY_POINT_GROUP,
    RegistrationOutcome,
    SiblingResolution,
    make_db_event_appender,
    register_all_siblings,
    resolve_siblings,
)
from forge_bridge.orchestration.dispatcher import (
    DispatchResult,
    InvocationEnvelope,
    dispatch_envelope,
    dispatch_plan,
)
from forge_bridge.orchestration.dispatch_consumer import (
    DispatchOnExecutionEntryConsumer,
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
    AmendedIntentLineageError,
    DecisionNotAllowedAtStageError,
    DuplicateToolIdError,
    InvalidGenerationDriverError,
    InvalidManifestRequestError,
    InvalidReconstructionRequestError,
    InvalidStageTransitionError,
    InvalidStatusTransitionError,
    LifecycleStateAlreadyExistsError,
    LifecycleStateNotFoundError,
    ManifestPreconditionError,
    PlannerRefusalError,
    ReplayRefusalError,
    UnknownDecisionEventError,
)
from forge_bridge.orchestration.identity_registries import (
    InMemoryPlatformUUIDRegistry,
    InMemoryTrainedIdentityRegistry,
    PlatformUUIDRegistryProtocol,
    TrainedIdentityRecord,
    TrainedIdentityRegistryProtocol,
)
from forge_bridge.orchestration.lineage_graph import (
    InMemoryLineageGraph,
    LineageGraphProtocol,
)
from forge_bridge.orchestration.planner import (
    REPLAY_REFUSAL_CODES,
    Planner,
    PlannerRefusalCode,
    PlanningContext,
)
from forge_bridge.orchestration.registration import (
    BridgeRegistrationContext,
    RegisterCapabilityCallable,
    RegisterToolCallable,
    ToolRegistration,
    ToolRegistry,
    tool_registration_from_capability,
)
from forge_bridge.orchestration.rule_checks import (
    DEFAULT_PLANNING_RULES,
    PlanningRuleRegistry,
    PlanningRuleViolation,
    default_planning_rule_registry,
)
from forge_bridge.orchestration.event_consumer import (
    ConsumerProcessResult,
    GraphEngineEventConsumer,
)
from forge_bridge.orchestration.manifest import (
    ManifestBody,
    ManifestSubgraphWalker,
    ProvenanceManifestAssembler,
    SnapshotIdSet,
    SubgraphClosure,
)
from forge_bridge.orchestration.replay import (
    ComparisonTarget,
    DimensionPolicy,
    EffectivePinningPolicy,
    PinningMode,
    ReconstructionRequest,
    ReplayEngine,
    SourceRunContext,
)

from forge_bridge.orchestration.worker import GenerationPoller, PollPassResult

__all__ = [
    "GraphEngine",
    "UNSET",
    "GenerationPoller",
    "PollPassResult",
    "InvocationEnvelope",
    "DispatchResult",
    "dispatch_envelope",
    "dispatch_plan",
    "DispatchOnExecutionEntryConsumer",
    "GenerationDriverProtocol",
    "GenerationDriverRegistry",
    "DriverPollResult",
    "DriverReregisteredWarning",
    "resolve_backend_id",
    "BridgeRegistrationContext",
    "ToolRegistration",
    "ToolRegistry",
    "RegisterToolCallable",
    "RegisterCapabilityCallable",
    "tool_registration_from_capability",
    "SiblingResolution",
    "RegistrationOutcome",
    "resolve_siblings",
    "register_all_siblings",
    "make_db_event_appender",
    "DEFAULT_ENTRY_POINT_GROUP",
    "Planner",
    "PlanningContext",
    "PlannerRefusalCode",
    "PlannerRefusalError",
    "REPLAY_REFUSAL_CODES",
    "PlatformUUIDRegistryProtocol",
    "TrainedIdentityRegistryProtocol",
    "InMemoryPlatformUUIDRegistry",
    "InMemoryTrainedIdentityRegistry",
    "TrainedIdentityRecord",
    "LineageGraphProtocol",
    "InMemoryLineageGraph",
    "PlanningRuleRegistry",
    "PlanningRuleViolation",
    "DEFAULT_PLANNING_RULES",
    "default_planning_rule_registry",
    "DecisionNotAllowedAtStageError",
    "DuplicateToolIdError",
    "InvalidGenerationDriverError",
    "InvalidStageTransitionError",
    "InvalidStatusTransitionError",
    "LifecycleStateAlreadyExistsError",
    "LifecycleStateNotFoundError",
    "UnknownDecisionEventError",
    "InvalidReconstructionRequestError",
    "ReplayRefusalError",
    "AmendedIntentLineageError",
    "ReplayEngine",
    "ReconstructionRequest",
    "EffectivePinningPolicy",
    "PinningMode",
    "DimensionPolicy",
    "ComparisonTarget",
    "SourceRunContext",
    "InvalidManifestRequestError",
    "ManifestPreconditionError",
    "ProvenanceManifestAssembler",
    "ManifestSubgraphWalker",
    "ManifestBody",
    "SubgraphClosure",
    "SnapshotIdSet",
    "GraphEngineEventConsumer",
    "ConsumerProcessResult",
]
