from __future__ import annotations

import json
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from typer.testing import CliRunner

from forge_bridge.__main__ import app
from forge_bridge.composition.graph_spec import GraphSpec, NodeSpec
from forge_bridge.composition.node_result import NodeResult
from forge_bridge.orchestration.run_graph import graph_spec_from_dict, run_graph


class _OperationStatus(str, Enum):
    SUCCEEDED = "succeeded"
    NO_PROVIDER = "no_provider"


@dataclass
class _OperationResult:
    status: _OperationStatus
    data: dict[str, Any] = field(default_factory=dict)
    error_code: str | None = None
    error: str | None = None


@dataclass
class _OperationRequest:
    operation_type: str
    bridge_asset_ids: list[str]
    idempotency_key: str
    params: dict[str, Any] = field(default_factory=dict)
    project_id: str | None = None
    requested_by: str | None = None


class _OperatorRegistry:
    def __init__(self) -> None:
        self._operators: dict[str, Any] = {}

    def register(self, operator: Any) -> None:
        self._operators[operator.operation_type] = operator

    def get(self, operation_type: str) -> Any:
        return self._operators[operation_type]


class _ApplyStepsOperator:
    operation_type = "traffik.editorial.apply_steps"

    def __init__(self) -> None:
        self.requests: list[_OperationRequest] = []

    async def execute(self, request: _OperationRequest) -> _OperationResult:
        self.requests.append(request)
        data = {
            "step_plan_result": {
                "packet_type": "EditorialStepPlanResult",
                "idempotency_key": request.idempotency_key,
            },
            "state": request.params["state"],
            "step_plan": request.params["step_plan"],
        }
        return _OperationResult(status=_OperationStatus.SUCCEEDED, data=data)


def _install_fake_forge_core(monkeypatch: pytest.MonkeyPatch):
    forge_core = ModuleType("forge_core")
    operations = ModuleType("forge_core.operations")
    dispatch_mod = ModuleType("forge_core.operations.dispatch")
    registry_mod = ModuleType("forge_core.operations.registry")

    default_registry = _OperatorRegistry()

    async def dispatch(request, registry, *, receipt_path=None):
        dispatch.calls.append((request, registry, receipt_path))
        if receipt_path is not None:
            Path(receipt_path).write_text(
                json.dumps({
                    "operation_type": request.operation_type,
                    "idempotency_key": request.idempotency_key,
                })
                + "\n",
                encoding="utf-8",
            )
        try:
            operator = registry.get(request.operation_type)
        except KeyError:
            return _OperationResult(
                status=_OperationStatus.NO_PROVIDER,
                error_code="NO_PROVIDER",
                error=f"no provider for {request.operation_type}",
            )
        return await operator.execute(request)

    dispatch.calls = []

    def get_default_registry():
        return default_registry

    operations.OperationRequest = _OperationRequest
    operations.OperationResult = _OperationResult
    operations.OperationStatus = _OperationStatus
    dispatch_mod.dispatch = dispatch
    registry_mod.OperatorRegistry = _OperatorRegistry
    registry_mod.get_default_registry = get_default_registry
    forge_core.operations = operations

    monkeypatch.setitem(sys.modules, "forge_core", forge_core)
    monkeypatch.setitem(sys.modules, "forge_core.operations", operations)
    monkeypatch.setitem(
        sys.modules,
        "forge_core.operations.dispatch",
        dispatch_mod,
    )
    monkeypatch.setitem(
        sys.modules,
        "forge_core.operations.registry",
        registry_mod,
    )
    return _OperatorRegistry, dispatch


def _state() -> dict[str, Any]:
    return {"timeline_id": "timeline-104", "tracks": [{"id": "v1"}]}


def _step_plan() -> dict[str, Any]:
    return {
        "packet_type": "EditorialStepPlan",
        "steps": [{"op": "insert", "clip": "sh010", "track": "v1"}],
    }


def _graph_spec() -> GraphSpec:
    return GraphSpec(
        nodes=(
            NodeSpec(
                node_id="apply_steps",
                operator_id="traffik.editorial.apply_steps",
                config={
                    "arguments": {
                        "state": _state(),
                        "step_plan": _step_plan(),
                    }
                },
            ),
        ),
        edges=(),
    )


def _graph_spec_json() -> dict[str, Any]:
    return {
        "nodes": [
            {
                "node_id": "apply_steps",
                "operator_id": "traffik.editorial.apply_steps",
                "config": {
                    "arguments": {
                        "state": _state(),
                        "step_plan": _step_plan(),
                    }
                },
            }
        ],
        "edges": [],
    }


@pytest.mark.asyncio
async def test_run_graph_dispatches_operation_and_writes_default_receipt(
    monkeypatch,
    tmp_path,
):
    registry_cls, dispatch = _install_fake_forge_core(monkeypatch)
    registry = registry_cls()
    operator = _ApplyStepsOperator()
    registry.register(operator)

    results = await run_graph(_graph_spec(), registry=registry, receipt_dir=tmp_path)

    result = results["apply_steps"]
    request = operator.requests[0]
    receipt_path = tmp_path / f"{request.idempotency_key}.jsonl"
    assert result.status == "ok"
    assert result.output["step_plan_result"]["idempotency_key"] == request.idempotency_key
    assert receipt_path.exists()
    assert dispatch.calls == [(request, registry, str(receipt_path))]


@pytest.mark.asyncio
async def test_run_graph_default_registry_without_provider_returns_error(
    monkeypatch,
    tmp_path,
):
    _registry_cls, _dispatch = _install_fake_forge_core(monkeypatch)

    results = await run_graph(_graph_spec(), registry=None, receipt_dir=tmp_path)

    result = results["apply_steps"]
    assert result.status == "error"
    assert result.reason_code == "NO_PROVIDER"
    assert result.message == "no provider for traffik.editorial.apply_steps"


def test_cli_graph_run_uses_run_graph_entrypoint(monkeypatch, tmp_path):
    spec_path = tmp_path / "graph.json"
    spec_path.write_text(json.dumps(_graph_spec_json()), encoding="utf-8")
    calls: list[GraphSpec] = []

    async def _fake_run_graph(spec, *, registry=None, receipt_dir=None):
        calls.append(spec)
        return {
            "apply_steps": NodeResult(
                status="ok",
                run_id=uuid.UUID("00000000-0000-0000-0000-000000000104"),
                output={"ok": True},
                resolved_class="pipeline.traffik.editorial.apply_steps",
            )
        }

    monkeypatch.setattr("forge_bridge.cli.graph.run_graph", _fake_run_graph)

    result = CliRunner().invoke(app, ["graph", "run", str(spec_path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["data"]["apply_steps"]["status"] == "ok"
    assert calls[0].nodes[0].operator_id == "traffik.editorial.apply_steps"


def test_graph_spec_from_dict_round_trips_minimal_json():
    spec = graph_spec_from_dict(_graph_spec_json())

    assert spec.nodes[0].node_id == "apply_steps"
    assert spec.nodes[0].config["arguments"]["step_plan"] == _step_plan()


def test_graph_executor_is_byte_stable_against_main():
    diff = subprocess.run(
        ["git", "diff", "main", "--", "forge_bridge/composition/executor.py"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert diff.stdout == ""
