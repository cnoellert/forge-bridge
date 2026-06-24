from __future__ import annotations

import copy
import ast
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


OPERATION_NODE_ID = "apply_steps"
RESOLVE_NODE_ID = "delta_to_manifest"
COMMIT_NODE_ID = "commit"


def _entry(
    *,
    action: str = "updated",
    object_type: str = "segment",
    after: dict | None = None,
) -> dict:
    return {
        "action": action,
        "object_type": object_type,
        "object_id": "segment-001",
        "before": {"name": "old_name"},
        "after": after or {"name": "new_name"},
        "metadata": {
            "sequence_name": "seq_001",
            "track_idx": 1,
            "record_in": 100,
            "seg_name": "old_name",
            "source_name": "plate_001",
        },
    }


def _timeline_delta(*entries: dict, sequence_id: str = "seq_001") -> dict:
    return {
        "type": "timeline_delta",
        "sequence_id": sequence_id,
        "changes": list(entries or (_entry(),)),
    }


def _operation_output(*entries: dict) -> dict:
    return {
        "step_plan_result": {"packet_type": "EditorialStepPlanResult"},
        "deltas": [_timeline_delta(*entries)],
    }


def _manifest_dict(
    *,
    payload_name: str = "new_name",
    apply_tool: str = "flame_rename_shots",
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
        "originating_capability": "flame_rename_shots",
        "apply_counterpart": {
            "tool": apply_tool,
            "parameter_overrides": {},
        },
    }


class _RenameMCP:
    def __init__(self, *, fresh_manifest: dict):
        self.calls: list[tuple[str, dict]] = []
        self._fresh_manifest = copy.deepcopy(fresh_manifest)

    async def list_tools(self):
        return [
            SimpleNamespace(
                name="flame_rename_shots",
                inputSchema={"type": "object", "properties": {}, "required": []},
            )
        ]

    async def call_tool(self, name: str, arguments: dict):
        self.calls.append((name, copy.deepcopy(arguments)))
        if name != "flame_rename_shots":
            raise AssertionError(name)
        if arguments["mode"] == "verify":
            return copy.deepcopy(self._fresh_manifest)
        if arguments["mode"] == "apply":
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


def _upstream_result(*entries: dict, artifact_id: uuid.UUID | None = None) -> NodeResult:
    return NodeResult(
        status="ok",
        run_id=uuid.uuid4(),
        artifact_id=artifact_id,
        output=_operation_output(*entries),
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
        "tool_name": "flame_rename_shots",
        "request": {
            "sequence_name": "seq_001",
            "entries": [{
                "identity": _entry()["metadata"],
                "intent": {"name": "new_name"},
            }]
        },
        "kwargs": {"project_id": "project-001"},
    }]
    assert "before" not in calls[0]["request"]["entries"][0]


@pytest.mark.asyncio
async def test_host_resolve_rejects_heterogeneous_delta_classes():
    result = await HostResolveBoundary(run_discover=lambda *a, **k: _manifest_dict()).dispatch(
        _delta_node(),
        {
            "deltas": _upstream_result(
                _entry(),
                _entry(action="inserted", object_type="segment"),
            )
        },
    )

    assert result.status == "error"
    assert result.reason_code == HETEROGENEOUS_DELTA


@pytest.mark.asyncio
async def test_host_resolve_rejects_multiple_sequence_ids_before_flattening():
    upstream = NodeResult(
        status="ok",
        run_id=uuid.uuid4(),
        output={
            "deltas": [
                _timeline_delta(_entry(), sequence_id="seq_001"),
                _timeline_delta(_entry(), sequence_id="seq_002"),
            ]
        },
    )

    result = await HostResolveBoundary(run_discover=lambda *a, **k: _manifest_dict()).dispatch(
        _delta_node(),
        {"deltas": upstream},
    )

    assert result.status == "error"
    assert result.reason_code == HETEROGENEOUS_DELTA


@pytest.mark.asyncio
async def test_host_resolve_rejects_unmapped_delta_action():
    result = await HostResolveBoundary(run_discover=lambda *a, **k: _manifest_dict()).dispatch(
        _delta_node(),
        {"deltas": _upstream_result(_entry(action="inserted", object_type="segment"))},
    )

    assert result.status == "error"
    assert result.reason_code == UNSUPPORTED_DELTA_ACTION


@pytest.mark.asyncio
async def test_host_resolve_reports_unresolved_target_for_discover_failure():
    async def run_discover(_tool_name: str, *, request: dict):
        return {
            "error": {
                "code": "identity_unresolved",
                "error_code": "identity_unresolved",
                "reason_code": "identity_unresolved",
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
async def test_host_resolve_enforces_manifest_apply_counterpart_tool():
    async def run_discover(_tool_name: str, *, request: dict):
        return _manifest_dict(apply_tool="wrong_tool")

    result = await HostResolveBoundary(run_discover=run_discover).dispatch(
        _delta_node(),
        {"deltas": _upstream_result()},
    )

    assert result.status == "error"
    assert result.reason_code == HOST_DISCOVER_FAILED
    assert "expected 'flame_rename_shots'" in (result.message or "")


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


async def _run_three_node_graph(
    *,
    assent_record: AssentRecord,
    fresh_manifest: dict,
):
    operation_calls: list[dict] = []
    discover_calls: list[dict] = []

    async def run_operation(operation_type: str, **kwargs):
        operation_calls.append({"operation_type": operation_type, **kwargs})
        return {"status": "success", "data": _operation_output()}

    async def run_discover(tool_name: str, *, request: dict):
        discover_calls.append({"tool_name": tool_name, "request": request})
        return _manifest_dict()

    mcp = _RenameMCP(fresh_manifest=fresh_manifest)
    dispatch = UnifiedDispatch(
        operation_boundary=OperationDispatchBoundary(run_operation=run_operation),
        host_resolve_boundary=HostResolveBoundary(run_discover=run_discover),
        commit_boundary=CommitBoundary(mcp=mcp),
        assent_record=assent_record,
    )
    results = await GraphExecutor(dispatch.dispatch).run(_three_node_graph())
    return results, operation_calls, discover_calls, mcp


@pytest.mark.asyncio
async def test_three_node_delta_apply_graph_commits_when_ratified():
    results, operation_calls, discover_calls, mcp = await _run_three_node_graph(
        assent_record=_ratified_assent(),
        fresh_manifest=_manifest_dict(),
    )

    assert results[COMMIT_NODE_ID].status == "ok"
    assert results[COMMIT_NODE_ID].output["type"] == "commit_applied"
    assert results[COMMIT_NODE_ID].output["count"] == 1
    assert operation_calls[0]["operation_type"] == "traffik.editorial.apply_steps"
    assert discover_calls[0]["tool_name"] == "flame_rename_shots"
    assert [(name, args["mode"]) for name, args in mcp.calls] == [
        ("flame_rename_shots", "verify"),
        ("flame_rename_shots", "apply"),
    ]
    assert results[COMMIT_NODE_ID].source_artifact_ids == (
        results[RESOLVE_NODE_ID].artifact_id,
    )


@pytest.mark.asyncio
async def test_three_node_delta_apply_graph_requires_ratified_assent():
    results, _operation_calls, _discover_calls, mcp = await _run_three_node_graph(
        assent_record=_proposed_assent(),
        fresh_manifest=_manifest_dict(),
    )

    assert results[COMMIT_NODE_ID].status == "error"
    assert results[COMMIT_NODE_ID].reason_code == CommitError.ASSENT_INVALID
    assert results[COMMIT_NODE_ID].message == UNRATIFIED_OPERATOR_MESSAGE
    assert [(name, args["mode"]) for name, args in mcp.calls] == [
        ("flame_rename_shots", "verify"),
    ]


@pytest.mark.asyncio
async def test_three_node_delta_apply_graph_reports_plan_state_drift():
    results, _operation_calls, _discover_calls, mcp = await _run_three_node_graph(
        assent_record=_ratified_assent(),
        fresh_manifest=_manifest_dict(payload_name="drifted_name"),
    )

    assert results[COMMIT_NODE_ID].status == "error"
    assert results[COMMIT_NODE_ID].reason_code == CommitError.PLAN_STATE_DRIFT
    assert results[COMMIT_NODE_ID].message == DRIFT_OPERATOR_MESSAGE
    assert [(name, args["mode"]) for name, args in mcp.calls] == [
        ("flame_rename_shots", "verify"),
    ]


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
