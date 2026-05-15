"""forge-bridge flame-exec — operator-side surface onto the Flame execution substrate.

A second operator surface onto the SAME execution path the LLM tool-call
surface (``flame_execute_python``) uses. Not a second execution substrate —
the CLI delegates into ``_execute_python_core`` directly. One execution
path, one observability path, one graph emission path, one error-shaping
path, one operational truth.

Architectural payoff per operator framing 2026-05-15: every LLM execution
failure now has a human-operable reproducer. Operator takes the salvaged
python + the graph_id + the traceback and replays the exact execution
through the same substrate. Observable → operable.

Scope discipline:

- Thin: collect args → call shared substrate → render output → map exit codes.
- No retry semantics.
- No direct HTTP implementation (delegates through bridge.execute).
- No graph-specific logic at the CLI layer (graph_id is metadata, surfaced
  in output; no "view graph with..." hints — graph surfaces are composable).
- No stdin piping at v1.6.0 (TTY ambiguity, blocking semantics, accidental
  giant payloads). Inline ``code`` arg or ``-f path.py`` only.
- node_kind stays ``"python"`` — operator surface is metadata, not ontology.

Exit codes:
    0 = execution success (Flame returned cleanly, no error)
    1 = Flame execution failure (resp.error set; traceback rendered)
    2 = transport / unreachable (Flame bridge not responding)
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer

from forge_bridge.bridge import BridgeConnectionError
from forge_bridge.cli.render import make_console
from forge_bridge.runtime.graph_emit import new_graph_id
from forge_bridge.tools.utility import _execute_python_core


def flame_exec_cmd(
    code: Annotated[
        Optional[str],
        typer.Argument(
            help="Python code to execute inside Flame (inline). Use -f to read "
            "from a file instead.",
        ),
    ] = None,
    file: Annotated[
        Optional[Path],
        typer.Option(
            "-f",
            "--file",
            help="Read Python code from a file instead of the inline argument.",
        ),
    ] = None,
    main_thread: Annotated[
        bool,
        typer.Option(
            "--main-thread",
            help="Execute on Flame's Qt main thread (required for write operations).",
        ),
    ] = False,
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON envelope to stdout."),
    ] = False,
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable color output."),
    ] = False,
) -> None:
    """Execute Python inside Flame through the shared substrate."""
    code_text = _resolve_code(code, file, as_json=as_json)
    graph_id = new_graph_id()

    try:
        result_json = asyncio.run(
            _execute_python_core(code_text, main_thread, graph_id)
        )
    except BridgeConnectionError as exc:
        _emit_transport_error(exc, graph_id, as_json=as_json)
        raise typer.Exit(code=2)
    except Exception as exc:  # noqa: BLE001 — operator surface should never traceback
        # Any non-transport unexpected exception is treated as transport-shape
        # at the CLI boundary (we don't know how to render an arbitrary
        # exception cleanly). The full traceback is still preserved in the
        # graph_emit event (status="transport_error"); the CLI prints a
        # short message.
        _emit_transport_error(exc, graph_id, as_json=as_json)
        raise typer.Exit(code=2)

    result = json.loads(result_json)
    flame_failed = bool(result.get("error"))
    _render_result(
        result,
        graph_id=graph_id,
        flame_failed=flame_failed,
        as_json=as_json,
        no_color=no_color,
    )
    raise typer.Exit(code=1 if flame_failed else 0)


# ── helpers ────────────────────────────────────────────────────────────────


def _resolve_code(
    code: Optional[str],
    file: Optional[Path],
    *,
    as_json: bool,
) -> str:
    """Pick inline or file source. Exactly one must be supplied."""
    if code is None and file is None:
        _emit_usage_error(
            "either a code argument or -f/--file must be provided",
            as_json=as_json,
        )
        raise typer.Exit(code=1)
    if code is not None and file is not None:
        _emit_usage_error(
            "code argument and -f/--file are mutually exclusive",
            as_json=as_json,
        )
        raise typer.Exit(code=1)
    if file is not None:
        try:
            return file.read_text(encoding="utf-8")
        except OSError as exc:
            _emit_usage_error(
                f"could not read code file {file}: {type(exc).__name__}",
                as_json=as_json,
            )
            raise typer.Exit(code=1)
    return code or ""


def _emit_usage_error(message: str, *, as_json: bool) -> None:
    if as_json:
        sys.stdout.write(
            json.dumps({"error": {"code": "usage", "message": message}}) + "\n"
        )
        return
    sys.stderr.write(f"forge-bridge flame-exec: {message}\n")


def _emit_transport_error(
    exc: BaseException,
    graph_id: str,
    *,
    as_json: bool,
) -> None:
    message = f"{type(exc).__name__}: {exc}"
    if as_json:
        sys.stdout.write(
            json.dumps(
                {
                    "error": {
                        "code": "flame_unreachable",
                        "message": message,
                        "graph_id": graph_id,
                    }
                }
            )
            + "\n"
        )
        return
    sys.stderr.write(
        f"forge-bridge flame-exec: Flame bridge unreachable — {message}\n"
        f"graph_id: {graph_id}\n"
    )


def _render_result(
    result: dict,
    *,
    graph_id: str,
    flame_failed: bool,
    as_json: bool,
    no_color: bool,
) -> None:
    if as_json:
        envelope = {
            "data": {
                "graph_id": graph_id,
                "status": "flame_error" if flame_failed else "ok",
                "stdout": result.get("stdout", ""),
                "stderr": result.get("stderr", ""),
                "result": result.get("result"),
                "error": result.get("error"),
                "traceback": result.get("traceback"),
            }
        }
        sys.stdout.write(json.dumps(envelope) + "\n")
        return

    console = make_console(no_color=no_color)
    console.print(f"graph_id {graph_id}")
    console.print(f"status   {'flame_error' if flame_failed else 'ok'}")
    console.print("")

    stdout = result.get("stdout") or ""
    stderr = result.get("stderr") or ""
    if stdout:
        sys.stdout.write(stdout)
        if not stdout.endswith("\n"):
            sys.stdout.write("\n")
    if stderr:
        sys.stderr.write(stderr)
        if not stderr.endswith("\n"):
            sys.stderr.write("\n")

    if flame_failed:
        console.print(f"error: {result.get('error')}", style="red", highlight=False)
        traceback = result.get("traceback") or ""
        if traceback:
            console.print("traceback:", style="red", highlight=False)
            sys.stderr.write(traceback)
            if not traceback.endswith("\n"):
                sys.stderr.write("\n")
