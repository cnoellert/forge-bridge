"""Top-level ``forge-bridge doctor`` — runtime topology probe.

Distinct from the legacy ``console doctor`` (which inspects the running
console process in depth). This one answers the operator's first
question — "what's running on this box, and what should I do next?" — by
probing each surface at the URL it should be at and reporting a stable
shape:

    {"ok": bool, "checks": [{"name", "ok", "status", "url", "fix"}, ...]}

Human mode prints a Rich table plus a one-line "Suggested next action".
"""
from __future__ import annotations

import json
import socket
import sys
from typing import Annotated, Any

import httpx
import typer
from rich.table import Table

from forge_bridge import config
from forge_bridge.cli.render import HEADER_STYLE, TOOLS_BOX, make_console, status_chip

_HTTP_TIMEOUT = 1.5
_TCP_TIMEOUT = 1.0


def runtime_doctor_cmd(
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit a stable JSON envelope to stdout."),
    ] = False,
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable color output."),
    ] = False,
) -> None:
    """Probe forge-bridge surfaces and report status, URLs, and next steps."""
    checks: list[dict[str, Any]] = [
        _check_console(),
        _check_mcp_http(),
        _check_flame_bridge(),
        _check_state_ws(),
    ]
    overall_ok = all(c["ok"] for c in checks)

    if as_json:
        payload = {"ok": overall_ok, "checks": checks}
        sys.stdout.write(json.dumps(payload) + "\n")
        raise typer.Exit(code=0 if overall_ok else 1)

    _render_human(checks, overall_ok, no_color=no_color)
    raise typer.Exit(code=0 if overall_ok else 1)


# ── individual probes ─────────────────────────────────────────────────────

def _check_console() -> dict[str, Any]:
    url = config.console_url()
    health_url = f"{url}/api/v1/health"
    try:
        with httpx.Client(timeout=_HTTP_TIMEOUT) as client:
            r = client.get(health_url)
    except (httpx.ConnectError, httpx.TimeoutException, httpx.RemoteProtocolError) as exc:
        return {
            "name": "console",
            "ok": False,
            "status": f"unreachable ({type(exc).__name__})",
            "url": url,
            "fix": "start the console + MCP server: `python -m forge_bridge mcp http`",
        }
    if r.status_code != 200:
        return {
            "name": "console",
            "ok": False,
            "status": f"http {r.status_code}",
            "url": url,
            "fix": "console responded but not 200 — check `forge-bridge console doctor`",
        }
    return {
        "name": "console",
        "ok": True,
        "status": "running",
        "url": url,
        "fix": "",
    }


def _check_mcp_http() -> dict[str, Any]:
    """Probe MCP HTTP transport with a TCP connect.

    streamable-http exposes JSON-RPC under ``/mcp`` and rejects bare GETs,
    so a TCP listen check is the cheapest reliable liveness probe — and
    matches what we can do for the WebSocket port.
    """
    host = config.mcp_http_host()
    port = config.mcp_http_port()
    url = config.mcp_http_url()
    if _tcp_reachable(host, port):
        return {
            "name": "mcp_http",
            "ok": True,
            "status": "listening",
            "url": url,
            "fix": "",
        }
    return {
        "name": "mcp_http",
        "ok": False,
        "status": "not listening",
        "url": url,
        "fix": "start the MCP HTTP server: `python -m forge_bridge mcp http`",
    }


def _check_flame_bridge() -> dict[str, Any]:
    url = config.flame_bridge_url()
    try:
        with httpx.Client(timeout=_HTTP_TIMEOUT) as client:
            r = client.get(f"{url}/status")
    except (httpx.ConnectError, httpx.TimeoutException, httpx.RemoteProtocolError) as exc:
        return {
            "name": "flame_bridge",
            "ok": False,
            "status": f"unreachable ({type(exc).__name__})",
            "url": url,
            "fix": "start Flame with the forge-bridge hook loaded "
                   "(see `./scripts/install-flame-hook.sh`)",
        }
    if r.status_code != 200:
        return {
            "name": "flame_bridge",
            "ok": False,
            "status": f"http {r.status_code}",
            "url": url,
            "fix": "Flame bridge responded but not 200 — restart Flame and retry",
        }
    try:
        body = r.json()
    except ValueError:
        body = {}
    flame_available = bool(body.get("flame_available"))
    if not flame_available:
        return {
            "name": "flame_bridge",
            "ok": False,
            "status": "running, no flame module",
            "url": url,
            "fix": "the bridge HTTP server is up but Flame isn't attached — "
                   "open a Flame project to load the `flame` module",
        }
    return {
        "name": "flame_bridge",
        "ok": True,
        "status": "running",
        "url": url,
        "fix": "",
    }


def _check_state_ws() -> dict[str, Any]:
    host = config.state_ws_host()
    port = config.state_ws_port()
    url = config.state_ws_url()
    if _tcp_reachable(host, port):
        return {
            "name": "state_ws",
            "ok": True,
            "status": "listening",
            "url": url,
            "fix": "",
        }
    return {
        "name": "state_ws",
        "ok": False,
        "status": "not listening",
        "url": url,
        "fix": "the State WebSocket server is optional — see docs/ARCHITECTURE.md "
               "if you need it for your workflow",
    }


def _tcp_reachable(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=_TCP_TIMEOUT):
            return True
    except (OSError, socket.timeout):
        return False


# ── human renderer ────────────────────────────────────────────────────────

def _render_human(
    checks: list[dict[str, Any]],
    overall_ok: bool,
    *,
    no_color: bool,
) -> None:
    console = make_console(no_color=no_color)
    table = Table(box=TOOLS_BOX, header_style=HEADER_STYLE)
    table.add_column("Surface")
    table.add_column("Status")
    table.add_column("URL")
    for c in checks:
        table.add_row(
            c["name"],
            status_chip("ok" if c["ok"] else "fail"),
            f"{c['status']}  {c['url']}",
        )
    console.print(table)

    if overall_ok:
        console.print("Suggested next action: all surfaces are running. "
                      "Open the Artist Console at "
                      f"{config.console_url()}/ui/.")
        return

    first_fail = next((c for c in checks if not c["ok"]), None)
    if first_fail and first_fail.get("fix"):
        console.print(f"Suggested next action: {first_fail['fix']}")
    else:
        console.print("Suggested next action: see per-surface fix hints above.")
