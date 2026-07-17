from __future__ import annotations

import copy
from dataclasses import dataclass
import json
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from forge_bridge.composition.commit_boundary import CommitBoundary
from forge_bridge.composition.compiler import compile_operator_sequence
from forge_bridge.composition.dispatch import UnifiedDispatch
from forge_bridge.composition.executor import GraphExecutor
from forge_bridge.composition.operation_boundary import OperationDispatchBoundary
from forge_bridge.core.assent import AssentRecord
from forge_bridge.orchestration.operation_runner import build_operation_runner


_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "shot_output_graph_operator_sequence.json"


def _fixture() -> dict[str, Any]:
    return json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))


def _manifest() -> dict[str, Any]:
    scope = _fixture()["operator_sequence"][1]["arguments"]["scope"]
    plan = {
        "kind": "pipeline.host_graph.mutation_plan",
        "schema_version": 1,
        "scope": scope,
        "expected_pre_state_fingerprint": "snapshot-before",
        "expected_post_state": {"fingerprint": "snapshot-after"},
        "changes": [
            {
                "kind": "pipeline.host_graph.change",
                "schema_version": 1,
                "change_id": "ensure-write",
                "action": "ensure_node",
                "payload": {"native_type": "Write File", "name": "FORGE_COMP_MAIN"},
            }
        ],
    }
    return {
        "kind": "pipeline.shot_output_graph.plan_result",
        "schema_version": 1,
        "status": "ready",
        "trust_status": "provisional",
        "type": "mutation_plan",
        "intent_parameters": {
            "target": {
                "dcc": "Flame",
                "instance_id": "flame-fixture-1",
                "session_id": "session-fixture-1",
            },
            "scope": scope,
            "semantic_intent": {
                "shot": "tst_010",
                "task": "comp",
                "role": "comp_render",
                "stream": "main",
                "dcc": "Flame",
            },
        },
        "resolved_plan": [
            {
                "identity": {
                    "change_id": "ensure-write",
                    "action": "ensure_node",
                    "scope_identity": "Flame:batch:test_104",
                    "expected_pre_state_fingerprint": "snapshot-before",
                },
                "payload": {"change": plan["changes"][0]},
            }
        ],
        "originating_capability": "forge_plan_shot_output_graph",
        "apply_counterpart": {
            "tool": "forge_apply_host_graph_plan",
            "parameter_overrides": {"plan": plan},
        },
        "plan": plan,
    }


class _HostGraphMCP:
    def __init__(self, manifest: dict[str, Any]) -> None:
        self._manifest = copy.deepcopy(manifest)
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.apply_count = 0

    async def list_tools(self):
        properties = {
            name: {"type": "object"} for name in ("target", "scope", "plan", "resolved_plan")
        }
        properties["mode"] = {"type": "string"}
        properties["semantic_intent"] = {"type": "object"}
        return [
            SimpleNamespace(
                name="forge_apply_host_graph_plan",
                inputSchema={
                    "type": "object",
                    "properties": properties,
                    "required": ["target", "scope", "plan", "mode"],
                },
            )
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]):
        self.calls.append((name, copy.deepcopy(arguments)))
        assert name == "forge_apply_host_graph_plan"
        if arguments["mode"] == "verify":
            return copy.deepcopy(self._manifest)
        if arguments["mode"] == "apply":
            self.apply_count += 1
            return {
                "kind": "pipeline.host_graph.mutation_dispatch",
                "status": "succeeded",
                "trust_status": "trusted",
                "drift": False,
            }
        raise AssertionError(arguments["mode"])


@dataclass
class _OperationRequest:
    operation_type: str
    bridge_asset_ids: list[str]
    idempotency_key: str
    params: dict[str, Any]
    project_id: str | None = None
    requested_by: str | None = None


def _install_operation_dispatch(monkeypatch, calls: list[_OperationRequest]) -> None:
    forge_core = ModuleType("forge_core")
    operations = ModuleType("forge_core.operations")
    dispatch_mod = ModuleType("forge_core.operations.dispatch")
    registry_mod = ModuleType("forge_core.operations.registry")
    sentinel_registry = object()
    current = {
        "kind": "pipeline.shot_resource.current_result",
        "status": "resolved",
        "trust_status": "trusted",
        "pointers": [{"role": "comp_render", "current_path": "/canonical/v001"}],
    }
    snapshot = {
        "kind": "pipeline.host_graph.operation_result",
        "status": "succeeded",
        "trust_status": "trusted",
        "result": {
            "kind": "pipeline.host_graph.snapshot",
            "fingerprint": "snapshot-before",
        },
    }
    manifest = _manifest()

    async def dispatch(request, registry, receipt_path=None):
        assert registry is sentinel_registry
        assert receipt_path
        calls.append(request)
        if request.operation_type == "pipeline.shot_resource.current":
            data = current
        elif request.operation_type == "pipeline.host_graph.inspect":
            data = snapshot
        elif request.operation_type == "pipeline.shot_output_graph.plan":
            assert request.params["stream_context"] == current
            assert request.params["host_graph_snapshot"] == snapshot
            data = manifest
        elif request.operation_type == "pipeline.host_graph.verify":
            assert request.params["expectations"] == manifest
            if request.params["apply_receipt"].get("type") != "commit_applied":
                data = {
                    "kind": "pipeline.host_graph.operation_result",
                    "status": "failed",
                    "trust_status": "review_required",
                    "error_code": "commit_not_applied",
                    "error": "fresh verification requires an applied commit receipt",
                }
            else:
                data = {
                    "kind": "pipeline.host_graph.operation_result",
                    "status": "succeeded",
                    "trust_status": "trusted",
                    "result": {
                        "kind": "pipeline.host_graph.verification_receipt",
                        "status": "passed",
                        "trust_status": "trusted",
                        "observed_fingerprint": "snapshot-after",
                    },
                }
        else:
            raise AssertionError(request.operation_type)
        return SimpleNamespace(
            status="failed" if data["status"] == "failed" else "succeeded",
            data=copy.deepcopy(data),
            error=data.get("error"),
        )

    operations.OperationRequest = _OperationRequest
    dispatch_mod.dispatch = dispatch
    registry_mod.get_default_registry = lambda: sentinel_registry
    forge_core.operations = operations
    monkeypatch.setitem(__import__("sys").modules, "forge_core", forge_core)
    monkeypatch.setitem(__import__("sys").modules, "forge_core.operations", operations)
    monkeypatch.setitem(
        __import__("sys").modules,
        "forge_core.operations.dispatch",
        dispatch_mod,
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "forge_core.operations.registry",
        registry_mod,
    )


def _assent(status: str) -> AssentRecord:
    return AssentRecord(
        graph_intent_id="phase106-shot-output-graph",
        chain_steps=["pipeline.shot_output_graph.plan", "commit"],
        status=status,
        decided_by="operator" if status == "ratified" else None,
    )


def test_real_pipeline_fixture_compiles_to_exact_issue_86_topology() -> None:
    fixture = _fixture()
    graph = compile_operator_sequence(fixture["operator_sequence"])

    assert fixture["fingerprint"] == (
        "07ca855ffcec77d6be8330f13df07b275a51a320788b5b95a73bc82164780d39"
    )
    assert len(graph.nodes) == 5
    assert len(graph.edges) == 5
    assert [edge.to_port for edge in graph.edges] == [
        "stream_context",
        "host_graph_snapshot",
        "held",
        "expectations",
        "apply_receipt",
    ]
    assert {edge.from_port for edge in graph.edges} == {"out"}
    assert all(
        "from_port" not in value
        for step in fixture["operator_sequence"]
        for value in step["inputs"]
    )


@pytest.mark.asyncio
async def test_real_fixture_runs_through_production_boundaries(monkeypatch, tmp_path):
    operation_calls: list[_OperationRequest] = []
    _install_operation_dispatch(monkeypatch, operation_calls)
    manifest = _manifest()
    mcp = _HostGraphMCP(manifest)
    runner = build_operation_runner(receipt_dir=tmp_path)
    dispatch = UnifiedDispatch(
        operation_boundary=OperationDispatchBoundary(run_operation=runner),
        commit_boundary=CommitBoundary(mcp=mcp),
        assent_record=_assent("ratified"),
    )

    results = await GraphExecutor(dispatch.dispatch).run(
        compile_operator_sequence(_fixture()["operator_sequence"])
    )

    assert [call.operation_type for call in operation_calls] == [
        "pipeline.shot_resource.current",
        "pipeline.host_graph.inspect",
        "pipeline.shot_output_graph.plan",
        "pipeline.host_graph.verify",
    ]
    assert results["commit#3"].output["type"] == "commit_applied"
    assert results["pipeline.host_graph.verify#4"].output["trust_status"] == "trusted"
    assert mcp.apply_count == 1
    assert [(name, args["mode"]) for name, args in mcp.calls] == [
        ("forge_apply_host_graph_plan", "verify"),
        ("forge_apply_host_graph_plan", "apply"),
    ]


@pytest.mark.asyncio
async def test_real_fixture_refuses_unratified_commit_before_apply(monkeypatch, tmp_path):
    operation_calls: list[_OperationRequest] = []
    _install_operation_dispatch(monkeypatch, operation_calls)
    mcp = _HostGraphMCP(_manifest())
    dispatch = UnifiedDispatch(
        operation_boundary=OperationDispatchBoundary(
            run_operation=build_operation_runner(receipt_dir=tmp_path)
        ),
        commit_boundary=CommitBoundary(mcp=mcp),
        assent_record=_assent("proposed"),
    )

    results = await GraphExecutor(dispatch.dispatch).run(
        compile_operator_sequence(_fixture()["operator_sequence"])
    )

    assert results["commit#3"].status == "error"
    assert results["commit#3"].reason_code == "ASSENT_INVALID"
    assert results["pipeline.host_graph.verify#4"].status == "error"
    assert results["pipeline.host_graph.verify#4"].reason_code == "commit_not_applied"
    assert mcp.apply_count == 0
    assert [(name, args["mode"]) for name, args in mcp.calls] == [
        ("forge_apply_host_graph_plan", "verify")
    ]
