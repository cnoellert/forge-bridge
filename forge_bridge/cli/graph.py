"""forge-bridge graph — read-only debug surface for Phase 24 proto-node records.

Closes ``v1.6-PHASE-24-CONVERGENCE.md`` §2.4 (the emitted records must be
structurally useful) by shipping a minimum consumer of the JSONL stream that
``forge_bridge.runtime.graph_emit`` writes. Also addresses ``v1.6-WRITERS-ROOM-CONVERGENCE.md``
Q20 (minimal ``fbridge graph list/show`` debug CLI; documented as debug
surface, not a product surface).

Scope discipline:

- ``list`` enumerates the per-graph JSONL files in ``FORGE_GRAPH_DIR``
  (default ``~/.forge-bridge/graphs/``), one row per graph, sorted by file
  mtime newest-first.
- ``show <graph_id>`` dumps every record in the matching file, in append order.

Out of scope (per ``v1.6-PHASE-24-CONVERGENCE.md`` §3):

- No projection/replay-fold of status into a derived current state — the
  substrate is append-only event records; consumers are free to project but
  this debug surface stays raw.
- No graph-shape rendering. That's the schematic surface (deferred).
- No promotion / mining. That's v1.6.x+.
- No write side (no rotation, no delete, no edit). Read-only.

The surface is intentionally generic: every record has ``graph_id``,
``node_kind``, ``status``, ``timestamp``, ``payload``. No node_kind-specific
formatting — that's a Phase 24+1 convergence (per §5.4 payload is
discovery-shaped, not pre-committed).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated, Any, Optional

import typer
from rich.table import Table

from forge_bridge.cli.render import HEADER_STYLE, TOOLS_BOX, make_console, status_chip
from forge_bridge.runtime.graph_emit import graph_dir

_DEFAULT_LIST_LIMIT = 20


# ── helpers ───────────────────────────────────────────────────────────────


def _safe_load_records(path: Path) -> list[dict[str, Any]]:
    """Read a graph JSONL file; skip blank lines and malformed records.

    Malformed records (non-JSON or non-dict) are silently dropped — this is a
    debug surface, not an integrity check. ``fbridge doctor`` Q18 is the
    place to surface structural problems.
    """
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(rec, dict):
                records.append(rec)
    return records


def _summarize(path: Path) -> dict[str, Any]:
    """Return a single-row summary for ``list``: counts + first/last metadata."""
    records = _safe_load_records(path)
    graph_id = path.stem
    if not records:
        return {
            "graph_id": graph_id,
            "record_count": 0,
            "first_node_kind": "",
            "first_status": "",
            "last_status": "",
            "last_timestamp": "",
            "mtime": path.stat().st_mtime if path.exists() else 0.0,
        }
    first = records[0]
    last = records[-1]
    return {
        "graph_id": graph_id,
        "record_count": len(records),
        "first_node_kind": first.get("node_kind", ""),
        "first_status": first.get("status", ""),
        "last_status": last.get("status", ""),
        "last_timestamp": last.get("timestamp", ""),
        "mtime": path.stat().st_mtime,
    }


# ── list ──────────────────────────────────────────────────────────────────


_GRAPH_LIST_EPILOG = """\
Examples:
  fbridge graph list                List recent graph sessions (newest first).
  fbridge graph list --limit 50     Show up to 50 sessions instead of 20.
  fbridge graph list --json         Stable JSON envelope.

What this shows:
  Every per-graph JSONL file in the graph dir (default
  ~/.forge-bridge/graphs/, override via FORGE_GRAPH_DIR). One row per
  graph_id, sorted by file mtime, newest first.
"""


def graph_list_cmd(
    limit: Annotated[
        int,
        typer.Option("--limit", help="Maximum graphs to list (default 20)."),
    ] = _DEFAULT_LIST_LIMIT,
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON envelope to stdout."),
    ] = False,
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable color output."),
    ] = False,
) -> None:
    """List recent graph sessions in the JSONL graph store."""
    target = graph_dir()
    if not target.exists():
        if as_json:
            sys.stdout.write(json.dumps({"data": [], "graph_dir": str(target)}) + "\n")
            return
        sys.stdout.write(f"graph dir: {target} (not yet created)\n")
        sys.stdout.write("no graphs recorded\n")
        return

    files = sorted(
        target.glob("*.jsonl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    rows = [_summarize(p) for p in files[:limit]]

    if as_json:
        sys.stdout.write(
            json.dumps({"data": rows, "graph_dir": str(target)}) + "\n"
        )
        return

    if not rows:
        sys.stdout.write(f"graph dir: {target}\n")
        sys.stdout.write("no graphs recorded\n")
        return

    console = make_console(no_color=no_color)
    table = Table(box=TOOLS_BOX, header_style=HEADER_STYLE)
    table.add_column("Graph ID")
    table.add_column("Records", justify="right")
    table.add_column("Kind")
    table.add_column("Last status")
    table.add_column("Last seen")
    for row in rows:
        table.add_row(
            row["graph_id"][:12],
            str(row["record_count"]),
            row["first_node_kind"] or "—",
            status_chip(_chip_for_status(row["last_status"])) if row["last_status"] else "—",
            row["last_timestamp"] or "—",
        )
    console.print(table)
    console.print(f"graph dir: {target}")


def _chip_for_status(status: str) -> str:
    """Map producer-conventional status keywords to the render.status_chip palette.

    Phase 24 producer surfaces emit ``started``/``completed``/``failed``/
    ``transport_error``. Map them onto the existing chip vocabulary
    (``ok``/``fail``/``warn``/``loaded``) without introducing new colors.
    """
    if status in ("completed", "ok"):
        return "ok"
    if status in ("failed", "error", "transport_error"):
        return "fail"
    if status in ("started", "created", "in_progress"):
        return "loaded"
    return status


# ── show ──────────────────────────────────────────────────────────────────


_GRAPH_SHOW_EPILOG = """\
Examples:
  fbridge graph show 0b0f27a10fcc4a2c93e8cd5f7c1033ee
  fbridge graph show 0b0f27a1                          # prefix match
  fbridge graph show <id> --json                       # stable JSON envelope

What this shows:
  Every JSONL record in <FORGE_GRAPH_DIR>/<graph_id>.jsonl, in append order.
  Use `fbridge graph list` to find graph_ids.

Exit codes:
  0  graph found and rendered                          1  prefix matched > 1 graph
  2  graph not found
"""


def graph_show_cmd(
    graph_id: Annotated[
        str,
        typer.Argument(help="Graph ID (full or unique prefix)."),
    ],
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON envelope to stdout."),
    ] = False,
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable color output."),
    ] = False,
) -> None:
    """Dump every event record in one graph's JSONL file."""
    target = graph_dir()
    path = _resolve_graph_path(target, graph_id, as_json=as_json)
    records = _safe_load_records(path)

    if as_json:
        sys.stdout.write(
            json.dumps({"data": records, "graph_id": path.stem, "path": str(path)})
            + "\n"
        )
        return

    console = make_console(no_color=no_color)
    if not records:
        console.print(f"graph: {path.stem}")
        console.print(f"file:  {path}")
        console.print("no records (empty or malformed JSONL)")
        return

    console.print(f"graph: {path.stem}")
    console.print(f"file:  {path}")
    console.print(f"records: {len(records)}")
    console.print("")
    for rec in records:
        ts = rec.get("timestamp", "")
        kind = rec.get("node_kind", "")
        status = rec.get("status", "")
        event_id = rec.get("event_id", "")[:8]
        chip = status_chip(_chip_for_status(status)) if status else "—"
        console.print(f"{ts}  {kind:<22} ", chip, f"  event={event_id}")
        payload = rec.get("payload") or {}
        if payload:
            console.print(
                "  payload: " + json.dumps(payload, separators=(", ", ": "))
            )


def _resolve_graph_path(
    target: Path,
    requested: str,
    *,
    as_json: bool,
) -> Path:
    """Resolve a graph_id (full or unique prefix) to a JSONL path.

    Exits with the documented exit codes on missing / ambiguous matches.
    """
    if not target.exists():
        _emit_missing(target, requested, as_json=as_json)
        raise typer.Exit(code=2)

    exact = target / f"{requested}.jsonl"
    if exact.exists():
        return exact

    candidates = sorted(target.glob(f"{requested}*.jsonl"))
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        _emit_ambiguous(candidates, requested, as_json=as_json)
        raise typer.Exit(code=1)

    _emit_missing(target, requested, as_json=as_json)
    raise typer.Exit(code=2)


def _emit_missing(target: Path, requested: str, *, as_json: bool) -> None:
    if as_json:
        sys.stdout.write(
            json.dumps(
                {
                    "error": {
                        "code": "graph_not_found",
                        "message": f"no graph matched '{requested}' in {target}",
                    }
                }
            )
            + "\n"
        )
        return
    sys.stderr.write(
        f"forge-bridge graph: no graph matched '{requested}' in {target}\n"
        "Run `fbridge graph list` to see available graph_ids.\n"
    )


def _emit_ambiguous(
    candidates: list[Path], requested: str, *, as_json: bool
) -> None:
    matched = [p.stem for p in candidates]
    if as_json:
        sys.stdout.write(
            json.dumps(
                {
                    "error": {
                        "code": "graph_ambiguous",
                        "message": f"prefix '{requested}' matched {len(matched)} graphs",
                        "matches": matched,
                    }
                }
            )
            + "\n"
        )
        return
    sys.stderr.write(
        f"forge-bridge graph: prefix '{requested}' matched {len(matched)} graphs:\n"
    )
    for m in matched:
        sys.stderr.write(f"  {m}\n")
    sys.stderr.write("Provide a longer prefix or the full graph_id.\n")


__all__ = [
    "graph_list_cmd",
    "graph_show_cmd",
    "_GRAPH_LIST_EPILOG",
    "_GRAPH_SHOW_EPILOG",
]
