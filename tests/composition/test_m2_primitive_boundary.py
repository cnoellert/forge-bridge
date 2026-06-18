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
