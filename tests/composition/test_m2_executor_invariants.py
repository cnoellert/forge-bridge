from __future__ import annotations

import subprocess
import uuid
from pathlib import Path

import pytest

from forge_bridge.composition.executor import GraphExecutor
from forge_bridge.composition.graph_spec import Edge, GraphSpec, NodeSpec
from forge_bridge.composition.node_result import NodeResult
from forge_bridge.graph.ports import PortContract


def test_graph_executor_has_no_assent_conduit():
    executor_source = (
        Path(__file__).parents[2] / "forge_bridge" / "composition" / "executor.py"
    ).read_text()

    forbidden = ("AssentRecord", "assent_record", "ratified", "ratification")
    for token in forbidden:
        assert token not in executor_source


def test_graph_executor_matches_main_byte_for_byte():
    executor_path = "forge_bridge/composition/executor.py"
    local = (Path(__file__).parents[2] / executor_path).read_bytes()
    main = subprocess.run(
        ["git", "show", f"main:{executor_path}"],
        check=True,
        capture_output=True,
    ).stdout

    assert local == main


@pytest.mark.asyncio
async def test_graph_executor_natively_resolves_five_incoming_edges():
    sources = tuple(NodeSpec(node_id=f"source_{i}", operator_id="source") for i in range(5))
    merge = NodeSpec(
        node_id="merge",
        operator_id="forge_assemble_deliverable_package",
        input_ports={f"in{i}": PortContract.any() for i in range(5)},
    )
    graph = GraphSpec(
        nodes=(*sources, merge),
        edges=tuple(Edge(from_node=f"source_{i}", to_node="merge", to_port=f"in{i}") for i in range(5)),
    )
    seen: dict[str, tuple[str, ...]] = {}

    async def dispatch(node: NodeSpec, resolved):
        seen[node.node_id] = tuple(sorted(resolved))
        return NodeResult(status="ok", run_id=uuid.uuid4())

    await GraphExecutor(dispatch).run(graph)

    assert seen["merge"] == ("in0", "in1", "in2", "in3", "in4")
