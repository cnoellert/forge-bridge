"""CLI-03 + P-01 — --json mode stdout purity across all five subcommands.

Three scenarios per command:
  - server returns valid envelope → stdout JSON-parses + exit 0
  - server unreachable → stdout has {"error": {"code": "server_unreachable", ...}} + exit 2
  - server returns 4xx/5xx error envelope → stdout has {"error": {...}} + exit 1

Doctor is intentionally excluded — its --json shape differs and is exercised in
tests/test_cli_doctor.py::test_doctor_json_mode.
"""
from __future__ import annotations

import json

import httpx
import pytest
from typer.testing import CliRunner

from forge_bridge import __main__ as entrypoint

runner = CliRunner()


def _mock_transport(monkeypatch, handler):
    transport = httpx.MockTransport(handler)
    real_init = httpx.Client.__init__

    def patched(self, *a, **kw):
        kw["transport"] = transport
        real_init(self, *a, **kw)

    monkeypatch.setattr(httpx.Client, "__init__", patched)


def _empty_data_handler(request):
    if request.url.path == "/api/v1/health":
        return httpx.Response(200, json={
            "data": {
                "status": "ok",
                "services": {
                    "mcp": {"status": "ok", "detail": ""},
                    "watcher": {"status": "ok", "detail": ""},
                    "console_port": {"status": "ok", "detail": ""},
                    "flame_bridge": {"status": "ok", "detail": ""},
                    "ws_server": {"status": "ok", "detail": ""},
                    "llm_backends": [],
                    "storage_callback": {"status": "absent", "detail": ""},
                },
                "instance_identity": {
                    "execution_log": {"id_match": True},
                    "manifest_service": {"id_match": True},
                },
            },
            "meta": {},
        })
    if request.url.path == "/api/v1/manifest":
        return httpx.Response(200, json={
            "data": {"tools": [], "count": 0, "schema_version": "1"},
            "meta": {},
        })
    return httpx.Response(200, json={"data": [], "meta": {}})


@pytest.mark.parametrize("cmd_args", [
    ["console", "tools", "--json"],
    ["console", "execs", "--json"],
    ["console", "manifest", "--json"],
    ["console", "health", "--json"],
])
def test_json_stdout_is_pure_json(monkeypatch, cmd_args):
    """P-01: --json output is byte-pure JSON across all four list-shape commands."""
    _mock_transport(monkeypatch, _empty_data_handler)
    result = runner.invoke(entrypoint.app, cmd_args, env={"FORGE_CONSOLE_PORT": "9996"})
    assert result.exit_code == 0, f"output: {result.output!r}"
    parsed = json.loads(result.output.strip())
    assert "data" in parsed or "error" in parsed


@pytest.mark.parametrize("cmd_args", [
    ["console", "tools", "--json"],
    ["console", "execs", "--json"],
    ["console", "manifest", "--json"],
    ["console", "health", "--json"],
])
def test_json_unreachable_envelope_pure(monkeypatch, cmd_args):
    def unreach(req):
        raise httpx.ConnectError("refused")

    _mock_transport(monkeypatch, unreach)
    result = runner.invoke(entrypoint.app, cmd_args, env={"FORGE_CONSOLE_PORT": "9996"})
    assert result.exit_code == 2
    parsed = json.loads(result.output.strip())
    assert parsed["error"]["code"] == "server_unreachable"


@pytest.mark.parametrize("cmd_args", [
    ["console", "tools", "--json"],
    ["console", "execs", "--json"],
    ["console", "manifest", "--json"],
    ["console", "health", "--json"],
])
def test_json_http_error_envelope_pure(monkeypatch, cmd_args):
    def err(req):
        return httpx.Response(
            500,
            json={"error": {"code": "internal_error", "message": "boom"}},
        )

    _mock_transport(monkeypatch, err)
    result = runner.invoke(entrypoint.app, cmd_args, env={"FORGE_CONSOLE_PORT": "9996"})
    assert result.exit_code == 1
    parsed = json.loads(result.output.strip())
    assert parsed["error"]["code"] == "internal_error"
