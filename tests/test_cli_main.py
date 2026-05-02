"""Tests for forge_bridge.__main__ — --transport and --mcp-port flag parsing.

Mirrors tests/test_cli_doctor.py style (CliRunner, monkeypatch).
All tests monkeypatch forge_bridge.mcp.server.main to a no-op so they do not
actually start the MCP server — they test CLI parsing only.
"""
from __future__ import annotations

import os
from unittest.mock import patch

import typer
from typer.testing import CliRunner

# Import the Typer app from the entry-point module
from forge_bridge.__main__ import app

runner = CliRunner()


def _make_noop_mcp_main(**kwargs):
    """Return a function that records call args without starting the server."""
    calls: list[dict] = []

    def _noop(*args, **kw):
        calls.append({"args": args, "kwargs": kw})

    _noop.calls = calls
    return _noop


# ---------------------------------------------------------------------------
# --transport flag smoke tests (flag parsing only; server NOT started)
# ---------------------------------------------------------------------------

def test_transport_flag_stdio(monkeypatch):
    """--transport stdio is accepted (the default path, smoke test)."""
    noop = _make_noop_mcp_main()
    monkeypatch.setattr("forge_bridge.mcp.server.main", noop)
    # Use --help so the callback is parsed but server is not started
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "--transport" in result.output


def test_transport_flag_sse(monkeypatch):
    """--transport sse is accepted."""
    noop = _make_noop_mcp_main()
    with patch("forge_bridge.mcp.server.main", noop):
        result = runner.invoke(app, ["--transport", "sse"])
    assert result.exit_code == 0
    assert noop.calls, "mcp_main was not called"
    assert noop.calls[0]["kwargs"].get("transport") == "sse"


def test_transport_flag_streamable_http(monkeypatch):
    """--transport streamable-http is accepted."""
    noop = _make_noop_mcp_main()
    with patch("forge_bridge.mcp.server.main", noop):
        result = runner.invoke(app, ["--transport", "streamable-http"])
    assert result.exit_code == 0
    assert noop.calls, "mcp_main was not called"
    assert noop.calls[0]["kwargs"].get("transport") == "streamable-http"


def test_transport_flag_invalid(monkeypatch):
    """--transport bogus exits non-zero with a CLI error (not a raw exception)."""
    noop = _make_noop_mcp_main()
    with patch("forge_bridge.mcp.server.main", noop):
        result = runner.invoke(app, ["--transport", "bogus"])
    assert result.exit_code != 0
    # Must not have called the server at all
    assert not noop.calls


def test_transport_default_is_stdio(monkeypatch):
    """Bare invocation (no --transport) defaults to stdio transport."""
    noop = _make_noop_mcp_main()
    with patch("forge_bridge.mcp.server.main", noop):
        result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert noop.calls, "mcp_main was not called on bare invocation"
    assert noop.calls[0]["kwargs"].get("transport") == "stdio"


# ---------------------------------------------------------------------------
# --mcp-port flag + FORGE_MCP_PORT env override
# ---------------------------------------------------------------------------

def test_mcp_port_default_is_9997(monkeypatch):
    """No --mcp-port flag and no env var → default port 9997 forwarded."""
    noop = _make_noop_mcp_main()
    with patch("forge_bridge.mcp.server.main", noop):
        # Clear the env var to ensure defaults kick in
        result = runner.invoke(app, ["--transport", "streamable-http"],
                               env={"FORGE_MCP_PORT": ""})
    # CliRunner sets env vars as strings; empty string causes int() to fail.
    # Re-run without the env var entirely.
    noop2 = _make_noop_mcp_main()
    env_backup = os.environ.pop("FORGE_MCP_PORT", None)
    try:
        with patch("forge_bridge.mcp.server.main", noop2):
            result2 = runner.invoke(app, ["--transport", "streamable-http"])
        assert result2.exit_code == 0
        assert noop2.calls, "mcp_main was not called"
        assert noop2.calls[0]["kwargs"].get("port") == 9997
    finally:
        if env_backup is not None:
            os.environ["FORGE_MCP_PORT"] = env_backup


def test_mcp_port_flag_overrides_default(monkeypatch):
    """--mcp-port 12345 forwards port=12345 regardless of default."""
    noop = _make_noop_mcp_main()
    with patch("forge_bridge.mcp.server.main", noop):
        result = runner.invoke(app, ["--transport", "streamable-http", "--mcp-port", "12345"])
    assert result.exit_code == 0
    assert noop.calls
    assert noop.calls[0]["kwargs"].get("port") == 12345


def test_mcp_port_env_override(monkeypatch):
    """FORGE_MCP_PORT env var is read and forwarded when no --mcp-port flag given."""
    noop = _make_noop_mcp_main()
    monkeypatch.setenv("FORGE_MCP_PORT", "11111")
    with patch("forge_bridge.mcp.server.main", noop):
        result = runner.invoke(app, ["--transport", "streamable-http"])
    assert result.exit_code == 0
    assert noop.calls
    assert noop.calls[0]["kwargs"].get("port") == 11111


def test_mcp_port_flag_precedence(monkeypatch):
    """Explicit --mcp-port flag wins over FORGE_MCP_PORT env var."""
    noop = _make_noop_mcp_main()
    monkeypatch.setenv("FORGE_MCP_PORT", "11111")
    with patch("forge_bridge.mcp.server.main", noop):
        result = runner.invoke(app, ["--transport", "streamable-http", "--mcp-port", "22222"])
    assert result.exit_code == 0
    assert noop.calls
    # Flag wins over env
    assert noop.calls[0]["kwargs"].get("port") == 22222


def test_mcp_port_env_stdio_does_not_error(monkeypatch):
    """FORGE_MCP_PORT set but --transport stdio (default) → env is read but ignored by server."""
    noop = _make_noop_mcp_main()
    monkeypatch.setenv("FORGE_MCP_PORT", "12345")
    with patch("forge_bridge.mcp.server.main", noop):
        result = runner.invoke(app, ["--transport", "stdio"])
    # Must not error — the CLI resolves port but server.main ignores it under stdio
    assert result.exit_code == 0
    assert noop.calls
    assert noop.calls[0]["kwargs"].get("transport") == "stdio"
