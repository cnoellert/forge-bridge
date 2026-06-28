"""Slice-3 read-only smoke: real apply_steps -> select_delta (no Flame, no commit)."""
import asyncio
from forge_core.operations.registry import get_default_registry
from forge_core.traffik.execution import TraffikEditorialOperator
from forge_core.traffik.tests.test_editing_federation import (
    _state, _bridge_authored_steps,
)
from forge_bridge.composition.graph_spec import Edge, GraphSpec, NodeSpec
from forge_bridge.graph.ports import PortContract, PortTopology
from forge_bridge.orchestration.run_graph import run_graph

reg = get_default_registry()
try:
    reg.register(TraffikEditorialOperator())
except ValueError as e:
    print("(editorial already registered:", e, ")")

spec = GraphSpec(
    nodes=(
        NodeSpec(
            node_id="apply_steps",
            operator_id="traffik.editorial.apply_steps",
            output_port=PortTopology.manifest(),
            config={"arguments": {"state": _state().to_dict(),
                                  "steps": _bridge_authored_steps()}},
        ),
        NodeSpec(
            node_id="select_delta",
            operator_id="select_delta",
            input_ports={"result": PortContract.manifest_gate()},
            output_port=PortTopology.manifest(),
        ),
    ),
    edges=(Edge(from_node="apply_steps", to_node="select_delta", to_port="result"),),
)

res = asyncio.run(run_graph(spec, registry=reg))
a, s = res["apply_steps"], res["select_delta"]
print("\n=== apply_steps ===")
print("status:", a.status, "| reason:", a.reason_code)
out = a.output if isinstance(a.output, dict) else {}
deltas = out.get("deltas") or []
print("deltas emitted:", len(deltas))
print("\n=== select_delta ===")
print("status:", s.status, "| reason:", s.reason_code)
if isinstance(s.output, dict):
    print("extracted delta keys:", sorted(s.output.keys()))
    print("extracted == deltas[0]:", s.output == (deltas[0] if deltas else None))
    print("delta.action(s):", [c.get("action") for c in (s.output.get("changes") or s.output.get("entries") or [])][:6])
