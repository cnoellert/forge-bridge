"""forge_bridge.mcp — MCP server with pluggable tool registry."""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from forge_bridge.mcp.registry import invoke_tool, register_tools
from forge_bridge.mcp.server import mcp as _mcp


def get_mcp() -> FastMCP:
    """Return the FastMCP server instance for tool registration."""
    return _mcp


__all__ = ["register_tools", "get_mcp", "invoke_tool"]
