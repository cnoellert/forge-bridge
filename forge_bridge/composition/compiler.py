"""Compile orchestration ``operator_sequence`` plans into ``GraphSpec``.

M1 Phase 3 keeps the live chain path untouched while making the B2 decision
concrete: a linear chain is a degenerate graph, and ``GraphSpec`` is the IR of
record. The compiler is structural and operator-agnostic; dispatch remains
responsible for deciding whether a node can execute.
"""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from forge_bridge.composition.graph_spec import Edge, GraphSpec, NodeSpec
from forge_bridge.graph.ports import PortContract, PortTopology

_STEP_SCALAR_EXCLUDE = frozenset({"operator_id", "backend_id", "inputs"})
_SAFE_PORT_RE = re.compile(r"[^0-9A-Za-z_]+")


def compile_operator_sequence(
    operator_sequence: Sequence[Mapping[str, Any]],
    *,
    backend_assignments: Mapping[str, str] | None = None,
) -> GraphSpec:
    """Compile a linear orchestration plan into a degenerate ``GraphSpec``.

    Existing execution plans express edges implicitly: one step's
    ``output_artifact_id`` reappears in a later step's ``inputs`` list. This
    pass makes those wires explicit and declares each target input port with a
    permissive ``PortContract.any()`` so the M1 executor's well-formedness
    checks admit faithfully compiled chains.
    """
    assignments = backend_assignments or {}
    node_ids = [_node_id(step, index) for index, step in enumerate(operator_sequence)]
    output_to_node = {
        str(step["output_artifact_id"]): node_id
        for step, node_id in zip(operator_sequence, node_ids)
        if step.get("output_artifact_id") is not None
    }

    nodes: list[NodeSpec] = []
    edges: list[Edge] = []

    for index, step in enumerate(operator_sequence):
        node_id = node_ids[index]
        operator_id = str(step.get("operator_id") or f"operator_{index}")
        input_ports: dict[str, PortContract] = {}
        static_inputs: list[dict[str, Any]] = []
        used_ports: set[str] = set()

        for input_index, raw_input in enumerate(step.get("inputs") or []):
            input_entry = dict(raw_input)
            source_node = output_to_node.get(str(input_entry.get("artifact_id")))
            if source_node is None:
                static_inputs.append(input_entry)
                continue
            port = _derive_port_name(input_entry, input_index, used_ports)
            input_ports[port] = PortContract.any()
            edges.append(Edge(from_node=source_node, to_node=node_id, to_port=port))

        config = {
            key: value for key, value in step.items()
            if key not in _STEP_SCALAR_EXCLUDE
        }
        config["inputs"] = static_inputs

        nodes.append(
            NodeSpec(
                node_id=node_id,
                operator_id=operator_id,
                input_ports=input_ports,
                output_port=PortTopology.any(),
                backend_id=_backend_id(step, node_id, operator_id, assignments),
                config=config,
            )
        )

    return GraphSpec(nodes=tuple(nodes), edges=tuple(edges))


def _node_id(step: Mapping[str, Any], index: int) -> str:
    operator_id = str(step.get("operator_id") or "operator")
    return f"{operator_id}#{index}"


def _backend_id(
    step: Mapping[str, Any],
    node_id: str,
    operator_id: str,
    assignments: Mapping[str, str],
) -> str | None:
    value = step.get("backend_id")
    if value is not None:
        return str(value)
    assigned = assignments.get(node_id) or assignments.get(operator_id)
    return str(assigned) if assigned is not None else None


def _derive_port_name(
    input_entry: Mapping[str, Any],
    index: int,
    used: set[str],
) -> str:
    metadata = input_entry.get("metadata")
    role = metadata.get("role") if isinstance(metadata, Mapping) else None
    seed = role or input_entry.get("artifact_type") or f"in{index}"
    base = _safe_port_name(str(seed)) or f"in{index}"
    name = base
    suffix = 2
    while name in used:
        name = f"{base}_{suffix}"
        suffix += 1
    used.add(name)
    return name


def _safe_port_name(value: str) -> str:
    return _SAFE_PORT_RE.sub("_", value.strip()).strip("_").lower()


__all__ = ["compile_operator_sequence"]
