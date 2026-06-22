from __future__ import annotations

import subprocess
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

from forge_bridge.composition.boundary import UnsupportedCompositionNodeError
from forge_bridge.composition.dispatch import UnifiedDispatch
from forge_bridge.composition.executor import GraphExecutor
from forge_bridge.composition.graph_spec import Edge, GraphSpec, NodeSpec
from forge_bridge.composition.node_result import NodeResult
from forge_bridge.composition.operation_boundary import (
    OPERATION_INPUT_ERROR,
    OPERATION_UNAVAILABLE,
    OperationDispatchBoundary,
)
from forge_bridge.graph.ports import PortTopology

RESOLVED_CLASS = "pipeline.traffik.editorial.apply_steps"


def _state() -> dict:
    return {
        "timeline_id": "timeline-001",
        "tracks": [{"id": "v1", "items": ["shot-a"]}],
    }


def _step_plan() -> dict:
    return {
        "packet_type": "EditorialStepPlan",
        "packet_id": "step-plan-001",
        "steps": [
            {
                "op": "insert",
                "track": "v1",
                "clip": "shot-b",
                "at_frame": 100,
            }
        ],
    }


def _success_packet() -> dict:
    """Bridge-shaped operation data from the Pipeline proof contract.

    The referenced Pipeline branch is external to this checkout; this fixture
    preserves the proof's documented packet identity: the full operation data
    remains output, with the receipt packet under ``step_plan_result``.
    """

    return {
        "step_plan_result": {
            "packet_type": "EditorialStepPlanResult",
            "packet_id": "step-result-001",
            "applied_step_count": 1,
        },
        "final_state": {
            "timeline_id": "timeline-001",
            "tracks": [{"id": "v1", "items": ["shot-a", "shot-b"]}],
        },
        "steps": _step_plan()["steps"],
        "deltas": [{"kind": "insert", "clip": "shot-b"}],
    }


def _operation_node(*, arguments: dict | None = None) -> NodeSpec:
    return NodeSpec(
        node_id="apply_steps",
        operator_id="traffik.editorial.apply_steps",
        input_ports=OperationDispatchBoundary.input_ports,
        output_port=OperationDispatchBoundary.output_port,
        config={"arguments": arguments or {"state": _state()}},
    )


@pytest.mark.asyncio
async def test_operation_boundary_uses_edge_step_plan_and_preserves_success_packet():
    calls: list[dict] = []
    source_id = uuid.uuid4()

    async def run_operation(operation_type: str, **kwargs):
        calls.append({"operation_type": operation_type, **kwargs})
        return {"status": "success", "data": _success_packet()}

    boundary = OperationDispatchBoundary(
        run_operation=run_operation,
        run_id=uuid.UUID("00000000-0000-0000-0000-000000000104"),
        artifact_id_factory=lambda: uuid.UUID("00000000-0000-0000-0000-000000000105"),
    )
    result = await boundary.dispatch(
        _operation_node(
            arguments={
                "state": _state(),
                "step_plan": {"ignored": "config loses to edge"},
                "idempotency_key": "idem-104",
                "project_id": "proj-104",
                "requested_by": "bridge-test",
            }
        ),
        {
            "step_plan": NodeResult(
                status="ok",
                run_id=uuid.uuid4(),
                artifact_id=source_id,
                output=_step_plan(),
            )
        },
    )

    assert result.status == "ok"
    assert result.output == _success_packet()
    assert result.output["step_plan_result"]["packet_id"] == "step-result-001"
    assert result.artifact_id == uuid.UUID("00000000-0000-0000-0000-000000000105")
    assert result.source_artifact_ids == (source_id,)
    assert result.resolved_class == RESOLVED_CLASS
    assert calls == [{
        "operation_type": "traffik.editorial.apply_steps",
        "state": _state(),
        "step_plan": _step_plan(),
        "receipt_path": None,
        "idempotency_key": "idem-104",
        "project_id": "proj-104",
        "requested_by": "bridge-test",
    }]


@pytest.mark.asyncio
async def test_operation_boundary_uses_config_step_plan_when_no_edge():
    calls: list[dict] = []

    async def run_operation(operation_type: str, **kwargs):
        calls.append({"operation_type": operation_type, **kwargs})
        return {"status": "success", "data": _success_packet()}

    result = await OperationDispatchBoundary(run_operation=run_operation).dispatch(
        _operation_node(arguments={"state": _state(), "step_plan": _step_plan()}),
        {},
    )

    assert result.status == "ok"
    assert calls[0]["step_plan"] == _step_plan()


@pytest.mark.asyncio
async def test_operation_boundary_maps_failure_to_error_without_output():
    async def run_operation(operation_type: str, **kwargs):
        return SimpleNamespace(
            status="failed",
            error_code="TRAFFIK_STEP_INVALID",
            message="step cannot be applied",
        )

    result = await OperationDispatchBoundary(run_operation=run_operation).dispatch(
        _operation_node(arguments={"state": _state(), "step_plan": _step_plan()}),
        {},
    )

    assert result.status == "error"
    assert result.reason_code == "TRAFFIK_STEP_INVALID"
    assert result.message == "step cannot be applied"
    assert result.output is None
    assert result.control_signal == "skip"


@pytest.mark.asyncio
async def test_operation_boundary_maps_partial_to_partial_with_fidelity():
    async def run_operation(operation_type: str, **kwargs):
        return {
            "status": "partial",
            "data": _success_packet(),
            "partial_fidelity_report": {"missing_steps": 1},
        }

    result = await OperationDispatchBoundary(run_operation=run_operation).dispatch(
        _operation_node(arguments={"state": _state(), "step_plan": _step_plan()}),
        {},
    )

    assert result.status == "partial"
    assert result.fidelity == {"missing_steps": 1}
    assert result.output == _success_packet()


@pytest.mark.asyncio
async def test_operation_boundary_missing_input_is_deterministic_error_not_raise():
    result = await OperationDispatchBoundary(run_operation=lambda *a, **k: None).dispatch(
        _operation_node(arguments={"state": _state()}),
        {},
    )

    assert result.status == "error"
    assert result.reason_code == OPERATION_INPUT_ERROR
    assert "step_plan" in (result.message or "")


@pytest.mark.asyncio
async def test_operation_boundary_missing_runner_is_deterministic_error():
    result = await OperationDispatchBoundary().dispatch(
        _operation_node(arguments={"state": _state(), "step_plan": _step_plan()}),
        {},
    )

    assert result.status == "error"
    assert result.reason_code == OPERATION_UNAVAILABLE


@pytest.mark.asyncio
async def test_operation_boundary_rejects_non_operation_node():
    with pytest.raises(UnsupportedCompositionNodeError):
        await OperationDispatchBoundary(run_operation=lambda *a, **k: None).dispatch(
            NodeSpec(node_id="filter", operator_id="filter"),
            {},
        )


@pytest.mark.asyncio
async def test_unified_dispatch_routes_operation_through_real_graph_executor():
    calls: list[dict] = []

    async def run_operation(operation_type: str, **kwargs):
        calls.append({"operation_type": operation_type, **kwargs})
        return {"status": "success", "data": _success_packet()}

    source = NodeSpec(
        node_id="step_plan",
        operator_id="forge_is_greenscreen",
        output_port=PortTopology.manifest(),
    )
    target = _operation_node(arguments={"state": _state()})
    graph = GraphSpec(
        nodes=(source, target),
        edges=(Edge(from_node="step_plan", to_node="apply_steps", to_port="step_plan"),),
    )

    async def dispatch(node: NodeSpec, resolved_inputs: dict[str, NodeResult]):
        if node.node_id == "step_plan":
            return NodeResult(
                status="ok",
                run_id=uuid.uuid4(),
                artifact_id=uuid.UUID("00000000-0000-0000-0000-000000000201"),
                output=_step_plan(),
                output_topology={"kind": "manifest"},
            )
        return await UnifiedDispatch(
            operation_boundary=OperationDispatchBoundary(run_operation=run_operation)
        ).dispatch(node, resolved_inputs)

    results = await GraphExecutor(dispatch).run(graph)

    assert results["apply_steps"].status == "ok"
    assert results["apply_steps"].resolved_class == RESOLVED_CLASS
    assert calls[0]["operation_type"] == "traffik.editorial.apply_steps"
    assert calls[0]["step_plan"] == _step_plan()


def test_graph_executor_is_byte_stable_vs_main():
    repo = Path(__file__).parents[2]
    diff = subprocess.run(
        ["git", "diff", "main", "--", "forge_bridge/composition/executor.py"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    assert diff.stdout == ""
