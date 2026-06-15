"""
FORGE MCP Server — rebuilt with pluggable registry.

Two connection layers:

  1. forge-bridge (AsyncClient, port 9998)
     Canonical pipeline state: projects, shots, sequences, versions,
     media, layers, stacks, dependency graph, registry, event log.
     Used for all structured pipeline data.

  2. Flame HTTP bridge (port 9999)
     Direct Flame API access: list libraries, execute batch ops,
     query Flame-internal state that isn't in the pipeline model.
     Kept because it's irreplaceable for Flame-native operations.

The client is created once at startup and shared across all tools.
Tools import `get_client()` — they never construct clients themselves.

All tool registrations route through registry.register_builtins(mcp).
No tool is registered directly with mcp.tool() in this file.

Usage:
    python -m forge_bridge.mcp

Config (env vars):
    FORGE_BRIDGE_URL      ws://host:9998   (forge-bridge server)
    FORGE_BRIDGE_HOST     127.0.0.1        (Flame HTTP bridge host)
    FORGE_BRIDGE_PORT     9999             (Flame HTTP bridge port)
    FORGE_MCP_CLIENT_NAME mcp_claude       (client identifier)
    FORGE_CONSOLE_PORT    9996             (Artist Console HTTP API)
"""

from __future__ import annotations

import asyncio
import logging
import os
import socket
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

from mcp.server.fastmcp import FastMCP

from forge_bridge.client import AsyncClient
from forge_bridge.mcp.registry import register_builtins
from forge_bridge.store.session import get_async_session_factory

if TYPE_CHECKING:
    from forge_bridge.console.manifest_service import ManifestService
    from forge_bridge.learning.execution_log import ExecutionLog
    from forge_bridge.orchestration.drivers import GenerationDriverRegistry
    from forge_bridge.orchestration.registration import ToolRegistry  # Issue #26
    from forge_bridge.console.read_api import ConsoleReadAPI  # Phase 16.1 D-07 #1

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Shared client — tools call get_client()
# ─────────────────────────────────────────────────────────────

_client: AsyncClient | None = None
_server_started: bool = False

# Canonical singletons owned by _lifespan (API-04 / D-16 instance-identity gate)
_canonical_execution_log: "ExecutionLog | None" = None
_canonical_manifest_service: "ManifestService | None" = None
# I-02: canonical watcher task handle for _check_watcher crash detection.
_canonical_watcher_task: "asyncio.Task | None" = None
# Phase 16.1 — canonical ConsoleReadAPI for boot-wiring smoke (D-07 #1).
# Set in _lifespan Step 4; cleared on teardown. Read by
# tests/console/test_lifespan_wiring.py to assert _llm_router stayed wired.
_canonical_console_read_api: "ConsoleReadAPI | None" = None
# Issue #26 — canonical ToolRegistry populated from sibling declarations at
# bootstrap Step 5 (the "later adapter rung" the Step-5 comment promised). Feeds
# the live generation_driver_registry the dispatch consumer reads, and holds the
# declaration registry a future live planner (rung C) will consume. Set in Step 5;
# cleared on teardown.
_canonical_tool_registry: "ToolRegistry | None" = None


def get_client() -> AsyncClient:
    """Return the shared AsyncClient. Raises if not yet connected."""
    if _client is None:
        raise RuntimeError(
            "forge-bridge client not connected. "
            "Is the MCP server started via main()?"
        )
    return _client


def _canonical_runtime_singletons() -> tuple["ExecutionLog", "ManifestService"]:
    """Return the process-canonical ExecutionLog and ManifestService.

    Bootstrap may be entered more than once in a long-lived process (for
    example when a serving console task already owns :9996 and the MCP
    lifespan starts again). Replacing these objects while an existing
    ConsoleReadAPI still serves the old pair is the runtime-identity drift
    that `/api/v1/health.instance_identity` detects. Reuse is the contract.
    """
    global _canonical_execution_log, _canonical_manifest_service
    if _canonical_execution_log is None:
        from forge_bridge.learning.execution_log import ExecutionLog

        _canonical_execution_log = ExecutionLog()
    if _canonical_manifest_service is None:
        from forge_bridge.console.manifest_service import ManifestService

        _canonical_manifest_service = ManifestService()
    return _canonical_execution_log, _canonical_manifest_service


# ─────────────────────────────────────────────────────────────
# Phase A.4 — startup-path unification (2026-05-05)
#
# Background. Multiple entry points (Claude Desktop's `mcp stdio`, direct
# `mcp http`, `fbridge up`'s subprocess spawn, and the launchd plist) all
# converge on the same MCP server process. Pre-Phase-A.4, only the launchd
# wrapper (`packaging/launchd/forge-bridge-daemon`) had a 30s `nc -z`
# pre-exec gate that waited for state_ws to be reachable on :9998 before
# starting mcp_http. Every other entry point relied on whatever ordering
# the caller set up. Under `fbridge up`, mcp_http and state_ws are
# spawned as detached subprocesses essentially simultaneously — mcp_http's
# 10s `wait_until_connected` deadline races state_ws's bind, and on race
# loss the server module's `_client` global is set to None and stays None.
# All forge_* tools then return "forge-bridge client not connected" until
# the daemon is restarted. Same code, different state per launch path.
#
# Fix. Pull the bus-readiness gate INTO the daemon's bootstrap so every
# entry point inherits identical initialization. `bootstrap_daemon()` is
# the single source of truth: it polls the bus port, runs `startup_bridge`,
# constructs the canonical singletons (ExecutionLog, ManifestService,
# ConsoleReadAPI, LLMRouter), launches the watcher and console uvicorn
# tasks, and returns a `_BootstrapResult` the lifespan yields over. The
# launchd shell wrapper's `nc` loop is now redundant.
#
# Invariant. Any observable daemon behavior MUST be identical regardless
# of which entry point started it. If a future initialization step is
# needed, it lands in `bootstrap_daemon()`. No entry point may bypass.
# ─────────────────────────────────────────────────────────────


# Default bus-readiness wait (seconds). Mirrors the launchd shell wrapper's
# 30s `nc -z` poll loop. Override via FORGE_BRIDGE_BUS_WAIT_SECONDS for
# test environments or constrained boot scenarios.
_DEFAULT_BUS_WAIT_SECONDS = 30.0


@dataclass
class _BootstrapResult:
    """Singletons + task handles produced by ``bootstrap_daemon``.

    The lifespan yields over this object and hands it back to
    ``teardown_daemon`` on exit so cleanup mirrors construction order.
    """

    execution_log: Any
    manifest_service: Any
    console_read_api: Any
    watcher_task: asyncio.Task
    generation_driver_registry: GenerationDriverRegistry
    tool_registry: Any
    execution_runtime_shutdown: asyncio.Event
    dispatch_consumer_task: asyncio.Task
    generation_poller_task: asyncio.Task
    terminal_consumer_task: asyncio.Task
    console_task: Optional[asyncio.Task]
    console_server: Optional[Any]


def _parse_bus_url(server_url: str) -> tuple[str, int]:
    """Extract (host, port) from a ws://host:port URL.

    Falls back to (127.0.0.1, 9998) on any parse failure — the bus poll
    is a best-effort gate, not a hard precondition. A bad URL just
    means the poll completes quickly and ``startup_bridge`` will surface
    the real error.
    """
    try:
        from urllib.parse import urlparse
        parsed = urlparse(server_url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 9998
        return host, port
    except Exception:
        return "127.0.0.1", 9998


async def _wait_for_bus(
    server_url: str,
    timeout: float,
    poll_interval: float = 0.5,
) -> bool:
    """Poll the WS bus port until reachable, or timeout expires.

    Mirrors `nc -z localhost :9998` from the launchd shell wrapper, brought
    into the daemon so every entry point benefits — not only the launchd
    path. Returns True if the port accepted a TCP connection within the
    timeout, False otherwise. Never raises.

    Phase A.4 invariant: this function MUST run before ``startup_bridge``
    in every daemon entry path. ``bootstrap_daemon`` enforces it.
    """
    if timeout <= 0:
        # Test/edge path: skip the wait entirely. ``startup_bridge`` still
        # runs and degrades gracefully on its own.
        return False

    host, port = _parse_bus_url(server_url)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                logger.info(
                    "bus reachable at %s:%d after %.1fs wait",
                    host, port, timeout - (deadline - time.monotonic()),
                )
                return True
        except OSError:
            pass
        await asyncio.sleep(poll_interval)
    logger.warning(
        "bus not reachable at %s:%d after %.1fs — proceeding with degraded "
        "init (forge_* tools will return 'client not connected')",
        host, port, timeout,
    )
    return False


def _execution_runtime_interval_seconds() -> float:
    """Worker polling cadence for the daemon-owned execution runtime."""
    return float(os.environ.get("FORGE_EXECUTION_RUNTIME_INTERVAL_SECONDS", "1.0"))


async def _run_terminal_consumer(
    session_factory: Any,
    *,
    poll_interval_seconds: float,
    shutdown_event: asyncio.Event,
) -> None:
    """Run the terminal consumer with daemon-owned commit boundaries."""
    from forge_bridge.orchestration.engine import GraphEngine
    from forge_bridge.orchestration.event_consumer import GraphEngineEventConsumer

    async with session_factory() as session:
        consumer = GraphEngineEventConsumer(
            session,
            graph_engine=GraphEngine(session),
        )
        last_event_id = None
        while True:
            try:
                results = await consumer.process_pending(after_event_id=last_event_id)
                if results:
                    last_event_id = results[-1].event_id
                    await session.commit()
            except Exception:
                await session.rollback()
                logger.exception("terminal consumer pass failed")

            if shutdown_event.is_set():
                return
            await asyncio.sleep(poll_interval_seconds)


async def _cancel_task(task: asyncio.Task) -> None:
    task.cancel()
    try:
        await task
    except (asyncio.CancelledError, Exception):
        pass


async def bootstrap_daemon(mcp_server: FastMCP) -> _BootstrapResult:
    """Single source of truth for daemon initialization (Phase A.4).

    Every entry point that runs the MCP server MUST go through this
    function. No entry point may bypass any step. Future required
    initialization MUST land here, not in a per-entry-point shim.

    Steps (one-to-one with the prior ``_lifespan`` 6-step sequence,
    with a new Step 0 that closes the `fbridge up` race):

      0. Wait for the WS bus port to be reachable. Mirrors the launchd
         shell wrapper's `nc -z` gate, now in-process so every entry
         point inherits it (Phase A.4 fix).
      1. ``startup_bridge()`` — connect AsyncClient to state_ws.
      2. Instantiate canonical ExecutionLog + ManifestService.
      3. Launch the registry watcher task.
      4. Construct ConsoleReadAPI with LLMRouter wired in (Bug B fix).
      5. Start the execution runtime workers (Phase 7 V3).
      6. Build the console Starlette app + register MCP resources.
      7. Launch the console uvicorn task on :9996.

    Returns a ``_BootstrapResult`` carrying the singletons + tasks the
    lifespan needs to expose (for tools, the chat handler, telemetry)
    and tear down (in reverse) on exit. The module globals
    (``_canonical_execution_log`` etc.) are also set so existing
    consumers that read them directly continue to work.
    """
    global _server_started, _canonical_execution_log, _canonical_manifest_service, _canonical_watcher_task, _canonical_console_read_api, _canonical_tool_registry

    # Step 0 — bus-readiness gate (Phase A.4 unification).
    bus_url = os.environ.get("FORGE_BRIDGE_URL", "ws://127.0.0.1:9998")
    bus_wait_seconds = float(os.environ.get(
        "FORGE_BRIDGE_BUS_WAIT_SECONDS", str(_DEFAULT_BUS_WAIT_SECONDS),
    ))
    await _wait_for_bus(bus_url, bus_wait_seconds)

    # Step 1 — connect AsyncClient to state_ws (existing behavior).
    await startup_bridge()
    _server_started = True  # D-14: trips the register_tools() guard

    # Step 2 — canonical singletons (API-04 + D-16 gate).
    from forge_bridge.console.read_api import (
        ConsoleReadAPI,
        register_canonical_singletons,
    )

    execution_log, manifest_service = _canonical_runtime_singletons()
    register_canonical_singletons(execution_log, manifest_service)

    # Step 3 — watcher with manifest_service injected (I-02 task handle).
    from forge_bridge.learning.watcher import watch_synthesized_tools
    watcher_task = asyncio.create_task(
        watch_synthesized_tools(mcp_server, manifest_service=manifest_service),
        name="watcher_task",
    )
    _canonical_watcher_task = watcher_task

    # Step 4 — ConsoleReadAPI (sole read layer) with LLMRouter wired (Bug B).
    console_port = int(os.environ.get("FORGE_CONSOLE_PORT", "9996"))
    session_factory = get_async_session_factory()
    from forge_bridge.llm.router import LLMRouter
    llm_router = LLMRouter()
    console_read_api = ConsoleReadAPI(
        execution_log=execution_log,
        manifest_service=manifest_service,
        console_port=console_port,
        session_factory=session_factory,
        llm_router=llm_router,
    )
    _canonical_console_read_api = console_read_api

    # Step 5 — execution runtime (Phase 7 V3).
    # V3 establishes the runtime; it does not expand the federation. Production
    # starts with an empty registry and degrades to dispatch_no_driver until a
    # later adapter rung registers real generation drivers.
    from forge_bridge.orchestration.dispatch_consumer import (
        DispatchOnExecutionEntryConsumer,
    )
    from forge_bridge.orchestration.drivers import GenerationDriverRegistry
    from forge_bridge.orchestration.worker import GenerationPoller

    generation_driver_registry = GenerationDriverRegistry()

    # Issue #26 — the adapter rung Step 5's comment promised. Register sibling
    # declarations into a ToolRegistry wired to THIS driver registry, BEFORE the
    # dispatch consumer starts, so generation siblings' drivers are reachable
    # (dispatch stops degrading to dispatch_no_driver). register_all_siblings
    # isolates per-sibling failures internally; we additionally guard the whole
    # call so a misconfigured sibling can never break daemon bootstrap (same
    # doctrine as the #23 MCP tool-attach hook). On a stock install with no
    # generation sibling installed, the driver registry stays empty by design —
    # this rung wires the path; rung B (install generators) lights the drivers.
    from forge_bridge import __version__ as _bridge_version
    from forge_bridge.orchestration.discovery import (
        make_db_event_appender,
        register_all_siblings,
        resolve_siblings,
    )
    from forge_bridge.orchestration.registration import ToolRegistry

    tool_registry = ToolRegistry(
        generation_driver_registry=generation_driver_registry
    )
    try:
        sibling_outcome = await register_all_siblings(
            resolve_siblings(),
            tool_registry=tool_registry,
            event_appender=make_db_event_appender(session_factory),
            bridge_version=_bridge_version,
        )
        logger.info(
            "sibling capability registration: %d registered, %d failed, "
            "%d empty, %d declaration-only (%d tools)",
            sibling_outcome.siblings_registered,
            sibling_outcome.siblings_failed,
            sibling_outcome.siblings_empty,
            sibling_outcome.siblings_declaration_only,
            len(tool_registry.all()),
        )
        if sibling_outcome.siblings_declaration_only:
            # #61: a generation sibling registered declarations but landed zero
            # drivers — discoverable but not invocable. Almost always a stale
            # dist-info entry-point (sibling source moved without a reinstall).
            logger.warning(
                "%d generation sibling(s) registered declaration-only (0 drivers) "
                "— dispatch will degrade to dispatch_no_driver; reinstall the "
                "sibling and verify dist-info/entry_points.txt (see #61)",
                sibling_outcome.siblings_declaration_only,
            )
    except Exception:  # bootstrap must never die on sibling registration
        logger.exception("sibling capability registration failed; continuing")
    _canonical_tool_registry = tool_registry

    execution_runtime_shutdown = asyncio.Event()
    runtime_interval_seconds = _execution_runtime_interval_seconds()
    dispatch_consumer_task = asyncio.create_task(
        DispatchOnExecutionEntryConsumer(
            session_factory,
            driver_registry=generation_driver_registry,
        ).run_forever(
            poll_interval_seconds=runtime_interval_seconds,
            shutdown_event=execution_runtime_shutdown,
        ),
        name="dispatch_consumer_task",
    )
    generation_poller_task = asyncio.create_task(
        GenerationPoller(
            session_factory,
            generation_driver_registry,
            poll_interval_seconds=runtime_interval_seconds,
        ).run_forever(shutdown_event=execution_runtime_shutdown),
        name="generation_poller_task",
    )
    terminal_consumer_task = asyncio.create_task(
        _run_terminal_consumer(
            session_factory,
            poll_interval_seconds=runtime_interval_seconds,
            shutdown_event=execution_runtime_shutdown,
        ),
        name="terminal_consumer_task",
    )

    # Step 6 — Starlette app + MCP resources/tools registration.
    from forge_bridge.console.app import build_console_app
    from forge_bridge.console.resources import register_console_resources

    app = build_console_app(console_read_api, session_factory=session_factory)
    register_console_resources(
        mcp_server, manifest_service, console_read_api,
        session_factory=session_factory,
    )

    # Step 7 — launch console uvicorn task (may degrade per D-29 / API-06).
    console_task, console_server = await _start_console_task(
        app, "127.0.0.1", console_port,
    )

    return _BootstrapResult(
        execution_log=execution_log,
        manifest_service=manifest_service,
        console_read_api=console_read_api,
        watcher_task=watcher_task,
        generation_driver_registry=generation_driver_registry,
        tool_registry=tool_registry,
        execution_runtime_shutdown=execution_runtime_shutdown,
        dispatch_consumer_task=dispatch_consumer_task,
        generation_poller_task=generation_poller_task,
        terminal_consumer_task=terminal_consumer_task,
        console_task=console_task,
        console_server=console_server,
    )


async def teardown_daemon(result: _BootstrapResult) -> None:
    """Reverse of ``bootstrap_daemon`` — every daemon entry point's
    lifespan exit MUST go through this function.

    Order: console uvicorn → execution runtime → watcher task → bridge
    client. Mirrors construction order in reverse.
    """
    global _server_started, _canonical_execution_log, _canonical_manifest_service, _canonical_watcher_task, _canonical_console_read_api, _canonical_tool_registry

    if result.console_task is not None and result.console_server is not None:
        result.console_server.should_exit = True
        try:
            await asyncio.wait_for(result.console_task, timeout=5.0)
        except asyncio.TimeoutError:
            result.console_task.cancel()
            try:
                await result.console_task
            except (asyncio.CancelledError, Exception):
                pass
        except (asyncio.CancelledError, Exception):
            pass

    result.execution_runtime_shutdown.set()
    await _cancel_task(result.terminal_consumer_task)
    await _cancel_task(result.generation_poller_task)
    await _cancel_task(result.dispatch_consumer_task)
    await _cancel_task(result.watcher_task)

    await shutdown_bridge()
    _server_started = False
    _canonical_execution_log = None
    _canonical_manifest_service = None
    _canonical_watcher_task = None
    _canonical_console_read_api = None
    _canonical_tool_registry = None


# ─────────────────────────────────────────────────────────────
# Server lifespan — thin wrapper over bootstrap_daemon / teardown_daemon
# ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def _lifespan(mcp_server: FastMCP):
    """FastMCP lifespan — delegates to ``bootstrap_daemon`` (Phase A.4).

    All initialization logic lives in ``bootstrap_daemon``; this wrapper
    exists only to bridge the FastMCP lifespan ContextManager protocol
    to the daemon's bootstrap / teardown functions. Future init lands
    in ``bootstrap_daemon``, not here.
    """
    result = await bootstrap_daemon(mcp_server)
    try:
        yield
    finally:
        await teardown_daemon(result)


# ─────────────────────────────────────────────────────────────
# MCP server definition
# ─────────────────────────────────────────────────────────────

mcp = FastMCP(
    "forge_bridge",
    instructions=(
        "Forge Bridge — pipeline state for Autodesk Flame VFX projects. "
        "Use forge_* tools to query and modify shots, sequences, versions, "
        "and media. Use flame_* tools for direct Flame API operations."
    ),
    lifespan=_lifespan,
)

# All tool registrations go through the registry
register_builtins(mcp)

# Federation tool-attach hook (issue #23): attach sibling operator callables as
# forge_* MCP tools. MUST run here at module-load — before _lifespan trips the
# register_tools() D-14 guard (_server_started). Per-sibling errors are isolated.
from forge_bridge.orchestration.discovery import (  # noqa: E402
    attached_sibling_tool_names,
    register_sibling_mcp_tools,
)

_sibling_tool_status = register_sibling_mcp_tools(mcp)
if _sibling_tool_status:
    logger.info("sibling MCP tool-attach: %s", _sibling_tool_status)

# Issue #67: tell the chat/exec reachability filter which sibling-attached ops
# run in-process, so they survive narrowing when Flame (:9999) is down (they
# need no Flame backend). Self-maintaining — names captured at the attach
# boundary above, not a hand-kept allowlist.
from forge_bridge.console._tool_filter import (  # noqa: E402
    register_sibling_in_process_tools,
)

register_sibling_in_process_tools(attached_sibling_tool_names())


# ─────────────────────────────────────────────────────────────
# Startup / shutdown
# ─────────────────────────────────────────────────────────────

async def startup_bridge(
    server_url: str | None = None,
    client_name: str | None = None,
) -> None:
    """Connect to forge-bridge server before serving MCP requests.

    Args:
        server_url: WebSocket URL of the forge-bridge server.
                    Defaults to $FORGE_BRIDGE_URL or ws://127.0.0.1:9998.
        client_name: Identifier for this MCP client.
                     Defaults to $FORGE_MCP_CLIENT_NAME or mcp_claude.
    """
    global _client

    server_url = server_url or os.environ.get("FORGE_BRIDGE_URL", "ws://127.0.0.1:9998")
    client_name = client_name or os.environ.get("FORGE_MCP_CLIENT_NAME", "mcp_claude")

    if _client is not None and getattr(_client, "is_connected", False):
        logger.info("Reusing existing forge-bridge client at %s", _client.server_url)
        return
    if _client is not None:
        try:
            await _client.stop()
        except Exception:
            pass
        _client = None

    _client = AsyncClient(
        client_name=client_name,
        server_url=server_url,
        endpoint_type="mcp",
        auto_reconnect=True,
    )

    try:
        await _client.start()
        await _client.wait_until_connected(timeout=10.0)
        logger.info(f"Connected to forge-bridge at {server_url}")
    except Exception as e:
        logger.warning(
            f"Could not connect to forge-bridge at {server_url}: {e}\n"
            "forge_* tools will fail. flame_* tools still work if Flame is running."
        )
        # Best-effort cleanup — AsyncClient.stop() is idempotent on a
        # partially-started client. Swallow cleanup errors so the warning
        # above remains the only user-visible signal.
        try:
            await _client.stop()
        except Exception:
            pass
        _client = None


async def shutdown_bridge() -> None:
    """Disconnect from forge-bridge server and clean up."""
    global _client
    if _client:
        await _client.stop()
        _client = None


# ─────────────────────────────────────────────────────────────
# Console uvicorn task launcher (API-06 / D-29 graceful degradation)
# ─────────────────────────────────────────────────────────────

async def _start_console_task(
    app,
    host: str,
    port: int,
    ready_timeout: float = 5.0,
):
    """Launch the console uvicorn server as an asyncio task.

    Returns (task, server) on successful bind; (None, None) on port
    unavailable (API-06 / D-29). Mirrors startup_bridge's degradation
    pattern: try, on Exception log WARNING, null out the resource, continue.
    """
    import socket

    import uvicorn

    from forge_bridge.console.logging_config import STDERR_ONLY_LOGGING_CONFIG

    # Port precheck — cleaner than letting Server.serve() raise an unhandled
    # OSError inside the task.
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        probe.bind((host, port))
    except OSError as e:
        logger.warning(
            "Console API disabled — port %s:%d unavailable: %s. "
            "MCP server continues without :%d.", host, port, e, port,
        )
        try:
            probe.close()
        except Exception:
            pass
        return None, None
    finally:
        try:
            probe.close()
        except Exception:
            pass

    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_config=STDERR_ONLY_LOGGING_CONFIG,  # D-20
        access_log=False,                       # D-21
        lifespan="off",                         # Starlette app has no lifespan of its own
    )
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve(), name="console_uvicorn_task")

    # Lightweight startup barrier — Server.started flips to True in startup()
    deadline = asyncio.get_running_loop().time() + ready_timeout
    while not server.started and asyncio.get_running_loop().time() < deadline:
        if task.done():  # serve() exited early — bind failed after precheck raced
            return None, None
        await asyncio.sleep(0.02)
    if not server.started:
        logger.warning(
            "Console uvicorn did not signal started within %.1fs", ready_timeout,
        )
    return task, server


def main(transport: str = "stdio", port: int = 9997) -> None:
    """Entry point: python -m forge_bridge.mcp

    Args:
        transport: FastMCP transport mode — ``stdio`` (default, preserves Claude Desktop
            compatibility), ``sse``, or ``streamable-http`` (long-running uvicorn server
            suitable for daemon mode; does not exit on stdin EOF).
        port: Port for FastMCP to bind under ``sse`` / ``streamable-http`` transports.
            Default 9997. Ignored under ``stdio``. Override via ``FORGE_MCP_PORT`` env var
            or ``--port`` CLI flag on the ``mcp http`` subcommand (resolved before this
            function is called).
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    )
    if transport == "stdio":
        # FastMCP's stdio loop runs `_mcp_server.run()` which honors the user-registered
        # lifespan via lifespan_context — Console + chat co-host on :9996 starts up
        # alongside each Claude Desktop session. Existing behavior; unchanged.
        mcp.run(transport=transport)
        return

    # sse / streamable-http: FastMCP's *_app() builders hardcode the Starlette
    # `lifespan=lambda app: self.session_manager.run()` and do NOT chain the
    # user-registered lifespan into the ASGI app's lifecycle. Without this wiring,
    # `_lifespan` (which co-hosts the Console + chat on :9996) never runs at server
    # start — it only runs per-MCP-request and is torn down between requests, so
    # `:9996` is never persistently bound under daemon mode (Phase 20.1 walk gap).
    # We compose the two lifespans here so both run for the full server lifetime.
    import contextlib
    import uvicorn

    mcp.settings.port = port
    if transport == "streamable-http":
        starlette_app = mcp.streamable_http_app()
    else:
        starlette_app = mcp.sse_app()

    fastmcp_lifespan = starlette_app.router.lifespan_context

    @contextlib.asynccontextmanager
    async def _composed_lifespan(app):
        # User lifespan first (startup_bridge → ManifestService → watcher → Console
        # uvicorn on :9996). Then FastMCP's session_manager. Teardown reverses.
        async with _lifespan(mcp), fastmcp_lifespan(app):
            yield

    starlette_app.router.lifespan_context = _composed_lifespan

    config = uvicorn.Config(
        starlette_app,
        host=mcp.settings.host,
        port=mcp.settings.port,
        log_level=mcp.settings.log_level.lower(),
    )
    asyncio.run(uvicorn.Server(config).serve())
