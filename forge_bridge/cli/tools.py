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
from rich.text import Text

from forge_bridge.cli.client import (
    ServerError,
    ServerUnreachableError,
    fetch,
    fetch_raw_envelope,
)
from forge_bridge.cli.render import (
    HEADER_STYLE,
    TOOLS_BOX,
    format_timestamp,
    make_console,
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


# PR9: presentation-only namespace → group title map. Tools whose namespace is
# missing fall back to the prefix on the name (defense-in-depth for older
# ToolRecord shapes). The order here drives the section order in `--help`-style
# rendering: pipeline state first, then live Flame, then synthesized.
_GROUP_TITLES: list[tuple[str, str]] = [
    ("forge", "Forge — pipeline state"),
    ("flame", "Flame — live API"),
    ("synth", "Synthesized — LLM-generated"),
]
_NAME_PREFIX_TO_NAMESPACE: dict[str, str] = {
    "forge_": "forge",
    "flame_": "flame",
    "synth_": "synth",
}


def _namespace_of(tool: dict) -> str:
    ns = (tool.get("namespace") or "").strip()
    if ns:
        return ns
    name = tool.get("name", "")
    for prefix, mapped in _NAME_PREFIX_TO_NAMESPACE.items():
        if name.startswith(prefix):
            return mapped
    return "other"


def _humanize(name: str) -> str:
    """`flame_get_sequence_segments` → `Get sequence segments`.

    Drops the leading `<namespace>_` prefix and converts the remaining
    snake_case to sentence case. Empty / single-token names pass through
    capitalized.
    """
    stripped = name
    for prefix in _NAME_PREFIX_TO_NAMESPACE:
        if name.startswith(prefix):
            stripped = name[len(prefix):]
            break
    if not stripped:
        return name
    words = stripped.replace("_", " ").split()
    if not words:
        return name
    return " ".join([words[0].capitalize(), *words[1:]])


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
    """Render the tool inventory grouped by namespace (PR9).

    Each section shows the raw tool name (still required for `fbridge run
    <name>`) alongside a humanized form derived from the snake_case name.
    `quiet=True` keeps the legacy tab-separated output for scripting.
    """
    if quiet:
        for t in tools:
            console.print(
                f"{t['name']}\t{_derive_status(t)}\t"
                f"{t.get('origin', '')}\t{_availability_label(t)}\t"
                f"{format_timestamp(t.get('synthesized_at'))}"
            )
        return

    grouped: dict[str, list[dict]] = {}
    for t in tools:
        grouped.setdefault(_namespace_of(t), []).append(t)

    # Section order is fixed (_GROUP_TITLES) so the output is predictable
    # across runs. Unknown namespaces (defensive — registry rejects them at
    # write time, but render anyway) get a generic "Other" footer.
    section_order = [(ns, title) for ns, title in _GROUP_TITLES if ns in grouped]
    other_keys = sorted(set(grouped) - {ns for ns, _ in _GROUP_TITLES})
    section_order.extend((ns, ns.capitalize()) for ns in other_keys)

    first = True
    for ns, title in section_order:
        if not first:
            console.print()
        first = False
        console.print(Text(title, style=HEADER_STYLE))
        table = Table(box=TOOLS_BOX, show_header=False, padding=(0, 1))
        table.add_column("Name", overflow="fold")
        table.add_column("Description", overflow="fold")
        table.add_column("Status", overflow="fold")
        for t in sorted(grouped[ns], key=lambda x: x.get("name", "")):
            table.add_row(
                t["name"],
                _humanize(t["name"]),
                _availability_chip(t),
            )
        console.print(table)


def _availability_label(tool: dict) -> str:
    """Plain-text availability for --quiet output and JSON-equivalent rendering."""
    av = tool.get("available")
    if av is True:
        return "available"
    if av is False:
        return "unavailable"
    return "unknown"


def _availability_chip(tool: dict) -> Text:
    """Styled availability chip for the Rich table column."""
    av = tool.get("available")
    if av is True:
        return Text("available", style="green")
    if av is False:
        return Text("unavailable", style="red")
    return Text("unknown", style="dim")


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
