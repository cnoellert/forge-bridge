"""Phase 4B Step 4 — parametric tests for pure content-addressed orch_* repos."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from forge_bridge.store.content_addressed_repo import ContentAddressedRepo, ImmutableArtifactError
from forge_bridge.store.models import DBEntity
from forge_bridge.store.orch_audit_report_repo import AuditReportRepo
from forge_bridge.store.orch_capability_snapshot_repo import CapabilitySnapshotRepo
from forge_bridge.store.orch_entity_views import (
    DBOrchAuditReport,
    DBOrchCapabilitySnapshot,
    DBOrchExecutionPlan,
    DBOrchInputsCatalog,
    DBOrchPartialFidelitySnapshot,
    DBOrchPipelineRun,
    DBOrchProvenanceManifest,
    DBOrchRuleSnapshot,
    DBOrchSpecConvergenceTrace,
    DBOrchValidationReport,
)
from forge_bridge.store.orch_execution_plan_repo import ExecutionPlanRepo
from forge_bridge.store.orch_inputs_catalog_repo import InputsCatalogRepo
from forge_bridge.store.orch_partial_fidelity_snapshot_repo import PartialFidelitySnapshotRepo
from forge_bridge.store.orch_pipeline_run_repo import PipelineRunRepo
from forge_bridge.store.orch_provenance_manifest_repo import ProvenanceManifestRepo
from forge_bridge.store.orch_rule_snapshot_repo import RuleSnapshotRepo
from forge_bridge.store.orch_spec_convergence_trace_repo import SpecConvergenceTraceRepo
from forge_bridge.store.orch_validation_report_repo import ValidationReportRepo


def _pipeline_run_body(**overrides) -> dict:
    body = {
        "run_kind": "original",
        "intent_id": str(uuid.uuid4()),
    }
    body.update(overrides)
    return body


def _inputs_catalog_body(**overrides) -> dict:
    body = {
        "inputs": [{"role": "structural", "ref": "img-1"}],
        "role_assignments": {"structural": "img-1"},
    }
    body.update(overrides)
    return body


def _spec_trace_body(**overrides) -> dict:
    body = {"iterations": [{"version": 1, "spec": "draft"}]}
    body.update(overrides)
    return body


def _rule_snapshot_body(**overrides) -> dict:
    body = {
        "rules": [{"rule_id": "R1", "statement": "anchor to source truth"}],
        "source_ref": "methodology/v17",
        "snapshot_timestamp": "2026-05-28T12:00:00Z",
    }
    body.update(overrides)
    return body


def _capability_snapshot_body(**overrides) -> dict:
    body = {
        "snapshots": [
            {
                "backend_identity_triple": {"surface": "magnific-api"},
                "declaration_hash": "abc",
                "capabilities_opaque": {},
            }
        ]
    }
    body.update(overrides)
    return body


def _partial_fidelity_body(**overrides) -> dict:
    body = {
        "models": [
            {
                "backend_identity_triple": {"surface": "magnific-api"},
                "dimensions": [{"axis": "dynamic_range", "scalar": 0.6}],
            }
        ]
    }
    body.update(overrides)
    return body


def _execution_plan_body(**overrides) -> dict:
    body = {
        "operator_sequence": ["generate_video_from_image"],
        "backend_assignments": {"generate_video_from_image": "magnific-api"},
        "transforms_inserted": [],
        "external_uploads_required": [],
        "cost_estimate": {"USD": 1.0},
        "predicted_compromise_consumption": [],
        "provenance_obligations": [],
        "feasibility_verdict": "feasible",
        "feasibility_explanation": "within budget",
        "intent_id": str(uuid.uuid4()),
        "planner_version": "4b-v0.1",
        "capability_snapshot_id": str(uuid.uuid4()),
        "rule_snapshot_id": str(uuid.uuid4()),
        "partial_fidelity_snapshot_id": str(uuid.uuid4()),
    }
    body.update(overrides)
    return body


def _validation_report_body(**overrides) -> dict:
    body = {
        "verdict": "pass",
        "evidence": {"notes": "ok"},
        "evidence_refs": [],
    }
    body.update(overrides)
    return body


def _audit_report_body(**overrides) -> dict:
    body = {
        "candidate_artifact_id": str(uuid.uuid4()),
        "intent_id": str(uuid.uuid4()),
        "rules_snapshot_ref": str(uuid.uuid4()),
        "per_criterion": [],
        "cross_criterion_summary": {"overall_verdict": "partial+remediation"},
    }
    body.update(overrides)
    return body


def _provenance_manifest_body(**overrides) -> dict:
    body = {
        "shot_id": str(uuid.uuid4()),
        "run_id": str(uuid.uuid4()),
        "intent_id": str(uuid.uuid4()),
        "spec_convergence_trace_id": str(uuid.uuid4()),
        "execution_plan_id": str(uuid.uuid4()),
        "audit_report_id": str(uuid.uuid4()),
        "promotion_ledger_entry_id": str(uuid.uuid4()),
        "canonical_artifact_id": str(uuid.uuid4()),
        "canonical_content_hash": "a" * 64,
        "full_lineage": [],
        "snapshots_bundled_by_content": {},
        "refusal_and_partial_records": [],
        "cost_summary": {"USD": 1.0},
    }
    body.update(overrides)
    return body


PURE_ORCH_REPO_CASES = [
    pytest.param(
        PipelineRunRepo,
        DBOrchPipelineRun,
        "orch_pipeline_run",
        _pipeline_run_body,
        "active",
        id="orch_pipeline_run",
    ),
    pytest.param(
        InputsCatalogRepo,
        DBOrchInputsCatalog,
        "orch_inputs_catalog",
        _inputs_catalog_body,
        "locked",
        id="orch_inputs_catalog",
    ),
    pytest.param(
        SpecConvergenceTraceRepo,
        DBOrchSpecConvergenceTrace,
        "orch_spec_convergence_trace",
        lambda: _spec_trace_body(),
        "open",
        id="orch_spec_convergence_trace_open",
    ),
    pytest.param(
        RuleSnapshotRepo,
        DBOrchRuleSnapshot,
        "orch_rule_snapshot",
        _rule_snapshot_body,
        "locked",
        id="orch_rule_snapshot",
    ),
    pytest.param(
        CapabilitySnapshotRepo,
        DBOrchCapabilitySnapshot,
        "orch_capability_snapshot",
        _capability_snapshot_body,
        "locked",
        id="orch_capability_snapshot",
    ),
    pytest.param(
        PartialFidelitySnapshotRepo,
        DBOrchPartialFidelitySnapshot,
        "orch_partial_fidelity_snapshot",
        _partial_fidelity_body,
        "locked",
        id="orch_partial_fidelity_snapshot",
    ),
    pytest.param(
        ExecutionPlanRepo,
        DBOrchExecutionPlan,
        "orch_execution_plan",
        _execution_plan_body,
        "feasible",
        id="orch_execution_plan",
    ),
    pytest.param(
        ValidationReportRepo,
        DBOrchValidationReport,
        "orch_validation_report",
        _validation_report_body,
        "pass",
        id="orch_validation_report",
    ),
    pytest.param(
        AuditReportRepo,
        DBOrchAuditReport,
        "orch_audit_report",
        _audit_report_body,
        "partial+remediation",
        id="orch_audit_report",
    ),
    pytest.param(
        ProvenanceManifestRepo,
        DBOrchProvenanceManifest,
        "orch_provenance_manifest",
        _provenance_manifest_body,
        "locked",
        id="orch_provenance_manifest",
    ),
]


@pytest.mark.parametrize(
    "repo_cls,model_cls,entity_type,body_factory,expected_status",
    PURE_ORCH_REPO_CASES,
)
async def test_insert_if_absent_idempotent(
    session_factory,
    repo_cls,
    model_cls,
    entity_type,
    body_factory,
    expected_status,
) -> None:
    body = body_factory()

    async with session_factory() as session:
        repo = repo_cls(session)
        first = await repo.insert_if_absent(body)
        second = await repo.insert_if_absent(body)
        await session.commit()
        assert first.id == second.id

    async with session_factory() as session:
        count = await session.scalar(
            select(func.count())
            .select_from(DBEntity)
            .where(DBEntity.entity_type == entity_type)
        )
        assert count == 1


@pytest.mark.parametrize(
    "repo_cls,model_cls,entity_type,body_factory,expected_status",
    PURE_ORCH_REPO_CASES,
)
async def test_get_by_content_hash(
    session_factory,
    repo_cls,
    model_cls,
    entity_type,
    body_factory,
    expected_status,
) -> None:
    body = body_factory()

    async with session_factory() as session:
        repo = repo_cls(session)
        inserted = await repo.insert_if_absent(body)
        await session.commit()
        content_hash = inserted.content_hash

    async with session_factory() as session:
        repo = repo_cls(session)
        found = await repo.get_by_content_hash(content_hash)
        assert found is not None
        assert found.id == inserted.id


@pytest.mark.parametrize(
    "repo_cls,model_cls,entity_type,body_factory,expected_status",
    PURE_ORCH_REPO_CASES,
)
async def test_update_refused(
    session_factory,
    repo_cls,
    model_cls,
    entity_type,
    body_factory,
    expected_status,
) -> None:
    body = body_factory()

    async with session_factory() as session:
        repo = repo_cls(session)
        inserted = await repo.insert_if_absent(body)
        await session.commit()
        entity_id = inserted.id

    async with session_factory() as session:
        repo = repo_cls(session)
        with pytest.raises(ImmutableArtifactError) as exc:
            await repo.update(entity_id, {"tampered": True})
        assert entity_type in str(exc.value)


@pytest.mark.parametrize(
    "repo_cls,model_cls,entity_type,body_factory,expected_status",
    PURE_ORCH_REPO_CASES,
)
async def test_delete_refused(
    session_factory,
    repo_cls,
    model_cls,
    entity_type,
    body_factory,
    expected_status,
) -> None:
    body = body_factory()

    async with session_factory() as session:
        repo = repo_cls(session)
        inserted = await repo.insert_if_absent(body)
        await session.commit()
        entity_id = inserted.id

    async with session_factory() as session:
        repo = repo_cls(session)
        with pytest.raises(ImmutableArtifactError) as exc:
            await repo.delete(entity_id)
        assert entity_type in str(exc.value)


@pytest.mark.parametrize(
    "repo_cls,model_cls,entity_type,body_factory,expected_status",
    PURE_ORCH_REPO_CASES,
)
async def test_status_default(
    session_factory,
    repo_cls,
    model_cls,
    entity_type,
    body_factory,
    expected_status,
) -> None:
    body = body_factory()

    async with session_factory() as session:
        repo = repo_cls(session)
        inserted = await repo.insert_if_absent(body)
        await session.commit()
        assert inserted.status == expected_status


async def test_spec_convergence_trace_locked_status_when_lock_event_present(
    session_factory,
) -> None:
    body = _spec_trace_body(lock_event={"locked_at": "2026-05-28T12:00:00Z"})

    async with session_factory() as session:
        repo = SpecConvergenceTraceRepo(session)
        inserted = await repo.insert_if_absent(body)
        await session.commit()
        assert inserted.status == "locked"
        assert inserted.locked is True


async def test_pipeline_run_typed_accessors(session_factory) -> None:
    intent_id = str(uuid.uuid4())
    body = _pipeline_run_body(
        intent_id=intent_id,
        source_run_id=str(uuid.uuid4()),
        effective_pinning_policy={"mode": "strict"},
    )

    async with session_factory() as session:
        row = await PipelineRunRepo(session).insert_if_absent(body)
        await session.commit()
        assert row.run_kind == "original"
        assert row.intent_id == intent_id
        assert row.effective_pinning_policy == {"mode": "strict"}


async def test_inputs_catalog_typed_accessors(session_factory) -> None:
    body = _inputs_catalog_body()

    async with session_factory() as session:
        row = await InputsCatalogRepo(session).insert_if_absent(body)
        await session.commit()
        assert row.inputs == body["inputs"]
        assert row.role_assignments == body["role_assignments"]


async def test_rule_snapshot_typed_accessors(session_factory) -> None:
    body = _rule_snapshot_body()

    async with session_factory() as session:
        row = await RuleSnapshotRepo(session).insert_if_absent(body)
        await session.commit()
        assert row.rules == body["rules"]
        assert row.snapshot_timestamp == body["snapshot_timestamp"]


async def test_capability_snapshot_typed_accessors(session_factory) -> None:
    body = _capability_snapshot_body()

    async with session_factory() as session:
        row = await CapabilitySnapshotRepo(session).insert_if_absent(body)
        await session.commit()
        assert row.snapshots == body["snapshots"]


async def test_partial_fidelity_snapshot_typed_accessors(session_factory) -> None:
    body = _partial_fidelity_body()

    async with session_factory() as session:
        row = await PartialFidelitySnapshotRepo(session).insert_if_absent(body)
        await session.commit()
        assert row.models == body["models"]


async def test_execution_plan_typed_accessors(session_factory) -> None:
    body = _execution_plan_body()

    async with session_factory() as session:
        row = await ExecutionPlanRepo(session).insert_if_absent(body)
        await session.commit()
        assert row.feasibility_verdict == "feasible"
        assert row.operator_sequence == body["operator_sequence"]
        assert row.planner_version == "4b-v0.1"


async def test_validation_report_typed_accessors(session_factory) -> None:
    body = _validation_report_body()

    async with session_factory() as session:
        row = await ValidationReportRepo(session).insert_if_absent(body)
        await session.commit()
        assert row.verdict == "pass"
        assert row.evidence_refs == []


async def test_audit_report_typed_accessors(session_factory) -> None:
    body = _audit_report_body()

    async with session_factory() as session:
        row = await AuditReportRepo(session).insert_if_absent(body)
        await session.commit()
        assert row.overall_verdict == "partial+remediation"
        assert row.per_criterion == []


async def test_provenance_manifest_typed_accessors(session_factory) -> None:
    body = _provenance_manifest_body()

    async with session_factory() as session:
        row = await ProvenanceManifestRepo(session).insert_if_absent(body)
        await session.commit()
        assert row.canonical_content_hash == body["canonical_content_hash"]
        assert row.cost_summary == body["cost_summary"]
