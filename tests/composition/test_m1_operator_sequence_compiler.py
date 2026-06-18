from __future__ import annotations

import uuid

from forge_bridge.composition.compiler import compile_operator_sequence
from forge_bridge.composition.executor import GraphExecutor
from forge_bridge.composition.node_result import NodeResult
from forge_bridge.graph.ports import PortTopology


_RUN_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


def _artifact_id(node_id: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"forge-bridge:m1:{node_id}")


def _dispatch(calls: list[tuple[str, tuple[str, ...]]]):
    def dispatch(node, resolved_inputs):
        calls.append((node.node_id, tuple(sorted(resolved_inputs))))
        return NodeResult(
            status="ok",
            run_id=_RUN_ID,
            artifact_id=_artifact_id(node.node_id),
            output={"node_id": node.node_id},
            output_topology=PortTopology.any().to_dict(),
            source_artifact_ids=tuple(
                result.artifact_id
                for result in resolved_inputs.values()
                if result.artifact_id is not None
            ),
        )

    return dispatch


def test_compile_operator_sequence_single_step_static_inputs_runs():
    static_input = {
        "artifact_id": "manual_intent:abc",
        "artifact_type": "text_intent",
        "metadata": {
            "prompt": "a lone lighthouse at dusk",
            "role": "structural",
            "scalars": {"data_root": "/tmp/forge", "target": "text"},
        },
    }
    graph = compile_operator_sequence([{
        "operator_id": "author_prompt",
        "backend_id": "ollama-api.llama3.2",
        "inputs": [static_input],
        "output_artifact_id": "draft-001",
    }])

    assert len(graph.nodes) == 1
    assert graph.edges == ()
    node = graph.nodes[0]
    assert node.node_id == "author_prompt#0"
    assert node.operator_id == "author_prompt"
    assert node.backend_id == "ollama-api.llama3.2"
    assert node.input_ports == {}
    assert node.config["inputs"] == [static_input]
    assert node.config["output_artifact_id"] == "draft-001"

    calls: list[tuple[str, tuple[str, ...]]] = []
    results = GraphExecutor(_dispatch(calls)).run(graph)
    assert calls == [("author_prompt#0", ())]
    assert results["author_prompt#0"].status == "ok"


def test_compile_operator_sequence_links_referenced_output_as_named_any_edge():
    operator_sequence = [
        {
            "operator_id": "author_prompt",
            "backend_id": "ollama-api.llama3.2",
            "inputs": [{
                "artifact_id": "manual_intent:abc",
                "artifact_type": "text_intent",
                "metadata": {"role": "structural", "prompt": "lighthouse"},
            }],
            "output_artifact_id": "draft-001",
        },
        {
            "operator_id": "author_prompt",
            "backend_id": "ollama-api.llama3.2",
            "inputs": [
                {
                    "artifact_id": "draft-001",
                    "artifact_type": "text_draft",
                    "metadata": {"role": "source text"},
                },
                {
                    "artifact_id": "manual_qc:def",
                    "artifact_type": "qc_correction",
                    "metadata": {
                        "role": "editorial",
                        "qc_correction": "make the light warmer",
                    },
                },
            ],
            "output_artifact_id": "draft-002",
        },
    ]

    graph = compile_operator_sequence(operator_sequence)

    assert [node.node_id for node in graph.nodes] == [
        "author_prompt#0",
        "author_prompt#1",
    ]
    assert len(graph.edges) == 1
    edge = graph.edges[0]
    assert edge.from_node == "author_prompt#0"
    assert edge.to_node == "author_prompt#1"
    assert edge.to_port == "source_text"

    target = graph.node("author_prompt#1")
    assert tuple(target.input_ports) == ("source_text",)
    assert target.input_ports["source_text"].accepts_topology(PortTopology.any())
    assert target.config["inputs"] == [operator_sequence[1]["inputs"][1]]

    calls: list[tuple[str, tuple[str, ...]]] = []
    results = GraphExecutor(_dispatch(calls)).run(graph)
    assert calls == [
        ("author_prompt#0", ()),
        ("author_prompt#1", ("source_text",)),
    ]
    assert results["author_prompt#1"].source_artifact_ids == (
        _artifact_id("author_prompt#0"),
    )


def test_compile_operator_sequence_declares_every_derived_edge_port():
    graph = compile_operator_sequence([
        {
            "operator_id": "a",
            "inputs": [],
            "output_artifact_id": "a-out",
        },
        {
            "operator_id": "b",
            "inputs": [{"artifact_id": "a-out", "artifact_type": "draft"}],
            "output_artifact_id": "b-out",
        },
    ])

    for edge in graph.edges:
        assert edge.to_port in graph.node(edge.to_node).input_ports

    calls: list[tuple[str, tuple[str, ...]]] = []
    GraphExecutor(_dispatch(calls)).run(graph)
    assert calls == [("a#0", ()), ("b#1", ("draft",))]
