"""``GraphSpec`` — the persisted node-id'd DAG that is the IR of record (M1).

The graph is the view of record; a linear ``operator_sequence`` compiles to a
degenerate single-path ``GraphSpec`` and runs through the same executor. Named
input ports (``NodeSpec.input_ports``) are the fan-in unlock — they reuse the
existing ``ports.py`` ``PortContract`` *per port* without modifying it.

Edge validation is graph-native: it reuses the pure ``PortContract`` algebra
(``accepts_topology``) but raises a graph-identity error (``from_node`` /
``to_node`` / ``to_port``), NOT the chain-identity ``ChainWireCompatibilityError``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from forge_bridge.graph.ports import PortContract, PortTopology


@dataclass(frozen=True)
class NodeSpec:
    """A node in the composition graph."""

    node_id: str
    operator_id: str
    #: Named input ports — ``{port_name: PortContract}``. The ``PortContract``'s
    #: ``accepts`` tuple is the shapes THIS port admits. Empty for source nodes.
    input_ports: dict[str, PortContract] = field(default_factory=dict)
    #: The single emitted topology.
    output_port: PortTopology = field(default_factory=PortTopology.any)
    backend_id: str | None = None
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Edge:
    """A directed edge wiring an upstream output to a named downstream input."""

    from_node: str
    to_node: str
    to_port: str
    from_port: str = "out"


@dataclass(frozen=True)
class GraphSpec:
    """A node-id'd DAG. Acyclic in M1 (the executor enforces it)."""

    nodes: tuple[NodeSpec, ...]
    edges: tuple[Edge, ...]

    def node(self, node_id: str) -> NodeSpec:
        for n in self.nodes:
            if n.node_id == node_id:
                return n
        raise KeyError(node_id)

    def incoming(self, node_id: str) -> tuple[Edge, ...]:
        """Edges terminating at ``node_id`` (its input wiring)."""
        return tuple(e for e in self.edges if e.to_node == node_id)


class GraphEdgeCompatibilityError(ValueError):
    """An edge wires an output topology a named input port does not accept."""

    code = "GRAPH_EDGE_COMPATIBILITY_ERROR"

    def __init__(
        self,
        *,
        from_node: str,
        to_node: str,
        to_port: str,
        expected: tuple[PortTopology, ...],
        actual: PortTopology,
    ) -> None:
        self.from_node = from_node
        self.to_node = to_node
        self.to_port = to_port
        self.expected = expected
        self.actual = actual
        message = (
            f"edge {from_node} -> {to_node}.{to_port}: port cannot accept "
            f"topology {actual.to_dict()}; expects one of "
            f"{[t.to_dict() for t in expected]}."
        )
        super().__init__(message)
        self.message = message

    def to_error(self) -> dict[str, Any]:
        return {
            "type": self.code,
            "message": self.message,
            "from_node": self.from_node,
            "to_node": self.to_node,
            "to_port": self.to_port,
            "expected": [t.to_dict() for t in self.expected],
            "actual": self.actual.to_dict(),
        }


class GraphCycleError(ValueError):
    """A GraphSpec contains a cycle — rejected before execution in M1."""

    code = "GRAPH_CYCLE_ERROR"
