"""``GraphExecutor`` — the topological executor over a ``node_id → NodeResult``
map (M1). **The single executor.**

``operator_sequence`` compiles to a degenerate ``GraphSpec`` and runs through
here; ``run_chain_steps`` (the single-``__previous_result__``-slot model) is
**replaced wholesale**, not extended — two executors would diverge and violate
"the graph is the view of record".

Contract for the implementation (the M1 green-bar; see
``.planning/M1-WIRE-AND-RUN-SEAM-DESIGN.md``):

1. **Acyclic enforcement** — reject a cyclic ``GraphSpec`` with ``GraphCycleError``
   before any dispatch.
2. **Topological order** — schedule nodes so every upstream completes first.
3. **Named-port input resolution** — for each node, resolve its incoming edges
   into ``{input_port_name: NodeResult}`` and hand that to ``dispatch``.
4. **Per-edge validation** — validate each edge with the pure
   ``PortContract.accepts_topology`` algebra against the upstream's
   ``output_port`` topology; on mismatch raise ``GraphEdgeCompatibilityError``
   (graph identity), NOT the chain-identity ``validate_chain_wire``.
5. **Permissive-by-default** — a port whose derived contract is
   ``PortContract.any()`` accepts anything (so introducing validation never
   regresses workflows that are unvalidated today).
6. **Lineage** — the dispatch mints each ``NodeResult`` with
   ``source_artifact_ids`` drawn from the resolved upstream results.

``dispatch`` is the bridge boundary adapter: ``(NodeSpec, resolved_inputs) ->
NodeResult``. Siblings never emit ``NodeResult``; the adapter mints it.
"""
from __future__ import annotations

from collections.abc import Callable

from forge_bridge.composition.graph_spec import (
    GraphCycleError,
    GraphEdgeCompatibilityError,
    GraphSpec,
    NodeSpec,
)
from forge_bridge.composition.node_result import NodeResult

#: Boundary-adapter signature: given a node and its resolved named inputs,
#: dispatch the operator and mint the typed ``NodeResult``.
DispatchFn = Callable[[NodeSpec, "dict[str, NodeResult]"], NodeResult]


class GraphExecutor:
    """Runs a ``GraphSpec`` to a ``node_id → NodeResult`` map."""

    def __init__(self, dispatch: DispatchFn) -> None:
        self._dispatch = dispatch

    def run(self, graph: GraphSpec) -> dict[str, NodeResult]:
        nodes = {node.node_id: node for node in graph.nodes}
        outgoing: dict[str, list[str]] = {node_id: [] for node_id in nodes}
        indegree: dict[str, int] = {node_id: 0 for node_id in nodes}

        for edge in graph.edges:
            outgoing.setdefault(edge.from_node, []).append(edge.to_node)
            indegree[edge.to_node] = indegree.get(edge.to_node, 0) + 1

        ready = [node.node_id for node in graph.nodes if indegree.get(node.node_id, 0) == 0]
        topo_order: list[str] = []
        cursor = 0
        while cursor < len(ready):
            node_id = ready[cursor]
            cursor += 1
            topo_order.append(node_id)
            for downstream in outgoing.get(node_id, ()):
                indegree[downstream] -= 1
                if indegree[downstream] == 0:
                    ready.append(downstream)

        if len(topo_order) != len(nodes):
            raise GraphCycleError("GraphSpec contains a cycle")

        results: dict[str, NodeResult] = {}
        for node_id in topo_order:
            node = nodes[node_id]
            resolved_inputs: dict[str, NodeResult] = {}
            for edge in graph.incoming(node_id):
                upstream_node = nodes[edge.from_node]
                contract = node.input_ports.get(edge.to_port)
                if contract is not None and not contract.accepts_topology(
                    upstream_node.output_port
                ):
                    raise GraphEdgeCompatibilityError(
                        from_node=edge.from_node,
                        to_node=node_id,
                        to_port=edge.to_port,
                        expected=contract.accepts,
                        actual=upstream_node.output_port,
                    )
                resolved_inputs[edge.to_port] = results[edge.from_node]
            results[node_id] = self._dispatch(node, resolved_inputs)

        return results
