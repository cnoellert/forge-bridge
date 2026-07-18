"""Manual prompt-authoring CLI commands."""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Annotated

import typer
from rich.table import Table

from forge_bridge.cli.render import HEADER_STYLE, TOOLS_BOX, make_console
from forge_bridge.orchestration import generation_review, manual_qc
from forge_bridge.orchestration.authoring_targets import (
    discover_authoring_target_options,
)


def author_cmd(
    intent: Annotated[
        str,
        typer.Argument(help="Single-beat text intent to author."),
    ],
    target_operator: Annotated[
        str | None,
        typer.Option(
            "--target-operator",
            help="Downstream generation operator this prompt is authored for.",
        ),
    ] = None,
    target_backend: Annotated[
        str | None,
        typer.Option(
            "--target-backend",
            help="Exact discovered backend id; required when the operator is ambiguous.",
        ),
    ] = None,
    from_approved_generation: Annotated[
        str | None,
        typer.Option(
            "--from-approved-generation",
            help="Author image-to-video motion from this human-approved still artifact.",
        ),
    ] = None,
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON envelope to stdout."),
    ] = False,
) -> None:
    """Author a text prompt and pause the run for manual QC."""

    if (
        target_backend is not None
        and target_operator is None
        and from_approved_generation is None
    ):
        _emit_error(
            "invalid_args",
            "--target-backend requires --target-operator",
            as_json=as_json,
        )
        raise typer.Exit(code=1)
    if (
        from_approved_generation is not None
        and target_operator is not None
        and target_operator != generation_review.VIDEO_FROM_IMAGE_OPERATOR
    ):
        _emit_error(
            "invalid_args",
            "--from-approved-generation requires generate_video_from_image",
            as_json=as_json,
        )
        raise typer.Exit(code=1)

    kwargs = {}
    if target_operator is not None:
        kwargs["target_operator"] = target_operator
    if target_backend is not None:
        kwargs["target_backend"] = target_backend

    try:
        if from_approved_generation is not None:
            result = asyncio.run(
                generation_review.start_conditioned_video_author(
                    intent,
                    from_approved_generation,
                    target_backend=target_backend,
                )
            )
        else:
            result = asyncio.run(manual_qc.start_author(intent, **kwargs))
    except Exception as exc:  # noqa: BLE001 - CLI boundary maps to stable envelope
        _emit_error("author_failed", str(exc), as_json=as_json)
        raise typer.Exit(code=1)

    body = {"ok": True, "data": result.to_dict()}
    if as_json:
        sys.stdout.write(json.dumps(body) + "\n")
        return
    _render_author_result(result.to_dict())


def generation_qc_cmd(
    generation_artifact_id: Annotated[
        str,
        typer.Argument(help="Terminal generated artifact id to review."),
    ],
    note: Annotated[
        str | None,
        typer.Argument(help="Visual correction note. Omit when using --approve."),
    ] = None,
    approve: Annotated[
        bool,
        typer.Option("--approve", help="Approve the artifact for downstream use."),
    ] = False,
    actor: Annotated[
        str,
        typer.Option("--actor", help="Human reviewer identity."),
    ] = "operator",
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON envelope to stdout."),
    ] = False,
) -> None:
    """Record one human visual decision for a terminal generation artifact."""

    if approve and note is not None:
        _emit_error("invalid_args", "omit NOTE when using --approve", as_json=as_json)
        raise typer.Exit(code=1)
    if not approve and not note:
        _emit_error("invalid_args", "NOTE is required unless --approve is set", as_json=as_json)
        raise typer.Exit(code=1)

    try:
        result = asyncio.run(
            generation_review.review_generation(
                generation_artifact_id,
                note=note,
                approve=approve,
                actor=actor,
            )
        )
    except ValueError as exc:
        _emit_error("invalid_args", str(exc), as_json=as_json)
        raise typer.Exit(code=1)
    except Exception as exc:  # noqa: BLE001 - CLI boundary maps to stable envelope
        _emit_error("generation_qc_failed", str(exc), as_json=as_json)
        raise typer.Exit(code=1)

    body = {"ok": True, "data": result.to_dict()}
    if as_json:
        sys.stdout.write(json.dumps(body) + "\n")
        return
    _render_generation_review(body["data"])


def author_targets_cmd(
    operator: Annotated[
        str | None,
        typer.Option("--operator", help="Filter targets by generation operator id."),
    ] = None,
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON envelope to stdout."),
    ] = False,
) -> None:
    """List discovered downstream targets available for prompt authoring."""

    try:
        options = asyncio.run(discover_authoring_target_options(operator_id=operator))
    except Exception as exc:  # noqa: BLE001 - CLI boundary maps to stable envelope
        _emit_error("target_discovery_failed", str(exc), as_json=as_json)
        raise typer.Exit(code=1)

    rows = [option.to_dict() for option in options]
    body = {"ok": True, "data": {"targets": rows, "count": len(rows)}}
    if as_json:
        sys.stdout.write(json.dumps(body) + "\n")
        return

    console = make_console()
    table = Table(box=TOOLS_BOX, header_style=HEADER_STYLE)
    table.add_column("Operator")
    table.add_column("Backend")
    table.add_column("Description")
    for row in rows:
        target = row["target"]
        table.add_row(
            str(target["operator_id"]),
            str(row["backend_id"]),
            str(row.get("summary") or row.get("label") or ""),
        )
    console.print(table)


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


def author_make_cmd(
    source_artifact_id: Annotated[
        str,
        typer.Argument(help="Approved author artifact id from `fbridge author` or `qc`."),
    ],
    grant_id: Annotated[
        str,
        typer.Argument(help="Ratified generation-grant handle for the persisted target."),
    ],
    inputs_json: Annotated[
        str | None,
        typer.Option(
            "--inputs-json",
            help="Optional JSON object with `scalars` and/or `references`.",
        ),
    ] = None,
    idempotency_key: Annotated[
        str | None,
        typer.Option(
            "--idempotency-key",
            help="Explicit retry identity; defaults to one make per author artifact.",
        ),
    ] = None,
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON envelope to stdout."),
    ] = False,
) -> None:
    """Submit an approved prompt to its persisted exact generation target."""

    try:
        inputs = json.loads(inputs_json) if inputs_json is not None else {}
        if not isinstance(inputs, dict):
            raise ValueError("--inputs-json must decode to an object")
        unknown = set(inputs) - {"scalars", "references"}
        if unknown:
            raise ValueError(
                "--inputs-json supports only `scalars` and `references`; "
                f"got {sorted(unknown)}"
            )
        scalars = inputs.get("scalars")
        references = inputs.get("references")
        if scalars is not None and not isinstance(scalars, dict):
            raise ValueError("inputs.scalars must be an object")
        if references is not None and not isinstance(references, list):
            raise ValueError("inputs.references must be an array")
    except (json.JSONDecodeError, ValueError) as exc:
        _emit_error("invalid_args", str(exc), as_json=as_json)
        raise typer.Exit(code=1)

    try:
        result = asyncio.run(
            manual_qc.make_approved(
                source_artifact_id,
                grant_id,
                scalars=scalars,
                references=references,
                idempotency_key=idempotency_key,
            )
        )
    except ValueError as exc:
        _emit_error("invalid_args", str(exc), as_json=as_json)
        raise typer.Exit(code=1)
    except Exception as exc:  # noqa: BLE001 - CLI boundary maps to stable envelope
        _emit_error("author_make_failed", str(exc), as_json=as_json)
        raise typer.Exit(code=1)

    body = {"ok": result.status == "submitted", "data": result.to_dict()}
    if as_json:
        sys.stdout.write(json.dumps(body) + "\n")
        if not body["ok"]:
            raise typer.Exit(code=1)
        return
    _render_make_result(body["data"])
    if not body["ok"]:
        raise typer.Exit(code=1)


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


def _render_make_result(data: dict) -> None:
    console = make_console()
    table = Table(box=TOOLS_BOX, header_style=HEADER_STYLE)
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("source_run_id", str(data["source_run_id"]))
    table.add_row("source_artifact_id", str(data["source_artifact_id"]))
    table.add_row("target", str(data["operator_id"]))
    table.add_row("artifact_id", str(data.get("artifact_id") or ""))
    table.add_row("status", str(data["status"]))
    if data.get("refusal_code"):
        table.add_row("refusal_code", str(data["refusal_code"]))
    if data.get("poll_with"):
        table.add_row("poll_with", str(data["poll_with"]))
    console.print(table)


def _render_generation_review(data: dict) -> None:
    console = make_console()
    table = Table(box=TOOLS_BOX, header_style=HEADER_STYLE)
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("generation_artifact_id", str(data["generation_artifact_id"]))
    table.add_row("decision", str(data["decision"]))
    table.add_row("actor", str(data["actor"]))
    if data.get("revised_run_id"):
        table.add_row("revised_run_id", str(data["revised_run_id"]))
    if data.get("revised_author_artifact_id"):
        table.add_row(
            "revised_author_artifact_id",
            str(data["revised_author_artifact_id"]),
        )
    console.print(table)
