from __future__ import annotations

import json
import uuid
from types import SimpleNamespace

import pytest

from forge_bridge.composition.boundary import (
    MCPToolBoundary,
    UnsupportedCompositionNodeError,
)
from forge_bridge.composition.executor import GraphExecutor
from forge_bridge.composition.graph_spec import Edge, GraphSpec, NodeSpec
from forge_bridge.graph.ports import PortContract, PortTopology


class _FakeMCP:
    def __init__(self, payloads: list[dict]):
        self._payloads = list(payloads)
        self.calls: list[tuple[str, dict]] = []

    async def call_tool(self, name: str, arguments: dict):
        self.calls.append((name, arguments))
        payload = self._payloads.pop(0)
        return SimpleNamespace(
            structuredContent={"result": json.dumps(payload)},
            content=[],
        )


def _ids():
    values = iter([
        uuid.UUID("00000000-0000-0000-0000-000000000001"),
        uuid.UUID("00000000-0000-0000-0000-000000000002"),
    ])
    return lambda: next(values)


def _greenscreen_node(
    node_id: str,
    *,
    input_ports: dict[str, PortContract] | None = None,
) -> NodeSpec:
    return NodeSpec(
        node_id=node_id,
        operator_id="forge_is_greenscreen",
        input_ports=input_ports or {},
        output_port=PortTopology.any(),
        config={
            "arguments": {
                "shot_id": node_id,
                "clip_ref": f"mock://perception/is_greenscreen/{node_id}_true",
            },
        },
    )


def test_mcp_boundary_runs_vision_node_and_records_lineage_through_any_edge():
    fake = _FakeMCP([
        {"is_greenscreen": True, "recommendation": "route"},
        {"is_greenscreen": True, "recommendation": "route"},
    ])
    source = _greenscreen_node("gs_010")
    consumer = _greenscreen_node(
        "gs_020",
        input_ports={"previous": PortContract.any()},
    )
    graph = GraphSpec(
        nodes=(source, consumer),
        edges=(Edge(from_node="gs_010", to_node="gs_020", to_port="previous"),),
    )
    boundary = MCPToolBoundary(
        mcp=fake,
        run_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        artifact_id_factory=_ids(),
    )

    results = GraphExecutor(boundary.dispatch).run(graph)

    assert results["gs_010"].status == "ok"
    assert results["gs_020"].status == "ok"
    assert results["gs_020"].source_artifact_ids == (
        uuid.UUID("00000000-0000-0000-0000-000000000001"),
    )
    assert fake.calls == [
        (
            "forge_is_greenscreen",
            {
                "shot_id": "gs_010",
                "clip_ref": "mock://perception/is_greenscreen/gs_010_true",
            },
        ),
        (
            "forge_is_greenscreen",
            {
                "shot_id": "gs_020",
                "clip_ref": "mock://perception/is_greenscreen/gs_020_true",
            },
        ),
    ]


def test_mcp_boundary_maps_structured_abstention_to_node_result():
    fake = _FakeMCP([{
        "artifact": {"abstention_reason": "mock_abstain"},
        "verdict": "inconclusive",
        "recommendation": "abstained on greenscreen question",
    }])
    boundary = MCPToolBoundary(
        mcp=fake,
        run_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        artifact_id_factory=_ids(),
    )

    result = boundary.dispatch(_greenscreen_node("amb_030"), {})

    assert result.status == "abstained"
    assert result.has_usable_output is False
    assert result.output is None
    assert result.reason_code == "mock_abstain"
    assert result.message == "abstained on greenscreen question"


def test_mcp_boundary_rejects_generation_nodes_before_dispatch():
    fake = _FakeMCP([{"ok": True}])
    boundary = MCPToolBoundary(mcp=fake)
    node = NodeSpec(node_id="make", operator_id="forge_generate_image")

    with pytest.raises(UnsupportedCompositionNodeError):
        boundary.dispatch(node, {})

    assert fake.calls == []
