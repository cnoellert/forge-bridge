from __future__ import annotations

import pytest

from forge_contracts import BridgeRegistrationContext

from forge_bridge.composition.compiler import compile_operator_sequence
from forge_bridge.composition.planner_inventory import (
    host_graph_planner_inventory,
    select_host_graph_plan,
)
from forge_bridge.orchestration.registration import (
    ToolRegistry,
    tool_registration_from_capability,
)


def _real_pipeline_registry(monkeypatch, plugins: str) -> ToolRegistry:
    contract_registry = pytest.importorskip(
        "forge_core.bridge.contract_registry",
        reason="Pipeline planner declaration is not installed",
    )
    monkeypatch.setenv("FORGE_PLUGINS", plugins)
    monkeypatch.delenv("FORGE_DCC", raising=False)
    registry = ToolRegistry()

    def register(registration) -> None:
        registry.register(
            tool_registration_from_capability(registration),
            sibling_name="forge_pipeline",
            handler=registration.handler,
        )

    contract_registry.register_bridge_adapters(
        BridgeRegistrationContext(
            bridge_version="phase108",
            requested_families=["execution"],
            dry_run=True,
        ),
        register,
    )
    return registry


def test_real_pipeline_declaration_selects_semantic_graph_without_admission_merge(
    monkeypatch,
) -> None:
    registry = _real_pipeline_registry(monkeypatch, "flame")
    inventory = host_graph_planner_inventory(registry)
    assert [(row["dcc"], row["proof_status"]) for row in inventory["profiles"]] == [
        ("flame", "trusted")
    ]
    assert inventory["grants_execution_authority"] is False

    scope = {
        "kind": "pipeline.host_graph.scope",
        "schema_version": 1,
        "dcc": "Flame",
        "graph_kind": "batch",
        "project": "TST",
        "instance_id": "flame-phase108",
        "session_id": "session-phase108",
        "graph_ref": "test_104",
        "operator_identity": "",
        "mutation_boundary": "dcc_host",
    }
    decision = select_host_graph_plan(
        registry,
        {
            "intent": "canonical_shot_output_graph",
            "scope": scope,
            "semantic_request": {
                "kind": "pipeline.shot_output_graph.request",
                "schema_version": 1,
                "canonical": "/canonical/TST",
                "shot": "tst_010",
                "task": "comp",
                "role": "comp_render",
                "stream": "main",
                "dcc": "Flame",
                "target_graph": scope,
            },
        },
        live_sessions=[
            {
                "dcc": "Flame",
                "instance_id": "flame-phase108",
                "session_id": "session-phase108",
                "live": True,
            }
        ],
        require_execution=True,
    )

    assert decision.status == "selected"
    assert decision.reason_code == "semantic_selected"
    assert decision.execution_ready is True
    graph = compile_operator_sequence(decision.operator_sequence)
    assert len(graph.nodes) == 5
    assert len(graph.edges) == 5
    assert all(edge.from_port == "out" for edge in graph.edges)

    atomic = select_host_graph_plan(
        registry,
        {
            "intent": "ensure_and_connect",
            "scope": scope,
            "target": {
                "dcc": "Flame",
                "instance_id": "flame-phase108",
                "session_id": "session-phase108",
            },
            "node_type_evidence": {
                "status": "succeeded",
                "trust_status": "trusted",
                "result": {
                    "kind": "pipeline.host_graph.node_type_list",
                    "node_types": [
                        {
                            "dcc": "flame",
                            "native_type": "Comp",
                            "display_name": "Comp",
                            "graph_kinds": ["batch"],
                        },
                        {
                            "dcc": "flame",
                            "native_type": "Write File",
                            "display_name": "Write File",
                            "graph_kinds": ["batch"],
                        },
                    ],
                },
            },
            "nodes": [
                {"native_type": "Comp", "name": "SOURCE"},
                {"native_type": "Write File", "name": "WRITE"},
            ],
            "connection": {
                "source_node": {"native_type": "Comp", "name": "SOURCE"},
                "source_port": "Result",
                "destination_node": {
                    "native_type": "Write File",
                    "name": "WRITE",
                },
                "destination_port": "Front",
            },
        },
        live_sessions=[
            {
                "dcc": "Flame",
                "instance_id": "flame-phase108",
                "session_id": "session-phase108",
                "live": True,
            }
        ],
    )
    assert atomic.status == "selected"
    assert atomic.execution_ready is False
    assert atomic.review_required is True
    assert [row["operator_id"] for row in atomic.operator_sequence] == [
        "forge_host_graph_ensure_node",
        "forge_host_graph_ensure_node",
        "forge_host_graph_connect",
    ]


def test_real_pipeline_inventory_selects_all_six_trusted_dcc_scopes(
    monkeypatch,
) -> None:
    registry = _real_pipeline_registry(
        monkeypatch,
        "flame,blender,houdini,fusion,nuke,resolve",
    )
    inventory = host_graph_planner_inventory(registry)
    profiles = {row["dcc"]: row for row in inventory["profiles"]}
    assert set(profiles) == {
        "blender",
        "flame",
        "fusion",
        "houdini",
        "nuke",
        "resolve",
    }

    for dcc, profile in sorted(profiles.items()):
        graph_kind = profile["graph_kinds"][0]
        scope = {
            "kind": "pipeline.host_graph.scope",
            "schema_version": 1,
            "dcc": dcc,
            "graph_kind": graph_kind,
            "project": "TST",
            "instance_id": f"{dcc}-phase108",
            "session_id": f"{dcc}-session-phase108",
            "graph_ref": f"{dcc}-graph-phase108",
            "operator_identity": "",
            "mutation_boundary": "dcc_host",
        }
        sessions = [
            {
                "dcc": dcc,
                "instance_id": scope["instance_id"],
                "session_id": scope["session_id"],
                "live": True,
            }
        ]
        read = select_host_graph_plan(
            registry,
            {"intent": "inspect_graph", "scope": scope},
            live_sessions=sessions,
            require_execution=True,
        )
        assert read.status == "selected", (dcc, read.to_dict())
        assert read.execution_ready is True
        assert len(compile_operator_sequence(read.operator_sequence).nodes) == 1

        semantic = select_host_graph_plan(
            registry,
            {
                "intent": "canonical_shot_output_graph",
                "scope": scope,
                "semantic_request": {
                    "kind": "pipeline.shot_output_graph.request",
                    "schema_version": 1,
                    "canonical": "/canonical/TST",
                    "shot": "tst_010",
                    "task": "comp",
                    "role": "comp_render",
                    "stream": "main",
                    "dcc": dcc,
                    "target_graph": scope,
                },
            },
            live_sessions=sessions,
            require_execution=True,
        )
        assert semantic.status == "selected", (dcc, semantic.to_dict())
        graph = compile_operator_sequence(semantic.operator_sequence)
        assert len(graph.nodes) == 5
        assert len(graph.edges) == 5
