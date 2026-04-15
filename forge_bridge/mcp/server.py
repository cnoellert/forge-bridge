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
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

from forge_bridge.client import AsyncClient
from forge_bridge.mcp.registry import register_builtins

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Shared client — tools call get_client()
# ─────────────────────────────────────────────────────────────

_client: AsyncClient | None = None


def get_client() -> AsyncClient:
    """Return the shared AsyncClient. Raises if not yet connected."""
    if _client is None:
        raise RuntimeError(
            "forge-bridge client not connected. "
            "Is the MCP server started via main()?"
        )
    return _client


# ─────────────────────────────────────────────────────────────
# Server lifespan — connect client, start watcher, clean up on exit
# ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def _lifespan(mcp_server: FastMCP):
    """Server lifespan: connect client, start watcher, clean up on exit."""
    # Connect to forge-bridge
    await _startup()

    # Launch synthesized tool watcher as background task
    from forge_bridge.learning.watcher import watch_synthesized_tools
    watcher_task = asyncio.create_task(watch_synthesized_tools(mcp_server))

    try:
        yield
    finally:
        watcher_task.cancel()
        try:
            await watcher_task
        except asyncio.CancelledError:
            pass
        await _shutdown()


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

async def _startup() -> None:
    """Connect to forge-bridge server before serving MCP requests."""
    global _client

    server_url  = os.environ.get("FORGE_BRIDGE_URL", "ws://127.0.0.1:9998")
    client_name = os.environ.get("FORGE_MCP_CLIENT_NAME", "mcp_claude")

    _client = AsyncClient(
        client_name=client_name,
        server_url=server_url,
        endpoint_type="mcp",
        auto_reconnect=True,
    )

    await _client.start()

    try:
        await _client.wait_until_connected(timeout=10.0)
        logger.info(f"Connected to forge-bridge at {server_url}")
    except Exception as e:
        logger.warning(
            f"Could not connect to forge-bridge at {server_url}: {e}\n"
            "forge_* tools will fail. flame_* tools still work if Flame is running."
        )


async def _shutdown() -> None:
    global _client
    if _client:
        await _client.stop()
        _client = None


def main() -> None:
    """Entry point: python -m forge_bridge.mcp"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    )
    # FastMCP handles the asyncio lifecycle — hook in via lifespan
    mcp.run()
