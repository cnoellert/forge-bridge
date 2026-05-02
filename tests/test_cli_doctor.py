"""HEALTH-03 — forge-bridge console doctor tests.

Covers the full check matrix from CONTEXT.md Area 1:
  - exit-code taxonomy: 0 (ok/warn-only), 1 (any fail), 2 (server unreachable)
  - JSONL parseability + T-11-01 raw-line redaction + T-11-02 lock-free read
  - sidecar/probation dir presence + writability
  - --json mode envelope
"""
from __future__ import annotations

import json
from unittest.mock import patch

import httpx
import typer
from typer.testing import CliRunner

from forge_bridge.cli.doctor import doctor_cmd

runner = CliRunner()


def _make_app():
    app = typer.Typer()
    app.command("doctor")(doctor_cmd)

    @app.command("__noop__", hidden=True)
    def _noop() -> None:  # pragma: no cover - stub
        pass

    return app


def _mock_transport(monkeypatch, handler):
    transport = httpx.MockTransport(handler)
    real_init = httpx.Client.__init__

    def patched(self, *a, **kw):
        kw["transport"] = transport
        real_init(self, *a, **kw)

    monkeypatch.setattr(httpx.Client, "__init__", patched)


def _setup_writable_dirs(tmp_path, monkeypatch):
    """Redirect ~/.forge-bridge/* to tmp_path and create writable subdirs.

    Also stubs subprocess.run so _check_daemon_state() returns a consistent
    ok result in integration tests. Without this stub the check calls the
    real systemctl/launchctl, which returns non-zero for uninstalled daemons
    and makes every CliRunner-level test fail on developer machines and CI.

    The stub returns stdout matching the "both running" pattern for whichever
    OS branch executes, so daemon_state → ok and existing exit-code assertions
    are unaffected.
    """
    from unittest.mock import MagicMock
    import sys as _sys
    import forge_bridge.cli.doctor as _doctor_module

    forge_home = tmp_path / ".forge-bridge"
    forge_home.mkdir()
    (forge_home / "synthesized").mkdir()
    (forge_home / "probation").mkdir()
    monkeypatch.setenv("HOME", str(tmp_path))
    # Stub subprocess.run → all daemons ok → daemon_state=ok
    # Linux branch checks stdout == "active"; macOS branch parses "state = running".
    if _sys.platform == "linux":
        _daemon_stdout = "active\n"
    else:
        _daemon_stdout = "state = running\n"
    monkeypatch.setattr(
        _doctor_module.subprocess, "run",
        lambda *a, **kw: MagicMock(stdout=_daemon_stdout, returncode=0),
    )


HEALTHY = {
    "data": {
        "status": "ok",
        "services": {
            "mcp": {"status": "ok", "detail": ""},
            "watcher": {"status": "ok", "detail": ""},
            "console_port": {"status": "ok", "port": 9996, "detail": ""},
            "flame_bridge": {"status": "ok", "detail": ""},
            "ws_server": {"status": "ok", "detail": ""},
            "llm_backends": [],
            "storage_callback": {"status": "absent", "detail": ""},
        },
        "instance_identity": {
            "execution_log": {"id_match": True, "detail": ""},
            "manifest_service": {"id_match": True, "detail": ""},
        },
    },
    "meta": {},
}


def _make_bad_health(**overrides):
    """Deep-copy HEALTHY then overlay service overrides."""
    body = json.loads(json.dumps(HEALTHY))
    body["data"]["services"].update(overrides)
    return body


def test_all_ok_exit_0(monkeypatch, tmp_path):
    _setup_writable_dirs(tmp_path, monkeypatch)
    # Empty JSONL is "ok" — 0 lines parsed cleanly
    (tmp_path / ".forge-bridge" / "executions.jsonl").write_text("")
    _mock_transport(monkeypatch, lambda r: httpx.Response(200, json=HEALTHY))
    result = runner.invoke(
        _make_app(), ["doctor"],
        env={"FORGE_CONSOLE_PORT": "9996", "HOME": str(tmp_path)},
    )
    assert result.exit_code == 0


def test_critical_fail_exit_1(monkeypatch, tmp_path):
    _setup_writable_dirs(tmp_path, monkeypatch)
    (tmp_path / ".forge-bridge" / "executions.jsonl").write_text("")
    bad = _make_bad_health(mcp={"status": "fail", "detail": "lifespan not started"})
    _mock_transport(monkeypatch, lambda r: httpx.Response(200, json=bad))
    result = runner.invoke(
        _make_app(), ["doctor"],
        env={"FORGE_CONSOLE_PORT": "9996", "HOME": str(tmp_path)},
    )
    assert result.exit_code == 1


def test_non_critical_warn_exit_0(monkeypatch, tmp_path):
    """Storage absent + LLM offline → warn-only → exit 0."""
    _setup_writable_dirs(tmp_path, monkeypatch)
    (tmp_path / ".forge-bridge" / "executions.jsonl").write_text("")
    body = _make_bad_health(
        storage_callback={"status": "absent", "detail": ""},
        llm_backends=[{"name": "ollama", "status": "fail", "detail": "offline"}],
    )
    _mock_transport(monkeypatch, lambda r: httpx.Response(200, json=body))
    result = runner.invoke(
        _make_app(), ["doctor"],
        env={"FORGE_CONSOLE_PORT": "9996", "HOME": str(tmp_path)},
    )
    assert result.exit_code == 0


def test_unreachable_exit_2(monkeypatch, tmp_path):
    _setup_writable_dirs(tmp_path, monkeypatch)

    def unreach(req):
        raise httpx.ConnectError("refused")

    _mock_transport(monkeypatch, unreach)
    result = runner.invoke(
        _make_app(), ["doctor"],
        env={"FORGE_CONSOLE_PORT": "9996", "HOME": str(tmp_path)},
    )
    assert result.exit_code == 2
    assert "server is not running" in result.output


def test_jsonl_parse_error_exit_1(monkeypatch, tmp_path):
    _setup_writable_dirs(tmp_path, monkeypatch)
    # One valid line + one malformed
    jsonl = tmp_path / ".forge-bridge" / "executions.jsonl"
    jsonl.write_text('{"valid": true}\nNOT_JSON\n')
    _mock_transport(monkeypatch, lambda r: httpx.Response(200, json=HEALTHY))
    result = runner.invoke(
        _make_app(), ["doctor"],
        env={"FORGE_CONSOLE_PORT": "9996", "HOME": str(tmp_path)},
    )
    assert result.exit_code == 1
    assert "JSONDecodeError" in result.output
    # T-11-01 / LRN-05: raw line content must NOT appear
    assert "NOT_JSON" not in result.output


def test_jsonl_missing_warns(monkeypatch, tmp_path):
    _setup_writable_dirs(tmp_path, monkeypatch)
    # No JSONL file written
    _mock_transport(monkeypatch, lambda r: httpx.Response(200, json=HEALTHY))
    result = runner.invoke(
        _make_app(), ["doctor"],
        env={"FORGE_CONSOLE_PORT": "9996", "HOME": str(tmp_path)},
    )
    assert result.exit_code == 0  # warn-only
    assert "log file not found" in result.output


def test_jsonl_partial_last_line_skipped(monkeypatch, tmp_path):
    _setup_writable_dirs(tmp_path, monkeypatch)
    jsonl = tmp_path / ".forge-bridge" / "executions.jsonl"
    # Last line lacks \n — concurrent-writer guard skips it
    jsonl.write_text('{"a": 1}\n{"b": 2')
    _mock_transport(monkeypatch, lambda r: httpx.Response(200, json=HEALTHY))
    result = runner.invoke(
        _make_app(), ["doctor"],
        env={"FORGE_CONSOLE_PORT": "9996", "HOME": str(tmp_path)},
    )
    # Only the complete line was parsed; partial line was skipped.
    assert result.exit_code == 0


def test_jsonl_no_lock_acquired(monkeypatch, tmp_path):
    """T-11-02: doctor's JSONL probe must NOT acquire any file lock."""
    _setup_writable_dirs(tmp_path, monkeypatch)
    (tmp_path / ".forge-bridge" / "executions.jsonl").write_text('{"x": 1}\n')
    _mock_transport(monkeypatch, lambda r: httpx.Response(200, json=HEALTHY))
    with patch("fcntl.flock") as mock_flock, patch("fcntl.lockf") as mock_lockf:
        result = runner.invoke(
            _make_app(), ["doctor"],
            env={"FORGE_CONSOLE_PORT": "9996", "HOME": str(tmp_path)},
        )
    assert mock_flock.call_count == 0
    assert mock_lockf.call_count == 0
    assert result.exit_code == 0


def test_doctor_json_mode(monkeypatch, tmp_path):
    _setup_writable_dirs(tmp_path, monkeypatch)
    (tmp_path / ".forge-bridge" / "executions.jsonl").write_text("")
    _mock_transport(monkeypatch, lambda r: httpx.Response(200, json=HEALTHY))
    result = runner.invoke(
        _make_app(), ["doctor", "--json"],
        env={"FORGE_CONSOLE_PORT": "9996", "HOME": str(tmp_path)},
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output.strip())
    assert "checks" in parsed["data"]
    assert isinstance(parsed["data"]["checks"], list)
    assert parsed["data"]["exit_code"] == 0


def test_doctor_json_mode_unreachable(monkeypatch, tmp_path):
    _setup_writable_dirs(tmp_path, monkeypatch)

    def unreach(req):
        raise httpx.ConnectError("refused")

    _mock_transport(monkeypatch, unreach)
    result = runner.invoke(
        _make_app(), ["doctor", "--json"],
        env={"FORGE_CONSOLE_PORT": "9996", "HOME": str(tmp_path)},
    )
    assert result.exit_code == 2
    parsed = json.loads(result.output.strip())
    assert parsed["error"]["code"] == "server_unreachable"


def test_sidecar_dir_missing_warns(monkeypatch, tmp_path):
    """No synthesized/ dir → warn (not fail) per the dir-writable check."""
    forge_home = tmp_path / ".forge-bridge"
    forge_home.mkdir()
    (forge_home / "executions.jsonl").write_text("")
    # NOTE: no synthesized/ or probation/ subdirs
    monkeypatch.setenv("HOME", str(tmp_path))
    _mock_transport(monkeypatch, lambda r: httpx.Response(200, json=HEALTHY))
    # Stub subprocess.run so _check_daemon_state() doesn't call real launchctl/systemctl.
    import forge_bridge.cli.doctor as _dm
    monkeypatch.setattr(_dm.subprocess, "run",
                        lambda *a, **kw: MagicMock(stdout="state = running\n", returncode=0))
    # Use --json so the long "directory does not exist" string isn't truncated
    # by the Rich table's fact-column width.
    result = runner.invoke(
        _make_app(), ["doctor", "--json"],
        env={"FORGE_CONSOLE_PORT": "9996", "HOME": str(tmp_path)},
    )
    # Both dirs missing → warn-only → exit 0
    assert result.exit_code == 0
    parsed = json.loads(result.output.strip())
    sidecar = next(c for c in parsed["data"]["checks"] if c["name"] == "sidecar_dir")
    probation = next(c for c in parsed["data"]["checks"] if c["name"] == "probation_dir")
    assert sidecar["status"] == "warn"
    assert "directory does not exist" in sidecar["fact"]
    assert probation["status"] == "warn"


def test_doctor_help_examples():
    result = runner.invoke(_make_app(), ["doctor", "--help"])
    assert result.exit_code == 0
    assert "Examples:" in result.output


# ---------------------------------------------------------------------------
# daemon_state sub-check tests (Plan 20.1-05 / D-13)
# ---------------------------------------------------------------------------

import sys
from unittest.mock import MagicMock  # noqa: E402 — appended block; patch already imported above


@patch("forge_bridge.cli.doctor.subprocess.run")
def test_daemon_state_linux_both_active(mock_run):
    """Linux: both units active → ok."""
    mock_run.return_value = MagicMock(stdout="active\n", returncode=0)
    with patch.object(sys, "platform", "linux"):
        from forge_bridge.cli.doctor import _check_daemon_state
        result = _check_daemon_state()
    assert result["status"] == "ok"
    assert "forge-bridge-server=active" in result["fact"]
    assert "forge-bridge=active" in result["fact"]
    assert result["name"] == "daemon_state"


@patch("forge_bridge.cli.doctor.subprocess.run")
def test_daemon_state_darwin_partial(mock_run):
    """macOS: bus running, console not → warn (single-row partial-state legibility)."""
    def runner_(args, *a, **kw):
        if "forge-bridge-server" in args[2]:
            return MagicMock(stdout="state = running\n", returncode=0)
        return MagicMock(stdout="state = not running\n", returncode=0)
    mock_run.side_effect = runner_
    with patch.object(sys, "platform", "darwin"):
        from forge_bridge.cli.doctor import _check_daemon_state
        result = _check_daemon_state()
    assert result["status"] == "warn"
    assert result["name"] == "daemon_state"


@patch("forge_bridge.cli.doctor.subprocess.run")
def test_daemon_state_probe_fail_surfaces_class_name(mock_run):
    """T-11-01 / LRN-05: subprocess failure surfaces exception CLASS, never str(exc)."""
    mock_run.side_effect = FileNotFoundError("systemctl: command not found")
    with patch.object(sys, "platform", "linux"):
        from forge_bridge.cli.doctor import _check_daemon_state
        result = _check_daemon_state()
    assert "FileNotFoundError" in result["fact"]
    # NEVER str(exc) — the literal "command not found" must NOT appear in the fact cell.
    assert "command not found" not in result["fact"], \
        f"T-11-01 violation: str(exc) leaked into doctor fact cell: {result['fact']!r}"
    assert result["status"] == "fail"
