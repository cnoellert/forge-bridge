from __future__ import annotations

import time
import uuid
from dataclasses import replace
from types import SimpleNamespace

import pytest

from forge_bridge.composition.boundary import MCPToolBoundary
from forge_bridge.composition.compare import (
    AbortOnFirstErrorDispatch,
    admitted_records_for,
    compare_idempotent_paths,
    compare_strategy_for,
    normalize_graph_results,
)
from forge_bridge.composition.dispatch import UnifiedDispatch
from forge_bridge.composition.executor import GraphExecutor
from forge_bridge.composition.graph_spec import Edge, GraphSpec, NodeSpec
from forge_bridge.composition.node_result import NodeResult
from forge_bridge.composition.primitive_boundary import PrimitiveBoundary
from forge_bridge.console._engine import run_chain_steps
from forge_bridge.graph.ports import PortContract, PortTopology


def _tool(name: str, properties: dict, required: list[str]):
    return SimpleNamespace(
        name=name,
        annotations=SimpleNamespace(readOnlyHint=True),
        inputSchema={
            "$defs": {
                "Input": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                }
            },
            "type": "object",
            "properties": {"params": {"$ref": "#/$defs/Input"}},
            "required": ["params"],
        },
    )


class _FakeMCP:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def list_tools(self):
        return _tools()

    async def call_tool(self, name: str, arguments: dict):
        self.calls.append((name, arguments))
        if name == "forge_is_greenscreen":
            return {
                "shots": [
                    {"id": "gs_010", "is_greenscreen": True},
                    {"id": "amb_030", "is_greenscreen": False},
                ],
                "count": 2,
            }
        if name == "forge_roto_ref":
            return {
                "shot_id": "gs_010",
                "artifact_refs": [{
                    "artifact_type": "DerivedHoldoutsArtifact",
                    "locator": "mock://gs_010_matte.exr",
                    "payload_id": "payload-gs-010",
                }],
            }
        raise AssertionError(name)


def _tools() -> list:
    return [
        _tool(
            "forge_is_greenscreen",
            {
                "shot_id": {"type": "string"},
                "clip_ref": {"type": "string"},
            },
            ["shot_id", "clip_ref"],
        ),
        _tool(
            "forge_roto_ref",
            {
                "shot_id": {"type": "string"},
                "clip_ref": {"type": "string"},
            },
            ["shot_id", "clip_ref"],
        ),
    ]


def _greenscreen_graph() -> GraphSpec:
    return GraphSpec(
        nodes=(
            NodeSpec(
                node_id="greenscreen",
                operator_id="forge_is_greenscreen",
                output_port=PortTopology.list_of("shot"),
                config={
                    "arguments": {
                        "shot_id": "batch",
                        "clip_ref": "mock://batch.mov",
                    }
                },
            ),
            NodeSpec(
                node_id="route_greenscreen",
                operator_id="filter",
                input_ports={"input": PortContract.any()},
                output_port=PortTopology.list_of("shot"),
                config={
                    "predicate": {
                        "field": "is_greenscreen",
                        "operator": "==",
                        "value": True,
                    }
                },
            ),
            NodeSpec(
                node_id="roto",
                operator_id="forge_roto_ref",
                input_ports={"input": PortContract.any()},
                config={
                    "arguments": {
                        "shot_id": "gs_010",
                        "clip_ref": "mock://gs_010.mov",
                    }
                },
            ),
        ),
        edges=(
            Edge(from_node="greenscreen", to_node="route_greenscreen", to_port="input"),
            Edge(from_node="route_greenscreen", to_node="roto", to_port="input"),
        ),
    )


@pytest.mark.asyncio
async def test_compare_harness_proves_greenscreen_filter_roto_vertical_equal():
    legacy_mcp = _FakeMCP()
    graph_mcp = _FakeMCP()
    graph = _greenscreen_graph()

    async def legacy_runner():
        return await run_chain_steps(
            steps=[
                "forge_is_greenscreen shot_id=batch clip_ref=mock://batch.mov",
                "filter(is_greenscreen == true)",
                "forge_roto_ref shot_id=gs_010 clip_ref=mock://gs_010.mov",
            ],
            tools=_tools(),
            mcp=legacy_mcp,
            request_id="req-compare",
            client_ip="127.0.0.1",
            started=time.monotonic(),
        )

    result = await compare_idempotent_paths(
        legacy_runner=legacy_runner,
        graph=graph,
        dispatch=UnifiedDispatch(
            mcp_boundary=MCPToolBoundary(mcp=graph_mcp),
            primitive_boundary=PrimitiveBoundary(),
        ).dispatch,
        terminal_node_id="roto",
        expected_steps=3,
    )

    assert result.equivalent
    assert result.graph.status_vector == ("ok", "ok", "ok")
    assert result.graph.terminal_output["artifact_refs"][0]["locator"].endswith(".exr")


@pytest.mark.asyncio
async def test_abort_wrapper_skips_downstream_dispatch_after_error():
    calls: list[str] = []

    async def dispatch(node: NodeSpec, _resolved):
        calls.append(node.node_id)
        status = "error" if node.node_id == "source" else "ok"
        return NodeResult(status=status, run_id=uuid.uuid4())

    graph = GraphSpec(
        nodes=(
            NodeSpec(node_id="source", operator_id="forge_is_greenscreen"),
            NodeSpec(
                node_id="downstream",
                operator_id="forge_roto_ref",
                input_ports={"input": PortContract.any()},
            ),
        ),
        edges=(Edge(from_node="source", to_node="downstream", to_port="input"),),
    )
    wrapper = AbortOnFirstErrorDispatch(dispatch)
    results = await GraphExecutor(wrapper.dispatch).run(graph)

    assert calls == ["source"]
    assert wrapper.skipped_node_ids == ["downstream"]
    assert normalize_graph_results(results, terminal_node_id="downstream").status_vector == (
        "error",
        "skipped",
    )


def test_compare_strategy_routes_idempotent_vs_record_replay():
    records = admitted_records_for(_greenscreen_graph())
    assert compare_strategy_for(records) == "double_exec"

    non_idempotent = replace(records[0], idempotent=False)
    assert compare_strategy_for((non_idempotent, *records[1:])) == "record_replay"
