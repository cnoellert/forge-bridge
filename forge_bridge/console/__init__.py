"""Console package -- Artist Console read layer (v1.3).

Provides:
  - ManifestService + ToolRecord -- in-memory synthesis manifest.
  - (Task 3 of this plan will add ConsoleReadAPI.)
  - (Plan 09-03 will add: app, handlers, resources, logging_config,
    register_console_resources.)
"""
from forge_bridge.console.manifest_service import ManifestService, ToolRecord

__all__ = [
    "ManifestService",
    "ToolRecord",
]
