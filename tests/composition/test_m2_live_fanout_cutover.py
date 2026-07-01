"""Live-cutover parity: the GRAPH-authored literal rename fan-out == the CLI hand-build.

The first step of the live foreach cutover routes a counter-free LITERAL
multi-select rename through the graph-authored fan-out spec
(``verbs.build_rename_fanout_spec``) instead of the CLI hand-build
(``verbs.build_rename_delta`` -> ``verbs.build_host_mutation_spec``). Both feed
the SAME ``preview_editorial_delta`` / ``apply_editorial_delta`` rail.

Unlike ``test_m2_batch_author_foreach.py`` (which seeds a test-only
``fixture_source`` through a custom dispatch), this exercises the PRODUCTION spec
through the REAL ``UnifiedDispatch``: the source is the admitted ``literal_source``
primitive, so nothing here is a test seam except the injected operation/discover
runners (the peer/host edge composition is import-free about — the same seam the
live rail injects at ``apply_editorial_delta._build_dispatch``).

Two claims:

  1. LIVE-PATH byte-identity — the live fan-out caller feeds ``timeline_sorted``
     segments (``interactive._run_fanout``), so graph and CLI land a byte-identical
     MutationManifest. Proven via the ``compare_idempotent_paths`` harness idiom.

  2. ORDER-AGNOSTIC on UNSORTED input — literal rename returns the template
     unchanged for every segment and the downstream is identity-keyed, so the
     graph (which does NO sort) and the CLI (which sorts internally) resolve the
     SAME set of identity->rename rows even when fed an out-of-order selection.
     The raw resolved_plan ORDER differs (the graph honestly preserves arrival
     order); keyed by identity the manifests are equal. This is the proof the
     graph rail needs no ordering node for the literal case.
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

    Reverse timeline order so ``timeline_sorted`` (which the CLI build applies
    internally) genuinely reorders it — the raw arrival order the graph preserves
    is then observably different from the CLI's sorted order.
    """
    segs = [
        _seg(f"orig_{i:02d}", track_idx=0, record_in_frame=100 + i * 100)
        for i in range(n)
    ]
    return list(reversed(segs))


# -- faithful injected runners (derive output from the delta, never fixed) ----
# Order-preserving on purpose: the manifest reflects delta entry order, so the
# order-agnostic claim is proven by the manifests, not laundered by the runner.


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
    operation + host discover edges carry injected runners (the same seam the
    live ``apply_editorial_delta._build_dispatch`` fills)."""
    return UnifiedDispatch(
        operation_boundary=OperationDispatchBoundary(run_operation=_run_operation),
        host_resolve_boundary=HostResolveBoundary(run_discover=_run_discover),
    )


def _cli_spec(segments: list[dict], template: str):
    delta = verbs.build_rename_delta(
        {"sequence_name": _SEQUENCE_NAME, "segments": segments, "new_name": template}
    )
    return verbs.build_host_mutation_spec(delta, verbs.host_resolve_operator())


def _by_identity(resolved_plan: list[dict]) -> list[dict]:
    return sorted(resolved_plan, key=lambda r: tuple(sorted(r["identity"].items())))


# -- the parity tests ---------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("n", [3, 4])
async def test_literal_rename_fanout_matches_cli_byte_identical_when_sorted(n):
    # The live caller (interactive._run_fanout) feeds timeline_sorted segments,
    # so graph and CLI land a byte-identical manifest. Proven with the harness.
    segments = verbs.timeline_sorted(_unsorted_segments(n))
    dispatch = _dispatch().dispatch
    graph = verbs.build_rename_fanout_spec(segments, "HERO", _SEQUENCE_NAME)

    async def legacy_runner():
        results = await GraphExecutor(dispatch).run(_cli_spec(segments, "HERO"))
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

    # Non-vacuity: every selected segment resolves to the literal name.
    graph_results = await GraphExecutor(dispatch).run(graph)
    manifest = graph_results["delta_to_manifest"].output
    assert len(manifest["resolved_plan"]) == n
    assert all(r["payload"]["shot_name"] == "HERO" for r in manifest["resolved_plan"])


@pytest.mark.asyncio
@pytest.mark.parametrize("n", [3, 4])
async def test_literal_rename_fanout_is_order_agnostic_on_unsorted_input(n):
    # Feed BOTH paths an out-of-order selection. The CLI sorts internally; the
    # graph does NO sort. Literal rename is order-agnostic, so the identity-keyed
    # manifests are equal even though the raw resolved_plan ORDER differs.
    unsorted = _unsorted_segments(n)
    assert unsorted != verbs.timeline_sorted(unsorted)  # the input really is out of order
    dispatch = _dispatch().dispatch

    graph = verbs.build_rename_fanout_spec(unsorted, "HERO", _SEQUENCE_NAME)
    graph_manifest = (await GraphExecutor(dispatch).run(graph))["delta_to_manifest"].output
    cli_manifest = (
        await GraphExecutor(dispatch).run(_cli_spec(unsorted, "HERO"))
    )["delta_to_manifest"].output

    # The graph honestly preserves arrival order; the CLI emits timeline order —
    # so the RAW resolved_plan differs (this is the finding, not papered over).
    assert graph_manifest["resolved_plan"] != cli_manifest["resolved_plan"]

    # Keyed by identity (how the host actually applies it) the manifests are
    # byte-identical: same set of identity->rename rows, same everything else.
    assert _by_identity(graph_manifest["resolved_plan"]) == _by_identity(
        cli_manifest["resolved_plan"]
    )
    for key in ("type", "intent_parameters", "originating_capability", "apply_counterpart"):
        assert graph_manifest[key] == cli_manifest[key]
    assert all(r["payload"]["shot_name"] == "HERO" for r in graph_manifest["resolved_plan"])
