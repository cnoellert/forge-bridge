"""`fbridge exec` interactive mode — the first renderer of the verb registry.

Bootstraps the engine once, then runs a small REPL: pick a verb (slash-command
or name), fill a couple of plain-language values (segments are PICKED from the
live timeline, not typed — identity is resolved behind the glass), see a
domain-language preview, confirm, apply. Confirmation IS the ratification act:
preview runs with no assent (fail-closed), [y] runs the same graph with a
ratified AssentRecord. Mutations never bypass the preview->ratify->apply rail.

The legacy ``fbridge exec "<chain string>"`` lane is untouched; this is the
no-argument lane. ponytail: in-process bootstrap (one cost at launch) beats a
new daemon route + restart for the first cut; promote to a thin HTTP client to
a daemon verb-endpoint if multiple surfaces need it.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from rich.prompt import Prompt, IntPrompt, Confirm

from forge_bridge.cli import verbs as _verbs
from forge_bridge.cli.render import make_console


def _held_manifest(results: dict[str, Any]) -> dict[str, Any] | None:
    for r in results.values():
        out = getattr(r, "output", None)
        if isinstance(out, dict) and "apply_counterpart" in out:
            return out
    return None


def _node_error(results: dict[str, Any]) -> tuple[str, str] | None:
    # surface the first fail-closed reason (e.g. UNRESOLVED_TARGET) for legibility
    for nid, r in results.items():
        if str(getattr(r.status, "value", r.status)) == "error" and nid != "commit":
            return nid, str(getattr(r, "reason_code", "") or getattr(r, "message", ""))
    return None


def _commit_applied(results: dict[str, Any]) -> dict[str, Any] | None:
    for r in results.values():
        out = getattr(r, "output", None)
        if isinstance(out, dict) and out.get("type") == "commit_applied":
            return out
    return None


async def _segments(sequence_name: str) -> list[dict[str, Any]]:
    from forge_bridge.tools.timeline import GetSegmentsInput, get_sequence_segments
    raw = await get_sequence_segments(GetSegmentsInput(sequence_name=sequence_name))
    data = json.loads(raw) if isinstance(raw, str) else raw
    segs = data.get("segments") if isinstance(data, dict) else None
    return segs if isinstance(segs, list) else []


def _ratified_assent() -> Any:
    from forge_bridge.core.assent import AssentRecord
    return AssentRecord(
        graph_intent_id="fbridge-exec-interactive",
        chain_steps=["delta_to_manifest", "commit"],
        status="ratified",
        decided_by="fbridge-exec",
        decided_at=datetime.now(timezone.utc),
        metadata={"surface": "exec-interactive"},
    )


async def _preview_rename(
    sequence: str, seg: dict[str, Any], new_name: str
) -> tuple[dict[str, Any] | None, tuple[str, str] | None]:
    """Resolve the held mutation manifest for a rename (NO assent, no mutation).

    Returns (held_manifest, None) on success, or (None, (where, why)) for a
    fail-closed reason (e.g. UNRESOLVED_TARGET).
    """
    from forge_bridge.orchestration.apply_editorial_delta import preview_editorial_delta
    delta = _verbs.build_rename_delta(
        {"sequence_name": sequence, "segment": seg, "new_name": new_name}
    )
    spec = _verbs.build_host_mutation_spec(delta, _verbs.host_resolve_operator())
    results = await preview_editorial_delta(spec)
    err = _node_error(results)
    if err is not None:
        return None, err
    held = _held_manifest(results)
    if held is None:
        return None, ("preview", "no mutation manifest")
    return held, None


async def _apply_held(held: dict[str, Any]) -> tuple[bool, str]:
    """Apply a held manifest via the ratified commit replay (the ratify rail)."""
    from forge_bridge.orchestration.apply_editorial_delta import (
        apply_editorial_delta, graph_replay_commit_spec,
    )
    applied = await apply_editorial_delta(
        graph_replay_commit_spec(held), assent_record=_ratified_assent()
    )
    commit = _commit_applied(applied)
    if commit and commit.get("applied"):
        return True, f"{commit.get('count')} renamed"
    cerr = _node_error(applied) or ("commit", "apply did not complete")
    return False, cerr[1]


async def _bootstrap() -> None:
    os.environ.setdefault("FORGE_PLUGINS", "flame,traffik")
    from forge_bridge.mcp.server import mcp, bootstrap_daemon
    await bootstrap_daemon(mcp)


async def _run_rename(con) -> None:
    sequence = Prompt.ask("[amber]Sequence[/amber]").strip()
    if not sequence:
        con.print("  cancelled — no sequence")
        return
    segs = await _segments(sequence)
    if not segs:
        con.print(f"  no segments found on [bold]{sequence}[/bold] (open it in Flame?)")
        return
    con.print(f"\n  Segments on [bold]{sequence}[/bold]:")
    for i, s in enumerate(segs, 1):
        con.print(f"    {i:>3}  {s.get('seg_name')}  [dim](track {s.get('track_idx')})[/dim]")
    idx = IntPrompt.ask("[amber]Which segment #[/amber]")
    if not (1 <= idx <= len(segs)):
        con.print("  cancelled — out of range")
        return
    seg = segs[idx - 1]
    new_name = Prompt.ask("[amber]New name[/amber]", default=str(seg.get("seg_name"))).strip()
    if not new_name or new_name == seg.get("seg_name"):
        con.print("  cancelled — name unchanged")
        return

    con.print("\n  [dim]checking the live timeline…[/dim]")
    held, err = await _preview_rename(sequence, seg, new_name)
    if err is not None:
        con.print(f"  [red]can't do that[/red] — {err[1]} ([dim]{err[0]}[/dim])")
        return
    plan = held.get("resolved_plan") or []
    con.print(f"\n  [bold]Preview[/bold] — will rename {len(plan)} segment in Flame:")
    con.print(f"    {seg.get('seg_name')}")
    con.print(f"      →  {new_name}")
    con.print("    [dim]reversible · nothing else touched[/dim]\n")

    if not Confirm.ask("  Apply this change?", default=False):
        con.print("  not applied.")
        return

    # confirmation IS the ratification act
    ok, msg = await _apply_held(held)
    if ok:
        con.print(f"  [green]✓ enacted in Flame[/green] — {msg}.")
    else:
        con.print(f"  [red]not applied[/red] — {msg}")


async def run_interactive() -> None:
    con = make_console()
    con.print("[dim]starting engine…[/dim]")
    await _bootstrap()

    con.print("\n[bold amber]forge exec[/bold amber] — type [bold]/help[/bold], or a verb. [dim]/quit to leave.[/dim]")
    handlers = {"rename": _run_rename}
    while True:
        try:
            line = Prompt.ask("\n[bold]forge[/bold]").strip()
        except (EOFError, KeyboardInterrupt):
            con.print("\nbye.")
            return
        if not line:
            continue
        cmd = line.lstrip("/").split()[0].lower()
        if cmd in ("quit", "exit", "q"):
            con.print("bye.")
            return
        if cmd in ("help", "?", ""):
            con.print("\n  What you can do:")
            for v in _verbs.list_verbs():
                con.print(f"    [bold]/{v.name}[/bold]  —  {v.summary}")
            con.print("    [bold]/quit[/bold]  —  leave")
            continue
        handler = handlers.get(cmd)
        if handler is None:
            con.print(f"  unknown: [bold]{cmd}[/bold].  try [bold]/help[/bold].")
            continue
        try:
            await handler(con)
        except Exception as exc:  # noqa: BLE001 — REPL must survive one bad verb
            con.print(f"  [red]error[/red]: {type(exc).__name__}: {exc}")


async def run_oneshot(
    *,
    verb: str,
    sequence: str,
    segment_name: str,
    new_name: str,
    do_apply: bool,
    as_json: bool = False,
) -> int:
    """Non-interactive one-shot: preview a verb (and optionally apply).

    Scriptable + testable sibling of the REPL. Segment is matched by exact
    ``seg_name`` (no interactive picker). Preview-only by default; ``do_apply``
    runs the ratified commit replay. Returns a process exit code.
    """
    con = make_console()
    await _bootstrap()

    if verb != "rename":
        con.print(f"[red]unsupported verb[/red]: {verb}")
        return 1

    segs = await _segments(sequence)
    matches = [s for s in segs if str(s.get("seg_name")) == segment_name]
    if len(matches) != 1:
        why = ("no segment" if not matches
               else f"{len(matches)} segments") + f" named {segment_name!r} on {sequence}"
        if as_json:
            print(json.dumps({"ok": False, "where": "select", "why": why}))  # noqa: T201
        else:
            con.print(f"[red]{why}[/red]")
        return 1
    seg = matches[0]

    held, err = await _preview_rename(sequence, seg, new_name)
    if err is not None:
        if as_json:
            print(json.dumps({"ok": False, "where": err[0], "why": err[1]}))  # noqa: T201
        else:
            con.print(f"[red]can't do that[/red] — {err[1]} ([dim]{err[0]}[/dim])")
        return 1

    if not do_apply:
        if as_json:
            print(json.dumps({"ok": True, "preview": True, "manifest": held}, default=str))  # noqa: T201
        else:
            plan = held.get("resolved_plan") or []
            con.print(f"Preview — would rename {len(plan)} segment: "
                      f"{segment_name} → {new_name} (not applied; pass --apply)")
        return 0

    ok, msg = await _apply_held(held)
    if as_json:
        print(json.dumps({"ok": ok, "applied": ok, "detail": msg}))  # noqa: T201
    else:
        con.print(f"{'✓ enacted in Flame — ' + msg if ok else '[red]not applied[/red] — ' + msg}")
    return 0 if ok else 4
