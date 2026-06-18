"""Named parity specimens for legacy-chain vs graph-executor comparison."""
from __future__ import annotations

from dataclasses import dataclass

from forge_bridge.composition.graph_spec import Edge, GraphSpec, NodeSpec
from forge_bridge.graph.ports import PortContract, PortTopology


@dataclass(frozen=True)
class ParityCase:
    """A legacy/graph pair intended to be semantically equivalent."""

    name: str
    legacy_steps: tuple[str, ...]
    graph: GraphSpec
    terminal_node_id: str


GREENSCREEN_FILTER_ROTO = ParityCase(
    name="greenscreen_filter_roto",
    legacy_steps=(
        "forge_is_greenscreen shot_id=batch clip_ref=mock://batch.mov",
        "filter(is_greenscreen == true)",
        "forge_roto_ref shot_id=gs_010 clip_ref=mock://gs_010.mov",
    ),
    graph=GraphSpec(
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
    ),
    terminal_node_id="roto",
)

PARITY_CASES = (GREENSCREEN_FILTER_ROTO,)
