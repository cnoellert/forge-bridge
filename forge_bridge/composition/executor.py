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

from forge_bridge.composition.graph_spec import GraphSpec, NodeSpec
from forge_bridge.composition.node_result import NodeResult

#: Boundary-adapter signature: given a node and its resolved named inputs,
#: dispatch the operator and mint the typed ``NodeResult``.
DispatchFn = Callable[[NodeSpec, "dict[str, NodeResult]"], NodeResult]


class GraphExecutor:
    """Runs a ``GraphSpec`` to a ``node_id → NodeResult`` map."""

    def __init__(self, dispatch: DispatchFn) -> None:
        self._dispatch = dispatch

    def run(self, graph: GraphSpec) -> dict[str, NodeResult]:
        # M1 GREEN-BAR TARGET — not yet implemented. The verification vertical
        # (tests/composition/test_m1_fan_in_vertical.py) is red against this.
        raise NotImplementedError(
            "GraphExecutor.run is the M1 green-bar: implement acyclic-enforced "
            "topological execution with named-port input resolution, per-edge "
            "accepts_topology validation, and lineage threading."
        )
