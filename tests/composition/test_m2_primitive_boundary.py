from __future__ import annotations

import uuid

import pytest

from forge_bridge.composition.graph_spec import NodeSpec
from forge_bridge.composition.node_result import NodeResult
from forge_bridge.composition.primitive_boundary import PrimitiveBoundary


def _ok_collection() -> NodeResult:
    return NodeResult(
        status="ok",
        run_id=uuid.uuid4(),
        artifact_id=uuid.uuid4(),
        output={
            "shots": [
                {"id": "gs_010", "is_greenscreen": True},
                {"id": "amb_030", "is_greenscreen": False},
            ],
            "count": 2,
        },
    )


def _ok_manifest(*, changes: bool) -> NodeResult:
    return NodeResult(
        status="ok",
        run_id=uuid.uuid4(),
        artifact_id=uuid.uuid4(),
        output={
            "type": "mutation_plan",
            "proposed_changes": [{"id": "a"}] if changes else [],
        },
    )


def _apply_steps_output() -> NodeResult:
    return NodeResult(
        status="ok",
        run_id=uuid.uuid4(),
        artifact_id=uuid.uuid4(),
        output={
            "deltas": [
                {
                    "type": "timeline_delta",
                    "sequence_id": "seq_001",
                    "changes": [
                        {
                            "action": "updated",
                            "object_type": "segment",
                            "object_id": "seg-001",
                        }
                    ],
                },
                {
                    "type": "timeline_delta",
                    "sequence_id": "seq_002",
                    "changes": [],
                },
            ]
        },
    )


@pytest.mark.asyncio
async def test_filter_primitive_consumes_upstream_output_as_data():
    node = NodeSpec(
        node_id="filter#1",
        operator_id="filter",
        config={
            "predicate": {
                "field": "is_greenscreen",
                "operator": "==",
                "value": True,
            }
        },
    )

    result = await PrimitiveBoundary().dispatch(node, {"input": _ok_collection()})

    assert result.status == "ok"
    assert result.resolved_class == "primitive.filter"
    assert result.output["count"] == 1
    assert result.output["shots"] == [{"id": "gs_010", "is_greenscreen": True}]
    assert result.output["filter"]["output_count"] == 1


@pytest.mark.asyncio
async def test_filter_primitive_rejects_missing_upstream_data():
    node = NodeSpec(node_id="filter#1", operator_id="filter", config={
        "predicate": {"field": "is_greenscreen", "operator": "==", "value": True}
    })

    result = await PrimitiveBoundary().dispatch(node, {})

    assert result.status == "error"
    assert result.reason_code == "invalid_primitive_input"
    assert result.resolved_class == "primitive.filter"


@pytest.mark.asyncio
async def test_filter_primitive_reports_predicate_errors():
    node = NodeSpec(node_id="filter#1", operator_id="filter", config={})

    result = await PrimitiveBoundary().dispatch(node, {"input": _ok_collection()})

    assert result.status == "error"
    assert result.reason_code == "missing_predicate"
    assert result.resolved_class == "primitive.filter"


@pytest.mark.asyncio
async def test_if_gate_primitive_open_runs_ok_without_control_signal():
    node = NodeSpec(
        node_id="if#1",
        operator_id="if",
        config={"step_text": "if(proposed_changes exists)"},
    )

    result = await PrimitiveBoundary().dispatch(
        node,
        {"input": _ok_manifest(changes=True)},
    )

    assert result.status == "ok"
    assert result.control_signal is None
    assert result.resolved_class == "primitive.if_gate"
    assert result.output["execution_state"] == "passed"


@pytest.mark.asyncio
async def test_if_gate_primitive_closed_runs_ok_and_signals_skip():
    upstream = _ok_manifest(changes=False)
    node = NodeSpec(
        node_id="if#1",
        operator_id="if",
        config={"predicate": {
            "field": "proposed_changes",
            "operator": "exists",
        }},
    )

    result = await PrimitiveBoundary().dispatch(node, {"input": upstream})

    assert result.status == "ok"
    assert result.has_usable_output is True
    assert result.control_signal == "skip"
    assert result.output["execution_state"] == "skipped"
    assert result.artifact_id is not None
    assert result.source_artifact_ids == (upstream.artifact_id,)


@pytest.mark.asyncio
async def test_select_delta_extracts_default_timeline_delta():
    upstream = _apply_steps_output()
    node = NodeSpec(node_id="select_delta", operator_id="select_delta")

    result = await PrimitiveBoundary().dispatch(node, {"result": upstream})

    assert result.status == "ok"
    assert result.resolved_class == "primitive.select_delta"
    assert result.output == upstream.output["deltas"][0]
    assert result.output_topology == {"kind": "manifest"}
    assert result.artifact_type == "manifest"
    assert result.source_artifact_ids == (upstream.artifact_id,)


@pytest.mark.asyncio
async def test_select_delta_extracts_configured_index():
    upstream = _apply_steps_output()
    node = NodeSpec(
        node_id="select_delta",
        operator_id="select_delta",
        config={"index": 1},
    )

    result = await PrimitiveBoundary().dispatch(node, {"result": upstream})

    assert result.status == "ok"
    assert result.output == upstream.output["deltas"][1]


@pytest.mark.asyncio
async def test_select_delta_rejects_missing_deltas():
    node = NodeSpec(node_id="select_delta", operator_id="select_delta")
    upstream = NodeResult(
        status="ok",
        run_id=uuid.uuid4(),
        artifact_id=uuid.uuid4(),
        output={"state": {}},
    )

    result = await PrimitiveBoundary().dispatch(node, {"result": upstream})

    assert result.status == "error"
    assert result.reason_code == "missing_delta"
    assert result.resolved_class == "primitive.select_delta"


@pytest.mark.asyncio
async def test_select_delta_rejects_bad_index():
    node = NodeSpec(
        node_id="select_delta",
        operator_id="select_delta",
        config={"index": True},
    )

    result = await PrimitiveBoundary().dispatch(node, {"result": _apply_steps_output()})

    assert result.status == "error"
    assert result.reason_code == "invalid_delta_selection"
