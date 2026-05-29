from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from forge_bridge.cli import runtime_doctor
from forge_bridge.cli.main import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_check_ratification_ok_when_recent_records(monkeypatch):
    async def _count(window):
        assert window == runtime_doctor._RECENT_ACTIVITY_WINDOW
        return 2

    monkeypatch.setattr(runtime_doctor, "_recent_ratification_count", _count)

    row = runtime_doctor._check_ratification()

    assert row == {
        "name": "ratification",
        "ok": True,
        "chip": "ok",
        "status": "2 ratifications in last 24h",
        "url": row["url"],
        "fix": "",
    }


def test_check_ratification_loaded_when_no_recent_records(monkeypatch):
    async def _count(_window):
        return 0

    monkeypatch.setattr(runtime_doctor, "_recent_ratification_count", _count)

    row = runtime_doctor._check_ratification()

    assert row["name"] == "ratification"
    assert row["ok"] is True
    assert row["chip"] == "loaded"
    assert row["status"] == "no ratifications in last 24h"
    assert row["fix"] == ""


def test_check_ratification_fail_when_session_unreachable(monkeypatch):
    async def _count(_window):
        raise ConnectionError("db down")

    monkeypatch.setattr(runtime_doctor, "_recent_ratification_count", _count)

    row = runtime_doctor._check_ratification()

    assert row["name"] == "ratification"
    assert row["ok"] is False
    assert row["chip"] == "fail"
    assert row["status"] == "db unreachable (ConnectionError)"
    assert "alembic upgrade head" in row["fix"]


def _row(name: str, *, ok: bool = True, chip: str | None = None) -> dict:
    row = {"name": name, "ok": ok, "status": "ok", "url": "", "fix": ""}
    if chip is not None:
        row["chip"] = chip
    return row


def test_runtime_doctor_json_includes_seven_rows(runner, monkeypatch):
    monkeypatch.setattr(runtime_doctor, "_check_console", lambda: _row("console"))
    monkeypatch.setattr(
        runtime_doctor,
        "_check_install_provenance",
        lambda: _row("install_provenance"),
    )
    monkeypatch.setattr(runtime_doctor, "_check_mcp_http", lambda: _row("mcp_http"))
    monkeypatch.setattr(
        runtime_doctor,
        "_check_flame_bridge",
        lambda: _row("flame_bridge"),
    )
    monkeypatch.setattr(runtime_doctor, "_check_state_ws", lambda: _row("state_ws"))
    monkeypatch.setattr(
        runtime_doctor,
        "_check_ratification",
        lambda: _row("ratification", chip="loaded"),
    )
    monkeypatch.setattr(
        runtime_doctor,
        "_check_graph_store",
        lambda: _row("graph_store", chip="loaded"),
    )

    result = runner.invoke(app, ["doctor", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert len(payload["checks"]) == 7
    assert [row["name"] for row in payload["checks"]] == [
        "console",
        "install_provenance",
        "mcp_http",
        "flame_bridge",
        "state_ws",
        "ratification",
        "graph_store",
    ]


def test_runtime_doctor_human_includes_ratification_row(runner, monkeypatch):
    monkeypatch.setattr(runtime_doctor, "_check_console", lambda: _row("console"))
    monkeypatch.setattr(
        runtime_doctor,
        "_check_install_provenance",
        lambda: _row("install_provenance"),
    )
    monkeypatch.setattr(runtime_doctor, "_check_mcp_http", lambda: _row("mcp_http"))
    monkeypatch.setattr(
        runtime_doctor,
        "_check_flame_bridge",
        lambda: _row("flame_bridge"),
    )
    monkeypatch.setattr(runtime_doctor, "_check_state_ws", lambda: _row("state_ws"))
    monkeypatch.setattr(
        runtime_doctor,
        "_check_ratification",
        lambda: _row("ratification", chip="ok"),
    )
    monkeypatch.setattr(
        runtime_doctor,
        "_check_graph_store",
        lambda: _row("graph_store", chip="loaded"),
    )

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "ratification" in result.stdout


def test_runtime_doctor_exit_1_when_ratification_fails(runner, monkeypatch):
    monkeypatch.setattr(runtime_doctor, "_check_console", lambda: _row("console"))
    monkeypatch.setattr(
        runtime_doctor,
        "_check_install_provenance",
        lambda: _row("install_provenance"),
    )
    monkeypatch.setattr(runtime_doctor, "_check_mcp_http", lambda: _row("mcp_http"))
    monkeypatch.setattr(
        runtime_doctor,
        "_check_flame_bridge",
        lambda: _row("flame_bridge"),
    )
    monkeypatch.setattr(runtime_doctor, "_check_state_ws", lambda: _row("state_ws"))
    monkeypatch.setattr(
        runtime_doctor,
        "_check_ratification",
        lambda: _row("ratification", ok=False, chip="fail"),
    )
    monkeypatch.setattr(
        runtime_doctor,
        "_check_graph_store",
        lambda: _row("graph_store", chip="loaded"),
    )

    result = runner.invoke(app, ["doctor", "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
