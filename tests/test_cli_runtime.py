"""Tests for the `forge up / down / status` CLI commands."""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from forge_bridge.__main__ import app

runner = CliRunner()


@pytest.fixture
def isolated_runtime(tmp_path, monkeypatch):
    monkeypatch.setenv("FORGE_RUNTIME_DIR", str(tmp_path))
    return tmp_path


def test_up_invokes_starters(isolated_runtime):
    fake_results = [
        {"name": "mcp_http", "started": True, "pid": 111, "host": "127.0.0.1",
         "port": 9997, "ready": True, "managed": True, "source": "forge"},
        {"name": "state_ws", "started": True, "pid": 222, "host": "127.0.0.1",
         "port": 9998, "ready": True, "managed": True, "source": "forge"},
    ]
    with patch("forge_bridge.runtime.manager.start_mcp_http",
               return_value=fake_results[0]) as m1, \
         patch("forge_bridge.runtime.manager.start_state_ws",
               return_value=fake_results[1]) as m2:
        result = runner.invoke(app, ["up"])
    assert result.exit_code == 0
    m1.assert_called_once()
    m2.assert_called_once()
    assert "mcp_http" in result.output
    assert "state_ws" in result.output
    # PR5: pid surfaces as "managed (pid 111)", not "pid=111".
    assert "managed (pid 111)" in result.output
    assert "managed (pid 222)" in result.output
    # PR5: forbidden legacy wording.
    assert "tracked" not in result.output


def test_up_external_port_shown_as_external(isolated_runtime):
    """When a service is already running externally, up labels it `external`."""
    fake_results = [
        {"name": "mcp_http", "started": False, "skipped": "external (already running)",
         "pid": None, "host": "127.0.0.1", "port": 9997,
         "managed": False, "source": "external"},
        {"name": "state_ws", "started": True, "pid": 222, "host": "127.0.0.1",
         "port": 9998, "ready": True, "managed": True, "source": "forge"},
    ]
    with patch("forge_bridge.runtime.manager.start_mcp_http",
               return_value=fake_results[0]), \
         patch("forge_bridge.runtime.manager.start_state_ws",
               return_value=fake_results[1]):
        result = runner.invoke(app, ["up"])
    assert result.exit_code == 0
    assert "mcp_http" in result.output
    assert "external" in result.output
    assert "managed (pid 222)" in result.output
    assert "tracked" not in result.output


def test_up_json_envelope(isolated_runtime):
    fake_results = [
        {"name": "mcp_http", "started": False, "skipped": "already running",
         "pid": 111, "host": "127.0.0.1", "port": 9997,
         "managed": True, "source": "forge"},
        {"name": "state_ws", "started": True, "pid": 222, "host": "127.0.0.1",
         "port": 9998, "ready": True, "managed": True, "source": "forge"},
    ]
    with patch("forge_bridge.runtime.manager.start_mcp_http",
               return_value=fake_results[0]), \
         patch("forge_bridge.runtime.manager.start_state_ws",
               return_value=fake_results[1]):
        result = runner.invoke(app, ["up", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.output.strip())
    assert payload["data"][0]["name"] == "mcp_http"
    assert payload["data"][0]["managed"] is True
    assert payload["data"][0]["source"] == "forge"
    assert payload["data"][1]["pid"] == 222
    assert payload["data"][1]["managed"] is True


def test_down_human_output(isolated_runtime):
    with patch("forge_bridge.runtime.manager.stop_all", return_value=[
        {"name": "mcp_http", "stopped": True, "pid": 111, "method": "SIGTERM",
         "managed": True, "source": "forge"},
        {"name": "state_ws", "stopped": False, "note": "stale PID",
         "managed": False, "source": "forge"},
    ]):
        result = runner.invoke(app, ["down"])
    assert result.exit_code == 0
    assert "mcp_http" in result.output
    assert "stopped" in result.output
    assert "managed (pid 111)" in result.output
    assert "stale PID" in result.output


def test_down_external_skipped(isolated_runtime):
    """External entry → reported as external, not stopped."""
    with patch("forge_bridge.runtime.manager.stop_all", return_value=[
        {"name": "mcp_http", "stopped": False,
         "note": "external (no managed PID to stop)",
         "managed": False, "source": "external"},
    ]):
        result = runner.invoke(app, ["down"])
    assert result.exit_code == 0
    assert "external" in result.output
    assert "tracked" not in result.output


def test_down_with_nothing_to_stop(isolated_runtime):
    with patch("forge_bridge.runtime.manager.stop_all", return_value=[]):
        result = runner.invoke(app, ["down"])
    assert result.exit_code == 0
    assert "no managed services to stop" in result.output
    assert "tracked" not in result.output


def test_status_human_output_uses_managed_external(isolated_runtime):
    """PR5: human status output replaces tracked/untracked with managed/external."""
    fake = {
        "services": [
            # console inherits mcp_http source — co-hosted.
            {"name": "console", "running": True, "tracked": False,
             "managed": True, "source": "forge", "pid": 111,
             "host": "127.0.0.1", "port": 9996},
            {"name": "mcp_http", "running": True, "tracked": True,
             "managed": True, "source": "forge", "pid": 111,
             "host": "127.0.0.1", "port": 9997},
            {"name": "state_ws", "running": True, "tracked": False,
             "managed": False, "source": "external", "pid": None,
             "host": "127.0.0.1", "port": 9998},
        ]
    }
    with patch("forge_bridge.runtime.manager.status", return_value=fake):
        result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    out = result.output
    assert "console" in out
    assert "running" in out
    assert "managed (pid 111)" in out
    assert "external" in out  # state_ws row
    # PR5 forbidden wording.
    assert "tracked" not in out
    assert "untracked" not in out


def test_status_human_output_not_running_shows_dash():
    fake = {
        "services": [
            {"name": "state_ws", "running": False, "tracked": False,
             "managed": False, "source": "external", "pid": None,
             "host": "127.0.0.1", "port": 9998},
        ]
    }
    with patch("forge_bridge.runtime.manager.status", return_value=fake):
        result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "not running" in result.output


def test_status_json_envelope(isolated_runtime):
    fake = {"services": [
        {"name": "console", "running": True, "tracked": False,
         "managed": True, "source": "forge", "pid": 111,
         "host": "127.0.0.1", "port": 9996},
    ]}
    with patch("forge_bridge.runtime.manager.status", return_value=fake):
        result = runner.invoke(app, ["status", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.output.strip())
    row = payload["data"]["services"][0]
    assert row["name"] == "console"
    # PR5 fields present in JSON.
    assert row["managed"] is True
    assert row["source"] == "forge"
    # Back-compat: existing fields preserved.
    assert "tracked" in row
    assert "running" in row
    assert "pid" in row


def test_existing_commands_still_work(isolated_runtime):
    """Adding up/down/status must not break PR1/PR2 commands."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for token in ("doctor", "actions", "console", "mcp", "flame", "up", "down", "status"):
        assert token in result.output, f"missing {token!r}"
