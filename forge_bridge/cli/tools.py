"""forge-bridge console tools — list and drill into registered tools.

Reads /api/v1/tools and /api/v1/tools/<name>; applies client-side filters
per D-03 (origin, namespace, readonly, search). Renders a Rich table for the
list view and a Rich Panel for the drilldown.
"""
from __future__ import annotations

import json
import logging
import sys
from typing import Annotated, Optional

import typer
from rich.panel import Panel
from rich.syntax import Syntax
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


def _derive_status(tool: dict) -> str:
    """Map ToolRecord dict to a status keyword for the chip column.

    Quarantined tools never appear (Phase 10.1 D-40 — filtered upstream).
    Synthesized tools are 'active'; builtin tools are 'loaded'.
    """
    if tool.get("origin") == "synthesized":
        return "active"
    return "loaded"


def _filter_tools(
    tools: list[dict],
    origin: Optional[str],
    namespace: Optional[str],
    readonly: Optional[bool],
    search: Optional[str],
) -> list[dict]:
    """Client-side filter per D-03. Tools list is small (tens to low hundreds)."""
    out = tools
    if origin:
        out = [t for t in out if t.get("origin") == origin]
    if namespace:
        out = [t for t in out if (t.get("namespace") or "").startswith(namespace)]
    if readonly is not None:
        # ToolRecord has no readonly field directly — surface via meta if present.
        # If not present, --readonly filter passes through unchanged (forward-compat).
        out = [
            t for t in out
            if (t.get("meta") or {}).get("readOnlyHint") == ("true" if readonly else "false")
        ]
    if search:
        needle = search.lower()
        out = [t for t in out if needle in t.get("name", "").lower()]
    return out


def tools_cmd(
    name: Annotated[Optional[str], typer.Argument(
        help="Optional tool name for drilldown view.",
    )] = None,
    origin: Annotated[Optional[str], typer.Option(
        "--origin",
        help="Filter by origin: builtin or synthesized.",
    )] = None,
    namespace: Annotated[Optional[str], typer.Option(
        "--namespace",
        help="Filter by namespace prefix (e.g., 'synth', 'flame').",
    )] = None,
    readonly: Annotated[Optional[bool], typer.Option(
        "--readonly/--no-readonly",
        help="Filter by readOnlyHint.",
    )] = None,
    search: Annotated[Optional[str], typer.Option(
        "-q", "--search",
        help="Substring search on tool name.",
    )] = None,
    as_json: Annotated[bool, typer.Option(
        "--json",
        help="Emit raw API JSON envelope to stdout (machine-readable).",
    )] = False,
    no_color: Annotated[bool, typer.Option(
        "--no-color",
        help="Disable color output.",
    )] = False,
    quiet: Annotated[bool, typer.Option(
        "--quiet",
        help="Suppress Rich decorations; minimal plain-text output.",
    )] = False,
) -> None:
    """List registered tools or drill into a single tool.

    Note: quarantined tools are filtered upstream at ConsoleReadAPI and never appear here.

    Examples:
      forge-bridge console tools --origin synthesized
    """
    # P-01 GUARD — must be FIRST statement, before any Console() instantiation
    if as_json:
        try:
            if name:
                envelope = fetch_raw_envelope(f"/api/v1/tools/{name}")
            else:
                envelope = fetch_raw_envelope("/api/v1/tools")
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

    # Rich path
    console = make_console(no_color=no_color)
    stderr_console = make_console(no_color=no_color, stderr=True)

    try:
        if name:
            tool = fetch(f"/api/v1/tools/{name}")
        else:
            tools = fetch("/api/v1/tools")
    except ServerUnreachableError:
        stderr_console.print(_UNREACHABLE_STDERR)
        raise typer.Exit(code=2)
    except ServerError as e:
        stderr_console.print(f"error: {e.code}: {e.message}")
        raise typer.Exit(code=1)

    if name:
        _render_drilldown(console, tool)
        return

    filtered = _filter_tools(tools, origin, namespace, readonly, search)
    if not filtered:
        console.print("No tools found.")
        return
    _render_list(console, filtered, quiet=quiet)


def _render_list(console, tools: list[dict], quiet: bool = False) -> None:
    if quiet:
        for t in tools:
            console.print(
                f"{t['name']}\t{_derive_status(t)}\t"
                f"{t.get('origin', '')}\t{format_timestamp(t.get('synthesized_at'))}"
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
        table.add_row(
            t["name"],
            status_chip(_derive_status(t)),
            type_label,
            format_timestamp(t.get("synthesized_at")),
        )
    console.print(table)


def _render_drilldown(console, tool: dict) -> None:
    meta_table = Table(box=TOOLS_BOX, header_style=HEADER_STYLE, show_header=False)
    meta_table.add_column("Field")
    meta_table.add_column("Value")
    for field in ("origin", "code_hash", "synthesized_at", "version", "observation_count"):
        meta_table.add_row(field, str(tool.get(field, "")))
    tags = tool.get("tags") or []
    meta_table.add_row("tags", ", ".join(tags) if tags else "(none)")
    panel = Panel(meta_table, title=tool.get("name", ""), border_style=HEADER_STYLE)
    console.print(panel)
    # Raw source for synth tools — Rich Syntax block, 40-line truncation per CONTEXT.md Area 3
    raw = (tool.get("meta") or {}).get("raw_source")
    if raw:
        lines = raw.splitlines()
        if len(lines) > 40:
            lines = lines[:40] + ["… (use --json for full source)"]
        console.print(Syntax("\n".join(lines), "python", theme="ansi_dark"))
