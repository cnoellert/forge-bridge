"""Slice-3 UAT — live preview of apply_steps -> select_delta -> host_resolve.

Drives the PRODUCTION rail (preview_editorial_delta_for_ratification): runs the
real traffik.editorial.apply_steps operation, select_delta extracts deltas[0],
host_resolve projects, delta_to_manifest holds the mutation manifest, and a
proposed AssentRecord is persisted. Prints the graph_intent_id you then ratify
with `fbridge ratify`.

Registers the traffik operators manually (the #116 bypass) — preview is the only
step that needs them; ratify replays the persisted held manifest commit-only.

Run:  conda activate forge && python scratchpad/slice3_uat_preview.py
"""
from __future__ import annotations

import asyncio

from forge_bridge.composition.graph_spec import Edge, GraphSpec, NodeSpec
from forge_bridge.composition.host_resolve_boundary import HostResolveBoundary
from forge_bridge.graph.ports import PortContract, PortTopology
from forge_bridge.orchestration.apply_editorial_delta import (
    preview_editorial_delta_for_ratification,
)
from forge_bridge.store.session import get_async_session_factory


def _build_registry():
    """Register traffik operators into a fresh registry (#116 bypass)."""
    from forge_core.operations.registry import get_default_registry

    reg = get_default_registry()
    # >>> OPERATOR FILL: exact class names + import path are Pipeline-side.
    # From issue #116: TraffikFlameDeltaHostResolveOperator. apply_steps is its
    # sibling. Confirm against the v2.1 checkout you proved i5 against.
    from forge_core.plugins.traffik import (  # type: ignore
        TraffikEditorialApplyStepsOperator,
        TraffikFlameDeltaHostResolveOperator,
    )

    reg.register(TraffikEditorialApplyStepsOperator())
    reg.register(TraffikFlameDeltaHostResolveOperator())
    return reg


def _spec() -> GraphSpec:
    # >>> OPERATOR FILL: real editorial state/step_plan that yields ONE rename
    # delta on the target sequence. The test stub {"timeline":"t1"},{} produces
    # nothing live — use the same payload you fed i5.
    apply_args = {
        "state": {"timeline": "REPLACE_ME"},
        "step_plan": {},
    }
    return GraphSpec(
        nodes=(
            NodeSpec(
                node_id="apply_steps",
                operator_id="traffik.editorial.apply_steps",
                output_port=PortTopology.manifest(),
                config={"arguments": apply_args},
            ),
            NodeSpec(
                node_id="select_delta",
                operator_id="select_delta",
                input_ports={"result": PortContract.manifest_gate()},
                output_port=PortTopology.manifest(),
                # config={"index": 0}  # default; set explicitly if N>1 deltas
            ),
            NodeSpec(
                node_id="host_resolve",
                operator_id="traffik.flame_delta.host_resolve",
                input_ports={"delta": PortContract.manifest_gate()},
                output_port=PortTopology.manifest(),
            ),
            NodeSpec(
                node_id="delta_to_manifest",
                operator_id="delta_to_manifest",
                input_ports=HostResolveBoundary.input_ports,
                output_port=HostResolveBoundary.output_port,
            ),
        ),
        edges=(
            Edge(from_node="apply_steps", to_node="select_delta", to_port="result"),
            Edge(from_node="select_delta", to_node="host_resolve", to_port="delta"),
            Edge(from_node="host_resolve", to_node="delta_to_manifest", to_port="deltas"),
        ),
    )


async def main() -> None:
    reg = _build_registry()
    session_factory = get_async_session_factory()
    preview = await preview_editorial_delta_for_ratification(
        _spec(),
        session_factory=session_factory,
        registry=reg,
        display="slice-3 select_delta live vertical",
    )
    print("graph_intent_id:", preview["graph_intent_id"])
    print("sequence:", preview["summary"]["manifest"].get("sequence_name"))
    print("apply_tool:", preview["summary"]["manifest"].get("apply_tool"))
    print("resolved_count:", preview["summary"]["manifest"].get("resolved_count"))
    print("\nInspect the held manifest, then:")
    print(f"  fbridge ratify {preview['graph_intent_id']} --actor <you>")


if __name__ == "__main__":
    asyncio.run(main())
