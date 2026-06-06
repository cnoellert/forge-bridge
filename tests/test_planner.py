"""Tests for Planner six-pass model (Phase 4B Step 9)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from forge_bridge.orchestration.errors import PlannerRefusalError
from forge_bridge.orchestration.identity_registries import (
    InMemoryPlatformUUIDRegistry,
    InMemoryTrainedIdentityRegistry,
    TrainedIdentityRecord,
)
from forge_bridge.orchestration.lineage_graph import InMemoryLineageGraph
from forge_bridge.orchestration.planner import REPLAY_REFUSAL_CODES, Planner
from forge_bridge.orchestration.registration import ToolRegistration, ToolRegistry
from forge_bridge.store.orch_capability_snapshot_repo import CapabilitySnapshotRepo
from forge_bridge.store.orch_execution_plan_repo import ExecutionPlanRepo
from forge_bridge.store.orch_inputs_catalog_repo import InputsCatalogRepo
from forge_bridge.store.orch_locked_intent_repo import LockedIntentRepo
from forge_bridge.store.orch_partial_fidelity_snapshot_repo import (
    PartialFidelitySnapshotRepo,
)
from forge_bridge.store.orch_pipeline_run_repo import PipelineRunRepo
from forge_bridge.store.orch_rule_snapshot_repo import RuleSnapshotRepo
from forge_bridge.store.orchestration_compromise_ledger_repo import (
    OrchestrationCompromiseLedgerRepo,
)


class _GenDriver:
    backend_id = "test.backend"

    async def poll(self, artifact):
        return None


def _locked_intent_body(**overrides) -> dict:
    body = {
        "source_read": {"shot_id": "shot-001"},
        "change_manifest": [],
        "success_criteria": [
            {
                "criterion_id": "motion_arc",
                "statement": "hand reaches clock face",
                "measurement_spec": {"method": "temporal_ioU"},
                "tolerances": {"min": 0.7},
            }
        ],
        "allowed_compromises": [{"criterion_id": "motion_arc", "budget": 0.5}],
        "hard_constraints": [],
        "escalation_threshold": 0.9,
        "deliverable_spec": {
            "medium": "video",
            "requires_first_frame": True,
            "acceptance_bar": 0.7,
        },
    }
    body.update(overrides)
    return body


def _rule_snapshot_body(**overrides) -> dict:
    body = {
        "rules": [
            {
                "rule_id": "rule-4",
                "enforcement_phases": ["planning-time"],
                "authoritative_phase": "planning-time",
            },
            {
                "rule_id": "rule-5",
                "enforcement_phases": ["planning-time"],
                "authoritative_phase": "planning-time",
            },
            {
                "rule_id": "rule-10",
                "enforcement_phases": ["planning-time"],
                "authoritative_phase": "planning-time",
            },
            {
                "rule_id": "rule-14",
                "enforcement_phases": ["planning-time"],
                "authoritative_phase": "planning-time",
            },
        ],
        "source_ref": "methodology/v17",
        "snapshot_timestamp": "2026-05-28T12:00:00Z",
    }
    body.update(overrides)
    return body


def _partial_fidelity_body(**overrides) -> dict:
    body = {
        "models": [
            {
                "backend_identity_triple": {
                    "surface": "test",
                    "path": "backend",
                },
                "dimensions": [{"axis": "dynamic_range", "scalar": 0.2}],
            }
        ]
    }
    body.update(overrides)
    return body


def _capability_body(**overrides) -> dict:
    body = {
        "snapshots": [
            {
                "backend_identity_triple": {
                    "surface": "test",
                    "path": "backend",
                    "revision": "v1",
                },
                "declaration_hash": "decl-1",
                "capabilities_opaque": {
                    "first_frame_guarantee": True,
                    "identity_lock_support": True,
                    "upload_support": True,
                    "acceptance_score": 0.9,
                    "estimated_cost": 1.0,
                },
            }
        ]
    }
    body.update(overrides)
    return body


def _inputs_catalog_body(**overrides) -> dict:
    body = {"inputs": [], "role_assignments": {}}
    body.update(overrides)
    return body


def _generation_tool(**caps) -> ToolRegistration:
    capabilities = {
        "backend_identity_triple": {
            "surface": "test",
            "path": "backend",
            "revision": "v1",
        },
        "first_frame_guarantee": True,
        "identity_lock_support": True,
        "upload_support": True,
        "acceptance_score": 0.9,
        "estimated_cost": 1.0,
        **caps,
    }
    return ToolRegistration(
        tool_id="forge_generators.test.backend",
        family="generation",
        payload_family="generation_v1",
        schema={"type": "object"},
        capabilities=capabilities,
    )


def _make_planner(
    session,
    *,
    tools: ToolRegistry | None = None,
    lineage: InMemoryLineageGraph | None = None,
    platform: InMemoryPlatformUUIDRegistry | None = None,
    trained: InMemoryTrainedIdentityRegistry | None = None,
) -> Planner:
    return Planner(
        session,
        tool_registry=tools or ToolRegistry(),
        platform_uuid_registry=platform or InMemoryPlatformUUIDRegistry(),
        trained_identity_registry=trained or InMemoryTrainedIdentityRegistry(),
        lineage_graph=lineage or InMemoryLineageGraph(),
    )


def _plan_kwargs(ids: dict, **extra) -> dict:
    kwargs = {
        "intent_id": ids["intent_id"],
        "run_id": ids["run_id"],
        "rule_snapshot_id": ids["rule_snapshot_id"],
        "partial_fidelity_snapshot_id": ids["partial_fidelity_snapshot_id"],
    }
    if ids.get("capability_snapshot_id") is not None:
        kwargs["capability_snapshot_id"] = ids["capability_snapshot_id"]
    if ids.get("inputs_catalog_id") is not None:
        kwargs["inputs_catalog_id"] = ids["inputs_catalog_id"]
    kwargs.update(extra)
    return kwargs


async def _seed_base(session, **overrides):
    intent = await LockedIntentRepo(session).insert_if_absent(
        _locked_intent_body(**overrides.pop("intent", {}))
    )
    rule = await RuleSnapshotRepo(session).insert_if_absent(
        _rule_snapshot_body(**overrides.pop("rule", {}))
    )
    partial = await PartialFidelitySnapshotRepo(session).insert_if_absent(
        _partial_fidelity_body(**overrides.pop("partial", {}))
    )
    run = await PipelineRunRepo(session).insert_if_absent(
        {"run_kind": "original", "intent_id": str(intent.id)}
    )
    capability = None
    if "capability" in overrides:
        capability = await CapabilitySnapshotRepo(session).insert_if_absent(
            _capability_body(**overrides.pop("capability", {}))
        )
    catalog = None
    if "inputs" in overrides:
        catalog = await InputsCatalogRepo(session).insert_if_absent(
            _inputs_catalog_body(**overrides.pop("inputs", {}))
        )
    return {
        "intent_id": intent.id,
        "rule_snapshot_id": rule.id,
        "partial_fidelity_snapshot_id": partial.id,
        "run_id": run.id,
        "capability_snapshot_id": capability.id if capability else None,
        "inputs_catalog_id": catalog.id if catalog else None,
    }


# ── Pass 1 refusals ───────────────────────────────────────────────────────────


async def test_plan_locked_intent_unresolvable(session_factory) -> None:
    async with session_factory() as session:
        ids = await _seed_base(session)
        planner = _make_planner(session)
        plan = await planner.plan(
            intent_id=uuid.uuid4(),
            run_id=ids["run_id"],
            rule_snapshot_id=ids["rule_snapshot_id"],
            partial_fidelity_snapshot_id=ids["partial_fidelity_snapshot_id"],
        )
        await session.commit()
    assert plan.feasibility_verdict == "infeasible"
    assert plan.refusal_code == "locked_intent_unresolvable"


async def test_plan_intent_missing_measurement_spec(session_factory) -> None:
    async with session_factory() as session:
        ids = await _seed_base(
            session,
            intent={
                "success_criteria": [{"criterion_id": "x", "statement": "y"}],
            },
        )
        planner = _make_planner(session)
        plan = await planner.plan(**_plan_kwargs(ids))
        await session.commit()
    assert plan.refusal_code == "locked_intent_unresolvable"


async def test_plan_snapshot_unresolvable_rule(session_factory) -> None:
    async with session_factory() as session:
        ids = await _seed_base(session)
        planner = _make_planner(session)
        plan = await planner.plan(
            intent_id=ids["intent_id"],
            run_id=ids["run_id"],
            rule_snapshot_id=uuid.uuid4(),
            partial_fidelity_snapshot_id=ids["partial_fidelity_snapshot_id"],
        )
        await session.commit()
    assert plan.refusal_code == "snapshot_unresolvable"


async def test_plan_snapshot_unresolvable_partial(session_factory) -> None:
    async with session_factory() as session:
        ids = await _seed_base(session)
        planner = _make_planner(session)
        plan = await planner.plan(
            intent_id=ids["intent_id"],
            run_id=ids["run_id"],
            rule_snapshot_id=ids["rule_snapshot_id"],
            partial_fidelity_snapshot_id=uuid.uuid4(),
        )
        await session.commit()
    assert plan.refusal_code == "snapshot_unresolvable"


async def test_plan_inputs_missing(session_factory) -> None:
    async with session_factory() as session:
        ids = await _seed_base(session, capability={})
        planner = _make_planner(session)
        plan = await planner.plan(
            **_plan_kwargs(ids, inputs_catalog_id=uuid.uuid4()),
        )
        await session.commit()
    assert plan.refusal_code == "inputs_missing"


async def test_plan_capability_snapshot_unresolvable(session_factory) -> None:
    async with session_factory() as session:
        ids = await _seed_base(session)
        planner = _make_planner(session)
        plan = await planner.plan(
            intent_id=ids["intent_id"],
            run_id=ids["run_id"],
            rule_snapshot_id=ids["rule_snapshot_id"],
            partial_fidelity_snapshot_id=ids["partial_fidelity_snapshot_id"],
            capability_snapshot_id=uuid.uuid4(),
        )
        await session.commit()
    assert plan.refusal_code == "capability_snapshot_unresolvable"


async def test_plan_auto_creates_capability_snapshot(session_factory) -> None:
    tools = ToolRegistry()
    tools.register(
        _generation_tool(), sibling_name="forge_generators", handler=_GenDriver()
    )
    async with session_factory() as session:
        ids = await _seed_base(session)
        planner = _make_planner(session, tools=tools)
        plan = await planner.plan(
            intent_id=ids["intent_id"],
            run_id=ids["run_id"],
            rule_snapshot_id=ids["rule_snapshot_id"],
            partial_fidelity_snapshot_id=ids["partial_fidelity_snapshot_id"],
        )
        await session.commit()
        cap_id = plan.capability_snapshot_id
        assert cap_id is not None

    async with session_factory() as session:
        second = await _make_planner(session, tools=tools).plan(
            intent_id=ids["intent_id"],
            run_id=ids["run_id"],
            rule_snapshot_id=ids["rule_snapshot_id"],
            partial_fidelity_snapshot_id=ids["partial_fidelity_snapshot_id"],
        )
        await session.commit()
        assert second.capability_snapshot_id == cap_id


# ── Pass 2 refusals ───────────────────────────────────────────────────────────


async def test_plan_no_feasible_backend(session_factory) -> None:
    async with session_factory() as session:
        ids = await _seed_base(
            session,
            capability={
                "snapshots": [
                    {
                        "backend_identity_triple": {"surface": "test", "path": "x"},
                        "capabilities_opaque": {},
                    }
                ]
            },
        )
        planner = _make_planner(session)
        plan = await planner.plan(**_plan_kwargs(ids))
        await session.commit()
    assert plan.refusal_code == "no_feasible_backend"


async def test_plan_trained_identity_expired(session_factory) -> None:
    identity_id = uuid.uuid4()
    trained = InMemoryTrainedIdentityRegistry()
    trained.register(
        TrainedIdentityRecord(
            identity_id=identity_id,
            backend_id="test.backend",
            validity_window=(
                datetime.now(timezone.utc) - timedelta(days=10),
                datetime.now(timezone.utc) - timedelta(days=1),
            ),
            reuse_constraints={},
        )
    )
    async with session_factory() as session:
        ids = await _seed_base(
            session,
            capability={},
            inputs={
                "inputs": [
                    {
                        "trained_identity_id": str(identity_id),
                    }
                ]
            },
        )
        planner = _make_planner(session, trained=trained)
        plan = await planner.plan(**_plan_kwargs(ids))
        await session.commit()
    assert plan.refusal_code == "trained_identity_validity_expired"


async def test_plan_identity_reuse_forbidden(session_factory) -> None:
    identity_id = uuid.uuid4()
    shot_id = uuid.uuid4()
    trained = InMemoryTrainedIdentityRegistry()
    trained.register(
        TrainedIdentityRecord(
            identity_id=identity_id,
            backend_id="test.backend",
            validity_window=(datetime.now(timezone.utc) - timedelta(days=1), None),
            reuse_constraints={"allowed_shot_scopes": [str(uuid.uuid4())]},
        )
    )
    async with session_factory() as session:
        ids = await _seed_base(
            session,
            capability={},
            inputs={"inputs": [{"trained_identity_id": str(identity_id)}]},
        )
        planner = _make_planner(session, trained=trained)
        plan = await planner.plan(**_plan_kwargs(ids))
        await session.commit()
    assert plan.refusal_code == "identity_reuse_forbidden"


async def test_plan_external_upload_unavailable(session_factory) -> None:
    async with session_factory() as session:
        ids = await _seed_base(
            session,
            capability={
                "snapshots": [
                    {
                        "backend_identity_triple": {"surface": "test", "path": "backend"},
                        "capabilities_opaque": {
                            "first_frame_guarantee": True,
                            "upload_support": False,
                        },
                    }
                ]
            },
            inputs={
                "inputs": [
                    {
                        "needs_upload": True,
                        "content_sha256": "abc123",
                    }
                ]
            },
        )
        planner = _make_planner(session)
        plan = await planner.plan(**_plan_kwargs(ids))
        await session.commit()
    assert plan.refusal_code == "external_upload_unavailable"


# ── Pass 3 / 4 refusals ─────────────────────────────────────────────────────


async def test_plan_transform_unavailable(session_factory) -> None:
    async with session_factory() as session:
        ids = await _seed_base(
            session,
            capability={
                "snapshots": [
                    {
                        "backend_identity_triple": {"surface": "test", "path": "backend"},
                        "capabilities_opaque": {
                            "first_frame_guarantee": True,
                            "content_policy_real_person_classifier": True,
                        },
                    }
                ]
            },
            inputs={"inputs": [{"photoreal_motion_source": True}]},
        )
        planner = _make_planner(session)
        plan = await planner.plan(**_plan_kwargs(ids))
        await session.commit()
    assert plan.refusal_code == "transform_unavailable"


async def test_plan_transform_inserted_when_provider_exists(session_factory) -> None:
    tools = ToolRegistry()
    tools.register(
        ToolRegistration(
            tool_id="forge_vision.depth.estimate",
            family="perceptual",
            payload_family="perception_validation_v1",
            schema={},
            capabilities={},
        ),
        sibling_name="forge_vision",
    )
    async with session_factory() as session:
        ids = await _seed_base(
            session,
            capability={
                "snapshots": [
                    {
                        "backend_identity_triple": {"surface": "test", "path": "backend"},
                        "capabilities_opaque": {
                            "first_frame_guarantee": True,
                            "content_policy_real_person_classifier": True,
                            "acceptance_score": 0.8,
                            "estimated_cost": 1.0,
                        },
                    }
                ]
            },
            inputs={"inputs": [{"photoreal_motion_source": True}]},
        )
        planner = _make_planner(session, tools=tools)
        plan = await planner.plan(**_plan_kwargs(ids))
        await session.commit()
    assert plan.feasibility_verdict == "feasible"
    assert len(plan.transforms_inserted) == 1


async def test_plan_anchor_lineage_violation(session_factory) -> None:
    lineage = InMemoryLineageGraph(violate_anchor=True)
    async with session_factory() as session:
        ids = await _seed_base(session, capability={})
        planner = _make_planner(session, lineage=lineage)
        plan = await planner.plan(**_plan_kwargs(ids))
        await session.commit()
    assert plan.refusal_code == "anchor_lineage_violation"


async def test_plan_chain_depth_exceeded(session_factory) -> None:
    lineage = InMemoryLineageGraph(default_depth=10)
    async with session_factory() as session:
        ids = await _seed_base(
            session,
            capability={},
            intent={"hard_constraints": [{"chain_depth_cap": 2}]},
        )
        planner = _make_planner(session, lineage=lineage)
        plan = await planner.plan(**_plan_kwargs(ids))
        await session.commit()
    assert plan.refusal_code == "chain_depth_exceeded"


async def test_plan_aspect_integrity_violation(session_factory) -> None:
    async with session_factory() as session:
        ids = await _seed_base(
            session,
            capability={},
            intent={"deliverable_spec": {"medium": "video", "pillarbox_bake": True}},
        )
        planner = _make_planner(session)
        plan = await planner.plan(**_plan_kwargs(ids))
        await session.commit()
    assert plan.refusal_code == "aspect_integrity_violation"


# ── Pass 5 ranking ────────────────────────────────────────────────────────────


async def test_plan_ranks_cheaper_candidate(session_factory) -> None:
    async with session_factory() as session:
        ids = await _seed_base(
            session,
            capability={
                "snapshots": [
                    {
                        "backend_identity_triple": {"surface": "test", "path": "expensive"},
                        "capabilities_opaque": {
                            "first_frame_guarantee": True,
                            "acceptance_score": 0.8,
                            "estimated_cost": 5.0,
                        },
                    },
                    {
                        "backend_identity_triple": {"surface": "test", "path": "cheap"},
                        "capabilities_opaque": {
                            "first_frame_guarantee": True,
                            "acceptance_score": 0.8,
                            "estimated_cost": 1.0,
                        },
                    },
                ]
            },
            partial={
                "models": [
                    {
                        "backend_identity_triple": {"surface": "test", "path": "expensive"},
                        "dimensions": [{"axis": "a", "scalar": 0.1}],
                    },
                    {
                        "backend_identity_triple": {"surface": "test", "path": "cheap"},
                        "dimensions": [{"axis": "a", "scalar": 0.1}],
                    },
                ]
            },
        )
        planner = _make_planner(session)
        plan = await planner.plan(**_plan_kwargs(ids))
        await session.commit()
    assert plan.feasibility_verdict == "feasible"
    assert plan.backend_assignments["generate_video_from_image"] == "test.cheap"


async def test_plan_ranks_shorter_chain_at_equal_cost(session_factory) -> None:
    async with session_factory() as session:
        ids = await _seed_base(
            session,
            capability={
                "snapshots": [
                    {
                        "backend_identity_triple": {"surface": "test", "path": "a"},
                        "capabilities_opaque": {
                            "first_frame_guarantee": True,
                            "acceptance_score": 0.8,
                            "estimated_cost": 1.0,
                            "chain_depth": 1,
                        },
                    },
                    {
                        "backend_identity_triple": {"surface": "test", "path": "b"},
                        "capabilities_opaque": {
                            "first_frame_guarantee": True,
                            "acceptance_score": 0.8,
                            "estimated_cost": 1.0,
                            "chain_depth": 5,
                        },
                    },
                ]
            },
            partial={
                "models": [
                    {
                        "backend_identity_triple": {"surface": "test", "path": "a"},
                        "dimensions": [{"axis": "a", "scalar": 0.1}],
                    },
                    {
                        "backend_identity_triple": {"surface": "test", "path": "b"},
                        "dimensions": [{"axis": "a", "scalar": 0.1}],
                    },
                ]
            },
        )
        planner = _make_planner(session)
        plan = await planner.plan(**_plan_kwargs(ids))
        await session.commit()
    assert plan.backend_assignments["generate_video_from_image"] == "test.a"


# ── Pass 6 refusals ───────────────────────────────────────────────────────────


async def test_plan_compromise_budget_exceeded(session_factory) -> None:
    async with session_factory() as session:
        ids = await _seed_base(
            session,
            capability={},
            partial={
                "models": [
                    {
                        "backend_identity_triple": {"surface": "test", "path": "backend"},
                        "dimensions": [{"axis": "dynamic_range", "scalar": 0.95}],
                    }
                ]
            },
            intent={
                "allowed_compromises": [{"criterion_id": "motion_arc", "budget": 0.1}],
                "escalation_threshold": 0.5,
            },
        )
        planner = _make_planner(session)
        plan = await planner.plan(**_plan_kwargs(ids))
        await session.commit()
    assert plan.refusal_code == "compromise_budget_exceeded"


async def test_plan_cumulative_threshold_exceeded(session_factory) -> None:
    async with session_factory() as session:
        ids = await _seed_base(session, capability={})
        ledger = OrchestrationCompromiseLedgerRepo(session)
        await ledger.insert_audit_actual(
            intent_id=ids["intent_id"],
            run_id=ids["run_id"],
            artifact_id=uuid.uuid4(),
            criterion_id="motion_arc",
            dimension="dynamic_range",
            magnitude={"scalar": 0.85},
        )
        planner = _make_planner(session)
        plan = await planner.plan(**_plan_kwargs(ids))
        await session.commit()
    assert plan.refusal_code == "cumulative_threshold_exceeded"


# ── Happy path + persistence ──────────────────────────────────────────────────


async def test_plan_happy_path_feasible(session_factory) -> None:
    async with session_factory() as session:
        ids = await _seed_base(session, capability={})
        planner = _make_planner(session)
        plan = await planner.plan(**_plan_kwargs(ids))
        await session.commit()
    assert plan.feasibility_verdict == "feasible"
    assert plan.content_hash is not None
    assert plan.operator_sequence
    assert plan.refusal_code is None


async def test_plan_idempotent_same_inputs(session_factory) -> None:
    async with session_factory() as session:
        ids = await _seed_base(session, capability={})
        planner = _make_planner(session)
        first = await planner.plan(**_plan_kwargs(ids))
        second = await planner.plan(**_plan_kwargs(ids))
        await session.commit()
    assert first.id == second.id
    assert first.content_hash == second.content_hash


async def test_plan_infeasible_persisted_with_empty_sequence(session_factory) -> None:
    async with session_factory() as session:
        ids = await _seed_base(session, capability={"snapshots": []})
        planner = _make_planner(session)
        plan = await planner.plan(**_plan_kwargs(ids))
        await session.commit()
    assert plan.feasibility_verdict == "infeasible"
    assert plan.operator_sequence == []
    assert plan.refusal_code == "no_feasible_backend"
    assert plan.feasibility_explanation


async def test_plan_not_visible_before_commit(session_factory) -> None:
    plan_id = None
    async with session_factory() as session:
        ids = await _seed_base(session, capability={})
        planner = _make_planner(session)
        plan = await planner.plan(**_plan_kwargs(ids))
        plan_id = plan.id

    async with session_factory() as session:
        assert await ExecutionPlanRepo(session).get_by_id(plan_id) is None

    async with session_factory() as session:
        ids = await _seed_base(session, capability={})
        planner = _make_planner(session)
        plan = await planner.plan(**_plan_kwargs(ids))
        await session.commit()
        plan_id = plan.id

    async with session_factory() as session:
        assert await ExecutionPlanRepo(session).get_by_id(plan_id) is not None


# ── Replay refusal codes ──────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "code",
    sorted(REPLAY_REFUSAL_CODES),
)
async def test_replay_refusal_codes_persist(session_factory, code: str) -> None:
    async with session_factory() as session:
        ids = await _seed_base(session, capability={})
        planner = _make_planner(session)
        from forge_bridge.orchestration.planner import PlanningContext

        planning_ctx = PlanningContext(
            intent_id=ids["intent_id"],
            run_id=ids["run_id"],
            rule_snapshot_id=ids["rule_snapshot_id"],
            partial_fidelity_snapshot_id=ids["partial_fidelity_snapshot_id"],
            capability_snapshot_id=ids["capability_snapshot_id"],
        )
        plan = await planner.persist_infeasible_plan(
            planning_ctx,
            code,
            f"replay test for {code}",
        )
        await session.commit()
    assert plan.refusal_code == code
    assert plan.feasibility_verdict == "infeasible"


async def test_validate_replay_spec_trace_missing(session_factory) -> None:
    async with session_factory() as session:
        ids = await _seed_base(session, capability={})
        planner = _make_planner(session)
        with pytest.raises(PlannerRefusalError) as exc:
            await planner.validate_replay_prerequisites(
                intent_id=ids["intent_id"],
                run_id=ids["run_id"],
                rule_snapshot_id=ids["rule_snapshot_id"],
                partial_fidelity_snapshot_id=ids["partial_fidelity_snapshot_id"],
                capability_snapshot_id=ids["capability_snapshot_id"],
                spec_convergence_trace_id=uuid.uuid4(),
            )
        assert exc.value.refusal_code == "spec_convergence_trace_missing"


async def test_validate_replay_backend_revision_unreachable(session_factory) -> None:
    async with session_factory() as session:
        ids = await _seed_base(session, capability={})
        planner = _make_planner(session)
        with pytest.raises(PlannerRefusalError) as exc:
            await planner.validate_replay_prerequisites(
                intent_id=ids["intent_id"],
                run_id=ids["run_id"],
                rule_snapshot_id=ids["rule_snapshot_id"],
                partial_fidelity_snapshot_id=ids["partial_fidelity_snapshot_id"],
                capability_snapshot_id=ids["capability_snapshot_id"],
                required_backend_revision="missing-revision",
            )
        assert exc.value.refusal_code == "backend_revision_unreachable"
