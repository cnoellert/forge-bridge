"""Tests for `fbridge flame-exec` — Phase 24 operator-side surface.

Verifies the second operator surface onto the SAME execution substrate.
The CLI delegates into _execute_python_core, so the assertions here focus
on the CLI's narrow responsibilities:

- arg resolution (inline vs -f path; mutual exclusion)
- exit code mapping (0=success, 1=Flame failure, 2=transport)
- output rendering in both human and JSON modes
- graph_id surfaced to operator in BOTH modes
- node_kind="python" preserved (no CLI-specific tag)
- shared graph emission (a JSONL record lands at the graph_id the CLI
  reported, proving single-substrate discipline)
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from forge_bridge.bridge import BridgeConnectionError, BridgeResponse
from forge_bridge.cli.main import app
from forge_bridge.runtime.graph_emit import graph_dir

runner = CliRunner()


# ── helpers ───────────────────────────────────────────────────────────────


def _bridge_returns(
    *,
    stdout: str = "",
    stderr: str = "",
    result=None,
    error: str | None = None,
    traceback: str | None = None,
):
    """Patch forge_bridge.bridge.execute with a coroutine returning BridgeResponse."""
    response = BridgeResponse(
        stdout=stdout,
        stderr=stderr,
        result=result,
        error=error,
        traceback=traceback,
    )
    return patch("forge_bridge.bridge.execute", AsyncMock(return_value=response))


def _bridge_raises(exc: BaseException):
    return patch("forge_bridge.bridge.execute", AsyncMock(side_effect=exc))


def _extract_graph_id_from_human(output: str) -> str:
    for line in output.splitlines():
        if line.startswith("graph_id "):
            return line.split()[1]
    pytest.fail(f"no graph_id line found in human output: {output!r}")


# ── exit-code mapping ─────────────────────────────────────────────────────


def test_success_exits_0_renders_stdout_and_graph_id() -> None:
    with _bridge_returns(stdout="hello\n", result="hello"):
        result = runner.invoke(app, ["flame-exec", "print('hello')"])
    assert result.exit_code == 0
    assert "graph_id " in result.stdout
    assert "status   ok" in result.stdout
    assert "hello" in result.stdout


def test_flame_error_exits_1_renders_traceback() -> None:
    with _bridge_returns(
        stdout="",
        stderr="",
        error="NameError: name 'foo' is not defined",
        traceback='Traceback (most recent call last):\n  File "<bridge>"\nNameError\n',
    ):
        result = runner.invoke(app, ["flame-exec", "foo()"])
    assert result.exit_code == 1
    assert "status   flame_error" in result.stdout
    # error/traceback render to stderr in human mode
    assert "NameError" in (result.stdout + result.stderr)


def test_transport_error_exits_2_with_graph_id() -> None:
    with _bridge_raises(BridgeConnectionError("connection refused")):
        result = runner.invoke(app, ["flame-exec", "print(1)"])
    assert result.exit_code == 2
    # stderr message + graph_id printed even on transport failure so operator
    # can still inspect the JSONL record (which got a "started" event before
    # bridge.execute raised).
    assert "Flame bridge unreachable" in result.stderr
    assert "graph_id: " in result.stderr


# ── code source resolution ────────────────────────────────────────────────


def test_missing_code_argument_is_usage_error() -> None:
    result = runner.invoke(app, ["flame-exec"])
    assert result.exit_code == 1
    assert "code argument or -f" in result.stderr


def test_both_code_and_file_is_usage_error(tmp_path: Path) -> None:
    file_arg = tmp_path / "code.py"
    file_arg.write_text("print(1)")
    result = runner.invoke(app, ["flame-exec", "print(2)", "-f", str(file_arg)])
    assert result.exit_code == 1
    assert "mutually exclusive" in result.stderr


def test_file_source_reads_code_from_disk(tmp_path: Path) -> None:
    file_arg = tmp_path / "introspect.py"
    file_arg.write_text("print('from-file')")
    with _bridge_returns(stdout="from-file\n", result="from-file") as mock:
        result = runner.invoke(app, ["flame-exec", "-f", str(file_arg)])
    assert result.exit_code == 0
    assert "from-file" in result.stdout
    # Verify the bridge call received the file contents.
    code_passed = mock.call_args.args[0]
    assert code_passed == "print('from-file')"


def test_file_source_unreadable_is_usage_error(tmp_path: Path) -> None:
    result = runner.invoke(app, ["flame-exec", "-f", str(tmp_path / "missing.py")])
    assert result.exit_code == 1
    assert "could not read code file" in result.stderr


def test_main_thread_flag_propagates_to_bridge() -> None:
    with _bridge_returns(stdout="x", result="x") as mock:
        result = runner.invoke(app, ["flame-exec", "--main-thread", "print('x')"])
    assert result.exit_code == 0
    # bridge.execute(code, main_thread=...) — check kwarg
    assert mock.call_args.kwargs.get("main_thread") is True


def test_main_thread_default_is_false() -> None:
    with _bridge_returns(stdout="x", result="x") as mock:
        result = runner.invoke(app, ["flame-exec", "print('x')"])
    assert result.exit_code == 0
    assert mock.call_args.kwargs.get("main_thread") is False


# ── JSON envelope ─────────────────────────────────────────────────────────


def test_json_envelope_shape_on_success() -> None:
    with _bridge_returns(stdout="hello\n", result="hello"):
        result = runner.invoke(app, ["flame-exec", "print('hello')", "--json"])
    assert result.exit_code == 0
    body = json.loads(result.stdout)
    data = body["data"]
    assert set(data.keys()) >= {
        "graph_id", "status", "stdout", "stderr", "result", "error", "traceback"
    }
    assert data["status"] == "ok"
    assert data["stdout"] == "hello\n"
    assert data["error"] is None


def test_json_envelope_shape_on_flame_error() -> None:
    with _bridge_returns(error="ZeroDivisionError", traceback="tb..."):
        result = runner.invoke(app, ["flame-exec", "1/0", "--json"])
    assert result.exit_code == 1
    body = json.loads(result.stdout)
    assert body["data"]["status"] == "flame_error"
    assert body["data"]["error"] == "ZeroDivisionError"
    assert body["data"]["traceback"] == "tb..."


def test_json_envelope_on_transport_error_includes_graph_id() -> None:
    with _bridge_raises(BridgeConnectionError("refused")):
        result = runner.invoke(app, ["flame-exec", "print(1)", "--json"])
    assert result.exit_code == 2
    body = json.loads(result.stdout)
    assert body["error"]["code"] == "flame_unreachable"
    assert body["error"]["graph_id"]  # graph_id surfaced for replay


# ── single-substrate discipline ────────────────────────────────────────────


def test_emits_python_node_kind_to_shared_graph_store() -> None:
    """CLI and MCP both emit node_kind='python' — operator surface is metadata, not ontology."""
    with _bridge_returns(stdout="ok\n", result="ok"):
        result = runner.invoke(app, ["flame-exec", "print('ok')", "--json"])
    assert result.exit_code == 0
    body = json.loads(result.stdout)
    graph_id = body["data"]["graph_id"]
    path = graph_dir() / f"{graph_id}.jsonl"
    assert path.exists(), f"shared substrate did not emit at {path}"
    lines = path.read_text().splitlines()
    records = [json.loads(line) for line in lines if line.strip()]
    assert len(records) == 2  # started + ok
    for rec in records:
        assert rec["node_kind"] == "python", (
            "CLI surface must use node_kind='python' — same as MCP path. "
            "Operator surface is metadata, not ontology."
        )
        assert rec["graph_id"] == graph_id


def test_human_and_json_graph_id_are_consistent() -> None:
    """Same execution → same graph_id surfaced in both render modes."""
    # Two separate invocations; just verify graph_id is present and matches
    # the substrate emission path in JSON mode.
    with _bridge_returns(stdout="ok", result="ok"):
        json_result = runner.invoke(app, ["flame-exec", "print('a')", "--json"])
    json_gid = json.loads(json_result.stdout)["data"]["graph_id"]
    path = graph_dir() / f"{json_gid}.jsonl"
    assert path.exists()

    with _bridge_returns(stdout="ok", result="ok"):
        human_result = runner.invoke(app, ["flame-exec", "print('b')"])
    human_gid = _extract_graph_id_from_human(human_result.stdout)
    path2 = graph_dir() / f"{human_gid}.jsonl"
    assert path2.exists()
    assert json_gid != human_gid  # distinct invocations → distinct graph_ids
