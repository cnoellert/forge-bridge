"""Batch-author foreach: the graph AUTHORS the multi-entry rename TimelineDelta.

Offline proof that the composition graph

    fixture_source(segments)
        -> foreach( rename_delta_entry )   # per-item single-entry delta
        -> collect                          # fold N single-entry -> one multi-entry
        -> traffik.flame_delta.host_resolve # project delta -> host-resolve payload
        -> delta_to_manifest                # resolve payload -> MutationManifest

reproduces "fan-out A" (the CLI multi-select rename) that ``cli/verbs.py`` today
hand-builds in Python. Two parity claims:

  1. LOAD-BEARING byte-identity (no fakes): the graph-authored TimelineDelta
     (``collect`` output, projected through ``TimelineDelta.from_dict``) equals
     ``verbs.build_rename_delta`` byte-for-byte. This is the real proof that the
     graph authors the same delta the CLI does — collect adds generic topology
     bookkeeping keys (iterations/collect/count), but the canonical
     TimelineDelta fields (type/sequence_id/changes/metadata) are identical.

  2. Terminal parity via ``compare_idempotent_paths``: legacy (CLI hand-build ->
     ``build_host_mutation_spec`` op+delta_to_manifest) vs the graph both land the
     SAME MutationManifest. The injected operation/discover runners are FAITHFUL
     (they derive their output from the delta's entries), so the terminal is not
     vacuous — n vs n+1 segments and counter-vs-literal produce distinct
     manifests.

Proven at n AND n+1 segments (a parity oracle can coincide at one size) for a
``$n`` counter template AND a token-free literal.

OFFLINE-ONLY: this is NOT wired into the live ``_run_fanout`` / interactive path;
live cutover is a separate slice. The #86 per-item position gap is now closed at
its root: ``ForEachNode`` authors each item's iteration index (under the reserved
``_foreach`` namespace), so the body reads a REAL ordinal — no pre-stamped scaffold.
The ordinal→timeline-position identity still rests on feeding the collection in
timeline order (see ``test_counter_derives_from_real_iteration_index`` for the
guard that the counter follows arrival order, not any injected value).
"""
from __future__ import annotations

import copy
import uuid

import pytest

from forge_bridge.cli import verbs
from forge_bridge.composition.compare import compare_idempotent_paths
from forge_bridge.composition.dispatch import UnifiedDispatch
from forge_bridge.composition.executor import GraphExecutor
from forge_bridge.composition.graph_spec import Edge, GraphSpec, NodeSpec
from forge_bridge.composition.host_resolve_boundary import HostResolveBoundary
from forge_bridge.composition.node_result import NodeResult
from forge_bridge.composition.operation_boundary import OperationDispatchBoundary
from forge_bridge.composition.primitive_boundary import PrimitiveBoundary
from forge_bridge.graph.editorial_delta import RENAME_SEQUENCE_ID
from forge_bridge.graph.ports import PortContract, PortTopology

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


def _segment_collection(n: int) -> tuple[dict, list[dict]]:
    """A timeline-sorted segment collection for ``n`` segments — fed PLAIN.

    The foreach boundary now authors each item's iteration index for real (under
    the reserved ``_foreach`` namespace), so the source items are no longer
    pre-stamped with a position. The list is fed in timeline order so the graph's
    arrival index matches the CLI's timeline position; the same sorted list is fed
    to the CLI build so both paths number identically.
    """
    segs = [
        _seg(f"orig_{i:02d}", track_idx=0, record_in_frame=100 + i * 100)
        for i in range(n)
    ]
    ordered = verbs.timeline_sorted(segs)
    return {"segments": ordered, "count": n}, ordered


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
                "summary": {
                    "held_entry_count": 0,
                    "routed_entry_count": len(entries),
                },
                "held_entries": [],
            },
        },
        "step_plan_result": {"packet_type": "EditorialStepPlanResult"},
        "deltas": [_timeline_delta(entries, sequence_name=sequence_name)],
    }


async def _run_operation(operation_type: str, *, params: dict, **_kwargs):
    # Project the (graph- OR CLI-authored) TimelineDelta into the host-resolve
    # payload the delta_to_manifest boundary consumes. TimelineDelta.from_dict
    # ignores collect's bookkeeping keys, so a graph delta and a clean CLI delta
    # project identically.
    from forge_core.traffik.editing import TimelineDelta

    assert operation_type == "traffik.flame_delta.host_resolve"
    td = TimelineDelta.from_dict(params["delta"])
    entries = [entry.to_dict() for entry in td.entries]
    sequence_name = entries[0]["metadata"]["sequence_name"]
    payload = _projected_payload(entries, sequence_name=sequence_name)
    return {
        "status": "success",
        "data": {"flame_delta_host_resolve_payload": payload},
    }


async def _run_discover(tool_name: str, *, request: dict, **_kwargs):
    # Build the manifest FROM the request entries so terminal parity is not
    # vacuous: the resolved_plan carries each entry's after-name + identity.
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


def _dispatch():
    """A dispatch that seeds the fixture_source and routes everything else real."""
    impl = UnifiedDispatch(
        primitive_boundary=PrimitiveBoundary(),
        operation_boundary=OperationDispatchBoundary(run_operation=_run_operation),
        host_resolve_boundary=HostResolveBoundary(run_discover=_run_discover),
    )

    async def dispatch(node: NodeSpec, resolved: dict[str, NodeResult]) -> NodeResult:
        if node.operator_id == "fixture_source":
            return NodeResult(
                status="ok",
                run_id=uuid.uuid4(),
                artifact_id=uuid.uuid4(),
                output=copy.deepcopy(node.config["output"]),
                output_topology=PortTopology.list_of("segment").to_dict(),
                artifact_type="segment",
            )
        return await impl.dispatch(node, resolved)

    return dispatch


# -- the graph ----------------------------------------------------------------


def _fanout_graph(*, template: str, collection: dict) -> GraphSpec:
    return GraphSpec(
        nodes=(
            NodeSpec(
                node_id="segments",
                operator_id="fixture_source",
                output_port=PortTopology.list_of("segment"),
                config={"output": collection},
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
                            "new_name": template,
                            "sequence_name": _SEQUENCE_NAME,
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
                operator_id="traffik.flame_delta.host_resolve",
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


def _legacy_runner(values: dict, dispatch, *, stage_count: int):
    async def runner():
        delta = verbs.build_rename_delta(values)
        legacy_spec = verbs.build_host_mutation_spec(
            delta, verbs.host_resolve_operator()
        )
        results = await GraphExecutor(dispatch).run(legacy_spec)
        manifest = results["delta_to_manifest"].output
        # Hand-assembled chain body: the CLI fan-out authoring is one Python call,
        # while the graph decomposes it into source/foreach/collect nodes, so the
        # stage counts differ by construction. The load-bearing parity is the
        # terminal manifest (+ the direct byte-identity assertion); the all-ok
        # status vector is aligned structurally to the graph's node count.
        chain = [{"step": f"stage_{i}", "result": {}} for i in range(stage_count - 1)]
        chain.append({"step": "delta_to_manifest", "result": manifest})
        return {
            "status": "success",
            "request_id": "legacy-fanout",
            "error": None,
            "chain": chain,
        }

    return runner


# -- the parity tests ---------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("template", ["sh_$n{3,10,10}", "HERO"])
@pytest.mark.parametrize("n", [3, 4])
async def test_graph_authors_multi_entry_rename_delta_equals_cli(template, n):
    collection, ordered = _segment_collection(n)
    values = {
        "sequence_name": _SEQUENCE_NAME,
        "segments": ordered,
        "new_name": template,
    }
    graph = _fanout_graph(template=template, collection=collection)
    dispatch = _dispatch()

    # (1) LOAD-BEARING byte-identity: the graph-authored TimelineDelta (collect
    # output, canonicalized) equals the CLI hand-build byte-for-byte.
    from forge_core.traffik.editing import TimelineDelta

    graph_results = await GraphExecutor(dispatch).run(graph)
    assert graph_results["collect"].status == "ok"
    graph_delta = TimelineDelta.from_dict(graph_results["collect"].output).to_dict()
    cli_delta = verbs.build_rename_delta(values)
    assert graph_delta == cli_delta

    # (2) Terminal parity through host_resolve -> delta_to_manifest.
    result = await compare_idempotent_paths(
        legacy_runner=_legacy_runner(values, dispatch, stage_count=len(graph.nodes)),
        graph=graph,
        dispatch=dispatch,
        terminal_node_id="delta_to_manifest",
        expected_steps=len(graph.nodes),
    )
    assert result.equivalent
    assert result.graph.status_vector == ("ok",) * len(graph.nodes)

    # Non-vacuity: the terminal manifest actually carries one resolved-plan row
    # per segment (n), so n vs n+1 land distinct manifests.
    manifest = graph_results["delta_to_manifest"].output
    assert manifest["type"] == "mutation_plan"
    assert len(manifest["resolved_plan"]) == n


@pytest.mark.asyncio
async def test_counter_expansion_is_authored_by_the_graph_node():
    # The $n{3,10,10} counter is expanded by the per-item graph node, not baked
    # upstream: names run sh010, sh020, sh030 in timeline order.
    n = 3
    collection, ordered = _segment_collection(n)
    graph = _fanout_graph(template="sh_$n{3,10,10}", collection=collection)
    results = await GraphExecutor(_dispatch()).run(graph)

    from forge_core.traffik.editing import TimelineDelta

    delta = TimelineDelta.from_dict(results["collect"].output).to_dict()
    names = [change["after"]["name"] for change in delta["changes"]]
    assert names == ["sh_010", "sh_020", "sh_030"]


@pytest.mark.asyncio
async def test_literal_name_applies_to_every_segment_without_a_counter():
    n = 4
    collection, _ordered = _segment_collection(n)
    graph = _fanout_graph(template="HERO", collection=collection)
    results = await GraphExecutor(_dispatch()).run(graph)

    from forge_core.traffik.editing import TimelineDelta

    delta = TimelineDelta.from_dict(results["collect"].output).to_dict()
    names = [change["after"]["name"] for change in delta["changes"]]
    assert names == ["HERO"] * n


@pytest.mark.asyncio
async def test_counter_derives_from_real_iteration_index_not_injected_value():
    # NEGATIVE / anti-scaffold guard: the counter must derive from the REAL foreach
    # iteration (arrival) index, NOT from any position value pre-injected onto the
    # source items. Each source segment carries a DELIBERATELY WRONG position under
    # BOTH the retired ``_position`` scaffold key AND the reserved ``_foreach``
    # namespace, reversed against arrival order. foreach is the SOLE author of
    # ``_foreach.index`` and overwrites the injected value with the true index, so
    # the emitted numbers follow arrival order (sh_010, sh_020, sh_030).
    #
    # Under the retired ``_position`` scaffold, ``_item_position`` read the injected
    # position directly, so this graph would have numbered sh_030, sh_020, sh_010 —
    # this assertion would FAIL. That it passes proves the ordinal is real.
    n = 3
    segs = [
        _seg(f"orig_{i:02d}", track_idx=0, record_in_frame=100 + i * 100)
        for i in range(n)
    ]
    ordered = verbs.timeline_sorted(segs)
    for arrival, seg in enumerate(ordered):
        reversed_position = n - 1 - arrival
        seg["_position"] = reversed_position                       # retired scaffold key
        seg["_foreach"] = {"index": reversed_position}             # reserved key, injected wrong
    collection = {"segments": ordered, "count": n}

    graph = _fanout_graph(template="sh_$n{3,10,10}", collection=collection)
    results = await GraphExecutor(_dispatch()).run(graph)

    from forge_core.traffik.editing import TimelineDelta

    delta = TimelineDelta.from_dict(results["collect"].output).to_dict()
    names = [change["after"]["name"] for change in delta["changes"]]
    assert names == ["sh_010", "sh_020", "sh_030"]
