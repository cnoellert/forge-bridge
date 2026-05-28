"""ProvenanceManifest assembler (Phase 4B §8)."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, ClassVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from forge_bridge.orchestration.errors import (
    InvalidManifestRequestError,
    ManifestPreconditionError,
)
from forge_bridge.store.models import (
    DBEntity,
    DBOrchestrationPromotionLedger,
    DBRelationship,
    DBRelationshipType,
)
from forge_bridge.store.orch_audit_report_repo import AuditReportRepo
from forge_bridge.store.orch_capability_snapshot_repo import CapabilitySnapshotRepo
from forge_bridge.store.orch_entity_views import DBOrchProvenanceManifest
from forge_bridge.store.orch_execution_plan_repo import ExecutionPlanRepo
from forge_bridge.store.orch_generation_artifact_repo import GenerationArtifactRepo
from forge_bridge.store.orch_locked_intent_repo import LockedIntentRepo
from forge_bridge.store.orch_partial_fidelity_snapshot_repo import (
    PartialFidelitySnapshotRepo,
)
from forge_bridge.store.orch_pipeline_run_repo import PipelineRunRepo
from forge_bridge.store.orch_provenance_manifest_repo import ProvenanceManifestRepo
from forge_bridge.store.orch_rule_snapshot_repo import RuleSnapshotRepo
from forge_bridge.store.orchestration_lifecycle_state_repo import (
    OrchestrationLifecycleStateRepo,
)
from forge_bridge.store.orchestration_promotion_ledger_repo import (
    OrchestrationPromotionLedgerRepo,
)
from forge_bridge.store.repo import EventRepo

_BACKWARD_REL_KEYS: dict[str, uuid.UUID] = {
    "content_source": uuid.UUID("00000000-0000-0000-0040-000000000001"),
    "anchored_to": uuid.UUID("00000000-0000-0000-0040-000000000002"),
}

_UUID_IN_TEXT = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SnapshotIdSet:
    rule_snapshot_ids: frozenset[uuid.UUID] = frozenset()
    capability_snapshot_ids: frozenset[uuid.UUID] = frozenset()
    partial_fidelity_snapshot_ids: frozenset[uuid.UUID] = frozenset()

    def merge(self, other: SnapshotIdSet) -> SnapshotIdSet:
        return SnapshotIdSet(
            rule_snapshot_ids=self.rule_snapshot_ids | other.rule_snapshot_ids,
            capability_snapshot_ids=self.capability_snapshot_ids
            | other.capability_snapshot_ids,
            partial_fidelity_snapshot_ids=self.partial_fidelity_snapshot_ids
            | other.partial_fidelity_snapshot_ids,
        )


@dataclass(frozen=True)
class SubgraphClosure:
    artifacts: list[DBEntity]
    edges: list[DBRelationship]
    snapshot_ids: SnapshotIdSet


@dataclass(frozen=True)
class ManifestBody:
    shot_id: uuid.UUID
    run_id: uuid.UUID
    intent_id: uuid.UUID
    spec_convergence_trace_id: uuid.UUID | None
    execution_plan_id: uuid.UUID
    audit_report_id: uuid.UUID
    promotion_ledger_entry_id: uuid.UUID
    canonical_artifact_id: uuid.UUID
    canonical_content_hash: str
    full_lineage: dict[str, Any]
    snapshots_bundled_by_content: dict[str, Any]
    refusal_and_partial_records: list[dict[str, Any]]
    cost_summary: dict[str, Any]
    assembled_at: str
    assembled_by: str
    manifest_id: uuid.UUID | None = None
    content_hash: str | None = None

    def to_jsonb(self) -> dict[str, Any]:
        payload = {
            "shot_id": str(self.shot_id),
            "run_id": str(self.run_id),
            "intent_id": str(self.intent_id),
            "spec_convergence_trace_id": (
                str(self.spec_convergence_trace_id)
                if self.spec_convergence_trace_id is not None
                else None
            ),
            "execution_plan_id": str(self.execution_plan_id),
            "audit_report_id": str(self.audit_report_id),
            "promotion_ledger_entry_id": str(self.promotion_ledger_entry_id),
            "canonical_artifact_id": str(self.canonical_artifact_id),
            "canonical_content_hash": self.canonical_content_hash,
            "full_lineage": self.full_lineage,
            "snapshots_bundled_by_content": self.snapshots_bundled_by_content,
            "refusal_and_partial_records": self.refusal_and_partial_records,
            "cost_summary": self.cost_summary,
            "assembled_at": self.assembled_at,
            "assembled_by": self.assembled_by,
        }
        return _normalize_for_json(payload)


class ManifestSubgraphWalker:
    """Closure-of-canonical walker via content_source + anchored_to edges."""

    BACKWARD_RELATIONSHIP_NAMES: ClassVar[frozenset[str]] = frozenset(
        {"content_source", "anchored_to"}
    )

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._rel_keys: dict[str, uuid.UUID] | None = None
        self._name_by_uuid: dict[uuid.UUID, str] | None = None

    async def _ensure_relationship_cache(self) -> None:
        if self._rel_keys is not None:
            return
        result = await self.session.execute(
            select(DBRelationshipType).where(
                DBRelationshipType.name.in_(tuple(self.BACKWARD_RELATIONSHIP_NAMES))
            )
        )
        rows = list(result.scalars().all())
        self._rel_keys = {
            row.name: row.key for row in rows if row.name in self.BACKWARD_RELATIONSHIP_NAMES
        }
        for name, key in _BACKWARD_REL_KEYS.items():
            self._rel_keys.setdefault(name, key)
        self._name_by_uuid = {key: name for name, key in self._rel_keys.items()}

    @property
    async def name_by_uuid(self) -> dict[uuid.UUID, str]:
        await self._ensure_relationship_cache()
        assert self._name_by_uuid is not None
        return self._name_by_uuid

    async def walk_backward(self, canonical_artifact_id: uuid.UUID) -> SubgraphClosure:
        await self._ensure_relationship_cache()
        assert self._rel_keys is not None

        rel_key_set = frozenset(self._rel_keys.values())
        visited: set[uuid.UUID] = {canonical_artifact_id}
        frontier: list[uuid.UUID] = [canonical_artifact_id]
        edges: list[DBRelationship] = []
        snapshot_ids = SnapshotIdSet()

        while frontier:
            current_id = frontier.pop(0)
            result = await self.session.execute(
                select(DBRelationship).where(
                    DBRelationship.target_id == current_id,
                    DBRelationship.rel_type_key.in_(tuple(rel_key_set)),
                )
            )
            for edge in result.scalars().all():
                edges.append(edge)
                upstream_id = edge.source_id
                if upstream_id in visited:
                    continue
                visited.add(upstream_id)
                frontier.append(upstream_id)

        artifact_rows: list[DBEntity] = []
        for artifact_id in sorted(visited):
            entity = await self.session.get(DBEntity, artifact_id)
            if entity is not None:
                artifact_rows.append(entity)
                snapshot_ids = snapshot_ids.merge(
                    _snapshot_ids_from_entity(entity)
                )

        return SubgraphClosure(
            artifacts=artifact_rows,
            edges=edges,
            snapshot_ids=snapshot_ids,
        )


class ProvenanceManifestAssembler:
    """Publish-time portable extract assembler."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._events = EventRepo(session)
        self._walker = ManifestSubgraphWalker(session)

    async def assemble(
        self,
        *,
        promotion_id: uuid.UUID | None = None,
        canonical_artifact_id: uuid.UUID | None = None,
        shot_id: uuid.UUID | None = None,
        assembled_by: str = "forge_bridge.orchestration.manifest_assembler",
    ) -> DBOrchProvenanceManifest:
        provided = [
            p
            for p in (promotion_id, canonical_artifact_id, shot_id)
            if p is not None
        ]
        if len(provided) != 1:
            raise InvalidManifestRequestError(
                "Exactly one of promotion_id, canonical_artifact_id, or shot_id "
                "must be provided"
            )

        promotion: DBOrchestrationPromotionLedger | None = None
        try:
            promotion = await self._resolve_promotion(
                promotion_id=promotion_id,
                canonical_artifact_id=canonical_artifact_id,
                shot_id=shot_id,
            )
            if promotion is None:
                raise ManifestPreconditionError("canonical_never_promoted")

            canonical_id = promotion.promoted_artifact_id
            canonical = await GenerationArtifactRepo(self.session).get_by_id(
                canonical_id
            )
            if canonical is None:
                raise ManifestPreconditionError("canonical_not_terminal")
            if (
                canonical.lifecycle_state not in GenerationArtifactRepo.TERMINAL_STATES
                or not canonical.content_hash
            ):
                raise ManifestPreconditionError("canonical_not_terminal")

            run_id = _parse_uuid(canonical.attributes.get("run_id"))
            if run_id is None:
                raise ManifestPreconditionError("run_artifacts_unresolvable")

            await self._emit_event(
                "manifest_assembly_started",
                {
                    "promotion_id": str(promotion.promotion_id),
                    "canonical_artifact_id": str(canonical_id),
                    "shot_id": str(promotion.shot_id),
                    "run_id": str(run_id),
                },
            )

            closure = await self._walker.walk_backward(canonical_id)
            run_ctx = await self._resolve_run_context(
                run_id=run_id,
                canonical_artifact_id=canonical_id,
                promotion=promotion,
            )
            snapshot_ids = closure.snapshot_ids.merge(run_ctx.snapshot_ids)

            snapshots_bundled = await self._bundle_snapshots(snapshot_ids)
            name_by_uuid = await self._walker.name_by_uuid
            full_lineage = await self._build_full_lineage(
                closure=closure,
                canonical=canonical.entity,
                run_id=run_id,
                promoted_artifact_id=canonical_id,
                name_by_uuid=name_by_uuid,
            )
            refusal_records = await self._collect_refusal_records(
                closure=closure,
                promotion=promotion,
            )
            cost_summary = _aggregate_costs(
                closure.artifacts,
                run_stage=run_ctx.lifecycle_stage,
            )

            assembled_at = promotion.promoted_at.isoformat()
            body = ManifestBody(
                shot_id=promotion.shot_id,
                run_id=run_id,
                intent_id=run_ctx.intent_id,
                spec_convergence_trace_id=run_ctx.spec_convergence_trace_id,
                execution_plan_id=run_ctx.execution_plan_id,
                audit_report_id=run_ctx.audit_report_id,
                promotion_ledger_entry_id=promotion.promotion_id,
                canonical_artifact_id=canonical_id,
                canonical_content_hash=canonical.content_hash,
                full_lineage=full_lineage,
                snapshots_bundled_by_content=snapshots_bundled,
                refusal_and_partial_records=refusal_records,
                cost_summary=cost_summary,
                assembled_at=assembled_at,
                assembled_by=assembled_by,
            )

            inserted = await ProvenanceManifestRepo(self.session).insert_if_absent(
                body.to_jsonb()
            )
            await self._emit_event(
                "manifest_assembly_completed",
                {
                    "manifest_id": str(inserted.id),
                    "manifest_content_hash": inserted.content_hash,
                    "artifacts_walked": len(closure.artifacts),
                    "snapshots_embedded": sum(
                        1
                        for key in (
                            "rule_snapshot",
                            "capability_snapshot",
                            "partial_fidelity_snapshot",
                        )
                        if snapshots_bundled.get(key) is not None
                    ),
                    "total_cost_by_currency": cost_summary.get(
                        "total_by_currency", {}
                    ),
                },
            )
            return inserted

        except ManifestPreconditionError as exc:
            await self._emit_event(
                "manifest_assembly_refused",
                {
                    "reason": exc.reason,
                    "promotion_id": str(promotion_id) if promotion_id else None,
                    "canonical_artifact_id": (
                        str(canonical_artifact_id) if canonical_artifact_id else None
                    ),
                    "shot_id": str(shot_id) if shot_id else None,
                },
            )
            raise

    async def _resolve_promotion(
        self,
        *,
        promotion_id: uuid.UUID | None,
        canonical_artifact_id: uuid.UUID | None,
        shot_id: uuid.UUID | None,
    ) -> DBOrchestrationPromotionLedger | None:
        ledger = OrchestrationPromotionLedgerRepo(self.session)
        if promotion_id is not None:
            return await self.session.get(
                DBOrchestrationPromotionLedger, promotion_id
            )
        if canonical_artifact_id is not None:
            return await ledger.was_ever_canonical(canonical_artifact_id)
        if shot_id is not None:
            return await ledger.get_current_canonical(shot_id)
        return None

    async def _resolve_run_context(
        self,
        *,
        run_id: uuid.UUID,
        canonical_artifact_id: uuid.UUID,
        promotion: DBOrchestrationPromotionLedger,
    ) -> _RunContext:
        lifecycle = await OrchestrationLifecycleStateRepo(self.session).get_by_run_id(
            run_id
        )
        if lifecycle is None or lifecycle.intent_id is None or lifecycle.plan_id is None:
            raise ManifestPreconditionError("run_artifacts_unresolvable")

        intent = await LockedIntentRepo(self.session).get_by_id(lifecycle.intent_id)
        plan = await ExecutionPlanRepo(self.session).get_by_id(lifecycle.plan_id)
        if intent is None or plan is None:
            raise ManifestPreconditionError("run_artifacts_unresolvable")

        audit = None
        if promotion.audit_report_id is not None:
            audit = await AuditReportRepo(self.session).get_by_id(
                promotion.audit_report_id
            )
        if audit is None:
            audit = await _find_audit_for_candidate(
                self.session, canonical_artifact_id
            )
        if audit is None:
            raise ManifestPreconditionError("run_artifacts_unresolvable")

        trace_id: uuid.UUID | None = None
        pipeline_run = await PipelineRunRepo(self.session).get_by_id(run_id)
        if pipeline_run is not None:
            trace_id = _parse_uuid(
                pipeline_run.attributes.get("spec_convergence_trace_id")
            )

        snapshot_ids = SnapshotIdSet(
            rule_snapshot_ids=_uuid_set(
                plan.rule_snapshot_id,
                audit.attributes.get("rules_snapshot_ref"),
            ),
            capability_snapshot_ids=_uuid_set(plan.capability_snapshot_id),
            partial_fidelity_snapshot_ids=_uuid_set(
                plan.partial_fidelity_snapshot_id
            ),
        )

        return _RunContext(
            intent_id=intent.id,
            execution_plan_id=plan.id,
            audit_report_id=audit.id,
            spec_convergence_trace_id=trace_id,
            snapshot_ids=snapshot_ids,
            lifecycle_stage=lifecycle.current_stage,
        )

    async def _bundle_snapshots(
        self,
        snapshot_ids: SnapshotIdSet,
    ) -> dict[str, Any]:
        bundled: dict[str, Any] = {
            "rule_snapshot": None,
            "capability_snapshot": None,
            "partial_fidelity_snapshot": None,
        }

        if snapshot_ids.rule_snapshot_ids:
            snap_id = min(snapshot_ids.rule_snapshot_ids)
            row = await RuleSnapshotRepo(self.session).get_by_id(snap_id)
            if row is None:
                raise ManifestPreconditionError("snapshot_unresolvable")
            bundled["rule_snapshot"] = _snapshot_bundle_entry(row.entity)

        if snapshot_ids.capability_snapshot_ids:
            snap_id = min(snapshot_ids.capability_snapshot_ids)
            row = await CapabilitySnapshotRepo(self.session).get_by_id(snap_id)
            if row is None:
                raise ManifestPreconditionError("snapshot_unresolvable")
            bundled["capability_snapshot"] = _snapshot_bundle_entry(row.entity)

        if snapshot_ids.partial_fidelity_snapshot_ids:
            snap_id = min(snapshot_ids.partial_fidelity_snapshot_ids)
            row = await PartialFidelitySnapshotRepo(self.session).get_by_id(snap_id)
            if row is None:
                raise ManifestPreconditionError("snapshot_unresolvable")
            bundled["partial_fidelity_snapshot"] = _snapshot_bundle_entry(row.entity)

        return bundled

    async def _build_full_lineage(
        self,
        *,
        closure: SubgraphClosure,
        canonical: DBEntity,
        run_id: uuid.UUID,
        promoted_artifact_id: uuid.UUID,
        name_by_uuid: dict[uuid.UUID, str],
    ) -> dict[str, Any]:
        artifacts = [
            _entity_to_artifact_dict(entity)
            for entity in sorted(closure.artifacts, key=lambda e: str(e.id))
        ]
        edges = [
            _edge_to_dict(edge, name_by_uuid)
            for edge in sorted(
                closure.edges,
                key=lambda e: (str(e.source_id), str(e.target_id), str(e.rel_type_key)),
            )
        ]
        superseded = await _superseded_within_run(
            self.session,
            run_id=run_id,
            promoted_artifact_id=promoted_artifact_id,
        )
        return {
            "artifacts": artifacts,
            "edges": edges,
            "superseded_within_run": [str(aid) for aid in sorted(superseded)],
        }

    async def _collect_refusal_records(
        self,
        *,
        closure: SubgraphClosure,
        promotion: DBOrchestrationPromotionLedger,
    ) -> list[dict[str, Any]]:
        records: dict[str, dict[str, Any]] = {}

        for entity in closure.artifacts:
            if entity.entity_type != "orch_generation_artifact":
                continue
            report = entity.attributes.get("partial_fidelity_report")
            if isinstance(report, dict):
                record_id = str(report.get("record_id", entity.id))
                records[record_id] = {
                    "record_id": record_id,
                    "kind": "partial",
                    **report,
                }

        for match in _UUID_IN_TEXT.findall(promotion.rationale or ""):
            record_id = match.lower()
            if record_id in records:
                continue
            entity = await self.session.get(DBEntity, uuid.UUID(record_id))
            if entity is None:
                continue
            report = entity.attributes.get("partial_fidelity_report")
            if isinstance(report, dict):
                records[record_id] = {
                    "record_id": record_id,
                    "kind": "partial",
                    **report,
                }
            elif entity.entity_type == "orch_generation_artifact":
                records[record_id] = {
                    "record_id": record_id,
                    "kind": "refusal",
                    "verdict": entity.attributes.get("verdict", "failed"),
                    "artifact_id": record_id,
                }

        return [records[key] for key in sorted(records)]

    async def _emit_event(self, event_type: str, payload: dict[str, Any]) -> None:
        await self._events.append(event_type, payload)


@dataclass(frozen=True)
class _RunContext:
    intent_id: uuid.UUID
    execution_plan_id: uuid.UUID
    audit_report_id: uuid.UUID
    spec_convergence_trace_id: uuid.UUID | None
    snapshot_ids: SnapshotIdSet
    lifecycle_stage: str


def _parse_uuid(value: Any) -> uuid.UUID | None:
    if value is None:
        return None
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def _uuid_set(*values: Any) -> frozenset[uuid.UUID]:
    parsed = {_parse_uuid(v) for v in values}
    return frozenset(v for v in parsed if v is not None)


def _snapshot_ids_from_entity(entity: DBEntity) -> SnapshotIdSet:
    attrs = entity.attributes if isinstance(entity.attributes, dict) else {}
    provenance = attrs.get("execution_provenance")
    provenance = provenance if isinstance(provenance, dict) else {}
    return SnapshotIdSet(
        rule_snapshot_ids=_uuid_set(
            provenance.get("rule_snapshot_id"),
            provenance.get("rules_snapshot_ref"),
            attrs.get("rule_snapshot_id"),
        ),
        capability_snapshot_ids=_uuid_set(
            provenance.get("capability_snapshot_id"),
            attrs.get("capability_snapshot_id"),
        ),
        partial_fidelity_snapshot_ids=_uuid_set(
            provenance.get("partial_fidelity_snapshot_id"),
            attrs.get("partial_fidelity_snapshot_id"),
        ),
    )


def _entity_to_artifact_dict(entity: DBEntity) -> dict[str, Any]:
    attrs = entity.attributes if isinstance(entity.attributes, dict) else {}
    payload: dict[str, Any] = {
        "artifact_id": str(entity.id),
        "content_hash": entity.content_hash,
        "entity_type": entity.entity_type,
        "content_provenance": attrs.get("content_provenance", {}),
    }
    if entity.entity_type == "orch_generation_artifact":
        execution = attrs.get("execution_provenance")
        if execution is not None:
            payload["execution_provenance"] = execution
    return payload


def _edge_to_dict(
    edge: DBRelationship,
    name_by_uuid: dict[uuid.UUID, str],
) -> dict[str, str]:
    rel_name = name_by_uuid.get(edge.rel_type_key, str(edge.rel_type_key))
    return {
        "from_artifact_id": str(edge.source_id),
        "to_artifact_id": str(edge.target_id),
        "relationship_type": rel_name,
    }


def _snapshot_bundle_entry(entity: DBEntity) -> dict[str, Any]:
    return {
        "snapshot_id": str(entity.id),
        "content_hash": entity.content_hash,
        "body": entity.attributes,
    }


def _stringify_backend_triple(triple: dict[str, Any]) -> str:
    surface = triple.get("surface", "unknown")
    path = triple.get("path", "default")
    revision = triple.get("revision")
    if revision:
        return f"{surface}.{path}@{revision}"
    return f"{surface}.{path}"


def _aggregate_costs(
    artifacts: list[DBEntity],
    *,
    run_stage: str,
) -> dict[str, Any]:
    total_by_currency: dict[str, float | int] = {}
    by_stage: dict[str, float | int] = {}
    by_backend: dict[str, float | int] = {}

    for entity in artifacts:
        if entity.entity_type != "orch_generation_artifact":
            continue
        attrs = entity.attributes if isinstance(entity.attributes, dict) else {}
        provenance = attrs.get("execution_provenance")
        if not isinstance(provenance, dict):
            continue
        cost = provenance.get("cost")
        if not isinstance(cost, dict):
            continue
        amount = cost.get("amount")
        currency = cost.get("currency")
        if amount is None or currency is None:
            continue
        amount_num: float | int
        if isinstance(amount, Decimal):
            amount_num = float(amount)
        elif isinstance(amount, int):
            amount_num = amount
        else:
            amount_num = float(amount)

        currency_key = str(currency)
        total_by_currency[currency_key] = total_by_currency.get(currency_key, 0) + amount_num

        stage_key = str(provenance.get("stage_id", run_stage))
        by_stage[stage_key] = by_stage.get(stage_key, 0) + amount_num

        triple = provenance.get("backend_identity_triple")
        if isinstance(triple, dict):
            backend_key = _stringify_backend_triple(triple)
            by_backend[backend_key] = by_backend.get(backend_key, 0) + amount_num

    return {
        "total_by_currency": total_by_currency,
        "by_stage": by_stage,
        "by_backend": by_backend,
    }


async def _find_audit_for_candidate(
    session: AsyncSession,
    candidate_artifact_id: uuid.UUID,
) -> Any:
    result = await session.execute(
        select(DBEntity).where(DBEntity.entity_type == "orch_audit_report")
    )
    candidate_str = str(candidate_artifact_id)
    for entity in result.scalars().all():
        attrs = entity.attributes if isinstance(entity.attributes, dict) else {}
        if str(attrs.get("candidate_artifact_id")) == candidate_str:
            from forge_bridge.store.orch_entity_views import DBOrchAuditReport

            return DBOrchAuditReport.from_entity(entity)
    return None


async def _superseded_within_run(
    session: AsyncSession,
    *,
    run_id: uuid.UUID,
    promoted_artifact_id: uuid.UUID,
) -> list[uuid.UUID]:
    run_str = str(run_id)
    result = await session.execute(
        select(DBEntity).where(
            DBEntity.entity_type == "orch_generation_artifact",
            DBEntity.status.in_(("complete", "partial")),
        )
    )
    superseded: list[uuid.UUID] = []
    for entity in result.scalars().all():
        if entity.id == promoted_artifact_id:
            continue
        attrs = entity.attributes if isinstance(entity.attributes, dict) else {}
        if str(attrs.get("run_id")) != run_str:
            continue
        superseded.append(entity.id)
    return superseded


def _normalize_for_json(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {str(k): _normalize_for_json(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return [_normalize_for_json(v) for v in value]
    return value
