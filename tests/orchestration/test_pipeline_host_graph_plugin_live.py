from __future__ import annotations

import textwrap
from typing import Any

import pytest

from forge_bridge.orchestration.operation_runner import build_operation_runner


class _AttachMCP:
    def __init__(self) -> None:
        self.tools: dict[str, dict[str, Any]] = {}

    def add_tool(self, fn, *, name: str, **kwargs: Any) -> None:
        self.tools[name] = {"fn": fn, **kwargs}


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
