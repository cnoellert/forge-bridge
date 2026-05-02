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
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

from forge_bridge.client import AsyncClient
from forge_bridge.mcp.registry import register_builtins
from forge_bridge.store.session import get_async_session_factory

if TYPE_CHECKING:
    from forge_bridge.console.manifest_service import ManifestService
    from forge_bridge.learning.execution_log import ExecutionLog
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


def get_client() -> AsyncClient:
    """Return the shared AsyncClient. Raises if not yet connected."""
    if _client is None:
        raise RuntimeError(
            "forge-bridge client not connected. "
            "Is the MCP server started via main()?"
        )
    return _client


# ─────────────────────────────────────────────────────────────
# Server lifespan — D-31 6-step sequence
# ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def _lifespan(mcp_server: FastMCP):
    """Server lifespan (D-31 6-step sequence):
      1. startup_bridge()
      2. instantiate ManifestService + canonical ExecutionLog
      3. launch watcher_task with manifest_service injected
      4. build ConsoleReadAPI(execution_log=..., manifest_service=...)
      5. build console Starlette app + register_console_resources(...)
      6. launch console_task (uvicorn Server.serve())

    Teardown reverses: cancel console_task, cancel watcher_task, shutdown_bridge.
    """
    global _server_started, _canonical_execution_log, _canonical_manifest_service, _canonical_watcher_task, _canonical_console_read_api

    # Step 1 — existing behavior
    await startup_bridge()
    _server_started = True  # D-14: trips the register_tools() guard

    # Step 2 — canonical singletons (API-04 + D-16 gate)
    from forge_bridge.console.manifest_service import ManifestService
    from forge_bridge.console.read_api import (
        ConsoleReadAPI,
        register_canonical_singletons,
    )
    from forge_bridge.learning.execution_log import ExecutionLog

    execution_log = ExecutionLog()
    manifest_service = ManifestService()
    _canonical_execution_log = execution_log
    _canonical_manifest_service = manifest_service
    # Record ids before the watcher task exists — I-02 task handle is installed
    # directly on the module global in Step 3.
    register_canonical_singletons(execution_log, manifest_service)

    # Step 3 — watcher with manifest_service injected
    # (I-02: also register the task handle so /api/v1/health can detect a
    # crashed watcher instead of falling back to the coarse _server_started
    # boolean.)
    from forge_bridge.learning.watcher import watch_synthesized_tools
    watcher_task = asyncio.create_task(
        watch_synthesized_tools(mcp_server, manifest_service=manifest_service),
        name="watcher_task",
    )
    _canonical_watcher_task = watcher_task

    # Step 4 — ConsoleReadAPI (sole read layer)
    console_port = int(os.environ.get("FORGE_CONSOLE_PORT", "9996"))
    # Step 4 (NEW per FB-B D-05) — Build canonical async session_factory singleton.
    # Idempotent and lazy at the connection level; missing DB at startup does NOT
    # crash _lifespan (matches the existing console-task graceful-degradation pattern
    # at mcp/server.py:252-313). Connection errors surface only on first repo use.
    session_factory = get_async_session_factory()
    # FB-D / Phase 16 — LLMRouter wired into ConsoleReadAPI so chat_handler
    # (handlers.py) can reach it via app.state.console_read_api._llm_router (D-16).
    # Construction is pure env-reading; clients are lazy on first use.
    from forge_bridge.llm.router import LLMRouter
    llm_router = LLMRouter()
    console_read_api = ConsoleReadAPI(
        execution_log=execution_log,
        manifest_service=manifest_service,
        console_port=console_port,
        session_factory=session_factory,   # NEW (D-05)
        llm_router=llm_router,             # NEW (FB-D / CHAT-01..05)
    )
    # Phase 16.1 (D-07 #1): publish ConsoleReadAPI as a module global so
    # tests/console/test_lifespan_wiring.py can verify _llm_router wiring.
    _canonical_console_read_api = console_read_api

    # Step 5 — Starlette app + MCP resources/tools registration
    from forge_bridge.console.app import build_console_app
    from forge_bridge.console.resources import register_console_resources

    app = build_console_app(console_read_api, session_factory=session_factory)   # NEW (D-05)
    register_console_resources(
        mcp_server, manifest_service, console_read_api,
        session_factory=session_factory,   # NEW (D-05)
    )

    # Step 6 — launch console uvicorn task (may degrade per D-29)
    console_task, console_server = await _start_console_task(
        app, "127.0.0.1", console_port,
    )

    try:
        yield
    finally:
        # Teardown — reverse of setup
        if console_task is not None and console_server is not None:
            console_server.should_exit = True
            try:
                await asyncio.wait_for(console_task, timeout=5.0)
            except asyncio.TimeoutError:
                console_task.cancel()
                try:
                    await console_task
                except (asyncio.CancelledError, Exception):
                    pass
            except (asyncio.CancelledError, Exception):
                pass

        watcher_task.cancel()
        try:
            await watcher_task
        except asyncio.CancelledError:
            pass

        await shutdown_bridge()
        _server_started = False  # reset for clean teardown / test isolation
        _canonical_execution_log = None
        _canonical_manifest_service = None
        _canonical_watcher_task = None  # I-02: clear on teardown
        _canonical_console_read_api = None  # Phase 16.1 D-07 #1: clear on teardown


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
            or ``--mcp-port`` CLI flag (resolved before this function is called).
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    )
    # Under sse / streamable-http, bind FastMCP to the requested port.
    # Under stdio the port is ignored; guard avoids mutating settings unnecessarily.
    if transport != "stdio":
        mcp.settings.port = port
    # FastMCP handles the asyncio lifecycle — hook in via lifespan
    mcp.run(transport=transport)
