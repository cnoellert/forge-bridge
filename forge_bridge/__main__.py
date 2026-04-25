"""forge-bridge entry point — Typer root for MCP server + Artist Console CLI.

Bare `forge-bridge` (no args) boots the MCP server on stdio — unchanged behavior
for existing Claude Desktop and Claude Code configurations.

`forge-bridge console <subcommand>` runs CLI subcommands that talk to the Artist
Console HTTP API on :9996. Subcommands are registered in Phase 11; this file only
lays the entry-point scaffold (D-10/D-11).
"""
from __future__ import annotations

import os
from typing import Optional

import typer

app = typer.Typer(
    name="forge-bridge",
    help="forge-bridge — MCP server + Artist Console.",
    no_args_is_help=False,  # bare invocation must boot MCP, not print help (D-10)
)

# Empty subcommand group for Phase 11 to fill
console_app = typer.Typer(
    name="console",
    help="Artist Console CLI (subcommands arrive in Phase 11).",
    no_args_is_help=True,  # `forge-bridge console` alone prints help
)
app.add_typer(console_app, name="console")

# Phase 11: register console subcommands.
# Imports are deferred from module top to here to keep `forge-bridge` (bare invocation)
# boot-fast — MCP server import path doesn't need cli.* modules.
from forge_bridge.cli import doctor, execs, health, manifest, tools  # noqa: E402

console_app.command("tools")(tools.tools_cmd)
console_app.command("execs")(execs.execs_cmd)
console_app.command("manifest")(manifest.manifest_cmd)
console_app.command("health")(health.health_cmd)
console_app.command("doctor")(doctor.doctor_cmd)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    console_port: Optional[int] = typer.Option(
        None,
        "--console-port",
        help="Override console HTTP API port (default 9996, or $FORGE_CONSOLE_PORT).",
        envvar=None,  # manual env lookup below for D-27 precedence clarity
    ),
) -> None:
    """Bare `forge-bridge` boots the MCP server. `forge-bridge console <cmd>` runs CLI."""
    if ctx.invoked_subcommand is not None:
        return  # subcommand will run; callback returns early

    # D-27 precedence: flag > env > default
    # If flag passed, override env. Otherwise leave env alone so existing
    # FORGE_CONSOLE_PORT (if any) wins; otherwise Plan 09-03 defaults to 9996.
    if console_port is not None:
        os.environ["FORGE_CONSOLE_PORT"] = str(console_port)

    # Lazy import — defer heavy server imports until AFTER Typer confirmed bare invocation.
    # This keeps `forge-bridge console --help` fast (no MCP/asyncio import for help).
    from forge_bridge.mcp.server import main as mcp_main
    mcp_main()


if __name__ == "__main__":
    app()
