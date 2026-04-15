"""forge_bridge.mcp — MCP server with pluggable tool registry."""

from forge_bridge.mcp.registry import register_tools
from forge_bridge.mcp.server import mcp as _mcp


def get_mcp():
    """Return the FastMCP server instance for tool registration."""
    return _mcp


__all__ = ["register_tools", "get_mcp"]
