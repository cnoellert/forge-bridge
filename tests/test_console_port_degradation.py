"""Integration test for API-06 / D-29 port-degradation behavior.

When :9996 (or the configured console port) is unavailable at boot,
`_start_console_task` must log a WARNING and return (None, None) without
raising. The MCP server lifecycle is unaffected — stdio continues to serve.
"""
from __future__ import annotations

import asyncio
import logging
import socket

import pytest  # noqa: F401 — pytest-asyncio auto mode still benefits from import

from forge_bridge.mcp.server import _start_console_task


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def test_start_console_task_returns_task_and_server_on_ok_port(caplog):
    """Happy path: free port, _start_console_task succeeds."""
    port = _find_free_port()

    # Build a minimal ASGI app (no route handlers needed — we just start + stop)
    async def _minimal_app(scope, receive, send):
        if scope["type"] == "lifespan":
            while True:
                msg = await receive()
                if msg["type"] == "lifespan.startup":
                    await send({"type": "lifespan.startup.complete"})
                elif msg["type"] == "lifespan.shutdown":
                    await send({"type": "lifespan.shutdown.complete"})
                    return

    task, server = await _start_console_task(_minimal_app, "127.0.0.1", port)
    try:
        assert task is not None and server is not None, (
            "Free port must yield (Task, Server), not (None, None)"
        )
        assert not task.done(), "uvicorn task should be running"
        assert server.started is True
    finally:
        if server is not None:
            server.should_exit = True
        if task is not None:
            try:
                await asyncio.wait_for(task, timeout=5.0)
            except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
                task.cancel()
                try:
                    await task
                except Exception:
                    pass


async def test_start_console_task_returns_none_none_when_port_busy(caplog):
    """API-06 SC#4: port unavailable → WARNING + (None, None), no raise."""
    busy_port = _find_free_port()
    # Occupy the port — hold the socket open for the duration of the test
    occupier = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    occupier.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    occupier.bind(("127.0.0.1", busy_port))
    occupier.listen(1)

    try:
        async def _minimal_app(scope, receive, send):
            pass

        with caplog.at_level(logging.WARNING, logger="forge_bridge.mcp.server"):
            task, server = await _start_console_task(
                _minimal_app, "127.0.0.1", busy_port,
            )

        assert task is None and server is None, (
            f"Occupied port must return (None, None). Got ({task!r}, {server!r})"
        )
        warning_messages = [
            r.getMessage()
            for r in caplog.records if r.levelno == logging.WARNING
        ]
        assert any(
            f"Console API disabled — port 127.0.0.1:{busy_port}" in m
            for m in warning_messages
        ), (
            f"Expected 'Console API disabled — port 127.0.0.1:{busy_port}' WARNING. "
            f"Got warnings: {warning_messages!r}"
        )
    finally:
        occupier.close()


async def test_start_console_task_does_not_raise_on_busy_port():
    """Even without caplog, the call itself must NOT raise."""
    busy_port = _find_free_port()
    occupier = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    occupier.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    occupier.bind(("127.0.0.1", busy_port))
    occupier.listen(1)
    try:
        async def _minimal_app(scope, receive, send):
            pass
        # MUST NOT raise
        task, server = await _start_console_task(
            _minimal_app, "127.0.0.1", busy_port,
        )
        assert task is None and server is None
    finally:
        occupier.close()
