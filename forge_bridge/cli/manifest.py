"""forge-bridge console manifest — synthesis manifest as Rich table or --json."""
from __future__ import annotations

import json
import logging
import sys
from typing import Annotated, Optional

import typer
from rich.table import Table

from forge_bridge.cli.client import (
    ServerError,
    ServerUnreachableError,
    fetch,
    fetch_raw_envelope,
)
from forge_bridge.cli.render import (
    HEADER_STYLE,
    TOOLS_BOX,
    created_column_header,
    format_timestamp,
    make_console,
    status_chip,
)

logger = logging.getLogger(__name__)

_UNREACHABLE_STDERR = (
    "forge-bridge console: server is not running on :9996.\n"
    "Start it with: python -m forge_bridge"
)
_UNREACHABLE_JSON = {
    "error": {"code": "server_unreachable", "message": _UNREACHABLE_STDERR}
}


def manifest_cmd(
    search: Annotated[Optional[str], typer.Option(
        "-q", "--search",
        help="Substring search on tool name.",
    )] = None,
    status: Annotated[Optional[str], typer.Option(
        "--status",
        help="Reserved for future status filtering; currently no-op.",
    )] = None,
    as_json: Annotated[bool, typer.Option("--json")] = False,
    no_color: Annotated[bool, typer.Option("--no-color")] = False,
    quiet: Annotated[bool, typer.Option("--quiet")] = False,
) -> None:
    """Show the synthesis manifest as a Rich table.

    Examples:
      forge-bridge console manifest -q synth
    """
    # P-01 GUARD
    if as_json:
        try:
            envelope = fetch_raw_envelope("/api/v1/manifest")
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
        data = fetch("/api/v1/manifest")
    except ServerUnreachableError:
        stderr_console.print(_UNREACHABLE_STDERR)
        raise typer.Exit(code=2)
    except ServerError as e:
        stderr_console.print(f"error: {e.code}: {e.message}")
        raise typer.Exit(code=1)

    tools = data.get("tools", [])
    if search:
        tools = [t for t in tools if search.lower() in t.get("name", "").lower()]
    if not tools:
        console.print("No manifest entries found.")
        return

    if quiet:
        for t in tools:
            console.print(
                f"{t['name']}\t{t.get('origin', '')}\t"
                f"{format_timestamp(t.get('synthesized_at'))}"
            )
        return

    table = Table(box=TOOLS_BOX, header_style=HEADER_STYLE)
    table.add_column("Name")
    table.add_column("Status")
    table.add_column("Type")
    table.add_column(created_column_header())
    for t in tools:
        origin = t.get("origin", "")
        type_label = "Synthesized" if origin == "synthesized" else "Built-in"
        chip_status = "active" if origin == "synthesized" else "loaded"
        table.add_row(
            t["name"],
            status_chip(chip_status),
            type_label,
            format_timestamp(t.get("synthesized_at")),
        )
    console.print(table)
