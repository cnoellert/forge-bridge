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


def _read_ifgate_prune_case(name: str) -> ParityCase:
    return ParityCase(
        name=name,
        legacy_steps=(
            "forge_is_greenscreen shot_id=manifest clip_ref=mock://manifest.mov",
            "if(proposed_changes exists)",
            "forge_roto_ref shot_id=gs_010 clip_ref=mock://gs_010.mov",
        ),
        graph=GraphSpec(
            nodes=(
                NodeSpec(
                    node_id="read_manifest",
                    operator_id="forge_is_greenscreen",
                    output_port=PortTopology.manifest(),
                    config={
                        "arguments": {
                            "shot_id": "manifest",
                            "clip_ref": "mock://manifest.mov",
                        }
                    },
                ),
                NodeSpec(
                    node_id="if_gate",
                    operator_id="if",
                    input_ports={"input": PortContract.manifest_gate()},
                    output_port=PortTopology.manifest(),
                    config={"step_text": "if(proposed_changes exists)"},
                ),
                NodeSpec(
                    node_id="downstream",
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
                Edge(from_node="read_manifest", to_node="if_gate", to_port="input"),
                Edge(from_node="if_gate", to_node="downstream", to_port="input"),
            ),
        ),
        terminal_node_id="downstream",
    )


READ_IFGATE_PRUNE_OPEN = _read_ifgate_prune_case(
    "read_ifgate_prune_open",
)
READ_IFGATE_PRUNE_CLOSED = _read_ifgate_prune_case(
    "read_ifgate_prune_closed",
)

READ_FOREACH_EXPAND = ParityCase(
    name="read_foreach_expand",
    legacy_steps=(
        "forge_is_greenscreen shot_id=gs_probe "
        "clip_ref=mock://perception/is_greenscreen/gs_probe_true",
        "foreach(forge_roto_ref shot_id=gs_010 clip_ref=mock://gs_010.mov)",
    ),
    graph=GraphSpec(
        nodes=(
            NodeSpec(
                node_id="read_collection",
                operator_id="forge_is_greenscreen",
                output_port=PortTopology.list_of("shot"),
                config={
                    "arguments": {
                        "shot_id": "gs_probe",
                        "clip_ref": (
                            "mock://perception/is_greenscreen/gs_probe_true"
                        ),
                    }
                },
            ),
            NodeSpec(
                node_id="foreach_roto",
                operator_id="foreach",
                input_ports={"input": PortContract.any()},
                output_port=PortTopology.iteration_results(),
                config={
                    "body": NodeSpec(
                        node_id="foreach_roto_body",
                        operator_id="forge_roto_ref",
                        input_ports={"item": PortContract.any()},
                        config={
                            "arguments": {
                                "shot_id": "gs_010",
                                "clip_ref": "mock://gs_010.mov",
                            }
                        },
                    )
                },
            ),
        ),
        edges=(
            Edge(from_node="read_collection", to_node="foreach_roto", to_port="input"),
        ),
    ),
    terminal_node_id="foreach_roto",
)

PARITY_CASES = (
    GREENSCREEN_FILTER_ROTO,
    READ_IFGATE_PRUNE_OPEN,
    READ_IFGATE_PRUNE_CLOSED,
    READ_FOREACH_EXPAND,
)
