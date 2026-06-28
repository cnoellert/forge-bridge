"""`fbridge exec` interactive mode — the first renderer of the verb registry.

Bootstraps the engine once, then runs a small REPL: pick a verb (slash-command
or name), fill a couple of plain-language values (segments are PICKED from the
live timeline, not typed — identity is resolved behind the glass), see a
domain-language preview, then choose: [y] apply now, [s] stage for later
ratification, or [n] cancel. Confirmation IS the ratification act: preview runs
with no assent (fail-closed), [y] runs the same graph with a ratified
AssentRecord, and [s] persists the previewed intent as a *proposed* graph-intent
that `fbridge ratify <id>` applies later. Mutations never bypass the
preview->ratify->apply rail; [s] never self-ratifies.

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

from rich.prompt import Prompt, IntPrompt

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


def _build_mutation_spec(
    verb: Any, sequence: str, seg: dict[str, Any], values: dict[str, Any]
) -> Any:
    """The single canonical author of a verb's host-mutation GraphSpec.

    Both the no-assent preview and the stage-for-ratification persist build their
    spec HERE — one representation, never two (the staged intent IS the previewed
    intent). ponytail: same call surface `run_oneshot` builds inline.
    """
    delta = verb.build_delta({"sequence_name": sequence, "segment": seg, **values})
    return _verbs.build_host_mutation_spec(delta, _verbs.host_resolve_operator())


async def _preview_mutation(
    verb: Any, sequence: str, seg: dict[str, Any], values: dict[str, Any]
) -> tuple[dict[str, Any] | None, tuple[str, str] | None]:
    """Resolve the held mutation manifest for a verb (NO assent, no mutation).

    Returns (held_manifest, None) on success, or (None, (where, why)) for a
    fail-closed reason (e.g. UNRESOLVED_TARGET).
    """
    from forge_bridge.orchestration.apply_editorial_delta import preview_editorial_delta
    spec = _build_mutation_spec(verb, sequence, seg, values)
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
        return True, f"{commit.get('count')} applied"
    # apply-path error: the failing node IS commit, so read every node (unlike
    # _node_error, which intentionally skips commit for the *preview* phase).
    for r in applied.values():
        if str(getattr(r.status, "value", r.status)) == "error":
            out = getattr(r, "output", None)
            nested = out.get("error", {}).get("type") if isinstance(out, dict) else None
            return False, _humanize(getattr(r, "reason_code", None) or nested
                                    or getattr(r, "message", None))
    return False, "apply did not complete"


async def _stage_mutation(
    verb: Any, sequence: str, seg: dict[str, Any], values: dict[str, Any], *, display: str
) -> str:
    """Persist the previewed mutation as a *proposed* graph-intent for later ratify.

    Reuses the SAME canonical spec author as the preview, then hands it to the
    proven in-process producer (writes the DB directly via the session factory —
    no daemon for the stage step; only the later `fbridge ratify` needs it). NO
    apply, NO assent — assent stays the ratifier's act. Returns the
    ``graph_intent_id`` that `fbridge ratify <id>` consumes.
    """
    from forge_bridge.orchestration.apply_editorial_delta import (
        preview_editorial_delta_for_ratification,
    )
    from forge_bridge.store.session import get_async_session_factory
    spec = _build_mutation_spec(verb, sequence, seg, values)
    staged = await preview_editorial_delta_for_ratification(
        spec, session_factory=get_async_session_factory(), display=display,
    )
    return staged.get("graph_intent_id")


_REQUIRED_PLUGINS = ("flame", "traffik")  # verbs need flame (host) + traffik (op)

_REASON_HUMAN = {
    "UNRESOLVED_TARGET": "couldn't find that segment in the live timeline",
    "HELD_FOR_REVIEW": "this change needs human review before it can apply",
    "UNSUPPORTED_DELTA_ACTION": "that kind of change isn't supported yet",
    "HETEROGENEOUS_DELTA": "mixed change types can't be applied together yet",
    "HOST_DISCOVER_FAILED": "Flame couldn't resolve the target",
    "PLAN_STATE_DRIFT": "the timeline changed since the preview — re-run it",
    "ASSENT_INVALID": "not approved",
    "APPLY_FAILED": "Flame rejected the change",
}


def _humanize(reason: str | None) -> str:
    if not reason:
        return "could not complete"
    return _REASON_HUMAN.get(reason, reason)


async def _bootstrap() -> None:
    # union (not setdefault): rename needs traffik even if the shell preset flame only
    have = {p.strip() for p in os.environ.get("FORGE_PLUGINS", "").split(",") if p.strip()}
    os.environ["FORGE_PLUGINS"] = ",".join(sorted(have | set(_REQUIRED_PLUGINS)))
    from forge_bridge.mcp.server import mcp, bootstrap_daemon
    await bootstrap_daemon(mcp)


def _parse_inline(rest: str) -> tuple[str | None, int | None, str | None, str | None]:
    """Parse a power-user slash line's inline args — verb-agnostic by design.

    Grammar (identical for every verb): ``<sequence> #<index> <value...>``.
    Returns ``(sequence, seg_index, value_raw, error)``. Any of the first three
    is ``None`` when not supplied — the caller then prompts for it (partial args
    just fill what's given). ``value_raw`` is the rest-of-line string (so a
    rename value may contain spaces); it is typed/validated downstream by the
    shared ``verbs.parse_value`` — the one trust boundary — so there is zero
    per-verb branching here. ``error`` is a clean message for a MALFORMED arg
    (a ``#index`` that isn't ``#<number>``); the caller aborts on it. The
    in-range check stays in ``_run_verb`` (it needs the live segment count).
    """
    parts = rest.split(None, 2)
    if not parts:
        return None, None, None, None
    sequence = parts[0]
    if len(parts) == 1:
        return sequence, None, None, None
    tok = parts[1]
    if not tok.startswith("#") or not tok[1:].lstrip("-").isdigit():
        return None, None, None, f"segment number must look like #N (got {tok!r})"
    value_raw = parts[2] if len(parts) > 2 else None
    return sequence, int(tok[1:]), value_raw, None


async def _run_verb(
    con, *, verb: Any,
    sequence: str | None = None,
    seg_index: int | None = None,
    value_raw: str | None = None,
) -> None:
    # any arg left None is prompted for — bare /verb prompts for all three.
    sequence = (sequence if sequence is not None
                else Prompt.ask("[amber]Sequence[/amber]")).strip()
    if not sequence:
        con.print("  cancelled — no sequence")
        return
    segs = await _segments(sequence)
    if not segs:
        con.print(f"  no segments found on [bold]{sequence}[/bold] (open it in Flame?)")
        return
    if seg_index is None:
        con.print(f"\n  Segments on [bold]{sequence}[/bold]:")
        for i, s in enumerate(segs, 1):
            con.print(f"    {i:>3}  {s.get('seg_name')}  [dim](track {s.get('track_idx')})[/dim]")
        idx = IntPrompt.ask("[amber]Which segment #[/amber]")
    else:
        idx = seg_index
    if not (1 <= idx <= len(segs)):
        con.print("  cancelled — out of range")
        return
    seg = segs[idx - 1]
    current = seg.get(verb.current_key)
    # one edited value, typed per the verb (str vs int) — IntPrompt keeps the
    # interactive lane numeric; parse_value is the shared trust-boundary gate.
    if value_raw is not None:
        raw = value_raw
    elif verb.value_kind == "int":
        raw = str(IntPrompt.ask(f"[amber]{verb.value_label}[/amber]", default=current))
    else:
        raw = Prompt.ask(f"[amber]{verb.value_label}[/amber]", default=str(current))
    value, perr = _verbs.parse_value(verb, raw)
    if perr is not None:
        con.print(f"  cancelled — {perr}")
        return
    if _verbs.is_unchanged(verb, value, current):
        con.print("  cancelled — value unchanged")
        return

    con.print("\n  [dim]checking the live timeline…[/dim]")
    held, err = await _preview_mutation(verb, sequence, seg, {verb.value_field: value})
    if err is not None:
        con.print(f"  [red]can't do that[/red] — {_humanize(err[1])}")
        return
    plan = held.get("resolved_plan") or []
    con.print(f"\n  [bold]Preview[/bold] — {verb.label}, {len(plan)} segment in Flame:")
    con.print(f"    {seg.get('seg_name')}:  {current}  →  {value}")
    con.print("    [dim]reversible · nothing else touched[/dim]\n")

    # apply now [y] / stage for later ratification [s] / cancel [n]
    choice = Prompt.ask(
        "  [y] apply now · [s] stage for ratify · [n] cancel",
        choices=["y", "s", "n"], default="n",
    ).lower()
    if choice == "n":
        con.print("  not applied.")
        return
    if choice == "s":
        # persist the previewed intent; ratification stays a separate operator act.
        # ponytail: in-process DB write — infra failures bubble to the REPL's outer
        # handler (clean message, no traceback), so no daemon-reachability guard here.
        gid = await _stage_mutation(
            verb, sequence, seg, {verb.value_field: value},
            display=f"{verb.name} {seg.get('seg_name')} -> {value}",
        )
        con.print("  [amber]staged — nothing applied yet.[/amber] Ratify later with:")
        con.print(f"    [bold]fbridge ratify {gid}[/bold]")
        return

    # [y]: confirmation IS the ratification act (apply-now rail, unchanged)
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
    con.print("[dim]power users: /rename <sequence> #<n> <new name> · /trim <sequence> #<n> <frame>[/dim]")
    # verbs are data — one registry lookup, zero per-verb code in the loop
    verbs_by_cmd = {v.name: v for v in _verbs.list_verbs()}
    while True:
        try:
            line = Prompt.ask("\n[bold]forge[/bold]").strip()
        except (EOFError, KeyboardInterrupt):
            con.print("\nbye.")
            return
        if not line:
            continue
        toks = line.lstrip("/").split(None, 1)
        if not toks:  # bare "/" etc.
            continue
        cmd = toks[0].lower()
        rest = toks[1] if len(toks) > 1 else ""
        if cmd in ("quit", "exit", "q"):
            con.print("bye.")
            return
        if cmd in ("help", "?"):
            con.print("\n  What you can do:")
            for v in _verbs.list_verbs():
                con.print(f"    [bold]/{v.name}[/bold]  —  {v.summary}")
            con.print("    [bold]/quit[/bold]  —  leave")
            continue
        verb = verbs_by_cmd.get(cmd)
        if verb is None:
            con.print(f"  unknown: [bold]{cmd}[/bold].  try [bold]/help[/bold].")
            continue
        # inline args skip the prompts; anything omitted falls back to prompting
        sequence, seg_index, value_raw, ierr = _parse_inline(rest)
        if ierr is not None:
            con.print(f"  cancelled — {ierr}")
            continue
        try:
            await _run_verb(con, verb=verb, sequence=sequence,
                            seg_index=seg_index, value_raw=value_raw)
        except (KeyboardInterrupt, EOFError):
            con.print("  cancelled.")
        except Exception as exc:  # noqa: BLE001 — REPL must survive one bad verb
            con.print(f"  [red]error[/red]: {type(exc).__name__}: {exc}")


def _emit(con, as_json: bool, payload: dict[str, Any], human: str) -> None:
    if as_json:
        print(json.dumps(payload, default=str))  # noqa: T201
    else:
        con.print(human)


async def run_oneshot(
    *,
    verb: str,
    sequence: str,
    segment_name: str,
    new_name: str,
    do_apply: bool,
    as_json: bool = False,
) -> int:
    """Non-interactive one-shot: preview a verb, or STAGE it for ratification.

    Segment is matched by exact ``seg_name``. ``new_name`` carries the raw new
    value as a string (ponytail: one CLI slot serves every verb; it is parsed per
    the verb's ``value_kind`` at the trust boundary). Preview-only by default.
    With ``do_apply`` it does NOT self-apply — it persists a proposed
    ``graph_intent`` and prints the ``fbridge ratify <id>`` command, so
    ratification stays a separate, audited operator act (assent is never
    self-signed here).
    """
    con = make_console()

    spec_verb = _verbs.REGISTRY.get(verb)
    if spec_verb is None:
        _emit(con, as_json, {"ok": False, "where": "verb", "why": f"unsupported verb {verb!r}"},
              f"[red]unsupported verb[/red]: {verb}")
        return 1

    await _bootstrap()

    segs = await _segments(sequence)
    if not segs:
        _emit(con, as_json, {"ok": False, "where": "sequence",
                             "why": f"no segments on {sequence!r} — is it open in Flame?"},
              f"[red]no segments on {sequence!r}[/red] — is it open in Flame?")
        return 1
    matches = [s for s in segs if str(s.get("seg_name")) == segment_name]
    if len(matches) != 1:
        why = (f"no segment named {segment_name!r}" if not matches
               else f"{len(matches)} segments named {segment_name!r} (ambiguous)")
        _emit(con, as_json, {"ok": False, "where": "select", "why": why}, f"[red]{why}[/red]")
        return 1
    seg = matches[0]

    value, perr = _verbs.parse_value(spec_verb, new_name)
    if perr is not None:
        _emit(con, as_json, {"ok": False, "where": "input", "why": perr},
              f"[yellow]{perr}[/yellow]")
        return 1
    current = seg.get(spec_verb.current_key)
    if _verbs.is_unchanged(spec_verb, value, current):
        _emit(con, as_json, {"ok": False, "where": "input", "why": "value unchanged"},
              "[yellow]value unchanged — nothing to do[/yellow]")
        return 1

    held, err = await _preview_mutation(spec_verb, sequence, seg, {spec_verb.value_field: value})
    if err is not None:
        _emit(con, as_json, {"ok": False, "where": err[0], "why": _humanize(err[1])},
              f"[red]can't do that[/red] — {_humanize(err[1])}")
        return 1

    plan = held.get("resolved_plan") or []
    if not do_apply:
        _emit(con, as_json, {"ok": True, "preview": True, "manifest": held},
              f"Preview — would {verb} {len(plan)} segment: {segment_name} "
              f"{current} → {value} (not applied; pass --apply to stage for ratification)")
        return 0

    # --apply STAGES (persists a proposed graph_intent); it does not self-ratify.
    from forge_bridge.orchestration.apply_editorial_delta import (
        preview_editorial_delta_for_ratification,
    )
    from forge_bridge.store.session import get_async_session_factory
    spec = _verbs.build_host_mutation_spec(
        spec_verb.build_delta(
            {"sequence_name": sequence, "segment": seg, spec_verb.value_field: value}),
        _verbs.host_resolve_operator(),
    )
    staged = await preview_editorial_delta_for_ratification(
        spec, session_factory=get_async_session_factory(),
        display=f"{verb} {segment_name} -> {value}",
    )
    gid = staged.get("graph_intent_id")
    _emit(con, as_json,
          {"ok": True, "staged": True, "graph_intent_id": gid},
          f"staged — review then apply with:  [bold]fbridge ratify {gid}[/bold]")
    return 0
