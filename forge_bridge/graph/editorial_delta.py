"""Shared editorial-delta authoring helpers + the per-item rename graph node.

This module is the SINGLE SOURCE OF TRUTH for the per-segment transform logic
that both surfaces need:

  * the interactive ``fbridge exec`` fan-out (``cli/verbs.py`` imports the
    counter helpers + ``_entry_metadata`` + ``build_rename_entry`` from here), and
  * the composition graph (``RenameDeltaNode`` is the foreach body node that maps
    ONE segment item to ONE single-entry ``TimelineDelta``).

Keeping the entry-authoring in one place is load-bearing: the CLI hand-build and
the graph author must stay byte-identical while both exist, so they call the SAME
per-entry primitive — no logic fork. Two verb families live here:

  * rename — ``build_rename_delta`` (CLI) + ``RenameDeltaNode`` (graph) share
    ``build_rename_entry`` / ``expand_counter`` / ``_entry_metadata``;
  * relative trim — ``_build_trim_delta`` (CLI) + ``TrimDeltaNode`` (graph) share
    ``build_trim_entry`` (+ ``_entry_metadata``). A trim is order-INSENSITIVE (a
    per-segment identity-keyed offset, no ``$n`` counter, no position), so it needs
    no timeline-ordering step.

``forge_core`` is imported lazily inside the entry builders / graph nodes
so this module (and everything that imports it, including ``fbridge --help``)
loads cleanly without the pipeline plugin installed. Graph stays peer-import-free
at module level.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, ClassVar

from forge_bridge.graph.foreach import FOREACH_INDEX_KEY, FOREACH_META_KEY
from forge_bridge.graph.ports import PortContract, PortTopology

# The canonical identity literals of an ``fbridge exec`` rename delta. They are
# defined ONCE here so the CLI multi-entry build and the per-item graph node
# emit the same ``sequence_id`` / ``object_id`` byte-for-byte.
RENAME_SEQUENCE_ID = "fbridge-exec-rename"
_RENAME_OBJECT_ID = "exec-rename"

# Same discipline for the relative-trim delta: defined ONCE so the CLI hand-build
# (``_build_trim_delta``) and the per-item graph node (``TrimDeltaNode``) emit a
# byte-identical ``sequence_id`` / ``object_id``.
TRIM_SEQUENCE_ID = "fbridge-exec-trim"
_TRIM_OBJECT_ID = "exec-trim"

# The per-side trim geometry: which single field the delta changes, which segment
# frame key holds its current value, and the sign the artist-facing count is
# applied with. ``head`` moves the in-point later (+count shortens); ``tail`` moves
# the out-point earlier (-count shortens). A single changed frame field is what the
# ``traffik.flame_delta.host_resolve`` operation classifies as a TEMPORAL trim,
# routing it to ``forge_apply_segment_temporal_delta`` (vs. rename's spatial
# ``forge_apply_segment_delta``) — the executor is selected from the delta CONTENT,
# not a different host-resolve operator id.
_TRIM_SIDES: dict[str, tuple[str, str, int]] = {
    "head": ("frame_in", "record_in_frame", 1),
    "tail": ("frame_out", "record_out_frame", -1),
}


# A per-segment counter token: ``$n`` / ``$iteration`` with an OPTIONAL
# ``{width[,start[,step]]}`` spec. This single form REPLACES the old
# ``$nn``/``$nnn`` repetition padding (one syntax, not two): ``$n`` -> 1,2,3
# (no pad); ``$n{3}`` -> 001,002,003; ``$n{3,10}`` -> 010,011,012 (start at 10);
# ``$n{3,10,10}`` -> 010,020,030 (start 10, step 10 -- the ``sh###`` convention).
_COUNTER_RE = re.compile(r"\$(?:n|iteration)(?:\{([^}]*)\})?")


def has_counter(template: str) -> bool:
    """True when ``template`` carries a per-segment counter token (see ``expand_counter``)."""
    return _COUNTER_RE.search(template) is not None


def _counter_spec(body: str | None) -> tuple[int, int, int]:
    """Parse a ``{width[,start[,step]]}`` body into ``(width, start, step)``.

    ``body is None`` (a bare ``$n``) -> ``(0, 1, 1)``: no pad, start 1, step 1.
    Raises ``ValueError`` for a malformed body (empty, a non-int field, a negative
    width, or >3 fields) so the renderer can reject the value legibly via
    ``validate_counter`` instead of silently mangling the name.
    """
    if body is None:
        return 0, 1, 1
    fields = body.split(",")
    if not (1 <= len(fields) <= 3):
        raise ValueError(body)
    nums = [int(f) for f in fields]          # ValueError on an empty / non-int field
    width = nums[0]
    if width < 0:
        raise ValueError(body)
    start = nums[1] if len(nums) > 1 else 1
    step = nums[2] if len(nums) > 2 else 1
    return width, start, step


def expand_counter(template: str, position: int) -> str:
    """Expand every counter token in ``template`` for a segment at 0-based ``position``.

    The rendered value is ``start + position*step`` zero-padded to ``width``
    (width 0 = no pad). ``position`` is the segment's index in TIMELINE order
    (see ``timeline_sorted``) so the numbering runs left-to-right as the eye
    expects. Multiple tokens in one template all render the SAME value. A template
    carrying NO token is returned unchanged, so a literal rename -- single OR
    multi -- is byte-identical to the legacy build. Raises ``ValueError`` on a
    malformed spec; callers gate with ``validate_counter`` first.
    """
    def _sub(m: re.Match[str]) -> str:
        width, start, step = _counter_spec(m.group(1))
        return f"{start + position * step:0{width}d}"
    return _COUNTER_RE.sub(_sub, template)


def validate_counter(template: str) -> str | None:
    """A legible reason ``template``'s counter spec is malformed, else ``None``.

    Lets the renderers reject ``$n{}`` / ``$n{x}`` / a non-int or >3-field spec
    BEFORE the builder expands it -- no silently-mangled names. A token-free
    template is always valid (the literal applies to every selected segment).
    """
    for m in _COUNTER_RE.finditer(template):
        try:
            _counter_spec(m.group(1))
        except ValueError:
            return (f"bad counter format {m.group(0)!r} — "
                    f"use $n{{width,start,step}}, e.g. $n{{3,10,10}}")
    return None


def _entry_metadata(seg: dict[str, Any], sequence_name: Any) -> dict[str, Any]:
    """The shared host-identity metadata block for one DeltaEntry."""
    return {
        "track_idx": int(seg["track_idx"]),
        "record_in": str(seg["record_in"]),
        "seg_name": str(seg["seg_name"]),
        "source_name": str(seg["source_name"]),
        "sequence_name": str(sequence_name),
    }


def build_rename_entry(
    seg: dict[str, Any],
    template: str,
    position: int,
    sequence_name: Any,
) -> Any:
    """Author ONE rename ``DeltaEntry`` for segment ``seg`` at 0-based ``position``.

    This is THE per-segment rename authoring primitive. ``build_rename_delta``
    (the CLI multi-entry hand-build) and ``RenameDeltaNode`` (the graph foreach
    body) both call it, so the two paths cannot drift. A token-free ``template``
    applies literally (``expand_counter`` returns it unchanged); a ``$n`` /
    ``$iteration`` token expands per 0-based timeline ``position``.
    """
    from forge_core.traffik.editing import DeltaEntry  # lazy: pipeline plugin

    return DeltaEntry(
        action="updated",
        object_type="segment",
        object_id=_RENAME_OBJECT_ID,
        before={"id": _RENAME_OBJECT_ID, "name": str(seg["seg_name"])},
        after={"id": _RENAME_OBJECT_ID, "name": expand_counter(template, position)},
        metadata=_entry_metadata(seg, sequence_name),
    )


def build_trim_entry(
    seg: dict[str, Any],
    count: int,
    trim_side: str,
    sequence_name: Any,
) -> Any:
    """Author ONE relative-trim ``DeltaEntry`` for segment ``seg``.

    THE per-segment trim authoring primitive. ``_build_trim_delta`` (the CLI
    multi-entry hand-build) and ``TrimDeltaNode`` (the graph foreach body) both
    call it, so the two paths cannot drift. ``count`` is the SIGNED artist-facing
    frame count (positive shortens, negative extends); ``trim_side`` (``head`` /
    ``tail``) selects the single changed field + the sign via ``_TRIM_SIDES``. The
    host derives the offset internally from ``after - before``, so the SAME count
    applies to every selected segment and the absolute frame stays internal.

    Order-INSENSITIVE by construction: each entry's before/after depends only on
    the segment's own frame value + count (no counter, no position), so a trim
    fan-out needs no timeline-ordering step.
    """
    from forge_core.traffik.editing import DeltaEntry  # lazy: pipeline plugin

    field, frame_key, sign = _TRIM_SIDES[trim_side]
    base = int(seg[frame_key])
    return DeltaEntry(
        action="updated",
        object_type="segment",
        object_id=_TRIM_OBJECT_ID,
        # single changed field -> classified as a supported temporal trim
        before={"id": _TRIM_OBJECT_ID, field: base},
        after={"id": _TRIM_OBJECT_ID, field: base + sign * int(count)},
        metadata=_entry_metadata(seg, sequence_name),
    )


def _item_position(item: dict[str, Any]) -> int:
    """The 0-based counter position for ``item``, from its foreach iteration index.

    Read from the reserved ``_foreach`` namespace that ``ForEachNode`` authors onto
    each per-iteration payload (default 0 when absent).
    """
    # ORDINAL-AS-COUNTER-POSITION GUARD: this is the foreach ARRIVAL-order index,
    # not a timeline position. Rendering it as a $n shot number is correct ONLY
    # under an upstream timeline-ordering guarantee on the collection fed to
    # foreach; nothing on this read path enforces that order.
    meta = item.get(FOREACH_META_KEY)
    if isinstance(meta, dict):
        try:
            return int(meta.get(FOREACH_INDEX_KEY, 0) or 0)
        except (TypeError, ValueError):
            return 0
    return 0


@dataclass(frozen=True)
class RenameDeltaNode:
    """Map ONE segment item to ONE single-entry rename ``TimelineDelta`` dict.

    The composition foreach body node for "fan-out A" rename: foreach hands this
    node one segment at a time, its iteration index authored under the reserved
    ``_foreach`` namespace (read via ``_item_position`` for a ``$n`` counter); a
    downstream ``collect`` folds the N single-entry deltas back into one
    multi-entry ``TimelineDelta`` byte-identical to the CLI hand-build. It AUTHORS
    a delta; it never applies (``no_state_mutation`` in admission) — ``commit``
    downstream owns application.
    """

    new_name: str
    sequence_name: str

    port_contract: ClassVar[PortContract] = PortContract(
        (PortTopology.any(),),
        PortTopology.manifest(),
    )

    def run(self, item: dict[str, Any]) -> dict[str, Any]:
        from forge_core.traffik.editing import TimelineDelta  # lazy: pipeline plugin

        entry = build_rename_entry(
            item, self.new_name, _item_position(item), self.sequence_name
        )
        return TimelineDelta(
            sequence_id=RENAME_SEQUENCE_ID, entries=[entry]
        ).to_dict()


@dataclass(frozen=True)
class TrimDeltaNode:
    """Map ONE segment item to ONE single-entry relative-trim ``TimelineDelta`` dict.

    The composition foreach body node for "fan-out A" trim: foreach hands this node
    one segment at a time; a downstream ``collect`` folds the N single-entry deltas
    back into one multi-entry ``TimelineDelta`` byte-identical to the CLI hand-build
    (``_build_trim_delta``). It reuses the SAME ``build_trim_entry`` primitive so the
    two paths cannot drift.

    Unlike ``RenameDeltaNode`` it does NOT read the foreach iteration index — a trim
    is position-INDEPENDENT (each entry's offset depends only on the segment's own
    frame value + the shared ``count``), so a trim fan-out carries no counter and no
    ordering seam. It AUTHORS a delta; it never applies (``no_state_mutation`` in
    admission) — ``commit`` downstream owns application.
    """

    count: int
    trim_side: str
    sequence_name: str

    port_contract: ClassVar[PortContract] = PortContract(
        (PortTopology.any(),),
        PortTopology.manifest(),
    )

    def run(self, item: dict[str, Any]) -> dict[str, Any]:
        from forge_core.traffik.editing import TimelineDelta  # lazy: pipeline plugin

        entry = build_trim_entry(
            item, self.count, self.trim_side, self.sequence_name
        )
        return TimelineDelta(
            sequence_id=TRIM_SEQUENCE_ID, entries=[entry]
        ).to_dict()
