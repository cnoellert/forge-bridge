"""Proof for two-pass exact Flame editorial realization wiring."""

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
    EDITORIAL_APPLY_STEPS_OPERATION_TYPE,
    EDITORIAL_STEP_CAPABILITIES_OPERATION_TYPE,
    FLAME_DELTA_HOST_RESOLVE_OPERATION_TYPE,
    FLAME_EDITORIAL_DELTA_REALIZATION_OPERATION_TYPE,
    LIVE_FLAME_READ_OPERATION_TYPE,
    LiveEditorialVerticalError,
    build_live_flame_realization_preview_spec,
    discover_live_flame_realization,
)


def _fingerprint(value: dict) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _step_plan() -> dict:
    return {
        "kind": "traffik.editorial_step_plan",
        "schema_version": 1,
        "plan_id": "phase115-trim",
        "operation_type": EDITORIAL_APPLY_STEPS_OPERATION_TYPE,
        "status": "ok",
        "steps": [
            {
                "operation": "trim_tail",
                "step_id": "trim-tail",
                "node_id": "trim-tail-node",
                "params": {
                    "sequence_id": "sequence-stable",
                    "track_id": "track-stable",
                    "segment_id": "segment-stable",
                    "new_frame_out": {
                        "number": 123,
                        "rate": {"numerator": 24, "denominator": 1},
                    },
                },
            }
        ],
    }


def _semantic_data() -> dict:
    source_fingerprint = _fingerprint(_step_plan())
    plan_fingerprint = "semantic-plan-fingerprint"
    return {
        "kind": "traffik.editorial_step_capability_result",
        "schema_version": 1,
        "operation_type": EDITORIAL_STEP_CAPABILITIES_OPERATION_TYPE,
        "mode": "discover",
        "status": "blocked",
        "trust_status": "review_required",
        "allowed": False,
        "dispatch_authorized": False,
        "drift": False,
        "read_only": True,
        "mutation_safe": True,
        "step_plan_fingerprint": source_fingerprint,
        "matrix_fingerprint": "matrix-fingerprint",
        "capability_plan_fingerprint": plan_fingerprint,
        "capability_plan": {
            "kind": "traffik.editorial.step_capability_plan",
            "schema_version": 1,
            "target_plugin": "flame",
            "host_mode": "flame",
            "source_step_plan_fingerprint": source_fingerprint,
            "allowed": False,
            "trust_status": "review_required",
            "fingerprint": plan_fingerprint,
        },
    }


def _entry() -> dict:
    return {
        "action": "updated",
        "object_type": "segment",
        "object_id": "segment-stable",
        "before": {"frame_out": 124},
        "after": {"frame_out": 123},
        "metadata": {
            "sequence_name": "FORGE_UAT_HOST_APPLY_20260624",
            "track_idx": 0,
            "record_in": "01:00:00:00",
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


def _apply_result() -> dict:
    return {
        "final_state": {"project": {"id": "project-1"}, "session": {}},
        "steps": [
            {
                "operation": "trim_tail",
                "step_id": "trim-tail",
                "node_id": "trim-tail-node",
                "status": "ok",
                "delta": _delta(),
            }
        ],
        "deltas": [_delta()],
        "stopped_at": None,
        "step_plan_result": {
            "kind": "traffik.editorial_step_plan_result",
            "schema_version": 1,
            "plan_id": "phase115-trim",
            "operation_type": EDITORIAL_APPLY_STEPS_OPERATION_TYPE,
            "status": "ok",
            "step_count": 1,
            "stopped_at": None,
        },
    }


def _realization_data() -> dict:
    source_fingerprint = _fingerprint(_step_plan())
    delta_fingerprint = _fingerprint(_delta())
    plan_fingerprint = "realization-plan-fingerprint"
    return {
        "kind": "flame.editorial.delta_realization_result",
        "schema_version": 1,
        "operation_type": FLAME_EDITORIAL_DELTA_REALIZATION_OPERATION_TYPE,
        "mode": "discover",
        "status": "ready",
        "trust_status": "trusted",
        "allowed": True,
        "dispatch_authorized": False,
        "drift": False,
        "read_only": True,
        "mutation_safe": True,
        "semantic_authority": "traffik",
        "realization_authority": "forge_flame",
        "composition_owner": "bridge",
        "step_plan_fingerprint": source_fingerprint,
        "semantic_capability_plan_fingerprint": "semantic-plan-fingerprint",
        "apply_result_fingerprint": _fingerprint(_apply_result()),
        "delta_fingerprint": delta_fingerprint,
        "lowerer_contract_fingerprint": "lowerer-contract-fingerprint",
        "realization_plan_fingerprint": plan_fingerprint,
        "realization_plan": {
            "kind": "flame.editorial.delta_realization_plan",
            "schema_version": 1,
            "fingerprint": plan_fingerprint,
            "delta_fingerprint": delta_fingerprint,
            "executor": "forge_apply_segment_temporal_delta",
            "delta": _delta(),
        },
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
                    "executor": "forge_apply_segment_temporal_delta",
                    "group_key": (
                        "forge_apply_segment_temporal_delta:updated_segment_trim"
                    ),
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
                "payload": {"new_frame_out": 123},
            }
        ],
        "originating_capability": "forge_apply_segment_temporal_delta",
        "apply_counterpart": {
            "tool": "forge_apply_segment_temporal_delta",
            "parameter_overrides": {"mode": "apply"},
        },
    }


@pytest.mark.asyncio
async def test_discovery_holds_blocked_semantics_and_trusted_exact_delta() -> None:
    calls: list[tuple[str, dict]] = []
    edit_state = {"project": {"id": "project-1"}, "session": {}}

    async def run_operation(operation_type: str, **kwargs):
        calls.append((operation_type, copy.deepcopy(kwargs)))
        if operation_type == EDITORIAL_STEP_CAPABILITIES_OPERATION_TYPE:
            return {"status": "succeeded", "data": _semantic_data()}
        if operation_type == LIVE_FLAME_READ_OPERATION_TYPE:
            return {"status": "succeeded", "data": edit_state}
        if operation_type == EDITORIAL_APPLY_STEPS_OPERATION_TYPE:
            assert kwargs["params"]["state"] == edit_state
            return {"status": "succeeded", "data": _apply_result()}
        if operation_type == FLAME_EDITORIAL_DELTA_REALIZATION_OPERATION_TYPE:
            assert kwargs["params"]["semantic_capability_plan"] == (
                _semantic_data()["capability_plan"]
            )
            assert kwargs["params"]["apply_result"] == _apply_result()
            return {"status": "succeeded", "data": _realization_data()}
        raise AssertionError(operation_type)

    discovery = await discover_live_flame_realization(
        _step_plan(),
        sequence_name="FORGE_UAT_HOST_APPLY_20260624",
        reel_names=["Testing"],
        project_id="project-1",
        authorization_id="phase115-test",
        run_operation=run_operation,
    )

    assert discovery["status"] == "ready"
    assert discovery["trust_status"] == "trusted"
    assert discovery["dispatch_authorized"] is False
    assert discovery["semantic_discovery"]["allowed"] is False
    assert discovery["realization_discovery"]["allowed"] is True
    assert [call[0] for call in calls] == [
        EDITORIAL_STEP_CAPABILITIES_OPERATION_TYPE,
        LIVE_FLAME_READ_OPERATION_TYPE,
        EDITORIAL_APPLY_STEPS_OPERATION_TYPE,
        FLAME_EDITORIAL_DELTA_REALIZATION_OPERATION_TYPE,
    ]
    assert [call[1]["idempotency_key"] for call in calls] == [
        "phase115-test:semantic-discover",
        "phase115-test:live-read",
        "phase115-test:apply-steps",
        "phase115-test:realization-discover",
    ]


@pytest.mark.asyncio
async def test_preview_graph_routes_only_reauthorized_exact_delta() -> None:
    async def discovery_runner(operation_type: str, **_kwargs):
        if operation_type == EDITORIAL_STEP_CAPABILITIES_OPERATION_TYPE:
            return {"status": "succeeded", "data": _semantic_data()}
        if operation_type == LIVE_FLAME_READ_OPERATION_TYPE:
            return {
                "status": "succeeded",
                "data": {"project": {"id": "project-1"}, "session": {}},
            }
        if operation_type == EDITORIAL_APPLY_STEPS_OPERATION_TYPE:
            return {"status": "succeeded", "data": _apply_result()}
        if operation_type == FLAME_EDITORIAL_DELTA_REALIZATION_OPERATION_TYPE:
            return {"status": "succeeded", "data": _realization_data()}
        raise AssertionError(operation_type)

    discovery = await discover_live_flame_realization(
        _step_plan(),
        sequence_name="FORGE_UAT_HOST_APPLY_20260624",
        run_operation=discovery_runner,
        authorization_id="phase115-graph",
    )
    graph = build_live_flame_realization_preview_spec(
        sequence_name="FORGE_UAT_HOST_APPLY_20260624",
        reel_names=["Testing"],
        step_plan=_step_plan(),
        realization_discovery=discovery,
    )
    operation_calls: list[tuple[str, dict]] = []

    async def run_operation(operation_type: str, **kwargs):
        params = copy.deepcopy(kwargs["params"])
        operation_calls.append((operation_type, params))
        if operation_type == LIVE_FLAME_READ_OPERATION_TYPE:
            return {
                "status": "succeeded",
                "data": {"project": {"id": "project-1"}, "session": {}},
            }
        if operation_type == EDITORIAL_APPLY_STEPS_OPERATION_TYPE:
            return {"status": "succeeded", "data": _apply_result()}
        if operation_type == FLAME_EDITORIAL_DELTA_REALIZATION_OPERATION_TYPE:
            assert params["mode"] == "apply"
            assert params["apply_result"] == _apply_result()
            assert params["held_realization_plan_fingerprint"] == (
                "realization-plan-fingerprint"
            )
            return {
                "status": "succeeded",
                "data": {**_realization_data(), "mode": "apply", "deltas": [_delta()]},
            }
        if operation_type == FLAME_DELTA_HOST_RESOLVE_OPERATION_TYPE:
            assert params == {"delta": _delta()}
            return {
                "status": "succeeded",
                "data": {"flame_delta_host_resolve_payload": _host_payload()},
            }
        raise AssertionError(operation_type)

    async def run_discover(tool_name: str, *, request: dict):
        assert tool_name == "forge_apply_segment_temporal_delta"
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
    assert [node.node_id for node in graph.nodes] == [
        "read_edit_state",
        "apply_steps",
        "authorize_realization",
        "select_delta",
        "host_resolve",
        "delta_to_manifest",
    ]
    assert [call[0] for call in operation_calls] == [
        LIVE_FLAME_READ_OPERATION_TYPE,
        EDITORIAL_APPLY_STEPS_OPERATION_TYPE,
        FLAME_EDITORIAL_DELTA_REALIZATION_OPERATION_TYPE,
        FLAME_DELTA_HOST_RESOLVE_OPERATION_TYPE,
    ]
    assert results["authorize_realization"].output["deltas"] == [_delta()]
    assert results["select_delta"].output == _delta()
    assert results["delta_to_manifest"].output == _manifest()


@pytest.mark.asyncio
async def test_preview_builder_refuses_tampered_discovery() -> None:
    async def run_operation(operation_type: str, **_kwargs):
        outputs = {
            EDITORIAL_STEP_CAPABILITIES_OPERATION_TYPE: _semantic_data(),
            LIVE_FLAME_READ_OPERATION_TYPE: {
                "project": {"id": "project-1"},
                "session": {},
            },
            EDITORIAL_APPLY_STEPS_OPERATION_TYPE: _apply_result(),
            FLAME_EDITORIAL_DELTA_REALIZATION_OPERATION_TYPE: (
                _realization_data()
            ),
        }
        return {"status": "succeeded", "data": outputs[operation_type]}

    discovery = await discover_live_flame_realization(
        _step_plan(),
        sequence_name="FORGE_UAT_HOST_APPLY_20260624",
        run_operation=run_operation,
        authorization_id="phase115-tamper",
    )
    tampered = copy.deepcopy(discovery)
    tampered["realization_discovery"]["apply_result_fingerprint"] = "drifted"

    with pytest.raises(
        LiveEditorialVerticalError,
        match="fingerprint mismatch",
    ):
        build_live_flame_realization_preview_spec(
            sequence_name="FORGE_UAT_HOST_APPLY_20260624",
            step_plan=_step_plan(),
            realization_discovery=tampered,
        )


@pytest.mark.asyncio
async def test_blocked_position_realization_cannot_mint_trusted_discovery() -> None:
    calls: list[str] = []

    async def run_operation(operation_type: str, **_kwargs):
        calls.append(operation_type)
        if operation_type == EDITORIAL_STEP_CAPABILITIES_OPERATION_TYPE:
            return {"status": "succeeded", "data": _semantic_data()}
        if operation_type == LIVE_FLAME_READ_OPERATION_TYPE:
            return {
                "status": "succeeded",
                "data": {"project": {"id": "project-1"}, "session": {}},
            }
        if operation_type == EDITORIAL_APPLY_STEPS_OPERATION_TYPE:
            return {"status": "succeeded", "data": _apply_result()}
        if operation_type == FLAME_EDITORIAL_DELTA_REALIZATION_OPERATION_TYPE:
            held = _realization_data()
            held.update(
                status="blocked",
                trust_status="review_required",
                allowed=False,
            )
            held["realization_plan"] = {
                **held["realization_plan"],
                "executor": "forge_apply_segment_position_delta",
            }
            return {"status": "succeeded", "data": held}
        raise AssertionError(operation_type)

    with pytest.raises(
        LiveEditorialVerticalError,
        match="exact realization is not trusted",
    ):
        await discover_live_flame_realization(
            _step_plan(),
            sequence_name="FORGE_UAT_HOST_APPLY_20260624",
            run_operation=run_operation,
            authorization_id="phase117-position-hold",
        )

    assert calls == [
        EDITORIAL_STEP_CAPABILITIES_OPERATION_TYPE,
        LIVE_FLAME_READ_OPERATION_TYPE,
        EDITORIAL_APPLY_STEPS_OPERATION_TYPE,
        FLAME_EDITORIAL_DELTA_REALIZATION_OPERATION_TYPE,
    ]
