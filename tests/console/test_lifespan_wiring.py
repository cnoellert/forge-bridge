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

from unittest.mock import AsyncMock, patch

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
    ), patch.object(
        # Phase A.4: skip the 30s bus-readiness wait in unit tests — same
        # rationale as the startup_bridge patch above (Pitfall 7), avoid
        # blocking on a port that isn't bound during the test.
        _mcp_server, "_wait_for_bus", new=AsyncMock(return_value=False)
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
    ), patch.object(
        # Phase A.4: skip the 30s bus-readiness wait in unit tests — same
        # rationale as the startup_bridge patch above (Pitfall 7), avoid
        # blocking on a port that isn't bound during the test.
        _mcp_server, "_wait_for_bus", new=AsyncMock(return_value=False)
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
    ), patch.object(
        # Phase A.4: skip the 30s bus-readiness wait in unit tests — same
        # rationale as the startup_bridge patch above (Pitfall 7), avoid
        # blocking on a port that isn't bound during the test.
        _mcp_server, "_wait_for_bus", new=AsyncMock(return_value=False)
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


# ── Issue #26 — sibling capability registration at bootstrap (rung A) ──────────

_STUB_TRIPLE = {
    "surface": "genstub",
    "path": "backend",
    "auth_mechanism": "x",
    "revision": "v1",
}
_STUB_BACKEND_ID = "genstub.backend"  # composite the driver registry keys on


class _StubGenDriver:
    # backend_id agrees with the triple-derived id; the registry rejects
    # divergence at registration time.
    backend_id = _STUB_BACKEND_ID
    backend_identity_triple = _STUB_TRIPLE

    async def poll(self, artifact):  # required by _validate_generation_handler
        return None


def _install_stub_sibling() -> str:
    import sys
    import types

    from forge_contracts import CapabilityDeclaration, CapabilityRegistration

    def register_bridge_adapters(ctx, register_capability):
        register_capability(
            CapabilityRegistration(
                declaration=CapabilityDeclaration(
                    capability_id="forge_generators.genstub.backend",
                    family="generation",
                    owner="test-sibling",
                    payload_family="generation_v1",
                    input_schema={"type": "object"},
                    metadata={"backend_identity_triple": _STUB_TRIPLE},
                ),
                handler=_StubGenDriver(),
            )
        )

    name = "tests.issue26_stub_sibling"
    module = types.ModuleType(name)
    module.register_bridge_adapters = register_bridge_adapters
    sys.modules[name] = module
    return f"{name}:register_bridge_adapters"


@pytest.mark.asyncio
async def test_lifespan_registers_sibling_drivers_into_live_registry():
    """Issue #26 rung A: bootstrap Step 5 runs register_all_siblings so a
    generation sibling's driver is reachable in the live driver registry the
    dispatch consumer reads — i.e. dispatch stops degrading to dispatch_no_driver.
    Proves the wiring; on a stock install with no generation sibling the registry
    stays empty by design (rung B installs the drivers)."""
    from forge_bridge.mcp import server as _mcp_server
    from forge_bridge.orchestration import discovery as _discovery

    target = _install_stub_sibling()
    injected = _discovery.resolve_siblings(
        entry_points_loader=lambda _group: {"genstub": target}
    )

    with patch.object(
        _mcp_server, "startup_bridge", new=AsyncMock(return_value=None)
    ), patch.object(
        _mcp_server, "shutdown_bridge", new=AsyncMock(return_value=None)
    ), patch.object(
        _mcp_server, "_wait_for_bus", new=AsyncMock(return_value=False)
    ), patch(
        "forge_bridge.learning.watcher.watch_synthesized_tools",
        new=AsyncMock(return_value=None),
    ), patch.object(
        _mcp_server, "_start_console_task", new=AsyncMock(return_value=(None, None))
    ), patch.object(
        _discovery, "resolve_siblings", return_value=injected
    ):
        async with _mcp_server._lifespan(_mcp_server.mcp):
            registry = _mcp_server._canonical_tool_registry
            assert registry is not None, (
                "Issue #26 regression: bootstrap Step 5 did not publish "
                "_canonical_tool_registry."
            )
            # The declaration is registered...
            assert registry.get("forge_generators.genstub.backend") is not None
            # ...and the driver is reachable in the live driver registry the
            # dispatch consumer was handed.
            driver_registry = registry._generation_driver_registry
            assert driver_registry is not None
            assert driver_registry.get_driver(_STUB_BACKEND_ID) is not None
            assert driver_registry.get_driver("missing.backend") is None

    # Teardown resets the global (no leakage).
    assert _mcp_server._canonical_tool_registry is None, (
        "_canonical_tool_registry leaked after _lifespan exit — teardown reset "
        "missing."
    )
