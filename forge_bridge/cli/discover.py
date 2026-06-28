"""fbridge discover — substrate-derived operator vocabulary introspection.

Thread B / B-1: enumerate what the substrate already knows about its
operator vocabulary. This surface is intentionally derived from live
registries and docstrings: graph primitive predicates, MCP tool records,
macro registry, and chain parser module documentation.
"""
from __future__ import annotations

import importlib
import inspect
import json
import re
import sys
from typing import Annotated, Any

import typer
from rich.table import Table

from forge_bridge.cli.client import (
    ServerError,
    ServerUnreachableError,
    fetch,
    fetch_raw_envelope,
)
from forge_bridge.cli.render import HEADER_STYLE, TOOLS_BOX, make_console


_PRIMITIVE_RE = re.compile(r"^is_(?P<name>.+)_step$")

_UNREACHABLE_STDERR = (
    "fbridge discover: daemon read API is not running on :9996.\n"
    "Start it with: fbridge up"
)
_UNREACHABLE_JSON = {
    "error": {"code": "server_unreachable", "message": _UNREACHABLE_STDERR}
}


def _first_line(text: str | None) -> str:
    doc = inspect.cleandoc(text or "")
    if not doc:
        return ""
    return doc.splitlines()[0]


def _doc(text: str | None) -> str:
    return inspect.cleandoc(text or "")


def _emit_json(data: Any) -> None:
    sys.stdout.write(json.dumps({"data": data}, default=str) + "\n")


def _primitive_records() -> list[dict[str, str]]:
    # Lazy import — graph pulls in the primitive modules. Keep root --help fast.
    import forge_bridge.graph as graph

    rows: list[dict[str, str]] = []
    for attr_name in dir(graph):
        match = _PRIMITIVE_RE.match(attr_name)
        if not match:
            continue
        predicate = getattr(graph, attr_name)
        if not callable(predicate):
            continue
        name = match.group("name")
        module = importlib.import_module(predicate.__module__)
        rows.append({
            "name": name,
            "module": module.__name__,
            "summary": _first_line(module.__doc__),
        })
    return sorted(rows, key=lambda row: row["name"])


def _primitive_detail(name: str) -> dict[str, str] | None:
    import forge_bridge.graph as graph

    primitives = {row["name"]: row for row in _primitive_records()}
    row = primitives.get(name)
    if row is None:
        return None
    module = importlib.import_module(row["module"])
    parser = getattr(graph, f"parse_{name}_step", None)
    return {
        "name": name,
        "module": row["module"],
        "module_docstring": _doc(module.__doc__),
        "parse_docstring": _doc(getattr(parser, "__doc__", None)),
    }


def _macro_records() -> list[dict[str, str]]:
    # Lazy import — macro load reads the user macro file at import time.
    from forge_bridge.console import _macros

    macros = _macros.list_macros()
    return [
        {"name": name, "chain": chain}
        for name, chain in sorted(macros.items(), key=lambda item: item[0])
    ]


def _not_found(kind: str, name: str, as_json: bool) -> None:
    message = f"{kind} not found: {name}"
    if as_json:
        sys.stdout.write(
            json.dumps({"error": {"code": f"{kind}_not_found", "message": message}})
            + "\n"
        )
    else:
        sys.stderr.write(message + "\n")
    raise typer.Exit(code=1)


def discover_primitives_cmd(
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON envelope to stdout."),
    ] = False,
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable color output."),
    ] = False,
) -> None:
    """List graph primitives derived from is_<name>_step callables."""
    rows = _primitive_records()
    if as_json:
        _emit_json(rows)
        return

    console = make_console(no_color=no_color)
    table = Table(box=TOOLS_BOX, header_style=HEADER_STYLE)
    table.add_column("Primitive")
    table.add_column("Description")
    for row in rows:
        table.add_row(row["name"], row["summary"] or "—")
    console.print(table)


def discover_primitive_cmd(
    name: Annotated[str, typer.Argument(help="Primitive name, e.g. collect.")],
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON envelope to stdout."),
    ] = False,
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable color output."),
    ] = False,
) -> None:
    """Show one primitive's module and parser docstrings."""
    detail = _primitive_detail(name)
    if detail is None:
        _not_found("primitive", name, as_json)
    if as_json:
        _emit_json(detail)
        return

    console = make_console(no_color=no_color)
    console.print(f"primitive: {detail['name']}")
    console.print(f"module:    {detail['module']}")
    console.print("")
    console.print(detail["module_docstring"] or "(no module docstring)")
    console.print("")
    console.print("parse docstring:")
    console.print(detail["parse_docstring"] or "(no parse docstring)")


def discover_tools_cmd(
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON envelope to stdout."),
    ] = False,
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable color output."),
    ] = False,
) -> None:
    """List MCP tools from the daemon read API (:9996 /api/v1/tools).

    The displayed artist_description / artist_label are resolved daemon-side
    from the peer-authored CapabilityDeclaration carry (real summaries/labels
    where present, derived fallback otherwise). discover is a read-API consumer,
    same as the other read commands — a daemon that is not running exits 2.
    """
    # P-01 GUARD — must be FIRST, before any Console() instantiation.
    if as_json:
        try:
            envelope = fetch_raw_envelope("/api/v1/tools")
        except ServerUnreachableError:
            sys.stdout.write(json.dumps(_UNREACHABLE_JSON) + "\n")
            raise typer.Exit(code=2)
        except ServerError as e:
            sys.stdout.write(
                json.dumps({"error": {"code": e.code, "message": e.message}}) + "\n"
            )
            raise typer.Exit(code=1)
        sys.stdout.write(json.dumps(envelope) + "\n")
        return

    console = make_console(no_color=no_color)
    stderr_console = make_console(no_color=no_color, stderr=True)
    try:
        rows = fetch("/api/v1/tools")
    except ServerUnreachableError:
        stderr_console.print(_UNREACHABLE_STDERR)
        raise typer.Exit(code=2)
    except ServerError as e:
        stderr_console.print(f"error: {e.code}: {e.message}")
        raise typer.Exit(code=1)

    rows = sorted(rows, key=lambda row: row.get("name", ""))
    table = Table(box=TOOLS_BOX, header_style=HEADER_STYLE)
    table.add_column("Tool")
    table.add_column("Description")
    table.add_column("Source")
    for row in rows:
        table.add_row(
            row.get("name", ""),
            row.get("artist_description") or "—",
            row.get("origin") or "—",
        )
    console.print(table)


def discover_tool_cmd(
    name: Annotated[str, typer.Argument(help="Tool name, e.g. forge_ping.")],
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON envelope to stdout."),
    ] = False,
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable color output."),
    ] = False,
) -> None:
    """Show one MCP tool's artist description, label, and provenance.

    Reads /api/v1/tools/<name> from the daemon read API. An unknown tool name
    is a 404 → exit 1; a daemon that is not running → exit 2.
    """
    # P-01 GUARD — must be FIRST, before any Console() instantiation.
    if as_json:
        try:
            envelope = fetch_raw_envelope(f"/api/v1/tools/{name}")
        except ServerUnreachableError:
            sys.stdout.write(json.dumps(_UNREACHABLE_JSON) + "\n")
            raise typer.Exit(code=2)
        except ServerError as e:
            sys.stdout.write(
                json.dumps({"error": {"code": e.code, "message": e.message}}) + "\n"
            )
            raise typer.Exit(code=1)
        sys.stdout.write(json.dumps(envelope) + "\n")
        return

    console = make_console(no_color=no_color)
    stderr_console = make_console(no_color=no_color, stderr=True)
    try:
        detail = fetch(f"/api/v1/tools/{name}")
    except ServerUnreachableError:
        stderr_console.print(_UNREACHABLE_STDERR)
        raise typer.Exit(code=2)
    except ServerError as e:
        stderr_console.print(f"error: {e.code}: {e.message}")
        raise typer.Exit(code=1)

    console.print(f"tool: {detail.get('name', name)}")
    if detail.get("artist_label"):
        console.print(f"label: {detail['artist_label']}")
    console.print(f"origin: {detail.get('origin') or '—'}")
    console.print(f"namespace: {detail.get('namespace') or '—'}")
    console.print(f"available: {detail.get('available')!r}")
    console.print("")
    # artist_description is resolved daemon-side, preferring the canonical
    # peer-authored CapabilityDeclaration.summary carry, derived fallback otherwise.
    console.print(detail.get("artist_description") or "(no description)")


def discover_macros_cmd(
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON envelope to stdout."),
    ] = False,
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable color output."),
    ] = False,
) -> None:
    """List user macros from the local macro registry."""
    rows = _macro_records()
    if as_json:
        _emit_json(rows)
        return

    console = make_console(no_color=no_color)
    if not rows:
        console.print("no macros registered")
        return
    table = Table(box=TOOLS_BOX, header_style=HEADER_STYLE)
    table.add_column("Macro")
    table.add_column("Chain expansion")
    for row in rows:
        table.add_row(row["name"], row["chain"])
    console.print(table)


def discover_macro_cmd(
    name: Annotated[str, typer.Argument(help="Macro name.")],
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON envelope to stdout."),
    ] = False,
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable color output."),
    ] = False,
) -> None:
    """Show one macro's full chain expansion."""
    rows = {row["name"]: row for row in _macro_records()}
    detail = rows.get(name)
    if detail is None:
        _not_found("macro", name, as_json)
    if as_json:
        _emit_json(detail)
        return

    console = make_console(no_color=no_color)
    console.print(f"macro: {detail['name']}")
    console.print("")
    console.print(detail["chain"])


def discover_grammar_cmd(
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON envelope to stdout."),
    ] = False,
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable color output."),
    ] = False,
) -> None:
    """Show the chain grammar reference from the parser module docstring."""
    # Lazy import — keep command registration cheap.
    from forge_bridge.console import _chain_parse

    data = {
        "module": _chain_parse.__name__,
        "docstring": _doc(_chain_parse.__doc__),
    }
    if as_json:
        _emit_json(data)
        return

    console = make_console(no_color=no_color)
    console.print(data["docstring"] or "(no grammar docstring)")
