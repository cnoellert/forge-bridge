"""Replay execution engine (Phase 4B §7)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from forge_bridge.core.traits import Relationship
from forge_bridge.orchestration.engine import GraphEngine
from forge_bridge.orchestration.errors import (
    AmendedIntentLineageError,
    InvalidReconstructionRequestError,
    ReplayRefusalError,
)
from forge_bridge.orchestration.planner import Planner
from forge_bridge.store.models import DBOrchestrationLifecycleState
from forge_bridge.store.orch_capability_snapshot_repo import CapabilitySnapshotRepo
from forge_bridge.store.orch_entity_views import (
    DBOrchExecutionPlan,
    DBOrchLockedIntent,
    DBOrchSpecConvergenceTrace,
)
from forge_bridge.store.orch_execution_plan_repo import ExecutionPlanRepo
from forge_bridge.store.orch_locked_intent_repo import LockedIntentRepo
from forge_bridge.store.orch_partial_fidelity_snapshot_repo import (
    PartialFidelitySnapshotRepo,
)
from forge_bridge.store.orch_pipeline_run_repo import PipelineRunRepo
from forge_bridge.store.orch_rule_snapshot_repo import RuleSnapshotRepo
from forge_bridge.store.orch_spec_convergence_trace_repo import SpecConvergenceTraceRepo
from forge_bridge.store.orchestration_lifecycle_state_repo import (
    OrchestrationLifecycleStateRepo,
)
from forge_bridge.store.repo import EventRepo, RelationshipRepo

PinningMode = Literal["honor_original", "refresh_current"]
DimensionPolicy = Literal["honor_pinning", "honor_snapshot", "refresh_current"]
ComparisonTarget = Literal["compare_against_original", "independent"]

RUN_LINEAGE_REL_KEYS: dict[str, uuid.UUID] = {
    "replays_run": uuid.UUID("00000000-0000-0000-0040-000000000005"),
    "remediates_run": uuid.UUID("00000000-0000-0000-0040-000000000006"),
    "amends_run": uuid.UUID("00000000-0000-0000-0040-000000000007"),
}

FEASIBLE_VERDICTS = frozenset({"feasible", "constrained-but-feasible"})


def _global_policy_for_dimension(
    pinning_mode: PinningMode,
    dimension: str,
) -> DimensionPolicy:
    if pinning_mode == "refresh_current":
        return "refresh_current"
    if dimension in {"backend", "identity"}:
        return "honor_pinning"
    return "honor_snapshot"


def _source_run_is_eligible(
    lifecycle: DBOrchestrationLifecycleState,
    *,
    kind: Literal["replay", "remediation"],
) -> bool:
    if lifecycle.current_stage == "publish" and lifecycle.status == "completed":
        return True
    if kind != "remediation":
        return False
    if lifecycle.current_stage != "execution" or lifecycle.status != "paused":
        return False
    block = lifecycle.block if isinstance(lifecycle.block, dict) else {}
    return (
        block.get("kind") == "awaiting_decision"
        and block.get("decision_type") == "approve_remediation"
    )


@dataclass(frozen=True)
class ReconstructionRequest:
    request_id: uuid.UUID
    kind: Literal["replay", "remediation"]
    source_run_id: uuid.UUID
    remediation_entry: (
        Literal[
            "new_attempt_same_plan",
            "replan_same_intent",
            "replan_amended_intent",
        ]
        | None
    ) = None
    pinning_mode: PinningMode = "honor_original"
    backend_policy: DimensionPolicy | None = None
    rules_policy: DimensionPolicy | None = None
    capability_policy: DimensionPolicy | None = None
    partial_fidelity_policy: DimensionPolicy | None = None
    identity_policy: DimensionPolicy | None = None
    comparison_target: ComparisonTarget = "compare_against_original"
    authored_at: datetime | None = None
    authored_by: str = "operator"

    def __post_init__(self) -> None:
        if self.kind == "remediation" and self.remediation_entry is None:
            raise InvalidReconstructionRequestError(
                "remediation kind requires remediation_entry"
            )
        if self.kind == "replay" and self.remediation_entry is not None:
            raise InvalidReconstructionRequestError(
                "replay kind forbids remediation_entry"
            )


@dataclass(frozen=True)
class EffectivePinningPolicy:
    backend: DimensionPolicy
    rules: DimensionPolicy
    capability: DimensionPolicy
    partial_fidelity: DimensionPolicy
    identity: DimensionPolicy

    @classmethod
    def from_request(cls, req: ReconstructionRequest) -> EffectivePinningPolicy:
        return cls(
            backend=req.backend_policy
            or _global_policy_for_dimension(req.pinning_mode, "backend"),
            rules=req.rules_policy
            or _global_policy_for_dimension(req.pinning_mode, "rules"),
            capability=req.capability_policy
            or _global_policy_for_dimension(req.pinning_mode, "capability"),
            partial_fidelity=req.partial_fidelity_policy
            or _global_policy_for_dimension(req.pinning_mode, "partial_fidelity"),
            identity=req.identity_policy
            or _global_policy_for_dimension(req.pinning_mode, "identity"),
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "backend": self.backend,
            "rules": self.rules,
            "capability": self.capability,
            "partial_fidelity": self.partial_fidelity,
            "identity": self.identity,
        }


@dataclass(frozen=True)
class SourceRunContext:
    lifecycle: DBOrchestrationLifecycleState
    plan: DBOrchExecutionPlan
    intent: DBOrchLockedIntent
    spec_convergence_trace: DBOrchSpecConvergenceTrace | None
    rule_snapshot_id: uuid.UUID
    capability_snapshot_id: uuid.UUID
    partial_fidelity_snapshot_id: uuid.UUID
    pipeline_run: Any
    authored_at: datetime


class ReplayEngine:
    """Thin orchestrator over Planner + GraphEngine."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        graph_engine: GraphEngine,
        planner: Planner,
    ) -> None:
        self.session = session
        self.graph_engine = graph_engine
        self.planner = planner
        self._events = EventRepo(session)

    async def reconstruct(
        self,
        request: ReconstructionRequest,
        *,
        amended_intent_id: uuid.UUID | None = None,
        current_rule_snapshot_id: uuid.UUID | None = None,
        current_partial_fidelity_snapshot_id: uuid.UUID | None = None,
        current_capability_snapshot_id: uuid.UUID | None = None,
    ) -> DBOrchestrationLifecycleState:
        if (
            request.remediation_entry == "replan_amended_intent"
            and amended_intent_id is None
        ):
            raise InvalidReconstructionRequestError(
                "replan_amended_intent requires amended_intent_id"
            )

        effective_policy = EffectivePinningPolicy.from_request(request)
        await self._emit_event(
            "replay_initiated",
            {
                "request_id": str(request.request_id),
                "kind": request.kind,
                "remediation_entry": request.remediation_entry,
                "source_run_id": str(request.source_run_id),
                "new_run_id": None,
                "effective_pinning_policy": effective_policy.as_dict(),
            },
        )

        try:
            source_ctx = await self._load_source_run_context(
                request.source_run_id,
                kind=request.kind,
            )
            if source_ctx.spec_convergence_trace is None:
                raise ReplayRefusalError(
                    "spec_convergence_trace_missing",
                    "Source run is missing spec convergence trace",
                )

            rule_snapshot_id = await self._resolve_pinned_dimension(
                "rules",
                effective_policy.rules,
                source_ctx,
                current_rule_snapshot_id,
            )
            partial_snapshot_id = await self._resolve_pinned_dimension(
                "partial_fidelity",
                effective_policy.partial_fidelity,
                source_ctx,
                current_partial_fidelity_snapshot_id,
            )
            capability_snapshot_id = await self._resolve_pinned_dimension(
                "capability",
                effective_policy.capability,
                source_ctx,
                current_capability_snapshot_id,
            )

            intent_id, lineage_rel = await self._resolve_intent_and_lineage(
                request,
                source_ctx,
                amended_intent_id=amended_intent_id,
            )

            new_run = await self._create_pipeline_run(
                request,
                source_ctx,
                effective_policy,
            )
            await self._create_lineage_edge(new_run.id, request.source_run_id, lineage_rel)
            await self._emit_event(
                "replay_new_run_created",
                {
                    "request_id": str(request.request_id),
                    "new_run_id": str(new_run.id),
                    "source_run_id": str(request.source_run_id),
                    "lineage_relationship": lineage_rel,
                },
            )

            await self.graph_engine.create_run(
                run_id=new_run.id,
                shot_id=source_ctx.lifecycle.shot_id,
                intent_id=intent_id,
            )
            await self.graph_engine.transition(
                new_run.id,
                to_stage="spec_convergence",
            )
            await self.graph_engine.apply_decision_event(
                new_run.id,
                "lock_intent",
                {"intent_id": str(intent_id)},
            )

            if request.remediation_entry == "new_attempt_same_plan":
                await self.graph_engine.transition(
                    new_run.id,
                    to_stage="execution",
                    plan_id=source_ctx.plan.id,
                    intent_id=intent_id,
                )
            else:
                source_backend_revision = None
                pinned_backend_id = None
                if effective_policy.backend == "honor_pinning":
                    assignments = source_ctx.plan.backend_assignments or {}
                    if isinstance(assignments, dict) and assignments:
                        pinned_backend_id = next(iter(assignments.values()))
                        source_backend_revision = await self._backend_revision_for(
                            source_ctx.capability_snapshot_id,
                            str(pinned_backend_id),
                        )

                plan = await self.planner.plan(
                    intent_id=intent_id,
                    run_id=new_run.id,
                    rule_snapshot_id=rule_snapshot_id,
                    partial_fidelity_snapshot_id=partial_snapshot_id,
                    capability_snapshot_id=capability_snapshot_id,
                    pinning_policy=effective_policy,
                    source_authored_at=source_ctx.authored_at
                    if effective_policy.identity == "honor_pinning"
                    else None,
                    source_backend_revision=source_backend_revision,
                    pinned_backend_id=str(pinned_backend_id)
                    if pinned_backend_id is not None
                    else None,
                )
                await self._emit_event(
                    "replay_planner_invoked",
                    {
                        "request_id": str(request.request_id),
                        "new_run_id": str(new_run.id),
                        "plan_id": str(plan.id),
                        "feasibility_verdict": plan.feasibility_verdict,
                        "refusal_code": plan.refusal_code,
                    },
                )
                if plan.feasibility_verdict in FEASIBLE_VERDICTS:
                    await self.graph_engine.transition(
                        new_run.id,
                        to_stage="execution",
                        plan_id=plan.id,
                        intent_id=intent_id,
                    )

            lifecycle = await OrchestrationLifecycleStateRepo(self.session).get_by_run_id(
                new_run.id
            )
            assert lifecycle is not None
            return lifecycle

        except ReplayRefusalError as exc:
            await self._emit_event(
                "replay_refusal_pre_validation",
                {
                    "request_id": str(request.request_id),
                    "refusal_code": exc.refusal_code,
                    "explanation": exc.explanation,
                    "source_run_id": str(request.source_run_id),
                },
            )
            raise

    async def _load_source_run_context(
        self,
        source_run_id: uuid.UUID,
        *,
        kind: Literal["replay", "remediation"] = "replay",
    ) -> SourceRunContext:
        lifecycle = await OrchestrationLifecycleStateRepo(self.session).get_by_run_id(
            source_run_id
        )
        if lifecycle is None:
            raise ReplayRefusalError(
                "source_run_incomplete",
                f"Source run {source_run_id} has no lifecycle state",
            )
        if not _source_run_is_eligible(lifecycle, kind=kind):
            raise ReplayRefusalError(
                "source_run_incomplete",
                "Source run must be at publish/completed before replay",
            )
        if lifecycle.plan_id is None or lifecycle.intent_id is None:
            raise ReplayRefusalError(
                "source_run_incomplete",
                "Source run is missing plan_id or intent_id",
            )

        plan = await ExecutionPlanRepo(self.session).get_by_id(lifecycle.plan_id)
        intent = await LockedIntentRepo(self.session).get_by_id(lifecycle.intent_id)
        pipeline_run = await PipelineRunRepo(self.session).get_by_id(source_run_id)
        if plan is None or intent is None or pipeline_run is None:
            raise ReplayRefusalError(
                "source_run_incomplete",
                "Source run plan, intent, or pipeline entity is missing",
            )

        trace_id = pipeline_run.attributes.get("spec_convergence_trace_id")
        trace = None
        if trace_id is not None:
            trace = await SpecConvergenceTraceRepo(self.session).get_by_id(
                uuid.UUID(str(trace_id))
            )

        authored_raw = pipeline_run.attributes.get("authored_at")
        authored_at = (
            datetime.fromisoformat(authored_raw)
            if isinstance(authored_raw, str)
            else datetime.now(timezone.utc)
        )

        return SourceRunContext(
            lifecycle=lifecycle,
            plan=plan,
            intent=intent,
            spec_convergence_trace=trace,
            rule_snapshot_id=uuid.UUID(str(plan.rule_snapshot_id)),
            capability_snapshot_id=uuid.UUID(str(plan.capability_snapshot_id)),
            partial_fidelity_snapshot_id=uuid.UUID(
                str(plan.partial_fidelity_snapshot_id)
            ),
            pipeline_run=pipeline_run,
            authored_at=authored_at,
        )

    async def _resolve_pinned_dimension(
        self,
        dimension: str,
        policy: DimensionPolicy,
        source_ctx: SourceRunContext,
        current_snapshot_id: uuid.UUID | None,
    ) -> uuid.UUID | None:
        if policy in {"honor_snapshot", "honor_pinning"}:
            snapshot_id = {
                "rules": source_ctx.rule_snapshot_id,
                "partial_fidelity": source_ctx.partial_fidelity_snapshot_id,
                "capability": source_ctx.capability_snapshot_id,
            }[dimension]
            repo_map = {
                "rules": RuleSnapshotRepo,
                "partial_fidelity": PartialFidelitySnapshotRepo,
                "capability": CapabilitySnapshotRepo,
            }
            row = await repo_map[dimension](self.session).get_by_id(snapshot_id)
            if row is None:
                raise ReplayRefusalError(
                    f"{dimension}_snapshot_unresolvable"
                    if dimension != "rules"
                    else "rule_snapshot_unresolvable",
                    f"Honor-pinned {dimension} snapshot {snapshot_id} not found",
                )
            return snapshot_id

        if dimension == "capability" and current_snapshot_id is None:
            return None
        if current_snapshot_id is None:
            code = {
                "rules": "rule_snapshot_unresolvable",
                "partial_fidelity": "partial_fidelity_snapshot_unresolvable",
                "capability": "capability_snapshot_unresolvable",
            }[dimension]
            raise ReplayRefusalError(
                code,
                f"refresh_current requires current {dimension} snapshot id",
            )
        repo_map = {
            "rules": RuleSnapshotRepo,
            "partial_fidelity": PartialFidelitySnapshotRepo,
            "capability": CapabilitySnapshotRepo,
        }
        row = await repo_map[dimension](self.session).get_by_id(current_snapshot_id)
        if row is None:
            code = {
                "rules": "rule_snapshot_unresolvable",
                "partial_fidelity": "partial_fidelity_snapshot_unresolvable",
                "capability": "capability_snapshot_unresolvable",
            }[dimension]
            raise ReplayRefusalError(
                code,
                f"Current {dimension} snapshot {current_snapshot_id} not found",
            )
        return current_snapshot_id

    async def _resolve_intent_and_lineage(
        self,
        request: ReconstructionRequest,
        source_ctx: SourceRunContext,
        *,
        amended_intent_id: uuid.UUID | None,
    ) -> tuple[uuid.UUID, str]:
        if request.kind == "replay":
            return source_ctx.intent.id, "replays_run"

        assert request.remediation_entry is not None
        if request.remediation_entry == "replan_amended_intent":
            assert amended_intent_id is not None
            amended = await LockedIntentRepo(self.session).get_by_id(amended_intent_id)
            if amended is None:
                raise ReplayRefusalError(
                    "locked_intent_unresolvable",
                    f"Amended intent {amended_intent_id} not found",
                )
            derived = amended.attributes.get("derived_from")
            if str(derived) != str(source_ctx.intent.id):
                raise AmendedIntentLineageError(
                    "amended intent derived_from does not match source intent"
                )
            return amended_intent_id, "amends_run"

        return source_ctx.intent.id, "remediates_run"

    async def _create_pipeline_run(
        self,
        request: ReconstructionRequest,
        source_ctx: SourceRunContext,
        effective_policy: EffectivePinningPolicy,
    ):
        run_kind = "remediation" if request.kind == "remediation" else "replay"
        body: dict[str, Any] = {
            "run_kind": run_kind,
            "intent_id": str(source_ctx.intent.id),
            "source_run_id": str(request.source_run_id),
            "effective_pinning_policy": effective_policy.as_dict(),
            "comparison_target": request.comparison_target,
            "authored_at": (request.authored_at or datetime.now(timezone.utc)).isoformat(),
            "authored_by": request.authored_by,
            "spec_convergence_trace_id": str(
                source_ctx.spec_convergence_trace.id
            )
            if source_ctx.spec_convergence_trace is not None
            else None,
        }
        if request.remediation_entry is not None:
            body["remediation_entry"] = request.remediation_entry
        return await PipelineRunRepo(self.session).insert_if_absent(body)

    async def _create_lineage_edge(
        self,
        new_run_id: uuid.UUID,
        source_run_id: uuid.UUID,
        lineage_rel: str,
    ) -> None:
        rel_key = RUN_LINEAGE_REL_KEYS[lineage_rel]
        await RelationshipRepo(self.session).save(
            Relationship(
                source_id=new_run_id,
                target_id=source_run_id,
                rel_key=rel_key,
                metadata={},
            )
        )

    async def _backend_revision_for(
        self,
        capability_snapshot_id: uuid.UUID,
        backend_id: str,
    ) -> str | None:
        snapshot = await CapabilitySnapshotRepo(self.session).get_by_id(
            capability_snapshot_id
        )
        if snapshot is None:
            return None
        for entry in snapshot.attributes.get("snapshots", []):
            if not isinstance(entry, dict):
                continue
            triple = entry.get("backend_identity_triple") or {}
            surface = triple.get("surface", "unknown")
            path = triple.get("path", "default")
            if f"{surface}.{path}" == backend_id:
                return triple.get("revision")
        return None

    async def _emit_event(self, event_type: str, payload: dict[str, Any]) -> None:
        await self._events.append(event_type, payload)
