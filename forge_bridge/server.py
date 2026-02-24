"""
FORGE MCP Server — Model Context Protocol interface to Autodesk Flame.

Connects to Flame via FORGE Bridge (HTTP) and exposes the Flame Python
API as structured MCP tools for LLM agents.

Usage:
    # Local (stdio, bridge on same machine)
    python -m forge_mcp

    # Remote (bridge on another machine)
    python -m forge_mcp --bridge-host 192.168.1.100

    # HTTP transport for multi-client
    python -m forge_mcp --http --port 8080

    # All options
    python -m forge_mcp --bridge-host 10.0.0.5 --bridge-port 9999 --bridge-timeout 60

Config priority: CLI args > environment variables > defaults
    FORGE_BRIDGE_HOST    (default: 127.0.0.1)
    FORGE_BRIDGE_PORT    (default: 9999)
    FORGE_BRIDGE_TIMEOUT (default: 30)
"""

import sys

from mcp.server.fastmcp import FastMCP

from forge_mcp.tools import project, timeline, batch, utility, publish

# ── Server ──────────────────────────────────────────────────────────────

mcp = FastMCP("forge_mcp")

# ── Project & Workspace Tools ───────────────────────────────────────────

mcp.tool(
    name="flame_ping",
    annotations={
        "title": "Check Flame Connection",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)(utility.ping)

mcp.tool(
    name="flame_get_project",
    annotations={
        "title": "Get Project Info",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)(project.get_project)

mcp.tool(
    name="flame_list_libraries",
    annotations={
        "title": "List Libraries",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)(project.list_libraries)

mcp.tool(
    name="flame_list_desktop",
    annotations={
        "title": "List Desktop Contents",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)(project.list_desktop)

mcp.tool(
    name="flame_find_media",
    annotations={
        "title": "Find Media by Name",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)(project.find_media)

# ── Timeline Tools ──────────────────────────────────────────────────────

mcp.tool(
    name="flame_get_sequence_info",
    annotations={
        "title": "Get Sequence Details",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)(timeline.get_sequence_info)

mcp.tool(
    name="flame_set_segment_attribute",
    annotations={
        "title": "Set Segment Attribute",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)(timeline.set_segment_attribute)

mcp.tool(
    name="flame_bulk_rename_segments",
    annotations={
        "title": "Bulk Rename Segments",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)(timeline.bulk_rename_segments)

# ── Batch Tools ─────────────────────────────────────────────────────────

mcp.tool(
    name="flame_list_batch_nodes",
    annotations={
        "title": "List Batch Nodes",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)(batch.list_batch_nodes)

mcp.tool(
    name="flame_get_node_attributes",
    annotations={
        "title": "Get Node Attributes",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)(batch.get_node_attributes)

mcp.tool(
    name="flame_create_node",
    annotations={
        "title": "Create Batch Node",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)(batch.create_node)

mcp.tool(
    name="flame_connect_nodes",
    annotations={
        "title": "Connect Batch Nodes",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)(batch.connect_nodes)

mcp.tool(
    name="flame_set_node_attribute",
    annotations={
        "title": "Set Node Attribute",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)(batch.set_node_attribute)

mcp.tool(
    name="flame_render_batch",
    annotations={
        "title": "Render Batch",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)(batch.render_batch)

mcp.tool(
    name="flame_batch_setup",
    annotations={
        "title": "Save/Load Batch Setup",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)(batch.batch_setup)

mcp.tool(
    name="flame_get_write_file_path",
    annotations={
        "title": "Get Write File Output Path",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)(batch.get_write_file_path)

# ── Utility Tools ───────────────────────────────────────────────────────

mcp.tool(
    name="flame_execute_python",
    annotations={
        "title": "Execute Raw Python in Flame",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)(utility.execute_python)

mcp.tool(
    name="flame_execute_shortcut",
    annotations={
        "title": "Trigger Keyboard Shortcut",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)(utility.execute_shortcut)

# ── Publish Workflow Tools ──────────────────────────────────────────────

mcp.tool(
    name="flame_rename_shots",
    annotations={
        "title": "Assign Shot Names to Sequence",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)(publish.rename_shots)

mcp.tool(
    name="flame_rename_segments",
    annotations={
        "title": "Rename Segments with Template",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)(publish.rename_segments)

mcp.tool(
    name="flame_publish_sequence",
    annotations={
        "title": "Publish Sequence via Export Preset",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)(publish.publish_sequence)


# ── Entry Point ─────────────────────────────────────────────────────────

def main():
    """Run the MCP server."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="forge_mcp",
        description="FORGE MCP Server — Flame automation via Model Context Protocol",
    )
    parser.add_argument(
        "--bridge-host",
        default=None,
        help="FORGE Bridge hostname/IP (default: 127.0.0.1, or FORGE_BRIDGE_HOST env)",
    )
    parser.add_argument(
        "--bridge-port",
        type=int,
        default=None,
        help="FORGE Bridge port (default: 9999, or FORGE_BRIDGE_PORT env)",
    )
    parser.add_argument(
        "--bridge-timeout",
        type=int,
        default=None,
        help="Bridge request timeout in seconds (default: 30, or FORGE_BRIDGE_TIMEOUT env)",
    )
    parser.add_argument(
        "--http",
        action="store_true",
        help="Use streamable HTTP transport instead of stdio",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="HTTP transport port (default: 8080, only with --http)",
    )

    args = parser.parse_args()

    # Apply bridge overrides before any tool use
    from forge_mcp.bridge import configure
    configure(host=args.bridge_host, port=args.bridge_port, timeout=args.bridge_timeout)

    if args.http:
        from forge_mcp.bridge import BRIDGE_URL
        print(f"Starting FORGE MCP server (HTTP:{args.port}) → {BRIDGE_URL}", file=sys.stderr)
        mcp.run(transport="streamable_http", port=args.port)
    else:
        mcp.run()  # stdio transport


if __name__ == "__main__":
    main()
