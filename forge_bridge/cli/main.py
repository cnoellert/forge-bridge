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
from forge_bridge.cli import run as _run
from forge_bridge.cli import runtime_doctor as _runtime_doctor
from forge_bridge.cli import tools as _tools

_ROOT_EPILOG = """\
Common workflows:

  fbridge doctor                 Check what's running and where (URLs + status).
  fbridge up                     Start the bridge runtime (mcp_http + state_ws).
  fbridge chat "say hi"          Ask a question through the shared chat endpoint.
  fbridge actions                Browse the tools currently registered.

First time? Try: fbridge doctor → fbridge up → fbridge chat "hello"

Run any subcommand with --help for examples and details.
"""

app = typer.Typer(
    name="forge-bridge",
    help=(
        "forge-bridge — unified CLI for the post-production pipeline bus.\n\n"
        "Front door for the MCP server, Flame HTTP bridge, Artist Console, "
        "and the chat endpoint. Use it to start the runtime, verify health, "
        "and explore registered tools without reading the docs."
    ),
    epilog=_ROOT_EPILOG,
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
    help=(
        "Inspect the Artist Console — list registered tools, browse exec "
        "history, read the synthesis manifest, check health, or run the "
        "in-depth diagnostic. Mirrors the `/api/v1/*` Read API."
    ),
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
_DOCTOR_EPILOG = """\
Examples:
  fbridge doctor                 Human-readable status table.
  fbridge doctor --json          Stable JSON envelope for scripts/CI.

Next:
  Any FAIL row prints a one-line fix. If everything is OK, try
  `fbridge actions` or open the Artist Console at the printed URL.
"""

_ACTIONS_EPILOG = """\
Examples:
  fbridge actions                List all registered tools.
  fbridge actions --origin synthesized   Show only LLM-synthesized tools.
  fbridge actions --json         Stable JSON envelope.
"""

_RUN_EPILOG = """\
Examples:
  fbridge run flame_ping         Execute a registered tool by exact name.
  fbridge run flame_ping --json  Emit {ok, action, result} envelope.
  fbridge run flame_ping -v      Show timing on stderr.

Discovery:
  Use `fbridge actions` to see what's registered. Names are exact-match.
"""

_CHAT_EPILOG = """\
Examples:
  fbridge chat "explain this batch setup"
  fbridge chat "hi" --verbose            Show model + provider + timing.
  fbridge chat "hi" --timeout 30         Short timeout, fail fast.
  fbridge chat "hi" --retries 0          Single attempt, no auto-retry.
  fbridge chat "hi" --json               JSON envelope (parseable).
  fbridge chat "hi" --quiet              Suppress progress messages.

Tip: `fbridge doctor` first if the call hangs or errors — chat needs
mcp_http running on :9996.
"""

app.command(
    "doctor",
    help=(
        "Verify what's running across forge-bridge surfaces (Console, MCP, "
        "Flame, State WS) — answers 'is this box ready to work?' with URLs "
        "and a single suggested next action."
    ),
    epilog=_DOCTOR_EPILOG,
)(_runtime_doctor.runtime_doctor_cmd)

app.command(
    "actions",
    help=(
        "Browse the tools currently registered with the bridge (built-in + "
        "synthesized) — useful for discovering what can be automated."
    ),
    epilog=_ACTIONS_EPILOG,
)(_tools.tools_cmd)

app.command(
    "chat",
    help=(
        "Send a question through the shared chat endpoint to exercise the "
        "LLM end-to-end. Wraps the call with timeout, retry, and timing "
        "feedback so you can tell what failed and why."
    ),
    epilog=_CHAT_EPILOG,
)(_chat.chat_cmd)

app.command(
    "run",
    help=(
        "Execute a registered tool by exact name — thin alias over the "
        "canonical execution path. Use `fbridge actions` to discover "
        "available names."
    ),
    epilog=_RUN_EPILOG,
)(_run.run_cmd)


# ── runtime manager: forge up / down / status ────────────────────────────
_UP_EPILOG = """\
Examples:
  fbridge up                     Start mcp_http (with co-hosted Console)
                                 and state_ws as background services.
  fbridge up --json              JSON envelope (managed/source per service).

Next:
  Verify with `fbridge status`, do a full surface check via `fbridge doctor`,
  or exercise the chat endpoint with `fbridge chat "hello"`.
"""

_DOWN_EPILOG = """\
Examples:
  fbridge down                   Stop everything fbridge started.
  fbridge down --json            JSON envelope.

Note: only services we started (managed=true) are stopped. External
processes — e.g. systemd / launchd daemons — are left alone.
"""

_STATUS_EPILOG = """\
Examples:
  fbridge status                 Human-readable table.
  fbridge status --json          Stable JSON envelope.

Each row shows running state and ownership: `managed (pid …)` if fbridge
started it, `external` if something else is bound to the port.
"""


@app.command(
    "up",
    help=(
        "Bring up the bridge runtime — start mcp_http (with co-hosted "
        "Console) and state_ws as detached background processes. Idempotent: "
        "skips ports already bound, marks them external."
    ),
    epilog=_UP_EPILOG,
)
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


@app.command(
    "down",
    help=(
        "Stop the background services that `fbridge up` started. External "
        "processes (e.g. systemd / launchd daemons) are not touched."
    ),
    epilog=_DOWN_EPILOG,
)
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


@app.command(
    "status",
    help=(
        "Show what's running and who started it — a quick view of the "
        "bridge runtime without the full surface health check that "
        "`fbridge doctor` does."
    ),
    epilog=_STATUS_EPILOG,
)
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
    help=(
        "Run the MCP server directly — `stdio` for Claude Desktop / Code "
        "configs, `http` for the always-on daemon mode used by `fbridge up`."
    ),
    no_args_is_help=True,
)
app.add_typer(mcp_app, name="mcp")


@mcp_app.command(
    "stdio",
    help=(
        "Start the MCP server on stdio. Use this from Claude Desktop / Claude "
        "Code config; the process exits when the parent client disconnects."
    ),
)
def mcp_stdio() -> None:
    from forge_bridge.mcp.server import main as mcp_main
    mcp_main(transport="stdio")


@mcp_app.command(
    "http",
    help=(
        "Start the MCP server on streamable-http for daemon mode. Long-running "
        "uvicorn server that does not exit on stdin EOF — what `fbridge up` "
        "uses behind the scenes."
    ),
)
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
    help=(
        "Talk to the Flame HTTP bridge running inside Flame on "
        f":{config.FLAME_BRIDGE_PORT} — currently just a liveness `ping`."
    ),
    no_args_is_help=True,
)
app.add_typer(flame_app, name="flame")

_FLAME_PING_TIMEOUT_SECONDS = 2.0


_FLAME_PING_EPILOG = """\
Examples:
  fbridge flame ping             Confirm Flame is up and the hook is loaded.
  fbridge flame ping --json      JSON envelope (status + flame_available).

Exit codes:
  0  reachable, Flame attached     1  reachable, status != 200
  2  unreachable                   (start Flame with the bridge hook loaded)
"""


@flame_app.command(
    "ping",
    help=(
        f"Confirm the Flame HTTP bridge on :{config.FLAME_BRIDGE_PORT} is "
        "reachable and that the `flame` module is attached — fastest way to "
        "tell whether Flame is alive and the hook is loaded."
    ),
    epilog=_FLAME_PING_EPILOG,
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
