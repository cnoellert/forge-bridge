"""Console package -- Artist Console read layer (v1.3).

Provides:
  - ManifestService + ToolRecord -- in-memory synthesis manifest.
  - ConsoleReadAPI -- sole read layer for Web UI / CLI / MCP resources / chat.
  - register_console_resources -- FastMCP resource + tool-shim registrar
    consumed by forge_bridge.mcp.server._lifespan (and MFST-06 consumers
    like projekt-forge).
"""
from forge_bridge.console.manifest_service import ManifestService, ToolRecord
from forge_bridge.console.read_api import ConsoleReadAPI
from forge_bridge.console.resources import register_console_resources

__all__ = [
    "ManifestService",
    "ToolRecord",
    "ConsoleReadAPI",
    "register_console_resources",
]
