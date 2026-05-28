"""Tests for ReplayEngine (Phase 4B Step 10)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import delete, select

from forge_bridge.orchestration.engine import GraphEngine
from forge_bridge.orchestration.errors import (
    AmendedIntentLineageError,
    InvalidReconstructionRequestError,
    ReplayRefusalError,
)
from forge_bridge.orchestration.identity_registries import (
    InMemoryTrainedIdentityRegistry,
    TrainedIdentityRecord,
)
from forge_bridge.orchestration.replay import (
    RUN_LINEAGE_REL_KEYS,
    EffectivePinningPolicy,
    ReconstructionRequest,
    ReplayEngine,
)
from forge_bridge.store.models import DBEntity, DBEvent
from forge_bridge.store.orch_capability_snapshot_repo import CapabilitySnapshotRepo
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
from forge_bridge.store.repo import RelationshipRepo

from tests.test_planner import (
    _capability_body,
    _locked_intent_body,
    _make_planner,
    _partial_fidelity_body,
    _plan_kwargs,
    _rule_snapshot_body,
)


def _replay_request(**overrides) -> ReconstructionRequest:
    defaults = {
        "request_id": uuid.uuid4(),
        "kind": "replay",
        "source_run_id": uuid.uuid4(),
        "authored_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return ReconstructionRequest(**defaults)


async def _replay_events(session) -> list[DBEvent]:
    result = await session.execute(
        select(DBEvent)
        .where(DBEvent.event_type.like("replay_%"))
        .order_by(DBEvent.occurred_at.asc())
    )
    return list(result.scalars().all())


def _make_replay_engine(session) -> ReplayEngine:
    return ReplayEngine(
        session,
        graph_engine=GraphEngine(session),
        planner=_make_planner(session),
    )


async def _seed_completed_source_run(
    session,
    *,
    capability: dict | None = None,
    with_trace: bool = True,
    authored_at: datetime | None = None,
) -> dict:
    intent = await LockedIntentRepo(session).insert_if_absent(_locked_intent_body())
    rule = await RuleSnapshotRepo(session).insert_if_absent(_rule_snapshot_body())
    partial = await PartialFidelitySnapshotRepo(session).insert_if_absent(
        _partial_fidelity_body()
    )
    cap_body = _capability_body(**(capability or {}))
    cap = await CapabilitySnapshotRepo(session).insert_if_absent(cap_body)
    trace = None
    trace_id_str = None
    if with_trace:
        trace = await SpecConvergenceTraceRepo(session).insert_if_absent(
            {"iterations": [{"version": 1}]}
        )
        trace_id_str = str(trace.id)
    authored = authored_at or datetime.now(timezone.utc)
    run = await PipelineRunRepo(session).insert_if_absent(
        {
            "run_kind": "original",
            "intent_id": str(intent.id),
            "spec_convergence_trace_id": trace_id_str,
            "authored_at": authored.isoformat(),
        }
    )
    ids = {
        "intent_id": intent.id,
        "rule_snapshot_id": rule.id,
        "partial_fidelity_snapshot_id": partial.id,
        "capability_snapshot_id": cap.id,
        "run_id": run.id,
    }
    planner = _make_planner(session)
    plan = await planner.plan(**_plan_kwargs(ids))
    shot_id = uuid.uuid4()
    engine = GraphEngine(session)
    await engine.create_run(run_id=run.id, shot_id=shot_id)
    await engine.transition(run.id, to_stage="spec_convergence")
    await engine.apply_decision_event(
        run.id, "lock_intent", {"intent_id": str(intent.id)}
    )
    await engine.transition(
        run.id, to_stage="execution", plan_id=plan.id, intent_id=intent.id
    )
    await engine.transition(run.id, to_stage="audit")
    promoted = uuid.uuid4()
    await engine.apply_decision_event(
        run.id, "promote_candidate", {"promoted_artifact_id": str(promoted)}
    )
    await engine.transition(run.id, to_stage="publish")
    await engine.transition(run.id, to_status="completed")
    return {
        **ids,
        "plan_id": plan.id,
        "shot_id": shot_id,
        "trace_id": trace.id if trace else None,
        "plan": plan,
        "authored_at": authored,
    }


# ── Request validation ────────────────────────────────────────────────────────


def test_reconstruction_request_remediation_requires_entry() -> None:
    with pytest.raises(InvalidReconstructionRequestError):
        ReconstructionRequest(
            request_id=uuid.uuid4(),
            kind="remediation",
            source_run_id=uuid.uuid4(),
        )


def test_reconstruction_request_replay_forbids_entry() -> None:
    with pytest.raises(InvalidReconstructionRequestError):
        ReconstructionRequest(
            request_id=uuid.uuid4(),
            kind="replay",
            source_run_id=uuid.uuid4(),
            remediation_entry="replan_same_intent",
        )


async def test_replan_amended_intent_requires_amended_id(session_factory) -> None:
    async with session_factory() as session:
        source = await _seed_completed_source_run(session)
        engine = _make_replay_engine(session)
        request = _replay_request(
            kind="remediation",
            source_run_id=source["run_id"],
            remediation_entry="replan_amended_intent",
        )
        with pytest.raises(InvalidReconstructionRequestError):
            await engine.reconstruct(request)


# ── Source run preconditions ──────────────────────────────────────────────────


async def test_source_run_incomplete_refuses(session_factory) -> None:
    async with session_factory() as session:
        run = await PipelineRunRepo(session).insert_if_absent(
            {"run_kind": "original", "intent_id": str(uuid.uuid4())}
        )
        await GraphEngine(session).create_run(run_id=run.id, shot_id=uuid.uuid4())
        engine = _make_replay_engine(session)
        request = _replay_request(source_run_id=run.id)
        with pytest.raises(ReplayRefusalError) as exc:
            await engine.reconstruct(request)
        await session.commit()
    assert exc.value.refusal_code == "source_run_incomplete"
    async with session_factory() as session:
        events = await _replay_events(session)
        types = [e.event_type for e in events]
        assert types == ["replay_initiated", "replay_refusal_pre_validation"]


async def test_completed_source_run_proceeds(session_factory) -> None:
    async with session_factory() as session:
        source = await _seed_completed_source_run(session)
        engine = _make_replay_engine(session)
        request = _replay_request(source_run_id=source["run_id"])
        lifecycle = await engine.reconstruct(request)
        await session.commit()
    assert lifecycle.current_stage == "execution"
    assert lifecycle.status == "active"


async def test_spec_convergence_trace_missing_refuses(session_factory) -> None:
    async with session_factory() as session:
        source = await _seed_completed_source_run(session, with_trace=False)
        engine = _make_replay_engine(session)
        request = _replay_request(source_run_id=source["run_id"])
        with pytest.raises(ReplayRefusalError) as exc:
            await engine.reconstruct(request)
        await session.commit()
    assert exc.value.refusal_code == "spec_convergence_trace_missing"


# ── Pinning resolution ────────────────────────────────────────────────────────


async def test_honor_original_uses_source_rule_snapshot(session_factory) -> None:
    async with session_factory() as session:
        source = await _seed_completed_source_run(session)
        planner = _make_planner(session)
        engine = ReplayEngine(
            session,
            graph_engine=GraphEngine(session),
            planner=planner,
        )
        request = _replay_request(
            source_run_id=source["run_id"],
            pinning_mode="honor_original",
        )
        with patch.object(
            planner, "plan", wraps=planner.plan
        ) as plan_mock:
            await engine.reconstruct(request)
            await session.commit()
            assert plan_mock.await_args.kwargs["rule_snapshot_id"] == source[
                "rule_snapshot_id"
            ]


async def test_honor_original_deleted_rule_snapshot_refuses(session_factory) -> None:
    async with session_factory() as session:
        source = await _seed_completed_source_run(session)
        await session.execute(
            delete(DBEntity).where(DBEntity.id == source["rule_snapshot_id"])
        )
        engine = _make_replay_engine(session)
        request = _replay_request(
            source_run_id=source["run_id"],
            pinning_mode="honor_original",
        )
        with pytest.raises(ReplayRefusalError) as exc:
            await engine.reconstruct(request)
        await session.commit()
    assert exc.value.refusal_code == "rule_snapshot_unresolvable"


async def test_refresh_current_uses_current_rule_snapshot(session_factory) -> None:
    current_rule = None
    async with session_factory() as session:
        source = await _seed_completed_source_run(session)
        current_rule = await RuleSnapshotRepo(session).insert_if_absent(
            _rule_snapshot_body(source_ref="methodology/v18")
        )
        planner = _make_planner(session)
        engine = ReplayEngine(
            session,
            graph_engine=GraphEngine(session),
            planner=planner,
        )
        request = _replay_request(
            source_run_id=source["run_id"],
            pinning_mode="refresh_current",
        )
        with patch.object(planner, "plan", wraps=planner.plan) as plan_mock:
            await engine.reconstruct(
                request,
                current_rule_snapshot_id=current_rule.id,
                current_partial_fidelity_snapshot_id=source[
                    "partial_fidelity_snapshot_id"
                ],
                current_capability_snapshot_id=source["capability_snapshot_id"],
            )
            await session.commit()
            assert plan_mock.await_args.kwargs["rule_snapshot_id"] == current_rule.id


async def test_refresh_current_missing_rule_id_refuses(session_factory) -> None:
    async with session_factory() as session:
        source = await _seed_completed_source_run(session)
        engine = _make_replay_engine(session)
        request = _replay_request(
            source_run_id=source["run_id"],
            pinning_mode="refresh_current",
        )
        with pytest.raises(ReplayRefusalError) as exc:
            await engine.reconstruct(
                request,
                current_partial_fidelity_snapshot_id=source[
                    "partial_fidelity_snapshot_id"
                ],
                current_capability_snapshot_id=source["capability_snapshot_id"],
            )
        await session.commit()
    assert exc.value.refusal_code == "rule_snapshot_unresolvable"


async def test_per_dimension_override_refresh_rules(session_factory) -> None:
    async with session_factory() as session:
        source = await _seed_completed_source_run(session)
        current_rule = await RuleSnapshotRepo(session).insert_if_absent(
            _rule_snapshot_body(source_ref="override/v1")
        )
        request = _replay_request(
            source_run_id=source["run_id"],
            pinning_mode="honor_original",
            rules_policy="refresh_current",
        )
        policy = EffectivePinningPolicy.from_request(request)
        assert policy.rules == "refresh_current"
        assert policy.capability == "honor_snapshot"
        planner = _make_planner(session)
        engine = ReplayEngine(
            session,
            graph_engine=GraphEngine(session),
            planner=planner,
        )
        with patch.object(planner, "plan", wraps=planner.plan) as plan_mock:
            await engine.reconstruct(
                request,
                current_rule_snapshot_id=current_rule.id,
            )
            await session.commit()
            assert plan_mock.await_args.kwargs["rule_snapshot_id"] == current_rule.id


async def test_capability_refresh_current_none_auto_snapshots(session_factory) -> None:
    async with session_factory() as session:
        source = await _seed_completed_source_run(session)
        planner = _make_planner(session)
        engine = ReplayEngine(
            session,
            graph_engine=GraphEngine(session),
            planner=planner,
        )
        request = _replay_request(
            source_run_id=source["run_id"],
            pinning_mode="refresh_current",
        )
        with patch.object(planner, "plan", wraps=planner.plan) as plan_mock:
            await engine.reconstruct(
                request,
                current_rule_snapshot_id=source["rule_snapshot_id"],
                current_partial_fidelity_snapshot_id=source[
                    "partial_fidelity_snapshot_id"
                ],
                current_capability_snapshot_id=None,
            )
            await session.commit()
            assert plan_mock.await_args.kwargs["capability_snapshot_id"] is None


# ── Remediation entry points ──────────────────────────────────────────────────


async def test_new_attempt_same_plan_skips_planner(session_factory) -> None:
    async with session_factory() as session:
        source = await _seed_completed_source_run(session)
        planner = _make_planner(session)
        planner.plan = AsyncMock(wraps=planner.plan)
        engine = ReplayEngine(
            session,
            graph_engine=GraphEngine(session),
            planner=planner,
        )
        request = _replay_request(
            kind="remediation",
            source_run_id=source["run_id"],
            remediation_entry="new_attempt_same_plan",
        )
        lifecycle = await engine.reconstruct(request)
        await session.commit()
        planner.plan.assert_not_called()
    assert lifecycle.current_stage == "execution"
    assert lifecycle.plan_id == source["plan_id"]


async def test_replan_same_intent_invokes_planner(session_factory) -> None:
    async with session_factory() as session:
        source = await _seed_completed_source_run(session)
        planner = _make_planner(session)
        engine = ReplayEngine(
            session,
            graph_engine=GraphEngine(session),
            planner=planner,
        )
        request = _replay_request(
            kind="remediation",
            source_run_id=source["run_id"],
            remediation_entry="replan_same_intent",
        )
        with patch.object(planner, "plan", wraps=planner.plan) as plan_mock:
            lifecycle = await engine.reconstruct(request)
            await session.commit()
            plan_mock.assert_awaited_once()
    assert lifecycle.current_stage == "execution"
    assert lifecycle.plan_id is not None


async def test_replan_infeasible_stays_at_routing(session_factory) -> None:
    async with session_factory() as session:
        source = await _seed_completed_source_run(session)
        empty = await CapabilitySnapshotRepo(session).insert_if_absent(
            {"snapshots": []}
        )
        engine = _make_replay_engine(session)
        request = _replay_request(
            source_run_id=source["run_id"],
            pinning_mode="refresh_current",
        )
        lifecycle = await engine.reconstruct(
            request,
            current_rule_snapshot_id=source["rule_snapshot_id"],
            current_partial_fidelity_snapshot_id=source[
                "partial_fidelity_snapshot_id"
            ],
            current_capability_snapshot_id=empty.id,
        )
        await session.commit()
    assert lifecycle.current_stage == "routing"


async def test_replan_amended_intent_valid_lineage(session_factory) -> None:
    async with session_factory() as session:
        source = await _seed_completed_source_run(session)
        amended = await LockedIntentRepo(session).insert_if_absent(
            _locked_intent_body(
                success_criteria=[
                    {
                        "criterion_id": "motion_arc",
                        "statement": "amended reach",
                        "measurement_spec": {"method": "temporal_ioU"},
                        "tolerances": {"min": 0.8},
                    }
                ],
                derived_from=str(source["intent_id"]),
            )
        )
        engine = _make_replay_engine(session)
        request = _replay_request(
            kind="remediation",
            source_run_id=source["run_id"],
            remediation_entry="replan_amended_intent",
        )
        lifecycle = await engine.reconstruct(
            request, amended_intent_id=amended.id
        )
        await session.commit()
    assert lifecycle.current_stage == "execution"
    assert lifecycle.intent_id == amended.id


async def test_replan_amended_intent_bad_lineage(session_factory) -> None:
    async with session_factory() as session:
        source = await _seed_completed_source_run(session)
        amended = await LockedIntentRepo(session).insert_if_absent(
            _locked_intent_body(derived_from=str(uuid.uuid4()))
        )
        engine = _make_replay_engine(session)
        request = _replay_request(
            kind="remediation",
            source_run_id=source["run_id"],
            remediation_entry="replan_amended_intent",
        )
        with pytest.raises(AmendedIntentLineageError):
            await engine.reconstruct(request, amended_intent_id=amended.id)


# ── Run-lineage edges ─────────────────────────────────────────────────────────


async def test_lineage_replays_run(session_factory) -> None:
    async with session_factory() as session:
        source = await _seed_completed_source_run(session)
        engine = _make_replay_engine(session)
        request = _replay_request(source_run_id=source["run_id"])
        lifecycle = await engine.reconstruct(request)
        await session.commit()
        new_run_id = lifecycle.run_id

    async with session_factory() as session:
        edges = await RelationshipRepo(session).get_outgoing(
            new_run_id, RUN_LINEAGE_REL_KEYS["replays_run"]
        )
        assert len(edges) == 1
        assert edges[0].target_id == source["run_id"]


@pytest.mark.parametrize(
    "remediation_entry",
    ["new_attempt_same_plan", "replan_same_intent"],
)
async def test_lineage_remediates_run(
    session_factory, remediation_entry: str
) -> None:
    async with session_factory() as session:
        source = await _seed_completed_source_run(session)
        engine = _make_replay_engine(session)
        request = _replay_request(
            kind="remediation",
            source_run_id=source["run_id"],
            remediation_entry=remediation_entry,
        )
        lifecycle = await engine.reconstruct(request)
        await session.commit()
        new_run_id = lifecycle.run_id

    async with session_factory() as session:
        edges = await RelationshipRepo(session).get_outgoing(
            new_run_id, RUN_LINEAGE_REL_KEYS["remediates_run"]
        )
        assert len(edges) == 1


async def test_lineage_amends_run(session_factory) -> None:
    async with session_factory() as session:
        source = await _seed_completed_source_run(session)
        amended = await LockedIntentRepo(session).insert_if_absent(
            _locked_intent_body(derived_from=str(source["intent_id"]))
        )
        engine = _make_replay_engine(session)
        request = _replay_request(
            kind="remediation",
            source_run_id=source["run_id"],
            remediation_entry="replan_amended_intent",
        )
        lifecycle = await engine.reconstruct(
            request, amended_intent_id=amended.id
        )
        await session.commit()
        new_run_id = lifecycle.run_id

    async with session_factory() as session:
        edges = await RelationshipRepo(session).get_outgoing(
            new_run_id, RUN_LINEAGE_REL_KEYS["amends_run"]
        )
        assert len(edges) == 1


# ── Events ────────────────────────────────────────────────────────────────────


async def test_successful_replay_event_sequence(session_factory) -> None:
    async with session_factory() as session:
        source = await _seed_completed_source_run(session)
        engine = _make_replay_engine(session)
        request = _replay_request(source_run_id=source["run_id"])
        await engine.reconstruct(request)
        await session.commit()

    async with session_factory() as session:
        types = [e.event_type for e in await _replay_events(session)]
        assert types == [
            "replay_initiated",
            "replay_new_run_created",
            "replay_planner_invoked",
        ]


async def test_pre_validation_refusal_event_sequence(session_factory) -> None:
    async with session_factory() as session:
        run = await PipelineRunRepo(session).insert_if_absent(
            {"run_kind": "original", "intent_id": str(uuid.uuid4())}
        )
        await GraphEngine(session).create_run(run_id=run.id, shot_id=uuid.uuid4())
        engine = _make_replay_engine(session)
        request = _replay_request(source_run_id=run.id)
        with pytest.raises(ReplayRefusalError):
            await engine.reconstruct(request)
        await session.commit()

    async with session_factory() as session:
        types = [e.event_type for e in await _replay_events(session)]
        assert types == ["replay_initiated", "replay_refusal_pre_validation"]


# ── Caller owns transaction ───────────────────────────────────────────────────


async def test_reconstruct_not_visible_before_commit(session_factory) -> None:
    new_run_id = None
    async with session_factory() as session:
        source = await _seed_completed_source_run(session)
        engine = _make_replay_engine(session)
        request = _replay_request(source_run_id=source["run_id"])
        lifecycle = await engine.reconstruct(request)
        new_run_id = lifecycle.run_id

    async with session_factory() as session:
        row = await OrchestrationLifecycleStateRepo(session).get_by_run_id(
            new_run_id
        )
        assert row is None


# ── Planner pinning extension ─────────────────────────────────────────────────


async def test_pinning_backend_revision_unreachable(session_factory) -> None:
    async with session_factory() as session:
        source = await _seed_completed_source_run(
            session,
            capability={
                "snapshots": [
                    {
                        "backend_identity_triple": {
                            "surface": "test",
                            "path": "backend",
                            "revision": "v1",
                        },
                        "capabilities_opaque": {
                            "first_frame_guarantee": True,
                            "acceptance_score": 0.9,
                            "estimated_cost": 1.0,
                        },
                    }
                ]
            },
        )
        new_cap = await CapabilitySnapshotRepo(session).insert_if_absent(
            {
                "snapshots": [
                    {
                        "backend_identity_triple": {
                            "surface": "test",
                            "path": "backend",
                            "revision": "v2",
                        },
                        "capabilities_opaque": {
                            "first_frame_guarantee": True,
                            "acceptance_score": 0.9,
                            "estimated_cost": 1.0,
                        },
                    }
                ]
            }
        )
        engine = _make_replay_engine(session)
        request = _replay_request(
            source_run_id=source["run_id"],
            pinning_mode="honor_original",
            capability_policy="refresh_current",
        )
        lifecycle = await engine.reconstruct(
            request,
            current_capability_snapshot_id=new_cap.id,
        )
        await session.commit()
    assert lifecycle.current_stage == "routing"


async def test_planner_identity_honor_pinning_expired_at_source(session_factory) -> None:
    identity_id = uuid.uuid4()
    source_time = datetime.now(timezone.utc) - timedelta(days=10)
    trained = InMemoryTrainedIdentityRegistry()
    trained.register(
        TrainedIdentityRecord(
            identity_id=identity_id,
            backend_id="test.backend",
            validity_window=(
                datetime.now(timezone.utc) - timedelta(days=5),
                None,
            ),
            reuse_constraints={},
        )
    )
    async with session_factory() as session:
        from forge_bridge.store.orch_inputs_catalog_repo import InputsCatalogRepo

        intent = await LockedIntentRepo(session).insert_if_absent(_locked_intent_body())
        rule = await RuleSnapshotRepo(session).insert_if_absent(_rule_snapshot_body())
        partial = await PartialFidelitySnapshotRepo(session).insert_if_absent(
            _partial_fidelity_body()
        )
        cap = await CapabilitySnapshotRepo(session).insert_if_absent(_capability_body())
        catalog = await InputsCatalogRepo(session).insert_if_absent(
            {"inputs": [{"trained_identity_id": str(identity_id)}], "role_assignments": {}}
        )
        run = await PipelineRunRepo(session).insert_if_absent(
            {"run_kind": "original", "intent_id": str(intent.id)}
        )
        ids = {
            "intent_id": intent.id,
            "rule_snapshot_id": rule.id,
            "partial_fidelity_snapshot_id": partial.id,
            "capability_snapshot_id": cap.id,
            "inputs_catalog_id": catalog.id,
            "run_id": run.id,
        }
        planner = _make_planner(session, trained=trained)
        policy = EffectivePinningPolicy(
            backend="refresh_current",
            rules="refresh_current",
            capability="refresh_current",
            partial_fidelity="refresh_current",
            identity="honor_pinning",
        )
        plan = await planner.plan(
            **_plan_kwargs(
                ids,
                pinning_policy=policy,
                source_authored_at=source_time,
            )
        )
        await session.commit()
    assert plan.refusal_code == "trained_identity_validity_expired"


async def test_planner_identity_refresh_current_valid_now(session_factory) -> None:
    identity_id = uuid.uuid4()
    source_time = datetime.now(timezone.utc) - timedelta(days=10)
    trained = InMemoryTrainedIdentityRegistry()
    trained.register(
        TrainedIdentityRecord(
            identity_id=identity_id,
            backend_id="test.backend",
            validity_window=(
                datetime.now(timezone.utc) - timedelta(days=5),
                None,
            ),
            reuse_constraints={},
        )
    )
    async with session_factory() as session:
        from forge_bridge.store.orch_inputs_catalog_repo import InputsCatalogRepo

        intent = await LockedIntentRepo(session).insert_if_absent(_locked_intent_body())
        rule = await RuleSnapshotRepo(session).insert_if_absent(_rule_snapshot_body())
        partial = await PartialFidelitySnapshotRepo(session).insert_if_absent(
            _partial_fidelity_body()
        )
        cap = await CapabilitySnapshotRepo(session).insert_if_absent(_capability_body())
        catalog = await InputsCatalogRepo(session).insert_if_absent(
            {"inputs": [{"trained_identity_id": str(identity_id)}], "role_assignments": {}}
        )
        run = await PipelineRunRepo(session).insert_if_absent(
            {"run_kind": "original", "intent_id": str(intent.id)}
        )
        ids = {
            "intent_id": intent.id,
            "rule_snapshot_id": rule.id,
            "partial_fidelity_snapshot_id": partial.id,
            "capability_snapshot_id": cap.id,
            "inputs_catalog_id": catalog.id,
            "run_id": run.id,
        }
        planner = _make_planner(session, trained=trained)
        policy = EffectivePinningPolicy(
            backend="refresh_current",
            rules="refresh_current",
            capability="refresh_current",
            partial_fidelity="refresh_current",
            identity="refresh_current",
        )
        plan = await planner.plan(
            **_plan_kwargs(
                ids,
                pinning_policy=policy,
                source_authored_at=source_time,
            )
        )
        await session.commit()
    assert plan.feasibility_verdict == "feasible"
    assert plan.refusal_code is None
