"""Regression tests for startup_bridge graceful degradation.

Phase 07.1 nyquist gate: this test MUST fail against forge-bridge v1.2.0
(where startup_bridge's try/except only wraps wait_until_connected, letting
_client.start()'s ConnectionRefusedError escape) and MUST pass against the
v1.2.1 fix (where the try/except wraps both start() and wait_until_connected,
and _client is nulled out on failure so shutdown_bridge is a no-op).

Reproducer one-liner (manual): in the `forge` env, with nothing bound to
:9998, `python -m projekt_forge --no-db` on v1.2.0 produces an
ExceptionGroup with ConnectionRefusedError. On v1.2.1 it boots cleanly.
"""

from __future__ import annotations

import asyncio
import logging
import socket

import pytest

from forge_bridge.mcp import server as mcp_server


def _find_free_port() -> int:
    """Bind a socket to port 0 (OS assigns a free port), close it, and
    return the port number. This gives us a port that is guaranteed
    NOT to have a listener on it when the test starts."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    return port


@pytest.fixture(autouse=True)
def _reset_server_module():
    """Ensure the mcp.server module globals are clean before + after each test."""
    mcp_server._client = None
    mcp_server._server_started = False
    yield
    # Best-effort cleanup in case a test left a client stub around
    if mcp_server._client is not None:
        try:
            asyncio.get_event_loop().run_until_complete(mcp_server.shutdown_bridge())
        except Exception:
            pass
    mcp_server._client = None
    mcp_server._server_started = False


async def test_startup_bridge_graceful_degradation_on_dead_port(caplog, monkeypatch):
    """startup_bridge MUST NOT propagate a connection error when :9998 is dead.

    The existing docstring + warning log promise "forge_* tools will fail.
    flame_* tools still work if Flame is running." The v1.2.0 code violates
    that contract because _client.start() raises first and escapes the
    try/except that was intended to guard wait_until_connected.
    """
    dead_port = _find_free_port()
    dead_url = f"ws://127.0.0.1:{dead_port}"
    monkeypatch.setenv("FORGE_BRIDGE_URL", dead_url)

    with caplog.at_level(logging.WARNING, logger="forge_bridge.mcp.server"):
        # MUST NOT raise. This is the nyquist assertion.
        await mcp_server.startup_bridge()

    # _client should be None so shutdown_bridge is a no-op
    assert mcp_server._client is None, (
        "After a failed connect, _client must be nulled out so shutdown_bridge's "
        "`if _client:` guard cleanly skips. Current state leaves a half-dead client."
    )

    # The warning log from the existing graceful-degradation path fired
    warning_messages = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    assert any("Could not connect to forge-bridge" in m for m in warning_messages), (
        f"Expected the existing 'Could not connect to forge-bridge' WARNING to fire. "
        f"Saw warnings: {warning_messages!r}"
    )


async def test_shutdown_bridge_after_failed_startup(monkeypatch):
    """shutdown_bridge MUST be a no-op when startup_bridge failed to connect.

    Regression guard: if the fix leaves _client dangling (even in a half-started
    state), shutdown_bridge would try to .stop() it and potentially raise or hang.
    """
    dead_port = _find_free_port()
    dead_url = f"ws://127.0.0.1:{dead_port}"
    monkeypatch.setenv("FORGE_BRIDGE_URL", dead_url)

    await mcp_server.startup_bridge()
    # MUST NOT raise — the `if _client:` guard in shutdown_bridge must skip
    await mcp_server.shutdown_bridge()
    assert mcp_server._client is None
