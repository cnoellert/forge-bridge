"""Tests for forge_bridge.runtime.manager — process orchestration.

Covers start/stop/status with subprocess.Popen and os.kill mocked, runtime
file roundtrip, stale-PID cleanup, idempotent up, and missing-file safety.
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from forge_bridge import config
from forge_bridge.runtime import manager


@pytest.fixture
def runtime_home(tmp_path, monkeypatch):
    monkeypatch.setenv("FORGE_RUNTIME_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch):
    """Speed up start/stop polling loops in tests."""
    monkeypatch.setattr("time.sleep", lambda *_a, **_k: None)


class _FakeProc:
    def __init__(self, pid=12345):
        self.pid = pid


# ── runtime file roundtrip ────────────────────────────────────────────────

def test_missing_runtime_file_is_safe(runtime_home):
    state = manager._read_runtime()
    assert state == {"services": {}}


def test_corrupt_runtime_file_is_safe(runtime_home):
    (runtime_home / "runtime.json").write_text("{not json")
    state = manager._read_runtime()
    assert state == {"services": {}}


def test_runtime_file_roundtrip(runtime_home):
    manager._write_runtime({"services": {"mcp_http": {"pid": 42, "port": 9997}}})
    state = manager._read_runtime()
    assert state["services"]["mcp_http"]["pid"] == 42
    assert state["services"]["mcp_http"]["port"] == 9997


# ── start_mcp_http ────────────────────────────────────────────────────────

def test_start_mcp_http_launches_subprocess(runtime_home):
    with patch.object(manager, "_tcp_in_use") as tcp, \
         patch.object(manager, "_pid_alive") as alive, \
         patch("subprocess.Popen") as popen:
        tcp.side_effect = [False, True]  # not in use; ready after start
        alive.return_value = True
        popen.return_value = _FakeProc(pid=1111)
        result = manager.start_mcp_http()
    assert result["started"] is True
    assert result["pid"] == 1111
    assert result["port"] == config.MCP_HTTP_PORT
    state = manager._read_runtime()
    assert state["services"]["mcp_http"]["pid"] == 1111


def test_start_mcp_http_skips_when_already_tracked_and_alive(runtime_home):
    manager._write_runtime({
        "services": {"mcp_http": {"pid": 9999, "port": config.MCP_HTTP_PORT, "host": config.MCP_HTTP_HOST}}
    })
    with patch.object(manager, "_pid_alive", return_value=True), \
         patch("subprocess.Popen") as popen:
        result = manager.start_mcp_http()
    assert result["started"] is False
    assert result["skipped"] == "already running"
    assert result["pid"] == 9999
    popen.assert_not_called()


def test_start_mcp_http_marks_external_when_port_in_use(runtime_home):
    """Port already bound by user-managed process → mark as external, no Popen."""
    with patch.object(manager, "_tcp_in_use", return_value=True), \
         patch.object(manager, "_pid_alive", return_value=False), \
         patch("subprocess.Popen") as popen:
        result = manager.start_mcp_http()
    assert result["started"] is False
    assert "external" in result["skipped"]
    popen.assert_not_called()
    state = manager._read_runtime()
    assert state["services"]["mcp_http"]["external"] is True


def test_start_state_ws_uses_state_ws_argv(runtime_home):
    with patch.object(manager, "_tcp_in_use") as tcp, \
         patch.object(manager, "_pid_alive", return_value=True), \
         patch("subprocess.Popen") as popen:
        tcp.side_effect = [False, True]
        popen.return_value = _FakeProc(pid=2222)
        result = manager.start_state_ws()
    assert result["started"] is True
    argv = popen.call_args.args[0]
    assert argv[-2:] == ["-m", "forge_bridge.server"]


# ── start_console (co-host semantics) ─────────────────────────────────────

def test_start_console_skips_when_console_port_already_open(runtime_home):
    with patch.object(manager, "_tcp_in_use", return_value=True), \
         patch("subprocess.Popen") as popen:
        result = manager.start_console()
    assert result["skipped"] == "already serving"
    popen.assert_not_called()


def test_start_console_falls_through_to_mcp_http(runtime_home):
    """When :9996 is dark, start_console launches mcp_http (which co-hosts the UI)."""
    with patch.object(manager, "_tcp_in_use") as tcp, \
         patch.object(manager, "_pid_alive", return_value=True), \
         patch("subprocess.Popen") as popen:
        # console probe = False; subsequent mcp_http probes = False then True
        tcp.side_effect = [False, False, True]
        popen.return_value = _FakeProc(pid=3333)
        result = manager.start_console()
    assert result["name"] == "console"
    assert "co-hosted" in result["note"]
    popen.assert_called_once()


# ── stop_all ──────────────────────────────────────────────────────────────

def test_stop_all_sigterm_path(runtime_home):
    manager._write_runtime({
        "services": {
            "mcp_http": {"pid": 4444, "port": config.MCP_HTTP_PORT, "host": "127.0.0.1"},
            "state_ws": {"pid": 5555, "port": config.STATE_WS_PORT, "host": "127.0.0.1"},
        }
    })
    alive_calls = {"mcp_http": iter([True, False]), "state_ws": iter([True, False])}

    def _alive(pid):
        if pid == 4444:
            return next(alive_calls["mcp_http"])
        if pid == 5555:
            return next(alive_calls["state_ws"])
        return False

    with patch.object(manager, "_pid_alive", side_effect=_alive), \
         patch("os.kill") as kill:
        results = manager.stop_all()
    methods = {r["name"]: r.get("method") for r in results if r.get("stopped")}
    assert methods == {"mcp_http": "SIGTERM", "state_ws": "SIGTERM"}
    pids_signaled = {c.args[0] for c in kill.call_args_list}
    assert pids_signaled == {4444, 5555}
    # runtime file is cleared
    state = manager._read_runtime()
    assert state["services"] == {}


def test_stop_all_escalates_to_sigkill_when_sigterm_doesnt_take(runtime_home):
    manager._write_runtime({
        "services": {"mcp_http": {"pid": 6666, "port": config.MCP_HTTP_PORT}},
    })
    with patch.object(manager, "_pid_alive", return_value=True), \
         patch("os.kill") as kill:
        results = manager.stop_all()
    assert results[0]["stopped"] is True
    assert results[0]["method"] == "SIGKILL"
    sigs = [c.args[1] for c in kill.call_args_list]
    import signal as _sig
    assert _sig.SIGTERM in sigs
    assert _sig.SIGKILL in sigs


def test_stop_all_handles_missing_file(runtime_home):
    """No runtime.json yet → stop_all is a no-op, returns []."""
    results = manager.stop_all()
    assert results == []


def test_stop_all_cleans_stale_pids(runtime_home):
    manager._write_runtime({
        "services": {"mcp_http": {"pid": 7777, "port": config.MCP_HTTP_PORT}},
    })
    with patch.object(manager, "_pid_alive", return_value=False), \
         patch("os.kill") as kill:
        results = manager.stop_all()
    assert results[0]["stopped"] is False
    assert results[0]["note"] == "stale PID"
    kill.assert_not_called()
    assert manager._read_runtime()["services"] == {}


# ── status ────────────────────────────────────────────────────────────────

def test_status_reports_console_via_port_probe(runtime_home):
    with patch.object(manager, "_tcp_in_use", return_value=True), \
         patch.object(manager, "_pid_alive", return_value=False):
        result = manager.status()
    rows = {r["name"]: r for r in result["services"]}
    assert rows["console"]["running"] is True
    assert rows["console"]["pid"] is None  # console has no own process


def test_status_reports_managed_pid_when_alive(runtime_home):
    manager._write_runtime({
        "services": {"mcp_http": {"pid": 8888, "port": config.MCP_HTTP_PORT, "host": "127.0.0.1"}},
    })
    with patch.object(manager, "_tcp_in_use", return_value=True), \
         patch.object(manager, "_pid_alive", return_value=True):
        result = manager.status()
    mcp = next(r for r in result["services"] if r["name"] == "mcp_http")
    assert mcp["running"] is True
    assert mcp["tracked"] is True
    assert mcp["pid"] == 8888


def test_status_cleans_stale_tracked_pid_when_port_also_dead(runtime_home):
    manager._write_runtime({
        "services": {"mcp_http": {"pid": 9090, "port": config.MCP_HTTP_PORT, "host": "127.0.0.1"}},
    })
    with patch.object(manager, "_tcp_in_use", return_value=False), \
         patch.object(manager, "_pid_alive", return_value=False):
        manager.status()
    assert "mcp_http" not in manager._read_runtime()["services"]


def test_status_with_no_runtime_file(runtime_home):
    """No file → all services report not-running gracefully."""
    with patch.object(manager, "_tcp_in_use", return_value=False), \
         patch.object(manager, "_pid_alive", return_value=False):
        result = manager.status()
    names = [r["name"] for r in result["services"]]
    assert names == ["console", "mcp_http", "state_ws"]
    assert all(r["running"] is False for r in result["services"])
