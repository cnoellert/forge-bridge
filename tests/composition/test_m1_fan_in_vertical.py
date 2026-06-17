"""M1 verification vertical — the green-bar the phase plan cuts against.

Three stub perception nodes emit ``NodeResult``s that converge on ONE consumer
node's three NAMED input ports, run through the ``GraphSpec`` executor. This is
the first proof that capabilities compose: named-port fan-in, per-edge
validation, permissive-by-default, acyclic enforcement, the discriminator
branch rule, and forward-only lineage.

Daemon-free and in-process: the nodes are canned ``NodeResult``s injected via a
stub dispatch (standing in for the bridge boundary adapter), so this proves the
ENGINE, not vision's perception.

Status at authoring: the ``NodeResult`` discriminator test is GREEN (the data
layer is done); the five execution tests are RED against the unimplemented
``GraphExecutor.run`` — that is the target.
"""
from __future__ import annotations

import uuid
from dataclasses import replace

import pytest

from forge_bridge.composition import (
    Edge,
    GraphCycleError,
    GraphEdgeCompatibilityError,
    GraphExecutor,
    GraphSpec,
    NodeResult,
    NodeSpec,
)
from forge_bridge.graph.ports import PortContract, PortTopology


# ── topologies modelled on vision's real fan-in node ─────────────────────────
# validate_perspective(CameraMotionEstimate, DepthEstimate, PlaneEstimate)
_CAM = PortTopology.single_item("CameraMotionEstimate")
_DEPTH = PortTopology.single_item("DepthEstimate")
_PLANES = PortTopology.single_item("PlaneEstimate")


def _perception_node(node_id: str, output: PortTopology) -> NodeSpec:
    """A source perception node (no inputs), emitting a typed single item."""
    return NodeSpec(node_id=node_id, operator_id=f"forge_{node_id}", output_port=output)


def _consumer_node(ports: dict[str, PortTopology]) -> NodeSpec:
    """The fan-in consumer with named, typed input ports."""
    return NodeSpec(
        node_id="consumer",
        operator_id="forge_validate_perspective",
        input_ports={
            name: PortContract(accepts=(topo,), emits=PortTopology.any())
            for name, topo in ports.items()
        },
        output_port=PortTopology.single_item("ValidationReport"),
    )


def _canned_ok(node_id: str, topo: PortTopology) -> NodeResult:
    return NodeResult(
        status="ok",
        run_id=uuid.uuid4(),
        artifact_id=uuid.uuid4(),
        output={"node": node_id},
        output_topology=topo.to_dict(),
        artifact_type=topo.item_type,
    )


def _stub_dispatch(canned: dict[str, NodeResult], captured: dict[str, tuple[str, ...]]):
    """Stand-in for the bridge boundary adapter: wrap → mint NodeResult.

    Records which named ports each node was handed (fan-in proof) and threads
    forward-only lineage from the resolved upstream results.
    """

    def dispatch(node: NodeSpec, resolved_inputs: dict[str, NodeResult]) -> NodeResult:
        captured[node.node_id] = tuple(sorted(resolved_inputs))
        srcs = tuple(
            r.artifact_id for r in resolved_inputs.values() if r.artifact_id is not None
        )
        return replace(canned[node.node_id], source_artifact_ids=srcs)

    return dispatch


def _fan_in_graph(consumer_ports: dict[str, PortTopology]) -> GraphSpec:
    cam = _perception_node("camera", _CAM)
    depth = _perception_node("depth", _DEPTH)
    planes = _perception_node("planes", _PLANES)
    consumer = _consumer_node(consumer_ports)
    return GraphSpec(
        nodes=(cam, depth, planes, consumer),
        edges=(
            Edge(from_node="camera", to_node="consumer", to_port="camera"),
            Edge(from_node="depth", to_node="consumer", to_port="depth"),
            Edge(from_node="planes", to_node="consumer", to_port="planes"),
        ),
    )


def _canned_for(graph: GraphSpec) -> dict[str, NodeResult]:
    topo = {
        "camera": _CAM, "depth": _DEPTH, "planes": _PLANES,
        "consumer": PortTopology.single_item("ValidationReport"),
    }
    return {n.node_id: _canned_ok(n.node_id, topo[n.node_id]) for n in graph.nodes}


# ── 1. named-port fan-in ─────────────────────────────────────────────────────
def test_fan_in_resolves_three_named_ports():
    graph = _fan_in_graph({"camera": _CAM, "depth": _DEPTH, "planes": _PLANES})
    captured: dict[str, tuple[str, ...]] = {}
    GraphExecutor(_stub_dispatch(_canned_for(graph), captured)).run(graph)
    assert captured["consumer"] == ("camera", "depth", "planes")


# ── 2. per-edge validation (graph-native error) ──────────────────────────────
def test_mistyped_edge_raises_graph_edge_error():
    # depth's DepthEstimate routed into the camera port (accepts CameraMotionEstimate)
    graph = _fan_in_graph({"camera": _CAM, "depth": _DEPTH, "planes": _PLANES})
    bad = GraphSpec(
        nodes=graph.nodes,
        edges=(
            Edge(from_node="depth", to_node="consumer", to_port="camera"),
            Edge(from_node="camera", to_node="consumer", to_port="depth"),
            Edge(from_node="planes", to_node="consumer", to_port="planes"),
        ),
    )
    captured: dict[str, tuple[str, ...]] = {}
    with pytest.raises(GraphEdgeCompatibilityError) as exc:
        GraphExecutor(_stub_dispatch(_canned_for(bad), captured)).run(bad)
    assert exc.value.to_port == "camera"
    assert exc.value.from_node == "depth"


# ── 3. permissive-by-default (no regression of unvalidated edges) ────────────
def test_permissive_any_port_accepts_anything():
    # A consumer whose ports are permissive any() — mirrors a semantic operator
    # whose derived contract is PortContract.any(). Mismatched topology must NOT
    # fail an edge that is unvalidated today.
    graph = _fan_in_graph({
        "camera": PortTopology.any(),
        "depth": PortTopology.any(),
        "planes": PortTopology.any(),
    })
    captured: dict[str, tuple[str, ...]] = {}
    results = GraphExecutor(_stub_dispatch(_canned_for(graph), captured)).run(graph)
    assert results["consumer"].status == "ok"


# ── 4. acyclic enforcement ───────────────────────────────────────────────────
def test_cyclic_graph_is_rejected():
    a = NodeSpec(node_id="a", operator_id="op_a",
                 input_ports={"in": PortContract.any()})
    b = NodeSpec(node_id="b", operator_id="op_b",
                 input_ports={"in": PortContract.any()})
    cyclic = GraphSpec(
        nodes=(a, b),
        edges=(
            Edge(from_node="a", to_node="b", to_port="in"),
            Edge(from_node="b", to_node="a", to_port="in"),  # back-edge
        ),
    )
    with pytest.raises(GraphCycleError):
        GraphExecutor(_stub_dispatch({}, {})).run(cyclic)


# ── 5. discriminator branch rule (usable-output from status ALONE) ───────────
def test_usable_output_derivable_from_discriminator_alone():
    rid = uuid.uuid4()
    assert NodeResult(status="ok", run_id=rid).has_usable_output is True
    assert NodeResult(status="partial", run_id=rid).has_usable_output is True
    assert NodeResult(status="abstained", run_id=rid).has_usable_output is False
    assert NodeResult(status="error", run_id=rid).has_usable_output is False


# ── 6. forward-only lineage recorded ─────────────────────────────────────────
def test_consumer_lineage_names_three_upstreams():
    graph = _fan_in_graph({"camera": _CAM, "depth": _DEPTH, "planes": _PLANES})
    canned = _canned_for(graph)
    captured: dict[str, tuple[str, ...]] = {}
    results = GraphExecutor(_stub_dispatch(canned, captured)).run(graph)
    expected = {canned[n].artifact_id for n in ("camera", "depth", "planes")}
    assert set(results["consumer"].source_artifact_ids) == expected
