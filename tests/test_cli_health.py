"""HEALTH-02 — forge-bridge console health tests."""
from __future__ import annotations

import json

import httpx
import typer
from typer.testing import CliRunner

from forge_bridge.cli.health import health_cmd

runner = CliRunner()


def _make_app():
    app = typer.Typer()
    app.command("health")(health_cmd)

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


HEALTHY_RESPONSE = {
    "data": {
        "status": "ok",
        "ts": "2026-04-24T10:00:00+00:00",
        "version": "1.3.0",
        "services": {
            "mcp": {"status": "ok", "detail": "lifespan started"},
            "watcher": {"status": "ok", "detail": ""},
            "console_port": {"status": "ok", "port": 9996, "detail": ""},
            "flame_bridge": {"status": "ok", "detail": ""},
            "ws_server": {"status": "ok", "detail": ""},
            "llm_backends": [{"name": "ollama", "status": "ok", "detail": ""}],
            "storage_callback": {"status": "absent", "detail": ""},
        },
        "instance_identity": {
            "execution_log": {"id_match": True, "detail": "canonical"},
            "manifest_service": {"id_match": True, "detail": "canonical"},
        },
    },
    "meta": {},
}


def _ok_handler(request):
    return httpx.Response(200, json=HEALTHY_RESPONSE)


def test_renders_panels(monkeypatch):
    _mock_transport(monkeypatch, _ok_handler)
    result = runner.invoke(_make_app(), ["health"], env={"FORGE_CONSOLE_PORT": "9996"})
    assert result.exit_code == 0
    # Critical block names
    assert "mcp" in result.output
    assert "watcher" in result.output
    assert "console_port" in result.output
    # Degraded-tolerant block
    assert "flame_bridge" in result.output
    assert "ws_server" in result.output
    # Provenance / llm
    assert "storage_callback" in result.output
    assert "ollama" in result.output


def test_json_envelope(monkeypatch):
    _mock_transport(monkeypatch, _ok_handler)
    result = runner.invoke(
        _make_app(), ["health", "--json"],
        env={"FORGE_CONSOLE_PORT": "9996"},
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output.strip())
    assert parsed["data"]["status"] == "ok"


def test_unreachable_rich(monkeypatch):
    def unreach(req):
        raise httpx.ConnectError("refused")

    _mock_transport(monkeypatch, unreach)
    result = runner.invoke(_make_app(), ["health"], env={"FORGE_CONSOLE_PORT": "9996"})
    assert result.exit_code == 2
    assert "server is not running" in result.output


def test_unreachable_json(monkeypatch):
    def unreach(req):
        raise httpx.ConnectError("refused")

    _mock_transport(monkeypatch, unreach)
    result = runner.invoke(
        _make_app(), ["health", "--json"],
        env={"FORGE_CONSOLE_PORT": "9996"},
    )
    assert result.exit_code == 2
    parsed = json.loads(result.output.strip())
    assert parsed["error"]["code"] == "server_unreachable"


def test_help_examples():
    result = runner.invoke(_make_app(), ["health", "--help"])
    assert result.exit_code == 0
    assert "Examples:" in result.output


def test_no_llm_backends_renders_none_row(monkeypatch):
    """LLM backends panel must render even when the backend list is empty."""
    response = json.loads(json.dumps(HEALTHY_RESPONSE))  # deep copy
    response["data"]["services"]["llm_backends"] = []

    def handler(req):
        return httpx.Response(200, json=response)

    _mock_transport(monkeypatch, handler)
    result = runner.invoke(_make_app(), ["health"], env={"FORGE_CONSOLE_PORT": "9996"})
    assert result.exit_code == 0
    assert "(none)" in result.output
