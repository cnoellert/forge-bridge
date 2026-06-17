"""``GraphExecutor`` — the topological executor over a ``node_id → NodeResult``
map (M1). **The single executor.**

``operator_sequence`` compiles to a degenerate ``GraphSpec`` and runs through
here; ``run_chain_steps`` (the single-``__previous_result__``-slot model) is
**replaced wholesale**, not extended — two executors would diverge and violate
"the graph is the view of record".

Contract for the implementation (the M1 green-bar; see
``.planning/M1-WIRE-AND-RUN-SEAM-DESIGN.md``):

All graph-shape checks are a **pre-pass that fails before any dispatch** —
the cycle check and the static edge-type check both reject a bad graph before
a single (potentially expensive) make is spent. Order matters: structural
well-formedness must precede the cycle check, or a dangling endpoint
masquerades as a cycle.

1. **Structural well-formedness** — every edge endpoint must be a declared
   node, and every edge must target a **declared** input port; otherwise raise
   ``GraphSpecError``. (An edge to an undeclared port is a wiring mistake, not
   permissive — permissiveness lives in ``PortContract.any()``, not in
   skipping unknown ports.)
2. **Acyclic enforcement** — reject a cyclic ``GraphSpec`` with
   ``GraphCycleError`` before any dispatch.
3. **Static edge-type validation** — a pre-pass (NOT interleaved with
   dispatch): validate each edge with the pure ``PortContract.accepts_topology``
   algebra against the upstream's *declared* ``output_port`` topology; on
   mismatch raise ``GraphEdgeCompatibilityError`` (graph identity), NOT the
   chain-identity ``validate_chain_wire``. Because the check is purely static,
   a type-invalid graph is rejected before any node dispatches.
4. **Permissive-by-default** — a port whose derived contract is
   ``PortContract.any()`` accepts anything (so introducing validation never
   regresses workflows that are unvalidated today).
5. **Topological dispatch** — schedule nodes so every upstream completes
   first; resolve each node's incoming edges into ``{input_port_name:
   NodeResult}`` and hand that to ``dispatch``. The executor is mechanism, not
   policy: a non-``ok`` (``abstained``/``error``) upstream result is propagated
   to the downstream node unchanged — branching on status is the node's job,
   never the executor's.
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
    GraphSpecError,
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

        # 1. Structural well-formedness — endpoints exist, ports are declared.
        #    Must precede the cycle check: a dangling endpoint would otherwise
        #    masquerade as a cycle (its downstream never gets scheduled).
        for edge in graph.edges:
            if edge.from_node not in nodes:
                raise GraphSpecError(
                    f"edge references unknown from_node {edge.from_node!r}"
                )
            if edge.to_node not in nodes:
                raise GraphSpecError(
                    f"edge references unknown to_node {edge.to_node!r}"
                )
            if edge.to_port not in nodes[edge.to_node].input_ports:
                raise GraphSpecError(
                    f"edge {edge.from_node} -> {edge.to_node}.{edge.to_port}: "
                    f"node {edge.to_node!r} declares no input port "
                    f"{edge.to_port!r}"
                )

        # 2. Acyclic enforcement — before any dispatch.
        topo_order = self._topological_order(graph, nodes)

        # 3. Static edge-type validation — a pre-pass, NOT interleaved with
        #    dispatch, so a type-invalid graph is rejected before any make.
        for edge in graph.edges:
            contract = nodes[edge.to_node].input_ports[edge.to_port]
            upstream_node = nodes[edge.from_node]
            if not contract.accepts_topology(upstream_node.output_port):
                raise GraphEdgeCompatibilityError(
                    from_node=edge.from_node,
                    to_node=edge.to_node,
                    to_port=edge.to_port,
                    expected=contract.accepts,
                    actual=upstream_node.output_port,
                )

        # 4. Topological dispatch — non-ok upstreams propagate unchanged.
        results: dict[str, NodeResult] = {}
        for node_id in topo_order:
            node = nodes[node_id]
            resolved_inputs = {
                edge.to_port: results[edge.from_node]
                for edge in graph.incoming(node_id)
            }
            results[node_id] = self._dispatch(node, resolved_inputs)

        return results

    @staticmethod
    def _topological_order(
        graph: GraphSpec, nodes: dict[str, NodeSpec]
    ) -> list[str]:
        """Kahn's algorithm; raises ``GraphCycleError`` on a cycle. Endpoints
        are already validated ∈ ``nodes`` by the structural pre-pass."""
        outgoing: dict[str, list[str]] = {node_id: [] for node_id in nodes}
        indegree: dict[str, int] = {node_id: 0 for node_id in nodes}
        for edge in graph.edges:
            outgoing[edge.from_node].append(edge.to_node)
            indegree[edge.to_node] += 1

        ready = [node_id for node_id in nodes if indegree[node_id] == 0]
        order: list[str] = []
        cursor = 0
        while cursor < len(ready):
            node_id = ready[cursor]
            cursor += 1
            order.append(node_id)
            for downstream in outgoing[node_id]:
                indegree[downstream] -= 1
                if indegree[downstream] == 0:
                    ready.append(downstream)

        if len(order) != len(nodes):
            raise GraphCycleError("GraphSpec contains a cycle")
        return order
