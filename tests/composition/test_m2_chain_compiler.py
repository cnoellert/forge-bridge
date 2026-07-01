from __future__ import annotations

import copy
import json
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from forge_bridge.composition.boundary import MCPToolBoundary
from forge_bridge.composition.chain_compiler import (
    ChainCompileError,
    compile_chain_steps,
)
from forge_bridge.composition.commit_boundary import CommitBoundary
from forge_bridge.composition.compare import (
    normalize_chain_body,
    normalize_graph_results,
)
from forge_bridge.composition.dispatch import UnifiedDispatch
from forge_bridge.composition.executor import GraphExecutor
from forge_bridge.composition.graph_spec import GraphSpec, NodeSpec
from forge_bridge.composition.primitive_boundary import PrimitiveBoundary
from forge_bridge.console._engine import run_chain_steps
from forge_bridge.core.assent import AssentRecord
from forge_bridge.graph.commit import CommitError


_FIXTURE_DIR = Path(__file__).parent / "fixtures"
_EXECUTION_LOG = Path.home() / ".forge-bridge" / "executions.jsonl"


class _ReplayMCP:
    def __init__(
        self,
        *,
        held: dict,
        verify_manifest: dict | None = None,
        roto_payload: dict | None = None,
    ):
        self.calls: list[tuple[str, dict]] = []
        self._held = copy.deepcopy(held)
        self._verify_manifest = copy.deepcopy(verify_manifest or held)
        self._roto_payload = roto_payload or {"artifact_refs": [], "verdict": "pass"}
        self.state = {
            _identity_key(item["identity"]): item["identity"]["seg_name"]
            for item in held["resolved_plan"]
        }

    async def list_tools(self):
        return _tools()

    async def call_tool(self, name: str, arguments: dict | None = None, **kwargs):
        args = arguments if arguments is not None else kwargs.get("arguments", {})
        self.calls.append((name, copy.deepcopy(args)))
        if name == "flame_rename_shots":
            mode = args.get("mode")
            if mode == "verify":
                return copy.deepcopy(self._verify_manifest)
            if mode == "discover" or args.get("dry_run") is True:
                return copy.deepcopy(self._held)
            if mode == "apply":
                return self._apply(args["resolved_plan"])
            raise AssertionError(f"unexpected rename mode: {mode!r}")
        if name == "forge_is_greenscreen":
            return {
                "shots": [
                    {"id": "gs_010", "is_greenscreen": True},
                    {"id": "amb_030", "is_greenscreen": False},
                ],
                "count": 2,
            }
        if name == "forge_roto_ref":
            return copy.deepcopy(self._roto_payload)
        raise AssertionError(name)

    def _apply(self, plan: list[dict]) -> dict:
        for item in plan:
            self.state[_identity_key(item["identity"])] = item["payload"]["shot_name"]
        return {
            "type": "rename_apply_result",
            "renamed": len(plan),
            "post_shot_names": list(self.state.values()),
        }


def _tool(name: str, *, read_only: bool = True):
    return SimpleNamespace(
        name=name,
        annotations=SimpleNamespace(readOnlyHint=read_only),
        inputSchema={"type": "object", "properties": {}, "required": []},
    )


def _tools():
    return [
        _tool("flame_rename_shots", read_only=False),
        _tool("forge_is_greenscreen"),
        _tool("forge_roto_ref"),
    ]


def _held_manifest_dict() -> dict:
    return json.loads((_FIXTURE_DIR / "commit_rename_held.json").read_text())


def _roto_payload() -> dict:
    return json.loads((_FIXTURE_DIR / "roto_ref_gs_010_call_a.json").read_text())


def _identity_key(identity: dict) -> tuple:
    return (
        identity.get("sequence_name"),
        identity.get("track_idx"),
        identity.get("record_in"),
        identity.get("source_name"),
    )


def _ratified_assent(chain_steps: list[str]) -> AssentRecord:
    return AssentRecord(
        graph_intent_id="graph-intent-chain-compiler",
        chain_steps=chain_steps,
        status="ratified",
        decided_by="operator",
    )


def _rename_commit_steps() -> list[str]:
    held = _held_manifest_dict()
    params = held["intent_parameters"]
    return [
        "flame_rename_shots "
        f"sequence_name={json.dumps(params['sequence_name'])} "
        f"prefix={params['prefix']} "
        f"increment={params['increment']} "
        f"padding={params['padding']} "
        f"start={params['start']} "
        "dry_run=true "
        f"rename shots on {params['sequence_name']} with prefix {params['prefix']} "
        "dry_run",
        "commit",
    ]


def test_compile_chain_steps_builds_linear_graph_from_varied_chain_text():
    graph = compile_chain_steps([
        "forge_is_greenscreen shot_id=batch clip_ref=mock://batch.mov",
        "filter(is_greenscreen == true)",
        "if(proposed_changes exists)",
        "foreach(forge_roto_ref shot_id=gs_010 clip_ref=mock://gs_010.mov)",
    ])

    assert [node.operator_id for node in graph.nodes] == [
        "forge_is_greenscreen",
        "filter",
        "if",
        "foreach",
    ]
    assert [(edge.from_node, edge.to_node, edge.to_port) for edge in graph.edges] == [
        ("forge_is_greenscreen#0", "filter#1", "input"),
        ("filter#1", "if#2", "input"),
        ("if#2", "foreach#3", "input"),
    ]
    assert graph.nodes[0].config["arguments"] == {
        "shot_id": "batch",
        "clip_ref": "mock://batch.mov",
    }
    assert graph.nodes[1].config["step_text"] == "filter(is_greenscreen == true)"
    body = graph.nodes[3].config["body"]
    assert body.operator_id == "forge_roto_ref"
    assert set(body.input_ports) == {"item"}
    assert body.config["arguments"]["clip_ref"] == "mock://gs_010.mov"


def test_compile_chain_steps_preserves_json_args_and_literals():
    graph = compile_chain_steps([
        'forge_is_greenscreen {"params": {"shot_id": "gs_010", '
        '"clip_ref": "mock://gs_010.mov", "enabled": true}}',
    ])

    assert graph.nodes[0].config["arguments"] == {
        "shot_id": "gs_010",
        "clip_ref": "mock://gs_010.mov",
        "enabled": True,
    }


@pytest.mark.parametrize(
    "steps",
    [
        ["unknown_tool"],
        ["select gs_010"],
        ["stage(ee_drift_review)"],
    ],
)
def test_compile_chain_steps_fails_closed_for_unadmitted_tokens(steps):
    with pytest.raises(ChainCompileError):
        compile_chain_steps(steps)


def test_compile_chain_steps_admits_collect_after_foreach():
    graph = compile_chain_steps([
        "forge_is_greenscreen shot_id=batch clip_ref=mock://batch.mov",
        "foreach(forge_roto_ref shot_id=gs_010 clip_ref=mock://gs_010.mov)",
        "collect",
    ])

    collect_node = graph.nodes[-1]
    assert collect_node.operator_id == "collect"
    # foreach emits iteration_results; the collect input port must accept it.
    foreach_node = graph.nodes[-2]
    assert collect_node.input_ports["input"].accepts_topology(
        foreach_node.output_port
    )


def test_execution_log_is_not_a_replayable_chain_corpus_today():
    """Grounding check for the broad-corpus bar.

    The local execution log is real and broad, but as captured today it does
    not persist chain-step text or per-step results. Slice 4 therefore commits
    deterministic fixtures for the first offline compiler oracle instead of
    claiming the log is replayable.
    """

    if not _EXECUTION_LOG.exists():
        pytest.skip("local execution log is absent")

    found = 0
    with _EXECUTION_LOG.open() as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            if any(key in record for key in ("chain_steps", "steps", "chain")):
                found += 1
                break

    assert found == 0


@pytest.mark.asyncio
async def test_chain_compiler_graph_apply_matches_legacy_replay_with_held_from_edge():
    steps = _rename_commit_steps()
    held = _held_manifest_dict()
    legacy_mcp = _ReplayMCP(held=held)
    graph_mcp = _ReplayMCP(held=held)
    assent = _ratified_assent(steps)

    legacy_body = await run_chain_steps(
        steps=steps,
        tools=_tools(),
        mcp=legacy_mcp,
        request_id="req-legacy-rename-commit",
        client_ip="127.0.0.1",
        started=time.monotonic(),
        assent_record=assent,
    )

    graph = compile_chain_steps(steps)
    results = await GraphExecutor(UnifiedDispatch(
        mcp_boundary=MCPToolBoundary(mcp=graph_mcp),
        primitive_boundary=PrimitiveBoundary(),
        commit_boundary=CommitBoundary(mcp=graph_mcp),
        assent_record=assent,
    ).dispatch).run(graph)

    assert normalize_chain_body(legacy_body).status_vector == ("ok", "ok")
    assert normalize_graph_results(results, terminal_node_id="commit#1").status_vector == (
        "ok",
        "ok",
    )
    assert [(name, args.get("mode"), args.get("dry_run")) for name, args in legacy_mcp.calls] == [
        ("flame_rename_shots", None, True),
        ("flame_rename_shots", "verify", None),
        ("flame_rename_shots", "apply", None),
    ]
    assert [(name, args.get("mode"), args.get("dry_run")) for name, args in graph_mcp.calls] == [
        ("flame_rename_shots", None, True),
        ("flame_rename_shots", "verify", None),
        ("flame_rename_shots", "apply", None),
    ]
    expected_names = [
        item["payload"]["shot_name"]
        for item in held["resolved_plan"]
    ]
    assert legacy_body["chain"][-1]["result"]["apply_result"]["post_shot_names"] == (
        expected_names
    )
    assert results["commit#1"].output["apply_result"]["post_shot_names"] == (
        expected_names
    )
    assert list(legacy_mcp.state.values()) == expected_names
    assert list(graph_mcp.state.values()) == expected_names


@pytest.mark.asyncio
async def test_commit_boundary_config_and_edge_held_sources_are_equivalent():
    held = _held_manifest_dict()
    steps = _rename_commit_steps()
    assent = _ratified_assent(steps)

    config_mcp = _ReplayMCP(held=held)
    base = compile_chain_steps(["commit"])
    config_graph = GraphSpec(
        nodes=(
            NodeSpec(
                node_id=base.nodes[0].node_id,
                operator_id=base.nodes[0].operator_id,
                input_ports=base.nodes[0].input_ports,
                output_port=base.nodes[0].output_port,
                backend_id=base.nodes[0].backend_id,
                config={"held": held},
            ),
        ),
        edges=(),
    )
    config_result = await GraphExecutor(UnifiedDispatch(
        commit_boundary=CommitBoundary(mcp=config_mcp),
        assent_record=assent,
    ).dispatch).run(config_graph)

    edge_mcp = _ReplayMCP(held=held)
    edge_result = await GraphExecutor(UnifiedDispatch(
        mcp_boundary=MCPToolBoundary(mcp=edge_mcp),
        commit_boundary=CommitBoundary(mcp=edge_mcp),
        assent_record=assent,
    ).dispatch).run(compile_chain_steps(steps))

    assert config_result["commit#0"].status == "ok"
    assert edge_result["commit#1"].status == "ok"
    assert config_result["commit#0"].output["count"] == edge_result["commit#1"].output[
        "count"
    ]


@pytest.mark.asyncio
async def test_chain_compiler_graph_apply_reports_drift_without_apply():
    held = _held_manifest_dict()
    drift = copy.deepcopy(held)
    drift["resolved_plan"][0]["payload"]["shot_name"] = "different"
    steps = _rename_commit_steps()
    mcp = _ReplayMCP(held=held, verify_manifest=drift)

    results = await GraphExecutor(UnifiedDispatch(
        mcp_boundary=MCPToolBoundary(mcp=mcp),
        commit_boundary=CommitBoundary(mcp=mcp),
        assent_record=_ratified_assent(steps),
    ).dispatch).run(compile_chain_steps(steps))

    assert results["commit#1"].status == "error"
    assert results["commit#1"].reason_code == CommitError.PLAN_STATE_DRIFT
    assert [(name, args.get("mode"), args.get("dry_run")) for name, args in mcp.calls] == [
        ("flame_rename_shots", None, True),
        ("flame_rename_shots", "verify", None),
    ]
