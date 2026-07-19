"""Proof for Bridge-owned authorization and live editorial graph wiring."""

from __future__ import annotations

import copy
import hashlib
import json

import pytest

from forge_bridge.composition.dispatch import UnifiedDispatch
from forge_bridge.composition.executor import GraphExecutor
from forge_bridge.composition.host_resolve_boundary import HostResolveBoundary
from forge_bridge.composition.operation_boundary import OperationDispatchBoundary
from forge_bridge.orchestration.live_editorial_vertical import (
    EDITORIAL_STEP_CAPABILITIES_OPERATION_TYPE,
    LiveEditorialVerticalError,
    authorize_live_flame_step_plan,
    build_live_flame_rename_preview_spec,
)


def _fingerprint(value: dict) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _step_plan() -> dict:
    return {
        "kind": "traffik.editorial_step_plan",
        "schema_version": 1,
        "plan_id": "phase114-rename",
        "operation_type": "traffik.editorial.apply_steps",
        "status": "ok",
        "steps": [
            {
                "operation": "rename_segment",
                "step_id": "rename",
                "params": {
                    "sequence_id": "sequence-stable",
                    "track_id": "track-stable",
                    "segment_id": "segment-stable",
                    "name": "shot-010__FORGE_UAT_PROPOSED",
                },
            }
        ],
    }


def _capability_data(*, mode: str, step_plan: dict | None = None) -> dict:
    source = step_plan or _step_plan()
    fingerprint = _fingerprint(source)
    return {
        "kind": "traffik.editorial_step_capability_result",
        "schema_version": 1,
        "operation_type": EDITORIAL_STEP_CAPABILITIES_OPERATION_TYPE,
        "mode": mode,
        "status": "ready" if mode == "discover" else "authorized",
        "trust_status": "trusted",
        "allowed": True,
        "dispatch_authorized": mode == "apply",
        "drift": False,
        "read_only": True,
        "mutation_safe": True,
        "step_plan_fingerprint": fingerprint,
        "matrix_fingerprint": "matrix-fingerprint",
        "capability_plan_fingerprint": "capability-fingerprint",
        "capability_plan": {
            "target_plugin": "flame",
            "source_step_plan_fingerprint": fingerprint,
            "steps": [
                {
                    "operation": "rename_segment",
                    "allowed": True,
                    "trust_status": "trusted",
                }
            ],
        },
    }


@pytest.mark.asyncio
async def test_authorize_live_flame_step_plan_holds_discover_fingerprints() -> None:
    calls: list[tuple[str, dict]] = []

    async def run_operation(operation_type: str, **kwargs):
        calls.append((operation_type, copy.deepcopy(kwargs)))
        mode = kwargs["params"]["mode"]
        return {"status": "succeeded", "data": _capability_data(mode=mode)}

    authorization = await authorize_live_flame_step_plan(
        _step_plan(),
        run_operation=run_operation,
        project_id="project-1",
    )

    assert authorization["status"] == "authorized"
    assert authorization["dispatch_authorized"] is True
    assert [call[0] for call in calls] == [
        EDITORIAL_STEP_CAPABILITIES_OPERATION_TYPE,
        EDITORIAL_STEP_CAPABILITIES_OPERATION_TYPE,
    ]
    assert [call[1]["params"]["mode"] for call in calls] == [
        "discover",
        "apply",
    ]
    apply_params = calls[1][1]["params"]
    assert apply_params["held_step_plan_fingerprint"] == _fingerprint(_step_plan())
    assert apply_params["held_matrix_fingerprint"] == "matrix-fingerprint"
    assert apply_params["held_capability_plan_fingerprint"] == (
        "capability-fingerprint"
    )


@pytest.mark.asyncio
async def test_authorize_live_flame_step_plan_refuses_drift() -> None:
    async def run_operation(_operation_type: str, **kwargs):
        mode = kwargs["params"]["mode"]
        data = _capability_data(mode=mode)
        if mode == "apply":
            data["matrix_fingerprint"] = "drifted"
        return {"status": "succeeded", "data": data}

    with pytest.raises(LiveEditorialVerticalError, match="drifted"):
        await authorize_live_flame_step_plan(
            _step_plan(),
            run_operation=run_operation,
        )


def test_preview_spec_requires_trusted_exact_rename_authorization() -> None:
    plan = _step_plan()
    authorization = _capability_data(mode="apply", step_plan=plan)

    graph = build_live_flame_rename_preview_spec(
        sequence_name="FORGE_UAT_HOST_APPLY_20260624",
        reel_names=["Testing"],
        step_plan=plan,
        capability_authorization=authorization,
        project_id="project-1",
    )

    assert [node.node_id for node in graph.nodes] == [
        "read_edit_state",
        "apply_steps",
        "select_delta",
        "host_resolve",
        "delta_to_manifest",
    ]
    assert [node.operator_id for node in graph.nodes] == [
        "flame.editorial.read_edit_state",
        "traffik.editorial.apply_steps",
        "select_delta",
        "traffik.flame_delta.host_resolve",
        "delta_to_manifest",
    ]
    assert [
        (edge.from_node, edge.to_node, edge.to_port) for edge in graph.edges
    ] == [
        ("read_edit_state", "apply_steps", "state"),
        ("apply_steps", "select_delta", "result"),
        ("select_delta", "host_resolve", "delta"),
        ("host_resolve", "delta_to_manifest", "deltas"),
    ]
    assert graph.nodes[0].config["arguments"] == {
        "sequence_name": "FORGE_UAT_HOST_APPLY_20260624",
        "reel_names": ["Testing"],
        "project_id": "project-1",
    }
    assert graph.nodes[1].config["held_capability_authorization"] == (
        authorization
    )

    for field, value in (
        ("dispatch_authorized", False),
        ("trust_status", "review_required"),
        ("drift", True),
    ):
        invalid = copy.deepcopy(authorization)
        invalid[field] = value
        with pytest.raises(LiveEditorialVerticalError, match="not trusted"):
            build_live_flame_rename_preview_spec(
                sequence_name="FORGE_UAT_HOST_APPLY_20260624",
                step_plan=plan,
                capability_authorization=invalid,
            )

    changed_plan = copy.deepcopy(plan)
    changed_plan["steps"][0]["params"]["name"] = "changed-after-authorization"
    with pytest.raises(LiveEditorialVerticalError, match="does not match"):
        build_live_flame_rename_preview_spec(
            sequence_name="FORGE_UAT_HOST_APPLY_20260624",
            step_plan=changed_plan,
            capability_authorization=authorization,
        )


def _entry() -> dict:
    return {
        "action": "updated",
        "object_type": "segment",
        "object_id": "segment-stable",
        "before": {"name": "shot-010"},
        "after": {"name": "shot-010__FORGE_UAT_PROPOSED"},
        "metadata": {
            "sequence_name": "FORGE_UAT_HOST_APPLY_20260624",
            "track_idx": 0,
            "record_in": 100,
            "seg_name": "shot-010",
            "source_name": "plate-010",
        },
    }


def _delta() -> dict:
    return {
        "type": "timeline_delta",
        "sequence_id": "sequence-stable",
        "changes": [_entry()],
    }


def _host_payload() -> dict:
    return {
        "schema_version": 3,
        "payload_kind": "traffik.flame_delta_host_resolve_payload",
        "plan": {
            "reason_code": "flame_delta_host_resolve_ready",
            "output": {
                "summary": {"held_entry_count": 0, "routed_entry_count": 1},
                "held_entries": [],
            },
        },
        "deltas": [
            {
                "type": "timeline_delta",
                "sequence_id": "FORGE_UAT_HOST_APPLY_20260624",
                "metadata": {
                    "executor": "forge_apply_segment_delta",
                    "group_key": "forge_apply_segment_delta:updated_segment_name",
                    "host_resolve_schema_version": 3,
                    "sequence_id_policy": "flame_sequence_name",
                    "source_delta_sequence_id": "sequence-stable",
                },
                "changes": [_entry()],
            }
        ],
    }


def _manifest() -> dict:
    return {
        "type": "mutation_plan",
        "intent_parameters": {
            "sequence_name": "FORGE_UAT_HOST_APPLY_20260624"
        },
        "resolved_plan": [
            {
                "identity": copy.deepcopy(_entry()["metadata"]),
                "payload": {"shot_name": "shot-010__FORGE_UAT_PROPOSED"},
            }
        ],
        "originating_capability": "forge_apply_segment_delta",
        "apply_counterpart": {
            "tool": "forge_apply_segment_delta",
            "parameter_overrides": {"mode": "apply"},
        },
    }


@pytest.mark.asyncio
async def test_preview_graph_routes_whole_edit_state_to_held_manifest() -> None:
    plan = _step_plan()
    authorization = _capability_data(mode="apply", step_plan=plan)
    graph = build_live_flame_rename_preview_spec(
        sequence_name="FORGE_UAT_HOST_APPLY_20260624",
        step_plan=plan,
        capability_authorization=authorization,
    )
    edit_state = {"project": {"id": "project-1"}, "session": {"active": True}}
    operation_calls: list[tuple[str, dict]] = []

    async def run_operation(operation_type: str, **kwargs):
        params = copy.deepcopy(kwargs["params"])
        operation_calls.append((operation_type, params))
        if operation_type == "flame.editorial.read_edit_state":
            return {"status": "succeeded", "data": copy.deepcopy(edit_state)}
        if operation_type == "traffik.editorial.apply_steps":
            assert params["state"] == edit_state
            assert params["step_plan"] == plan
            return {"status": "succeeded", "data": {"deltas": [_delta()]}}
        if operation_type == "traffik.flame_delta.host_resolve":
            assert params == {"delta": _delta()}
            return {
                "status": "succeeded",
                "data": {
                    "flame_delta_host_resolve_payload": _host_payload(),
                },
            }
        raise AssertionError(operation_type)

    async def run_discover(tool_name: str, *, request: dict):
        assert tool_name == "forge_apply_segment_delta"
        assert request["sequence_name"] == "FORGE_UAT_HOST_APPLY_20260624"
        return _manifest()

    dispatch = UnifiedDispatch(
        operation_boundary=OperationDispatchBoundary(
            run_operation=run_operation
        ),
        host_resolve_boundary=HostResolveBoundary(run_discover=run_discover),
    )
    results = await GraphExecutor(dispatch.dispatch).run(graph)

    assert all(result.status == "ok" for result in results.values())
    assert [call[0] for call in operation_calls] == [
        "flame.editorial.read_edit_state",
        "traffik.editorial.apply_steps",
        "traffik.flame_delta.host_resolve",
    ]
    assert results["read_edit_state"].output == edit_state
    assert results["select_delta"].output == _delta()
    assert results["delta_to_manifest"].output == _manifest()
