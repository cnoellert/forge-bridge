from __future__ import annotations

import copy
import ast
import json
import subprocess
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

from forge_bridge.composition.commit_boundary import (
    DRIFT_OPERATOR_MESSAGE,
    UNRATIFIED_OPERATOR_MESSAGE,
    CommitBoundary,
)
from forge_bridge.composition.dispatch import UnifiedDispatch
from forge_bridge.composition.executor import GraphExecutor
from forge_bridge.composition.graph_spec import Edge, GraphSpec, NodeSpec
from forge_bridge.composition.host_resolve_boundary import (
    HETEROGENEOUS_DELTA,
    HELD_FOR_REVIEW,
    HOST_DISCOVER_FAILED,
    UNRESOLVED_TARGET,
    UNSUPPORTED_DELTA_ACTION,
    HostResolveBoundary,
)
from forge_bridge.composition.node_result import NodeResult
from forge_bridge.composition.operation_boundary import OperationDispatchBoundary
from forge_bridge.core.assent import AssentRecord
from forge_bridge.graph.commit import CommitError
from forge_bridge.graph.ports import PortContract, PortTopology
import forge_bridge.orchestration.apply_editorial_delta as apply_delta_module


OPERATION_NODE_ID = "apply_steps"
RESOLVE_NODE_ID = "delta_to_manifest"
COMMIT_NODE_ID = "commit"
HOST_RESOLVE_OPERATION_FIXTURE = (
    Path(__file__).parents[1]
    / "fixtures"
    / "traffik_flame_delta_host_resolve_operation_fixtures.json"
)


def _entry(
    *,
    action: str = "updated",
    object_type: str = "segment",
    sequence_name: str = "seq_001",
    after: dict | None = None,
) -> dict:
    return {
        "action": action,
        "object_type": object_type,
        "object_id": "segment-001",
        "before": {"name": "old_name"},
        "after": after or {"name": "new_name"},
        "metadata": {
            "sequence_name": sequence_name,
            "track_idx": 1,
            "record_in": 100,
            "seg_name": "old_name",
            "source_name": "plate_001",
        },
    }


def _timeline_delta(
    *entries: dict,
    sequence_id: str = "seq_001",
    executor: str = "forge_apply_segment_delta",
) -> dict:
    return {
        "type": "timeline_delta",
        "sequence_id": sequence_id,
        "metadata": {
            "executor": executor,
            "group_key": f"{executor}:updated_segment_name",
            "host_resolve_schema_version": 3,
            "sequence_id_policy": "flame_sequence_name",
            "source_delta_sequence_id": "source-seq-001",
        },
        "changes": list(entries or (_entry(),)),
    }


def _projected_host_resolve_payload(
    *entries: dict,
    executor: str = "forge_apply_segment_delta",
) -> dict:
    # The canonical host-resolve contract shape. Some tests still hand-feed it
    # to isolate delta_to_manifest/commit behavior; the select_delta chain below
    # proves the full apply_steps -> host_resolve operation path.
    return {
        "schema_version": 3,
        "payload_kind": "traffik.flame_delta_host_resolve_payload",
        "plan": {
            "reason_code": "flame_delta_apply_plan_ready",
            "output": {
                "summary": {
                    "held_entry_count": 0,
                    "routed_entry_count": len(entries or (_entry(),)),
                },
                "held_entries": [],
            },
        },
        "step_plan_result": {"packet_type": "EditorialStepPlanResult"},
        "deltas": [_timeline_delta(*entries, executor=executor)],
    }


def _operation_fixture_delta(case_name: str = "ready_segment_name_delta") -> dict:
    fixture = json.loads(HOST_RESOLVE_OPERATION_FIXTURE.read_text())
    cases = {case["name"]: case for case in fixture["cases"]}
    return copy.deepcopy(cases[case_name]["input"]["delta"])


def _operation_output_from_fixture_delta(delta: dict) -> dict:
    entries = list(delta["changes"])
    sequence_name = entries[0]["metadata"]["sequence_name"]
    payload = _projected_host_resolve_payload(*entries)
    payload["plan"]["reason_code"] = "flame_delta_host_resolve_ready"
    payload["deltas"][0]["sequence_id"] = sequence_name
    payload["deltas"][0]["metadata"]["source_delta_sequence_id"] = delta["sequence_id"]
    return {"flame_delta_host_resolve_payload": payload}


def _manifest_dict(
    *,
    payload_name: str = "new_name",
    apply_tool: str = "forge_apply_segment_delta",
) -> dict:
    identity = dict(_entry()["metadata"])
    return {
        "type": "mutation_plan",
        "intent_parameters": {"sequence_name": identity["sequence_name"]},
        "resolved_plan": [
            {
                "identity": identity,
                "payload": {"shot_name": payload_name},
            }
        ],
        "originating_capability": "forge_apply_segment_delta",
        "apply_counterpart": {
            "tool": apply_tool,
            "parameter_overrides": {"mode": "apply"},
        },
    }


class _SegmentDeltaMCP:
    def __init__(self, *, fresh_manifest: dict, apply_drift: bool = False):
        self.calls: list[tuple[str, dict]] = []
        self._fresh_manifest = copy.deepcopy(fresh_manifest)
        self._apply_drift = apply_drift

    async def list_tools(self):
        return [
            SimpleNamespace(
                name="forge_apply_segment_delta",
                inputSchema={"type": "object", "properties": {}, "required": []},
            )
        ]

    async def call_tool(self, name: str, arguments: dict):
        self.calls.append((name, copy.deepcopy(arguments)))
        if name != "forge_apply_segment_delta":
            raise AssertionError(name)
        if arguments["mode"] == "verify":
            return copy.deepcopy(self._fresh_manifest)
        if arguments["mode"] == "discover":
            return _manifest_dict()
        if arguments["mode"] == "apply":
            if self._apply_drift:
                return {
                    "drift": True,
                    "error_code": "plan_state_drift",
                    "reason_code": "plan_state_drift",
                }
            return {
                "type": "rename_apply_result",
                "renamed": len(arguments["resolved_plan"]),
            }
        raise AssertionError(arguments["mode"])


def _ratified_assent() -> AssentRecord:
    return AssentRecord(
        graph_intent_id="graph-intent-delta",
        chain_steps=["traffik.editorial.apply_steps", "delta_to_manifest", "commit"],
        status="ratified",
        decided_by="operator",
    )


def _proposed_assent() -> AssentRecord:
    return AssentRecord(
        graph_intent_id="graph-intent-delta",
        chain_steps=["traffik.editorial.apply_steps", "delta_to_manifest", "commit"],
        status="proposed",
    )


def _upstream_result(
    *entries: dict,
    artifact_id: uuid.UUID | None = None,
    executor: str = "forge_apply_segment_delta",
) -> NodeResult:
    return NodeResult(
        status="ok",
        run_id=uuid.uuid4(),
        artifact_id=artifact_id,
        output=_projected_host_resolve_payload(*entries, executor=executor),
    )


def _delta_node() -> NodeSpec:
    return NodeSpec(
        node_id=RESOLVE_NODE_ID,
        operator_id="delta_to_manifest",
        input_ports=HostResolveBoundary.input_ports,
        output_port=HostResolveBoundary.output_port,
    )


@pytest.mark.asyncio
async def test_host_resolve_builds_discover_request_and_forwards_manifest():
    calls: list[dict] = []
    source_id = uuid.UUID("00000000-0000-0000-0000-000000000401")

    async def run_discover(tool_name: str, *, request: dict, **kwargs):
        calls.append({"tool_name": tool_name, "request": request, "kwargs": kwargs})
        return _manifest_dict()

    boundary = HostResolveBoundary(
        run_discover=run_discover,
        run_id=uuid.UUID("00000000-0000-0000-0000-000000000402"),
        artifact_id_factory=lambda: uuid.UUID("00000000-0000-0000-0000-000000000403"),
        project_id="project-001",
    )
    result = await boundary.dispatch(
        _delta_node(),
        {"deltas": _upstream_result(artifact_id=source_id)},
    )

    assert result.status == "ok"
    assert result.output == _manifest_dict()
    assert result.output_topology == {"kind": "manifest"}
    assert result.artifact_id == uuid.UUID("00000000-0000-0000-0000-000000000403")
    assert result.source_artifact_ids == (source_id,)
    assert result.resolved_class == "host.resolve.delta_to_manifest"
    assert calls == [{
        "tool_name": "forge_apply_segment_delta",
        "request": {
            "sequence_name": "seq_001",
            "entries": [_entry()],
        },
        "kwargs": {"project_id": "project-001"},
    }]
    assert "before" in calls[0]["request"]["entries"][0]
    assert "action" in calls[0]["request"]["entries"][0]
    assert "changes" not in calls[0]["request"]["entries"][0]


@pytest.mark.asyncio
async def test_host_resolve_rejects_heterogeneous_executors():
    output = _projected_host_resolve_payload(_entry())
    output["deltas"].append(
        _timeline_delta(
            _entry(),
            executor="forge_apply_segment_temporal_delta",
        )
    )
    upstream = NodeResult(status="ok", run_id=uuid.uuid4(), output=output)

    result = await HostResolveBoundary(run_discover=lambda *a, **k: _manifest_dict()).dispatch(
        _delta_node(),
        {"deltas": upstream},
    )

    assert result.status == "error"
    assert result.reason_code == HETEROGENEOUS_DELTA


@pytest.mark.asyncio
async def test_host_resolve_rejects_multiple_sequence_ids_before_flattening():
    output = _projected_host_resolve_payload(_entry(sequence_name="seq_001"))
    output["deltas"].append(
        _timeline_delta(
            _entry(sequence_name="seq_002"),
            sequence_id="seq_002",
        )
    )
    upstream = NodeResult(
        status="ok",
        run_id=uuid.uuid4(),
        output=output,
    )

    result = await HostResolveBoundary(run_discover=lambda *a, **k: _manifest_dict()).dispatch(
        _delta_node(),
        {"deltas": upstream},
    )

    assert result.status == "error"
    assert result.reason_code == HETEROGENEOUS_DELTA


@pytest.mark.asyncio
async def test_host_resolve_routes_temporal_executor():
    calls: list[dict] = []

    async def run_discover(tool_name: str, *, request: dict):
        calls.append({"tool_name": tool_name, "request": request})
        return _manifest_dict(apply_tool="forge_apply_segment_temporal_delta")

    result = await HostResolveBoundary(run_discover=run_discover).dispatch(
        _delta_node(),
        {
            "deltas": _upstream_result(
                _entry(after={"frame_out": 120}),
                executor="forge_apply_segment_temporal_delta",
            )
        },
    )

    assert result.status == "ok"
    assert result.output["apply_counterpart"]["tool"] == (
        "forge_apply_segment_temporal_delta"
    )
    assert calls[0]["tool_name"] == "forge_apply_segment_temporal_delta"
    assert "action" in calls[0]["request"]["entries"][0]
    assert "changes" not in calls[0]["request"]["entries"][0]


@pytest.mark.asyncio
async def test_host_resolve_routes_start_frame_executor():
    calls: list[dict] = []

    async def run_discover(tool_name: str, *, request: dict):
        calls.append({"tool_name": tool_name, "request": request})
        return _manifest_dict(apply_tool="forge_apply_segment_start_frame_delta")

    result = await HostResolveBoundary(run_discover=run_discover).dispatch(
        _delta_node(),
        {
            "deltas": _upstream_result(
                _entry(after={"start_frame": 1002}),
                executor="forge_apply_segment_start_frame_delta",
            )
        },
    )

    assert result.status == "ok"
    assert result.output["apply_counterpart"]["tool"] == (
        "forge_apply_segment_start_frame_delta"
    )
    assert calls == [
        {
            "tool_name": "forge_apply_segment_start_frame_delta",
            "request": {
                "sequence_name": "seq_001",
                "entries": [_entry(after={"start_frame": 1002})],
            },
        }
    ]


@pytest.mark.asyncio
async def test_host_resolve_routes_insert_executor():
    calls: list[dict] = []
    entry = _entry(action="inserted", after={"name": "SEQ_010_slate"})

    async def run_discover(tool_name: str, *, request: dict):
        calls.append({"tool_name": tool_name, "request": request})
        return _manifest_dict(apply_tool="forge_apply_segment_insert_delta")

    result = await HostResolveBoundary(run_discover=run_discover).dispatch(
        _delta_node(),
        {
            "deltas": _upstream_result(
                entry,
                executor="forge_apply_segment_insert_delta",
            )
        },
    )

    assert result.status == "ok"
    assert result.output["apply_counterpart"]["tool"] == (
        "forge_apply_segment_insert_delta"
    )
    assert calls == [
        {
            "tool_name": "forge_apply_segment_insert_delta",
            "request": {
                "sequence_name": "seq_001",
                "entries": [entry],
            },
        }
    ]


@pytest.mark.asyncio
async def test_host_resolve_rejects_untrusted_executor():
    result = await HostResolveBoundary(run_discover=lambda *a, **k: _manifest_dict()).dispatch(
        _delta_node(),
        {
            "deltas": _upstream_result(executor="forge_unknown_delta_executor")
        },
    )

    assert result.status == "error"
    assert result.reason_code == HOST_DISCOVER_FAILED
    assert "executor 'forge_unknown_delta_executor' not trusted" in (
        result.message or ""
    )


@pytest.mark.asyncio
async def test_host_resolve_reports_held_for_review_before_homogeneity():
    held_output = _projected_host_resolve_payload()
    held_output["deltas"] = []
    held_output["plan"] = {
        "reason_code": "flame_delta_apply_plan_review_required",
        "output": {
            "summary": {"held_entry_count": 1},
            "held_entries": [
                {
                    "reason_code": "segment_temporal_review_required",
                    "message": "duration change needs review",
                }
            ],
        },
    }
    upstream = NodeResult(status="ok", run_id=uuid.uuid4(), output=held_output)

    result = await HostResolveBoundary(run_discover=lambda *a, **k: _manifest_dict()).dispatch(
        _delta_node(),
        {"deltas": upstream},
    )

    assert result.status == "error"
    assert result.reason_code == HELD_FOR_REVIEW
    assert "duration change needs review" in (result.message or "")


@pytest.mark.asyncio
async def test_host_resolve_rejects_non_projected_schema_version():
    output = _projected_host_resolve_payload()
    output["schema_version"] = 2
    upstream = NodeResult(status="ok", run_id=uuid.uuid4(), output=output)

    result = await HostResolveBoundary(run_discover=lambda *a, **k: _manifest_dict()).dispatch(
        _delta_node(),
        {"deltas": upstream},
    )

    assert result.status == "error"
    assert result.reason_code == HOST_DISCOVER_FAILED
    assert "schema_version 3" in (result.message or "")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error_code",
    [
        "identity_unresolved",
        "missing_flame_identity",
        "invalid_flame_identity",
    ],
)
async def test_host_resolve_reports_unresolved_target_for_identity_failures(error_code):
    async def run_discover(_tool_name: str, *, request: dict):
        return {
            "error": {
                "code": error_code,
                "error_code": error_code,
                "reason_code": error_code,
                "message": "target not found",
            }
        }

    result = await HostResolveBoundary(run_discover=run_discover).dispatch(
        _delta_node(),
        {"deltas": _upstream_result()},
    )

    assert result.status == "error"
    assert result.reason_code == UNRESOLVED_TARGET


@pytest.mark.asyncio
async def test_host_resolve_reports_generic_discover_failure_distinctly():
    async def run_discover(_tool_name: str, *, request: dict):
        return {"error": {"code": "transport_error", "message": "bridge down"}}

    result = await HostResolveBoundary(run_discover=run_discover).dispatch(
        _delta_node(),
        {"deltas": _upstream_result()},
    )

    assert result.status == "error"
    assert result.reason_code == HOST_DISCOVER_FAILED
    assert result.reason_code != UNRESOLVED_TARGET


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error_code",
    [
        "unknown_delta_action",
        "object_type_requires_future_executor",
        "segment_inserted_requires_future_executor",
        "segment_removed_requires_future_executor",
        "segment_shifted_requires_future_executor",
        "unknown_segment_fields",
        "no_segment_fields_changed",
    ],
)
async def test_host_resolve_maps_real_unsupported_classifier_codes(error_code):
    async def run_discover(_tool_name: str, *, request: dict):
        return {"error": {"code": error_code, "message": error_code}}

    result = await HostResolveBoundary(run_discover=run_discover).dispatch(
        _delta_node(),
        {"deltas": _upstream_result()},
    )

    assert result.status == "error"
    assert result.reason_code == UNSUPPORTED_DELTA_ACTION


@pytest.mark.asyncio
async def test_host_resolve_enforces_manifest_apply_counterpart_tool():
    async def run_discover(_tool_name: str, *, request: dict):
        return _manifest_dict(apply_tool="wrong_tool")

    result = await HostResolveBoundary(run_discover=run_discover).dispatch(
        _delta_node(),
        {"deltas": _upstream_result()},
    )

    assert result.status == "error"
    assert result.reason_code == HOST_DISCOVER_FAILED
    assert "expected 'forge_apply_segment_delta'" in (result.message or "")


def _three_node_graph() -> GraphSpec:
    return GraphSpec(
        nodes=(
            NodeSpec(
                node_id=OPERATION_NODE_ID,
                operator_id="traffik.editorial.apply_steps",
                output_port=PortTopology.manifest(),
                config={"arguments": {"state": {"timeline": "t1"}, "step_plan": {}}},
            ),
            NodeSpec(
                node_id=RESOLVE_NODE_ID,
                operator_id="delta_to_manifest",
                input_ports=HostResolveBoundary.input_ports,
                output_port=HostResolveBoundary.output_port,
            ),
            NodeSpec(
                node_id=COMMIT_NODE_ID,
                operator_id="commit",
                input_ports={"held": PortContract.manifest_gate()},
            ),
        ),
        edges=(
            Edge(
                from_node=OPERATION_NODE_ID,
                to_node=RESOLVE_NODE_ID,
                to_port="deltas",
            ),
            Edge(
                from_node=RESOLVE_NODE_ID,
                to_node=COMMIT_NODE_ID,
                to_port="held",
            ),
        ),
    )


def _host_resolve_operation_graph(delta: dict) -> GraphSpec:
    return GraphSpec(
        nodes=(
            NodeSpec(
                node_id=OPERATION_NODE_ID,
                operator_id="traffik.flame_delta.host_resolve",
                output_port=PortTopology.manifest(),
                config={"arguments": {"delta": copy.deepcopy(delta)}},
            ),
            NodeSpec(
                node_id=RESOLVE_NODE_ID,
                operator_id="delta_to_manifest",
                input_ports=HostResolveBoundary.input_ports,
                output_port=HostResolveBoundary.output_port,
            ),
            NodeSpec(
                node_id=COMMIT_NODE_ID,
                operator_id="commit",
                input_ports={"held": PortContract.manifest_gate()},
            ),
        ),
        edges=(
            Edge(
                from_node=OPERATION_NODE_ID,
                to_node=RESOLVE_NODE_ID,
                to_port="deltas",
            ),
            Edge(
                from_node=RESOLVE_NODE_ID,
                to_node=COMMIT_NODE_ID,
                to_port="held",
            ),
        ),
    )


def _apply_steps_select_delta_graph() -> GraphSpec:
    return GraphSpec(
        nodes=(
            NodeSpec(
                node_id=OPERATION_NODE_ID,
                operator_id="traffik.editorial.apply_steps",
                output_port=PortTopology.manifest(),
                config={"arguments": {"state": {"timeline": "t1"}, "step_plan": {}}},
            ),
            NodeSpec(
                node_id="select_delta",
                operator_id="select_delta",
                input_ports={"result": PortContract.manifest_gate()},
                output_port=PortTopology.manifest(),
            ),
            NodeSpec(
                node_id="host_resolve",
                operator_id="traffik.flame_delta.host_resolve",
                input_ports={"delta": PortContract.manifest_gate()},
                output_port=PortTopology.manifest(),
            ),
            NodeSpec(
                node_id=RESOLVE_NODE_ID,
                operator_id="delta_to_manifest",
                input_ports=HostResolveBoundary.input_ports,
                output_port=HostResolveBoundary.output_port,
            ),
            NodeSpec(
                node_id=COMMIT_NODE_ID,
                operator_id="commit",
                input_ports={"held": PortContract.manifest_gate()},
            ),
        ),
        edges=(
            Edge(
                from_node=OPERATION_NODE_ID,
                to_node="select_delta",
                to_port="result",
            ),
            Edge(
                from_node="select_delta",
                to_node="host_resolve",
                to_port="delta",
            ),
            Edge(
                from_node="host_resolve",
                to_node=RESOLVE_NODE_ID,
                to_port="deltas",
            ),
            Edge(
                from_node=RESOLVE_NODE_ID,
                to_node=COMMIT_NODE_ID,
                to_port="held",
            ),
        ),
    )


async def _run_three_node_graph(
    *,
    assent_record: AssentRecord,
    fresh_manifest: dict,
):
    operation_calls: list[dict] = []
    discover_calls: list[dict] = []

    async def run_operation(operation_type: str, **kwargs):
        operation_calls.append({"operation_type": operation_type, **kwargs})
        return {"status": "success", "data": _projected_host_resolve_payload()}

    async def run_discover(tool_name: str, *, request: dict):
        discover_calls.append({"tool_name": tool_name, "request": request})
        return _manifest_dict()

    mcp = _SegmentDeltaMCP(fresh_manifest=fresh_manifest)
    dispatch = UnifiedDispatch(
        operation_boundary=OperationDispatchBoundary(run_operation=run_operation),
        host_resolve_boundary=HostResolveBoundary(run_discover=run_discover),
        commit_boundary=CommitBoundary(mcp=mcp),
        assent_record=assent_record,
    )
    results = await GraphExecutor(dispatch.dispatch).run(_three_node_graph())
    return results, operation_calls, discover_calls, mcp


@pytest.mark.asyncio
async def test_three_node_delta_apply_graph_over_projected_input_commits_when_ratified():
    results, operation_calls, discover_calls, mcp = await _run_three_node_graph(
        assent_record=_ratified_assent(),
        fresh_manifest=_manifest_dict(),
    )

    assert results[COMMIT_NODE_ID].status == "ok"
    assert results[COMMIT_NODE_ID].output["type"] == "commit_applied"
    assert results[COMMIT_NODE_ID].output["count"] == 1
    assert operation_calls[0]["operation_type"] == "traffik.editorial.apply_steps"
    assert discover_calls[0]["tool_name"] == "forge_apply_segment_delta"
    assert results[RESOLVE_NODE_ID].output["apply_counterpart"]["tool"] == (
        "forge_apply_segment_delta"
    )
    assert [(name, args["mode"]) for name, args in mcp.calls] == [
        ("forge_apply_segment_delta", "verify"),
        ("forge_apply_segment_delta", "apply"),
    ]
    assert results[COMMIT_NODE_ID].source_artifact_ids == (
        results[RESOLVE_NODE_ID].artifact_id,
    )


@pytest.mark.asyncio
async def test_host_resolve_operation_delta_param_graph_commits_when_ratified():
    delta = _operation_fixture_delta()
    operation_calls: list[dict] = []
    discover_calls: list[dict] = []

    async def run_operation(operation_type: str, *, params: dict, **kwargs):
        operation_calls.append({
            "operation_type": operation_type,
            "params": copy.deepcopy(params),
            "kwargs": kwargs,
        })
        return {
            "status": "success",
            "data": _operation_output_from_fixture_delta(params["delta"]),
        }

    async def run_discover(tool_name: str, *, request: dict):
        discover_calls.append({"tool_name": tool_name, "request": request})
        return _manifest_dict()

    mcp = _SegmentDeltaMCP(fresh_manifest=_manifest_dict())
    dispatch = UnifiedDispatch(
        operation_boundary=OperationDispatchBoundary(run_operation=run_operation),
        host_resolve_boundary=HostResolveBoundary(run_discover=run_discover),
        commit_boundary=CommitBoundary(mcp=mcp),
        assent_record=_ratified_assent(),
    )
    results = await GraphExecutor(dispatch.dispatch).run(
        _host_resolve_operation_graph(delta)
    )

    assert operation_calls[0]["operation_type"] == "traffik.flame_delta.host_resolve"
    assert operation_calls[0]["params"] == {"delta": delta}
    assert results[RESOLVE_NODE_ID].status == "ok"
    assert discover_calls[0]["tool_name"] == "forge_apply_segment_delta"
    entry = discover_calls[0]["request"]["entries"][0]
    assert entry["action"] == "updated"
    assert "changes" not in entry
    assert results[COMMIT_NODE_ID].status == "ok"
    assert results[COMMIT_NODE_ID].output["type"] == "commit_applied"
    assert [(name, args["mode"]) for name, args in mcp.calls] == [
        ("forge_apply_segment_delta", "verify"),
        ("forge_apply_segment_delta", "apply"),
    ]


@pytest.mark.asyncio
async def test_apply_steps_select_delta_host_resolve_graph_commits_when_ratified():
    delta = _operation_fixture_delta()
    operation_calls: list[dict] = []
    discover_calls: list[dict] = []

    async def run_operation(operation_type: str, *, params: dict, **kwargs):
        operation_calls.append({
            "operation_type": operation_type,
            "params": copy.deepcopy(params),
            "kwargs": kwargs,
        })
        if operation_type == "traffik.editorial.apply_steps":
            return {
                "status": "success",
                "data": {
                    "state": params["state"],
                    "step_plan": params["step_plan"],
                    "deltas": [copy.deepcopy(delta)],
                },
            }
        if operation_type == "traffik.flame_delta.host_resolve":
            return {
                "status": "success",
                "data": _operation_output_from_fixture_delta(params["delta"]),
            }
        raise AssertionError(operation_type)

    async def run_discover(tool_name: str, *, request: dict):
        discover_calls.append({"tool_name": tool_name, "request": request})
        return _manifest_dict()

    mcp = _SegmentDeltaMCP(fresh_manifest=_manifest_dict())
    dispatch = UnifiedDispatch(
        operation_boundary=OperationDispatchBoundary(run_operation=run_operation),
        host_resolve_boundary=HostResolveBoundary(run_discover=run_discover),
        commit_boundary=CommitBoundary(mcp=mcp),
        assent_record=_ratified_assent(),
    )
    results = await GraphExecutor(dispatch.dispatch).run(
        _apply_steps_select_delta_graph()
    )

    assert [call["operation_type"] for call in operation_calls] == [
        "traffik.editorial.apply_steps",
        "traffik.flame_delta.host_resolve",
    ]
    assert operation_calls[1]["params"] == {"delta": delta}
    assert results["select_delta"].output == delta
    assert results["host_resolve"].status == "ok"
    assert results[RESOLVE_NODE_ID].status == "ok"
    assert discover_calls[0]["tool_name"] == "forge_apply_segment_delta"
    assert results[COMMIT_NODE_ID].status == "ok"
    assert results[COMMIT_NODE_ID].output["type"] == "commit_applied"
    assert [(name, args["mode"]) for name, args in mcp.calls] == [
        ("forge_apply_segment_delta", "verify"),
        ("forge_apply_segment_delta", "apply"),
    ]


@pytest.mark.asyncio
async def test_three_node_delta_apply_graph_over_projected_input_requires_ratified_assent():
    results, _operation_calls, _discover_calls, mcp = await _run_three_node_graph(
        assent_record=_proposed_assent(),
        fresh_manifest=_manifest_dict(),
    )

    assert results[COMMIT_NODE_ID].status == "error"
    assert results[COMMIT_NODE_ID].reason_code == CommitError.ASSENT_INVALID
    assert results[COMMIT_NODE_ID].message == UNRATIFIED_OPERATOR_MESSAGE
    assert [(name, args["mode"]) for name, args in mcp.calls] == [
        ("forge_apply_segment_delta", "verify"),
    ]


@pytest.mark.asyncio
async def test_three_node_delta_apply_graph_over_projected_input_reports_plan_state_drift():
    results, _operation_calls, _discover_calls, mcp = await _run_three_node_graph(
        assent_record=_ratified_assent(),
        fresh_manifest=_manifest_dict(payload_name="drifted_name"),
    )

    assert results[COMMIT_NODE_ID].status == "error"
    assert results[COMMIT_NODE_ID].reason_code == CommitError.PLAN_STATE_DRIFT
    assert results[COMMIT_NODE_ID].message == DRIFT_OPERATOR_MESSAGE
    assert [(name, args["mode"]) for name, args in mcp.calls] == [
        ("forge_apply_segment_delta", "verify"),
    ]


@pytest.mark.asyncio
async def test_three_node_delta_apply_graph_over_projected_input_reports_apply_drift_signal():
    async def run_operation(operation_type: str, **kwargs):
        return {"status": "success", "data": _projected_host_resolve_payload()}

    async def run_discover(tool_name: str, *, request: dict):
        return _manifest_dict()

    mcp = _SegmentDeltaMCP(fresh_manifest=_manifest_dict(), apply_drift=True)
    dispatch = UnifiedDispatch(
        operation_boundary=OperationDispatchBoundary(run_operation=run_operation),
        host_resolve_boundary=HostResolveBoundary(run_discover=run_discover),
        commit_boundary=CommitBoundary(mcp=mcp),
        assent_record=_ratified_assent(),
    )

    results = await GraphExecutor(dispatch.dispatch).run(_three_node_graph())

    assert results[COMMIT_NODE_ID].status == "error"
    assert results[COMMIT_NODE_ID].reason_code == CommitError.PLAN_STATE_DRIFT
    assert [(name, args["mode"]) for name, args in mcp.calls] == [
        ("forge_apply_segment_delta", "verify"),
        ("forge_apply_segment_delta", "apply"),
    ]


@pytest.mark.asyncio
async def test_apply_editorial_delta_over_projected_input_uses_discover_verify_apply(
    monkeypatch,
):
    async def operation_runner(operation_type: str, **kwargs):
        return {"status": "success", "data": _projected_host_resolve_payload()}

    monkeypatch.setattr(
        apply_delta_module,
        "build_operation_runner",
        lambda *args, **kwargs: operation_runner,
    )
    mcp = _SegmentDeltaMCP(fresh_manifest=_manifest_dict())

    results = await apply_delta_module.apply_editorial_delta(
        _three_node_graph(),
        assent_record=_ratified_assent(),
        mcp=mcp,
    )

    assert results[COMMIT_NODE_ID].status == "ok"
    assert [(name, args["mode"]) for name, args in mcp.calls] == [
        ("forge_apply_segment_delta", "discover"),
        ("forge_apply_segment_delta", "verify"),
        ("forge_apply_segment_delta", "apply"),
    ]
    assert mcp.calls[0][1]["sequence_name"] == "seq_001"
    assert mcp.calls[0][1]["entries"] == [_entry()]


@pytest.mark.asyncio
async def test_apply_editorial_delta_selects_delta_before_host_resolve(
    monkeypatch,
):
    delta = _operation_fixture_delta()
    operation_calls: list[dict] = []

    async def operation_runner(operation_type: str, *, params: dict, **kwargs):
        operation_calls.append({
            "operation_type": operation_type,
            "params": copy.deepcopy(params),
            "kwargs": kwargs,
        })
        if operation_type == "traffik.editorial.apply_steps":
            return {
                "status": "success",
                "data": {
                    "state": params["state"],
                    "step_plan": params["step_plan"],
                    "deltas": [copy.deepcopy(delta)],
                },
            }
        if operation_type == "traffik.flame_delta.host_resolve":
            return {
                "status": "success",
                "data": _operation_output_from_fixture_delta(params["delta"]),
            }
        raise AssertionError(operation_type)

    monkeypatch.setattr(
        apply_delta_module,
        "build_operation_runner",
        lambda *args, **kwargs: operation_runner,
    )
    mcp = _SegmentDeltaMCP(fresh_manifest=_manifest_dict())

    results = await apply_delta_module.apply_editorial_delta(
        _apply_steps_select_delta_graph(),
        assent_record=_ratified_assent(),
        mcp=mcp,
    )

    assert [call["operation_type"] for call in operation_calls] == [
        "traffik.editorial.apply_steps",
        "traffik.flame_delta.host_resolve",
    ]
    assert operation_calls[1]["params"] == {"delta": delta}
    assert results["select_delta"].status == "ok"
    assert results["host_resolve"].status == "ok"
    assert results[COMMIT_NODE_ID].status == "ok"
    assert [(name, args["mode"]) for name, args in mcp.calls] == [
        ("forge_apply_segment_delta", "discover"),
        ("forge_apply_segment_delta", "verify"),
        ("forge_apply_segment_delta", "apply"),
    ]


@pytest.mark.asyncio
async def test_reapply_same_ratified_assent_over_projected_input_fails_closed(
    monkeypatch,
):
    async def operation_runner(operation_type: str, **kwargs):
        return {"status": "success", "data": _projected_host_resolve_payload()}

    monkeypatch.setattr(
        apply_delta_module,
        "build_operation_runner",
        lambda *args, **kwargs: operation_runner,
    )

    post_rename_manifest = _manifest_dict()
    post_rename_manifest["resolved_plan"][0]["identity"]["seg_name"] = "new_name"

    class _ReapplyMCP(_SegmentDeltaMCP):
        def __init__(self):
            super().__init__(fresh_manifest=_manifest_dict())
            self._applied = False

        async def call_tool(self, name: str, arguments: dict):
            if arguments["mode"] == "verify" and self._applied:
                self.calls.append((name, copy.deepcopy(arguments)))
                return copy.deepcopy(post_rename_manifest)
            result = await super().call_tool(name, arguments)
            if arguments["mode"] == "apply":
                self._applied = True
            return result

    mcp = _ReapplyMCP()
    assent = _ratified_assent()

    first_results = await apply_delta_module.apply_editorial_delta(
        _three_node_graph(),
        assent_record=assent,
        mcp=mcp,
    )
    second_results = await apply_delta_module.apply_editorial_delta(
        _three_node_graph(),
        assent_record=assent,
        mcp=mcp,
    )

    assert first_results[COMMIT_NODE_ID].status == "ok"
    assert second_results[COMMIT_NODE_ID].status == "error"
    assert second_results[COMMIT_NODE_ID].reason_code in {
        CommitError.PLAN_STATE_DRIFT,
        CommitError.MUTATION_MANIFEST_INVALID,
    }
    assert [args["mode"] for _name, args in mcp.calls].count("apply") == 1


@pytest.mark.asyncio
async def test_preview_editorial_delta_over_projected_input_resolves_without_applying(
    monkeypatch,
):
    async def operation_runner(operation_type: str, **kwargs):
        return {"status": "success", "data": _projected_host_resolve_payload()}

    monkeypatch.setattr(
        apply_delta_module,
        "build_operation_runner",
        lambda *args, **kwargs: operation_runner,
    )
    mcp = _SegmentDeltaMCP(fresh_manifest=_manifest_dict())

    results = await apply_delta_module.preview_editorial_delta(
        _three_node_graph(),
        mcp=mcp,
    )

    # The resolve node is the operator preview: a real manifest.
    assert results[RESOLVE_NODE_ID].status == "ok"
    assert results[RESOLVE_NODE_ID].output["apply_counterpart"]["tool"] == (
        "forge_apply_segment_delta"
    )
    # No assent -> commit verifies but fail-closes; the host is never mutated.
    assert results[COMMIT_NODE_ID].status == "error"
    assert "apply" not in [args["mode"] for _name, args in mcp.calls]


@pytest.mark.asyncio
async def test_apply_editorial_delta_over_projected_input_writes_3layer_receipt(
    tmp_path,
    monkeypatch,
):
    async def operation_runner(operation_type: str, **kwargs):
        return {"status": "success", "data": _projected_host_resolve_payload()}

    monkeypatch.setattr(
        apply_delta_module,
        "build_operation_runner",
        lambda *args, **kwargs: operation_runner,
    )
    mcp = _SegmentDeltaMCP(fresh_manifest=_manifest_dict())
    assent = _ratified_assent()
    spec = _three_node_graph()

    results = await apply_delta_module.apply_editorial_delta(
        spec,
        assent_record=assent,
        mcp=mcp,
        receipt_dir=tmp_path,
    )

    assert results[COMMIT_NODE_ID].status == "ok"
    receipt_path = tmp_path / f"{assent.id}.json"
    assert receipt_path.exists()
    import json as _json

    receipt = _json.loads(receipt_path.read_text())
    assert receipt["assent_record_id"] == str(assent.id)
    assert receipt["graph_intent_id"] == "graph-intent-delta"
    assert receipt["target_host"] == "flame"
    assert receipt["target_sequence_id"] == "seq_001"
    assert receipt["apply_result"]["renamed"] == 1
    # captured, not asserted-as-literal: derived from the operation node's operator_id.
    operation_operator_id = next(
        node.operator_id for node in spec.nodes if node.node_id == OPERATION_NODE_ID
    )
    assert receipt["source_operation_type"] == operation_operator_id
    assert receipt["manifest"]["apply_counterpart"]["tool"] == "forge_apply_segment_delta"


@pytest.mark.asyncio
async def test_preview_editorial_delta_over_projected_input_writes_no_receipt(
    tmp_path,
    monkeypatch,
):
    async def operation_runner(operation_type: str, **kwargs):
        return {"status": "success", "data": _projected_host_resolve_payload()}

    monkeypatch.setattr(
        apply_delta_module,
        "build_operation_runner",
        lambda *args, **kwargs: operation_runner,
    )
    mcp = _SegmentDeltaMCP(fresh_manifest=_manifest_dict())

    await apply_delta_module.preview_editorial_delta(
        _three_node_graph(),
        mcp=mcp,
        receipt_dir=tmp_path,
    )

    assert list(tmp_path.iterdir()) == []


def test_composition_imports_no_peer_host_packages():
    banned_roots = {"forge_core", "traffik", "flame"}
    violations: list[str] = []
    for path in sorted(Path("forge_bridge/composition").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for name in names:
                if name.split(".", 1)[0] in banned_roots:
                    violations.append(f"{path}:{name}")
    assert violations == []


def test_executor_is_byte_stable_and_public_all_unchanged():
    import forge_bridge

    diff = subprocess.run(
        ["git", "diff", "--exit-code", "--", "forge_bridge/composition/executor.py"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert diff.stdout == ""
    assert diff.returncode == 0
    assert len(forge_bridge.__all__) == 19


@pytest.mark.asyncio
async def test_host_resolve_rejects_manifest_naming_a_different_tool():
    """Catch #1: Bridge owns ``apply_counterpart`` (convergence Q1), never the
    injected adapter.

    The boundary resolves the apply tool from its OWN ``_APPLY_TOOL_BY_DELTA_CLASS``
    map ((updated, segment) -> flame_rename_shots) and calls ``run_discover`` with
    it. If the returned manifest names a DIFFERENT tool, forwarding it unchecked
    lets the adapter override Bridge's host-tool decision: CommitBoundary derives
    its verify/apply tool from ``held.apply_counterpart["tool"]``, so held-discover
    and fresh-verify would silently diverge onto two tools. The boundary must
    reject the divergence rather than trust the injected runner.
    """

    async def run_discover(tool_name: str, *, request: dict, **kwargs):
        # tool_name is "flame_rename_shots" (Bridge-resolved), but the runner
        # returns a manifest naming a different tool.
        manifest = _manifest_dict()
        manifest["apply_counterpart"]["tool"] = "flame_create_reel"
        manifest["originating_capability"] = "flame_create_reel"
        return manifest

    result = await HostResolveBoundary(run_discover=run_discover).dispatch(
        _delta_node(),
        {"deltas": _upstream_result()},
    )

    # Today this passes through as status="ok" carrying the wrong tool downstream.
    assert result.status == "error"
    assert "flame_create_reel" in (result.message or "")
