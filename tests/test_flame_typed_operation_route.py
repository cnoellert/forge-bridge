"""Narrow typed-operation coverage for the production Flame hook."""

from __future__ import annotations

import importlib.util
import json
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path
from types import ModuleType

import pytest


_BRIDGE_PATH = (
    Path(__file__).parent.parent / "flame_hooks" / "forge_bridge" / "scripts" / "forge_bridge.py"
)


@pytest.fixture
def bridge():
    spec = importlib.util.spec_from_file_location(
        "forge_bridge_typed_operation_test",
        _BRIDGE_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _post_once(bridge, payload: object) -> tuple[int, dict]:
    server = bridge._ReusableHTTPServer(("127.0.0.1", 0), bridge.BridgeHandler)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    request = urllib.request.Request(
        f"http://127.0.0.1:{server.server_port}/",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            status = response.status
            body = json.load(response)
    except urllib.error.HTTPError as exc:
        status = exc.code
        body = json.load(exc)
    finally:
        thread.join(timeout=2)
        server.server_close()
    return status, body


@pytest.mark.parametrize(
    ("operation", "attribute"),
    (
        ("shot_resource_load", "_exec_typed_host_load_on_main_thread"),
        ("host_graph_read", "_exec_typed_host_graph_read_on_main_thread"),
        (
            "host_graph_mutation",
            "_exec_typed_host_graph_mutation_on_main_thread",
        ),
    ),
)
def test_root_accepts_only_allowlisted_typed_operations(
    bridge,
    monkeypatch,
    operation: str,
    attribute: str,
) -> None:
    captured: list[tuple[dict, float | None]] = []

    def execute(params: dict, timeout: float | None = None) -> dict:
        captured.append((params, timeout))
        return {"result": {"operation": operation}}

    monkeypatch.setattr(bridge, attribute, execute)
    status, body = _post_once(
        bridge,
        {"op": operation, "params": {"mode": "verify"}, "timeout": 12},
    )

    assert status == 200
    assert body == {"result": {"operation": operation}}
    assert captured == [({"mode": "verify"}, 12)]


def test_root_rejects_arbitrary_and_malformed_operations(bridge) -> None:
    assert _post_once(
        bridge,
        {"op": "arbitrary_code", "params": {}},
    ) == (400, {"error": "Unknown operation"})
    assert _post_once(
        bridge,
        {"op": "host_graph_read", "params": []},
    ) == (400, {"error": "params must be an object"})
    assert _post_once(
        bridge,
        {"op": "host_graph_read", "params": {}, "timeout": "slow"},
    ) == (400, {"error": "timeout must be numeric"})


def test_typed_host_graph_read_runs_via_flame_plugin(bridge, monkeypatch) -> None:
    captured: dict = {}
    dispatch_module = ModuleType("forge_core.host_graph.routing")

    def execute(payload: dict, *, plugins: list[object]) -> dict:
        captured["payload"] = payload
        captured["plugins"] = plugins
        return {"kind": "pipeline.host_graph.read_dispatch_result"}

    dispatch_module.execute_host_graph_read_dispatch = execute
    plugin_module = ModuleType("forge_flame.plugin")

    class FlamePlugin:
        pass

    plugin_module.FlamePlugin = FlamePlugin
    monkeypatch.setattr(bridge, "_bootstrap_forge_runtime", lambda: None)
    monkeypatch.setitem(sys.modules, "forge_core.host_graph.routing", dispatch_module)
    monkeypatch.setitem(sys.modules, "forge_flame.plugin", plugin_module)

    result = bridge._execute_typed_host_graph_read({"scope": {"dcc": "flame"}})

    assert result == {"kind": "pipeline.host_graph.read_dispatch_result"}
    assert captured["payload"] == {"scope": {"dcc": "flame"}}
    assert len(captured["plugins"]) == 1
    assert isinstance(captured["plugins"][0], FlamePlugin)


def test_typed_host_graph_mutation_runs_via_flame_plugin(
    bridge,
    monkeypatch,
) -> None:
    captured: dict = {}
    dispatch_module = ModuleType("forge_core.host_graph.routing")

    def execute(payload: dict, *, plugins: list[object]) -> dict:
        captured["payload"] = payload
        captured["plugins"] = plugins
        return {"kind": "pipeline.host_graph.mutation_dispatch_result"}

    dispatch_module.execute_host_graph_mutation_dispatch = execute
    plugin_module = ModuleType("forge_flame.plugin")

    class FlamePlugin:
        pass

    plugin_module.FlamePlugin = FlamePlugin
    monkeypatch.setattr(bridge, "_bootstrap_forge_runtime", lambda: None)
    monkeypatch.setitem(sys.modules, "forge_core.host_graph.routing", dispatch_module)
    monkeypatch.setitem(sys.modules, "forge_flame.plugin", plugin_module)

    result = bridge._execute_typed_host_graph_mutation(
        {"operation_type": "pipeline.host_graph.ensure_node"}
    )

    assert result == {"kind": "pipeline.host_graph.mutation_dispatch_result"}
    assert captured["payload"] == {
        "operation_type": "pipeline.host_graph.ensure_node"
    }
    assert len(captured["plugins"]) == 1
    assert isinstance(captured["plugins"][0], FlamePlugin)


def test_typed_host_load_runs_via_flame_plugin(bridge, monkeypatch) -> None:
    captured: dict = {}
    dispatch_module = ModuleType("forge_core.shot_resources.host_load_dispatch")

    def execute(payload: dict, *, plugins: list[object]) -> dict:
        captured["payload"] = payload
        captured["plugins"] = plugins
        return {"kind": "pipeline.shot_resource.host_load_dispatch_result"}

    dispatch_module.execute_host_load_dispatch = execute
    plugin_module = ModuleType("forge_flame.plugin")

    class FlamePlugin:
        pass

    plugin_module.FlamePlugin = FlamePlugin
    monkeypatch.setattr(bridge, "_bootstrap_forge_runtime", lambda: None)
    monkeypatch.setitem(
        sys.modules,
        "forge_core.shot_resources.host_load_dispatch",
        dispatch_module,
    )
    monkeypatch.setitem(sys.modules, "forge_flame.plugin", plugin_module)

    result = bridge._execute_typed_host_load({"mode": "verify"})

    assert result == {"kind": "pipeline.shot_resource.host_load_dispatch_result"}
    assert captured["payload"] == {"mode": "verify"}
    assert len(captured["plugins"]) == 1
    assert isinstance(captured["plugins"][0], FlamePlugin)


def test_bootstrap_adds_source_and_conda_runtime(
    bridge,
    monkeypatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "checkout"
    conda_site = tmp_path / "site-packages"
    repo_root.mkdir()
    conda_site.mkdir()
    added: list[str] = []

    monkeypatch.setenv("FORGE_REPO_ROOT", str(repo_root))
    monkeypatch.setenv("FORGE_CONDA_SITE", str(conda_site))
    monkeypatch.setattr("site.addsitedir", added.append)
    monkeypatch.setattr(sys, "path", [p for p in sys.path if p != str(repo_root)])

    bridge._bootstrap_forge_runtime()

    assert sys.path[0] == str(repo_root)
    assert added == [str(conda_site)]


def test_typed_operation_runs_on_main_thread(bridge, monkeypatch) -> None:
    flame_module = ModuleType("flame")
    calls: list[str] = []

    def schedule_idle_event(callback) -> None:
        calls.append("scheduled")
        callback()

    flame_module.schedule_idle_event = schedule_idle_event
    monkeypatch.setitem(sys.modules, "flame", flame_module)

    result = bridge._exec_typed_operation_on_main_thread(
        lambda params: {"params": params},
        {"mode": "verify"},
        timeout=1,
    )

    assert calls == ["scheduled"]
    assert result == {"result": {"params": {"mode": "verify"}}}


def test_exec_forwards_request_timeout_to_main_thread(bridge, monkeypatch) -> None:
    captured: list[tuple[str, float | None]] = []

    def execute(code: str, timeout: float | None = None) -> dict:
        captured.append((code, timeout))
        return {"result": "ok"}

    monkeypatch.setattr(bridge, "_exec_on_main_thread", execute)
    server = bridge._ReusableHTTPServer(("127.0.0.1", 0), bridge.BridgeHandler)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    request = urllib.request.Request(
        f"http://127.0.0.1:{server.server_port}/exec",
        data=json.dumps({"code": "flame.batch", "main_thread": True, "timeout": 45}).encode(
            "utf-8"
        ),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            assert json.load(response) == {"result": "ok"}
    finally:
        thread.join(timeout=2)
        server.server_close()

    assert captured == [("flame.batch", 45)]
