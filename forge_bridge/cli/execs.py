"""forge-bridge console execs — list and drill into execution history.

Reads /api/v1/execs with server-side filters (since/promoted/code_hash/limit/offset)
and applies the client-side --tool filter per D-04 (W-01 workaround). Drilldown
by hash via /api/v1/execs?code_hash=<hash>&limit=1.
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
    format_timestamp,
    make_console,
    short_hash,
)
from forge_bridge.cli.since import parse_since

logger = logging.getLogger(__name__)

_UNREACHABLE_STDERR = (
    "forge-bridge console: server is not running on :9996.\n"
    "Start it with: python -m forge_bridge"
)
_UNREACHABLE_JSON = {
    "error": {"code": "server_unreachable", "message": _UNREACHABLE_STDERR}
}
_TOOL_CLIENT_SIDE_NOTE = (
    "note: --tool is filtered client-side until v1.4 API support; "
    "narrow with --since to scan less history."
)


def execs_cmd(
    hash_arg: Annotated[Optional[str], typer.Argument(
        metavar="HASH",
        help="Optional code_hash for drilldown view (full or short).",
    )] = None,
    tool: Annotated[Optional[str], typer.Option(
        "--tool",
        help="Filter by tool name (client-side; emits stderr note).",
    )] = None,
    since: Annotated[Optional[str], typer.Option(
        "--since",
        help="Filter from this point: Nm/Nh/Nd/Nw or ISO 8601.",
    )] = None,
    until: Annotated[Optional[str], typer.Option(
        "--until",
        help="Filter up to this point: Nm/Nh/Nd/Nw or ISO 8601.",
    )] = None,
    promoted: Annotated[Optional[bool], typer.Option(
        "--promoted/--no-promoted",
        help="Filter by promoted flag.",
    )] = None,
    hash_flag: Annotated[Optional[str], typer.Option(
        "--hash",
        help="Filter by code_hash (full or prefix). Aliased to API code_hash.",
    )] = None,
    limit: Annotated[int, typer.Option(
        "--limit",
        help="Max records (default 50, max 500).",
        min=1, max=500,
    )] = 50,
    offset: Annotated[int, typer.Option(
        "--offset",
        help="Pagination offset.",
        min=0,
    )] = 0,
    as_json: Annotated[bool, typer.Option(
        "--json",
        help="Emit raw API JSON envelope to stdout.",
    )] = False,
    no_color: Annotated[bool, typer.Option(
        "--no-color",
    )] = False,
    quiet: Annotated[bool, typer.Option(
        "--quiet",
    )] = False,
) -> None:
    """List execution history or drill into a single record.

    Examples:
      forge-bridge console execs --since 24h --promoted
      forge-bridge console execs --tool synth_foo --limit 20 --json
    """
    # Build server-supported params first. W-01: NEVER include `tool` in params.
    params: dict[str, str] = {"limit": str(limit), "offset": str(offset)}
    if since:
        try:
            params["since"] = parse_since(since)
        except ValueError:
            _emit_user_error(f"invalid --since value: {since!r}", as_json=as_json)
            raise typer.Exit(code=1)
    if until:
        try:
            params["until"] = parse_since(until)
        except ValueError:
            _emit_user_error(f"invalid --until value: {until!r}", as_json=as_json)
            raise typer.Exit(code=1)
    if promoted is not None:
        params["promoted_only"] = "true" if promoted else "false"
    if hash_flag:
        params["code_hash"] = hash_flag

    # P-01 GUARD — first statement before any Console() instantiation.
    if as_json:
        try:
            if hash_arg:
                envelope = fetch_raw_envelope(
                    "/api/v1/execs",
                    params={"code_hash": hash_arg, "limit": "1"},
                )
            else:
                envelope = fetch_raw_envelope("/api/v1/execs", params=params)
        except ServerUnreachableError:
            sys.stdout.write(json.dumps(_UNREACHABLE_JSON) + "\n")
            raise typer.Exit(code=2)
        except ServerError as e:
            sys.stdout.write(json.dumps({
                "error": {"code": e.code, "message": e.message}
            }) + "\n")
            raise typer.Exit(code=1)
        # Apply client-side --tool filter on the data field even in --json mode
        # (envelope shape preserved; only data list is narrowed).
        if tool and isinstance(envelope.get("data"), list):
            envelope["data"] = [r for r in envelope["data"] if r.get("tool") == tool]
        sys.stdout.write(json.dumps(envelope) + "\n")
        return

    # Rich path
    console = make_console(no_color=no_color)
    stderr_console = make_console(no_color=no_color, stderr=True)

    # Client-side --tool stderr note — D-04 (only in non-json mode)
    if tool:
        stderr_console.print(_TOOL_CLIENT_SIDE_NOTE)

    try:
        if hash_arg:
            records = fetch("/api/v1/execs", params={"code_hash": hash_arg, "limit": "1"})
            if not records:
                stderr_console.print(f"execution not found: {hash_arg}")
                raise typer.Exit(code=1)
            _render_drilldown(console, records[0])
            return
        records = fetch("/api/v1/execs", params=params)
    except ServerUnreachableError:
        stderr_console.print(_UNREACHABLE_STDERR)
        raise typer.Exit(code=2)
    except ServerError as e:
        stderr_console.print(f"error: {e.code}: {e.message}")
        raise typer.Exit(code=1)

    if tool:
        records = [r for r in records if r.get("tool") == tool]

    if not records:
        console.print("No executions found.")
        return
    _render_list(console, records, quiet=quiet)


def _render_list(console, records: list[dict], quiet: bool = False) -> None:
    if quiet:
        for r in records:
            console.print(
                f"{r.get('tool', '')}\t{short_hash(r.get('code_hash'))}\t"
                f"{format_timestamp(r.get('timestamp'))}\t"
                f"{'yes' if r.get('promoted') else 'no'}"
            )
        return
    table = Table(box=TOOLS_BOX, header_style=HEADER_STYLE)
    table.add_column("Tool")
    table.add_column("Hash")
    table.add_column("Timestamp")
    table.add_column("Promoted")
    for r in records:
        table.add_row(
            r.get("tool", ""),
            short_hash(r.get("code_hash")),
            format_timestamp(r.get("timestamp")),
            "✓" if r.get("promoted") else "",
        )
    console.print(table)


def _render_drilldown(console, record: dict) -> None:
    meta_table = Table(box=TOOLS_BOX, header_style=HEADER_STYLE, show_header=False)
    meta_table.add_column("Field")
    meta_table.add_column("Value")
    for field in ("tool", "code_hash", "timestamp", "promoted", "intent"):
        meta_table.add_row(field, str(record.get(field, "")))
    panel = Panel(meta_table, title="Execution Record", border_style=HEADER_STYLE)
    console.print(panel)
    if record.get("raw_code"):
        console.print(Syntax(record["raw_code"], "python", theme="ansi_dark"))


def _emit_user_error(message: str, as_json: bool) -> None:
    if as_json:
        sys.stdout.write(json.dumps({
            "error": {"code": "bad_request", "message": message}
        }) + "\n")
    else:
        console = make_console(stderr=True)
        console.print(f"error: {message}")
