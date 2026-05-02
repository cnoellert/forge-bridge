"""forge-bridge entry point.

Delegates to the unified Typer front door at ``forge_bridge.cli.main.app``.
Bare ``python -m forge_bridge`` (no args) prints help and exits 0; the MCP
server only starts via ``mcp stdio`` or ``mcp http`` subcommands.
"""
from __future__ import annotations

from forge_bridge.cli.main import app

if __name__ == "__main__":
    app()
