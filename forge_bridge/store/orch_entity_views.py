"""Phase 4B orch_* entity view wrappers over DBEntity rows."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, ClassVar, Optional


class _OrchEntityViewBase:
    """Shared read-only view over a content-addressed DBEntity row."""

    ENTITY_TYPE: ClassVar[str]

    def __init__(self, entity) -> None:
        from forge_bridge.store.models import DBEntity

        if not isinstance(entity, DBEntity):
            raise TypeError(f"Expected DBEntity, got {type(entity)!r}")
        if entity.entity_type != self.ENTITY_TYPE:
            raise ValueError(
                f"{self.__class__.__name__} requires entity_type="
                f"{self.ENTITY_TYPE!r}; got {entity.entity_type!r}"
            )
        self._entity = entity

    @classmethod
    def from_entity(cls, entity) -> _OrchEntityViewBase:
        return cls(entity)

    @property
    def id(self) -> uuid.UUID:
        return self._entity.id

    @property
    def project_id(self) -> uuid.UUID | None:
        return self._entity.project_id

    @property
    def name(self) -> str | None:
        return self._entity.name

    @property
    def status(self) -> str | None:
        return self._entity.status

    @property
    def content_hash(self) -> str | None:
        return self._entity.content_hash

    @property
    def attributes(self) -> dict[str, Any]:
        return self._entity.attributes

    @property
    def created_at(self) -> datetime:
        return self._entity.created_at

    @property
    def entity(self):
        return self._entity

    def _attr(self, key: str, default: Any = None) -> Any:
        return self._entity.attributes.get(key, default)


class DBOrchLockedIntent(_OrchEntityViewBase):
    ENTITY_TYPE = "orch_locked_intent"

    @property
    def source_read(self) -> Any:
        return self._attr("source_read")

    @property
    def change_manifest(self) -> Any:
        return self._attr("change_manifest")

    @property
    def success_criteria(self) -> Any:
        return self._attr("success_criteria")

    @property
    def allowed_compromises(self) -> Any:
        return self._attr("allowed_compromises")

    @property
    def hard_constraints(self) -> Any:
        return self._attr("hard_constraints")

    @property
    def escalation_threshold(self) -> Any:
        return self._attr("escalation_threshold")

    @property
    def deliverable_spec(self) -> Any:
        return self._attr("deliverable_spec")


class DBOrchPipelineRun(_OrchEntityViewBase):
    ENTITY_TYPE = "orch_pipeline_run"

    @property
    def run_kind(self) -> Any:
        return self._attr("run_kind")

    @property
    def intent_id(self) -> Any:
        return self._attr("intent_id")

    @property
    def source_run_id(self) -> Any:
        return self._attr("source_run_id")

    @property
    def effective_pinning_policy(self) -> Any:
        return self._attr("effective_pinning_policy")


class DBOrchInputsCatalog(_OrchEntityViewBase):
    ENTITY_TYPE = "orch_inputs_catalog"

    @property
    def inputs(self) -> Any:
        return self._attr("inputs")

    @property
    def role_assignments(self) -> Any:
        return self._attr("role_assignments")


class DBOrchSpecConvergenceTrace(_OrchEntityViewBase):
    ENTITY_TYPE = "orch_spec_convergence_trace"

    @property
    def iterations(self) -> Any:
        return self._attr("iterations")

    @property
    def lock_event(self) -> Any:
        return self._attr("lock_event")

    @property
    def locked(self) -> bool:
        return self.lock_event is not None


class DBOrchRuleSnapshot(_OrchEntityViewBase):
    ENTITY_TYPE = "orch_rule_snapshot"

    @property
    def rules(self) -> Any:
        return self._attr("rules")

    @property
    def source_ref(self) -> Any:
        return self._attr("source_ref")

    @property
    def snapshot_timestamp(self) -> Any:
        return self._attr("snapshot_timestamp")


class DBOrchCapabilitySnapshot(_OrchEntityViewBase):
    ENTITY_TYPE = "orch_capability_snapshot"

    @property
    def snapshots(self) -> Any:
        return self._attr("snapshots")


class DBOrchPartialFidelitySnapshot(_OrchEntityViewBase):
    ENTITY_TYPE = "orch_partial_fidelity_snapshot"

    @property
    def models(self) -> Any:
        return self._attr("models")


class DBOrchExecutionPlan(_OrchEntityViewBase):
    ENTITY_TYPE = "orch_execution_plan"

    @property
    def operator_sequence(self) -> Any:
        return self._attr("operator_sequence")

    @property
    def backend_assignments(self) -> Any:
        return self._attr("backend_assignments")

    @property
    def transforms_inserted(self) -> Any:
        return self._attr("transforms_inserted")

    @property
    def external_uploads_required(self) -> Any:
        return self._attr("external_uploads_required")

    @property
    def cost_estimate(self) -> Any:
        return self._attr("cost_estimate")

    @property
    def predicted_compromise_consumption(self) -> Any:
        return self._attr("predicted_compromise_consumption")

    @property
    def provenance_obligations(self) -> Any:
        return self._attr("provenance_obligations")

    @property
    def feasibility_verdict(self) -> Any:
        return self._attr("feasibility_verdict")

    @property
    def feasibility_explanation(self) -> Any:
        return self._attr("feasibility_explanation")

    @property
    def refusal_code(self) -> Any:
        return self._attr("refusal_code")

    @property
    def intent_id(self) -> Any:
        return self._attr("intent_id")

    @property
    def planner_version(self) -> Any:
        return self._attr("planner_version")

    @property
    def capability_snapshot_id(self) -> Any:
        return self._attr("capability_snapshot_id")

    @property
    def rule_snapshot_id(self) -> Any:
        return self._attr("rule_snapshot_id")

    @property
    def partial_fidelity_snapshot_id(self) -> Any:
        return self._attr("partial_fidelity_snapshot_id")


class DBOrchValidationReport(_OrchEntityViewBase):
    ENTITY_TYPE = "orch_validation_report"

    @property
    def verdict(self) -> Any:
        return self._attr("verdict")

    @property
    def evidence(self) -> Any:
        return self._attr("evidence")

    @property
    def evidence_refs(self) -> Any:
        return self._attr("evidence_refs")


class DBOrchAuditReport(_OrchEntityViewBase):
    ENTITY_TYPE = "orch_audit_report"

    @property
    def candidate_artifact_id(self) -> Any:
        return self._attr("candidate_artifact_id")

    @property
    def intent_id(self) -> Any:
        return self._attr("intent_id")

    @property
    def rules_snapshot_ref(self) -> Any:
        return self._attr("rules_snapshot_ref")

    @property
    def per_criterion(self) -> Any:
        return self._attr("per_criterion")

    @property
    def cross_criterion_summary(self) -> Any:
        return self._attr("cross_criterion_summary")

    @property
    def overall_verdict(self) -> Any:
        summary = self.cross_criterion_summary
        if isinstance(summary, dict):
            return summary.get("overall_verdict")
        return None


class DBOrchProvenanceManifest(_OrchEntityViewBase):
    ENTITY_TYPE = "orch_provenance_manifest"

    @property
    def shot_id(self) -> Any:
        return self._attr("shot_id")

    @property
    def run_id(self) -> Any:
        return self._attr("run_id")

    @property
    def intent_id(self) -> Any:
        return self._attr("intent_id")

    @property
    def spec_convergence_trace_id(self) -> Any:
        return self._attr("spec_convergence_trace_id")

    @property
    def execution_plan_id(self) -> Any:
        return self._attr("execution_plan_id")

    @property
    def audit_report_id(self) -> Any:
        return self._attr("audit_report_id")

    @property
    def promotion_ledger_entry_id(self) -> Any:
        return self._attr("promotion_ledger_entry_id")

    @property
    def canonical_artifact_id(self) -> Any:
        return self._attr("canonical_artifact_id")

    @property
    def canonical_content_hash(self) -> Any:
        return self._attr("canonical_content_hash")

    @property
    def full_lineage(self) -> Any:
        return self._attr("full_lineage")

    @property
    def snapshots_bundled_by_content(self) -> Any:
        return self._attr("snapshots_bundled_by_content")

    @property
    def refusal_and_partial_records(self) -> Any:
        return self._attr("refusal_and_partial_records")

    @property
    def cost_summary(self) -> Any:
        return self._attr("cost_summary")


class DBOrchGenerationArtifact(_OrchEntityViewBase):
    """Hybrid lifecycle artifact — lifecycle_state lives in status column."""

    ENTITY_TYPE = "orch_generation_artifact"

    @property
    def lifecycle_state(self) -> str | None:
        return self._entity.status

    @property
    def platform_locators(self) -> Any:
        return self._attr("platform_locators")

    @property
    def content_provenance(self) -> Any:
        return self._attr("content_provenance")

    @property
    def execution_provenance(self) -> Any:
        return self._attr("execution_provenance")

    @property
    def partial_fidelity_report(self) -> Any:
        return self._attr("partial_fidelity_report")

    @property
    def polling_history(self) -> list[Any]:
        history = self._attr("polling_history", [])
        return history if isinstance(history, list) else []

    @property
    def run_id(self) -> Any:
        return self._attr("run_id")


class DBOrchExecutionResult(_OrchEntityViewBase):
    """Lightweight terminal record for synchronous execution-family steps."""

    ENTITY_TYPE = "orch_execution_result"

    @property
    def run_id(self) -> Any:
        return self._attr("run_id")

    @property
    def step_id(self) -> Any:
        return self._attr("step_id")

    @property
    def family(self) -> Any:
        return self._attr("family")

    @property
    def disposition(self) -> Any:
        return self._attr("disposition")

    @property
    def result_payload(self) -> Any:
        return self._attr("result_payload")

    @property
    def result_ref(self) -> Any:
        return self._attr("result_ref")
