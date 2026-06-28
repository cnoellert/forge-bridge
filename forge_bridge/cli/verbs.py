"""Artist-facing verb registry — the renderer-agnostic vocabulary layer.

A *verb* is an artist-legible action ("Rename a shot") that knows how to turn a
few plain-language values into a host-mutation ``GraphSpec`` riding the proven
preview->ratify->apply rail (``forge_apply_segment_delta``). The interactive
``fbridge exec`` shell is the first renderer of this registry; a web card is a
later renderer of the same data. Verbs are DATA; surfaces are interchangeable.

``forge_core``/composition imports are lazy so ``fbridge --help`` stays fast and
this module imports cleanly without the pipeline plugin installed.

ponytail: with verb #2 (trim) here, the n=1->n=2 generalization landed. The two
verbs (rename + trim) differ only in their single edited value (a name STRING vs
an in-point frame INT) and which segment field holds its current value --
captured by the ``value_*``/``current_key`` fields below + ``parse_value`` (the
trust-boundary typed parse), so the renderers carry zero per-verb branching. Both
share one renderer-agnostic path. Still deferred to verb #3: multi-field verbs,
segment_picker/sequence_picker as declared field kinds, and value kinds beyond
str/int -- not invented before something needs them.
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
    value_kind: str         # "str" | "int"
    value_label: str        # prompt label, e.g. "New name" / "New start frame"
    current_key: str        # segment dict key holding the current value
    # identity fields the verb needs resolved from the live host before build
    needs_segment: bool = True


def parse_value(verb: Verb, raw: str) -> tuple[Any, str | None]:
    """Parse + validate a raw string into ``verb``'s typed value at the trust boundary.

    Returns ``(value, None)`` on success or ``(None, reason)`` for a rejected input.
    """
    raw = (raw or "").strip()
    if verb.value_kind == "int":
        try:
            n = int(raw)
        except (TypeError, ValueError):
            return None, f"{verb.value_label} must be a whole number"
        if n < 0:
            return None, f"{verb.value_label} must be 0 or greater"
        return n, None
    if not raw:
        return None, f"{verb.value_label} must not be empty"
    return raw, None


def is_unchanged(verb: Verb, value: Any, current: Any) -> bool:
    """True when the new value equals the segment's current value (nothing to do)."""
    if verb.value_kind == "int":
        try:
            return current is not None and int(value) == int(current)
        except (TypeError, ValueError):
            return False
    return str(value) == str(current)


def build_rename_delta(values: dict[str, Any]) -> dict[str, Any]:
    """Build a host-neutral rename TimelineDelta dict from collected values.

    ``values`` must carry: ``sequence_name``, ``segment`` (the full segment dict
    from ``flame_get_sequence_segments`` — supplies track_idx/record_in/
    source_name/seg_name so the artist never types Flame identity), ``new_name``.
    """
    from forge_core.traffik.editing import DeltaEntry, TimelineDelta  # lazy

    seg = values["segment"]
    before = str(seg["seg_name"])
    after = str(values["new_name"])
    delta = TimelineDelta(
        sequence_id="fbridge-exec-rename",
        entries=[DeltaEntry(
            action="updated",
            object_type="segment",
            object_id="exec-rename",
            before={"id": "exec-rename", "name": before},
            after={"id": "exec-rename", "name": after},
            metadata={
                "track_idx": int(seg["track_idx"]),
                "record_in": str(seg["record_in"]),
                "seg_name": before,
                "source_name": str(seg["source_name"]),
                "sequence_name": str(values["sequence_name"]),
            },
        )],
    )
    return delta.to_dict()


def build_trim_delta(values: dict[str, Any]) -> dict[str, Any]:
    """Build a host-neutral head-trim TimelineDelta dict from collected values.

    A head-trim rides the temporal-delta rail: a single-field ``frame_in`` update
    (the segment's timeline in-point) lowered by the host_resolve operation to
    ``forge_apply_segment_temporal_delta`` (the only protocol-compliant temporal
    executor — ``updated_segment_trim``; shifting frame_in moves the in-point and
    so the start frame / head / duration together). There is no pure metadata
    start-frame *renumber* executor on the rail. ``values`` must carry:
    ``sequence_name``, ``segment`` (the full segment dict from
    ``flame_get_sequence_segments`` — supplies track_idx/record_in/
    record_in_frame/source_name/seg_name), and ``new_frame`` (the new in-point).
    """
    from forge_core.traffik.editing import DeltaEntry, TimelineDelta  # lazy

    seg = values["segment"]
    before = int(seg["record_in_frame"])
    after = int(values["new_frame"])
    delta = TimelineDelta(
        sequence_id="fbridge-exec-start-frames",
        entries=[DeltaEntry(
            action="updated",
            object_type="segment",
            object_id="exec-start-frames",
            # single changed field -> classified as a supported temporal trim
            before={"id": "exec-start-frames", "frame_in": before},
            after={"id": "exec-start-frames", "frame_in": after},
            metadata={
                "track_idx": int(seg["track_idx"]),
                "record_in": str(seg["record_in"]),
                "seg_name": str(seg["seg_name"]),
                "source_name": str(seg["source_name"]),
                "sequence_name": str(values["sequence_name"]),
            },
        )],
    )
    return delta.to_dict()


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
    "trim": Verb(
        name="trim",
        label="Trim a segment's head",
        summary="Move a segment's in-point in the open Flame sequence — head-trim; "
                "shifts start frame/duration (reversible, ratified).",
        build_delta=build_trim_delta,
        value_field="new_frame",
        value_kind="int",
        value_label="New in-point frame",
        current_key="record_in_frame",
    ),
}


def host_resolve_operator() -> str:
    return _HOST_RESOLVE_OP


def list_verbs() -> list[Verb]:
    return list(REGISTRY.values())

# Coverage: tests/cli/test_exec_verbs.py (delta envelope, spec wiring, registry).
