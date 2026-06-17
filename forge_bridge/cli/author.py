"""Manual prompt-authoring CLI commands."""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Annotated

import typer
from rich.table import Table

from forge_bridge.cli.render import HEADER_STYLE, TOOLS_BOX, make_console
from forge_bridge.orchestration import manual_qc


def author_cmd(
    intent: Annotated[
        str,
        typer.Argument(help="Single-beat text intent to author."),
    ],
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON envelope to stdout."),
    ] = False,
) -> None:
    """Author a text prompt and pause the run for manual QC."""

    try:
        result = asyncio.run(manual_qc.start_author(intent))
    except Exception as exc:  # noqa: BLE001 - CLI boundary maps to stable envelope
        _emit_error("author_failed", str(exc), as_json=as_json)
        raise typer.Exit(code=1)

    body = {"ok": True, "data": result.to_dict()}
    if as_json:
        sys.stdout.write(json.dumps(body) + "\n")
        return
    _render_author_result(result.to_dict())


def qc_cmd(
    run_id: Annotated[
        str,
        typer.Argument(help="Run id from a prior `fbridge author` or `fbridge qc`."),
    ],
    note: Annotated[
        str | None,
        typer.Argument(help="QC note for a new attempt. Omit when using --approve."),
    ] = None,
    approve: Annotated[
        bool,
        typer.Option("--approve", help="Approve the run instead of authoring a revision."),
    ] = False,
    actor: Annotated[
        str,
        typer.Option("--actor", help="Human reviewer identity for approval."),
    ] = "operator",
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON envelope to stdout."),
    ] = False,
) -> None:
    """Apply a QC note as a derived authoring run, or approve the current run."""

    if approve and note is not None:
        _emit_error("invalid_args", "omit NOTE when using --approve", as_json=as_json)
        raise typer.Exit(code=1)
    if not approve and not note:
        _emit_error("invalid_args", "NOTE is required unless --approve is set", as_json=as_json)
        raise typer.Exit(code=1)

    try:
        if approve:
            result = asyncio.run(manual_qc.approve(run_id, actor=actor))
            body = {"ok": True, "data": result.to_dict()}
            if as_json:
                sys.stdout.write(json.dumps(body) + "\n")
            else:
                _render_approval(body["data"])
            return

        assert note is not None
        result = asyncio.run(manual_qc.revise(run_id, note))
    except ValueError as exc:
        _emit_error("invalid_args", str(exc), as_json=as_json)
        raise typer.Exit(code=1)
    except Exception as exc:  # noqa: BLE001 - CLI boundary maps to stable envelope
        _emit_error("qc_failed", str(exc), as_json=as_json)
        raise typer.Exit(code=1)

    body = {"ok": True, "data": result.to_dict()}
    if as_json:
        sys.stdout.write(json.dumps(body) + "\n")
        return
    _render_author_result(result.to_dict())


def _emit_error(code: str, message: str, *, as_json: bool) -> None:
    body = {"ok": False, "error": {"code": code, "message": message}}
    if as_json:
        sys.stdout.write(json.dumps(body) + "\n")
        return
    sys.stderr.write(f"{code}: {message}\n")


def _render_author_result(data: dict) -> None:
    console = make_console()
    table = Table(box=TOOLS_BOX, header_style=HEADER_STYLE)
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("run_id", str(data["run_id"]))
    table.add_row("artifact_id", str(data["artifact_id"]))
    table.add_row("status", f"{data['lifecycle_stage']}/{data['lifecycle_status']}")
    console.print(table)
    console.print(str(data.get("text") or ""))


def _render_approval(data: dict) -> None:
    console = make_console()
    table = Table(box=TOOLS_BOX, header_style=HEADER_STYLE)
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("run_id", str(data["run_id"]))
    table.add_row("status", f"{data['lifecycle_stage']}/{data['lifecycle_status']}")
    console.print(table)
