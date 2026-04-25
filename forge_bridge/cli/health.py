"""forge-bridge console health — Rich Panels per service group + --json passthrough."""
from __future__ import annotations

import json
import logging
import sys
from typing import Annotated

import typer
from rich.panel import Panel
from rich.table import Table

from forge_bridge.cli.client import (
    ServerError,
    ServerUnreachableError,
    fetch,
    fetch_raw_envelope,
)
from forge_bridge.cli.render import HEADER_STYLE, TOOLS_BOX, make_console, status_chip

logger = logging.getLogger(__name__)

_UNREACHABLE_STDERR = (
    "forge-bridge console: server is not running on :9996.\n"
    "Start it with: python -m forge_bridge"
)
_UNREACHABLE_JSON = {
    "error": {"code": "server_unreachable", "message": _UNREACHABLE_STDERR}
}


def health_cmd(
    as_json: Annotated[bool, typer.Option("--json")] = False,
    no_color: Annotated[bool, typer.Option("--no-color")] = False,
    quiet: Annotated[bool, typer.Option("--quiet")] = False,
) -> None:
    """Show service liveness across MCP, watcher, bridge, LLM backends, etc.

    Examples:
      forge-bridge console health --json
    """
    # P-01 GUARD
    if as_json:
        try:
            envelope = fetch_raw_envelope("/api/v1/health")
        except ServerUnreachableError:
            sys.stdout.write(json.dumps(_UNREACHABLE_JSON) + "\n")
            raise typer.Exit(code=2)
        except ServerError as e:
            sys.stdout.write(json.dumps({
                "error": {"code": e.code, "message": e.message}
            }) + "\n")
            raise typer.Exit(code=1)
        sys.stdout.write(json.dumps(envelope) + "\n")
        return

    console = make_console(no_color=no_color)
    stderr_console = make_console(no_color=no_color, stderr=True)
    try:
        data = fetch("/api/v1/health")
    except ServerUnreachableError:
        stderr_console.print(_UNREACHABLE_STDERR)
        raise typer.Exit(code=2)
    except ServerError as e:
        stderr_console.print(f"error: {e.code}: {e.message}")
        raise typer.Exit(code=1)

    services = data.get("services", {}) or {}
    instance_identity = data.get("instance_identity", {}) or {}
    agg = data.get("status", "unknown")

    # Aggregate pill at top
    console.print(status_chip(agg))

    # Critical block: mcp · watcher · console_port
    _render_panel(console, "Critical (mcp · watcher · console_port)", [
        ("mcp", services.get("mcp", {})),
        ("watcher", services.get("watcher", {})),
        ("console_port", services.get("console_port", {})),
    ])
    # Degraded-tolerant block: flame_bridge · ws_server
    _render_panel(console, "Degraded-tolerant (flame_bridge · ws_server)", [
        ("flame_bridge", services.get("flame_bridge", {})),
        ("ws_server", services.get("ws_server", {})),
    ])
    # llm_backends block — one line per backend
    backends = services.get("llm_backends") or []
    if backends:
        _render_panel(console, "LLM backends", [
            (b.get("name", "?"), b) for b in backends
        ])
    else:
        _render_panel(console, "LLM backends", [("(none)", {"status": "absent"})])
    # Provenance block
    _render_panel(console, "Provenance (storage_callback · instance_identity)", [
        ("storage_callback", services.get("storage_callback", {})),
        ("execution_log_id_match", instance_identity.get("execution_log", {})),
        ("manifest_service_id_match", instance_identity.get("manifest_service", {})),
    ])


def _render_panel(console, title: str, rows: list[tuple[str, dict]]) -> None:
    table = Table(box=TOOLS_BOX, header_style=HEADER_STYLE, show_header=False)
    table.add_column("Service")
    table.add_column("Status")
    table.add_column("Detail")
    for name, info in rows:
        info = info or {}
        status = info.get("status", "unknown") if isinstance(info, dict) else "unknown"
        detail = info.get("detail", "") if isinstance(info, dict) else ""
        # Special-case id_match (instance_identity rows)
        if isinstance(info, dict) and "id_match" in info:
            status = "ok" if info["id_match"] else "fail"
        table.add_row(name, status_chip(status), str(detail))
    console.print(Panel(table, title=title, border_style=HEADER_STYLE))
