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

