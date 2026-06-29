"""Artist-facing verb registry — the renderer-agnostic vocabulary layer.

A *verb* is an artist-legible action ("Rename a shot") that knows how to turn a
few plain-language values into a host-mutation ``GraphSpec`` riding the proven
preview->ratify->apply rail (``forge_apply_segment_delta``). The interactive
``fbridge exec`` shell is the first renderer of this registry; a web card is a
later renderer of the same data. Verbs are DATA; surfaces are interchangeable.

``forge_core``/composition imports are lazy so ``fbridge --help`` stays fast and
this module imports cleanly without the pipeline plugin installed.

ponytail: the verbs differ only in their single edited value and which side of
the segment it touches -- captured by the ``value_*``/``current_key``/
``trim_side`` fields below + ``parse_value`` (the trust-boundary typed parse), so
the renderers carry zero per-verb branching. Editorial trim is ALWAYS relative:
``trim_head``/``trim_tail`` take a SIGNED FRAME COUNT (``value_kind="offset"``;
positive trims OFF / shortens, negative extends ON), never an absolute frame --
the artist never sees or types a timeline frame number. Still deferred: multi-
field verbs, segment_picker/sequence_picker as declared field kinds, and value
kinds beyond str/int/offset -- not invented before something needs them.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class Verb:
    """One artist-legible action. ``name`` is its slash-command."""

    name: str
    label: str
    summary: str
    # values (plain dict the renderer collected) -> TimelineDelta dict
    build_delta: Callable[[dict[str, Any]], dict[str, Any]]
    # the single artist-edited value: how to prompt, its type, and the segment
    # dict key that holds its CURRENT value (prompt default + unchanged check).
    value_field: str        # key the renderer puts the new value under in ``values``
    value_kind: str         # "str" | "int" | "offset" (signed relative count)
    value_label: str        # prompt label, e.g. "New name" / "Frames to trim..."
    current_key: str        # segment dict key holding the current value
    # "head" | "tail" for a relative trim verb; None for non-trim verbs. Drives
    # the CLI-side range guard (``validate_trim``) + the offset display.
    trim_side: str | None = None
    # identity fields the verb needs resolved from the live host before build
    needs_segment: bool = True


def parse_value(verb: Verb, raw: str) -> tuple[Any, str | None]:
    """Parse + validate a raw string into ``verb``'s typed value at the trust boundary.

    Returns ``(value, None)`` on success or ``(None, reason)`` for a rejected input.
    """
    raw = (raw or "").strip()
    if verb.value_kind in ("int", "offset"):
        try:
            n = int(raw)
        except (TypeError, ValueError):
            return None, f"{verb.value_label} must be a whole number"
        if verb.value_kind == "offset":
            # a relative trim count: negatives extend; 0 is a no-op, not a frame.
            if n == 0:
                return None, "nothing to trim — enter a non-zero number of frames"
            return n, None
        if n < 0:
            return None, f"{verb.value_label} must be 0 or greater"
        return n, None
    if not raw:
        return None, f"{verb.value_label} must not be empty"
    return raw, None


def is_unchanged(verb: Verb, value: Any, current: Any) -> bool:
    """True when the verb's value is a no-op (nothing to do)."""
    if verb.value_kind == "offset":
        # an offset has no absolute "current": 0 is the no-op (parse_value already
        # rejects it; this is the belt-and-suspenders gate the renderers call).
        try:
            return int(value) == 0
        except (TypeError, ValueError):
            return False
    if verb.value_kind == "int":
        try:
            return current is not None and int(value) == int(current)
        except (TypeError, ValueError):
            return False
    return str(value) == str(current)


def validate_trim(verb: Verb, n: int, seg: dict[str, Any]) -> str | None:
    """CLI-side range guard for a relative trim — the legible-error UX fix.

    Rejects an impossible trim BEFORE it reaches the host (whose only signal for
    the common mistake is an opaque ``HOST_DISCOVER_FAILED`` -> "couldn't resolve
    the target"). Returns a plain-language reason, or ``None`` when in range / not
    a trim verb. Checks (mirrors ``_expected_temporal_post_state`` on the host):
    trimming off >= the segment duration collapses it; extending (negative ``n``)
    beyond the available head/tail handle is impossible.
    """
    if verb.trim_side is None:
        return None
    duration = seg.get("duration")
    if isinstance(duration, int) and n >= duration:
        return f"can't trim {n} off a {duration}-frame segment"
    if n < 0:  # extend — consumes the handle on this side
        handle = seg.get("head" if verb.trim_side == "head" else "tail")
        if isinstance(handle, int) and -n > handle:
            return (f"can't extend the {verb.trim_side} by {-n} — only {handle} "
                    f"frame{'' if handle == 1 else 's'} of handle available")
    return None


def describe_change(verb: Verb, current: Any, value: Any) -> str:
    """One-line, artist-legible summary of a verb's change for the preview.

    Offset verbs never leak an absolute frame ("trim 10 off the head"); other
    verbs show the before->after of their single edited value.
    """
    if verb.value_kind == "offset":
        n = int(value)
        return (f"trim {abs(n)} frame{'' if abs(n) == 1 else 's'} "
                f"{'off' if n > 0 else 'onto'} the {verb.trim_side}")
    return f"{current}  →  {value}"


# -- multi-segment fan-out (Approach A: ONE multi-entry TimelineDelta) ---------
# A selection of N segments rides the SAME rail as one: a single TimelineDelta
# carrying N DeltaEntry rows (host_resolve resolves each, commit applies all).
# The builders accept ``values["segments"]`` (a list) and treat the legacy
# ``values["segment"]`` as the one-element case, so a single-segment build stays
# byte-identical to before (a 1-element list -> exactly the old 1-entry delta).

_COUNTER_TOKENS = ("$nnn", "$nn", "$n", "$iteration")


def has_counter(template: str) -> bool:
    """True when ``template`` carries a per-segment counter token (see ``expand_counter``)."""
    return any(tok in template for tok in _COUNTER_TOKENS)


def expand_counter(template: str, index: int, count: int) -> str:
    """Expand a per-iteration counter token in a rename ``template``.

    ``$n``/``$iteration`` -> bare 1-based ``index`` (1, 2, …); ``$nn`` -> width-2
    zero-pad (01, 02, …); ``$nnn`` -> width-3. ``index`` is the segment's position
    in TIMELINE order (see ``timeline_sorted``) so the numbering runs left-to-right
    as the eye expects. ``count`` (the batch size) is accepted for the caller's
    symmetry; the token widths are explicit, so it is not consulted here. Longest
    token first so ``$nnn`` is never eaten by ``$n``.
    """
    out = template.replace("$iteration", str(index))
    out = out.replace("$nnn", f"{index:03d}")
    out = out.replace("$nn", f"{index:02d}")
    out = out.replace("$n", str(index))
    return out


def timeline_sorted(segs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Order segments left-to-right on the timeline: ``(track_idx, in-point)`` asc.

    Prefers the numeric ``record_in_frame`` for a correct chronological order,
    falling back to the ``record_in`` timecode string when the frame is absent
    (the kind-flag in the key keeps int/str frames from being compared). Stable +
    idempotent, so a caller may pre-sort and the builder re-sort harmlessly.
    """
    def key(s: dict[str, Any]) -> tuple:
        ti = int(s.get("track_idx", 0) or 0)
        rif = s.get("record_in_frame")
        if isinstance(rif, int):
            return (ti, 0, rif, "")
        return (ti, 1, 0, str(s.get("record_in", "")))
    return sorted(segs, key=key)


def _segments_of(values: dict[str, Any]) -> list[dict[str, Any]]:
    """The timeline-sorted segment list for a build — ``segments`` or legacy ``segment``."""
    segs = values.get("segments")
    if segs is None:
        segs = [values["segment"]]
    return timeline_sorted(segs)


def _entry_metadata(seg: dict[str, Any], sequence_name: Any) -> dict[str, Any]:
    """The shared host-identity metadata block for one DeltaEntry."""
    return {
        "track_idx": int(seg["track_idx"]),
        "record_in": str(seg["record_in"]),
        "seg_name": str(seg["seg_name"]),
        "source_name": str(seg["source_name"]),
        "sequence_name": str(sequence_name),
    }


def build_rename_delta(values: dict[str, Any]) -> dict[str, Any]:
    """Build a host-neutral rename TimelineDelta dict (1..N segments).

    ``values`` carries ``sequence_name``, the segment(s) (``segments`` list, or
    the legacy single ``segment`` — the full dict(s) from
    ``flame_get_sequence_segments``, supplying track_idx/record_in/source_name/
    seg_name so the artist never types Flame identity), and ``new_name``. A
    single-segment rename takes ``new_name`` LITERALLY (byte-identical to before);
    a multi-segment rename treats it as a counter TEMPLATE and expands the token
    (``$n``/``$nn``/``$nnn``/``$iteration``) per timeline-ordered index.
    """
    from forge_core.traffik.editing import DeltaEntry, TimelineDelta  # lazy

    segs = _segments_of(values)
    template = str(values["new_name"])
    count = len(segs)
    entries = [
        DeltaEntry(
            action="updated",
            object_type="segment",
            object_id="exec-rename",
            before={"id": "exec-rename", "name": str(seg["seg_name"])},
            # a counter only makes sense across a batch; a lone rename is literal
            after={"id": "exec-rename",
                   "name": expand_counter(template, i, count) if count > 1 else template},
            metadata=_entry_metadata(seg, values["sequence_name"]),
        )
        for i, seg in enumerate(segs, 1)
    ]
    return TimelineDelta(sequence_id="fbridge-exec-rename", entries=entries).to_dict()


def _build_trim_delta(
    values: dict[str, Any], *, field: str, frame_key: str, sign: int
) -> dict[str, Any]:
    """Build a host-neutral relative-trim TimelineDelta dict (1..N segments, one field).

    A trim rides the temporal-delta rail: each entry's single changed field
    (``frame_in`` head / ``frame_out`` tail) is lowered by the host_resolve
    operation to ``forge_apply_segment_temporal_delta`` (the only protocol-
    compliant temporal executor). The host derives the OFFSET internally from
    ``after - before``, so the SAME artist-facing ``count`` applies to every
    selected segment and the absolute frame stays internal. ``sign`` is +1 for a
    head trim (in-point later) and -1 for a tail trim (out-point earlier).
    ``values`` carries ``sequence_name`` + the segment(s) (``segments`` / legacy
    ``segment``) supplying the identity metadata + per-segment ``frame_key``.
    """
    from forge_core.traffik.editing import DeltaEntry, TimelineDelta  # lazy

    segs = _segments_of(values)
    count = int(values["count"])
    entries = [
        DeltaEntry(
            action="updated",
            object_type="segment",
            object_id="exec-trim",
            # single changed field -> classified as a supported temporal trim
            before={"id": "exec-trim", field: int(seg[frame_key])},
            after={"id": "exec-trim", field: int(seg[frame_key]) + sign * count},
            metadata=_entry_metadata(seg, values["sequence_name"]),
        )
        for seg in segs
    ]
    return TimelineDelta(sequence_id="fbridge-exec-trim", entries=entries).to_dict()


def build_trim_head_delta(values: dict[str, Any]) -> dict[str, Any]:
    """Head-trim: positive ``count`` trims off (in-point later), negative extends.

    ``after_frame_in = record_in_frame + count`` so the host's offset
    (``after - before``) equals ``count`` (positive moves the in-point later /
    shortens; negative extends, consuming a head handle).
    """
    return _build_trim_delta(values, field="frame_in", frame_key="record_in_frame", sign=1)


def build_trim_tail_delta(values: dict[str, Any]) -> dict[str, Any]:
    """Tail-trim: positive ``count`` trims off (out-point earlier), negative extends.

    ``after_frame_out = record_out_frame - count`` so the host's offset
    (``before - after``) equals ``count`` (positive moves the out-point earlier /
    shortens; negative extends, consuming a tail handle).
    """
    return _build_trim_delta(values, field="frame_out", frame_key="record_out_frame", sign=-1)


def build_host_mutation_spec(delta_dict: dict[str, Any], operator_id: str) -> Any:
    """operation(projects delta) -> delta_to_manifest (discover).

    The PREVIEW spec — resolves the held manifest, no commit. Apply replays the
    held manifest through ``graph_replay_commit_spec`` (commit takes ``held`` via
    config, not an edge), exactly as ``fbridge ratify`` does. Proven in slice 1.
    """
    from forge_bridge.composition.graph_spec import GraphSpec, NodeSpec, Edge
    from forge_bridge.composition.host_resolve_boundary import HostResolveBoundary

    return GraphSpec(
        nodes=(
            NodeSpec(node_id="op", operator_id=operator_id,
                     config={"arguments": {"delta": delta_dict}}),
            NodeSpec(node_id="delta_to_manifest", operator_id="delta_to_manifest",
                     input_ports=HostResolveBoundary.input_ports,
                     output_port=HostResolveBoundary.output_port),
        ),
        edges=(Edge(from_node="op", to_node="delta_to_manifest", to_port="deltas"),),
    )


_HOST_RESOLVE_OP = "traffik.flame_delta.host_resolve"

# ponytail: these verbs are Bridge-INTERNAL operators (host_resolve /
# delta_to_manifest are AdmissionRecord entries, NOT peer CapabilityDeclarations),
# so their ``summary`` here IS the canonical author — the derived-fallback path of
# the description seam (orchestration.registration.artist_description). They are not
# routed through that resolver because there is no peer summary to prefer.
REGISTRY: dict[str, Verb] = {
    "rename": Verb(
        name="rename",
        label="Rename a segment",
        summary="Rename a segment in the open Flame sequence (reversible, ratified).",
        build_delta=build_rename_delta,
        value_field="new_name",
        value_kind="str",
        value_label="New name",
        current_key="seg_name",
    ),
    "trim_head": Verb(
        name="trim_head",
        label="Trim a segment's head",
        summary="Trim frames off (or onto) a segment's head in the open Flame "
                "sequence — positive shortens, negative extends (reversible, ratified).",
        build_delta=build_trim_head_delta,
        value_field="count",
        value_kind="offset",
        value_label="Frames to trim off the head (negative = extend)",
        current_key="record_in_frame",
        trim_side="head",
    ),
    "trim_tail": Verb(
        name="trim_tail",
        label="Trim a segment's tail",
        summary="Trim frames off (or onto) a segment's tail in the open Flame "
                "sequence — positive shortens, negative extends (reversible, ratified).",
        build_delta=build_trim_tail_delta,
        value_field="count",
        value_kind="offset",
        value_label="Frames to trim off the tail (negative = extend)",
        current_key="record_out_frame",
        trim_side="tail",
    ),
}


def host_resolve_operator() -> str:
    return _HOST_RESOLVE_OP


def list_verbs() -> list[Verb]:
    return list(REGISTRY.values())

# Coverage: tests/cli/test_exec_verbs.py (delta envelope, spec wiring, registry).
