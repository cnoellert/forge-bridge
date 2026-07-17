from __future__ import annotations

from copy import deepcopy

from forge_bridge.composition.compiler import compile_operator_sequence
from forge_bridge.composition.planner_inventory import (
    HOST_GRAPH_CAPABILITY_ID,
    host_graph_planner_inventory,
    select_host_graph_plan,
)
from forge_bridge.orchestration.registration import ToolRegistration, ToolRegistry


def _scope(**overrides):
    values = {
        "dcc": "flame",
        "graph_kind": "batch",
        "project": "TST",
        "instance_id": "flame-1",
        "session_id": "session-1",
        "graph_ref": "test_104",
    }
    values.update(overrides)
    return values


def _session(**overrides):
    values = {
        "dcc": "flame",
        "instance_id": "flame-1",
        "session_id": "session-1",
        "live": True,
    }
    values.update(overrides)
    return values


def _scope_row(operation_type: str, *, proof_status: str = "trusted"):
    return {
        "plugin": "flame",
        "dcc": "flame",
        "display_name": "Autodesk Flame Batch",
        "graph_kinds": ["batch"],
        "supported_modes": ["discover", "verify", "apply"],
        "status": "available",
        "proof_status": proof_status,
        "identity_tiers": ["exact_type_name"],
        "container_types": ["Compass"],
        "operation_type": operation_type,
        "node_types": [
            {
                "native_type": "Write File",
                "display_name": "Write File",
                "graph_kinds": ["batch"],
                "creatable": True,
            },
            {
                "native_type": "WriteFile",
                "display_name": "Write File",
                "graph_kinds": ["batch"],
                "creatable": True,
            },
            {
                "native_type": "Comp",
                "display_name": "Comp",
                "graph_kinds": ["batch"],
                "creatable": True,
            },
        ],
    }


def _operation(
    operation_type: str,
    intents: list[str],
    *,
    selection_class: str = "atomic",
    proof_status: str = "trusted",
):
    effect_class = (
        "host_mutation"
        if operation_type.startswith("pipeline.host_graph.")
        and operation_type.rsplit(".", 1)[-1]
        in {"ensure_node", "connect", "delete_node"}
        else "read"
    )
    return {
        "operation_type": operation_type,
        "tool_name": operation_type,
        "label": operation_type,
        "summary": operation_type,
        "effect_class": effect_class,
        "state_owner": "dcc_host" if effect_class == "host_mutation" else "read_only",
        "idempotent": True,
        "selection_class": selection_class,
        "selection_priority": 0 if selection_class == "semantic" else 100,
        "planner_intents": intents,
        "dcc_scopes": [_scope_row(operation_type, proof_status=proof_status)],
        "available_dccs": ["flame"],
        "discovery_only": True,
        "grants_execution_authority": False,
    }


def _inventory(*, proof_status: str = "trusted"):
    operations = [
        _operation("pipeline.host_graph.inspect", ["inspect_graph"], proof_status=proof_status),
        _operation(
            "pipeline.host_graph.list_node_types",
            ["inspect_node_types", "list_node_types"],
            proof_status=proof_status,
        ),
        _operation(
            "pipeline.host_graph.describe_node_type",
            ["inspect_node_types", "describe_node_type"],
            proof_status=proof_status,
        ),
        _operation("pipeline.host_graph.verify", ["verify_graph"], proof_status=proof_status),
        _operation(
            "pipeline.shot_output_graph.plan",
            ["canonical_shot_output_graph"],
            selection_class="semantic",
            proof_status=proof_status,
        ),
        _operation(
            "pipeline.host_graph.ensure_node",
            ["ensure_node", "ensure_and_connect", "canonical_shot_output_graph"],
            proof_status=proof_status,
        ),
        _operation(
            "pipeline.host_graph.connect",
            ["connect_nodes", "ensure_and_connect", "canonical_shot_output_graph"],
            proof_status=proof_status,
        ),
        _operation(
            "pipeline.host_graph.delete_node",
            ["delete_node"],
            proof_status=proof_status,
        ),
    ]
    return {
        "kind": "pipeline.host_graph.planner_inventory",
        "schema_version": 1,
        "status": "ready",
        "trust_status": proof_status,
        "discovery_only": True,
        "grants_execution_authority": False,
        "automatic_mutation_admission": False,
        "selection_policy": ["semantic", "atomic", "refuse_or_clarify"],
        "edge_value_semantics": "whole_operation_output",
        "from_port": "reserved",
        "profiles": [
            {
                "plugin": "flame",
                "dcc": "flame",
                "display_name": "Autodesk Flame Batch",
                "graph_kinds": ["batch"],
                "proof_status": proof_status,
                "node_types": _scope_row("profile")["node_types"],
            }
        ],
        "operations": operations,
    }


def _registry(inventory=None):
    registry = ToolRegistry()
    registry.register(
        ToolRegistration(
            tool_id=HOST_GRAPH_CAPABILITY_ID,
            family="execution",
            payload_family="pipeline.host_graph.draft",
            schema={"type": "object"},
            capabilities={"planner_inventory": inventory or _inventory()},
            summary="Host graph operations",
            label="Host graph operations",
        ),
        sibling_name="forge_pipeline",
    )
    registry.drain_pending_events()
    return registry


def _semantic_request():
    return {
        "intent": "canonical_shot_output_graph",
        "scope": _scope(),
        "semantic_request": {
            "kind": "pipeline.shot_output_graph.request",
            "schema_version": 1,
            "canonical": "/canonical/TST",
            "shot": "tst_010",
            "task": "comp",
            "role": "comp_render",
            "stream": "artist_a",
            "dcc": "flame",
            "target_graph": _scope(),
        },
    }


def test_registry_inventory_is_read_only_and_does_not_grant_admission() -> None:
    inventory = host_graph_planner_inventory(_registry())

    assert inventory["discovery_only"] is True
    assert inventory["grants_execution_authority"] is False
    assert inventory["automatic_mutation_admission"] is False


def test_semantic_operation_wins_and_compiles_exact_phase106_topology() -> None:
    decision = select_host_graph_plan(
        _registry(),
        _semantic_request(),
        live_sessions=[_session()],
        require_execution=True,
    )

    assert decision.status == "selected"
    assert decision.reason_code == "semantic_selected"
    assert decision.selected_operation_types == ("pipeline.shot_output_graph.plan",)
    assert decision.execution_ready is True
    assert decision.review_required is False
    assert decision.candidates == (
        "pipeline.shot_output_graph.plan",
        "pipeline.host_graph.connect",
        "pipeline.host_graph.ensure_node",
    )
    graph = compile_operator_sequence(decision.operator_sequence)
    assert [node.operator_id for node in graph.nodes] == [
        "pipeline.shot_resource.current",
        "pipeline.host_graph.inspect",
        "pipeline.shot_output_graph.plan",
        "commit",
        "pipeline.host_graph.verify",
    ]
    assert [edge.to_port for edge in graph.edges] == [
        "stream_context",
        "host_graph_snapshot",
        "held",
        "expectations",
        "apply_receipt",
    ]
    assert {edge.from_port for edge in graph.edges} == {"out"}


def test_novel_read_only_node_type_flow_selects_atoms_and_compiles() -> None:
    decision = select_host_graph_plan(
        _registry(),
        {"intent": "inspect_node_types", "scope": _scope(), "node_type": "Comp"},
        live_sessions=[_session()],
        require_execution=True,
    )

    assert decision.status == "selected"
    assert decision.reason_code == "atomic_selected"
    assert decision.execution_ready is True
    assert decision.selected_operation_types == (
        "pipeline.host_graph.list_node_types",
        "pipeline.host_graph.describe_node_type",
    )
    graph = compile_operator_sequence(decision.operator_sequence)
    assert [node.operator_id for node in graph.nodes] == list(
        decision.selected_operation_types
    )
    assert graph.edges == ()


def test_explicit_low_level_atoms_are_selected_but_not_auto_admitted() -> None:
    request = {
        "intent": "ensure_and_connect",
        "scope": _scope(),
        "target": {"dcc": "flame", "session_id": "session-1"},
        "nodes": [
            {"native_type": "Comp", "name": "SOURCE"},
            {"native_type": "Write File", "name": "WRITE"},
        ],
        "connection": {
            "source_node": {"native_type": "Comp", "name": "SOURCE"},
            "source_port": "Result",
            "destination_node": {"native_type": "Write File", "name": "WRITE"},
            "destination_port": "Front",
        },
    }

    decision = select_host_graph_plan(
        _registry(), request, live_sessions=[_session()]
    )
    assert decision.status == "selected"
    assert decision.selected_operation_types == (
        "pipeline.host_graph.ensure_node",
        "pipeline.host_graph.connect",
    )
    assert decision.execution_ready is False
    assert decision.review_required is True
    assert [row["operator_id"] for row in decision.operator_sequence] == [
        "forge_host_graph_ensure_node",
        "forge_host_graph_ensure_node",
        "forge_host_graph_connect",
    ]
    assert all(row["arguments"]["mode"] == "discover" for row in decision.operator_sequence)
    assert all(
        row["effect_class"] == "mutation_plan_authoring"
        for row in decision.operator_sequence
    )

    refusal = select_host_graph_plan(
        _registry(),
        request,
        live_sessions=[_session()],
        require_execution=True,
    )
    assert refusal.status == "refused"
    assert refusal.reason_code == "unadmitted_mutation"
    assert refusal.candidates == (
        "forge_host_graph_ensure_node",
        "forge_host_graph_ensure_node",
        "forge_host_graph_connect",
    )


def test_absent_dcc_session_scope_and_provisional_capability_refuse() -> None:
    absent_dcc = select_host_graph_plan(
        _registry(),
        {"intent": "inspect_graph", "scope": _scope(dcc="maya")},
        live_sessions=[_session()],
    )
    assert absent_dcc.reason_code == "dcc_unavailable"
    assert absent_dcc.candidates == ("flame",)

    absent_session = select_host_graph_plan(
        _registry(),
        {"intent": "inspect_graph", "scope": _scope(session_id="missing")},
        live_sessions=[_session()],
    )
    assert absent_session.reason_code == "session_not_live"
    assert absent_session.candidates == ("session-1",)

    unsupported_scope = select_host_graph_plan(
        _registry(),
        {"intent": "inspect_graph", "scope": _scope(graph_kind="timeline")},
        live_sessions=[_session()],
    )
    assert unsupported_scope.reason_code == "unsupported_graph_scope"
    assert unsupported_scope.candidates == ("batch",)

    provisional = _inventory(proof_status="provisional")
    provisional_decision = select_host_graph_plan(
        _registry(provisional),
        {"intent": "inspect_graph", "scope": _scope()},
        live_sessions=[_session()],
    )
    assert provisional_decision.reason_code == "capability_not_trusted"
    assert provisional_decision.candidates == ("provisional",)


def test_ambiguous_node_type_refuses_with_exact_candidates() -> None:
    decision = select_host_graph_plan(
        _registry(),
        {
            "intent": "inspect_node_types",
            "scope": _scope(),
            "node_type": "WRITE FILE",
        },
        live_sessions=[_session()],
    )

    assert decision.status == "refused"
    assert decision.intent == "inspect_node_types"
    assert decision.reason_code == "ambiguous_node_type"
    assert decision.candidates == ("Write File", "WriteFile")


def test_unknown_and_unadmitted_delete_intents_fail_closed() -> None:
    unknown = select_host_graph_plan(
        _registry(),
        {"intent": "invent_magic_node", "scope": _scope()},
        live_sessions=[_session()],
    )
    assert unknown.status == "refused"
    assert unknown.reason_code == "intent_unsupported"
    assert "inspect_graph" in unknown.candidates

    delete = select_host_graph_plan(
        _registry(),
        {"intent": "delete_node", "scope": _scope()},
        live_sessions=[_session()],
        require_execution=True,
    )
    assert delete.status == "refused"
    assert delete.reason_code == "unadmitted_mutation"


def test_empty_atomic_request_fails_closed_before_admission() -> None:
    decision = select_host_graph_plan(
        _registry(),
        {"intent": "ensure_and_connect", "scope": _scope()},
        live_sessions=[_session()],
    )

    assert decision.status == "refused"
    assert decision.reason_code == "invalid_atomic_request"
    assert decision.operator_sequence == ()


def test_dynamic_node_type_evidence_enables_atomic_selection_fail_closed() -> None:
    inventory = _inventory()
    inventory["profiles"][0]["node_types"] = []
    for operation in inventory["operations"]:
        for scope in operation["dcc_scopes"]:
            scope["node_types"] = []
    request = {
        "intent": "ensure_and_connect",
        "scope": _scope(),
        "target": {"dcc": "flame", "session_id": "session-1"},
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
            "destination_node": {"native_type": "Write File", "name": "WRITE"},
            "destination_port": "Front",
        },
    }

    selected = select_host_graph_plan(
        _registry(inventory),
        request,
        live_sessions=[_session()],
    )
    assert selected.status == "selected"
    assert selected.review_required is True

    request["node_type_evidence"]["trust_status"] = "provisional"
    refused = select_host_graph_plan(
        _registry(inventory),
        request,
        live_sessions=[_session()],
    )
    assert refused.status == "refused"
    assert refused.reason_code == "node_type_evidence_not_trusted"


def test_inventory_copy_cannot_mutate_registry_declaration() -> None:
    registry = _registry()
    inventory = host_graph_planner_inventory(registry)
    inventory["operations"].clear()

    fresh = host_graph_planner_inventory(registry)
    assert fresh["operations"] == _inventory()["operations"]


def test_invalid_inventory_authority_claim_is_rejected() -> None:
    inventory = deepcopy(_inventory())
    inventory["grants_execution_authority"] = True

    try:
        host_graph_planner_inventory(_registry(inventory))
    except ValueError as exc:
        assert "must not grant execution authority" in str(exc)
    else:
        raise AssertionError("invalid authority claim must fail closed")
