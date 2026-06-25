from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from forge_bridge.composition.admission import admit_operator
from forge_bridge.composition.graph_spec import NodeSpec
from forge_bridge.composition.host_resolve_boundary import (
    HELD_FOR_REVIEW,
    HostResolveBoundary,
)
from forge_bridge.composition.node_result import NodeResult


FIXTURE_PATH = (
    Path(__file__).parents[1]
    / "fixtures"
    / "traffik_flame_delta_host_resolve_operation_fixtures.json"
)


def _fixture_cases() -> dict[str, dict]:
    fixture = json.loads(FIXTURE_PATH.read_text())
    return {case["name"]: case for case in fixture["cases"]}


def _project_case(case: dict) -> dict:
    editing = pytest.importorskip("forge_core.traffik.editing")
    return editing.project_flame_delta_host_resolve_payload(case["input"]["delta"])


def _operation_output_from_projection(projection: dict) -> dict:
    return {"flame_delta_host_resolve_payload": projection["output"]}


def _delta_node() -> NodeSpec:
    return NodeSpec(
        node_id="delta_to_manifest",
        operator_id="delta_to_manifest",
        input_ports=HostResolveBoundary.input_ports,
        output_port=HostResolveBoundary.output_port,
    )


def _upstream_result(output: dict) -> NodeResult:
    return NodeResult(
        status="ok",
        run_id=uuid.UUID("00000000-0000-0000-0000-000000000901"),
        artifact_id=uuid.UUID("00000000-0000-0000-0000-000000000902"),
        output=output,
        resolved_class="pipeline.traffik.flame_delta.host_resolve",
    )


def _manifest_dict(apply_tool: str, request: dict) -> dict:
    entry = request["entries"][0]
    identity = dict(entry["metadata"])
    return {
        "type": "mutation_plan",
        "intent_parameters": {"sequence_name": request["sequence_name"]},
        "resolved_plan": [
            {
                "identity": identity,
                "payload": {"shot_name": entry.get("after", {}).get("name")},
            }
        ],
        "originating_capability": apply_tool,
        "apply_counterpart": {
            "tool": apply_tool,
            "parameter_overrides": {"mode": "apply"},
        },
    }


def test_admits_flame_delta_host_resolve_operation():
    record = admit_operator("traffik.flame_delta.host_resolve")

    assert record.dispatch_kind == "operation"
    assert record.resolved_class == "pipeline.traffik.flame_delta.host_resolve"
    assert record.no_state_mutation is True
    assert record.idempotent_result is True


@pytest.mark.asyncio
async def test_host_resolve_unwraps_ready_operation_output_and_routes_delta_entry():
    case = _fixture_cases()["ready_segment_name_delta"]
    projection = _project_case(case)
    expected = case["expected"]
    calls: list[dict] = []

    assert projection["status"] == expected["projection_status"]
    assert projection["reason_code"] == expected["projection_reason_code"]
    assert projection["output"]["payload_kind"] == expected["payload_kind"]
    assert projection["output"]["schema_version"] == 3
    assert len(projection["output"]["deltas"]) == expected["delta_count"]

    async def run_discover(tool_name: str, *, request: dict):
        calls.append({"tool_name": tool_name, "request": request})
        return _manifest_dict(tool_name, request)

    result = await HostResolveBoundary(run_discover=run_discover).dispatch(
        _delta_node(),
        {"deltas": _upstream_result(_operation_output_from_projection(projection))},
    )

    assert result.status == "ok"
    assert calls[0]["tool_name"] == expected["first_delta_executor"]
    assert calls[0]["request"]["sequence_name"] == expected["first_delta_sequence_id"]
    entry = calls[0]["request"]["entries"][0]
    assert entry["action"] == "updated"
    assert "changes" not in entry


@pytest.mark.asyncio
async def test_host_resolve_unwraps_held_operation_output_without_discover():
    case = _fixture_cases()["held_heterogeneous_name_and_frame_in_delta"]
    projection = _project_case(case)
    expected = case["expected"]
    calls: list[dict] = []

    assert projection["status"] == expected["projection_status"]
    assert projection["reason_code"] == expected["projection_reason_code"]
    assert projection["output"]["payload_kind"] == expected["payload_kind"]
    assert projection["output"]["schema_version"] == 3
    assert len(projection["output"]["deltas"]) == expected["delta_count"]

    async def run_discover(tool_name: str, *, request: dict):
        calls.append({"tool_name": tool_name, "request": request})
        return _manifest_dict(tool_name, request)

    result = await HostResolveBoundary(run_discover=run_discover).dispatch(
        _delta_node(),
        {"deltas": _upstream_result(_operation_output_from_projection(projection))},
    )

    assert result.status == "error"
    assert result.reason_code == HELD_FOR_REVIEW
    assert calls == []
