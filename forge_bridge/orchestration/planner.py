"""Six-pass planner — semantic kernel (Phase 4B §5)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from forge_bridge.orchestration.identity_registries import (
    PlatformUUIDRegistryProtocol,
    TrainedIdentityRegistryProtocol,
)
from forge_bridge.orchestration.lineage_graph import LineageGraphProtocol
from forge_bridge.orchestration.errors import PlannerRefusalError
from forge_bridge.orchestration.planner_passes import (
    pass_1_validate_completeness,
    pass_2_filter_candidates,
    pass_3_insert_transforms,
    pass_4_validate_plan_shape_rules,
    pass_5_rank_and_predict,
    pass_6_emit_feasibility_verdict,
)
from forge_bridge.orchestration.registration import ToolRegistry
from forge_bridge.orchestration.rule_checks import (
    PlanningRuleRegistry,
    default_planning_rule_registry,
)
from forge_bridge.store.orch_entity_views import (
    DBOrchExecutionPlan,
    DBOrchLockedIntent,
)
from forge_bridge.store.orch_execution_plan_repo import ExecutionPlanRepo
from forge_bridge.store.orch_partial_fidelity_snapshot_repo import (
    PartialFidelitySnapshotRepo,
)
from forge_bridge.store.orch_pipeline_run_repo import PipelineRunRepo
from forge_bridge.store.orch_rule_snapshot_repo import RuleSnapshotRepo
from forge_bridge.store.orch_spec_convergence_trace_repo import SpecConvergenceTraceRepo
from forge_bridge.store.orchestration_compromise_ledger_repo import (
    OrchestrationCompromiseLedgerRepo,
)

if TYPE_CHECKING:
    from forge_bridge.orchestration.replay import EffectivePinningPolicy

PlannerRefusalCode = Literal[
    "inputs_missing",
    "snapshot_unresolvable",
    "locked_intent_unresolvable",
    "no_feasible_backend",
    "external_upload_unavailable",
    "trained_identity_validity_expired",
    "identity_reuse_forbidden",
    "transform_unavailable",
    "anchor_lineage_violation",
    "chain_depth_exceeded",
    "aspect_integrity_violation",
    "compromise_budget_exceeded",
    "cumulative_threshold_exceeded",
    "backend_revision_unreachable",
    "rule_snapshot_unresolvable",
    "capability_snapshot_unresolvable",
    "partial_fidelity_snapshot_unresolvable",
    "spec_convergence_trace_missing",
    "source_run_incomplete",
]

REPLAY_REFUSAL_CODES: frozenset[str] = frozenset(
    {
        "backend_revision_unreachable",
        "rule_snapshot_unresolvable",
        "partial_fidelity_snapshot_unresolvable",
        "spec_convergence_trace_missing",
        "source_run_incomplete",
    }
)


@dataclass
class PlanningContext:
    intent_id: uuid.UUID
    run_id: uuid.UUID
    rule_snapshot_id: uuid.UUID
    partial_fidelity_snapshot_id: uuid.UUID
    inputs_catalog_id: uuid.UUID | None = None
    capability_snapshot_id: uuid.UUID | None = None
    shot_id: uuid.UUID | None = None

    intent: DBOrchLockedIntent | None = None
    rule_snapshot: dict[str, Any] | None = None
    partial_fidelity_snapshot: dict[str, Any] | None = None
    inputs_catalog: dict[str, Any] | None = None
    capability_snapshot: dict[str, Any] | None = None

    candidates: list[dict[str, Any]] = field(default_factory=list)
    transforms_inserted: list[dict[str, Any]] = field(default_factory=list)
    operator_sequence: list[dict[str, Any]] = field(default_factory=list)
    backend_assignments: dict[str, Any] = field(default_factory=dict)
    external_uploads_required: list[Any] = field(default_factory=list)
    cost_estimate: dict[str, Any] = field(default_factory=dict)
    predicted_compromise_consumption: list[Any] = field(default_factory=list)
    provenance_obligations: list[Any] = field(default_factory=list)
    selected_candidate: dict[str, Any] | None = None
    content_policy_transform_required: bool = False

    feasibility_verdict: str = "infeasible"
    feasibility_explanation: str = ""
    refusal_code: str | None = None

    pinning_policy: Any | None = None
    source_authored_at: datetime | None = None
    source_backend_revision: str | None = None
    pinned_backend_id: str | None = None

    def plan_under_construction(self) -> dict[str, Any]:
        chain_depth = 0
        if self.candidates:
            chain_depth = max(int(c.get("chain_depth", 0)) for c in self.candidates)
        if self.selected_candidate is not None:
            chain_depth = int(self.selected_candidate.get("chain_depth", chain_depth))
        return {
            "operator_sequence": self.operator_sequence,
            "transforms_inserted": self.transforms_inserted,
            "content_policy_transform_required": self.content_policy_transform_required,
            "chain_depth": chain_depth,
        }


class Planner:
    """Six-pass planner. Caller owns transaction; never commits."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        tool_registry: ToolRegistry,
        platform_uuid_registry: PlatformUUIDRegistryProtocol,
        trained_identity_registry: TrainedIdentityRegistryProtocol,
        lineage_graph: LineageGraphProtocol,
        planning_rules: PlanningRuleRegistry | None = None,
        planner_version: str = "phase4b-v0.1",
    ) -> None:
        self.session = session
        self.tool_registry = tool_registry
        self.platform_uuid_registry = platform_uuid_registry
        self.trained_identity_registry = trained_identity_registry
        self.lineage_graph = lineage_graph
        self.planning_rules = planning_rules or default_planning_rule_registry()
        self.planner_version = planner_version
        self.compromise_ledger_repo = OrchestrationCompromiseLedgerRepo(session)

    async def plan(
        self,
        *,
        intent_id: uuid.UUID,
        run_id: uuid.UUID,
        rule_snapshot_id: uuid.UUID,
        partial_fidelity_snapshot_id: uuid.UUID,
        inputs_catalog_id: uuid.UUID | None = None,
        capability_snapshot_id: uuid.UUID | None = None,
        pinning_policy: Any | None = None,
        source_authored_at: datetime | None = None,
        source_backend_revision: str | None = None,
        pinned_backend_id: str | None = None,
    ) -> DBOrchExecutionPlan:
        ctx = PlanningContext(
            intent_id=intent_id,
            run_id=run_id,
            rule_snapshot_id=rule_snapshot_id,
            partial_fidelity_snapshot_id=partial_fidelity_snapshot_id,
            inputs_catalog_id=inputs_catalog_id,
            capability_snapshot_id=capability_snapshot_id,
            pinning_policy=pinning_policy,
            source_authored_at=source_authored_at,
            source_backend_revision=source_backend_revision,
            pinned_backend_id=pinned_backend_id,
        )
        try:
            await self._pass_1_validate_completeness(ctx)
            await self._pass_2_filter_candidates(ctx)
            await self._pass_3_insert_transforms(ctx)
            await self._pass_4_validate_plan_shape_rules(ctx)
            await self._pass_5_rank_and_predict(ctx)
            await self._pass_6_emit_feasibility_verdict(ctx)
            body = self._build_plan_body(ctx, refusal_code=None)
        except PlannerRefusalError as exc:
            ctx.refusal_code = exc.refusal_code
            ctx.feasibility_explanation = exc.explanation
            body = self._build_plan_body(ctx, refusal_code=exc.refusal_code)

        return await ExecutionPlanRepo(self.session).insert_if_absent(body)

    async def validate_replay_prerequisites(
        self,
        *,
        intent_id: uuid.UUID,
        run_id: uuid.UUID,
        rule_snapshot_id: uuid.UUID,
        partial_fidelity_snapshot_id: uuid.UUID,
        capability_snapshot_id: uuid.UUID,
        spec_convergence_trace_id: uuid.UUID | None = None,
        source_run_id: uuid.UUID | None = None,
        required_backend_revision: str | None = None,
    ) -> None:
        """Replay-mode guard checks (Step 10 composes this)."""
        if spec_convergence_trace_id is not None:
            trace = await SpecConvergenceTraceRepo(self.session).get_by_id(
                spec_convergence_trace_id
            )
            if trace is None:
                raise PlannerRefusalError(
                    "spec_convergence_trace_missing",
                    f"Spec convergence trace {spec_convergence_trace_id} not found",
                )

        if source_run_id is not None:
            source = await PipelineRunRepo(self.session).get_by_id(source_run_id)
            if source is None or source.attributes.get("status") == "incomplete":
                raise PlannerRefusalError(
                    "source_run_incomplete",
                    f"Source run {source_run_id} incomplete or missing",
                )

        rule = await RuleSnapshotRepo(self.session).get_by_id(rule_snapshot_id)
        if rule is None:
            raise PlannerRefusalError(
                "rule_snapshot_unresolvable",
                f"Rule snapshot {rule_snapshot_id} not found for replay",
            )

        partial = await PartialFidelitySnapshotRepo(self.session).get_by_id(
            partial_fidelity_snapshot_id
        )
        if partial is None:
            raise PlannerRefusalError(
                "partial_fidelity_snapshot_unresolvable",
                f"Partial fidelity snapshot {partial_fidelity_snapshot_id} not found",
            )

        from forge_bridge.store.orch_capability_snapshot_repo import (
            CapabilitySnapshotRepo,
        )

        capability = await CapabilitySnapshotRepo(self.session).get_by_id(
            capability_snapshot_id
        )
        if capability is None:
            raise PlannerRefusalError(
                "capability_snapshot_unresolvable",
                f"Capability snapshot {capability_snapshot_id} not found",
            )

        if required_backend_revision is not None:
            revisions = {
                ((entry or {}).get("backend_identity_triple") or {}).get("revision")
                for entry in capability.attributes.get("snapshots", [])
            }
            if required_backend_revision not in revisions:
                raise PlannerRefusalError(
                    "backend_revision_unreachable",
                    f"Backend revision {required_backend_revision} unreachable",
                )

        _ = intent_id
        _ = run_id

    async def persist_infeasible_plan(
        self,
        ctx: PlanningContext,
        refusal_code: str,
        explanation: str,
    ) -> DBOrchExecutionPlan:
        ctx.refusal_code = refusal_code
        ctx.feasibility_explanation = explanation
        body = self._build_plan_body(ctx, refusal_code=refusal_code)
        return await ExecutionPlanRepo(self.session).insert_if_absent(body)

    async def _pass_1_validate_completeness(self, ctx: PlanningContext) -> None:
        await pass_1_validate_completeness(self, ctx)

    async def _pass_2_filter_candidates(self, ctx: PlanningContext) -> None:
        await pass_2_filter_candidates(self, ctx)

    async def _pass_3_insert_transforms(self, ctx: PlanningContext) -> None:
        await pass_3_insert_transforms(self, ctx)

    async def _pass_4_validate_plan_shape_rules(self, ctx: PlanningContext) -> None:
        await pass_4_validate_plan_shape_rules(self, ctx)

    async def _pass_5_rank_and_predict(self, ctx: PlanningContext) -> None:
        await pass_5_rank_and_predict(self, ctx)

    async def _pass_6_emit_feasibility_verdict(self, ctx: PlanningContext) -> None:
        await pass_6_emit_feasibility_verdict(self, ctx)

    def _build_plan_body(
        self,
        ctx: PlanningContext,
        *,
        refusal_code: str | None,
    ) -> dict[str, Any]:
        infeasible = refusal_code is not None
        return {
            "operator_sequence": [] if infeasible else ctx.operator_sequence,
            "backend_assignments": {} if infeasible else ctx.backend_assignments,
            "transforms_inserted": [] if infeasible else ctx.transforms_inserted,
            "external_uploads_required": [] if infeasible else ctx.external_uploads_required,
            "cost_estimate": {} if infeasible else ctx.cost_estimate,
            "predicted_compromise_consumption": []
            if infeasible
            else ctx.predicted_compromise_consumption,
            "provenance_obligations": [] if infeasible else ctx.provenance_obligations,
            "feasibility_verdict": "infeasible" if infeasible else ctx.feasibility_verdict,
            "feasibility_explanation": ctx.feasibility_explanation
            if infeasible
            else ctx.feasibility_explanation,
            "refusal_code": refusal_code,
            "intent_id": str(ctx.intent_id),
            "planner_version": self.planner_version,
            "capability_snapshot_id": str(ctx.capability_snapshot_id)
            if ctx.capability_snapshot_id
            else None,
            "rule_snapshot_id": str(ctx.rule_snapshot_id),
            "partial_fidelity_snapshot_id": str(ctx.partial_fidelity_snapshot_id),
        }
