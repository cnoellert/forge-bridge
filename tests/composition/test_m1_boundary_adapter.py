from __future__ import annotations

import json
import uuid
from types import SimpleNamespace

import pytest

from forge_bridge.composition.boundary import (
    MCPToolBoundary,
    UnsupportedCompositionNodeError,
)
from forge_bridge.composition.compiler import compile_operator_sequence
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


class _ListedFakeMCP(_FakeMCP):
    async def list_tools(self):
        return [
            SimpleNamespace(name="forge_is_greenscreen", inputSchema=None),
        ]


class _GreenscreenRequiredFakeMCP:
    """Tiny schema-faithful fake: forge_is_greenscreen requires shot_id+clip_ref."""

    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    async def call_tool(self, name: str, arguments: dict):
        self.calls.append((name, arguments))
        missing = [
            key for key in ("shot_id", "clip_ref")
            if key not in arguments
        ]
        if missing:
            payload = {
                "error": {
                    "type": "missing_required_argument",
                    "message": f"Missing required argument: {missing[0]}",
                }
            }
        else:
            payload = {"is_greenscreen": True, "recommendation": "route"}
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


async def test_mcp_boundary_runs_vision_node_and_records_lineage_through_any_edge():
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

    results = await GraphExecutor(boundary.dispatch).run(graph)

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


async def test_mcp_boundary_dispatches_inside_running_event_loop():
    fake = _ListedFakeMCP([
        {"is_greenscreen": True, "recommendation": "route"},
    ])
    boundary = MCPToolBoundary(mcp=fake, artifact_id_factory=_ids())

    result = await boundary.dispatch(_greenscreen_node("gs_010"), {})

    assert result.status == "ok"
    assert fake.calls == [
        (
            "forge_is_greenscreen",
            {
                "shot_id": "gs_010",
                "clip_ref": "mock://perception/is_greenscreen/gs_010_true",
            },
        )
    ]


async def test_mcp_boundary_maps_structured_abstention_to_node_result():
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

    result = await boundary.dispatch(_greenscreen_node("amb_030"), {})

    assert result.status == "abstained"
    assert result.has_usable_output is False
    assert result.output is None
    assert result.reason_code == "mock_abstain"
    assert result.message == "abstained on greenscreen question"


async def test_mcp_boundary_rejects_generation_nodes_before_dispatch():
    fake = _FakeMCP([{"ok": True}])
    boundary = MCPToolBoundary(mcp=fake)
    node = NodeSpec(node_id="make", operator_id="forge_generate_image")

    with pytest.raises(UnsupportedCompositionNodeError):
        await boundary.dispatch(node, {})

    assert fake.calls == []


async def test_mcp_boundary_null_error_field_is_not_error_status():
    # A success envelope carrying a null/empty `error` slot must map to ok —
    # the status check is truthy, not key-presence (latent landmine for the
    # next admitted operator). Pins boundary.py:_status_for_payload.
    fake = _FakeMCP([{"is_greenscreen": True, "verdict": "pass", "error": None}])
    boundary = MCPToolBoundary(mcp=fake, artifact_id_factory=_ids())

    result = await boundary.dispatch(_greenscreen_node("gs_010"), {})

    assert result.status == "ok"
    assert result.output["is_greenscreen"] is True


async def test_compiled_plan_scalars_lower_to_tool_kwargs():
    graph = compile_operator_sequence([{
        "operator_id": "forge_is_greenscreen",
        "inputs": [{
            "artifact_id": "plate:gs_010",
            "artifact_type": "plate",
            "metadata": {
                "role": "source_plate",
                "scalars": {
                    "shot_id": "gs_010",
                    "clip_ref": "mock://perception/is_greenscreen/gs_010_true",
                },
            },
        }],
        "output_artifact_id": "greenscreen-assessment:gs_010",
    }])
    fake = _GreenscreenRequiredFakeMCP()
    boundary = MCPToolBoundary(mcp=fake, artifact_id_factory=_ids())

    results = await GraphExecutor(boundary.dispatch).run(graph)

    assert results["forge_is_greenscreen#0"].status == "ok"
    assert fake.calls == [
        (
            "forge_is_greenscreen",
            {
                "shot_id": "gs_010",
                "clip_ref": "mock://perception/is_greenscreen/gs_010_true",
            },
        )
    ]


async def test_compiled_plan_missing_required_kwarg_is_not_invented():
    graph = compile_operator_sequence([{
        "operator_id": "forge_is_greenscreen",
        "inputs": [{
            "artifact_id": "plate:gs_010",
            "artifact_type": "plate",
            "metadata": {
                "role": "source_plate",
                "scalars": {"shot_id": "gs_010"},
            },
        }],
        "output_artifact_id": "greenscreen-assessment:gs_010",
    }])
    fake = _GreenscreenRequiredFakeMCP()
    boundary = MCPToolBoundary(mcp=fake, artifact_id_factory=_ids())

    results = await GraphExecutor(boundary.dispatch).run(graph)

    assert fake.calls == [("forge_is_greenscreen", {"shot_id": "gs_010"})]
    result = results["forge_is_greenscreen#0"]
    assert result.status == "error"
    assert result.reason_code == "missing_required_argument"
    assert result.message == "Missing required argument: clip_ref"


async def test_edge_fed_node_does_not_extract_kwargs_from_upstream_output():
    # M1 edges are value-blind: resolved_inputs contributes lineage only.
    # Identity-param-vs-scalar binding is deliberately unbound pending #86.
    graph = compile_operator_sequence([
        {
            "operator_id": "forge_is_greenscreen",
            "inputs": [{
                "artifact_id": "plate:source",
                "artifact_type": "plate",
                "metadata": {
                    "scalars": {
                        "shot_id": "source",
                        "clip_ref": "mock://perception/is_greenscreen/source_true",
                    },
                },
            }],
            "output_artifact_id": "assessment:source",
        },
        {
            "operator_id": "forge_is_greenscreen",
            "inputs": [
                {
                    "artifact_id": "assessment:source",
                    "artifact_type": "IsGreenscreenAssessment",
                    "metadata": {"role": "previous_assessment"},
                },
                {
                    "artifact_id": "plate:target",
                    "artifact_type": "plate",
                    "metadata": {"scalars": {"shot_id": "target"}},
                },
            ],
            "output_artifact_id": "assessment:target",
        },
    ])
    fake = _GreenscreenRequiredFakeMCP()
    boundary = MCPToolBoundary(mcp=fake, artifact_id_factory=_ids())

    results = await GraphExecutor(boundary.dispatch).run(graph)

    assert fake.calls == [
        (
            "forge_is_greenscreen",
            {
                "shot_id": "source",
                "clip_ref": "mock://perception/is_greenscreen/source_true",
            },
        ),
        ("forge_is_greenscreen", {"shot_id": "target"}),
    ]
    target = results["forge_is_greenscreen#1"]
    assert target.status == "error"
    assert target.source_artifact_ids == (
        results["forge_is_greenscreen#0"].artifact_id,
    )
