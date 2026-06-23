from __future__ import annotations

import sys
from dataclasses import dataclass, field
from enum import Enum
from types import ModuleType
from typing import Any

import pytest

from forge_bridge.orchestration.operation_runner import (
    OperationRunnerUnavailable,
    build_operation_runner,
)


class _OperationStatus(str, Enum):
    SUCCEEDED = "succeeded"


@dataclass
class _OperationResult:
    status: _OperationStatus
    data: dict[str, Any] = field(default_factory=dict)
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
        return _OperationResult(
            status=_OperationStatus.SUCCEEDED,
            data={
                "state": request.params["state"],
                "step_plan": request.params["step_plan"],
                "idempotency_key": request.idempotency_key,
            },
        )


def _install_fake_forge_core(monkeypatch: pytest.MonkeyPatch):
    forge_core = ModuleType("forge_core")
    operations = ModuleType("forge_core.operations")
    dispatch_mod = ModuleType("forge_core.operations.dispatch")
    registry_mod = ModuleType("forge_core.operations.registry")

    default_registry = _OperatorRegistry()

    async def dispatch(request, registry, *, receipt_path=None):
        dispatch.calls.append((request, registry, receipt_path))
        return await registry.get(request.operation_type).execute(request)

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


@pytest.mark.asyncio
async def test_build_operation_runner_dispatches_operation_request(monkeypatch):
    registry_cls, dispatch = _install_fake_forge_core(monkeypatch)
    registry = registry_cls()
    operator = _ApplyStepsOperator()
    registry.register(operator)

    runner = build_operation_runner(registry=registry)
    result = await runner(
        "traffik.editorial.apply_steps",
        state={"timeline": "t1"},
        step_plan={"steps": [{"op": "insert"}]},
        receipt_path="/tmp/receipt.json",
        bridge_asset_ids=["asset-1"],
        idempotency_key="idem-104",
        project_id="project-104",
        requested_by="bridge",
    )

    request = operator.requests[0]
    assert request.operation_type == "traffik.editorial.apply_steps"
    assert request.bridge_asset_ids == ["asset-1"]
    assert request.idempotency_key == "idem-104"
    assert request.params == {
        "state": {"timeline": "t1"},
        "step_plan": {"steps": [{"op": "insert"}]},
    }
    assert request.project_id == "project-104"
    assert request.requested_by == "bridge"
    assert dispatch.calls == [(request, registry, "/tmp/receipt.json")]
    assert result.status is _OperationStatus.SUCCEEDED
    assert result.data["step_plan"] == {"steps": [{"op": "insert"}]}


@pytest.mark.asyncio
async def test_build_operation_runner_derives_stable_idempotency_key(monkeypatch):
    registry_cls, _dispatch = _install_fake_forge_core(monkeypatch)
    registry = registry_cls()
    operator = _ApplyStepsOperator()
    registry.register(operator)

    runner = build_operation_runner(registry=registry)
    first = await runner(
        "traffik.editorial.apply_steps",
        state={"timeline": "t1"},
        step_plan={"steps": [{"op": "insert"}]},
        project_id="project-104",
    )
    second = await runner(
        "traffik.editorial.apply_steps",
        state={"timeline": "t1"},
        step_plan={"steps": [{"op": "insert"}]},
        project_id="project-104",
    )

    assert first.data["idempotency_key"] == second.data["idempotency_key"]


def test_build_operation_runner_degrades_when_forge_core_dispatch_absent(monkeypatch):
    monkeypatch.setitem(sys.modules, "forge_core.operations.dispatch", None)

    with pytest.raises(OperationRunnerUnavailable):
        build_operation_runner()
