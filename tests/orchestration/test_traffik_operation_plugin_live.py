from __future__ import annotations

import copy
import json
from importlib.metadata import entry_points
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

import pytest

from forge_bridge.composition.commit_boundary import CommitBoundary
from forge_bridge.composition.dispatch import UnifiedDispatch
from forge_bridge.composition.executor import GraphExecutor
from forge_bridge.composition.graph_spec import Edge, GraphSpec, NodeSpec
from forge_bridge.composition.host_resolve_boundary import HostResolveBoundary
from forge_bridge.composition.operation_boundary import OperationDispatchBoundary
from forge_bridge.core.assent import AssentRecord
from forge_bridge.graph.ports import PortContract, PortTopology
from forge_bridge.orchestration.operation_runner import (
    OperationRunnerUnavailable,
    build_operation_runner,
)


FIXTURE_PATH = (
    Path(__file__).parents[1]
    / "fixtures"
    / "traffik_flame_delta_host_resolve_operation_fixtures.json"
)


class _EntryPoint:
    def __init__(self, name: str, factory: Callable[[], object]) -> None:
        self.name = name
        self._factory = factory

    def load(self) -> Callable[[], object]:
        return self._factory


def _fixture_delta(case_name: str = "ready_segment_name_delta") -> dict[str, Any]:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    cases = {case["name"]: case for case in fixture["cases"]}
    return copy.deepcopy(cases[case_name]["input"]["delta"])


def _status_value(result: Any) -> str:
    return str(getattr(result.status, "value", result.status))


def _minimal_edit_state() -> dict[str, Any]:
    return {
        "project": {
            "id": "project-1",
            "name": "Demo",
            "bins": [],
            "media_assets": [],
            "source_clips": [],
            "subclips": [],
            "sequences": [
                {
                    "id": "seq-1",
                    "name": "cut",
                    "tracks": [],
                    "duration": {
                        "number": 0,
                        "rate": {"frame_rate": "FPS_24"},
                    },
                    "metadata": {},
                }
            ],
            "sequence_versions": [],
            "segment_versions": [],
            "active_sequence_versions": {},
            "active_segment_versions": {},
            "metadata": {},
        },
        "session": {
            "active_sequence_id": "seq-1",
            "source_clip_id": None,
            "playhead": None,
            "source_mark": None,
            "record_mark": None,
            "selection": {"segment_ids": [], "track_ids": [], "range": None},
            "track_targets": [],
        },
    }


def _slate_edit_state() -> dict[str, Any]:
    state = _minimal_edit_state()
    project = state["project"]
    project["media_assets"] = [
        {
            "id": "slate-asset",
            "name": "SEQ_010",
            "media_ref": "file:///show/slates/SEQ_010.mov",
            "duration": {"number": 240, "rate": {"frame_rate": "FPS_24"}},
            "metadata": {},
        }
    ]
    project["source_clips"] = [
        {
            "id": "slate-source",
            "name": "SEQ_010",
            "media_asset_id": "slate-asset",
            "source_in": {"number": 0, "rate": {"frame_rate": "FPS_24"}},
            "source_out": {"number": 240, "rate": {"frame_rate": "FPS_24"}},
            "metadata": {},
        }
    ]
    sequence = project["sequences"][0]
    sequence.update(
        {
            "id": "seq-010",
            "name": "SEQ_010",
            "duration": {"number": 90000, "rate": {"frame_rate": "FPS_24"}},
            "tracks": [
                _empty_track("video-base", "L01"),
                _empty_track("video-top", "L02"),
                _empty_track("audio-left", "Audio L", audio=True),
            ],
        }
    )
    sequence["tracks"][1]["metadata"] = {
        "custom": {
            "flame_version_index": 0,
            "flame_version_track_index": 0,
        }
    }
    state["session"]["active_sequence_id"] = "seq-010"
    return state


def _empty_track(track_id: str, name: str, *, audio: bool = False) -> dict[str, Any]:
    metadata = {"custom": {"audio": True, "track_kind": "audio"}} if audio else {}
    return {
        "id": track_id,
        "name": name,
        "versions": [
            {
                "id": f"{track_id}-v1",
                "name": "v1",
                "segments": [],
                "metadata": {},
            }
        ],
        "active_version_index": 0,
        "metadata": metadata,
    }


def _slate_graph() -> GraphSpec:
    return GraphSpec(
        nodes=(
            NodeSpec(
                node_id="top",
                operator_id="traffik.editorial.resolve_top_video_layer",
                output_port=PortTopology.manifest(),
                config={"arguments": {"state": _slate_edit_state()}},
            ),
            NodeSpec(
                node_id="mark",
                operator_id="traffik.editorial.mark_timecode_range",
                input_ports={"state": PortContract.manifest_gate()},
                output_port=PortTopology.manifest(),
                config={
                    "arguments": {
                        "mark_in_timecode": "59:53:00",
                        "mark_out_timecode": "59:58:00",
                        "scope": "record",
                    }
                },
            ),
            NodeSpec(
                node_id="overwrite",
                operator_id="traffik.editorial.overwrite_insert",
                input_ports={"state": PortContract.manifest_gate()},
                output_port=PortTopology.manifest(),
                config={
                    "arguments": {
                        "source_clip_id": "slate-source",
                        "name": "SEQ_010_slate",
                    }
                },
            ),
            NodeSpec(
                node_id="select_delta",
                operator_id="select_delta",
                input_ports={"result": PortContract.manifest_gate()},
                output_port=PortTopology.manifest(),
            ),
            NodeSpec(
                node_id="host_project",
                operator_id="traffik.flame_delta.host_resolve",
                input_ports={"delta": PortContract.manifest_gate()},
                output_port=PortTopology.manifest(),
            ),
            NodeSpec(
                node_id="resolve",
                operator_id="delta_to_manifest",
                input_ports={"deltas": PortContract.manifest_gate()},
                output_port=PortTopology.manifest(),
            ),
            NodeSpec(
                node_id="commit",
                operator_id="commit",
                input_ports={"held": PortContract.manifest_gate()},
            ),
        ),
        edges=(
            Edge(from_node="top", to_node="mark", to_port="state"),
            Edge(from_node="mark", to_node="overwrite", to_port="state"),
            Edge(from_node="overwrite", to_node="select_delta", to_port="result"),
            Edge(from_node="select_delta", to_node="host_project", to_port="delta"),
            Edge(from_node="host_project", to_node="resolve", to_port="deltas"),
            Edge(from_node="resolve", to_node="commit", to_port="held"),
        ),
    )


def _insert_manifest(request: dict[str, Any]) -> dict[str, Any]:
    entry = copy.deepcopy(request["entries"][0])
    return {
        "type": "mutation_plan",
        "intent_parameters": {
            "sequence_name": request["sequence_name"],
            "entry": entry,
        },
        "resolved_plan": [
            {
                "identity": copy.deepcopy(entry["metadata"]),
                "payload": {"method": "version_fork_overwrite"},
            }
        ],
        "originating_capability": "forge_apply_segment_insert_delta",
        "apply_counterpart": {
            "tool": "forge_apply_segment_insert_delta",
            "parameter_overrides": {"mode": "apply"},
        },
    }


class _InsertMCP:
    def __init__(self) -> None:
        self.manifest: dict[str, Any] | None = None
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def list_tools(self):
        return [
            SimpleNamespace(
                name="forge_apply_segment_insert_delta",
                inputSchema={"type": "object", "properties": {}, "required": []},
            )
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]):
        self.calls.append((name, copy.deepcopy(arguments)))
        if arguments["mode"] == "verify":
            return copy.deepcopy(self.manifest)
        if arguments["mode"] == "apply":
            return {"ok": True, "created_version_index": 1}
        raise AssertionError(arguments["mode"])


def _load_traffik_stack(monkeypatch: pytest.MonkeyPatch, *, patch_entry_points: bool):
    plugins_module = pytest.importorskip(
        "forge_core.plugins",
        reason="forge_core plugin discovery is not installed",
    )
    registry_module = pytest.importorskip(
        "forge_core.operations.registry",
        reason="forge_core operation registry is not installed",
    )
    execution_module = pytest.importorskip(
        "forge_core.traffik.execution",
        reason="forge_core Traffik operations are not installed",
    )
    plugin_module = pytest.importorskip(
        "forge_core.traffik.plugin",
        reason="forge_core Traffik plugin is not installed",
    )
    slate_module = pytest.importorskip(
        "forge_core.traffik.slate_insert",
        reason="forge_core Traffik slate-insert operations are not installed",
    )

    if patch_entry_points:
        monkeypatch.setattr(
            plugins_module,
            "entry_points",
            lambda group: [_EntryPoint("traffik", plugin_module.create_plugin)],
        )

    monkeypatch.setenv("FORGE_PLUGINS", "traffik")
    monkeypatch.delenv("FORGE_DCC", raising=False)
    monkeypatch.setattr(registry_module, "_DEFAULT_REGISTRY", None, raising=False)
    return registry_module, execution_module, slate_module


async def _dispatch_traffik_pair(
    *,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    patch_entry_points: bool,
) -> None:
    registry_module, execution_module, slate_module = _load_traffik_stack(
        monkeypatch,
        patch_entry_points=patch_entry_points,
    )
    expected_types = {
        execution_module.EDITORIAL_OPERATION_TYPE,
        execution_module.FLAME_DELTA_HOST_RESOLVE_OPERATION_TYPE,
        slate_module.TOP_VIDEO_LAYER_OPERATION_TYPE,
        slate_module.MARK_TIMECODE_RANGE_OPERATION_TYPE,
        slate_module.OVERWRITE_INSERT_OPERATION_TYPE,
    }

    registry = registry_module.get_default_registry()
    assert expected_types <= set(registry.registered_types)

    try:
        runner = build_operation_runner(receipt_dir=tmp_path)
    except OperationRunnerUnavailable as exc:
        pytest.skip(f"forge_core operation runner is unavailable: {exc}")

    apply_result = await runner(
        execution_module.EDITORIAL_OPERATION_TYPE,
        params={"state": _minimal_edit_state(), "steps": []},
        idempotency_key="bridge-traffik-plugin-apply-steps",
        requested_by="bridge-plugin-proof",
    )
    assert _status_value(apply_result) == "succeeded"
    assert apply_result.data["deltas"] == []

    host_result = await runner(
        execution_module.FLAME_DELTA_HOST_RESOLVE_OPERATION_TYPE,
        params={"delta": _fixture_delta()},
        idempotency_key="bridge-traffik-plugin-host-resolve",
        requested_by="bridge-plugin-proof",
    )
    assert _status_value(host_result) == "succeeded"

    payload = host_result.data["flame_delta_host_resolve_payload"]
    projection = host_result.data["flame_delta_host_resolve_projection"]
    assert projection["status"] == "ok"
    assert projection["reason_code"] == "flame_delta_host_resolve_ready"
    assert payload["payload_kind"] == "traffik.flame_delta_host_resolve_payload"
    assert payload["schema_version"] == 3
    assert payload["deltas"][0]["metadata"]["executor"] == "forge_apply_segment_delta"

    top_result = await runner(
        slate_module.TOP_VIDEO_LAYER_OPERATION_TYPE,
        params={"state": _slate_edit_state()},
        idempotency_key="bridge-traffik-plugin-top-layer",
        requested_by="bridge-plugin-proof",
    )
    assert _status_value(top_result) == "succeeded"
    assert top_result.data["session"]["track_targets"][0]["track_id"] == "video-top"

    mark_result = await runner(
        slate_module.MARK_TIMECODE_RANGE_OPERATION_TYPE,
        params={
            "state": top_result.data,
            "mark_in_timecode": "59:53:00",
            "mark_out_timecode": "59:58:00",
            "scope": "record",
        },
        idempotency_key="bridge-traffik-plugin-mark-range",
        requested_by="bridge-plugin-proof",
    )
    assert _status_value(mark_result) == "succeeded"

    overwrite_result = await runner(
        slate_module.OVERWRITE_INSERT_OPERATION_TYPE,
        params={
            "state": mark_result.data,
            "source_clip_id": "slate-source",
            "name": "SEQ_010_slate",
        },
        idempotency_key="bridge-traffik-plugin-overwrite",
        requested_by="bridge-plugin-proof",
    )
    assert _status_value(overwrite_result) == "succeeded"
    assert overwrite_result.data["deltas"][0]["changes"][0]["action"] == "inserted"

    mcp = _InsertMCP()

    async def run_discover(tool_name: str, *, request: dict[str, Any]):
        assert tool_name == "forge_apply_segment_insert_delta"
        mcp.manifest = _insert_manifest(request)
        return copy.deepcopy(mcp.manifest)

    dispatch = UnifiedDispatch(
        operation_boundary=OperationDispatchBoundary(run_operation=runner),
        host_resolve_boundary=HostResolveBoundary(run_discover=run_discover),
        commit_boundary=CommitBoundary(mcp=mcp),
        assent_record=AssentRecord(
            graph_intent_id="slate-insert-plugin-proof",
            chain_steps=[
                "traffik.editorial.resolve_top_video_layer",
                "traffik.editorial.mark_timecode_range",
                "traffik.editorial.overwrite_insert",
                "select_delta",
                "traffik.flame_delta.host_resolve",
                "delta_to_manifest",
                "commit",
            ],
            status="ratified",
            decided_by="bridge-plugin-proof",
        ),
    )
    results = await GraphExecutor(dispatch.dispatch).run(_slate_graph())

    assert all(result.status == "ok" for result in results.values())
    delta = results["select_delta"].output
    assert delta["changes"][0]["action"] == "inserted"
    assert delta["changes"][0]["metadata"]["version_index"] == 0
    assert delta["changes"][0]["metadata"]["version_track_idx"] == 0
    projected = results["host_project"].output["flame_delta_host_resolve_payload"]
    assert projected["deltas"][0]["metadata"]["executor"] == (
        "forge_apply_segment_insert_delta"
    )
    assert results["commit"].output["type"] == "commit_applied"
    assert [(name, args["mode"]) for name, args in mcp.calls] == [
        ("forge_apply_segment_insert_delta", "verify"),
        ("forge_apply_segment_insert_delta", "apply"),
    ]


@pytest.mark.asyncio
async def test_operation_runner_dispatches_traffik_ops_via_plugin_discovery(
    monkeypatch,
    tmp_path,
) -> None:
    """Bridge can call Traffik ops through forge_core plugin loading.

    This uses the real Traffik plugin factory, but patches the entry-point
    source so Bridge CI can prove the seam from a source checkout without
    requiring an installed forge-pipeline distribution.
    """

    await _dispatch_traffik_pair(
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
        patch_entry_points=True,
    )


@pytest.mark.asyncio
async def test_installed_forge_plugins_traffik_dispatches_host_resolve(
    monkeypatch,
    tmp_path,
) -> None:
    """Deployment proof: installed v2.1.1+ entry points expose Traffik ops."""

    installed_plugins = entry_points(group="forge_core.plugins")
    if not any(ep.name == "traffik" for ep in installed_plugins):
        pytest.skip("installed forge_core.plugins entry points do not include traffik")

    await _dispatch_traffik_pair(
        monkeypatch=monkeypatch,
        tmp_path=tmp_path,
        patch_entry_points=False,
    )
