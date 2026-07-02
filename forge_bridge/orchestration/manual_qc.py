"""Manual author -> QC -> re-author loop over the generation runtime.

This is intentionally thin: it creates a one-step ``author_prompt`` execution
plan, dispatches it through the existing GenerationDriverRegistry, polls once,
and leaves the run paused at execution so a human QC note can mint a derived
attempt through ReplayEngine.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from forge_bridge import __version__
from forge_bridge.orchestration.author_driver import OllamaAuthorDriver
from forge_bridge.orchestration.discovery import (
    make_db_event_appender,
    register_all_siblings,
    resolve_siblings,
)
from forge_bridge.orchestration.dispatcher import dispatch_plan
from forge_bridge.orchestration.drivers import GenerationDriverRegistry
from forge_bridge.orchestration.engine import GraphEngine
from forge_bridge.orchestration.errors import PlannerRefusalError
from forge_bridge.orchestration.lineage_graph import InMemoryLineageGraph
from forge_bridge.orchestration.planner import Planner
from forge_bridge.orchestration.registration import ToolRegistry
from forge_bridge.orchestration.replay import ReconstructionRequest, ReplayEngine
from forge_bridge.orchestration.worker import GenerationPoller
from forge_bridge.store.orch_execution_plan_repo import ExecutionPlanRepo
from forge_bridge.store.orch_capability_snapshot_repo import CapabilitySnapshotRepo
from forge_bridge.store.orch_generation_artifact_repo import GenerationArtifactRepo
from forge_bridge.store.orch_locked_intent_repo import LockedIntentRepo
from forge_bridge.store.orch_partial_fidelity_snapshot_repo import (
    PartialFidelitySnapshotRepo,
)
from forge_bridge.store.generation_grant_repo import GenerationGrantRepo
from forge_bridge.store.orch_pipeline_run_repo import PipelineRunRepo
from forge_bridge.store.orch_rule_snapshot_repo import RuleSnapshotRepo
from forge_bridge.store.orch_spec_convergence_trace_repo import (
    SpecConvergenceTraceRepo,
)
from forge_bridge.store.session import get_async_session_factory

AUTHOR_OPERATOR_ID = "author_prompt"
AUTHOR_TARGET = "prompt"
DEFAULT_DATA_ROOT = Path.home() / ".forge-bridge" / "generation"
MANUAL_QC_SHOT_ID = uuid.UUID("00000000-0000-0000-0000-0000000000a1")


@dataclass(frozen=True)
class ManualQCResult:
    run_id: uuid.UUID
    artifact_id: uuid.UUID
    text: str
    lifecycle_stage: str
    lifecycle_status: str

    def to_dict(self) -> dict[str, Any]:
        body = asdict(self)
        body["run_id"] = str(self.run_id)
        body["artifact_id"] = str(self.artifact_id)
        return body


@dataclass(frozen=True)
class ManualQCApproval:
    run_id: uuid.UUID
    lifecycle_stage: str
    lifecycle_status: str

    def to_dict(self) -> dict[str, Any]:
        body = asdict(self)
        body["run_id"] = str(self.run_id)
        return body


@dataclass(frozen=True)
class _Runtime:
    session_factory: async_sessionmaker[AsyncSession]
    driver_registry: GenerationDriverRegistry
    event_appender: Callable[[str, dict], Awaitable[None]]


async def start_author(
    intent: str,
    *,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
    driver_registry: GenerationDriverRegistry | None = None,
    event_appender: Callable[[str, dict], Awaitable[None]] | None = None,
    data_root: Path | None = None,
) -> ManualQCResult:
    """Create, dispatch, poll, and pause a single ``author_prompt`` run."""

    clean_intent = intent.strip()
    if not clean_intent:
        raise ValueError("intent must be a non-empty string")

    runtime = await _runtime(
        session_factory=session_factory,
        driver_registry=driver_registry,
        event_appender=event_appender,
    )
    backend_id, triple = _select_author_backend(runtime.driver_registry)
    data_root = data_root or DEFAULT_DATA_ROOT

    async with runtime.session_factory() as session:
        intent_row = await LockedIntentRepo(session).insert_if_absent(
            _locked_intent_body(clean_intent)
        )
        rule = await RuleSnapshotRepo(session).insert_if_absent(_rule_snapshot_body())
        capability = await CapabilitySnapshotRepo(session).insert_if_absent(
            _capability_snapshot_body(triple)
        )
        partial = await PartialFidelitySnapshotRepo(session).insert_if_absent(
            _partial_fidelity_body(triple)
        )
        trace = await SpecConvergenceTraceRepo(session).insert_if_absent(
            {
                "iterations": [
                    {
                        "version": 1,
                        "source": "manual_qc",
                        "operator_id": AUTHOR_OPERATOR_ID,
                    }
                ],
                "lock_event": {"kind": "manual_qc_author"},
            }
        )
        # Origin-run GenerationGrant mint (#146): author-QC is bridge's OWN
        # authority (a free local ollama draft), so bridge mints AND auto-
        # ratifies a fresh grant here and threads its handle onto run.grant_id.
        # The chokepoint resolves run.grant_id via run_id and consumes it once,
        # keeping the live author flow green while still gated. This is a fresh
        # per-run grant, NOT grant inheritance (that stays reserved for #142).
        grant_repo = GenerationGrantRepo(session)
        grant = await grant_repo.propose(
            operator_id=AUTHOR_OPERATOR_ID,
            backend_identity_triple=triple,
            estimated_cost={"currency": "USD", "amount": 0.0},
            run_kind="manual_qc_author",
        )
        await grant_repo.ratify(grant.grant_id, actor="bridge:manual_qc")
        run = await PipelineRunRepo(session).insert_if_absent(
            {
                "run_kind": "manual_qc_author",
                "intent_id": str(intent_row.id),
                "spec_convergence_trace_id": str(trace.id),
                "authored_at": datetime.now(timezone.utc).isoformat(),
                "grant_id": grant.grant_id,
            }
        )
        plan = await ExecutionPlanRepo(session).insert_if_absent(
            _plan_body(
                intent_id=intent_row.id,
                run_id=run.id,
                rule_snapshot_id=rule.id,
                capability_snapshot_id=capability.id,
                partial_fidelity_snapshot_id=partial.id,
                backend_id=backend_id,
                intent=clean_intent,
                data_root=data_root,
            )
        )

        engine = GraphEngine(session)
        await engine.create_run(
            run_id=run.id,
            shot_id=MANUAL_QC_SHOT_ID,
            intent_id=intent_row.id,
        )
        await engine.transition(run.id, to_stage="spec_convergence")
        await engine.apply_decision_event(
            run.id,
            "lock_intent",
            {"intent_id": str(intent_row.id), "source": "manual_qc"},
        )
        await engine.transition(
            run.id,
            to_stage="execution",
            plan_id=plan.id,
            intent_id=intent_row.id,
        )
        await session.commit()

    return await _dispatch_poll_and_pause(
        runtime,
        run_id=run.id,
        plan_id=plan.id,
    )


async def revise(
    run_id: uuid.UUID | str,
    qc_note: str,
    *,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
    driver_registry: GenerationDriverRegistry | None = None,
    event_appender: Callable[[str, dict], Awaitable[None]] | None = None,
) -> ManualQCResult:
    """Mint a derived authoring run with a typed ``qc_correction`` reference."""

    source_run_id = _parse_uuid(run_id, "run_id")
    clean_note = qc_note.strip()
    if not clean_note:
        raise ValueError("qc_note must be a non-empty string")

    runtime = await _runtime(
        session_factory=session_factory,
        driver_registry=driver_registry,
        event_appender=event_appender,
    )

    async with runtime.session_factory() as session:
        replay = ReplayEngine(
            session,
            graph_engine=GraphEngine(session),
            planner=Planner(
                session,
                tool_registry=ToolRegistry(),
                platform_uuid_registry=None,  # type: ignore[arg-type]
                trained_identity_registry=None,  # type: ignore[arg-type]
                lineage_graph=InMemoryLineageGraph(),
            ),
        )
        # D6: derived-run GenerationGrant inheritance point; ReplayEngine must
        # carry source_run.grant_id onto this remediation run when grants land.
        lifecycle = await replay.reconstruct(
            ReconstructionRequest(
                request_id=uuid.uuid4(),
                kind="remediation",
                source_run_id=source_run_id,
                remediation_entry="new_attempt_same_plan",
            )
        )
        source_plan = await ExecutionPlanRepo(session).get_by_id(lifecycle.plan_id)
        if source_plan is None:
            raise PlannerRefusalError(
                "source_run_incomplete",
                f"source plan {lifecycle.plan_id} missing",
            )
        revised_plan = await ExecutionPlanRepo(session).insert_if_absent(
            _plan_body_with_qc(
                source_plan.attributes,
                clean_note,
                source_run_id,
                lifecycle.run_id,
            )
        )
        await GraphEngine(session).transition(
            lifecycle.run_id,
            plan_id=revised_plan.id,
            event_payload={"manual_qc": "qc_correction_attached"},
        )
        # Derived-run GenerationGrant mint (#146): each remediation attempt
        # mints AND auto-ratifies its OWN fresh grant (author-QC authority),
        # passed explicitly to the chokepoint. This is deliberately NOT grant
        # inheritance from the source run (a single-use grant, inherited, would
        # already be consumed) — inheritance stays reserved for #142.
        _backend_id, triple = _select_author_backend(runtime.driver_registry)
        grant_repo = GenerationGrantRepo(session)
        grant = await grant_repo.propose(
            operator_id=AUTHOR_OPERATOR_ID,
            backend_identity_triple=triple,
            estimated_cost={"currency": "USD", "amount": 0.0},
            run_kind="manual_qc_remediation",
        )
        await grant_repo.ratify(grant.grant_id, actor="bridge:manual_qc")
        derived_grant_id = grant.grant_id
        await session.commit()

    return await _dispatch_poll_and_pause(
        runtime,
        run_id=lifecycle.run_id,
        plan_id=revised_plan.id,
        grant_id=derived_grant_id,
    )


async def approve(
    run_id: uuid.UUID | str,
    *,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
    actor: str = "operator",
) -> ManualQCApproval:
    """Accept the current authoring run and advance it out of QC pause."""

    parsed = _parse_uuid(run_id, "run_id")
    factory = session_factory or get_async_session_factory()
    async with factory() as session:
        lifecycle = await GraphEngine(session).transition(
            parsed,
            to_stage="audit",
            to_status="active",
            clear_block=True,
            event_payload={"manual_qc": "approved", "actor": actor},
        )
        await session.commit()
        return ManualQCApproval(
            run_id=parsed,
            lifecycle_stage=lifecycle.current_stage,
            lifecycle_status=lifecycle.status,
        )


async def _runtime(
    *,
    session_factory: async_sessionmaker[AsyncSession] | None,
    driver_registry: GenerationDriverRegistry | None,
    event_appender: Callable[[str, dict], Awaitable[None]] | None,
) -> _Runtime:
    factory = session_factory or get_async_session_factory()
    registry = driver_registry
    appender = event_appender or make_db_event_appender(factory)
    if registry is None:
        registry = GenerationDriverRegistry()
        tool_registry = ToolRegistry(generation_driver_registry=registry)
        await register_all_siblings(
            resolve_siblings(),
            tool_registry=tool_registry,
            event_appender=appender,
            bridge_version=__version__,
        )
        # Self-contained on a stock install (#66 Slice 1): register bridge's OWN
        # local-Ollama author_prompt driver directly into the default registry,
        # so _select_author_backend finds an ollama-api author surface even with
        # ZERO federation siblings present. Only the default (registry is None)
        # path gets it — a caller-supplied registry stays exactly as passed.
        _register_bridge_author_driver(registry)
    return _Runtime(factory, registry, appender)


def _register_bridge_author_driver(registry: GenerationDriverRegistry) -> None:
    """Register the bridge-local ollama-api author driver if not already present.

    Guarded against a sibling that happens to register the same composite
    backend_id (surface.model): register_driver would raise on a duplicate, so
    a pre-existing backend wins and bridge's driver is skipped.
    """
    driver = OllamaAuthorDriver()
    if driver.backend_id in registry.registered_backends():
        return
    registry.register_driver(driver)


async def _dispatch_poll_and_pause(
    runtime: _Runtime,
    *,
    run_id: uuid.UUID,
    plan_id: uuid.UUID,
    grant_id: str | None = None,
) -> ManualQCResult:
    async with runtime.session_factory() as session:
        plan = await ExecutionPlanRepo(session).get_by_id(plan_id)
        if plan is None:
            raise PlannerRefusalError("source_run_incomplete", f"plan {plan_id} missing")

    # grant_id is None for the origin run (the chokepoint resolves run.grant_id
    # from run_id); the remediation path passes its fresh grant explicitly.
    dispatch = await dispatch_plan(
        plan,
        driver_registry=runtime.driver_registry,
        session_factory=runtime.session_factory,
        event_appender=runtime.event_appender,
        run_id=run_id,
        grant_id=grant_id,
    )
    if dispatch.status != "submitted" or dispatch.artifact_id is None:
        raise RuntimeError(f"author dispatch failed: {dispatch.refusal_code}")

    await GenerationPoller(runtime.session_factory, runtime.driver_registry).poll_once()

    async with runtime.session_factory() as session:
        artifact = await GenerationArtifactRepo(session).get_by_id(dispatch.artifact_id)
        if artifact is None:
            raise RuntimeError(f"artifact {dispatch.artifact_id} disappeared")
        text = _artifact_text(artifact.execution_provenance)
        lifecycle = await GraphEngine(session).transition(
            run_id,
            to_status="paused",
            block={
                "kind": "awaiting_decision",
                "decision_type": "approve_remediation",
                "source": "manual_qc",
                "artifact_id": str(dispatch.artifact_id),
            },
            event_payload={"manual_qc": "awaiting_review"},
        )
        await session.commit()

    return ManualQCResult(
        run_id=run_id,
        artifact_id=dispatch.artifact_id,
        text=text,
        lifecycle_stage=lifecycle.current_stage,
        lifecycle_status=lifecycle.status,
    )


def _select_author_backend(
    driver_registry: GenerationDriverRegistry,
) -> tuple[str, dict[str, Any]]:
    for backend_id in sorted(driver_registry.registered_backends()):
        driver = driver_registry.get_driver(backend_id)
        triple = getattr(driver, "backend_identity_triple", {}) if driver else {}
        # NOTE: backend_identity_triple.path is the model (for example
        # "llama3.2"); AUTHOR_OPERATOR_ID lives on the plan step as operator_id.
        # Slice 1 selects the free local authoring surface pragmatically.
        if isinstance(triple, dict) and triple.get("surface") == "ollama-api":
            return backend_id, dict(triple)
    raise RuntimeError("no local (ollama-api) author_prompt driver registered")


def _locked_intent_body(intent: str) -> dict[str, Any]:
    return {
        "source_read": {"kind": "manual_qc_author", "intent": intent},
        "change_manifest": [],
        "success_criteria": [
            {
                "criterion_id": "manual_qc_text",
                "statement": "human reviewer accepts authored prompt text",
                "measurement_spec": {"method": "manual_qc"},
                "tolerances": {"accepted": True},
            }
        ],
        "allowed_compromises": [],
        "hard_constraints": ["text_only", "single_beat", "manual_qc"],
        "escalation_threshold": 1.0,
        "deliverable_spec": {
            "medium": "text",
            "operator_id": AUTHOR_OPERATOR_ID,
            "target": AUTHOR_TARGET,
        },
    }


def _rule_snapshot_body() -> dict[str, Any]:
    return {
        "rules": ["manual_qc_required_before_acceptance"],
        "source_ref": "manual-qc-slice-1",
        "snapshot_timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _partial_fidelity_body(triple: dict[str, Any]) -> dict[str, Any]:
    return {
        "models": [
            {
                "backend_identity_triple": triple,
                "dimensions": [{"axis": "manual_qc", "scalar": 0.0}],
            }
        ]
    }


def _capability_snapshot_body(triple: dict[str, Any]) -> dict[str, Any]:
    return {
        "snapshots": [
            {
                "backend_identity_triple": triple,
                "declaration_hash": "manual-qc-slice-1",
                "capabilities_opaque": {
                    "operator_id": AUTHOR_OPERATOR_ID,
                    "cost_tier": "draft",
                },
            }
        ]
    }


def _plan_body(
    *,
    intent_id: uuid.UUID,
    run_id: uuid.UUID,
    rule_snapshot_id: uuid.UUID,
    capability_snapshot_id: uuid.UUID,
    partial_fidelity_snapshot_id: uuid.UUID,
    backend_id: str,
    intent: str,
    data_root: Path,
) -> dict[str, Any]:
    return {
        "operator_sequence": [
            {
                "operator_id": AUTHOR_OPERATOR_ID,
                "backend_id": backend_id,
                "inputs": [
                    {
                        "artifact_id": f"manual_intent:{intent_id}",
                        "artifact_type": "text_intent",
                        "metadata": {
                            "prompt": intent,
                            "role": "structural",
                            "scalars": {
                                "data_root": str(data_root),
                                "target": AUTHOR_TARGET,
                            },
                        },
                    }
                ],
                "output_artifact_id": str(uuid.uuid4()),
            }
        ],
        "backend_assignments": {AUTHOR_OPERATOR_ID: backend_id},
        "transforms_inserted": [],
        "external_uploads_required": [],
        "cost_estimate": {"currency": "USD", "estimated": 0.0},
        "predicted_compromise_consumption": [],
        "provenance_obligations": ["manual_qc_note_before_remediation"],
        "feasibility_verdict": "feasible",
        "feasibility_explanation": "manual QC authoring run",
        "refusal_code": None,
        "intent_id": str(intent_id),
        "run_id": str(run_id),
        "planner_version": "manual-qc-slice-1",
        "capability_snapshot_id": str(capability_snapshot_id),
        "rule_snapshot_id": str(rule_snapshot_id),
        "partial_fidelity_snapshot_id": str(partial_fidelity_snapshot_id),
    }


def _plan_body_with_qc(
    source_body: dict[str, Any],
    qc_note: str,
    source_run_id: uuid.UUID,
    new_run_id: uuid.UUID,
) -> dict[str, Any]:
    body = dict(source_body)
    steps = [dict(step) for step in body.get("operator_sequence") or []]
    if not steps:
        raise RuntimeError("source plan has no operator sequence")
    inputs = list(steps[0].get("inputs") or [])
    inputs.append(
        {
            "artifact_id": f"manual_qc:{uuid.uuid4()}",
            "artifact_type": "qc_correction",
            "metadata": {
                "role": "editorial",
                "qc_correction": qc_note,
                "source_run_id": str(source_run_id),
            },
        }
    )
    steps[0]["inputs"] = inputs
    steps[0]["output_artifact_id"] = str(uuid.uuid4())
    body["operator_sequence"] = steps
    body["run_id"] = str(new_run_id)
    body["provenance_obligations"] = list(
        body.get("provenance_obligations") or []
    ) + ["qc_correction_ref"]
    body["manual_qc"] = {
        "source_run_id": str(source_run_id),
        "qc_correction": qc_note,
    }
    return body


def _artifact_text(execution_provenance: Any) -> str:
    if not isinstance(execution_provenance, dict):
        return ""
    for key in ("text", "final_text"):
        value = execution_provenance.get(key)
        if isinstance(value, str) and value:
            return value
    media_url = execution_provenance.get("media_url")
    if isinstance(media_url, str) and media_url:
        path = Path(media_url.removeprefix("file://")).expanduser()
        if path.exists():
            return path.read_text(encoding="utf-8")
    return ""


def _parse_uuid(value: uuid.UUID | str, field: str) -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except ValueError as exc:
        raise ValueError(f"{field} must be a UUID") from exc
