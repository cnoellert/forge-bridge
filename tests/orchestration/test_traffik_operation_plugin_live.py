from __future__ import annotations

import copy
import json
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any, Callable

import pytest

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

    if patch_entry_points:
        monkeypatch.setattr(
            plugins_module,
            "entry_points",
            lambda group: [_EntryPoint("traffik", plugin_module.create_plugin)],
        )

    monkeypatch.setenv("FORGE_PLUGINS", "traffik")
    monkeypatch.delenv("FORGE_DCC", raising=False)
    monkeypatch.setattr(registry_module, "_DEFAULT_REGISTRY", None, raising=False)
    return registry_module, execution_module


async def _dispatch_traffik_pair(
    *,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    patch_entry_points: bool,
) -> None:
    registry_module, execution_module = _load_traffik_stack(
        monkeypatch,
        patch_entry_points=patch_entry_points,
    )
    expected_types = {
        execution_module.EDITORIAL_OPERATION_TYPE,
        execution_module.FLAME_DELTA_HOST_RESOLVE_OPERATION_TYPE,
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
