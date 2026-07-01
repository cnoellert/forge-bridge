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

# Single source of truth for the per-segment rename authoring: the counter
# helpers, the entry-identity metadata block, and the per-entry builder now live
# in ``forge_bridge.graph.editorial_delta`` so the CLI hand-build here and the
# composition ``RenameDeltaNode`` stay byte-identical (no logic fork). Re-imported
# into this module's namespace so ``verbs.expand_counter`` / ``verbs.has_counter``
# / ``verbs.validate_counter`` keep resolving for existing renderers + tests.
from forge_bridge.graph.editorial_delta import (  # noqa: F401 (re-exported)
    RENAME_SEQUENCE_ID,
    TRIM_SEQUENCE_ID,
    _entry_metadata,
    build_rename_entry,
    build_trim_entry,
    expand_counter,
    has_counter,
    validate_counter,
)


class TimelineOrderError(ValueError):
    """The segments reaching an order-SENSITIVE graph fan-out are not timeline-ordered.

    Raised fail-closed at the counter-rename graph-assembly edge
    (``build_rename_fanout_spec``) when a ``$n`` counter template would number
    segments by foreach ARRIVAL index while the arrival order is not timeline
    order — which would silently stamp the wrong shot numbers. The gather boundary
    (``interactive._match_selected``) is the single home that guarantees the order;
    this is the assert that keeps a future caller from bypassing it. Surfaced to
    the operator through the normal preview fail path (never silently applied).
    """


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
#
# The per-segment counter helpers (``has_counter`` / ``expand_counter`` /
# ``validate_counter``) + ``_entry_metadata`` + ``build_rename_entry`` now live in
# ``forge_bridge.graph.editorial_delta`` (imported at the top of this module) so
# the composition ``RenameDeltaNode`` reuses the SAME authoring code.


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


def build_rename_delta(values: dict[str, Any]) -> dict[str, Any]:
    """Build a host-neutral rename TimelineDelta dict (1..N segments).

    ``values`` carries ``sequence_name``, the segment(s) (``segments`` list, or
    the legacy single ``segment`` — the full dict(s) from
    ``flame_get_sequence_segments``, supplying track_idx/record_in/source_name/
    seg_name so the artist never types Flame identity), and ``new_name``. A
    name with NO counter token applies LITERALLY to every segment (single or
    multi — byte-identical to the legacy single build); a name carrying ``$n`` /
    ``$iteration`` (optional ``{width,start,step}``) expands per 0-based
    timeline-ordered position (see ``expand_counter``).

    The per-entry authoring is ``build_rename_entry`` — the SAME primitive the
    composition ``RenameDeltaNode`` calls, so the CLI hand-build and the graph
    author stay byte-identical.
    """
    from forge_core.traffik.editing import TimelineDelta  # lazy

    segs = _segments_of(values)
    template = str(values["new_name"])
    entries = [
        build_rename_entry(seg, template, i, values["sequence_name"])
        for i, seg in enumerate(segs)
    ]
    return TimelineDelta(sequence_id=RENAME_SEQUENCE_ID, entries=entries).to_dict()


def _build_trim_delta(
    values: dict[str, Any], *, trim_side: str
) -> dict[str, Any]:
    """Build a host-neutral relative-trim TimelineDelta dict (1..N segments, one field).

    A trim rides the temporal-delta rail: each entry's single changed field
    (``frame_in`` head / ``frame_out`` tail) is lowered by the host_resolve
    operation to ``forge_apply_segment_temporal_delta`` (the only protocol-
    compliant temporal executor). The host derives the OFFSET internally from
    ``after - before``, so the SAME artist-facing ``count`` applies to every
    selected segment and the absolute frame stays internal. ``trim_side``
    (``head`` / ``tail``) selects the changed field + the sign.

    The per-entry authoring is ``build_trim_entry`` — the SAME primitive the
    composition ``TrimDeltaNode`` calls, so the CLI hand-build and the graph
    author stay byte-identical. ``values`` carries ``sequence_name`` + the
    segment(s) (``segments`` / legacy ``segment``) supplying the identity
    metadata + per-segment frame value.
    """
    from forge_core.traffik.editing import TimelineDelta  # lazy

    segs = _segments_of(values)
    count = int(values["count"])
    entries = [
        build_trim_entry(seg, count, trim_side, values["sequence_name"])
        for seg in segs
    ]
    return TimelineDelta(sequence_id=TRIM_SEQUENCE_ID, entries=entries).to_dict()


def build_trim_head_delta(values: dict[str, Any]) -> dict[str, Any]:
    """Head-trim: positive ``count`` trims off (in-point later), negative extends.

    ``after_frame_in = record_in_frame + count`` so the host's offset
    (``after - before``) equals ``count`` (positive moves the in-point later /
    shortens; negative extends, consuming a head handle).
    """
    return _build_trim_delta(values, trim_side="head")


def build_trim_tail_delta(values: dict[str, Any]) -> dict[str, Any]:
    """Tail-trim: positive ``count`` trims off (out-point earlier), negative extends.

    ``after_frame_out = record_out_frame - count`` so the host's offset
    (``before - after``) equals ``count`` (positive moves the out-point earlier /
    shortens; negative extends, consuming a tail handle).
    """
    return _build_trim_delta(values, trim_side="tail")


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


def build_rename_fanout_spec(
    segments: list[dict[str, Any]],
    template: str,
    sequence_name: Any,
) -> Any:
    """Author the GRAPH fan-out rename spec (counter-free literal rename only).

    The production promotion of the offline ``_fanout_graph`` proof
    (``tests/composition/test_m2_batch_author_foreach.py``). Instead of
    hand-building a multi-entry ``TimelineDelta`` in Python (``build_rename_delta``
    -> ``build_host_mutation_spec``), the graph AUTHORS it::

        literal_source(segments)
            -> foreach( rename_delta_entry )   # per-item single-entry delta
            -> collect                          # fold N single-entry -> one multi-entry
            -> traffik.flame_delta.host_resolve # project delta -> host-resolve payload
            -> delta_to_manifest                # resolve payload -> MutationManifest

    It rides the SAME ``preview_editorial_delta`` / ``apply_editorial_delta`` rail
    downstream (``host_resolve`` + ``delta_to_manifest`` are the identical nodes
    ``build_host_mutation_spec`` uses; the source of the ``delta`` is the only
    thing that changes — a graph author, not a CLI hand-build).

    Authors BOTH the counter-free literal rename AND the ``$n`` counter rename.
    A literal template returns the name unchanged for every segment, so it is
    order-agnostic and needs no ordering step. A ``$n`` counter numbers each
    segment by its foreach ARRIVAL index, so it is order-SENSITIVE — correct only
    when the arrival order IS timeline order. This function is the counter graph's
    ASSEMBLY EDGE, so it asserts that invariant fail-closed here: a counter
    template over segments that are not ``timeline_sorted`` raises
    ``TimelineOrderError`` (the single definition of order is ``timeline_sorted``)
    rather than silently stamping the wrong shot numbers. The invariant is
    established upstream at the gather boundary (``interactive._match_selected``);
    this assert catches any caller that bypasses it. The check is scoped to counter
    templates: a literal rename is order-agnostic, so it is accepted on unsorted
    input with no ordering step (see ``.planning/CONVERGENCE-foreach-cutover.md``).
    ``fixture_source`` in the offline proof is replaced by the admitted
    ``literal_source`` primitive so the spec runs through the real
    ``UnifiedDispatch`` (no test seam).
    """
    from forge_bridge.composition.graph_spec import GraphSpec, NodeSpec, Edge
    from forge_bridge.composition.host_resolve_boundary import HostResolveBoundary
    from forge_bridge.graph.ports import PortContract, PortTopology

    # Fail-closed assert-at-edge: an order-SENSITIVE counter template requires the
    # foreach arrival order to be timeline order. Reuse ``timeline_sorted`` as the
    # single definition of order. Literal templates are order-agnostic (skipped).
    if has_counter(str(template)):
        segs = list(segments)
        if segs != timeline_sorted(segs):
            raise TimelineOrderError(
                "counter rename needs the selected segments in timeline order, "
                "but they reached the graph unsorted — refusing rather than "
                "stamping the wrong numbers"
            )

    return GraphSpec(
        nodes=(
            NodeSpec(
                node_id="segments",
                operator_id="literal_source",
                output_port=PortTopology.list_of("segment"),
                config={"output": {"segments": list(segments)}},
            ),
            NodeSpec(
                node_id="foreach",
                operator_id="foreach",
                input_ports={"input": PortContract.any()},
                output_port=PortTopology.iteration_results(),
                config={
                    "body": NodeSpec(
                        node_id="rename_body",
                        operator_id="rename_delta_entry",
                        input_ports={"item": PortContract.any()},
                        output_port=PortTopology.manifest(),
                        config={
                            "new_name": str(template),
                            "sequence_name": str(sequence_name),
                        },
                    )
                },
            ),
            NodeSpec(
                node_id="collect",
                operator_id="collect",
                input_ports={"input": PortContract.any()},
                output_port=PortTopology.manifest(),
            ),
            NodeSpec(
                node_id="host_resolve",
                operator_id=_HOST_RESOLVE_OP,
                input_ports={"delta": PortContract.manifest_gate()},
                output_port=PortTopology.manifest(),
            ),
            NodeSpec(
                node_id="delta_to_manifest",
                operator_id="delta_to_manifest",
                input_ports=HostResolveBoundary.input_ports,
                output_port=HostResolveBoundary.output_port,
            ),
        ),
        edges=(
            Edge(from_node="segments", to_node="foreach", to_port="input"),
            Edge(from_node="foreach", to_node="collect", to_port="input"),
            Edge(from_node="collect", to_node="host_resolve", to_port="delta"),
            Edge(
                from_node="host_resolve",
                to_node="delta_to_manifest",
                to_port="deltas",
            ),
        ),
    )


def build_trim_fanout_spec(
    segments: list[dict[str, Any]],
    count: int,
    trim_side: str,
    sequence_name: Any,
) -> Any:
    """Author the GRAPH fan-out relative-trim spec (order-insensitive).

    The trim analog of ``build_rename_fanout_spec``. Instead of hand-building a
    multi-entry ``TimelineDelta`` in Python (``_build_trim_delta`` ->
    ``build_host_mutation_spec``), the graph AUTHORS it::

        literal_source(segments)
            -> foreach( trim_delta_entry )      # per-item single-entry temporal delta
            -> collect                          # fold N single-entry -> one multi-entry
            -> traffik.flame_delta.host_resolve # project delta -> host-resolve payload
            -> delta_to_manifest                # resolve payload -> MutationManifest

    It rides the SAME ``preview_editorial_delta`` / ``apply_editorial_delta`` rail
    downstream as rename — and, crucially, the SAME ``host_resolve`` operator
    (``traffik.flame_delta.host_resolve``). The TEMPORAL executor
    (``forge_apply_segment_temporal_delta``, vs. rename's spatial
    ``forge_apply_segment_delta``) is selected inside that operation from the delta
    CONTENT — ``build_trim_entry`` authors a single ``frame_in`` / ``frame_out``
    change, which the operation classifies as a temporal trim. There is no separate
    temporal host-resolve operator id.

    A trim is order-AGNOSTIC (each entry's offset depends only on that segment's own
    frame value + the shared ``count``, downstream is identity-keyed), so it is safe
    on unsorted input with NO ordering step — the same property that let literal
    rename skip a sort. ``count`` is the signed artist-facing frame count;
    ``trim_side`` is ``head`` / ``tail``.
    """
    from forge_bridge.composition.graph_spec import GraphSpec, NodeSpec, Edge
    from forge_bridge.composition.host_resolve_boundary import HostResolveBoundary
    from forge_bridge.graph.ports import PortContract, PortTopology

    return GraphSpec(
        nodes=(
            NodeSpec(
                node_id="segments",
                operator_id="literal_source",
                output_port=PortTopology.list_of("segment"),
                config={"output": {"segments": list(segments)}},
            ),
            NodeSpec(
                node_id="foreach",
                operator_id="foreach",
                input_ports={"input": PortContract.any()},
                output_port=PortTopology.iteration_results(),
                config={
                    "body": NodeSpec(
                        node_id="trim_body",
                        operator_id="trim_delta_entry",
                        input_ports={"item": PortContract.any()},
                        output_port=PortTopology.manifest(),
                        config={
                            "count": int(count),
                            "trim_side": str(trim_side),
                            "sequence_name": str(sequence_name),
                        },
                    )
                },
            ),
            NodeSpec(
                node_id="collect",
                operator_id="collect",
                input_ports={"input": PortContract.any()},
                output_port=PortTopology.manifest(),
            ),
            NodeSpec(
                node_id="host_resolve",
                operator_id=_HOST_RESOLVE_OP,
                input_ports={"delta": PortContract.manifest_gate()},
                output_port=PortTopology.manifest(),
            ),
            NodeSpec(
                node_id="delta_to_manifest",
                operator_id="delta_to_manifest",
                input_ports=HostResolveBoundary.input_ports,
                output_port=HostResolveBoundary.output_port,
            ),
        ),
        edges=(
            Edge(from_node="segments", to_node="foreach", to_port="input"),
            Edge(from_node="foreach", to_node="collect", to_port="input"),
            Edge(from_node="collect", to_node="host_resolve", to_port="delta"),
            Edge(
                from_node="host_resolve",
                to_node="delta_to_manifest",
                to_port="deltas",
            ),
        ),
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
