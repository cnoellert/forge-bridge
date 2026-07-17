from __future__ import annotations

import textwrap
from types import SimpleNamespace
from typing import Any

import pytest

from forge_bridge.composition.commit_boundary import CommitBoundary
from forge_bridge.composition.dispatch import UnifiedDispatch
from forge_bridge.composition.executor import GraphExecutor
from forge_bridge.composition.graph_spec import GraphSpec, NodeSpec
from forge_bridge.core.assent import AssentRecord
from forge_bridge.graph.commit import CommitError
from forge_bridge.orchestration.operation_runner import build_operation_runner


class _AttachMCP:
    def __init__(self) -> None:
        self.tools: dict[str, dict[str, Any]] = {}

    def add_tool(self, fn, *, name: str, **kwargs: Any) -> None:
        self.tools[name] = {"fn": fn, **kwargs}


class _PipelineHostGraphMCP:
    def __init__(self, tool) -> None:
        self._tool = tool
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def list_tools(self):
        return [
            SimpleNamespace(
                name="forge_apply_host_graph_plan",
                inputSchema={
                    "type": "object",
                    "properties": {
                        name: {"type": "object"}
                        for name in (
                            "target",
                            "scope",
                            "plan",
                            "resolved_plan",
                            "semantic_intent",
                        )
                    }
                    | {"mode": {"type": "string"}},
                    "required": ["target", "scope", "plan", "mode"],
                },
            )
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]):
        self.calls.append((name, dict(arguments)))
        assert name == "forge_apply_host_graph_plan"
        return await self._tool(**arguments)


def _phase105_modules():
    host_graph = pytest.importorskip(
        "forge_core.host_graph",
        reason="Pipeline Phase 105 host-graph package is not installed",
    )
    contracts = pytest.importorskip(
        "forge_core.host_graph.contracts",
        reason="Pipeline Phase 105 contracts are not installed",
    )
    registry = pytest.importorskip(
        "forge_core.operations.registry",
        reason="Pipeline Phase 105 operation registry is not installed",
    )
    bridge_registry = pytest.importorskip(
        "forge_core.bridge.registry",
        reason="Pipeline Phase 105 MCP attach hook is not installed",
    )
    return host_graph, contracts, registry, bridge_registry


def _held_manifest() -> dict[str, Any]:
    scope = {
        "kind": "pipeline.host_graph.scope",
        "schema_version": 1,
        "dcc": "Flame",
        "graph_kind": "batch",
        "project": "TST",
        "instance_id": "phase106-live-proof",
        "session_id": "phase106-session",
        "graph_ref": "test_104",
        "operator_identity": "",
        "mutation_boundary": "dcc_host",
    }
    plan = {
        "kind": "pipeline.host_graph.mutation_plan",
        "schema_version": 1,
        "scope": scope,
        "expected_pre_state_fingerprint": "pre",
        "changes": [{"change_id": "ensure-write", "action": "ensure_node"}],
        "status": "ready",
        "trust_status": "provisional",
    }
    return {
        "type": "mutation_plan",
        "intent_parameters": {
            "target": {"dcc": "Flame", "instance_id": "phase106-live-proof"},
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
                    "expected_pre_state_fingerprint": "pre",
                },
                "payload": {"change": plan["changes"][0]},
            }
        ],
        "originating_capability": "forge_plan_shot_output_graph",
        "apply_counterpart": {
            "tool": "forge_apply_host_graph_plan",
            "parameter_overrides": {"plan": plan},
        },
    }


def _ratified_assent() -> AssentRecord:
    return AssentRecord(
        graph_intent_id="phase106-live-proof",
        chain_steps=["commit"],
        status="ratified",
        decided_by="pipeline-host-graph-proof",
    )


def test_phase105_operations_and_tool_attach_are_discovered_without_manual_register(
    monkeypatch,
) -> None:
    _, contracts, registry_module, bridge_registry = _phase105_modules()
    monkeypatch.setenv("FORGE_PLUGINS", "flame")
    monkeypatch.delenv("FORGE_DCC", raising=False)
    monkeypatch.setattr(registry_module, "_DEFAULT_REGISTRY", None, raising=False)

    registry = registry_module.get_default_registry()
    expected = {
        "pipeline.shot_resource.current",
        contracts.HOST_GRAPH_INSPECT_OPERATION_TYPE,
        contracts.SHOT_OUTPUT_GRAPH_PLAN_OPERATION_TYPE,
        contracts.HOST_GRAPH_VERIFY_OPERATION_TYPE,
    }
    assert expected <= set(registry.registered_types)

    mcp = _AttachMCP()
    registered = bridge_registry.register_with(mcp)

    assert "forge_plan_shot_output_graph" in registered
    assert "forge_plan_shot_output_graph" in mcp.tools
    assert mcp.tools["forge_plan_shot_output_graph"]["annotations"] == {"readOnlyHint": True}


@pytest.mark.asyncio
async def test_build_operation_runner_dispatches_real_phase105_semantic_plan(
    monkeypatch,
    tmp_path,
) -> None:
    host_graph, contracts, registry_module, _ = _phase105_modules()
    monkeypatch.setenv("FORGE_PLUGINS", "")
    monkeypatch.delenv("FORGE_DCC", raising=False)
    monkeypatch.setattr(registry_module, "_DEFAULT_REGISTRY", None, raising=False)

    config_path = tmp_path / "pipeline_config.yaml"
    config_path.write_text(
        textwrap.dedent(
            """
            output_roles:
              comp_render:
                media_class: image
                root: images
                bin: comps/flame
                pattern: "<shot>_<task>_<version><frame><ext>"
            task_outputs:
              comp:
                - role: comp_render
                  family: image
            shot_dirs:
              - path: images
                children:
                  - path: comps
                    children:
                      - path: flame
                        role: comp_render
                        children:
                          - path: clip
                            role: comp_openclip
              - path: comp
                children:
                  - path: flame
                    children:
                      - path: batch
                        role: comp_batch
            write_file_defaults:
              pattern_role: comp_render
              open_clip_role: comp_openclip
              setup_role: comp_batch
              pattern: "<shot>_<task>_<version><frame><ext>"
              open_clip_pattern: "<shot>_<task><ext>"
              setup_pattern: "<shot>_<task>_<version><ext>"
              image_format: "OpenEXR 16-bit fp"
              compression: DWAA
              compression_quality: 45
              padding: 4
              create_open_clip: true
              include_setup: true
            """
        ),
        encoding="utf-8",
    )
    canonical = tmp_path / "project"
    version_path = canonical / "_04_shots" / "tst_010" / "images" / "comps" / "flame" / "v003"
    version_path.mkdir(parents=True)
    scope = host_graph.HostGraphScope(
        dcc="Flame",
        graph_kind="batch",
        project="TST",
        instance_id="phase105-plugin-proof",
        session_id="phase105-session",
        graph_ref="test_104",
    )
    source = host_graph.HostNodeDescriptor(
        native_type="Comp",
        name="COMP_OUT",
        stable_id="comp-out-1",
        outputs=(host_graph.HostPortDescriptor("Result", "output", index=0),),
    )
    snapshot = host_graph.HostGraphSnapshot(scope=scope, nodes=(source,))
    runner = build_operation_runner(receipt_dir=tmp_path / "receipts")

    current = await runner(
        "pipeline.shot_resource.current",
        params={
            "canonical": str(canonical),
            "shot": "tst_010",
            "task": "comp",
            "dcc": "Flame",
            "stream": "main",
            "config_path": str(config_path),
        },
    )
    planned = await runner(
        contracts.SHOT_OUTPUT_GRAPH_PLAN_OPERATION_TYPE,
        params={
            "request": {
                "kind": contracts.SHOT_OUTPUT_GRAPH_REQUEST_KIND,
                "schema_version": contracts.SHOT_OUTPUT_GRAPH_SCHEMA_VERSION,
                "canonical": str(canonical),
                "shot": "tst_010",
                "task": "comp",
                "role": "comp_render",
                "stream": "main",
                "dcc": "Flame",
                "target_graph": scope.to_dict(),
                "version_policy": {"mode": "current"},
                "upstream_source": {
                    "selector": source.selector.to_dict(),
                    "port": "Result",
                },
            },
            "stream_context": current.data,
            "host_graph_snapshot": {
                "kind": "pipeline.host_graph.operation_result",
                "result": snapshot.to_dict(),
            },
            "config_path": str(config_path),
        },
    )

    assert str(getattr(current.status, "value", current.status)) == "succeeded"
    assert str(getattr(planned.status, "value", planned.status)) == "succeeded"
    assert planned.data["kind"] == "pipeline.shot_output_graph.plan_result"
    assert planned.data["status"] == "ready"
    assert planned.data["type"] == "mutation_plan"
    assert planned.data["apply_counterpart"]["tool"] == ("forge_apply_host_graph_plan")
    assert len(planned.data["resolved_plan"]) == 3


@pytest.mark.asyncio
@pytest.mark.parametrize("drift", [False, True])
async def test_real_pipeline_grouped_verify_drives_bridge_commit_boundary(
    monkeypatch,
    drift: bool,
) -> None:
    host_tools = pytest.importorskip(
        "forge_flame.host_graph_tools",
        reason="Pipeline Phase 106 fresh verify manifest is not installed",
    )
    router = pytest.importorskip("forge_core.session.router")
    route_result_type = router.RouteResult
    calls: list[str] = []

    def route(target, path, payload, **kwargs):
        mode = payload["params"]["mode"]
        calls.append(mode)
        plan = dict(payload["params"]["plan"])
        if mode == "verify" and drift:
            plan.update(status="review_required", trust_status="review_required")
            status = "review_required"
            trust_status = "review_required"
            reason = "host_graph_pre_state_drift"
        elif mode == "verify":
            status = "ready"
            trust_status = "provisional"
            reason = None
        else:
            status = "succeeded"
            trust_status = "trusted"
            reason = None
            plan = {
                "kind": "pipeline.host_graph.apply_receipt",
                "status": "succeeded",
                "trust_status": "trusted",
                "mutation_count": 1,
            }
        return route_result_type(
            ok=True,
            response={
                "result": {
                    "kind": "pipeline.host_graph.mutation_dispatch_result",
                    "operation_type": "pipeline.host_graph.apply_plan",
                    "mode": mode,
                    "status": status,
                    "trust_status": trust_status,
                    "state_owner": "dcc_host",
                    "reason": reason,
                    "result": plan,
                }
            },
        )

    monkeypatch.setattr(router, "route", route)
    held = _held_manifest()
    mcp = _PipelineHostGraphMCP(host_tools.forge_apply_host_graph_plan)
    graph = GraphSpec(
        nodes=(NodeSpec(node_id="commit", operator_id="commit", config={"held": held}),),
        edges=(),
    )
    result = (
        await GraphExecutor(
            UnifiedDispatch(
                commit_boundary=CommitBoundary(mcp=mcp),
                assent_record=_ratified_assent(),
            ).dispatch
        ).run(graph)
    )["commit"]

    if drift:
        assert result.status == "error"
        assert result.reason_code == CommitError.PLAN_STATE_DRIFT
        assert calls == ["verify"]
    else:
        assert result.status == "ok"
        assert result.output["type"] == "commit_applied"
        assert calls == ["verify", "apply"]
