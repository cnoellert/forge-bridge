"""Phase A.4 — daemon startup-path unification regression tests.

Pre-Phase-A.4, multiple entry points produced different daemon state:
  - launchd shell wrapper waited up to 30s for state_ws to bind on :9998
    before exec'ing mcp_http (`packaging/launchd/forge-bridge-daemon`).
  - `fbridge up` had no equivalent gate. mcp_http and state_ws subprocesses
    were spawned essentially simultaneously; mcp_http's 10s
    wait_until_connected deadline raced state_ws's bind. On race loss,
    `_client = None` was set in the server module and forge_* tools
    returned "forge-bridge client not connected" until restart.

Phase A.4 fix: `bootstrap_daemon()` is the single source of truth for
daemon initialization. It runs `_wait_for_bus()` BEFORE `startup_bridge()`
so every entry point inherits the same 30s gate.

These tests pin the structural invariant:
  1. _wait_for_bus polls until reachable, returns True quickly.
  2. _wait_for_bus returns False after timeout if port never opens.
  3. _wait_for_bus tolerates state_ws coming up late (the fbridge-up race).
  4. bootstrap_daemon calls _wait_for_bus BEFORE startup_bridge.
  5. teardown_daemon reverses bootstrap_daemon (no leaked tasks/globals).
  6. The /api/v1/health endpoint exposes bridge_client.connected so the
     race symptom is observable from outside the process.
"""
from __future__ import annotations

import asyncio
import socket
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ---------------------------------------------------------------------------
# _wait_for_bus — the new bus-readiness gate
# ---------------------------------------------------------------------------


class TestWaitForBus:
    @pytest.mark.asyncio
    async def test_returns_true_when_port_already_open(self):
        """Happy path: bus is already up. Function returns True quickly."""
        from forge_bridge.mcp.server import _wait_for_bus

        # Bind a real listener so the TCP probe succeeds.
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        port = srv.getsockname()[1]
        try:
            ok = await _wait_for_bus(
                f"ws://127.0.0.1:{port}", timeout=5.0, poll_interval=0.05,
            )
        finally:
            srv.close()
        assert ok is True

    @pytest.mark.asyncio
    async def test_returns_false_after_timeout_when_port_never_opens(self):
        """Sad path: bus never binds. Function returns False after timeout
        (NEVER raises — startup_bridge's graceful-degradation contract)."""
        from forge_bridge.mcp.server import _wait_for_bus

        dead_port = _find_free_port()
        ok = await _wait_for_bus(
            f"ws://127.0.0.1:{dead_port}", timeout=0.5, poll_interval=0.05,
        )
        assert ok is False

    @pytest.mark.asyncio
    async def test_tolerates_late_binding_bus(self):
        """The fbridge-up race scenario: bus binds AFTER bootstrap starts.
        _wait_for_bus must keep polling and detect the late bind. This is
        the structural invariant Phase A.4 fixes."""
        from forge_bridge.mcp.server import _wait_for_bus

        port = _find_free_port()
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        async def _bind_late():
            await asyncio.sleep(0.4)
            srv.bind(("127.0.0.1", port))
            srv.listen(1)

        try:
            late_binder = asyncio.create_task(_bind_late())
            ok = await _wait_for_bus(
                f"ws://127.0.0.1:{port}", timeout=3.0, poll_interval=0.1,
            )
            await late_binder
        finally:
            try:
                srv.close()
            except Exception:
                pass
        assert ok is True, (
            "Phase A.4 invariant: late-binding bus must be detected. "
            "If this fails, the fbridge-up race is back."
        )

    @pytest.mark.asyncio
    async def test_zero_timeout_skips_immediately(self):
        """timeout<=0 short-circuits — used by tests/contexts where the
        wait is undesirable. Must NOT raise."""
        from forge_bridge.mcp.server import _wait_for_bus

        ok = await _wait_for_bus("ws://127.0.0.1:9998", timeout=0.0)
        assert ok is False


# ---------------------------------------------------------------------------
# bootstrap_daemon — single source of truth invariants
# ---------------------------------------------------------------------------


class TestBootstrapDaemonOrdering:
    @pytest.mark.asyncio
    async def test_wait_for_bus_called_before_startup_bridge(self):
        """Phase A.4 ordering invariant: _wait_for_bus runs FIRST.
        Without this ordering the race the fix exists to close would
        re-open."""
        from forge_bridge.mcp import server as _mcp_server

        call_order: list[str] = []

        async def _record_wait(*args, **kwargs):
            call_order.append("_wait_for_bus")
            return False

        async def _record_startup():
            call_order.append("startup_bridge")

        with patch.object(
            _mcp_server, "_wait_for_bus", new=AsyncMock(side_effect=_record_wait),
        ), patch.object(
            _mcp_server, "startup_bridge", new=AsyncMock(side_effect=_record_startup),
        ), patch.object(
            _mcp_server, "shutdown_bridge", new=AsyncMock(return_value=None),
        ), patch(
            "forge_bridge.learning.watcher.watch_synthesized_tools",
            new=AsyncMock(return_value=None),
        ), patch.object(
            _mcp_server, "_start_console_task", new=AsyncMock(return_value=(None, None)),
        ):
            result = await _mcp_server.bootstrap_daemon(_mcp_server.mcp)
            try:
                assert call_order == ["_wait_for_bus", "startup_bridge"], (
                    f"bootstrap_daemon call order is wrong: {call_order!r}. "
                    "Phase A.4 invariant: _wait_for_bus MUST precede startup_bridge."
                )
            finally:
                await _mcp_server.teardown_daemon(result)


class TestBootstrapDaemonSingletons:
    @pytest.mark.asyncio
    async def test_publishes_canonical_singletons_and_clears_on_teardown(self):
        """bootstrap_daemon publishes _canonical_console_read_api etc.;
        teardown_daemon clears them. Mirrors what _lifespan used to do
        directly. Catches any future regression where a singleton is set
        but not torn down (or vice versa)."""
        from forge_bridge.mcp import server as _mcp_server

        with patch.object(
            _mcp_server, "_wait_for_bus", new=AsyncMock(return_value=False),
        ), patch.object(
            _mcp_server, "startup_bridge", new=AsyncMock(return_value=None),
        ), patch.object(
            _mcp_server, "shutdown_bridge", new=AsyncMock(return_value=None),
        ), patch(
            "forge_bridge.learning.watcher.watch_synthesized_tools",
            new=AsyncMock(return_value=None),
        ), patch.object(
            _mcp_server, "_start_console_task", new=AsyncMock(return_value=(None, None)),
        ):
            result = await _mcp_server.bootstrap_daemon(_mcp_server.mcp)

            # During the live window, the canonical references are populated.
            assert _mcp_server._canonical_console_read_api is not None
            assert _mcp_server._canonical_execution_log is not None
            assert _mcp_server._canonical_manifest_service is not None
            assert _mcp_server._canonical_watcher_task is not None
            assert _mcp_server._server_started is True

            # ConsoleReadAPI must have llm_router wired (Bug B regression).
            assert _mcp_server._canonical_console_read_api._llm_router is not None

            await _mcp_server.teardown_daemon(result)

        # After teardown, every canonical reference is cleared.
        assert _mcp_server._canonical_console_read_api is None
        assert _mcp_server._canonical_execution_log is None
        assert _mcp_server._canonical_manifest_service is None
        assert _mcp_server._canonical_watcher_task is None
        assert _mcp_server._server_started is False

    @pytest.mark.asyncio
    async def test_reentrant_bootstrap_reuses_canonical_runtime_singletons(self):
        """Nested FastMCP lifespans lease one process runtime."""
        from forge_bridge.mcp import server as _mcp_server

        startup = AsyncMock(return_value=None)
        shutdown = AsyncMock(return_value=None)

        with patch.object(
            _mcp_server, "_wait_for_bus", new=AsyncMock(return_value=False),
        ), patch.object(
            _mcp_server, "startup_bridge", new=startup,
        ), patch.object(
            _mcp_server, "shutdown_bridge", new=shutdown,
        ), patch(
            "forge_bridge.learning.watcher.watch_synthesized_tools",
            new=AsyncMock(return_value=None),
        ), patch.object(
            _mcp_server, "_start_console_task", new=AsyncMock(return_value=(None, None)),
        ):
            first = await _mcp_server.bootstrap_daemon(_mcp_server.mcp)
            second = await _mcp_server.bootstrap_daemon(_mcp_server.mcp)
            second_released = False
            try:
                assert second is first
                assert second.execution_log is first.execution_log
                assert second.manifest_service is first.manifest_service
                assert second.dispatch_consumer_task is first.dispatch_consumer_task
                assert second.generation_poller_task is first.generation_poller_task
                assert second.terminal_consumer_task is first.terminal_consumer_task
                startup.assert_awaited_once()
                assert (
                    _mcp_server._canonical_console_read_api._execution_log
                    is first.execution_log
                )
                health = await first.console_read_api.get_health()
                assert health["instance_identity"]["execution_log"]["id_match"] is True
                assert (
                    health["instance_identity"]["manifest_service"]["id_match"]
                    is True
                )

                await _mcp_server.teardown_daemon(second)
                second_released = True
                assert _mcp_server._server_started is True
                assert not first.dispatch_consumer_task.done()
                assert not first.generation_poller_task.done()
                assert not first.terminal_consumer_task.done()
                shutdown.assert_not_awaited()
            finally:
                if not second_released:
                    await _mcp_server.teardown_daemon(second)
                await _mcp_server.teardown_daemon(first)

            assert first.dispatch_consumer_task.done()
            assert first.generation_poller_task.done()
            assert first.terminal_consumer_task.done()
            shutdown.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_terminal_consumer_bounds_every_empty_poll_transaction(
        self,
        monkeypatch,
    ):
        """An empty event poll commits and closes before the worker sleeps."""
        from forge_bridge.mcp import server as _mcp_server
        from forge_bridge.orchestration import engine, event_consumer

        shutdown_event = asyncio.Event()
        sessions = []

        class FakeSession:
            def __init__(self):
                self.commits = 0
                self.rollbacks = 0
                self.closed = False

            async def commit(self):
                self.commits += 1

            async def rollback(self):
                self.rollbacks += 1

        class SessionContext:
            def __init__(self):
                self.session = FakeSession()

            async def __aenter__(self):
                sessions.append(self.session)
                return self.session

            async def __aexit__(self, *_exc):
                self.session.closed = True

        class FakeConsumer:
            calls = 0

            def __init__(self, _session, *, graph_engine):
                self.graph_engine = graph_engine

            async def process_pending(self, *, after_event_id=None):
                del after_event_id
                type(self).calls += 1
                if type(self).calls == 2:
                    shutdown_event.set()
                return []

        monkeypatch.setattr(engine, "GraphEngine", lambda _session: object())
        monkeypatch.setattr(
            event_consumer, "GraphEngineEventConsumer", FakeConsumer
        )

        await _mcp_server._run_terminal_consumer(
            lambda: SessionContext(),
            poll_interval_seconds=0,
            shutdown_event=shutdown_event,
        )

        assert len(sessions) == 2
        assert all(session.commits == 1 for session in sessions)
        assert all(session.rollbacks == 0 for session in sessions)
        assert all(session.closed is True for session in sessions)


# ---------------------------------------------------------------------------
# Health endpoint exposes the bridge-client state — visibility invariant
# ---------------------------------------------------------------------------


class TestBridgeClientHealthVisibility:
    @pytest.mark.asyncio
    async def test_bridge_client_check_present_in_health_services(self):
        """/api/v1/health must surface bridge_client.connected so operators
        can see the race symptom without having to call a forge_* tool.

        Pre-Phase-A.4, ``mcp: ok`` could mask ``_client is None`` —
        the symptom we're fixing was invisible at the health-endpoint
        boundary. This test pins that the visibility is now there."""
        from forge_bridge.console.read_api import ConsoleReadAPI
        from forge_bridge.console.manifest_service import ManifestService
        from forge_bridge.mcp import server as _mcp_server

        # Stand up a minimal ReadAPI and force _client to None to simulate
        # the post-race state.
        api = ConsoleReadAPI(
            execution_log=MagicMock(),
            manifest_service=ManifestService(),
            console_port=9996,
        )
        with patch.object(_mcp_server, "_client", new=None):
            health = await api.get_health()

        services = health["services"]
        assert "bridge_client" in services, (
            "Phase A.4 visibility invariant: bridge_client must appear in "
            "/api/v1/health services. If this fails, the race symptom is "
            "invisible from outside the process again."
        )
        bc = services["bridge_client"]
        assert bc["status"] == "fail"
        assert bc["connected"] is False
        # Overall status flips to "degraded" — non-critical because flame_*
        # tools still work even when the bridge client is down.
        assert health["status"] in ("degraded", "fail"), (
            f"bridge_client fail must affect overall status; got {health['status']!r}"
        )

    @pytest.mark.asyncio
    async def test_bridge_client_check_reports_connected_when_client_alive(self):
        """Mirror invariant: when _client is connected, bridge_client.status
        is 'ok' and connected=True."""
        from forge_bridge.console.read_api import ConsoleReadAPI
        from forge_bridge.console.manifest_service import ManifestService
        from forge_bridge.mcp import server as _mcp_server

        api = ConsoleReadAPI(
            execution_log=MagicMock(),
            manifest_service=ManifestService(),
            console_port=9996,
        )
        fake_client = MagicMock()
        fake_client.is_connected = True
        with patch.object(_mcp_server, "_client", new=fake_client):
            health = await api.get_health()

        bc = health["services"]["bridge_client"]
        assert bc["status"] == "ok"
        assert bc["connected"] is True
