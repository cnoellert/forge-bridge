"""
FORGE MCP Server — rewired for forge-bridge architecture.

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

from mcp.server.fastmcp import FastMCP

from forge_bridge.client import AsyncClient
from forge_bridge.mcp import tools

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
# MCP server definition
# ─────────────────────────────────────────────────────────────

mcp = FastMCP(
    "forge_bridge",
    instructions=(
        "Forge Bridge — pipeline state for Autodesk Flame VFX projects. "
        "Use forge_* tools to query and modify shots, sequences, versions, "
        "and media. Use flame_* tools for direct Flame API operations."
    ),
)

# ── forge-bridge tools (pipeline state) ──────────────────────

mcp.tool(
    name="forge_ping",
    annotations={
        "title": "Check forge-bridge connection",
        "readOnlyHint": True,
        "idempotentHint": True,
    },
)(tools.ping)

mcp.tool(
    name="forge_list_projects",
    annotations={
        "title": "List all pipeline projects",
        "readOnlyHint": True,
        "idempotentHint": True,
    },
)(tools.list_projects)

mcp.tool(
    name="forge_get_project",
    annotations={
        "title": "Get project details",
        "readOnlyHint": True,
        "idempotentHint": True,
    },
)(tools.get_project)

mcp.tool(
    name="forge_create_project",
    annotations={
        "title": "Create a new project",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
    },
)(tools.create_project)

mcp.tool(
    name="forge_list_shots",
    annotations={
        "title": "List shots in a project",
        "readOnlyHint": True,
        "idempotentHint": True,
    },
)(tools.list_shots)

mcp.tool(
    name="forge_get_shot",
    annotations={
        "title": "Get shot details with stack",
        "readOnlyHint": True,
        "idempotentHint": True,
    },
)(tools.get_shot)

mcp.tool(
    name="forge_create_shot",
    annotations={
        "title": "Create a shot with stack and layers",
        "readOnlyHint": False,
        "idempotentHint": False,
    },
)(tools.create_shot)

mcp.tool(
    name="forge_update_shot_status",
    annotations={
        "title": "Update shot status",
        "readOnlyHint": False,
        "idempotentHint": True,
    },
)(tools.update_shot_status)

mcp.tool(
    name="forge_list_versions",
    annotations={
        "title": "List versions for a shot",
        "readOnlyHint": True,
        "idempotentHint": True,
    },
)(tools.list_versions)

mcp.tool(
    name="forge_get_shot_stack",
    annotations={
        "title": "Get all layers in a shot's stack",
        "readOnlyHint": True,
        "idempotentHint": True,
    },
)(tools.get_shot_stack)

mcp.tool(
    name="forge_get_dependents",
    annotations={
        "title": "Get entities that depend on this one",
        "readOnlyHint": True,
        "idempotentHint": True,
    },
)(tools.get_dependents)

mcp.tool(
    name="forge_list_roles",
    annotations={
        "title": "List all registered roles",
        "readOnlyHint": True,
        "idempotentHint": True,
    },
)(tools.list_roles)

mcp.tool(
    name="forge_get_events",
    annotations={
        "title": "Get recent pipeline events",
        "readOnlyHint": True,
        "idempotentHint": True,
    },
)(tools.get_events)

# ── Flame HTTP bridge tools (kept, unchanged) ─────────────────
# These are imported from the original tools module and registered
# under flame_* names. They talk to Flame directly via HTTP.

try:
    from forge_bridge.tools import project as flame_project
    from forge_bridge.tools import timeline as flame_timeline
    from forge_bridge.tools import batch as flame_batch
    from forge_bridge.tools import utility as flame_utility
    from forge_bridge.tools import publish as flame_publish

    mcp.tool(name="flame_ping",        annotations={"readOnlyHint": True})(flame_utility.ping)
    mcp.tool(name="flame_get_project", annotations={"readOnlyHint": True})(flame_project.get_project)
    mcp.tool(name="flame_list_libraries", annotations={"readOnlyHint": True})(flame_project.list_libraries)
    mcp.tool(name="flame_list_desktop",   annotations={"readOnlyHint": True})(flame_project.list_desktop)
    mcp.tool(name="flame_find_media",     annotations={"readOnlyHint": True})(flame_project.find_media)

    mcp.tool(name="flame_get_sequence_segments",
             annotations={"title": "Get all segments with FORGE metadata", "readOnlyHint": True}
             )(flame_timeline.get_sequence_segments)

    mcp.tool(name="flame_preview_rename",
             annotations={"title": "Preview rename without changes", "readOnlyHint": True, "idempotentHint": True}
             )(flame_timeline.preview_rename)

    mcp.tool(name="flame_rename_shots",
             annotations={"title": "Rename shots and segments on a sequence", "readOnlyHint": False}
             )(flame_timeline.rename_shots)

    mcp.tool(name="flame_preview_start_frames",
             annotations={"title": "Preview start frame assignments", "readOnlyHint": True, "idempotentHint": True}
             )(flame_timeline.preview_start_frames)

    mcp.tool(name="flame_set_start_frames",
             annotations={"title": "Set composite start frames on a sequence", "readOnlyHint": False}
             )(flame_timeline.set_start_frames)

    mcp.tool(name="flame_set_segment_attribute",
             annotations={"title": "Set an attribute on a single segment", "readOnlyHint": False}
             )(flame_timeline.set_segment_attribute)

except ImportError:
    logger.warning("Flame HTTP bridge tools not available — forge_bridge.tools not found")

# ── Publish workflow tools (forge-bridge state, no Flame dependency) ──

mcp.tool(
    name="forge_check_shots",
    annotations={"title": "Pre-publish preflight — check if shots exist", "readOnlyHint": True, "idempotentHint": True},
)(tools.check_shots)

mcp.tool(
    name="forge_register_publish",
    annotations={"title": "Register a published component in forge-bridge", "readOnlyHint": False},
)(tools.register_publish)

mcp.tool(
    name="flame_snapshot_timeline",
    annotations={"title": "Snapshot Flame timeline — all sequences and segments", "readOnlyHint": True, "idempotentHint": True},
)(tools.snapshot_timeline)

mcp.tool(
    name="forge_list_published_plates",
    annotations={"title": "List published video plates from the forge-bridge registry", "readOnlyHint": True, "idempotentHint": True},
)(tools.list_published_plates)

mcp.tool(
    name="forge_get_shot_versions",
    annotations={"title": "Get all published plate versions for a specific shot", "readOnlyHint": True, "idempotentHint": True},
)(tools.get_shot_versions)


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
