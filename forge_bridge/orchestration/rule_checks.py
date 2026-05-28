"""Planning-time rule check strategies (Phase 4B §5). v0.1 stub implementations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Protocol

from forge_bridge.orchestration.lineage_graph import LineageGraphProtocol
from forge_bridge.store.orch_entity_views import DBOrchLockedIntent


@dataclass(frozen=True)
class PlanningRuleViolation:
    rule_id: str
    refusal_code: str
    explanation: str
    rule_authoritative_phase: str


class PlanningRuleCheck(Protocol):
    rule_id: str

    async def check(
        self,
        *,
        plan_under_construction: dict,
        intent: DBOrchLockedIntent,
        capability_snapshot: dict,
        lineage_graph: LineageGraphProtocol,
    ) -> PlanningRuleViolation | None: ...


class Rule4AnchorLineageCheck:
    rule_id = "rule-4"

    async def check(
        self,
        *,
        plan_under_construction: dict,
        intent: DBOrchLockedIntent,
        capability_snapshot: dict,
        lineage_graph: LineageGraphProtocol,
    ) -> PlanningRuleViolation | None:
        sequence = plan_under_construction.get("operator_sequence", [])
        if await lineage_graph.would_violate_anchor_lineage(sequence):
            return PlanningRuleViolation(
                rule_id=self.rule_id,
                refusal_code="anchor_lineage_violation",
                explanation="Operator sequence anchors to prior-step output instead of source truth",
                rule_authoritative_phase="planning-time",
            )
        return None


class Rule5ChainDepthCheck:
    rule_id = "rule-5"
    DEFAULT_HARD_CAP: ClassVar[int] = 5

    async def check(
        self,
        *,
        plan_under_construction: dict,
        intent: DBOrchLockedIntent,
        capability_snapshot: dict,
        lineage_graph: LineageGraphProtocol,
    ) -> PlanningRuleViolation | None:
        cap = self.DEFAULT_HARD_CAP
        for rule in (intent.hard_constraints or []):
            if isinstance(rule, dict) and rule.get("chain_depth_cap") is not None:
                cap = int(rule["chain_depth_cap"])

        depth = plan_under_construction.get("chain_depth", 0)
        if depth > cap:
            return PlanningRuleViolation(
                rule_id=self.rule_id,
                refusal_code="chain_depth_exceeded",
                explanation=f"Chain depth {depth} exceeds cap {cap}",
                rule_authoritative_phase="planning-time",
            )
        return None


class Rule10AspectIntegrityCheck:
    rule_id = "rule-10"

    async def check(
        self,
        *,
        plan_under_construction: dict,
        intent: DBOrchLockedIntent,
        capability_snapshot: dict,
        lineage_graph: LineageGraphProtocol,
    ) -> PlanningRuleViolation | None:
        deliverable = intent.deliverable_spec or {}
        if deliverable.get("medium") == "video" and deliverable.get("pillarbox_bake"):
            return PlanningRuleViolation(
                rule_id=self.rule_id,
                refusal_code="aspect_integrity_violation",
                explanation="Video deliverable must not bake pillarbox into pixels",
                rule_authoritative_phase="planning-time",
            )
        return None


class Rule14ContentPolicyCheck:
    rule_id = "rule-14"

    async def check(
        self,
        *,
        plan_under_construction: dict,
        intent: DBOrchLockedIntent,
        capability_snapshot: dict,
        lineage_graph: LineageGraphProtocol,
    ) -> PlanningRuleViolation | None:
        if plan_under_construction.get("content_policy_transform_required") and not (
            plan_under_construction.get("transforms_inserted")
        ):
            return PlanningRuleViolation(
                rule_id=self.rule_id,
                refusal_code="transform_unavailable",
                explanation="Required content-policy bypass transform was not inserted",
                rule_authoritative_phase="planning-time",
            )
        return None


class PlanningRuleRegistry:
    def __init__(self) -> None:
        self._checks: dict[str, PlanningRuleCheck] = {}

    def register(self, check: PlanningRuleCheck) -> None:
        self._checks[check.rule_id] = check

    def get(self, rule_id: str) -> PlanningRuleCheck | None:
        return self._checks.get(rule_id)

    def all(self) -> list[PlanningRuleCheck]:
        return list(self._checks.values())


DEFAULT_PLANNING_RULES: tuple[PlanningRuleCheck, ...] = (
    Rule4AnchorLineageCheck(),
    Rule5ChainDepthCheck(),
    Rule10AspectIntegrityCheck(),
    Rule14ContentPolicyCheck(),
)


def default_planning_rule_registry() -> PlanningRuleRegistry:
    registry = PlanningRuleRegistry()
    for check in DEFAULT_PLANNING_RULES:
        registry.register(check)
    return registry
