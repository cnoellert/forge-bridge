"""Tests for forge_bridge.config — centralized runtime defaults."""
from __future__ import annotations

from forge_bridge import config


def test_default_constants():
    assert config.CONSOLE_HOST == "127.0.0.1"
    assert config.CONSOLE_PORT == 9996
    assert config.MCP_HTTP_HOST == "127.0.0.1"
    assert config.MCP_HTTP_PORT == 9997
    assert config.STATE_WS_HOST == "127.0.0.1"
    assert config.STATE_WS_PORT == 9998
    assert config.FLAME_BRIDGE_HOST == "127.0.0.1"
    assert config.FLAME_BRIDGE_PORT == 9999
    assert config.FLAME_SIDECAR_HOST == "127.0.0.1"
    assert config.FLAME_SIDECAR_PORT == 10000


def test_helpers_match_defaults_when_env_unset(monkeypatch):
    for var in (
        "FORGE_CONSOLE_HOST", "FORGE_CONSOLE_PORT",
        "FORGE_MCP_HTTP_HOST", "FORGE_MCP_PORT",
        "FORGE_STATE_WS_HOST", "FORGE_STATE_WS_PORT",
        "FORGE_BRIDGE_HOST", "FORGE_BRIDGE_PORT",
        "FORGE_FLAME_SIDECAR_HOST", "FORGE_FLAME_SIDECAR_PORT",
    ):
        monkeypatch.delenv(var, raising=False)

    assert config.console_host() == "127.0.0.1"
    assert config.console_port() == 9996
    assert config.console_url() == "http://127.0.0.1:9996"
    assert config.mcp_http_url() == "http://127.0.0.1:9997"
    assert config.state_ws_url() == "ws://127.0.0.1:9998"
    assert config.flame_bridge_url() == "http://127.0.0.1:9999"
    assert config.flame_sidecar_url() == "http://127.0.0.1:10000"


def test_env_override_int(monkeypatch):
    monkeypatch.setenv("FORGE_CONSOLE_PORT", "8888")
    assert config.console_port() == 8888


def test_env_override_str(monkeypatch):
    monkeypatch.setenv("FORGE_BRIDGE_HOST", "10.0.0.5")
    assert config.flame_bridge_host() == "10.0.0.5"


def test_env_invalid_int_falls_back_to_default(monkeypatch):
    """Unparseable env values should not crash callers — fall back to default."""
    monkeypatch.setenv("FORGE_CONSOLE_PORT", "not-a-number")
    assert config.console_port() == config.CONSOLE_PORT


def test_env_empty_string_uses_default(monkeypatch):
    monkeypatch.setenv("FORGE_CONSOLE_PORT", "")
    assert config.console_port() == config.CONSOLE_PORT
