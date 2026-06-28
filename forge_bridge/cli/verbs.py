"""Artist-facing verb registry — the renderer-agnostic vocabulary layer.

A *verb* is an artist-legible action ("Rename a shot") that knows how to turn a
few plain-language values into a host-mutation ``GraphSpec`` riding the proven
preview->ratify->apply rail (``forge_apply_segment_delta``). The interactive
``fbridge exec`` shell is the first renderer of this registry; a web card is a
later renderer of the same data. Verbs are DATA; surfaces are interchangeable.

``forge_core``/composition imports are lazy so ``fbridge --help`` stays fast and
this module imports cleanly without the pipeline plugin installed.

ponytail: rename ships its interaction concretely (pick a segment from the live
timeline, resolve identity behind the glass). The generic field-type framework
(segment_picker / sequence_picker as declared field kinds) gets extracted when
verb #2 and #3 exist to generalize from — not invented for n=1.
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
    # identity fields the verb needs resolved from the live host before build
    needs_segment: bool = True


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
        label="Rename a shot",
        summary="Rename a segment in the open Flame sequence (reversible, ratified).",
        build_delta=build_rename_delta,
    ),
}


def host_resolve_operator() -> str:
    return _HOST_RESOLVE_OP


def list_verbs() -> list[Verb]:
    return list(REGISTRY.values())


def _selfcheck() -> None:
    # Build a rename delta from a fake live-segment dict and assert the shape +
    # the GraphSpec wiring. Catches drift in the delta identity envelope / edges.
    seg = {
        "track_idx": 0, "record_in": "'01:00:00+00'",
        "seg_name": "shot_010", "source_name": "shot_010",
    }
    delta = build_rename_delta(
        {"sequence_name": "CUT", "segment": seg, "new_name": "shot_010_v2"}
    )
    entry = delta["changes"][0] if "changes" in delta else delta["entries"][0]
    assert entry["action"] == "updated"
    assert entry["after"]["name"] == "shot_010_v2"
    md = entry["metadata"]
    assert md["track_idx"] == 0 and md["sequence_name"] == "CUT"
    assert md["seg_name"] == "shot_010" and md["source_name"] == "shot_010"

    spec = build_host_mutation_spec(delta, _HOST_RESOLVE_OP)
    assert [n.node_id for n in spec.nodes] == ["op", "delta_to_manifest"]
    assert len(spec.edges) == 1 and spec.edges[0].to_port == "deltas"
    assert "rename" in REGISTRY
    print("verbs selfcheck OK")  # noqa: T201 — __main__ self-check


if __name__ == "__main__":
    _selfcheck()
