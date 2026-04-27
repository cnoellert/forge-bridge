"""Phase 16.1 (D-07 #1) — boot-wiring regression guard.

Drives the real `_lifespan` via `async with` and asserts:
  - `_canonical_console_read_api` is published (Plan 16.1-03 wiring exists)
  - `_canonical_console_read_api._llm_router is not None`
    (Bug B regression: see commit 60d28fa)
  - On lifespan exit, the global is reset to None (no leakage)

The Phase 16 deploy (assist-01, 2026-04-27) failed with `ConsoleReadAPI`
constructed WITHOUT `llm_router=` — every chat request 500'd. The integration
tests injected a mocked router via app.state directly, bypassing the real
`_lifespan` boot path; nothing asserted the wiring after lifespan init.
This test plugs that hole.

Pitfall 7 (16.1-RESEARCH.md §6): patch startup_bridge + shutdown_bridge
or the test hangs ~10s on the WS connect timeout against :9998.
Also patch watch_synthesized_tools (watcher task startup) and
_start_console_task (uvicorn console task) to avoid port-bind and
filesystem side effects during the smoke test.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_lifespan_publishes_console_read_api():
    """Plan 16.1-03 Task 3.1 wired _canonical_console_read_api in _lifespan
    Step 4 — assert it's actually published when lifespan enters."""
    from forge_bridge.mcp import server as _mcp_server

    # Patch I/O boundaries so the test runs offline.
    # Pitfall 7: startup_bridge + shutdown_bridge must be patched or the test
    # hangs ~10s on the WS connect timeout against :9998.
    # Also patch the watcher task and console uvicorn task to avoid
    # port-bind and filesystem side effects.
    with patch.object(
        _mcp_server, "startup_bridge", new=AsyncMock(return_value=None)
    ), patch.object(
        _mcp_server, "shutdown_bridge", new=AsyncMock(return_value=None)
    ), patch(
        "forge_bridge.learning.watcher.watch_synthesized_tools",
        new=AsyncMock(return_value=None),
    ), patch.object(
        _mcp_server, "_start_console_task", new=AsyncMock(return_value=(None, None))
    ):
        async with _mcp_server._lifespan(_mcp_server.mcp):
            api = _mcp_server._canonical_console_read_api
            assert api is not None, (
                "Plan 16.1-03 regression: _lifespan did not publish "
                "_canonical_console_read_api. Check Step 4 assignment."
            )


@pytest.mark.asyncio
async def test_lifespan_wires_llm_router_into_console_read_api():
    """Bug B regression guard.

    The Phase 16 deploy (assist-01, 2026-04-27) failed with ConsoleReadAPI
    constructed WITHOUT llm_router= — chat_handler then 500'd on every call
    because `app.state.console_read_api._llm_router is None`.
    Commit 60d28fa added the kwarg; this test asserts it stays.

    See:
      - .planning/phases/16-fb-d-chat-endpoint/16-VERIFICATION.md "Bug B"
      - forge_bridge/mcp/server.py:138-144 (the ConsoleReadAPI(...) construction)
    """
    from forge_bridge.mcp import server as _mcp_server

    with patch.object(
        _mcp_server, "startup_bridge", new=AsyncMock(return_value=None)
    ), patch.object(
        _mcp_server, "shutdown_bridge", new=AsyncMock(return_value=None)
    ), patch(
        "forge_bridge.learning.watcher.watch_synthesized_tools",
        new=AsyncMock(return_value=None),
    ), patch.object(
        _mcp_server, "_start_console_task", new=AsyncMock(return_value=(None, None))
    ):
        async with _mcp_server._lifespan(_mcp_server.mcp):
            api = _mcp_server._canonical_console_read_api
            assert api is not None, "_canonical_console_read_api not published"
            assert api._llm_router is not None, (
                "Bug B regression: ConsoleReadAPI was constructed without "
                "llm_router=. See commit 60d28fa for the original fix and "
                "forge_bridge/mcp/server.py:138-144 for the constructor."
            )


@pytest.mark.asyncio
async def test_lifespan_teardown_clears_canonical_console_read_api():
    """Plan 16.1-03 Task 3.1 teardown — assert the global resets on exit."""
    from forge_bridge.mcp import server as _mcp_server

    with patch.object(
        _mcp_server, "startup_bridge", new=AsyncMock(return_value=None)
    ), patch.object(
        _mcp_server, "shutdown_bridge", new=AsyncMock(return_value=None)
    ), patch(
        "forge_bridge.learning.watcher.watch_synthesized_tools",
        new=AsyncMock(return_value=None),
    ), patch.object(
        _mcp_server, "_start_console_task", new=AsyncMock(return_value=(None, None))
    ):
        async with _mcp_server._lifespan(_mcp_server.mcp):
            assert _mcp_server._canonical_console_read_api is not None

    # After exit, the global is back to None.
    assert _mcp_server._canonical_console_read_api is None, (
        "_canonical_console_read_api leaked after _lifespan exit — "
        "teardown reset missing. Check forge_bridge/mcp/server.py "
        "_lifespan finally block."
    )
