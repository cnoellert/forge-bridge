"""Tests for forge_bridge.runtime.manager — process orchestration.

Covers start/stop/status with subprocess.Popen and os.kill mocked, runtime
file roundtrip, stale-PID cleanup, idempotent up, and missing-file safety.
"""
from __future__ import annotations

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
    """Port-only running console (no managed mcp_http) → external."""
    with patch.object(manager, "_tcp_in_use", return_value=True), \
         patch.object(manager, "_pid_alive", return_value=False):
        result = manager.status()
    rows = {r["name"]: r for r in result["services"]}
    assert rows["console"]["running"] is True
    assert rows["console"]["pid"] is None  # console has no own process
    assert rows["console"]["managed"] is False
    assert rows["console"]["source"] == "external"


def test_status_reports_managed_pid_when_alive(runtime_home):
    manager._write_runtime({
        "services": {"mcp_http": {"pid": 8888, "port": config.MCP_HTTP_PORT, "host": "127.0.0.1"}},
    })
    with patch.object(manager, "_tcp_in_use", return_value=True), \
         patch.object(manager, "_pid_alive", return_value=True):
        result = manager.status()
    mcp = next(r for r in result["services"] if r["name"] == "mcp_http")
    assert mcp["running"] is True
    assert mcp["tracked"] is True  # back-compat field still present
    assert mcp["managed"] is True  # PR5
    assert mcp["source"] == "forge"  # PR5
    assert mcp["pid"] == 8888


def test_status_console_inherits_managed_when_mcp_http_managed(runtime_home):
    """Console row carries the same managed/source/pid as mcp_http when co-hosted."""
    manager._write_runtime({
        "services": {"mcp_http": {"pid": 8888, "port": config.MCP_HTTP_PORT, "host": "127.0.0.1"}},
    })
    with patch.object(manager, "_tcp_in_use", return_value=True), \
         patch.object(manager, "_pid_alive", return_value=True):
        result = manager.status()
    rows = {r["name"]: r for r in result["services"]}
    assert rows["console"]["managed"] is True
    assert rows["console"]["source"] == "forge"
    assert rows["console"]["pid"] == 8888  # inherited from mcp_http


def test_status_external_port_owner_reports_external(runtime_home):
    """Port open but no managed PID → managed=False, source=external."""
    with patch.object(manager, "_tcp_in_use", return_value=True), \
         patch.object(manager, "_pid_alive", return_value=False):
        result = manager.status()
    rows = {r["name"]: r for r in result["services"]}
    assert rows["mcp_http"]["managed"] is False
    assert rows["mcp_http"]["source"] == "external"
    assert rows["mcp_http"]["pid"] is None


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
    assert all(r["managed"] is False for r in result["services"])


# ── PR5: managed/source on _start return values ──────────────────────────

def test_start_fresh_returns_managed_forge(runtime_home):
    with patch.object(manager, "_tcp_in_use") as tcp, \
         patch.object(manager, "_pid_alive", return_value=True), \
         patch("subprocess.Popen") as popen:
        tcp.side_effect = [False, True]
        popen.return_value = type("P", (), {"pid": 4242})()
        result = manager.start_mcp_http()
    assert result["managed"] is True
    assert result["source"] == "forge"


def test_start_external_port_returns_managed_false(runtime_home):
    with patch.object(manager, "_tcp_in_use", return_value=True), \
         patch.object(manager, "_pid_alive", return_value=False):
        result = manager.start_mcp_http()
    assert result["managed"] is False
    assert result["source"] == "external"
    assert result["skipped"] == "external (already running)"


def test_start_already_running_managed_returns_managed_forge(runtime_home):
    manager._write_runtime({
        "services": {"mcp_http": {"pid": 5555, "port": config.MCP_HTTP_PORT, "host": "127.0.0.1"}},
    })
    with patch.object(manager, "_pid_alive", return_value=True):
        result = manager.start_mcp_http()
    assert result["managed"] is True
    assert result["source"] == "forge"
    assert result["pid"] == 5555


def test_stop_one_external_record_marks_external(runtime_home):
    """Stopping a record with PID=None → reported as external, not stopped."""
    result = manager._stop_one("mcp_http", {"pid": None, "host": "127.0.0.1",
                                            "port": config.MCP_HTTP_PORT,
                                            "external": True})
    assert result["stopped"] is False
    assert result["managed"] is False
    assert result["source"] == "external"
    assert "external" in result["note"]


# ── restart (launchd-aware) ─────────────────────────────────────────────────


def _svc_row(name, *, running, managed, host="127.0.0.1", port=9997, pid=None):
    return {
        "name": name, "running": running, "managed": managed,
        "source": "forge" if managed else "external", "pid": pid,
        "tracked": managed, "host": host, "port": port,
    }


def test_restart_unknown_target_raises(runtime_home):
    with pytest.raises(ValueError):
        manager.restart("bogus")


def test_restart_launchd_supervised_kickstarts(runtime_home):
    rows = {"services": [_svc_row("mcp_http", running=True, managed=False)]}
    with patch.object(manager, "status", return_value=rows), patch.object(
        manager, "_launchd_label", return_value="com.cnoellert.forge-bridge"
    ), patch.object(
        manager, "_kickstart_launchd", return_value={"ok": True, "returncode": 0}
    ) as kick:
        out = manager.restart("console")
    assert len(out) == 1
    assert out[0]["supervisor"] == "launchd"
    assert out[0]["label"] == "com.cnoellert.forge-bridge"
    assert out[0]["ok"] is True
    kick.assert_called_once_with("com.cnoellert.forge-bridge")


def test_restart_managed_stops_then_starts(runtime_home):
    rows = {"services": [_svc_row("mcp_http", running=True, managed=True, pid=4242)]}
    with patch.object(manager, "status", return_value=rows), patch.object(
        manager, "_launchd_label", return_value=None
    ), patch.object(
        manager, "_stop_one", return_value={"stopped": True}
    ) as stop, patch.object(
        manager, "_wait_for_port_release", return_value=True
    ) as wait_release, patch.object(
        manager, "_start",
        return_value={"started": True, "ready": True, "pid": 5151,
                      "host": "127.0.0.1", "port": 9997},
    ) as start:
        out = manager.restart("console")
    assert out[0]["supervisor"] == "managed"
    assert out[0]["ok"] is True
    stop.assert_called_once()
    wait_release.assert_called_once_with("127.0.0.1", 9997)
    start.assert_called_once_with("mcp_http")


def test_restart_managed_waits_for_port_release_before_start(runtime_home):
    rows = {"services": [_svc_row("mcp_http", running=True, managed=True, pid=4242)]}
    with patch.object(manager, "status", return_value=rows), patch.object(
        manager, "_launchd_label", return_value=None
    ), patch.object(
        manager, "_stop_one", return_value={"stopped": True}
    ), patch.object(
        manager, "_wait_for_port_release", return_value=False
    ) as wait_release, patch.object(manager, "_start") as start:
        out = manager.restart("console")

    assert out[0]["supervisor"] == "managed"
    assert out[0]["ok"] is False
    assert out[0]["note"] == "port did not release before restart"
    wait_release.assert_called_once_with("127.0.0.1", 9997)
    start.assert_not_called()


def test_restart_not_running_starts(runtime_home):
    rows = {"services": [_svc_row("mcp_http", running=False, managed=False)]}
    with patch.object(manager, "status", return_value=rows), patch.object(
        manager, "_launchd_label", return_value=None
    ), patch.object(
        manager, "_start",
        return_value={"started": True, "ready": True, "pid": 9,
                      "host": "127.0.0.1", "port": 9997},
    ) as start:
        out = manager.restart("console")
    assert out[0]["action"] == "start"
    assert out[0]["ok"] is True
    start.assert_called_once_with("mcp_http")


def test_restart_external_unknown_skips(runtime_home):
    rows = {"services": [_svc_row("mcp_http", running=True, managed=False)]}
    with patch.object(manager, "status", return_value=rows), patch.object(
        manager, "_launchd_label", return_value=None
    ):
        out = manager.restart("console")
    assert out[0]["action"] == "skip"
    assert out[0]["supervisor"] == "external"


def test_restart_all_targets_both_services(runtime_home):
    rows = {"services": [
        _svc_row("mcp_http", running=True, managed=False, port=9997),
        _svc_row("state_ws", running=True, managed=False, port=9998),
    ]}
    labels = {"mcp_http": "com.cnoellert.forge-bridge",
              "state_ws": "com.cnoellert.forge-bridge-server"}
    with patch.object(manager, "status", return_value=rows), patch.object(
        manager, "_launchd_label", side_effect=lambda n: labels[n]
    ), patch.object(
        manager, "_kickstart_launchd", return_value={"ok": True, "returncode": 0}
    ):
        out = manager.restart("all")
    assert [r["name"] for r in out] == ["mcp_http", "state_ws"]
    assert all(r["supervisor"] == "launchd" for r in out)


def test_launchd_supervised_running_detects(runtime_home, tmp_path):
    rows = {"services": [
        _svc_row("mcp_http", running=True, managed=False),
        _svc_row("state_ws", running=False, managed=False),
        _svc_row("console", running=True, managed=False),
    ]}
    label_dir = tmp_path / "LaunchDaemons"
    label_dir.mkdir()
    (label_dir / "com.cnoellert.forge-bridge.plist").write_text("x")
    with patch.object(manager, "status", return_value=rows), patch.object(
        manager, "_LAUNCHD_DIR", label_dir
    ):
        out = manager.launchd_supervised_running()
    assert out == ["mcp_http"]
