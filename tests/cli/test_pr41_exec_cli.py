"""PR41 — `fbridge exec` HTTP transport + Typer command tests.

Two angles:
- Helper-only (`_exec_http`) tests pin transport correctness via httpx.MockTransport.
- CLI tests stub `_exec_http` with `monkeypatch.setattr` and exercise the Typer
  command end-to-end with `CliRunner` to pin exit codes + rendering.
"""
from __future__ import annotations

import json

import httpx
import pytest
from typer.testing import CliRunner

from forge_bridge.cli import exec as exec_module
from forge_bridge.cli.exec import ExecTransportError, _exec_http
from forge_bridge.cli.main import app


# ────────────────────────────────────────────────────────────────────────────
# Helper-only tests (transport correctness)
# ────────────────────────────────────────────────────────────────────────────


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_exec_http_success_returns_envelope():
    def handler(request):
        body = json.loads(request.content)
        assert body == {"text": "list projects"}
        return httpx.Response(
            200,
            json={"status": "success", "request_id": "abc", "chain": [], "error": None},
        )

    result = _exec_http("list projects", client=_client(handler))

    assert result["status"] == "success"
    assert result["chain"] == []


def test_exec_http_connect_error_classified():
    def handler(request):
        raise httpx.ConnectError("refused")

    with pytest.raises(ExecTransportError) as ei:
        _exec_http("x", client=_client(handler))

    assert ei.value.kind == "CONNECT_ERROR"


def test_exec_http_connect_timeout_classified_as_transport():
    """Regression guard: ConnectTimeout is NOT a ConnectError subclass — must still map to CONNECT_ERROR."""
    def handler(request):
        raise httpx.ConnectTimeout("timed out")

    with pytest.raises(ExecTransportError) as ei:
        _exec_http("x", client=_client(handler))

    assert ei.value.kind == "CONNECT_ERROR"


def test_exec_http_non_200_classified():
    def handler(request):
        return httpx.Response(500, text="boom")

    with pytest.raises(ExecTransportError) as ei:
        _exec_http("x", client=_client(handler))

    assert ei.value.kind == "HTTP_STATUS"
    assert ei.value.detail == "500"


def test_exec_http_invalid_json_classified():
    def handler(request):
        return httpx.Response(200, content=b"not json")

    with pytest.raises(ExecTransportError) as ei:
        _exec_http("x", client=_client(handler))

    assert ei.value.kind == "INVALID_JSON"


def test_exec_http_uses_env_override(monkeypatch):
    captured = {}

    def handler(request):
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"status": "success", "chain": []})

    monkeypatch.setenv("FORGE_CONSOLE_URL", "http://test-host:5555")
    _exec_http("x", client=_client(handler))

    assert captured["url"] == "http://test-host:5555/api/v1/exec"


# ────────────────────────────────────────────────────────────────────────────
# CLI tests (exit codes + rendering)
# ────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def runner() -> CliRunner:
    # click 8.2+ always captures stderr separately; mix_stderr kwarg was removed.
    return CliRunner()


def test_cli_exec_success_default_rendering(runner, monkeypatch):
    monkeypatch.setattr(
        exec_module,
        "_exec_http",
        lambda text, **_: {
            "status": "success",
            "request_id": "rid",
            "chain": [
                {"step": "list projects", "result": {"projects": []}},
            ],
            "error": None,
        },
    )

    result = runner.invoke(app, ["exec", "list projects"])

    assert result.exit_code == 0
    assert "--- list projects" in result.stdout
    assert '"projects"' in result.stdout


def test_cli_exec_success_json_flag_emits_raw_envelope(runner, monkeypatch):
    monkeypatch.setattr(
        exec_module,
        "_exec_http",
        lambda text, **_: {
            "status": "success",
            "request_id": "rid",
            "chain": [],
            "error": None,
        },
    )

    result = runner.invoke(app, ["exec", "list projects", "--json"])

    assert result.exit_code == 0
    body = json.loads(result.stdout)
    assert body["status"] == "success"
    assert body["request_id"] == "rid"


def test_cli_exec_execution_error_exit_4(runner, monkeypatch):
    monkeypatch.setattr(
        exec_module,
        "_exec_http",
        lambda text, **_: {
            "status": "error",
            "request_id": "rid",
            "chain": [],
            "error": {"code": "EMPTY_COMMAND", "message": "nothing", "step_index": None, "original_error": None},
        },
    )

    result = runner.invoke(app, ["exec", ""])

    assert result.exit_code == 4
    # Default rendering writes the error to stderr.
    assert "EMPTY_COMMAND" in result.stderr


def test_cli_exec_connect_error_exit_2(runner, monkeypatch):
    def boom(text, **_):
        raise ExecTransportError("CONNECT_ERROR")

    monkeypatch.setattr(exec_module, "_exec_http", boom)

    result = runner.invoke(app, ["exec", "list projects"])

    assert result.exit_code == 2
    assert "fbridge up" in result.stderr


def test_cli_exec_http_status_exit_3(runner, monkeypatch):
    def boom(text, **_):
        raise ExecTransportError("HTTP_STATUS", "500")

    monkeypatch.setattr(exec_module, "_exec_http", boom)

    result = runner.invoke(app, ["exec", "list projects"])

    assert result.exit_code == 3
    assert "500" in result.stderr


def test_cli_exec_invalid_json_exit_3(runner, monkeypatch):
    def boom(text, **_):
        raise ExecTransportError("INVALID_JSON")

    monkeypatch.setattr(exec_module, "_exec_http", boom)

    result = runner.invoke(app, ["exec", "list projects"])

    assert result.exit_code == 3


def test_cli_exec_http_error_exit_2(runner, monkeypatch):
    """Catch-all httpx.HTTPError (read timeout, network) is treated as transport failure."""
    def boom(text, **_):
        raise ExecTransportError("HTTP_ERROR", "read timeout")

    monkeypatch.setattr(exec_module, "_exec_http", boom)

    result = runner.invoke(app, ["exec", "list projects"])

    assert result.exit_code == 2
    assert "read timeout" in result.stderr
