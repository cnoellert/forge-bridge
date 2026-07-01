"""Phase 7 V1 — generation lifecycle round-trip."""

from __future__ import annotations

import sys
import types
import uuid
from datetime import datetime, timezone
from typing import Any

from forge_contracts import CapabilityDeclaration, CapabilityRegistration
from forge_contracts.references import ArtifactRef
from sqlalchemy import select

from forge_bridge.orchestration import (
    DispatchResult,
    DriverPollResult,
    GenerationDriverRegistry,
    GenerationPoller,
    InMemoryLineageGraph,
    InvocationEnvelope,
    Planner,
    ToolRegistry,
    dispatch_envelope,
    dispatch_plan,
    register_all_siblings,
    resolve_backend_id,
    resolve_siblings,
)
from forge_bridge.orchestration.drivers import (
    DriverSubmitResult,
    backend_id_from_identity_triple,
)
from forge_bridge.store.models import DBEntity
from forge_bridge.store.orch_execution_plan_repo import ExecutionPlanRepo
from forge_bridge.store.orch_generation_artifact_repo import GenerationArtifactRepo
from forge_bridge.store.orch_inputs_catalog_repo import InputsCatalogRepo
from forge_bridge.store.orch_locked_intent_repo import LockedIntentRepo
from forge_bridge.store.orch_partial_fidelity_snapshot_repo import (
    PartialFidelitySnapshotRepo,
)
from forge_bridge.store.orch_pipeline_run_repo import PipelineRunRepo
from forge_bridge.store.orch_rule_snapshot_repo import RuleSnapshotRepo

_TRIPLE = {
    "surface": "test",
    "path": "faithful_backend",
    "revision": "v1",
}
_BACKEND_ID = "test.faithful_backend"


class FaithfulLifecycleDriver:
    backend_id = _BACKEND_ID
    backend_identity_triple = _TRIPLE

    def __init__(self) -> None:
        self.submissions: list[InvocationEnvelope] = []
        self.request_ids: list[str] = []
        self.polled_request_ids: list[str] = []

    async def submit(self, invocation: InvocationEnvelope) -> DriverSubmitResult:
        self.submissions.append(invocation)
        request_id = f"req-{len(self.submissions)}"
        self.request_ids.append(request_id)
        return DriverSubmitResult(
            request_id=request_id,
            submitted_at=datetime(2026, 6, 5, 12, 0, tzinfo=timezone.utc),
            raw_response_summary={"remote_state": "accepted"},
        )

    async def poll(self, artifact) -> DriverPollResult:
        request_id = artifact.execution_provenance["request_id"]
        self.polled_request_ids.append(request_id)
        return DriverPollResult(
            next_state="complete",
            polling_event={
                "backend_status": "complete",
                "request_id": request_id,
            },
            terminal_provenance={
                "backend_identity_triple": self.backend_identity_triple,
                "request_id": request_id,
                "terminal_status": "complete",
            },
        )


def _install_module(name: str, register_bridge_adapters) -> str:
    module = types.ModuleType(name)
    module.register_bridge_adapters = register_bridge_adapters
    sys.modules[name] = module
    return f"{name}:register_bridge_adapters"


def _capability(driver: FaithfulLifecycleDriver) -> CapabilityRegistration:
    return CapabilityRegistration(
        declaration=CapabilityDeclaration(
            capability_id="forge_generators.test.faithful_backend",
            family="generation",
            owner="test-sibling",
            payload_family="generation_v1",
            input_schema={"type": "object"},
            metadata={
                "backend_identity_triple": _TRIPLE,
                "first_frame_guarantee": True,
                "identity_lock_support": True,
                "upload_support": True,
                "acceptance_score": 0.95,
                "estimated_cost": 1.0,
            },
        ),
        handler=driver,
    )


async def _seed_base(session) -> dict[str, uuid.UUID]:
    intent = await LockedIntentRepo(session).insert_if_absent(
        {
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
    )
    rule = await RuleSnapshotRepo(session).insert_if_absent(
        {
            "rules": [],
            "source_ref": "phase7-test",
            "snapshot_timestamp": "2026-06-05T12:00:00Z",
        }
    )
    partial = await PartialFidelitySnapshotRepo(session).insert_if_absent(
        {
            "models": [
                {
                    "backend_identity_triple": _TRIPLE,
                    "dimensions": [{"axis": "motion", "scalar": 0.1}],
                }
            ]
        }
    )
    run = await PipelineRunRepo(session).insert_if_absent(
        {"run_kind": "original", "intent_id": str(intent.id)}
    )
    catalog = await InputsCatalogRepo(session).insert_if_absent(
        {"inputs": [], "role_assignments": {}}
    )
    return {
        "intent_id": intent.id,
        "rule_snapshot_id": rule.id,
        "partial_fidelity_snapshot_id": partial.id,
        "run_id": run.id,
        "inputs_catalog_id": catalog.id,
    }


def _plan_kwargs(ids: dict[str, uuid.UUID]) -> dict[str, uuid.UUID]:
    return {
        "intent_id": ids["intent_id"],
        "run_id": ids["run_id"],
        "rule_snapshot_id": ids["rule_snapshot_id"],
        "partial_fidelity_snapshot_id": ids["partial_fidelity_snapshot_id"],
        "inputs_catalog_id": ids["inputs_catalog_id"],
    }


async def _events() -> tuple[list[tuple[str, dict]], Any]:
    events: list[tuple[str, dict]] = []

    async def append(event_type: str, payload: dict) -> None:
        events.append((event_type, payload))

    return events, append


async def test_generation_lifecycle_round_trip_discover_plan_dispatch_poll_terminal(
    session_factory,
) -> None:
    driver = FaithfulLifecycleDriver()
    driver_registry = GenerationDriverRegistry()
    tool_registry = ToolRegistry(generation_driver_registry=driver_registry)

    async def register_bridge_adapters(ctx, register_capability):
        assert ctx.requested_families == []
        register_capability(_capability(driver))

    target = _install_module(
        "tests.phase7_generation_sibling", register_bridge_adapters
    )
    events, append = await _events()
    await register_all_siblings(
        resolve_siblings(entry_points_loader=lambda _group: {"generator": target}),
        tool_registry=tool_registry,
        event_appender=append,
        bridge_version="phase7-test",
    )

    assert driver_registry.get_driver(_BACKEND_ID) is driver
    assert driver_registry.get_driver("legacy.wrong_key") is None

    async with session_factory() as session:
        ids = await _seed_base(session)
        planner = Planner(
            session,
            tool_registry=tool_registry,
            platform_uuid_registry=None,  # type: ignore[arg-type]
            trained_identity_registry=None,  # type: ignore[arg-type]
            lineage_graph=InMemoryLineageGraph(),
        )
        plan = await planner.plan(**_plan_kwargs(ids))
        await session.commit()

    assert plan.operator_sequence[0]["backend_id"] == _BACKEND_ID

    result = await dispatch_plan(
        plan,
        driver_registry=driver_registry,
        session_factory=session_factory,
        event_appender=append,
    )
    assert result == DispatchResult(status="submitted", artifact_id=result.artifact_id)
    assert result.artifact_id is not None
    assert driver.submissions[0].operator_id == "generate_video_from_image"

    async with session_factory() as session:
        artifact = await GenerationArtifactRepo(session).get_by_id(result.artifact_id)
        assert artifact is not None
        assert artifact.lifecycle_state == "submitted"
        assert artifact.execution_provenance["backend_identity_triple"] == _TRIPLE
        assert artifact.execution_provenance["request_id"] == "req-1"
        assert resolve_backend_id(artifact) == _BACKEND_ID

    poll_result = await GenerationPoller(session_factory, driver_registry).poll_once()
    assert poll_result.processed == 1
    assert poll_result.terminal == 1
    assert driver.polled_request_ids == ["req-1"]

    async with session_factory() as session:
        terminal = await GenerationArtifactRepo(session).get_by_id(result.artifact_id)
        assert terminal is not None
        assert terminal.lifecycle_state == "complete"
        assert terminal.content_hash is not None

    event_names = [event_type for event_type, _payload in events]
    assert "generation_dispatch_submitted" in event_names
    assert "generation_dispatch_lineage_recorded" in event_names


async def test_dispatch_envelope_plan_free_direct_call_reaches_same_lifecycle(
    session_factory,
) -> None:
    """A plan-free ``dispatch_envelope`` caller (no ``plan_id``) lands in the
    identical submit/persist/poll lifecycle: an artifact row is created, a
    pollable ``artifact_id`` is returned, and both lineage events fire cleanly
    with ``plan_id`` absent everywhere."""

    driver = FaithfulLifecycleDriver()
    driver_registry = GenerationDriverRegistry()
    driver_registry.register_driver(driver)

    events, append = await _events()

    envelope = InvocationEnvelope(
        operator_id="generate_video_from_image",
        inputs=[
            ArtifactRef(
                artifact_id="artifact-src-1",
                artifact_type="artifact",
                metadata={},
            )
        ],
        backend_identity_triple=dict(_TRIPLE),
    )
    # Plan-free provenance: NO plan_id (a direct forge_generate_* caller has no
    # plan). ``planned_output_artifact_id`` is optional provenance.
    provenance = {"planned_output_artifact_id": None}

    result = await dispatch_envelope(
        envelope,
        provenance=provenance,
        driver_registry=driver_registry,
        session_factory=session_factory,
        event_appender=append,
    )

    assert result == DispatchResult(status="submitted", artifact_id=result.artifact_id)
    assert result.artifact_id is not None
    assert driver.submissions[0].operator_id == "generate_video_from_image"

    # The artifact lands in the same status-driven lifecycle the poller consumes.
    async with session_factory() as session:
        artifact = await GenerationArtifactRepo(session).get_by_id(result.artifact_id)
        assert artifact is not None
        assert artifact.lifecycle_state == "submitted"
        assert artifact.execution_provenance["backend_identity_triple"] == _TRIPLE
        assert artifact.execution_provenance["request_id"] == "req-1"
        assert resolve_backend_id(artifact) == _BACKEND_ID
        # plan_id is absent for a plan-free caller (body + lineage).
        assert "plan_id" not in artifact.content_provenance
        assert "source_plan_id" not in artifact.content_provenance["lineage"]
        assert artifact.content_provenance["operator_id"] == "generate_video_from_image"
        assert artifact.content_provenance["lineage"]["input_artifact_ids"] == [
            "artifact-src-1"
        ]

    # Both lineage events fire cleanly with plan_id absent.
    submitted = [p for n, p in events if n == "generation_dispatch_submitted"]
    lineage = [p for n, p in events if n == "generation_dispatch_lineage_recorded"]
    assert len(submitted) == 1
    assert len(lineage) == 1
    assert "plan_id" not in submitted[0]
    assert submitted[0]["backend_id"] == _BACKEND_ID
    assert submitted[0]["operator_id"] == "generate_video_from_image"
    assert "plan_id" not in lineage[0]
    assert lineage[0]["input_artifact_ids"] == ["artifact-src-1"]

    # Pollable by artifact_id in the shared lifecycle — same poller, no plan.
    poll_result = await GenerationPoller(session_factory, driver_registry).poll_once()
    assert poll_result.processed == 1
    assert poll_result.terminal == 1
    assert driver.polled_request_ids == ["req-1"]

    async with session_factory() as session:
        terminal = await GenerationArtifactRepo(session).get_by_id(result.artifact_id)
        assert terminal is not None
        assert terminal.lifecycle_state == "complete"
        assert terminal.content_hash is not None


async def test_generation_dispatch_no_driver_refuses_without_artifact(
    session_factory,
) -> None:
    async with session_factory() as session:
        plan = await ExecutionPlanRepo(session).insert_if_absent(
            {
                "operator_sequence": [
                    {
                        "operator_id": "generate_video_from_image",
                        "backend_id": "missing.backend",
                        "inputs": [],
                        "output_artifact_id": str(uuid.uuid4()),
                    }
                ],
                "backend_assignments": {
                    "generate_video_from_image": "missing.backend"
                },
                "transforms_inserted": [],
                "external_uploads_required": [],
                "cost_estimate": {},
                "predicted_compromise_consumption": [],
                "provenance_obligations": [],
                "feasibility_verdict": "feasible",
                "feasibility_explanation": "",
                "refusal_code": None,
                "intent_id": str(uuid.uuid4()),
                "planner_version": "phase7-test",
                "capability_snapshot_id": None,
                "rule_snapshot_id": str(uuid.uuid4()),
                "partial_fidelity_snapshot_id": str(uuid.uuid4()),
            }
        )
        await session.commit()

    events, append = await _events()
    result = await dispatch_plan(
        plan,
        driver_registry=GenerationDriverRegistry(),
        session_factory=session_factory,
        event_appender=append,
    )

    assert result == DispatchResult(status="refused", refusal_code="dispatch_no_driver")
    assert events == [
        (
            "dispatch_no_driver",
            {
                "plan_id": str(plan.id),
                "operator_id": "generate_video_from_image",
                "backend_id": "missing.backend",
            },
        )
    ]
    async with session_factory() as session:
        rows = await session.execute(
            select(DBEntity).where(DBEntity.entity_type == "orch_generation_artifact")
        )
        assert list(rows.scalars().all()) == []


def test_driver_registry_uses_backend_identity_triple_key() -> None:
    driver = FaithfulLifecycleDriver()
    registry = GenerationDriverRegistry()
    registry.register_driver(driver)

    assert backend_id_from_identity_triple(_TRIPLE) == _BACKEND_ID
    assert registry.registered_backends() == frozenset({_BACKEND_ID})
    assert registry.get_driver(_BACKEND_ID) is driver
    assert registry.get_driver("legacy.wrong_key") is None
