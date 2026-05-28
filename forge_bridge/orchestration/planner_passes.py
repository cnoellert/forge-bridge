"""Planner six-pass implementation (Phase 4B §5)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from forge_bridge.orchestration.errors import PlannerRefusalError
from forge_bridge.store.orch_capability_snapshot_repo import CapabilitySnapshotRepo
from forge_bridge.store.orch_inputs_catalog_repo import InputsCatalogRepo
from forge_bridge.store.orch_locked_intent_repo import LockedIntentRepo
from forge_bridge.store.orch_partial_fidelity_snapshot_repo import (
    PartialFidelitySnapshotRepo,
)
from forge_bridge.store.orch_pipeline_run_repo import PipelineRunRepo
from forge_bridge.store.orch_rule_snapshot_repo import RuleSnapshotRepo
from forge_bridge.store.orch_spec_convergence_trace_repo import SpecConvergenceTraceRepo

if TYPE_CHECKING:
    from forge_bridge.orchestration.planner import Planner, PlanningContext


def backend_id_from_snapshot_entry(entry: dict[str, Any]) -> str:
    triple = entry.get("backend_identity_triple") or {}
    surface = triple.get("surface", "unknown")
    path = triple.get("path", "default")
    return f"{surface}.{path}"


def _capabilities(entry: dict[str, Any]) -> dict[str, Any]:
    caps = entry.get("capabilities_opaque") or entry.get("capabilities") or {}
    return caps if isinstance(caps, dict) else {}


def _raise_refusal(code: str, explanation: str) -> None:
    raise PlannerRefusalError(code, explanation)


async def pass_1_validate_completeness(planner: Planner, ctx: PlanningContext) -> None:
    intent = await LockedIntentRepo(planner.session).get_by_id(ctx.intent_id)
    if intent is None:
        _raise_refusal("locked_intent_unresolvable", f"Intent {ctx.intent_id} not found")
    ctx.intent = intent

    for criterion in intent.success_criteria or []:
        if not isinstance(criterion, dict) or not criterion.get("measurement_spec"):
            _raise_refusal(
                "locked_intent_unresolvable",
                "Success criterion missing measurement_spec",
            )

    rule = await RuleSnapshotRepo(planner.session).get_by_id(ctx.rule_snapshot_id)
    if rule is None:
        _raise_refusal(
            "snapshot_unresolvable",
            f"Rule snapshot {ctx.rule_snapshot_id} not found",
        )
    ctx.rule_snapshot = rule.attributes

    partial = await PartialFidelitySnapshotRepo(planner.session).get_by_id(
        ctx.partial_fidelity_snapshot_id
    )
    if partial is None:
        _raise_refusal(
            "snapshot_unresolvable",
            f"Partial fidelity snapshot {ctx.partial_fidelity_snapshot_id} not found",
        )
    ctx.partial_fidelity_snapshot = partial.attributes

    if ctx.inputs_catalog_id is not None:
        catalog = await InputsCatalogRepo(planner.session).get_by_id(
            ctx.inputs_catalog_id
        )
        if catalog is None:
            _raise_refusal(
                "inputs_missing",
                f"Inputs catalog {ctx.inputs_catalog_id} not found",
            )
        ctx.inputs_catalog = catalog.attributes

    if ctx.capability_snapshot_id is None:
        snapshots = []
        for tool in planner.tool_registry.by_family("generation"):
            caps = tool.capabilities if isinstance(tool.capabilities, dict) else {}
            triple = caps.get("backend_identity_triple") or {
                "surface": tool.tool_id.split(".")[0] if "." in tool.tool_id else tool.tool_id,
                "path": "default",
            }
            snapshots.append(
                {
                    "backend_identity_triple": triple,
                    "declaration_hash": tool.tool_id,
                    "capabilities_opaque": caps,
                }
            )
        body = {"snapshots": snapshots}
        created = await CapabilitySnapshotRepo(planner.session).insert_if_absent(body)
        ctx.capability_snapshot_id = created.id
        ctx.capability_snapshot = created.attributes
    else:
        capability = await CapabilitySnapshotRepo(planner.session).get_by_id(
            ctx.capability_snapshot_id
        )
        if capability is None:
            _raise_refusal(
                "capability_snapshot_unresolvable",
                f"Capability snapshot {ctx.capability_snapshot_id} not found",
            )
        ctx.capability_snapshot = capability.attributes

    run = await PipelineRunRepo(planner.session).get_by_id(ctx.run_id)
    if run is not None and run.intent_id:
        ctx.shot_id = uuid.UUID(str(run.attributes.get("shot_id", ctx.run_id)))


async def pass_2_filter_candidates(planner: Planner, ctx: PlanningContext) -> None:
    assert ctx.intent is not None
    assert ctx.capability_snapshot is not None

    deliverable = ctx.intent.deliverable_spec or {}
    inputs = (ctx.inputs_catalog or {}).get("inputs", [])
    shot_id = ctx.shot_id or ctx.run_id
    identity_as_of = (
        ctx.source_authored_at
        if ctx.pinning_policy is not None
        and getattr(ctx.pinning_policy, "identity", None) == "honor_pinning"
        and ctx.source_authored_at is not None
        else datetime.now(timezone.utc)
    )

    candidates: list[dict[str, Any]] = []
    for entry in ctx.capability_snapshot.get("snapshots", []):
        if not isinstance(entry, dict):
            continue
        backend_id = backend_id_from_snapshot_entry(entry)
        caps = _capabilities(entry)

        if deliverable.get("requires_first_frame") and not caps.get(
            "first_frame_guarantee", False
        ):
            continue
        if deliverable.get("requires_identity_lock") and not caps.get(
            "identity_lock_support", False
        ):
            continue

        if (
            ctx.pinning_policy is not None
            and getattr(ctx.pinning_policy, "backend", None) == "honor_pinning"
            and ctx.source_backend_revision is not None
            and ctx.pinned_backend_id is not None
            and backend_id == ctx.pinned_backend_id
        ):
            triple = entry.get("backend_identity_triple") or {}
            if triple.get("revision") != ctx.source_backend_revision:
                continue

        for input_item in inputs:
            if not isinstance(input_item, dict):
                continue
            identity_id = input_item.get("trained_identity_id")
            if identity_id is not None:
                valid, reason = await planner.trained_identity_registry.is_valid_for_context(
                    uuid.UUID(str(identity_id)),
                    shot_id=shot_id,
                    as_of=identity_as_of,
                )
                if not valid:
                    if reason == "validity_expired":
                        _raise_refusal(
                            "trained_identity_validity_expired",
                            f"Trained identity {identity_id} expired",
                        )
                    if reason == "reuse_forbidden_for_scope":
                        _raise_refusal(
                            "identity_reuse_forbidden",
                            f"Trained identity {identity_id} forbidden for shot",
                        )

            if input_item.get("needs_upload"):
                content_sha = input_item.get("content_sha256", "")
                platform_uuid = await planner.platform_uuid_registry.lookup(
                    content_sha,
                    backend_id,
                )
                if platform_uuid is None and not caps.get("upload_support", False):
                    _raise_refusal(
                        "external_upload_unavailable",
                        f"No platform UUID for {content_sha} on {backend_id}",
                    )

        cost = caps.get("estimated_cost", caps.get("cost", 1.0))
        depth = int(
            caps.get(
                "chain_depth",
                await planner.lineage_graph.chain_depth_from(ctx.run_id),
            )
        )
        candidates.append(
            {
                "backend_id": backend_id,
                "entry": entry,
                "capabilities": caps,
                "cost": float(cost) if cost is not None else 1.0,
                "acceptance_score": float(caps.get("acceptance_score", 0.5)),
                "chain_depth": depth,
            }
        )

    if not candidates:
        if (
            ctx.pinning_policy is not None
            and getattr(ctx.pinning_policy, "backend", None) == "honor_pinning"
            and ctx.source_backend_revision is not None
        ):
            _raise_refusal(
                "backend_revision_unreachable",
                "Honor-pinned backend revision is unavailable in capability snapshot",
            )
        _raise_refusal("no_feasible_backend", "No backend satisfies hard constraints")

    ctx.candidates = candidates


async def pass_3_insert_transforms(planner: Planner, ctx: PlanningContext) -> None:
    assert ctx.intent is not None
    inputs = (ctx.inputs_catalog or {}).get("inputs", [])
    requires_transform = any(
        isinstance(item, dict) and item.get("photoreal_motion_source")
        for item in inputs
    )

    if not requires_transform:
        return

    for candidate in ctx.candidates:
        caps = candidate["capabilities"]
        if not caps.get("content_policy_real_person_classifier"):
            continue

        ctx.content_policy_transform_required = True
        perceptual = planner.tool_registry.by_family("perceptual")
        matte = planner.tool_registry.by_family("matte")
        provider = perceptual[0] if perceptual else (matte[0] if matte else None)
        if provider is None:
            _raise_refusal(
                "transform_unavailable",
                "Content-policy bypass transform required but no perceptual/matte provider",
            )

        ctx.transforms_inserted.append(
            {
                "transform_id": f"transform-{provider.tool_id}",
                "reason": "content_policy_bypass",
                "rule_ref": "rule-14",
                "providing_operator": provider.tool_id,
            }
        )
        return


async def pass_4_validate_plan_shape_rules(planner: Planner, ctx: PlanningContext) -> None:
    assert ctx.intent is not None
    assert ctx.rule_snapshot is not None
    assert ctx.capability_snapshot is not None

    plan_under_construction = ctx.plan_under_construction()
    for rule in ctx.rule_snapshot.get("rules", []):
        if not isinstance(rule, dict):
            continue
        phases = rule.get("enforcement_phases") or []
        if "planning-time" not in phases:
            continue
        rule_id = rule.get("rule_id") or rule.get("id")
        check = planner.planning_rules.get(str(rule_id)) if rule_id else None
        if check is None:
            continue
        violation = await check.check(
            plan_under_construction=plan_under_construction,
            intent=ctx.intent,
            capability_snapshot=ctx.capability_snapshot,
            lineage_graph=planner.lineage_graph,
        )
        if violation is not None:
            _raise_refusal(violation.refusal_code, violation.explanation)


async def pass_5_rank_and_predict(planner: Planner, ctx: PlanningContext) -> None:
    assert ctx.intent is not None
    assert ctx.partial_fidelity_snapshot is not None

    models_by_backend: dict[str, dict] = {}
    for model in ctx.partial_fidelity_snapshot.get("models", []):
        if isinstance(model, dict):
            bid = backend_id_from_snapshot_entry(model)
            models_by_backend[bid] = model

    ranked: list[tuple[float, float, int, dict]] = []
    for candidate in ctx.candidates:
        backend_id = candidate["backend_id"]
        model = models_by_backend.get(backend_id, {})
        dimensions = model.get("dimensions", [])
        predicted = []
        for criterion in ctx.intent.success_criteria or []:
            if not isinstance(criterion, dict):
                continue
            cid = criterion.get("criterion_id", "unknown")
            for dim in dimensions:
                if isinstance(dim, dict):
                    predicted.append(
                        {
                            "criterion_id": cid,
                            "dimension": dim.get("axis", "default"),
                            "magnitude": {"scalar": dim.get("scalar", 0.0)},
                        }
                    )
        candidate["predicted_compromise_consumption"] = predicted
        depth = await planner.lineage_graph.chain_depth_from(ctx.run_id)
        candidate["chain_depth"] = depth
        ranked.append(
            (
                -candidate["acceptance_score"],
                candidate["cost"],
                depth,
                candidate,
            )
        )

    ranked.sort(key=lambda item: (item[0], item[1], item[2]))
    ctx.selected_candidate = ranked[0][3]
    ctx.operator_sequence = [
        {
            "operator_id": "generate_video_from_image",
            "backend_id": ctx.selected_candidate["backend_id"],
            "inputs": [],
            "output_artifact_id": str(
                uuid.uuid5(
                    ctx.run_id,
                    f"{ctx.intent_id}:{ctx.selected_candidate['backend_id']}",
                )
            ),
        }
    ]
    ctx.backend_assignments = {
        "generate_video_from_image": ctx.selected_candidate["backend_id"]
    }
    ctx.cost_estimate = {"USD": ctx.selected_candidate["cost"]}
    ctx.predicted_compromise_consumption = ctx.selected_candidate.get(
        "predicted_compromise_consumption", []
    )


async def pass_6_emit_feasibility_verdict(planner: Planner, ctx: PlanningContext) -> None:
    assert ctx.intent is not None

    allowed = {
        item.get("criterion_id"): item.get("budget", 1.0)
        for item in (ctx.intent.allowed_compromises or [])
        if isinstance(item, dict)
    }
    escalation = float(ctx.intent.escalation_threshold or 1.0)

    for prediction in ctx.predicted_compromise_consumption:
        if not isinstance(prediction, dict):
            continue
        cid = prediction.get("criterion_id")
        magnitude = prediction.get("magnitude") or {}
        scalar = float(magnitude.get("scalar", 0.0))
        budget = float(allowed.get(cid, 1.0))
        if scalar > budget and scalar > escalation:
            _raise_refusal(
                "compromise_budget_exceeded",
                f"Predicted compromise for {cid} exceeds allowed budget",
            )

    ledger = planner.compromise_ledger_repo
    cumulative = 0.0
    for entry in await ledger.get_entries(ctx.intent_id, side="audit_actual"):
        mag = entry.magnitude if isinstance(entry.magnitude, dict) else {}
        cumulative += float(mag.get("scalar", 0.0))

    predicted_total = sum(
        float((p.get("magnitude") or {}).get("scalar", 0.0))
        for p in ctx.predicted_compromise_consumption
        if isinstance(p, dict)
    )
    if cumulative + predicted_total > escalation:
        _raise_refusal(
            "cumulative_threshold_exceeded",
            "Cumulative compromise consumption exceeds escalation threshold",
        )

    ctx.feasibility_verdict = "feasible"
    ctx.feasibility_explanation = "Plan satisfies constraints and compromise budget"
