"""MFST-05 — forge-bridge console manifest tests.

Covers:
- list view rendering (same columns as tools)
- -q/--search filter (client-side)
- --json passthrough byte-identical to /api/v1/manifest
- connection-error UX (Rich + JSON)
- --help Examples block
"""
from __future__ import annotations

import json

import httpx
import typer
from typer.testing import CliRunner

from forge_bridge.cli.manifest import manifest_cmd

runner = CliRunner()


def _make_app():
    app = typer.Typer()
    app.command("manifest")(manifest_cmd)

    # Force subcommand-mode dispatch.
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


SAMPLE_MANIFEST_TOOLS = [
    {
        "name": "synth_foo",
        "origin": "synthesized",
        "namespace": "synth",
        "synthesized_at": "2026-04-22T10:00:00+00:00",
        "code_hash": "a" * 64,
        "version": "1.0.0",
        "observation_count": 5,
        "tags": [],
        "meta": {},
    },
    {
        "name": "flame_bar",
        "origin": "builtin",
        "namespace": "flame",
        "synthesized_at": None,
        "code_hash": None,
        "version": None,
        "observation_count": 0,
        "tags": [],
        "meta": {},
    },
]
MANIFEST_RESPONSE = {
    "data": {
        "tools": SAMPLE_MANIFEST_TOOLS,
        "count": 2,
        "schema_version": "1",
    },
    "meta": {},
}


def _ok_handler(request):
    return httpx.Response(200, json=MANIFEST_RESPONSE)


def test_lists_manifest(monkeypatch):
    _mock_transport(monkeypatch, _ok_handler)
    result = runner.invoke(_make_app(), ["manifest"], env={"FORGE_CONSOLE_PORT": "9996"})
    assert result.exit_code == 0
    assert "synth_foo" in result.output
    assert "flame_bar" in result.output


def test_search_filter(monkeypatch):
    _mock_transport(monkeypatch, _ok_handler)
    result = runner.invoke(
        _make_app(), ["manifest", "-q", "flame"],
        env={"FORGE_CONSOLE_PORT": "9996"},
    )
    assert result.exit_code == 0
    assert "flame_bar" in result.output
    assert "synth_foo" not in result.output


def test_json_envelope_byte_identical(monkeypatch):
    _mock_transport(monkeypatch, _ok_handler)
    result = runner.invoke(
        _make_app(), ["manifest", "--json"],
        env={"FORGE_CONSOLE_PORT": "9996"},
    )
    assert result.exit_code == 0
    parsed = json.loads(result.output.strip())
    assert parsed == MANIFEST_RESPONSE


def test_unreachable_rich(monkeypatch):
    def unreach(req):
        raise httpx.ConnectError("refused")

    _mock_transport(monkeypatch, unreach)
    result = runner.invoke(_make_app(), ["manifest"], env={"FORGE_CONSOLE_PORT": "9996"})
    assert result.exit_code == 2
    assert "server is not running" in result.output


def test_unreachable_json(monkeypatch):
    def unreach(req):
        raise httpx.ConnectError("refused")

    _mock_transport(monkeypatch, unreach)
    result = runner.invoke(
        _make_app(), ["manifest", "--json"],
        env={"FORGE_CONSOLE_PORT": "9996"},
    )
    assert result.exit_code == 2
    parsed = json.loads(result.output.strip())
    assert parsed["error"]["code"] == "server_unreachable"


def test_help_examples():
    result = runner.invoke(_make_app(), ["manifest", "--help"])
    assert result.exit_code == 0
    assert "Examples:" in result.output


def test_empty_no_crash(monkeypatch):
    def empty(req):
        return httpx.Response(
            200,
            json={"data": {"tools": [], "count": 0, "schema_version": "1"}, "meta": {}},
        )

    _mock_transport(monkeypatch, empty)
    result = runner.invoke(_make_app(), ["manifest"], env={"FORGE_CONSOLE_PORT": "9996"})
    assert result.exit_code == 0
    assert "No manifest entries found" in result.output
