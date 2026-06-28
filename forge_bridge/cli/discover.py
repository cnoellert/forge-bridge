"""fbridge discover — substrate-derived operator vocabulary introspection.

Thread B / B-1: enumerate what the substrate already knows about its
operator vocabulary. This surface is intentionally derived from live
registries and docstrings: graph primitive predicates, MCP tool records,
macro registry, and chain parser module documentation.
"""
from __future__ import annotations

import asyncio
import importlib
import inspect
import json
import re
import sys
from typing import Annotated, Any

import typer
from rich.table import Table

from forge_bridge.cli.render import HEADER_STYLE, TOOLS_BOX, make_console


_PRIMITIVE_RE = re.compile(r"^is_(?P<name>.+)_step$")


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


async def _list_mcp_tools() -> list[Any]:
    # Lazy import — importing the MCP server registers builtins and pulls in
    # Flame/tool modules. Keep `fbridge --help` and unrelated commands quick.
    from forge_bridge.mcp import server as _server

    return await _server.mcp.list_tools()


def _annotation_value(annotations: Any, name: str) -> Any:
    if annotations is None:
        return None
    return getattr(annotations, name, None)


def _tool_record(tool: Any) -> dict[str, Any]:
    # Lazy — keeps `fbridge --help` off the forge_contracts import path. By the
    # time records are built the heavy MCP-server import has already run.
    from forge_bridge.orchestration.registration import artist_description

    meta = getattr(tool, "meta", None) or {}
    annotations = getattr(tool, "annotations", None)
    description = _doc(getattr(tool, "description", ""))
    name = getattr(tool, "name", "")
    # Description seam: the ONE canonical artist description is the peer-authored
    # CapabilityDeclaration.summary, which the registration path carries onto
    # ToolRegistration.summary. discover reads MCP-tool *meta* — a DIFFERENT,
    # structurally-disconnected source (nothing copies declaration.summary into
    # tool meta). Reading a parallel meta["summary"] here would stand up a
    # competing second author that can diverge from the declaration, so discover
    # does NOT: it resolves with summary=None → a clearly-subordinate derived
    # fallback (docstring first line / humanized name). discover will surface the
    # canonical summary once it can read ToolRegistration.
    return {
        "name": name,
        "description": description,
        "artist_description": artist_description(
            summary=None, operator_id=name, fallback_doc=description
        ),
        "annotations": {
            "title": _annotation_value(annotations, "title"),
            "readOnlyHint": _annotation_value(annotations, "readOnlyHint"),
            "idempotentHint": _annotation_value(annotations, "idempotentHint"),
        },
        "_source": meta.get("_source", ""),
    }


def _tool_records() -> list[dict[str, Any]]:
    tools = asyncio.run(_list_mcp_tools())
    return sorted((_tool_record(tool) for tool in tools), key=lambda row: row["name"])


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
    """List MCP tools from the in-process FastMCP registry."""
    rows = _tool_records()
    if as_json:
        _emit_json(rows)
        return

    console = make_console(no_color=no_color)
    table = Table(box=TOOLS_BOX, header_style=HEADER_STYLE)
    table.add_column("Tool")
    table.add_column("Description")
    table.add_column("Source")
    for row in rows:
        table.add_row(
            row["name"],
            row.get("artist_description") or "—",
            row.get("_source") or "—",
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
    """Show one MCP tool's description, annotations, and provenance."""
    rows = {row["name"]: row for row in _tool_records()}
    detail = rows.get(name)
    if detail is None:
        _not_found("tool", name, as_json)
    if as_json:
        _emit_json(detail)
        return

    annotations = detail["annotations"]
    console = make_console(no_color=no_color)
    console.print(f"tool: {detail['name']}")
    console.print(f"_source: {detail.get('_source') or '—'}")
    console.print(
        "annotations: "
        f"title={annotations.get('title')!r}, "
        f"readOnlyHint={annotations.get('readOnlyHint')!r}, "
        f"idempotentHint={annotations.get('idempotentHint')!r}"
    )
    console.print("")
    # discover surfaces the derived ``artist_description`` (subordinate fallback);
    # the canonical peer-authored summary lives on ToolRegistration.summary and is
    # not yet reachable from this MCP-tool-meta surface (see _tool_record).
    if detail.get("artist_description"):
        console.print(f"description: {detail['artist_description']}")
        console.print("")
    console.print(detail["description"] or "(no description)")


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
