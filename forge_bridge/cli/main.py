"""forge-bridge unified CLI front door.

Single Typer root for human-facing commands. Bare invocation prints help
and exits 0 — MCP only starts via the explicit ``mcp stdio`` / ``mcp http``
subcommands. Existing legacy console subcommands remain reachable under
``forge-bridge console <cmd>``; ``doctor`` and ``actions`` are top-level
aliases for the most common console operations.

Imports of heavy modules (mcp.server, httpx) are lazy so ``--help`` is fast.
"""
from __future__ import annotations

import json
import sys
from typing import Annotated

import typer

from forge_bridge import config
from forge_bridge.cli import chat as _chat
from forge_bridge.cli import doctor as _doctor
from forge_bridge.cli import execs as _execs
from forge_bridge.cli import health as _health
from forge_bridge.cli import manifest as _manifest
from forge_bridge.cli import runtime_doctor as _runtime_doctor
from forge_bridge.cli import tools as _tools

app = typer.Typer(
    name="forge-bridge",
    help="forge-bridge — unified CLI for MCP server, Flame, and Artist Console.",
    no_args_is_help=False,  # bare invocation prints help + exits 0 (handled in callback)
)


@app.callback(invoke_without_command=True)
def _root(ctx: typer.Context) -> None:
    """Bare ``forge-bridge`` prints help and exits 0; MCP only starts via subcommands."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(code=0)

# ── console group: legacy aliases preserved verbatim ──────────────────────
console_app = typer.Typer(
    name="console",
    help="Artist Console subcommands (legacy aliases preserved).",
    no_args_is_help=True,
)
console_app.command("tools")(_tools.tools_cmd)
console_app.command("execs")(_execs.execs_cmd)
console_app.command("manifest")(_manifest.manifest_cmd)
console_app.command("health")(_health.health_cmd)
console_app.command("doctor")(_doctor.doctor_cmd)
app.add_typer(console_app, name="console")

# ── top-level commands ────────────────────────────────────────────────────
# `doctor` is the runtime topology probe (PR2). The legacy in-depth check
# remains reachable as `console doctor`.
app.command(
    "doctor",
    help="Probe forge-bridge surfaces (Console, MCP, Flame, State WS) "
         "and report status, URLs, and next steps.",
)(_runtime_doctor.runtime_doctor_cmd)
app.command("actions", help="List registered tools (alias of `console tools`).")(
    _tools.tools_cmd
)
app.command(
    "chat",
    help="Send a message through the shared `/api/v1/chat` endpoint with "
         "timeout, retry, and timing feedback.",
)(_chat.chat_cmd)


# ── runtime manager: forge up / down / status ────────────────────────────
@app.command("up", help="Start managed forge-bridge services (mcp_http + state_ws).")
def up_cmd(
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON envelope to stdout."),
    ] = False,
) -> None:
    from forge_bridge.runtime import manager

    results = [manager.start_mcp_http(), manager.start_state_ws()]
    if as_json:
        sys.stdout.write(json.dumps({"data": results}) + "\n")
        return
    for r in results:
        name = r["name"]
        host = r.get("host", "")
        port = r.get("port", "")
        addr = f"{host}:{port}"
        if r.get("started"):
            state_label = "ready" if r.get("ready") else "starting"
            sys.stdout.write(
                f"{name:<10} {state_label:<10} managed (pid {r.get('pid')})  {addr}\n"
            )
        elif r.get("managed"):
            sys.stdout.write(
                f"{name:<10} {'already up':<10} managed (pid {r.get('pid')})  {addr}\n"
            )
        else:
            sys.stdout.write(
                f"{name:<10} {'already up':<10} external  {addr}\n"
            )


@app.command("down", help="Stop all managed forge-bridge services.")
def down_cmd(
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON envelope to stdout."),
    ] = False,
) -> None:
    from forge_bridge.runtime import manager

    results = manager.stop_all()
    if as_json:
        sys.stdout.write(json.dumps({"data": results}) + "\n")
        return
    if not results:
        sys.stdout.write("no managed services to stop\n")
        return
    for r in results:
        name = r["name"]
        if r.get("stopped"):
            method = r.get("method", "SIGTERM")
            sys.stdout.write(
                f"{name:<10} stopped ({method})  managed (pid {r.get('pid')})\n"
            )
        else:
            note = r.get("note", "not stopped")
            sys.stdout.write(f"{name:<10} {note}\n")


@app.command("status", help="Report which managed forge-bridge services are running.")
def status_cmd(
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON envelope to stdout."),
    ] = False,
) -> None:
    from forge_bridge.runtime import manager

    state = manager.status()
    if as_json:
        sys.stdout.write(json.dumps({"data": state}) + "\n")
        return
    for row in state["services"]:
        name = row["name"]
        running = "running" if row["running"] else "not running"
        # PR5: replace tracked/untracked with the user-facing managed/external
        # split. Co-hosted console rows inherit the underlying mcp_http source
        # so a forge-managed mcp_http surfaces as `managed (pid …)` here too.
        if row.get("managed"):
            ownership = f"managed (pid {row.get('pid')})"
        elif row["running"]:
            ownership = "external"
        else:
            ownership = "—"
        sys.stdout.write(
            f"{name:<14} {running:<12} {ownership:<28} "
            f"{row['host']}:{row['port']}\n"
        )


# ── mcp group: explicit start ─────────────────────────────────────────────
mcp_app = typer.Typer(
    name="mcp",
    help="Start the MCP server on a chosen transport.",
    no_args_is_help=True,
)
app.add_typer(mcp_app, name="mcp")


@mcp_app.command("stdio", help="Start the MCP server on stdio (Claude Desktop default).")
def mcp_stdio() -> None:
    from forge_bridge.mcp.server import main as mcp_main
    mcp_main(transport="stdio")


@mcp_app.command("http", help="Start the MCP server on streamable-http (daemon mode).")
def mcp_http(
    port: Annotated[
        int,
        typer.Option(
            "--port",
            help=f"Port to bind (default {config.MCP_HTTP_PORT}).",
        ),
    ] = config.MCP_HTTP_PORT,
) -> None:
    from forge_bridge.mcp.server import main as mcp_main
    mcp_main(transport="streamable-http", port=port)


# ── flame group: thin ping ────────────────────────────────────────────────
flame_app = typer.Typer(
    name="flame",
    help="Flame HTTP bridge endpoint commands.",
    no_args_is_help=True,
)
app.add_typer(flame_app, name="flame")

_FLAME_PING_TIMEOUT_SECONDS = 2.0


@flame_app.command(
    "ping",
    help=f"Probe the Flame HTTP bridge on :{config.FLAME_BRIDGE_PORT}.",
)
def flame_ping(
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON envelope to stdout."),
    ] = False,
) -> None:
    import httpx

    host = config.flame_bridge_host()
    port = config.flame_bridge_port()
    url = f"http://{host}:{port}/status"
    try:
        with httpx.Client(timeout=_FLAME_PING_TIMEOUT_SECONDS) as client:
            response = client.get(url)
    except (httpx.ConnectError, httpx.TimeoutException, httpx.RemoteProtocolError) as exc:
        exc_name = type(exc).__name__
        if as_json:
            sys.stdout.write(
                json.dumps(
                    {"error": {"code": "flame_unreachable", "message": exc_name}}
                )
                + "\n"
            )
        else:
            sys.stderr.write(
                f"forge-bridge flame: bridge not reachable on {url} ({exc_name}).\n"
                "Is Flame running with the bridge hook loaded?\n"
            )
        raise typer.Exit(code=2)

    if response.status_code != 200:
        message = f"http {response.status_code}"
        if as_json:
            sys.stdout.write(
                json.dumps(
                    {"error": {"code": "flame_status_error", "message": message}}
                )
                + "\n"
            )
        else:
            sys.stderr.write(f"forge-bridge flame: bridge returned {message}\n")
        raise typer.Exit(code=1)

    try:
        body = response.json()
    except ValueError:
        body = {}

    if as_json:
        sys.stdout.write(json.dumps({"data": body}) + "\n")
        return

    flame_available = bool(body.get("flame_available"))
    sys.stdout.write(
        f"flame bridge: ok ({url})\n"
        f"flame_available: {flame_available}\n"
    )


if __name__ == "__main__":
    app()
