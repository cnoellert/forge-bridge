"""Live-cutover parity: the GRAPH-authored $n COUNTER rename == the CLI hand-build.

The counter-path step of the live foreach cutover routes a ``$n`` counter
multi-select rename through the graph-authored fan-out spec
(``verbs.build_rename_fanout_spec``) instead of the CLI hand-build
(``verbs.build_rename_delta`` -> ``verbs.build_host_mutation_spec``). Both feed
the SAME ``preview_editorial_delta`` / ``apply_editorial_delta`` rail.

Sibling to ``test_m2_live_fanout_cutover.py`` (the counter-FREE literal step).
Unlike a literal rename, a ``$n`` counter is ORDER-SENSITIVE: it numbers each
segment by its foreach ARRIVAL index, so it is correct only when the arrival
order IS timeline order. This suite proves two things:

  1. PARITY over timeline-ORDERED input — the graph-authored counter rename lands
     a byte-identical MutationManifest to the CLI hand-build, at n and n+1. The
     graph expands the counter from the real foreach iteration index
     (``RenameDeltaNode`` -> ``_foreach.index``, #135); the CLI expands it from
     the timeline position. Over sorted input both agree, byte-for-byte.

  2. ASSERT-FIRES on UNORDERED input — feeding the counter graph assembly an
     out-of-order selection raises ``verbs.TimelineOrderError`` (fail-closed),
     proving the guard is real and never silently stamps the wrong numbers. A
     LITERAL template over the SAME unsorted input is accepted (the assert is
     scoped to order-sensitive counters).

This exercises the PRODUCTION spec through the REAL ``UnifiedDispatch``: the
source is the admitted ``literal_source`` primitive and the body is the admitted
``rename_delta_entry`` primitive, so nothing here is a test seam except the
injected operation/discover runners (the same seam the live rail injects at
``apply_editorial_delta._build_dispatch``).
"""
from __future__ import annotations

import copy

import pytest

from forge_bridge.cli import verbs
from forge_bridge.composition.compare import compare_idempotent_paths
from forge_bridge.composition.dispatch import UnifiedDispatch
from forge_bridge.composition.executor import GraphExecutor
from forge_bridge.composition.host_resolve_boundary import HostResolveBoundary
from forge_bridge.composition.operation_boundary import OperationDispatchBoundary
from forge_bridge.graph.editorial_delta import RENAME_SEQUENCE_ID

_APPLY_TOOL = "forge_apply_segment_delta"
_SEQUENCE_NAME = "CUT"
_COUNTER = "sh_$n{3,10,10}"  # -> sh_010, sh_020, sh_030, ... in timeline order


# -- segment fixtures ---------------------------------------------------------


def _seg(name: str, *, track_idx: int = 0, record_in_frame: int = 100) -> dict:
    return {
        "track_idx": track_idx,
        "record_in": f"tc_{record_in_frame}",
        "record_in_frame": record_in_frame,
        "record_out_frame": record_in_frame + 100,
        "duration": 100,
        "seg_name": name,
        "source_name": f"{name}_src",
    }


def _unsorted_segments(n: int) -> list[dict]:
    """A DELIBERATELY out-of-timeline-order selection of ``n`` segments.

    Reverse timeline order so ``timeline_sorted`` genuinely reorders it — the raw
    arrival order the graph would preserve is observably different from timeline
    order, which is exactly what makes a counter unsafe on it.
    """
    segs = [
        _seg(f"orig_{i:02d}", track_idx=0, record_in_frame=100 + i * 100)
        for i in range(n)
    ]
    return list(reversed(segs))


# -- faithful injected runners (derive output from the delta, never fixed) ----


def _timeline_delta(entries: list[dict], *, sequence_name: str) -> dict:
    return {
        "type": "timeline_delta",
        "sequence_id": sequence_name,
        "metadata": {
            "executor": _APPLY_TOOL,
            "group_key": f"{_APPLY_TOOL}:updated_segment_name",
            "host_resolve_schema_version": 3,
            "sequence_id_policy": "flame_sequence_name",
            "source_delta_sequence_id": RENAME_SEQUENCE_ID,
        },
        "changes": [copy.deepcopy(entry) for entry in entries],
    }


def _projected_payload(entries: list[dict], *, sequence_name: str) -> dict:
    return {
        "schema_version": 3,
        "payload_kind": "traffik.flame_delta_host_resolve_payload",
        "plan": {
            "reason_code": "flame_delta_host_resolve_ready",
            "output": {
                "summary": {"held_entry_count": 0, "routed_entry_count": len(entries)},
                "held_entries": [],
            },
        },
        "step_plan_result": {"packet_type": "EditorialStepPlanResult"},
        "deltas": [_timeline_delta(entries, sequence_name=sequence_name)],
    }


async def _run_operation(operation_type: str, *, params: dict, **_kwargs):
    from forge_core.traffik.editing import TimelineDelta

    assert operation_type == verbs.host_resolve_operator()
    td = TimelineDelta.from_dict(params["delta"])
    entries = [entry.to_dict() for entry in td.entries]
    sequence_name = entries[0]["metadata"]["sequence_name"]
    payload = _projected_payload(entries, sequence_name=sequence_name)
    return {"status": "success", "data": {"flame_delta_host_resolve_payload": payload}}


async def _run_discover(tool_name: str, *, request: dict, **_kwargs):
    assert tool_name == _APPLY_TOOL
    resolved_plan = [
        {
            "identity": dict(entry["metadata"]),
            "payload": {"shot_name": entry["after"]["name"]},
        }
        for entry in request["entries"]
    ]
    return {
        "type": "mutation_plan",
        "intent_parameters": {"sequence_name": request["sequence_name"]},
        "resolved_plan": resolved_plan,
        "originating_capability": _APPLY_TOOL,
        "apply_counterpart": {
            "tool": _APPLY_TOOL,
            "parameter_overrides": {"mode": "apply"},
        },
    }


def _dispatch() -> UnifiedDispatch:
    """The REAL UnifiedDispatch — literal_source/foreach/collect/rename are all
    routed through the production primitive/foreach boundaries; only the peer
    operation + host discover edges carry injected runners."""
    return UnifiedDispatch(
        operation_boundary=OperationDispatchBoundary(run_operation=_run_operation),
        host_resolve_boundary=HostResolveBoundary(run_discover=_run_discover),
    )


def _cli_spec(segments: list[dict], template: str):
    delta = verbs.build_rename_delta(
        {"sequence_name": _SEQUENCE_NAME, "segments": segments, "new_name": template}
    )
    return verbs.build_host_mutation_spec(delta, verbs.host_resolve_operator())


# -- (1) parity over timeline-ordered input -----------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("n", [3, 4])
async def test_counter_rename_fanout_matches_cli_byte_identical_when_sorted(n):
    # The live caller feeds timeline_sorted segments (the gather-boundary
    # invariant), so graph and CLI number identically and land a byte-identical
    # manifest — including resolved_plan ORDER (both emit timeline order).
    segments = verbs.timeline_sorted(_unsorted_segments(n))
    dispatch = _dispatch().dispatch
    graph = verbs.build_rename_fanout_spec(segments, _COUNTER, _SEQUENCE_NAME)

    async def legacy_runner():
        results = await GraphExecutor(dispatch).run(_cli_spec(segments, _COUNTER))
        manifest = results["delta_to_manifest"].output
        chain = [{"step": f"stage_{i}", "result": {}} for i in range(len(graph.nodes) - 1)]
        chain.append({"step": "delta_to_manifest", "result": manifest})
        return {"status": "success", "request_id": "legacy", "error": None, "chain": chain}

    result = await compare_idempotent_paths(
        legacy_runner=legacy_runner,
        graph=graph,
        dispatch=dispatch,
        terminal_node_id="delta_to_manifest",
        expected_steps=len(graph.nodes),
    )
    assert result.equivalent
    assert result.graph.status_vector == ("ok",) * len(graph.nodes)

    # Non-vacuity: the counter is expanded per timeline position (NOT a literal),
    # so the manifest carries the distinct sh_010, sh_020, ... shot numbers.
    graph_results = await GraphExecutor(dispatch).run(graph)
    manifest = graph_results["delta_to_manifest"].output
    names = [r["payload"]["shot_name"] for r in manifest["resolved_plan"]]
    assert names == [f"sh_{10 + i * 10:03d}" for i in range(n)]


# -- (2) assert-fires on unordered input (fail-closed) ------------------------


@pytest.mark.parametrize("n", [3, 4])
def test_counter_fanout_refuses_unsorted_input(n):
    # The counter graph assembly edge REFUSES an out-of-order selection rather
    # than silently stamping the wrong numbers. This proves the assert is real.
    unsorted = _unsorted_segments(n)
    assert unsorted != verbs.timeline_sorted(unsorted)  # the input really is out of order
    with pytest.raises(verbs.TimelineOrderError):
        verbs.build_rename_fanout_spec(unsorted, _COUNTER, _SEQUENCE_NAME)


def test_literal_fanout_accepts_unsorted_input():
    # The assert is scoped to order-SENSITIVE counters: a literal template over the
    # SAME unsorted input is accepted (order-agnostic — no ordering step needed).
    unsorted = _unsorted_segments(3)
    assert unsorted != verbs.timeline_sorted(unsorted)
    verbs.build_rename_fanout_spec(unsorted, "HERO", _SEQUENCE_NAME)  # no raise


def test_counter_fanout_accepts_sorted_input():
    # And a counter over already-timeline-sorted input is accepted (the invariant
    # the gather boundary establishes for the live path).
    ordered = verbs.timeline_sorted(_unsorted_segments(3))
    verbs.build_rename_fanout_spec(ordered, _COUNTER, _SEQUENCE_NAME)  # no raise
