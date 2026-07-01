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
from pathlib import Path
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


async def _desktop_sequences() -> list[str] | None:
    """Names of every sequence on the live Flame desktop (read-only).

    Mirrors the desktop walk ``_find_seq`` uses in ``tools.timeline`` (reel
    groups -> reels -> sequences), but collects names only — cheaper than the
    full segment read, and ``flame_list_desktop`` only returns sequence *counts*.
    ``main_thread`` stays at its safe default (False): this never mutates Flame.

    The return value distinguishes the two cases the caller collapses on:
    ``[]`` is a SUCCESSFUL read of an empty desktop (no sequence open); ``None``
    is a READ FAILURE (Flame unreachable / hook error) — the caller falls back
    to the typed prompt on ``None`` so nothing regresses.
    """
    from forge_bridge import bridge
    try:
        data = await bridge.execute_json("""
import flame, json
ws = flame.project.current_project.current_workspace
desk = ws.desktop
names = []
for rg in desk.reel_groups:
    for reel in rg.reels:
        for seq in (reel.sequences or []):
            n = seq.name.get_value() if hasattr(seq.name, 'get_value') else str(seq.name)
            names.append(str(n))
print(json.dumps(names))
""")
    except Exception:  # noqa: BLE001 — any read failure => fall back to the prompt
        return None
    return [str(n) for n in data] if isinstance(data, list) else None


async def _selected_segments() -> tuple[str, list[dict[str, Any]]] | None:
    """Identity of the segment(s) highlighted in the live Flame timeline (read-only).

    Reads ``flame.timeline.clip`` — the sequence open in the timeline viewer —
    and walks ``clip.versions -> tracks -> segments`` enumerating ``track_idx``
    the SAME way ``_collect_segments`` (``tools.timeline``) does, emitting an
    identity dict ``{track_idx, record_in, seg_name, source_name}`` for each
    segment whose ``selected`` PyAttribute is True. That tuple is the drop-in key
    ``_selected_key_tuple`` / ``_seg_key_tuple`` already use, so the identities
    match the full dicts ``_segments`` returns (see ``_match_selected``).
    ``main_thread`` stays at its safe default (False): this never mutates Flame.

    Guarded to the timeline: ``flame.get_current_tab() == "Timeline"`` AND a real
    open sequence. The return value is tri-state, mirroring ``_desktop_sequences``:

      ``None``            -> read FAILURE / not on the Timeline tab / no open clip
                            (the caller falls back to the normal sequence flow).
      ``(name, [])``      -> a SUCCESSFUL read with NOTHING highlighted (the
                            caller also falls back — empty selection picks nothing).
      ``(name, [ids…])``  -> the highlighted segments' identities on ``name``.
    """
    from forge_bridge import bridge
    try:
        data = await bridge.execute_json("""
import flame, json
try:
    _tab = flame.get_current_tab()
except Exception:
    _tab = None
_clip = getattr(flame.timeline, 'clip', None)
if _tab != 'Timeline' or _clip is None or not hasattr(_clip, 'versions'):
    print(json.dumps(None))
else:
    _name = _clip.name.get_value() if hasattr(_clip.name, 'get_value') else str(_clip.name)
    _tracks = []
    for _ver in _clip.versions:
        for _track in _ver.tracks:
            _tracks.append(_track)
    _selected = []
    for _ti, _track in enumerate(_tracks):
        for _seg in _track.segments:
            _src = str(_seg.source_name) if _seg.source_name else ''
            if not _src:
                continue  # gap / filler — never a real selectable segment
            try:
                _sel = _seg.selected.get_value() if hasattr(_seg.selected, 'get_value') else bool(_seg.selected)
            except Exception:
                _sel = False
            if _sel is not True:
                continue
            try:
                _sn = _seg.name.get_value() if hasattr(_seg.name, 'get_value') else str(_seg.name)
            except Exception:
                _sn = ''
            _selected.append({
                'track_idx': _ti,
                'record_in': str(_seg.record_in),
                'seg_name': _sn,
                'source_name': _src,
            })
    print(json.dumps({'sequence': str(_name), 'selected': _selected}))
""")
    except Exception:  # noqa: BLE001 — any read failure => caller falls back
        return None
    if not isinstance(data, dict):  # None (guard tripped) or malformed read
        return None
    name = data.get("sequence")
    sel = data.get("selected")
    if not isinstance(name, str) or not isinstance(sel, list):
        return None
    return name, [s for s in sel if isinstance(s, dict)]


def _selection_key(item: dict[str, Any]) -> tuple[int, str, str, str]:
    """The 4-tuple identity shared by selection identities AND ``_segments`` dicts.

    Mirrors ``_selected_key_tuple`` / ``_seg_key_tuple`` in ``tools.timeline`` so
    a selection identity matches the full segment dict for the SAME live segment.
    """
    return (
        int(item.get("track_idx", 0)),
        str(item.get("record_in", "")),
        str(item.get("seg_name") or item.get("name") or ""),
        str(item.get("source_name", "")),
    )


def _match_selected(
    segs: list[dict[str, Any]], identities: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Filter the full ``_segments`` dicts down to the selected identities.

    Selection gives only identity; trim verbs need the full dict
    (``record_in_frame`` / ``record_out_frame`` / ``head`` / ``tail`` / …). So we
    keep the ``_segments``-shaped dicts whose key matches a selected identity —
    never hand-build a dict from the (thin) selection walk.
    """
    keys = {_selection_key(i) for i in identities}
    return [s for s in segs if _selection_key(s) in keys]


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


def _build_mutation_spec_multi(
    verb: Any, sequence: str, segs: list[dict[str, Any]], values: dict[str, Any]
) -> Any:
    """The single canonical author of a verb's host-mutation GraphSpec (1..N segs).

    Both the no-assent preview and the stage-for-ratification persist build their
    spec HERE — one representation, never two (the staged intent IS the previewed
    intent). The builder folds ``segs`` into ONE multi-entry TimelineDelta riding
    the same preview->ratify->commit rail (Approach A). ponytail: same call
    surface `run_oneshot` builds inline.
    """
    delta = verb.build_delta({"sequence_name": sequence, "segments": segs, **values})
    return _verbs.build_host_mutation_spec(delta, _verbs.host_resolve_operator())


def _build_mutation_spec(
    verb: Any, sequence: str, seg: dict[str, Any], values: dict[str, Any]
) -> Any:
    """Single-segment spec author — the 1-element case of ``_build_mutation_spec_multi``."""
    return _build_mutation_spec_multi(verb, sequence, [seg], values)


async def _preview_mutation_multi(
    verb: Any, sequence: str, segs: list[dict[str, Any]], values: dict[str, Any]
) -> tuple[dict[str, Any] | None, tuple[str, str] | None]:
    """Resolve the held mutation manifest for a verb over N segments (NO assent).

    Returns (held_manifest, None) on success, or (None, (where, why)) for a
    fail-closed reason (e.g. UNRESOLVED_TARGET).
    """
    from forge_bridge.orchestration.apply_editorial_delta import preview_editorial_delta
    spec = _build_mutation_spec_multi(verb, sequence, segs, values)
    results = await preview_editorial_delta(spec)
    err = _node_error(results)
    if err is not None:
        return None, err
    held = _held_manifest(results)
    if held is None:
        return None, ("preview", "no mutation manifest")
    return held, None


async def _preview_mutation(
    verb: Any, sequence: str, seg: dict[str, Any], values: dict[str, Any]
) -> tuple[dict[str, Any] | None, tuple[str, str] | None]:
    """Single-segment preview — the 1-element case of ``_preview_mutation_multi``."""
    return await _preview_mutation_multi(verb, sequence, [seg], values)


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


async def _stage_mutation_multi(
    verb: Any, sequence: str, segs: list[dict[str, Any]], values: dict[str, Any],
    *, display: str,
) -> str:
    """Persist the previewed N-segment mutation as a *proposed* graph-intent.

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
    spec = _build_mutation_spec_multi(verb, sequence, segs, values)
    staged = await preview_editorial_delta_for_ratification(
        spec, session_factory=get_async_session_factory(), display=display,
    )
    return staged.get("graph_intent_id")


async def _stage_mutation(
    verb: Any, sequence: str, seg: dict[str, Any], values: dict[str, Any], *, display: str
) -> str:
    """Single-segment stage — the 1-element case of ``_stage_mutation_multi``."""
    return await _stage_mutation_multi(verb, sequence, [seg], values, display=display)


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
    # host temporal-trim contract codes (forge_apply_segment_temporal_delta) —
    # surfaced for legibility when a trim slips past the CLI-side range guard.
    "insufficient_handles": "not enough handle to extend the trim that far",
    "unsupported_delta": "that trim isn't supported (it may collapse the segment)",
    "identity_unresolved": "couldn't find that segment in the live timeline",
    "unsupported_live_segment": "the live segment is missing the frame data to trim",
}


def _humanize(reason: str | None) -> str:
    if not reason:
        return "could not complete"
    return _REASON_HUMAN.get(reason, reason)


async def _bootstrap() -> None:
    # Quiet library INFO chatter (plugin discovery, dispatch, synth-tool watcher)
    # so the interactive REPL stays legible — the REPL speaks via Rich, not the
    # logging module, so WARNING+ still surfaces real problems. forge_core is the
    # peer plugin loader; composition/learning are ours.
    import logging
    for _name in ("forge_core", "forge_bridge.composition", "forge_bridge.learning"):
        logging.getLogger(_name).setLevel(logging.WARNING)
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


async def _resolve_sequence(con) -> str | None:
    """Auto-resolve the sequence for a bare ``/verb`` (no typed identity).

    Collapses on the live Flame desktop so the artist never types a sequence
    name: exactly one open sequence is used silently; several are listed for a
    numeric pick (mirroring how ``_run_verb`` lists segments); none yields a
    plain "open one" message. A *read failure* (``_desktop_sequences`` -> None,
    Flame unreachable) falls back to the original typed prompt so nothing
    regresses. Returns the chosen sequence name, or ``None`` to abort the verb.

    Renderer-neutral by design (prints + prompts through ``con``/Rich) so a later
    surface can lift the collapse rule; the explicit ``sequence=...`` paths
    (one-shot, slash inline-args, NL composer) never reach here.
    """
    seqs = await _desktop_sequences()
    if seqs is None:  # read failed — preserve the original typed-prompt behavior
        typed = Prompt.ask("[amber]Sequence[/amber]").strip()
        if not typed:
            con.print("  cancelled — no sequence")
            return None
        return typed
    if not seqs:
        con.print("  no sequence open — open one in Flame")
        return None
    if len(seqs) == 1:
        con.print(f"  using the open sequence: [bold]{seqs[0]}[/bold]")
        return seqs[0]
    con.print("\n  Open sequences:")
    for i, name in enumerate(seqs, 1):
        con.print(f"    {i:>3}  {name}")
    idx = IntPrompt.ask("[amber]Which sequence #[/amber]")
    if not (1 <= idx <= len(seqs)):
        con.print("  cancelled — out of range")
        return None
    return seqs[idx - 1]


async def _run_fanout(
    con, *, verb: Any, sequence: str, segs: list[dict[str, Any]]
) -> None:
    """Apply ``verb`` to ALL selected ``segs`` in ONE preview->ratify->commit.

    Approach A: the value is collected ONCE (one offset for a trim, one name
    TEMPLATE for a rename), then every timeline-sorted segment becomes one entry
    of a single multi-entry TimelineDelta riding the same rail as a lone edit.
    The preview lists each segment's concrete change (rename shows the expanded
    per-segment name). ``segs`` arrives timeline-sorted, so the counter numbering
    and the preview rows agree with the builder's entry order.
    """
    con.print(f"\n  [bold]{len(segs)}[/bold] segments selected on [bold]{sequence}[/bold]:")
    for i, s in enumerate(segs, 1):
        con.print(f"    {i:>3}  {s.get('seg_name')}  [dim](track {s.get('track_idx')})[/dim]")

    # one value for the whole batch: offset (trim) defaults to 0; a rename takes a
    # counter TEMPLATE so each segment gets a distinct expanded name (see #guard).
    if verb.value_kind == "offset":
        raw = str(IntPrompt.ask(f"[amber]{verb.value_label}[/amber]", default=0))
    elif verb.value_kind == "int":
        raw = str(IntPrompt.ask(f"[amber]{verb.value_label}[/amber]"))
    else:
        raw = Prompt.ask(
            f"[amber]{verb.value_label} — use $n for a per-segment counter "
            f"(e.g. shot_$n)[/amber]")
    value, perr = _verbs.parse_value(verb, raw)
    if perr is not None:
        con.print(f"  cancelled — {perr}")
        return

    # a counter is OPTIONAL — Flame allows duplicate segment names, so a bare
    # name applies literally to every selected segment. Only a MALFORMED counter
    # spec ($n{x}, $n{}) is rejected, before it silently mangles a name.
    if verb.value_kind == "str":
        cerr = _verbs.validate_counter(value)
        if cerr is not None:
            con.print(f"  [red]can't do that[/red] — {cerr}")
            return
    # per-segment range guard for trims: reject naming EACH offender, never
    # silently apply to the rest of the batch.
    if verb.trim_side is not None:
        fails = [(s, _verbs.validate_trim(verb, value, s)) for s in segs]
        fails = [(s, why) for s, why in fails if why is not None]
        if fails:
            detail = "; ".join(f"{s.get('seg_name')}: {why}" for s, why in fails)
            con.print(f"  [red]can't do that[/red] — {detail}")
            return

    con.print("\n  [dim]checking the live timeline…[/dim]")
    held, err = await _preview_mutation_multi(verb, sequence, segs, {verb.value_field: value})
    if err is not None:
        con.print(f"  [red]can't do that[/red] — {_humanize(err[1])}")
        return
    plan = held.get("resolved_plan") or []
    con.print(f"\n  [bold]Preview[/bold] — {verb.label}, {len(plan)} segments in Flame:")
    # iterate the SAME timeline-sorted order + 0-based index the delta builder
    # uses, so the previewed name matches exactly what gets applied.
    for i, s in enumerate(_verbs.timeline_sorted(segs)):
        if verb.value_kind == "str":
            con.print(f"    {s.get('seg_name')}  →  "
                      f"{_verbs.expand_counter(value, i)}")
        else:
            con.print(f"    {s.get('seg_name')}:  "
                      f"{_verbs.describe_change(verb, s.get(verb.current_key), value)}")
    con.print("    [dim]reversible · nothing else touched[/dim]\n")

    # same y/s/n gate as the single path; confirmation IS the ratification act.
    con.print("  How do you want to proceed?")
    con.print("    [bold]y[/bold] — apply now: make the changes in Flame (reversible — re-run to undo)")
    con.print("    [bold]s[/bold] — stage it: save for approval, apply later with [dim]fbridge ratify <id>[/dim]")
    con.print("    [bold]n[/bold] — cancel: do nothing")
    choice = Prompt.ask(
        "  [amber]y / s / n[/amber]",
        choices=["y", "s", "n"], default="n",
    ).lower()
    if choice == "n":
        con.print("  not applied.")
        return
    if choice == "s":
        gid = await _stage_mutation_multi(
            verb, sequence, segs, {verb.value_field: value},
            display=f"{verb.name} ×{len(segs)} -> {value}",
        )
        con.print("  [amber]staged — nothing applied yet.[/amber] Ratify later with:")
        con.print(f"    [bold]fbridge ratify {gid}[/bold]")
        return
    ok, msg = await _apply_held(held)
    if ok:
        con.print(f"  [green]✓ enacted in Flame[/green] — {msg}.")
    else:
        con.print(f"  [red]not applied[/red] — {msg}")


async def _run_verb(
    con, *, verb: Any,
    sequence: str | None = None,
    seg_index: int | None = None,
    value_raw: str | None = None,
) -> None:
    # Fully-interactive bare /verb (no typed identity): try the LIVE timeline
    # selection first so the artist's highlight auto-targets the segment(s) —
    # collapsing both the sequence prompt AND the segment-index prompt. Explicit
    # sequence=/seg_index= paths (one-shot, slash inline-args, NL composer) never
    # reach here, so they stay byte-identical.
    seg: dict[str, Any] | None = None
    if sequence is None and seg_index is None:
        picked = await _selected_segments()
        if picked is not None:
            sel_seq, identities = picked
            if identities:  # something highlighted -> scope to just those segments
                chosen = _match_selected(await _segments(sel_seq), identities)
                if len(chosen) == 1:
                    sequence, seg = sel_seq, chosen[0]
                    con.print(f"  using your selected segment: "
                              f"[bold]{seg.get('seg_name')}[/bold] on [bold]{sequence}[/bold]")
                elif len(chosen) > 1:
                    # FAN-OUT (Approach A): apply the verb to ALL selected segments
                    # in one preview->ratify->commit via a single multi-entry delta.
                    await _run_fanout(con, verb=verb, sequence=sel_seq,
                                      segs=_verbs.timeline_sorted(chosen))
                    return
                # chosen empty (selection matched no live segment) -> fall through

    # any arg left None is prompted for — bare /verb auto-resolves the sequence
    # off the live desktop (zero typing), then prompts for index + value.
    if sequence is None:
        sequence = await _resolve_sequence(con)
        if sequence is None:
            return
    else:
        sequence = sequence.strip()
        if not sequence:
            con.print("  cancelled — no sequence")
            return
    # skip the segment list entirely when the live selection already resolved one
    if seg is None:
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
    # one edited value, typed per the verb — IntPrompt keeps the numeric lanes
    # numeric; an offset (relative trim) defaults to 0, never an absolute frame.
    if value_raw is not None:
        raw = value_raw
    elif verb.value_kind == "offset":
        raw = str(IntPrompt.ask(f"[amber]{verb.value_label}[/amber]", default=0))
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
    # CLI-side range guard: reject an impossible trim with a legible message
    # before it reaches the host (no-op for non-trim verbs).
    rerr = _verbs.validate_trim(verb, value, seg)
    if rerr is not None:
        con.print(f"  [red]can't do that[/red] — {rerr}")
        return

    con.print("\n  [dim]checking the live timeline…[/dim]")
    held, err = await _preview_mutation(verb, sequence, seg, {verb.value_field: value})
    if err is not None:
        con.print(f"  [red]can't do that[/red] — {_humanize(err[1])}")
        return
    plan = held.get("resolved_plan") or []
    con.print(f"\n  [bold]Preview[/bold] — {verb.label}, {len(plan)} segment in Flame:")
    con.print(f"    {seg.get('seg_name')}:  {_verbs.describe_change(verb, current, value)}")
    con.print("    [dim]reversible · nothing else touched[/dim]\n")

    # apply now [y] / stage for later ratification [s] / cancel [n]
    con.print("  How do you want to proceed?")
    con.print("    [bold]y[/bold] — apply now: make the change in Flame (reversible — re-run to undo)")
    con.print("    [bold]s[/bold] — stage it: save for approval, apply later with [dim]fbridge ratify <id>[/dim]")
    con.print("    [bold]n[/bold] — cancel: do nothing")
    choice = Prompt.ask(
        "  [amber]y / s / n[/amber]",
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


# meta-commands the REPL loop recognizes (besides the registry verbs); these
# join the verb names as completion + did-you-mean candidates.
_META_COMMANDS = ("help", "quit", "exit")


def _command_completions(prefix: str) -> list[str]:
    """Slash-commands matching ``prefix`` — registry-driven, pure, terminal-free.

    Candidates are ``/`` + each verb name (from ``list_verbs()``, so a newly
    registered verb auto-completes) + the meta-commands. ``prefix`` may carry a
    leading ``/``; a bare ``/`` (or empty) returns every command. Sorted so the
    completer + the did-you-mean hint share one stable order.
    """
    stub = prefix.lstrip("/").lower()
    names = [v.name for v in _verbs.list_verbs()] + list(_META_COMMANDS)
    return sorted(f"/{n}" for n in names if n.startswith(stub))


def _did_you_mean(cmd: str) -> list[str]:
    """Commands ``cmd`` is a NON-exact prefix of — for the unknown-command hint.

    Excludes an exact self-match (an exact command never reaches the miss branch;
    this also keeps the hint empty for an exact hit, so it fires only on a real
    near-miss like the orphaned ``/trim`` -> ``/trim_head``, ``/trim_tail``).
    """
    self_cmd = f"/{cmd.lstrip('/').lower()}"
    return [c for c in _command_completions(cmd) if c != self_cmd]


# persistent REPL command history (stdlib readline; up-arrow recalls across
# sessions). Path follows the per-machine ``~/.forge-bridge/`` convention every
# other runtime artifact uses (executions.jsonl, graphs/, corpus/ …) — there is no
# shared home-dir helper, each call site composes it inline, so we do the same.
def _history_path() -> Path:
    return Path.home() / ".forge-bridge" / "exec_history"


def _load_history(readline: Any) -> None:
    """Read persisted command history; guarded — missing/locked file is a no-op.

    ``readline`` may be ``None`` on a platform without it (history simply disabled,
    the REPL still runs).
    """
    if readline is None:
        return
    try:
        readline.read_history_file(str(_history_path()))
    except (FileNotFoundError, OSError):  # no history yet / unreadable — fine
        pass
    readline.set_history_length(1000)


def _save_history(readline: Any) -> None:
    """Persist command history on REPL exit; guarded — an unwritable file never crashes."""
    if readline is None:
        return
    try:
        path = _history_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        readline.write_history_file(str(path))
    except OSError:  # locked / read-only home — drop history, don't crash the REPL
        pass


async def run_interactive() -> None:
    con = make_console()
    con.print("[dim]starting engine…[/dim]")
    await _bootstrap()

    # readline gives the existing Prompt.ask() input() real as-you-type slash
    # completion (stdlib; graceful no-op where unavailable). Completes only the
    # first token (the command) — args come from the live host, out of scope.
    try:
        import readline
    except ImportError:  # pragma: no cover - platform without readline
        readline = None
    if readline is not None:
        # whitespace-only delimiters so the leading '/' stays part of the word
        # readline replaces (default delims include '/').
        readline.set_completer_delims(" \t\n")

        def _completer(text: str, state: int) -> str | None:
            if " " in readline.get_line_buffer().lstrip():
                return None  # past the command — don't complete args
            matches = _command_completions(text)
            return matches[state] if state < len(matches) else None

        readline.set_completer(_completer)
        # macOS often ships libedit, which binds completion differently than GNU.
        if "libedit" in (readline.__doc__ or ""):
            readline.parse_and_bind("bind ^I rl_complete")
        else:
            readline.parse_and_bind("tab: complete")
        # up-arrow recalls prior commands across sessions (stdlib; guarded no-op
        # when the history file is missing/locked).
        _load_history(readline)

    con.print("\n[bold amber]forge exec[/bold amber] — type [bold]/help[/bold], or a verb. [dim]/quit to leave.[/dim]")
    con.print("[dim]power users: /rename <sequence> #<n> <new name> · "
              "/trim_head <sequence> #<n> <±frames> · /trim_tail <sequence> #<n> <±frames>[/dim]")
    # verbs are data — one registry lookup, zero per-verb code in the loop
    verbs_by_cmd = {v.name: v for v in _verbs.list_verbs()}
    # try/finally so the history file is persisted on EVERY exit path (normal
    # /quit, Ctrl-D/Ctrl-C, or an unexpected error escaping the per-verb guard).
    try:
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
                hints = _did_you_mean(cmd)
                if hints:
                    con.print(f"  did you mean: [bold]{', '.join(hints)}[/bold]?")
                else:
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
    finally:
        _save_history(readline)


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
    # CLI-side range guard: a legible reject before the host (no-op for non-trim).
    rerr = _verbs.validate_trim(spec_verb, value, seg)
    if rerr is not None:
        _emit(con, as_json, {"ok": False, "where": "input", "why": rerr},
              f"[red]can't do that[/red] — {rerr}")
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
              f"({_verbs.describe_change(spec_verb, current, value)}) "
              "(not applied; pass --apply to stage for ratification)")
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
