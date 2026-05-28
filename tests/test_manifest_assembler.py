"""Tests for ProvenanceManifestAssembler (Phase 4B Step 11)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import delete, select

from forge_bridge.core.traits import Relationship
from forge_bridge.orchestration.errors import (
    InvalidManifestRequestError,
    ManifestPreconditionError,
)
from forge_bridge.orchestration.manifest import (
    ManifestSubgraphWalker,
    ProvenanceManifestAssembler,
)
from forge_bridge.store.content_addressed_repo import ContentAddressedRepo
from forge_bridge.store.models import DBEntity, DBEvent, DBRelationship
from forge_bridge.store.orch_audit_report_repo import AuditReportRepo
from forge_bridge.store.orch_capability_snapshot_repo import CapabilitySnapshotRepo
from forge_bridge.store.orch_execution_plan_repo import ExecutionPlanRepo
from forge_bridge.store.orch_generation_artifact_repo import GenerationArtifactRepo
from forge_bridge.store.orch_locked_intent_repo import LockedIntentRepo
from forge_bridge.store.orch_partial_fidelity_snapshot_repo import (
    PartialFidelitySnapshotRepo,
)
from forge_bridge.store.orch_pipeline_run_repo import PipelineRunRepo
from forge_bridge.store.orch_provenance_manifest_repo import ProvenanceManifestRepo
from forge_bridge.store.orch_rule_snapshot_repo import RuleSnapshotRepo
from forge_bridge.store.orch_spec_convergence_trace_repo import SpecConvergenceTraceRepo
from forge_bridge.store.orchestration_lifecycle_state_repo import (
    OrchestrationLifecycleStateRepo,
)
from forge_bridge.store.orchestration_promotion_ledger_repo import (
    OrchestrationPromotionLedgerRepo,
)
from forge_bridge.store.repo import RelationshipRepo

REL_CONTENT_SOURCE = uuid.UUID("00000000-0000-0000-0040-000000000001")
REL_ANCHORED_TO = uuid.UUID("00000000-0000-0000-0040-000000000002")


async def _manifest_events(session) -> list[DBEvent]:
    result = await session.execute(
        select(DBEvent)
        .where(DBEvent.event_type.like("manifest_%"))
        .order_by(DBEvent.occurred_at.asc())
    )
    return list(result.scalars().all())


async def _save_rel(session, source_id, target_id, rel_key) -> None:
    await RelationshipRepo(session).save(
        Relationship(source_id=source_id, target_id=target_id, rel_key=rel_key)
    )


async def _terminal_artifact(
    session,
    *,
    run_id: uuid.UUID,
    body: dict | None = None,
) -> uuid.UUID:
    repo = GenerationArtifactRepo(session)
    payload = {
        "run_id": str(run_id),
        "platform_locators": {"output": "https://cdn.example/out.mp4"},
        "content_provenance": {"reference_inputs": []},
        "execution_provenance": {
            "backend_identity_triple": {
                "surface": "test",
                "path": "backend",
                "revision": "v1",
            },
            "cost": {"currency": "USD", "amount": 10},
        },
    }
    if body:
        payload.update(body)
    submitted = await repo.insert_submitted(payload)
    terminal = await repo.transition(
        submitted.id,
        "complete",
        terminal_provenance=payload.get("execution_provenance"),
    )
    return terminal.id


async def _insert_terminal_gen_artifact(
    session,
    artifact_id: uuid.UUID,
    *,
    run_id: uuid.UUID,
    execution_provenance: dict | None = None,
    partial_fidelity_report: dict | None = None,
) -> uuid.UUID:
    provenance = execution_provenance or {
        "backend_identity_triple": {
            "surface": "test",
            "path": "backend",
            "revision": "v1",
        },
    }
    attrs: dict = {
        "run_id": str(run_id),
        "platform_locators": {"output": f"https://cdn.example/{artifact_id.hex[:8]}.mp4"},
        "content_provenance": {"reference_inputs": []},
        "execution_provenance": provenance,
        "polling_history": [],
    }
    if partial_fidelity_report is not None:
        attrs["partial_fidelity_report"] = partial_fidelity_report
    entity = DBEntity(
        id=artifact_id,
        entity_type="orch_generation_artifact",
        status="complete",
        content_hash=ContentAddressedRepo._canonical_hash(attrs),
        attributes=attrs,
    )
    session.add(entity)
    await session.flush()
    return artifact_id


async def _seed_happy_assembly(
    session,
    *,
    lineage_chain: bool = True,
    include_anchored: bool = True,
    sibling_partial: bool = True,
    rationale_record_id: uuid.UUID | None = None,
) -> dict:
    shot_id = uuid.uuid4()
    run_id = uuid.uuid4()

    rule = await RuleSnapshotRepo(session).insert_if_absent(
        {
            "rules": [{"rule_id": "R1", "statement": "anchor"}],
            "source_ref": "methodology/v17",
            "snapshot_timestamp": "2026-05-28T12:00:00Z",
        }
    )
    cap = await CapabilitySnapshotRepo(session).insert_if_absent(
        {"snapshots": [{"backend_identity_triple": {"surface": "test", "path": "x"}}]}
    )
    partial = await PartialFidelitySnapshotRepo(session).insert_if_absent(
        {"models": [{"backend_identity_triple": {"surface": "test", "path": "x"}}]}
    )
    intent = await LockedIntentRepo(session).insert_if_absent(
        {
            "source_read": {"shot_id": str(shot_id)},
            "change_manifest": [],
            "success_criteria": [
                {
                    "criterion_id": "c1",
                    "statement": "ok",
                    "measurement_spec": {"method": "iou"},
                    "tolerances": {"min": 0.7},
                }
            ],
            "allowed_compromises": [],
            "hard_constraints": [],
            "escalation_threshold": 0.9,
            "deliverable_spec": {"medium": "video"},
        }
    )
    trace = await SpecConvergenceTraceRepo(session).insert_if_absent(
        {"iterations": [{"version": 1}]}
    )
    plan = await ExecutionPlanRepo(session).insert_if_absent(
        {
            "operator_sequence": [{"op": "generate"}],
            "backend_assignments": {"generate": "test.backend"},
            "intent_id": str(intent.id),
            "rule_snapshot_id": str(rule.id),
            "capability_snapshot_id": str(cap.id),
            "partial_fidelity_snapshot_id": str(partial.id),
            "feasibility_verdict": "feasible",
        }
    )
    session.add(
        DBEntity(
            id=run_id,
            entity_type="orch_pipeline_run",
            content_hash=f"run-{run_id.hex}",
            attributes={
                "run_kind": "original",
                "intent_id": str(intent.id),
                "spec_convergence_trace_id": str(trace.id),
            },
        )
    )
    await OrchestrationLifecycleStateRepo(session).insert(
        run_id=run_id,
        shot_id=shot_id,
        current_stage="publish",
        status="completed",
        intent_id=intent.id,
        plan_id=plan.id,
    )

    source_id = uuid.uuid4()
    step1_id = uuid.uuid4()
    step2_id = uuid.uuid4()
    canonical_id = uuid.uuid4()

    if lineage_chain:
        for artifact_id, cost, partial_report in (
            (source_id, None, None),
            (step1_id, {"currency": "USD", "amount": 5}, None),
            (
                step2_id,
                {"currency": "credits", "amount": 200},
                {
                    "record_id": str(step2_id),
                    "verdict": "partial",
                    "dimensions": [{"axis": "motion", "scalar": 0.1}],
                },
            ),
            (canonical_id, {"currency": "USD", "amount": 10}, None),
        ):
            provenance = {
                "backend_identity_triple": {
                    "surface": "test",
                    "path": "backend" if artifact_id != step2_id else "backend_credits",
                    "revision": "v1",
                },
                "rule_snapshot_id": str(rule.id),
            }
            if cost is not None:
                provenance["cost"] = cost
            await _insert_terminal_gen_artifact(
                session,
                artifact_id,
                run_id=run_id,
                execution_provenance=provenance,
                partial_fidelity_report=partial_report,
            )

        await _save_rel(session, step2_id, canonical_id, REL_CONTENT_SOURCE)
        await _save_rel(session, step1_id, step2_id, REL_CONTENT_SOURCE)
        await _save_rel(session, source_id, step1_id, REL_CONTENT_SOURCE)
        if include_anchored:
            await _save_rel(session, step2_id, source_id, REL_ANCHORED_TO)
    else:
        await _insert_terminal_gen_artifact(
            session,
            canonical_id,
            run_id=run_id,
            execution_provenance={
                "backend_identity_triple": {
                    "surface": "test",
                    "path": "backend",
                    "revision": "v1",
                },
                "cost": {"currency": "USD", "amount": 10},
                "rule_snapshot_id": str(rule.id),
            },
        )

    sibling_id = None
    if sibling_partial:
        sibling_id = uuid.uuid4()
        await _insert_terminal_gen_artifact(
            session,
            sibling_id,
            run_id=run_id,
            execution_provenance={
                "backend_identity_triple": {
                    "surface": "test",
                    "path": "backend",
                    "revision": "v1",
                },
                "cost": {"currency": "USD", "amount": 999},
            },
            partial_fidelity_report={
                "record_id": "sibling-partial",
                "verdict": "partial",
            },
        )

    audit = await AuditReportRepo(session).insert_if_absent(
        {
            "candidate_artifact_id": str(canonical_id),
            "intent_id": str(intent.id),
            "rules_snapshot_ref": str(rule.id),
            "per_criterion": [],
            "cross_criterion_summary": {"overall_verdict": "pass"},
        }
    )

    rationale = "operator selected best candidate"
    if rationale_record_id is not None:
        rationale = f"see record {rationale_record_id} for context"

    promotion = await OrchestrationPromotionLedgerRepo(session).insert_promotion(
        shot_id=shot_id,
        promoted_artifact_id=canonical_id,
        promoted_by="operator",
        rationale=rationale,
        audit_report_id=audit.id,
        promoted_at=datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc),
    )

    return {
        "shot_id": shot_id,
        "run_id": run_id,
        "canonical_id": canonical_id,
        "promotion_id": promotion.promotion_id,
        "rule_id": rule.id,
        "sibling_id": sibling_id,
        "source_id": source_id if lineage_chain else None,
        "step1_id": step1_id if lineage_chain else None,
        "step2_id": step2_id if lineage_chain else None,
        "rationale_record_id": rationale_record_id,
    }


# ── Request validation ────────────────────────────────────────────────────────


async def test_assemble_zero_params_raises(session_factory) -> None:
    async with session_factory() as session:
        with pytest.raises(InvalidManifestRequestError):
            await ProvenanceManifestAssembler(session).assemble()


async def test_assemble_multiple_params_raises(session_factory) -> None:
    async with session_factory() as session:
        with pytest.raises(InvalidManifestRequestError):
            await ProvenanceManifestAssembler(session).assemble(
                promotion_id=uuid.uuid4(),
                shot_id=uuid.uuid4(),
            )


# ── Resolution paths ──────────────────────────────────────────────────────────


async def test_assemble_by_promotion_id(session_factory) -> None:
    async with session_factory() as session:
        ctx = await _seed_happy_assembly(session, lineage_chain=False)
        manifest = await ProvenanceManifestAssembler(session).assemble(
            promotion_id=ctx["promotion_id"]
        )
        await session.commit()
    assert manifest.attributes["promotion_ledger_entry_id"] == str(
        ctx["promotion_id"]
    )


async def test_assemble_by_canonical_artifact_id(session_factory) -> None:
    async with session_factory() as session:
        ctx = await _seed_happy_assembly(session, lineage_chain=False)
        manifest = await ProvenanceManifestAssembler(session).assemble(
            canonical_artifact_id=ctx["canonical_id"]
        )
        await session.commit()
    assert manifest.attributes["canonical_artifact_id"] == str(ctx["canonical_id"])


async def test_assemble_by_shot_id(session_factory) -> None:
    async with session_factory() as session:
        ctx = await _seed_happy_assembly(session, lineage_chain=False)
        manifest = await ProvenanceManifestAssembler(session).assemble(
            shot_id=ctx["shot_id"]
        )
        await session.commit()
    assert manifest.attributes["shot_id"] == str(ctx["shot_id"])


# ── Preconditions ───────────────────────────────────────────────────────────────


async def test_canonical_never_promoted(session_factory) -> None:
    async with session_factory() as session:
        artifact_id = await _terminal_artifact(session, run_id=uuid.uuid4())
        with pytest.raises(ManifestPreconditionError) as exc:
            await ProvenanceManifestAssembler(session).assemble(
                canonical_artifact_id=artifact_id
            )
        await session.commit()
    assert exc.value.reason == "canonical_never_promoted"


async def test_canonical_not_terminal(session_factory) -> None:
    async with session_factory() as session:
        run_id = uuid.uuid4()
        shot_id = uuid.uuid4()
        submitted = await GenerationArtifactRepo(session).insert_submitted(
            {"run_id": str(run_id)}
        )
        promotion = await OrchestrationPromotionLedgerRepo(session).insert_promotion(
            shot_id=shot_id,
            promoted_artifact_id=submitted.id,
            promoted_by="operator",
            rationale="premature",
        )
        with pytest.raises(ManifestPreconditionError) as exc:
            await ProvenanceManifestAssembler(session).assemble(
                promotion_id=promotion.promotion_id
            )
        await session.commit()
    assert exc.value.reason == "canonical_not_terminal"


# ── Subgraph walker ───────────────────────────────────────────────────────────


async def test_walker_single_artifact_closure(session_factory) -> None:
    async with session_factory() as session:
        ctx = await _seed_happy_assembly(session, lineage_chain=False)
        closure = await ManifestSubgraphWalker(session).walk_backward(
            ctx["canonical_id"]
        )
    assert len(closure.artifacts) == 1
    assert closure.artifacts[0].id == ctx["canonical_id"]
    assert closure.edges == []


async def test_walker_linear_chain(session_factory) -> None:
    async with session_factory() as session:
        ctx = await _seed_happy_assembly(session, include_anchored=False)
        closure = await ManifestSubgraphWalker(session).walk_backward(
            ctx["canonical_id"]
        )
    assert len(closure.artifacts) == 4
    assert len(closure.edges) == 3


async def test_walker_anchored_chain_includes_both_edge_types(session_factory) -> None:
    async with session_factory() as session:
        ctx = await _seed_happy_assembly(session)
        closure = await ManifestSubgraphWalker(session).walk_backward(
            ctx["canonical_id"]
        )
    rel_types = {edge.rel_type_key for edge in closure.edges}
    assert REL_CONTENT_SOURCE in rel_types
    assert REL_ANCHORED_TO in rel_types


async def test_walker_cycle_protection(session_factory) -> None:
    a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    async with session_factory() as session:
        run_id = uuid.uuid4()
        for artifact_id in (a, b, c):
            await _insert_terminal_gen_artifact(session, artifact_id, run_id=run_id)
        await _save_rel(session, b, a, REL_CONTENT_SOURCE)
        await _save_rel(session, c, b, REL_CONTENT_SOURCE)
        await _save_rel(session, a, c, REL_CONTENT_SOURCE)
        closure = await ManifestSubgraphWalker(session).walk_backward(a)
    assert len(closure.artifacts) == 3


async def test_walker_extracts_snapshot_ids(session_factory) -> None:
    async with session_factory() as session:
        ctx = await _seed_happy_assembly(session)
        closure = await ManifestSubgraphWalker(session).walk_backward(
            ctx["canonical_id"]
        )
    assert ctx["rule_id"] in closure.snapshot_ids.rule_snapshot_ids


# ── Manifest content ──────────────────────────────────────────────────────────


async def test_happy_path_manifest_fields(session_factory) -> None:
    async with session_factory() as session:
        ctx = await _seed_happy_assembly(session)
        manifest = await ProvenanceManifestAssembler(session).assemble(
            promotion_id=ctx["promotion_id"],
            assembled_by="test-assembler",
        )
        await session.commit()
        attrs = manifest.attributes
    assert attrs["assembled_by"] == "test-assembler"
    assert attrs["assembled_at"] == "2026-05-28T12:00:00+00:00"
    assert manifest.content_hash
    lineage = attrs["full_lineage"]
    assert len(lineage["artifacts"]) == 4
    assert len(lineage["edges"]) == 4
    assert all("relationship_type" in edge for edge in lineage["edges"])
    bundled = attrs["snapshots_bundled_by_content"]["rule_snapshot"]
    assert bundled is not None
    assert bundled["body"]["source_ref"] == "methodology/v17"
    assert attrs["cost_summary"]["total_by_currency"]["USD"] == 15
    assert attrs["cost_summary"]["total_by_currency"]["credits"] == 200


async def test_idempotent_assembly(session_factory) -> None:
    async with session_factory() as session:
        ctx = await _seed_happy_assembly(session, lineage_chain=False)
        assembler = ProvenanceManifestAssembler(session)
        first = await assembler.assemble(promotion_id=ctx["promotion_id"])
        second = await assembler.assemble(promotion_id=ctx["promotion_id"])
        await session.commit()
    assert first.id == second.id
    assert first.content_hash == second.content_hash


# ── Refusal / partial inclusion ─────────────────────────────────────────────────


async def test_partial_in_closure_included(session_factory) -> None:
    async with session_factory() as session:
        ctx = await _seed_happy_assembly(session)
        manifest = await ProvenanceManifestAssembler(session).assemble(
            promotion_id=ctx["promotion_id"]
        )
        await session.commit()
    records = manifest.attributes["refusal_and_partial_records"]
    assert any(r.get("kind") == "partial" for r in records)


async def test_sibling_partial_excluded(session_factory) -> None:
    async with session_factory() as session:
        ctx = await _seed_happy_assembly(session, lineage_chain=False)
        manifest = await ProvenanceManifestAssembler(session).assemble(
            promotion_id=ctx["promotion_id"]
        )
        await session.commit()
    records = manifest.attributes["refusal_and_partial_records"]
    assert all(r.get("record_id") != "sibling-partial" for r in records)


async def test_rationale_record_included_outside_closure(session_factory) -> None:
    external_id = uuid.uuid4()
    async with session_factory() as session:
        await _insert_terminal_gen_artifact(
            session,
            external_id,
            run_id=uuid.uuid4(),
            partial_fidelity_report={
                "record_id": str(external_id),
                "verdict": "partial",
            },
        )

        ctx = await _seed_happy_assembly(
            session,
            lineage_chain=False,
            sibling_partial=False,
            rationale_record_id=external_id,
        )
        manifest = await ProvenanceManifestAssembler(session).assemble(
            promotion_id=ctx["promotion_id"]
        )
        await session.commit()
    record_ids = {
        r.get("record_id") for r in manifest.attributes["refusal_and_partial_records"]
    }
    assert str(external_id) in record_ids


# ── Snapshot portability ───────────────────────────────────────────────────────


async def test_snapshot_embedded_by_content(session_factory) -> None:
    async with session_factory() as session:
        ctx = await _seed_happy_assembly(session, lineage_chain=False)
        manifest = await ProvenanceManifestAssembler(session).assemble(
            promotion_id=ctx["promotion_id"]
        )
        embedded = manifest.attributes["snapshots_bundled_by_content"]["rule_snapshot"][
            "body"
        ]
        live = await RuleSnapshotRepo(session).get_by_id(ctx["rule_id"])
        await session.execute(delete(DBEntity).where(DBEntity.id == ctx["rule_id"]))
        await session.commit()
    assert embedded == live.attributes


# ── Cost aggregation ──────────────────────────────────────────────────────────


async def test_cost_null_and_missing_provenance(session_factory) -> None:
    async with session_factory() as session:
        ctx = await _seed_happy_assembly(session, lineage_chain=False)
        extra_id = uuid.uuid4()
        await _insert_terminal_gen_artifact(
            session,
            extra_id,
            run_id=ctx["run_id"],
            execution_provenance={"cost": None},
        )
        await _save_rel(session, extra_id, ctx["canonical_id"], REL_CONTENT_SOURCE)
        manifest = await ProvenanceManifestAssembler(session).assemble(
            promotion_id=ctx["promotion_id"]
        )
        await session.commit()
    assert "USD" in manifest.attributes["cost_summary"]["total_by_currency"]


async def test_cost_by_backend_aggregates(session_factory) -> None:
    async with session_factory() as session:
        ctx = await _seed_happy_assembly(session)
        manifest = await ProvenanceManifestAssembler(session).assemble(
            promotion_id=ctx["promotion_id"]
        )
        await session.commit()
    by_backend = manifest.attributes["cost_summary"]["by_backend"]
    assert by_backend["test.backend@v1"] == 15


# ── Replay manifests ───────────────────────────────────────────────────────────


async def test_two_promotions_two_manifests(session_factory) -> None:
    async with session_factory() as session:
        ctx1 = await _seed_happy_assembly(session, lineage_chain=False)
        ctx2 = await _seed_happy_assembly(session, lineage_chain=False)
        m1 = await ProvenanceManifestAssembler(session).assemble(
            promotion_id=ctx1["promotion_id"]
        )
        m2 = await ProvenanceManifestAssembler(session).assemble(
            promotion_id=ctx2["promotion_id"]
        )
        await session.commit()
    assert m1.id != m2.id
    assert m1.content_hash != m2.content_hash


# ── Transaction + events ───────────────────────────────────────────────────────


async def test_not_visible_before_commit(session_factory) -> None:
    manifest_id = None
    async with session_factory() as session:
        ctx = await _seed_happy_assembly(session, lineage_chain=False)
        manifest = await ProvenanceManifestAssembler(session).assemble(
            promotion_id=ctx["promotion_id"]
        )
        manifest_id = manifest.id

    async with session_factory() as session:
        assert await ProvenanceManifestRepo(session).get_by_id(manifest_id) is None


async def test_event_sequence_happy_path(session_factory) -> None:
    async with session_factory() as session:
        ctx = await _seed_happy_assembly(session, lineage_chain=False)
        await ProvenanceManifestAssembler(session).assemble(
            promotion_id=ctx["promotion_id"]
        )
        await session.commit()

    async with session_factory() as session:
        types = {e.event_type for e in await _manifest_events(session)}
        assert types == {
            "manifest_assembly_started",
            "manifest_assembly_completed",
        }


async def test_event_sequence_refused(session_factory) -> None:
    async with session_factory() as session:
        with pytest.raises(ManifestPreconditionError):
            await ProvenanceManifestAssembler(session).assemble(
                promotion_id=uuid.uuid4()
            )
        await session.commit()

    async with session_factory() as session:
        types = [e.event_type for e in await _manifest_events(session)]
        assert types == ["manifest_assembly_refused"]
