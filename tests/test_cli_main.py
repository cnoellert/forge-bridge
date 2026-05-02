"""Tests for forge_bridge.cli.main — unified CLI front door.

PR1: bare invocation prints help and exits 0; MCP only starts via the
explicit ``mcp stdio`` / ``mcp http`` subcommands. ``doctor`` and
``actions`` are top-level aliases of the existing ``console doctor``
and ``console tools`` commands. ``flame ping`` probes :9999/status.
"""
from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from forge_bridge.__main__ import app

runner = CliRunner()


# ── bare invocation: help, no MCP ────────────────────────────────────────

def test_bare_invocation_shows_help_and_exits_zero():
    """`python -m forge_bridge` with no args must print help and exit 0."""
    with patch("forge_bridge.mcp.server.main") as mcp_main:
        result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "forge-bridge" in result.output
    assert "mcp" in result.output
    assert "console" in result.output
    mcp_main.assert_not_called()


def test_help_flag_does_not_start_mcp():
    with patch("forge_bridge.mcp.server.main") as mcp_main:
        result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output or "usage" in result.output.lower()
    mcp_main.assert_not_called()


# ── command surface visible from top-level help ──────────────────────────

def test_top_level_help_lists_expected_commands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    out = result.output
    for token in ("doctor", "actions", "mcp", "flame", "console"):
        assert token in out, f"top-level help missing {token!r}"


# ── mcp group: explicit start only ───────────────────────────────────────

def test_mcp_stdio_invokes_server_with_stdio_transport():
    with patch("forge_bridge.mcp.server.main") as mcp_main:
        result = runner.invoke(app, ["mcp", "stdio"])
    assert result.exit_code == 0
    mcp_main.assert_called_once()
    assert mcp_main.call_args.kwargs.get("transport") == "stdio"


def test_mcp_http_default_port_9997():
    with patch("forge_bridge.mcp.server.main") as mcp_main:
        result = runner.invoke(app, ["mcp", "http"])
    assert result.exit_code == 0
    mcp_main.assert_called_once()
    kwargs = mcp_main.call_args.kwargs
    assert kwargs.get("transport") == "streamable-http"
    assert kwargs.get("port") == 9997


def test_mcp_http_port_override():
    with patch("forge_bridge.mcp.server.main") as mcp_main:
        result = runner.invoke(app, ["mcp", "http", "--port", "12345"])
    assert result.exit_code == 0
    mcp_main.assert_called_once()
    assert mcp_main.call_args.kwargs.get("port") == 12345


def test_mcp_stdio_help_does_not_start_server():
    with patch("forge_bridge.mcp.server.main") as mcp_main:
        result = runner.invoke(app, ["mcp", "stdio", "--help"])
    assert result.exit_code == 0
    mcp_main.assert_not_called()


def test_mcp_http_help_does_not_start_server():
    with patch("forge_bridge.mcp.server.main") as mcp_main:
        result = runner.invoke(app, ["mcp", "http", "--help"])
    assert result.exit_code == 0
    assert "--port" in result.output
    mcp_main.assert_not_called()


# ── flame ping: thin /status probe ───────────────────────────────────────

class _FakeResponse:
    def __init__(self, status_code: int, body: dict | None = None):
        self.status_code = status_code
        self._body = body or {}

    def json(self) -> dict:
        return self._body


class _FakeClient:
    """Minimal stand-in for httpx.Client used by flame ping."""

    def __init__(self, *, response=None, exc=None, **_kwargs):
        self._response = response
        self._exc = exc

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False

    def get(self, _url):
        if self._exc is not None:
            raise self._exc
        return self._response


def test_flame_ping_ok_human():
    fake = _FakeResponse(200, {"status": "running", "flame_available": True})
    with patch("httpx.Client", lambda **kw: _FakeClient(response=fake, **kw)):
        result = runner.invoke(app, ["flame", "ping"])
    assert result.exit_code == 0
    assert "flame bridge: ok" in result.output
    assert "flame_available: True" in result.output


def test_flame_ping_ok_json():
    fake = _FakeResponse(200, {"status": "running", "flame_available": True})
    with patch("httpx.Client", lambda **kw: _FakeClient(response=fake, **kw)):
        result = runner.invoke(app, ["flame", "ping", "--json"])
    assert result.exit_code == 0
    import json as _json
    payload = _json.loads(result.output.strip())
    assert payload["data"]["flame_available"] is True


def test_flame_ping_unreachable_exits_2():
    import httpx
    with patch(
        "httpx.Client",
        lambda **kw: _FakeClient(exc=httpx.ConnectError("nope"), **kw),
    ):
        result = runner.invoke(app, ["flame", "ping"])
    assert result.exit_code == 2


def test_flame_ping_unreachable_json_envelope():
    import httpx
    with patch(
        "httpx.Client",
        lambda **kw: _FakeClient(exc=httpx.ConnectError("nope"), **kw),
    ):
        result = runner.invoke(app, ["flame", "ping", "--json"])
    assert result.exit_code == 2
    import json as _json
    payload = _json.loads(result.output.strip())
    assert payload["error"]["code"] == "flame_unreachable"


# ── top-level aliases delegate to console_app handlers ───────────────────

def test_top_level_doctor_is_alias_of_console_doctor():
    """Both `doctor` and `console doctor` resolve to the same callback."""
    from forge_bridge.cli import doctor as doctor_mod
    from forge_bridge.cli.main import app as main_app

    # Walk the Typer click app to find the registered callbacks.
    click_app = typer_to_click(main_app)
    top_doctor = click_app.commands["doctor"].callback
    console_group = click_app.commands["console"]
    console_doctor = console_group.commands["doctor"].callback
    # Typer wraps callbacks; compare the underlying function identity by name.
    assert top_doctor.__wrapped__ is doctor_mod.doctor_cmd or \
        top_doctor is doctor_mod.doctor_cmd or \
        console_doctor is top_doctor


def test_top_level_actions_is_alias_of_console_tools():
    from forge_bridge.cli import tools as tools_mod
    from forge_bridge.cli.main import app as main_app

    click_app = typer_to_click(main_app)
    top_actions = click_app.commands["actions"].callback
    console_group = click_app.commands["console"]
    console_tools = console_group.commands["tools"].callback
    assert top_actions.__wrapped__ is tools_mod.tools_cmd or \
        top_actions is tools_mod.tools_cmd or \
        console_tools is top_actions


def typer_to_click(app):
    """Resolve a Typer.Typer to its underlying click Group."""
    from typer.main import get_command
    return get_command(app)
