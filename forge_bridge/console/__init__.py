"""Console package -- Artist Console read layer (v1.3).

Provides:
  - ManifestService + ToolRecord -- in-memory synthesis manifest.
  - ConsoleReadAPI -- sole read layer for Web UI / CLI / MCP resources / chat.
  - (Plan 09-03 will add: app, handlers, resources, logging_config,
    register_console_resources.)
"""
from forge_bridge.console.manifest_service import ManifestService, ToolRecord
from forge_bridge.console.read_api import ConsoleReadAPI

__all__ = [
    "ManifestService",
    "ToolRecord",
    "ConsoleReadAPI",
]
