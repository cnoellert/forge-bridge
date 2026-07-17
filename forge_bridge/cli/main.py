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
import re
import sys
from typing import Annotated

import typer

from forge_bridge import config
from forge_bridge.cli import author as _author
from forge_bridge.cli import chat as _chat
from forge_bridge.cli import discover as _discover
from forge_bridge.cli import doctor as _doctor
from forge_bridge.cli import exec as _exec
from forge_bridge.cli import execs as _execs
from forge_bridge.cli import flame_exec as _flame_exec
from forge_bridge.cli import graph as _graph
from forge_bridge.cli import health as _health
from forge_bridge.cli import manifest as _manifest
from forge_bridge.cli import run as _run
from forge_bridge.cli import runtime_doctor as _runtime_doctor
from forge_bridge.cli import tools as _tools

_ROOT_EPILOG = """\
Common workflows:

  fbridge doctor                 Check what's running and where (URLs + status).
  fbridge up                     Start the bridge runtime (mcp_http + state_ws).
  fbridge exec "list projects"   Deterministic run via console daemon (no LLM).
  fbridge chat "say hi"          Ask through the shared chat endpoint (LLM).
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

_EXEC_EPILOG = """\
Examples:
  fbridge exec "list forge projects"
  fbridge exec "list forge projects -> list versions" --json

Routes through the console daemon (POST /api/v1/exec on :9996) — same shared
chain engine as chat, no LLM. Fails loudly with exit code 2 if the daemon
isn't running; start it with `fbridge up`. Override the daemon URL with
``FORGE_CONSOLE_URL``. Exit codes: 0=success, 1=usage, 2=transport,
3=protocol, 4=execution error.
"""

_CHAT_EPILOG = """\
Examples:
  fbridge chat "explain this batch setup"
  fbridge chat "hi" --trace              Show per-step summaries on stderr.
  fbridge chat "hi" --verbose            Dump full chain JSON.
  fbridge chat "hi" --timeout 30         Short timeout, fail fast.
  fbridge chat "hi" --retries 0          Single attempt, no auto-retry.
  fbridge chat "hi" --json               JSON envelope (parseable).
  fbridge chat "hi" --quiet              Suppress progress messages.

Tip: `fbridge doctor` first if the call hangs or errors — chat needs
mcp_http running on :9996.
"""

_RATIFY_EPILOG = """\
Examples:
  fbridge ratify 4bd83c2f1abc
  fbridge ratify 4bd83c2f1abc --actor jdoe
  fbridge ratify 4bd83c2f1abc --json

Atomic operation: writes operator assent for the graph-intent, then applies
the persisted chain through the shared store-and-replay substrate.

Exit codes:
  0  apply succeeded
  1  apply failed or CLI validation failed
  2  daemon unreachable
"""

_GRAPH_INTENT_ID_RE = re.compile(r"^[a-f0-9]{12}$")
_RATIFY_TIMEOUT_SECONDS = 65.0


class _RatifyTransportError(Exception):
    """Transport failure while calling the console daemon ratify endpoint."""

    def __init__(self, url: str, reason: str) -> None:
        self.url = url
        self.reason = reason
        super().__init__(reason)


def _ratify_http(graph_intent_id: str, actor: str, *, client=None) -> dict:
    """POST to /api/v1/ratify and return the daemon's JSON envelope."""
    import httpx

    url = f"{config.console_url()}/api/v1/ratify"
    own_client = client is None
    if own_client:
        client = httpx.Client(timeout=_RATIFY_TIMEOUT_SECONDS)

    try:
        try:
            response = client.post(
                url,
                json={"graph_intent_id": graph_intent_id, "actor": actor},
            )
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.TimeoutException) as exc:
            raise _RatifyTransportError(url, type(exc).__name__)
        except httpx.HTTPError as exc:
            raise _RatifyTransportError(url, str(exc) or type(exc).__name__)

        try:
            body = response.json()
        except ValueError:
            return {
                "error": {
                    "code": "invalid_response",
                    "message": f"daemon returned non-JSON response ({response.status_code})",
                    "status_code": response.status_code,
                }
            }
        if not isinstance(body, dict):
            return {
                "error": {
                    "code": "invalid_response",
                    "message": "daemon returned a non-object JSON response",
                    "status_code": response.status_code,
                }
            }
        return body
    finally:
        if own_client:
            client.close()


def _ratify_validation_error(message: str) -> dict:
    return {"error": {"code": "validation_error", "message": message}}


def _ratify_is_success(body: dict) -> bool:
    return "apply_complete" in body and "error" not in body


def _ratify_error_code(body: dict) -> str:
    error = body.get("error")
    if isinstance(error, dict):
        return str(error.get("code") or "ratify_failed")
    if body.get("stop_reason") == "chain_aborted":
        return "chain_aborted"
    if body.get("status") == "error":
        nested = body.get("error")
        if isinstance(nested, dict):
            return str(nested.get("code") or nested.get("type") or "chain_aborted")
        return "chain_aborted"
    return "ratify_failed"


def _render_ratify_human(body: dict) -> None:
    from rich.table import Table

    from forge_bridge.cli.render import HEADER_STYLE, TOOLS_BOX, make_console

    console = make_console()
    table = Table(box=TOOLS_BOX, header_style=HEADER_STYLE)
    table.add_column("Field")
    table.add_column("Value")

    if _ratify_is_success(body):
        payload = body.get("apply_complete") or {}
        graph_intent_id = payload.get("graph_intent_id", "")
        chain = payload.get("chain")
        if isinstance(chain, dict):
            status = chain.get("status", "success")
            steps = len(chain.get("chain") or [])
        else:
            status = "success"
            steps = 0
        table.add_row("status", "apply_complete")
        table.add_row("graph_intent_id", str(graph_intent_id))
        table.add_row("chain_status", str(status))
        table.add_row("steps", str(steps))
        console.print(table)
        return

    error = body.get("error")
    if isinstance(error, dict):
        table.add_row("status", "failed")
        table.add_row("code", str(error.get("code", "ratify_failed")))
        table.add_row("message", str(error.get("message", "")))
        details = error.get("details")
        if isinstance(details, dict):
            for key in ("graph_intent_id", "current_status", "reason", "url"):
                if key in details:
                    table.add_row(key, str(details[key]))
        console.print(table)
        return

    table.add_row("status", "failed")
    table.add_row("code", _ratify_error_code(body))
    if "graph_intent_id" in body:
        table.add_row("graph_intent_id", str(body["graph_intent_id"]))
    console.print(table)


@app.command(
    "ratify",
    help="Ratify a previewed graph-intent and apply its persisted chain.",
    epilog=_RATIFY_EPILOG,
)
def ratify_cmd(
    graph_intent_id: Annotated[
        str,
        typer.Argument(
            help="12-char graph-intent identifier from a prior chat preview",
        ),
    ],
    actor: Annotated[
        str,
        typer.Option(
            "--actor",
            help="Caller identity (free string; future SEED-AUTH integration point)",
        ),
    ] = "local",
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Emit JSON result instead of Rich-rendered table",
        ),
    ] = False,
) -> None:
    """Ratify a previously-emitted graph-intent and apply it.

    Atomic operation: writes the assent record (proposed -> ratified
    transition), then invokes the shared store-and-replay substrate
    to execute the persisted chain (ratified -> applied | failed
    transition). Result returned to stdout.

    Exit codes:
      0  apply succeeded (assent.applied event emitted)
      1  apply failed (any class -- see envelope for code)
      2  daemon unreachable (transport error)
    """
    if not _GRAPH_INTENT_ID_RE.match(graph_intent_id):
        body = _ratify_validation_error(
            "graph_intent_id must be a 12-character lowercase hex string"
        )
        if json_output:
            sys.stdout.write(json.dumps(body) + "\n")
        else:
            _render_ratify_human(body)
        raise typer.Exit(code=1)

    actor = actor.strip()
    if not actor:
        body = _ratify_validation_error("actor must be a non-empty string")
        if json_output:
            sys.stdout.write(json.dumps(body) + "\n")
        else:
            _render_ratify_human(body)
        raise typer.Exit(code=1)

    try:
        body = _ratify_http(graph_intent_id, actor)
    except _RatifyTransportError as exc:
        body = {
            "error": {
                "code": "daemon_unreachable",
                "url": exc.url,
                "reason": exc.reason,
            }
        }
        if json_output:
            sys.stdout.write(json.dumps(body) + "\n")
        else:
            _render_ratify_human(body)
        raise typer.Exit(code=2)

    if json_output:
        sys.stdout.write(json.dumps(body, default=str) + "\n")
    else:
        _render_ratify_human(body)

    if not _ratify_is_success(body):
        raise typer.Exit(code=1)


def _ratify_generation_http(grant_id: str, actor: str, *, client=None) -> dict:
    """POST to /api/v1/ratify-generation and return the daemon's JSON grant."""
    import httpx

    url = f"{config.console_url()}/api/v1/ratify-generation"
    own_client = client is None
    if own_client:
        client = httpx.Client(timeout=_RATIFY_TIMEOUT_SECONDS)
    try:
        try:
            response = client.post(
                url, json={"grant_id": grant_id, "actor": actor},
            )
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.TimeoutException) as exc:
            raise _RatifyTransportError(url, type(exc).__name__)
        except httpx.HTTPError as exc:
            raise _RatifyTransportError(url, str(exc) or type(exc).__name__)
        try:
            body = response.json()
        except ValueError:
            return {"error": {"code": "invalid_response",
                              "message": f"daemon returned non-JSON ({response.status_code})",
                              "status_code": response.status_code}}
        if not isinstance(body, dict):
            return {"error": {"code": "invalid_response",
                              "message": "daemon returned a non-object JSON response",
                              "status_code": response.status_code}}
        return body
    finally:
        if own_client:
            client.close()


def _render_ratify_generation_human(body: dict) -> None:
    from rich.table import Table

    from forge_bridge.cli.render import HEADER_STYLE, TOOLS_BOX, make_console

    console = make_console()
    table = Table(box=TOOLS_BOX, header_style=HEADER_STYLE)
    table.add_column("Field")
    table.add_column("Value")

    error = body.get("error")
    if isinstance(error, dict):
        table.add_row("status", "failed")
        table.add_row("code", str(error.get("code", "ratify_failed")))
        table.add_row("message", str(error.get("message", "")))
        details = error.get("details")
        if isinstance(details, dict):
            for key in ("current_status", "url", "reason"):
                if key in details:
                    table.add_row(key, str(details[key]))
        console.print(table)
        return

    # Success — the canonical grant.to_dict() shape.
    table.add_row("grant_id", str(body.get("grant_id", "")))
    table.add_row("status", str(body.get("status", "")))
    table.add_row("run_kind", str(body.get("run_kind", "")))
    table.add_row("decided_by", str(body.get("decided_by", "")))
    cost = body.get("estimated_cost")
    if isinstance(cost, dict):
        table.add_row(
            "estimated_cost",
            f"{cost.get('amount', '')} {cost.get('currency', '')}".strip(),
        )
    console.print(table)


@app.command(
    "ratify-generation",
    help="Ratify a generation grant so a paid generation submit can spend (#146).",
)
def ratify_generation_cmd(
    grant_id: Annotated[
        str,
        typer.Argument(help="12-char generation-grant handle from an estimate/quote"),
    ],
    actor: Annotated[
        str,
        typer.Option("--actor", help="Caller identity (free string)"),
    ] = "local",
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON result instead of a Rich table"),
    ] = False,
) -> None:
    """Ratify a generation grant (pure proposed -> ratified; nothing is applied).

    Exit codes:
      0  grant ratified
      1  ratify failed or CLI validation failed
      2  daemon unreachable (transport error)
    """
    if not _GRAPH_INTENT_ID_RE.match(grant_id):
        body = _ratify_validation_error(
            "grant_id must be a 12-character lowercase hex string"
        )
        if json_output:
            sys.stdout.write(json.dumps(body) + "\n")
        else:
            _render_ratify_generation_human(body)
        raise typer.Exit(code=1)

    actor = actor.strip()
    if not actor:
        body = _ratify_validation_error("actor must be a non-empty string")
        if json_output:
            sys.stdout.write(json.dumps(body) + "\n")
        else:
            _render_ratify_generation_human(body)
        raise typer.Exit(code=1)

    try:
        body = _ratify_generation_http(grant_id, actor)
    except _RatifyTransportError as exc:
        body = {"error": {"code": "daemon_unreachable", "url": exc.url,
                          "reason": exc.reason}}
        if json_output:
            sys.stdout.write(json.dumps(body) + "\n")
        else:
            _render_ratify_generation_human(body)
        raise typer.Exit(code=2)

    if json_output:
        sys.stdout.write(json.dumps(body, default=str) + "\n")
    else:
        _render_ratify_generation_human(body)

    if body.get("error") is not None or body.get("status") != "ratified":
        raise typer.Exit(code=1)


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
    "author",
    help=(
        "Author a text prompt through the generation runtime and pause for "
        "manual QC."
    ),
)(_author.author_cmd)

app.command(
    "author-targets",
    help="List discovered downstream generator targets for prompt authoring.",
)(_author.author_targets_cmd)

app.command(
    "qc",
    help=(
        "Apply a manual QC note as a derived authoring run, or approve a run."
    ),
)(_author.qc_cmd)

app.command(
    "chat",
    help=(
        "Exercise the LLM end-to-end through the shared chat endpoint. "
        "Wraps the call with timeout, retry, and timing feedback so you "
        "can tell what failed and why."
    ),
    epilog=_CHAT_EPILOG,
)(_chat.chat_cmd)

app.command(
    "exec",
    help=(
        "Run a command string through the deterministic chain engine (PR30/PR31) "
        "via the console daemon (POST /api/v1/exec). No LLM. Fails loudly if the "
        "daemon isn't running — start it with `fbridge up`."
    ),
    epilog=_EXEC_EPILOG,
)(_exec.exec_cmd)

app.command(
    "run",
    help=(
        "Execute a registered tool by exact name — thin alias over the "
        "canonical execution path. Use `fbridge actions` to discover "
        "available names."
    ),
    epilog=_RUN_EPILOG,
)(_run.run_cmd)

_FLAME_EXEC_EPILOG = """\
Examples:
  fbridge flame-exec "import flame; print(flame.project.current_project.name)"
  fbridge flame-exec -f introspect_reels.py
  fbridge flame-exec --main-thread "import flame; flame.batch.create_node('Action')"
  fbridge flame-exec "print(1)" --json

After execution, the printed graph_id round-trips through:
  fbridge graph show <graph_id>      # full event stream for this run

Exit codes:
  0  execution success (Flame returned cleanly)
  1  Flame execution failure (resp.error set; traceback rendered)
  2  Flame bridge unreachable / transport-level failure

This is the operator-side surface onto the same execution path the chat
endpoint uses through `flame_execute_python`. Every LLM execution
failure can be reproduced here against the same substrate.
"""

app.command(
    "flame-exec",
    help=(
        "Execute Python inside Flame through the shared execution substrate "
        "— operator-side complement to the `flame_execute_python` MCP tool. "
        "Reports a graph_id you can replay with `fbridge graph show`."
    ),
    epilog=_FLAME_EXEC_EPILOG,
)(_flame_exec.flame_exec_cmd)


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
    _warn_launchd_supervised(manager)


def _warn_launchd_supervised(manager) -> None:
    """Hint when launchd-supervised daemons are running: `up`/`down` can't
    manage them — `fbridge restart` is the right tool."""
    supervised = manager.launchd_supervised_running()
    if supervised:
        sys.stdout.write(
            "note: "
            + ", ".join(supervised)
            + " are launchd-supervised — `fbridge up`/`down` can't manage them; "
            "use `fbridge restart`.\n"
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
        _warn_launchd_supervised(manager)
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
    _warn_launchd_supervised(manager)


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


@app.command(
    "restart",
    help=(
        "Restart bridge services, routing by how each is supervised — "
        "launchd-supervised daemons via unload/wait/reload (needs sudo), "
        "forge-managed ones via stop+start. The friendly wrapper for a daemon "
        "redeploy: no need to know the launchd incantation."
    ),
)
def restart_cmd(
    target: Annotated[
        str,
        typer.Argument(
            help="What to restart: all | console (:9996/:9997) | server (:9998).",
        ),
    ] = "all",
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON envelope to stdout."),
    ] = False,
) -> None:
    from forge_bridge.runtime import manager

    try:
        results = manager.restart(target)
    except ValueError as exc:
        sys.stderr.write(f"{exc}\n")
        raise typer.Exit(2)
    if as_json:
        sys.stdout.write(json.dumps({"data": results}) + "\n")
        return
    for r in results:
        name = r["name"]
        addr = f"{r.get('host', '')}:{r.get('port', '')}"
        if r["action"] == "skip":
            sys.stdout.write(f"{name:<10} {'skipped':<12} {r.get('note', '')}\n")
        elif r.get("supervisor") == "launchd":
            label = "restarted" if r.get("ok") else "FAILED"
            detail = ""
            if not r.get("ok"):
                reason = r.get("note") or r.get("error")
                if reason:
                    detail = f" ({reason})"
            sys.stdout.write(
                f"{name:<10} {label:<12} launchd ({r.get('label')})  "
                f"{addr}{detail}\n"
            )
        else:
            verb = "started" if r["action"] == "start" else "restarted"
            label = verb if r.get("ok") else "FAILED"
            sys.stdout.write(
                f"{name:<10} {label:<12} managed (pid {r.get('pid')})  {addr}\n"
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


# ── graph group: read-only debug surface over the JSONL graph store ───────
graph_app = typer.Typer(
    name="graph",
    help=(
        "Inspect the Phase 24 proto-node JSONL graph store (default "
        "~/.forge-bridge/graphs/). Read-only debug surface — for product "
        "rendering / replay / promotion, see v1.6+ phases."
    ),
    no_args_is_help=True,
)
graph_app.command(
    "list",
    help=(
        "List recent graph sessions — one row per per-graph JSONL file, "
        "newest first by file mtime."
    ),
    epilog=_graph._GRAPH_LIST_EPILOG,
)(_graph.graph_list_cmd)
graph_app.command(
    "show",
    help=(
        "Dump every event record in one graph's JSONL file. Accepts a full "
        "graph_id or any unique prefix."
    ),
    epilog=_graph._GRAPH_SHOW_EPILOG,
)(_graph.graph_show_cmd)
graph_app.command(
    "run",
    help="Run a composition GraphSpec JSON file through the production runtime.",
    epilog=_graph._GRAPH_RUN_EPILOG,
)(_graph.graph_run_cmd)
app.add_typer(graph_app, name="graph")


# ── discover group: substrate-derived operator vocabulary ─────────────────
discover_app = typer.Typer(
    name="discover",
    help=(
        "Discover the forge-bridge operator vocabulary: the chain grammar, "
        "the six graph primitives, and the available tools."
    ),
    no_args_is_help=True,
)
discover_app.command(
    "primitives",
    help="List graph primitives derived from the primitive registry.",
)(_discover.discover_primitives_cmd)
discover_app.command(
    "primitive",
    help="Show one graph primitive's substrate docstrings.",
)(_discover.discover_primitive_cmd)
discover_app.command(
    "tools",
    help="List MCP tools registered with the bridge.",
)(_discover.discover_tools_cmd)
discover_app.command(
    "tool",
    help="Show one MCP tool's description, annotations, and provenance.",
)(_discover.discover_tool_cmd)
discover_app.command(
    "macros",
    help="List user macros and their chain expansions.",
)(_discover.discover_macros_cmd)
discover_app.command(
    "macro",
    help="Show one macro's full chain expansion.",
)(_discover.discover_macro_cmd)
discover_app.command(
    "grammar",
    help="Show the deterministic chain grammar reference.",
)(_discover.discover_grammar_cmd)
app.add_typer(discover_app, name="discover")


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
