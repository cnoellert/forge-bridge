"""Centralized runtime defaults for forge-bridge surfaces.

Single source of truth for the host/port pairs the CLI and runtime use to
talk to each other. Anything CLI-facing should pull defaults from here
instead of inlining literals — so there's exactly one place to change a
port, and operators can read this file to learn the topology.

Both forms are exposed:

* Module-level constants (``CONSOLE_PORT`` etc.) for callers that just want
  the default value.
* Helper functions (``console_port()`` etc.) for callers that want the
  default with the matching ``FORGE_*`` env-var override applied.

Env-var overrides are intentionally permissive: an unparseable value falls
back to the default rather than raising. CLI surfaces that already validate
their own env vars (e.g. ``cli/client.resolve_port``) keep their stricter
behavior; the helpers here are for read-only consumers like ``doctor``.
"""
from __future__ import annotations

import os

# ── Defaults ────────────────────────────────────────────────────────────
CONSOLE_HOST = "127.0.0.1"
CONSOLE_PORT = 9996

MCP_HTTP_HOST = "127.0.0.1"
MCP_HTTP_PORT = 9997

STATE_WS_HOST = "127.0.0.1"
STATE_WS_PORT = 9998

FLAME_BRIDGE_HOST = "127.0.0.1"
FLAME_BRIDGE_PORT = 9999

FLAME_SIDECAR_HOST = "127.0.0.1"
FLAME_SIDECAR_PORT = 10000


# ── Env-var override helpers ────────────────────────────────────────────
def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_str(name: str, default: str) -> str:
    return os.environ.get(name) or default


def console_host() -> str:
    return _env_str("FORGE_CONSOLE_HOST", CONSOLE_HOST)


def console_port() -> int:
    return _env_int("FORGE_CONSOLE_PORT", CONSOLE_PORT)


def console_url() -> str:
    return f"http://{console_host()}:{console_port()}"


def mcp_http_host() -> str:
    return _env_str("FORGE_MCP_HTTP_HOST", MCP_HTTP_HOST)


def mcp_http_port() -> int:
    return _env_int("FORGE_MCP_PORT", MCP_HTTP_PORT)


def mcp_http_url() -> str:
    return f"http://{mcp_http_host()}:{mcp_http_port()}"


def state_ws_host() -> str:
    return _env_str("FORGE_STATE_WS_HOST", STATE_WS_HOST)


def state_ws_port() -> int:
    return _env_int("FORGE_STATE_WS_PORT", STATE_WS_PORT)


def state_ws_url() -> str:
    return f"ws://{state_ws_host()}:{state_ws_port()}"


def flame_bridge_host() -> str:
    return _env_str("FORGE_BRIDGE_HOST", FLAME_BRIDGE_HOST)


def flame_bridge_port() -> int:
    return _env_int("FORGE_BRIDGE_PORT", FLAME_BRIDGE_PORT)


def flame_bridge_url() -> str:
    return f"http://{flame_bridge_host()}:{flame_bridge_port()}"


def flame_sidecar_host() -> str:
    return _env_str("FORGE_FLAME_SIDECAR_HOST", FLAME_SIDECAR_HOST)


def flame_sidecar_port() -> int:
    return _env_int("FORGE_FLAME_SIDECAR_PORT", FLAME_SIDECAR_PORT)


def flame_sidecar_url() -> str:
    return f"http://{flame_sidecar_host()}:{flame_sidecar_port()}"
