"""Production entrypoint for running composition ``GraphSpec`` objects.

This is intentionally narrow: direct callers and the CLI use this function,
while chat/apply production paths stay on their existing rails until the
corpus-gated cutover. The graph runtime composes here through injected
boundaries; ``GraphExecutor`` remains the pure scheduling floor.
"""
from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import asdict
from pathlib import Path
from typing import Any

from forge_bridge.composition.dispatch import UnifiedDispatch
from forge_bridge.composition.executor import GraphExecutor
from forge_bridge.composition.graph_spec import Edge, GraphSpec, NodeSpec
from forge_bridge.composition.node_result import NodeResult
from forge_bridge.composition.operation_boundary import OperationDispatchBoundary
from forge_bridge.graph.ports import PortContract, PortTopology
from forge_bridge.orchestration.operation_runner import build_operation_runner


async def run_graph(
    spec: GraphSpec,
    *,
    registry: Any | None = None,
    receipt_dir: str | Path | None = None,
) -> dict[str, NodeResult]:
    """Run ``spec`` through the production composition dispatch spine."""

    runner = build_operation_runner(registry, receipt_dir=receipt_dir)
    dispatch = UnifiedDispatch(
        operation_boundary=OperationDispatchBoundary(run_operation=runner),
    )
    return await GraphExecutor(dispatch.dispatch).run(spec)


def graph_spec_from_dict(data: Mapping[str, Any]) -> GraphSpec:
    """Decode the CLI JSON representation into a ``GraphSpec``."""

    nodes = tuple(_node_spec_from_dict(item) for item in data.get("nodes", ()))
    edges = tuple(_edge_from_dict(item) for item in data.get("edges", ()))
    return GraphSpec(nodes=nodes, edges=edges)


def node_results_to_dict(results: Mapping[str, NodeResult]) -> dict[str, Any]:
    """Return a JSON-serializable result map for CLI/API-style renderers."""

    return {node_id: _jsonable(asdict(result)) for node_id, result in results.items()}


def _node_spec_from_dict(data: Mapping[str, Any]) -> NodeSpec:
    return NodeSpec(
        node_id=str(data["node_id"]),
        operator_id=str(data["operator_id"]),
        input_ports={
            str(name): _port_contract_from_dict(value)
            for name, value in (data.get("input_ports") or {}).items()
        },
        output_port=_port_topology_from_dict(data.get("output_port")),
        backend_id=(
            str(data["backend_id"])
            if data.get("backend_id") is not None
            else None
        ),
        config=dict(data.get("config") or {}),
    )


def _edge_from_dict(data: Mapping[str, Any]) -> Edge:
    return Edge(
        from_node=str(data["from_node"]),
        to_node=str(data["to_node"]),
        to_port=str(data["to_port"]),
        from_port=str(data.get("from_port", "out")),
    )


def _port_contract_from_dict(data: Any) -> PortContract:
    if not isinstance(data, Mapping):
        return PortContract.any()
    accepts = tuple(
        _port_topology_from_dict(item)
        for item in data.get("accepts", ())
    )
    return PortContract(
        accepts=accepts or (PortTopology.any(),),
        emits=_port_topology_from_dict(data.get("emits")),
    )


def _port_topology_from_dict(data: Any) -> PortTopology:
    if not isinstance(data, Mapping):
        return PortTopology.any()
    return PortTopology.from_dict(dict(data))


def _jsonable(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_jsonable(item) for item in value]
    return value


__all__ = [
    "graph_spec_from_dict",
    "node_results_to_dict",
    "run_graph",
]
