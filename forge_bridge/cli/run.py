"""forge-bridge run — execute a registered tool by exact name.

Discovery uses the in-process FastMCP singleton's ``list_tools()``;
execution dispatches to ``mcp.call_tool`` directly so we receive the raw
``(content_blocks, structured_dict)`` shape instead of the string flattening
that ``forge_bridge.mcp.registry.invoke_tool`` produces (its string form is
the right contract for the LLM router but leaks tuple reprs to humans).

PR7 / PR7.1 scope: exact-match lookup, no args, no fuzzy matching, no new
HTTP routes. MCP server, registry, and ``invoke_tool`` are untouched.
"""
from __future__ import annotations

import asyncio
import json
import sys
from typing import Annotated, Any

import typer

# Exit codes — match sibling CLIs.
_EXIT_OK = 0
_EXIT_FAIL = 1
_EXIT_UNKNOWN_ACTION = 1


class _UnknownAction(Exception):
    def __init__(self, name: str, available: list[str]):
        self.name = name
        self.available = available
        super().__init__(name)


async def _lookup_and_call(name: str) -> Any:
    # Lazy import — pulling in mcp.server triggers register_builtins() and
    # flame tool imports. Keeps `fbridge --help` fast.
    from forge_bridge.mcp import server as _server

    available = await _server.mcp.list_tools()
    names = sorted(t.name for t in available)
    if name not in names:
        raise _UnknownAction(name, names)
    return await _server.mcp.call_tool(name, arguments={})


def _extract(raw: Any) -> Any:
    """Pull the structured value out of a FastMCP call_tool return.

    Handles three shapes:
      - ``(content_blocks, structured_dict)`` — emitted when the tool has an
        output schema. Prefer ``structured["result"]`` (FastMCP's wrap_output
        convention) and JSON-decode it when it's a string.
      - ``list[ContentBlock]`` — no schema; concatenate text and try to parse
        as JSON for richer rendering downstream.
      - anything else — pass through.
    """
    if isinstance(raw, tuple) and len(raw) == 2:
        _, structured = raw
        if isinstance(structured, dict):
            inner = structured.get("result", structured)
            if isinstance(inner, str):
                try:
                    return json.loads(inner)
                except (ValueError, TypeError):
                    return inner
            return inner
    if isinstance(raw, list):
        text = "".join(getattr(b, "text", "") or "" for b in raw)
        if text:
            try:
                return json.loads(text)
            except (ValueError, TypeError):
                return text
        return None
    return raw


def _render_human(value: Any) -> str:
    if value is None or value == "" or value == [] or value == {}:
        return "No output"
    if isinstance(value, dict):
        return "\n".join(f"{k}: {v}" for k, v in value.items())
    return str(value)


def run_cmd(
    action: Annotated[
        str,
        typer.Argument(help="Exact name of the registered tool to execute."),
    ],
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit a stable JSON envelope to stdout."),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show timing on stderr."),
    ] = False,
) -> None:
    """Execute a registered action by exact name."""
    import time

    started = time.monotonic()
    try:
        raw = asyncio.run(_lookup_and_call(action))
    except _UnknownAction as exc:
        if as_json:
            sys.stdout.write(
                json.dumps({
                    "ok": False,
                    "action": exc.name,
                    "error": {
                        "code": "unknown_action",
                        "message": f"Unknown action: {exc.name}",
                        "fix": "list registered tools with `fbridge actions`",
                    },
                }) + "\n"
            )
        else:
            sys.stderr.write(f"Unknown action: {exc.name}\n")
            sys.stderr.write("Run `fbridge actions` to list registered tools.\n")
        raise typer.Exit(code=_EXIT_UNKNOWN_ACTION)
    except Exception as exc:
        kind = type(exc).__name__
        message = str(exc) or kind
        if as_json:
            sys.stdout.write(
                json.dumps({
                    "ok": False,
                    "action": action,
                    "error": {"code": "execution_failed", "message": message},
                }) + "\n"
            )
        else:
            sys.stderr.write(f"forge-bridge run: {kind}: {message}\n")
        raise typer.Exit(code=_EXIT_FAIL)

    elapsed = time.monotonic() - started
    value = _extract(raw)

    if as_json:
        sys.stdout.write(
            json.dumps(
                {"ok": True, "action": action, "result": value},
                default=str,
            ) + "\n"
        )
        return

    if verbose:
        sys.stderr.write(f"[run] {action} ok ({elapsed:.2f}s)\n")
    rendered = _render_human(value)
    sys.stdout.write(rendered + ("\n" if not rendered.endswith("\n") else ""))
