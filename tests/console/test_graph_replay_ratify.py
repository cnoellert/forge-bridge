from __future__ import annotations

import copy
from types import SimpleNamespace

import pytest

from forge_bridge.composition.graph_spec import Edge, GraphSpec, NodeSpec
from forge_bridge.composition.host_resolve_boundary import HostResolveBoundary
from forge_bridge.console._chat_compile import run_apply_branch
from forge_bridge.console.handlers import _apply_complete_body
from forge_bridge.core.assent import AssentRecord
from forge_bridge.graph.commit import CommitError
from forge_bridge.graph.ports import PortTopology
from forge_bridge.orchestration import apply_editorial_delta as apply_delta_module
from forge_bridge.store.assent_record_repo import AssentRecordRepo


def _entry(*, segment_name: str = "old_name", payload_name: str = "new_name") -> dict:
    return {
        "action": "updated",
        "object_type": "segment",
        "object_id": "segment-001",
        "before": {"name": segment_name},
        "after": {"name": payload_name},
        "metadata": {
            "sequence_name": "seq_001",
            "track_idx": 1,
            "record_in": 100,
            "seg_name": segment_name,
            "source_name": "plate_001",
        },
    }


def _projected_host_resolve_payload() -> dict:
    return {
        "schema_version": 3,
        "payload_kind": "traffik.flame_delta_host_resolve_payload",
        "plan": {
            "reason_code": "flame_delta_host_resolve_ready",
            "output": {
                "summary": {"held_entry_count": 0, "routed_entry_count": 1},
                "held_entries": [],
            },
        },
        "deltas": [{
            "type": "timeline_delta",
            "sequence_id": "seq_001",
            "metadata": {
                "executor": "forge_apply_segment_delta",
                "group_key": "forge_apply_segment_delta:updated_segment_name",
                "host_resolve_schema_version": 3,
                "sequence_id_policy": "flame_sequence_name",
                "source_delta_sequence_id": "source-seq-001",
            },
            "changes": [_entry()],
        }],
    }


def _manifest_dict(*, payload_name: str = "new_name") -> dict:
    identity = dict(_entry()["metadata"])
    return {
        "type": "mutation_plan",
        "intent_parameters": {"sequence_name": identity["sequence_name"]},
        "resolved_plan": [{
            "identity": identity,
            "payload": {"shot_name": payload_name},
        }],
        "originating_capability": "forge_apply_segment_delta",
        "apply_counterpart": {
            "tool": "forge_apply_segment_delta",
            "parameter_overrides": {"mode": "apply"},
        },
    }


def _preview_graph() -> GraphSpec:
    return GraphSpec(
        nodes=(
            NodeSpec(
                node_id="operation",
                operator_id="traffik.flame_delta.host_resolve",
                output_port=PortTopology.manifest(),
                config={"arguments": {"delta": {"type": "timeline_delta"}}},
            ),
            NodeSpec(
                node_id="delta_to_manifest",
                operator_id="delta_to_manifest",
                input_ports=HostResolveBoundary.input_ports,
                output_port=HostResolveBoundary.output_port,
            ),
        ),
        edges=(
            Edge(
                from_node="operation",
                to_node="delta_to_manifest",
                to_port="deltas",
            ),
        ),
    )


class _GraphReplayMCP:
    def __init__(self, *, fresh_manifest: dict | None = None):
        self.calls: list[tuple[str, dict]] = []
        self._fresh_manifest = copy.deepcopy(fresh_manifest or _manifest_dict())

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
        if arguments["mode"] == "apply":
            return {"type": "rename_apply_result", "renamed": 1}
        raise AssertionError(arguments["mode"])


@pytest.mark.asyncio
async def test_preview_persists_graph_replay_before_ratify(session_factory, monkeypatch):
    operation_calls: list[dict] = []

    async def operation_runner(operation_type: str, *, params: dict, **kwargs):
        operation_calls.append({"operation_type": operation_type, "params": params})
        return {
            "status": "success",
            "data": {
                "flame_delta_host_resolve_payload": _projected_host_resolve_payload()
            },
        }

    async def run_discover(tool_name: str, *, request: dict):
        assert tool_name == "forge_apply_segment_delta"
        return _manifest_dict()

    monkeypatch.setattr(
        apply_delta_module,
        "build_operation_runner",
        lambda *args, **kwargs: operation_runner,
    )

    preview = await apply_delta_module.preview_editorial_delta_for_ratification(
        _preview_graph(),
        session_factory=session_factory,
        run_discover=run_discover,
        mcp=_GraphReplayMCP(),
    )

    async with session_factory() as session:
        repo = AssentRecordRepo(session)
        record = await repo.get_by_graph_intent_id(preview["graph_intent_id"])

    assert operation_calls[0]["operation_type"] == "traffik.flame_delta.host_resolve"
    assert preview["operator_display"]["label"] == (
        "Graph intent: editorial delta apply"
    )
    assert preview["summary"]["manifest"]["apply_tool"] == "forge_apply_segment_delta"
    assert record is not None
    assert record.status == "proposed"
    assert record.chain_steps == [
        "operation:traffik.flame_delta.host_resolve",
        "delta_to_manifest:delta_to_manifest",
    ]
    replay = record.metadata["graph_replay"]
    assert replay["kind"] == "graph_host_mutation"
    assert replay["schema_version"] == 1
    assert replay["held_manifest"] == _manifest_dict()
    assert replay["display"] == "editorial delta apply"


@pytest.mark.asyncio
async def test_ratify_graph_replay_uses_persisted_manifest_not_chain_steps(
    session_factory,
):
    graph_replay = apply_delta_module.build_graph_replay_metadata(
        held_manifest=_manifest_dict()
    )
    async with session_factory() as session:
        repo = AssentRecordRepo(session)
        record = await repo.propose(
            ["poison_tool", "commit"],
            metadata={"graph_replay": graph_replay},
        )
        await session.commit()

    mcp = _GraphReplayMCP()
    outcome = await run_apply_branch(
        graph_intent_id=record.graph_intent_id,
        session_factory=session_factory,
        tools=[],
        mcp=mcp,
        request_id="req-graph-replay",
        client_ip="127.0.0.1",
        started=0.0,
        actor="operator",
    )

    assert outcome.regime == "apply_complete"
    assert [(name, args["mode"]) for name, args in mcp.calls] == [
        ("forge_apply_segment_delta", "verify"),
        ("forge_apply_segment_delta", "apply"),
    ]
    assert mcp.calls[0][1]["resolved_plan"] == _manifest_dict()["resolved_plan"]
    assert outcome.assent_record["metadata"]["graph_replay"] == graph_replay

    body = _apply_complete_body(outcome, "json")
    assert body["count"] == 1
    assert body["graph_intent"]["label"] == "Graph intent: editorial delta apply"
    assert body["graph_intent"]["manifest_summary"]["resolved_count"] == 1

    async with session_factory() as session:
        repo = AssentRecordRepo(session)
        applied = await repo.get_by_graph_intent_id(record.graph_intent_id)

    assert applied.status == "applied"
    assert applied.apply_result["status"] == "success"
    assert applied.metadata["graph_replay"]["held_manifest"] == _manifest_dict()


@pytest.mark.asyncio
async def test_ratify_graph_replay_drift_fails_without_apply(session_factory):
    graph_replay = apply_delta_module.build_graph_replay_metadata(
        held_manifest=_manifest_dict()
    )
    async with session_factory() as session:
        repo = AssentRecordRepo(session)
        record = await repo.propose(
            ["poison_tool", "commit"],
            metadata={"graph_replay": graph_replay},
        )
        await session.commit()

    mcp = _GraphReplayMCP(fresh_manifest=_manifest_dict(payload_name="drifted"))
    outcome = await run_apply_branch(
        graph_intent_id=record.graph_intent_id,
        session_factory=session_factory,
        tools=[],
        mcp=mcp,
        request_id="req-graph-replay-drift",
        client_ip="127.0.0.1",
        started=0.0,
        actor="operator",
    )

    assert outcome.regime == "chain_aborted"
    assert outcome.chain_body["error"]["original_error"]["type"] == (
        CommitError.PLAN_STATE_DRIFT
    )
    assert [(name, args["mode"]) for name, args in mcp.calls] == [
        ("forge_apply_segment_delta", "verify"),
    ]

    async with session_factory() as session:
        repo = AssentRecordRepo(session)
        failed = await repo.get_by_graph_intent_id(record.graph_intent_id)

    assert failed.status == "failed"
    assert failed.apply_failure_reason == "drift_invalid"


@pytest.mark.asyncio
async def test_invalid_graph_replay_does_not_fall_back_to_chain_steps(session_factory):
    async with session_factory() as session:
        repo = AssentRecordRepo(session)
        record = await repo.propose(
            ["emit_plan", "commit"],
            metadata={"graph_replay": {"kind": "graph_host_mutation"}},
        )
        await session.commit()

    mcp = _GraphReplayMCP()
    outcome = await run_apply_branch(
        graph_intent_id=record.graph_intent_id,
        session_factory=session_factory,
        tools=[],
        mcp=mcp,
        request_id="req-invalid-graph-replay",
        client_ip="127.0.0.1",
        started=0.0,
        actor="operator",
    )

    assert outcome.regime == "error"
    assert outcome.error["code"] == "assent_graph_replay_invalid"
    assert mcp.calls == []


def test_graph_replay_display_uses_existing_assent_metadata_key():
    outcome = SimpleNamespace(
        graph_intent_id="abc123def456",
        chain_body={
            "status": "success",
            "chain": [{"step": "commit", "result": {"type": "commit_applied", "count": 1}}],
        },
        assent_record=AssentRecord(
            graph_intent_id="abc123def456",
            chain_steps=["human-readable"],
            metadata={
                "graph_replay": apply_delta_module.build_graph_replay_metadata(
                    held_manifest=_manifest_dict()
                )
            },
        ).to_dict(),
    )

    body = _apply_complete_body(outcome, "json")

    assert body["graph_intent"] == {
        "label": "Graph intent: editorial delta apply",
        "manifest_summary": {
            "type": "mutation_plan",
            "apply_tool": "forge_apply_segment_delta",
            "sequence_name": "seq_001",
            "resolved_count": 1,
        },
    }
