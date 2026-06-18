from __future__ import annotations

import json
import time
import uuid
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from forge_bridge.composition.boundary import MCPToolBoundary
from forge_bridge.composition.compare import (
    SkipPropagationDispatch,
    admitted_records_for,
    compare_idempotent_paths,
    compare_strategy_for,
    normalize_chain_body,
    normalize_graph_results,
    normalize_terminal_output,
)
from forge_bridge.composition.dispatch import UnifiedDispatch
from forge_bridge.composition.executor import GraphExecutor
from forge_bridge.composition.graph_spec import Edge, GraphSpec, NodeSpec
from forge_bridge.composition.node_result import NodeResult
from forge_bridge.composition.parity_corpus import (
    GREENSCREEN_FILTER_ROTO,
    READ_IFGATE_PRUNE_CLOSED,
    READ_IFGATE_PRUNE_OPEN,
)
from forge_bridge.composition.primitive_boundary import PrimitiveBoundary
from forge_bridge.console._engine import run_chain_steps
from forge_bridge.graph.ports import PortContract


def _tool(name: str, properties: dict, required: list[str]):
    return SimpleNamespace(
        name=name,
        annotations=SimpleNamespace(readOnlyHint=True),
        inputSchema={
            "$defs": {
                "Input": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                }
            },
            "type": "object",
            "properties": {"params": {"$ref": "#/$defs/Input"}},
            "required": ["params"],
        },
    )


_FIXTURE_DIR = Path(__file__).parent / "fixtures"


class _FakeMCP:
    def __init__(
        self,
        *,
        roto_payload: dict | None = None,
        greenscreen_payload: dict | None = None,
    ) -> None:
        self.calls: list[tuple[str, dict]] = []
        self._roto_payload = roto_payload
        self._greenscreen_payload = greenscreen_payload

    async def list_tools(self):
        return _tools()

    async def call_tool(self, name: str, arguments: dict):
        self.calls.append((name, arguments))
        if name == "forge_is_greenscreen":
            if self._greenscreen_payload is not None:
                return self._greenscreen_payload
            return {
                "shots": [
                    {"id": "gs_010", "is_greenscreen": True},
                    {"id": "amb_030", "is_greenscreen": False},
                ],
                "count": 2,
            }
        if name == "forge_roto_ref":
            if self._roto_payload is not None:
                return self._roto_payload
            return _load_roto_capture("a")
        raise AssertionError(name)


def _tools() -> list:
    return [
        _tool(
            "forge_is_greenscreen",
            {
                "shot_id": {"type": "string"},
                "clip_ref": {"type": "string"},
            },
            ["shot_id", "clip_ref"],
        ),
        _tool(
            "forge_roto_ref",
            {
                "shot_id": {"type": "string"},
                "clip_ref": {"type": "string"},
            },
            ["shot_id", "clip_ref"],
        ),
    ]


def _load_roto_capture(name: str) -> dict:
    path = _FIXTURE_DIR / f"roto_ref_gs_010_call_{name}.json"
    return json.loads(path.read_text())


def _manifest_payload(*, changes: bool) -> dict:
    return {
        "type": "mutation_plan",
        "proposed_changes": [{"id": "a"}] if changes else [],
    }


def _uuid_factory(*values: str):
    ids = iter(uuid.UUID(value) for value in values)
    return lambda: next(ids)


@pytest.mark.asyncio
async def test_compare_harness_proves_greenscreen_filter_roto_vertical_equal():
    legacy_mcp = _FakeMCP(roto_payload=_load_roto_capture("a"))
    graph_mcp = _FakeMCP(roto_payload=_load_roto_capture("b"))
    case = GREENSCREEN_FILTER_ROTO

    async def legacy_runner():
        return await run_chain_steps(
            steps=list(case.legacy_steps),
            tools=_tools(),
            mcp=legacy_mcp,
            request_id="req-compare",
            client_ip="127.0.0.1",
            started=time.monotonic(),
        )

    result = await compare_idempotent_paths(
        legacy_runner=legacy_runner,
        graph=case.graph,
        dispatch=UnifiedDispatch(
            mcp_boundary=MCPToolBoundary(mcp=graph_mcp),
            primitive_boundary=PrimitiveBoundary(),
        ).dispatch,
        terminal_node_id=case.terminal_node_id,
        expected_steps=len(case.legacy_steps),
    )

    assert result.equivalent
    assert result.graph.status_vector == ("ok", "ok", "ok")
    assert result.graph.terminal_output["artifact"]["media_content_sha256"].startswith(
        "19ffdc03"
    )


@pytest.mark.parametrize(
    ("case", "changes", "expected"),
    [
        (READ_IFGATE_PRUNE_OPEN, True, ("ok", "ok", "ok")),
        (READ_IFGATE_PRUNE_CLOSED, False, ("ok", "ok", "skipped")),
    ],
)
@pytest.mark.asyncio
async def test_compare_harness_aligns_if_gate_linear_prune(case, changes, expected):
    legacy_mcp = _FakeMCP(
        greenscreen_payload=_manifest_payload(changes=changes),
        roto_payload=_load_roto_capture("a"),
    )
    graph_mcp = _FakeMCP(
        greenscreen_payload=_manifest_payload(changes=changes),
        roto_payload=_load_roto_capture("b"),
    )

    async def legacy_runner():
        return await run_chain_steps(
            steps=list(case.legacy_steps),
            tools=_tools(),
            mcp=legacy_mcp,
            request_id=f"req-{case.name}",
            client_ip="127.0.0.1",
            started=time.monotonic(),
        )

    result = await compare_idempotent_paths(
        legacy_runner=legacy_runner,
        graph=case.graph,
        dispatch=UnifiedDispatch(
            mcp_boundary=MCPToolBoundary(mcp=graph_mcp),
            primitive_boundary=PrimitiveBoundary(),
        ).dispatch,
        terminal_node_id=case.terminal_node_id,
        expected_steps=len(case.legacy_steps),
    )

    assert result.equivalent
    assert result.legacy.status_vector == expected
    assert result.graph.status_vector == expected


def test_roto_real_capture_normalizer_collapses_volatile_envelope():
    call_a = _load_roto_capture("a")
    call_b = _load_roto_capture("b")

    normalized_a = normalize_terminal_output(call_a)
    normalized_b = normalize_terminal_output(call_b)

    assert normalized_a == normalized_b
    assert normalized_a["artifact"]["media_content_sha256"].startswith("19ffdc03")
    assert normalized_a["artifact"]["derived_from"]["media_content_sha256"].startswith(
        "8f66f347"
    )
    assert normalized_a["artifact_refs"][0]["payload_id"].startswith("19ffdc03")
    assert normalized_a["artifact"]["derivation_run"]["request_id"] == (
        "bb3d7891b27d3b6c"
    )
    assert normalized_a["artifact"]["sequence_locator"]["path"] == (
        "mock://roto_ref/roto_<artifact_id>/gs_010_roto.####.exr"
    )


def test_roto_normalizer_preserves_matte_sha_divergence():
    call_a = _load_roto_capture("a")
    call_b = _load_roto_capture("b")
    call_b["artifact"]["media_content_sha256"] = "different-matte-sha"

    assert normalize_terminal_output(call_a) != normalize_terminal_output(call_b)


def test_normalize_chain_body_rejects_clarification_needed_status():
    body = {
        "status": "clarification_needed",
        "request_id": "req",
        "clarification_needed": {
            "kind": "referent",
            "prompt": "Which shot?",
        },
        "stop_reason": "clarification_needed",
        "chain": [],
    }

    with pytest.raises(ValueError, match="clarification_needed"):
        normalize_chain_body(body)


def test_normalize_chain_body_marks_only_engine_injected_skip_as_skipped():
    body = {
        "status": "success",
        "request_id": "req",
        "error": None,
        "chain": [
            {"step": "read", "result": {"type": "mutation_plan"}},
            {
                "step": "if(proposed_changes exists)",
                "result": {
                    "type": "mutation_plan",
                    "execution_state": "skipped",
                    "if_gate": {"matched": False},
                },
            },
            {
                "step": "downstream",
                "result": {
                    "type": "mutation_plan",
                    "execution_state": "skipped",
                    "skipped_step": "downstream",
                },
            },
        ],
    }

    assert normalize_chain_body(body).status_vector == ("ok", "ok", "skipped")


@pytest.mark.asyncio
async def test_graph_status_tokens_gate_ran_ok_downstream_skipped():
    calls: list[str] = []

    async def dispatch(node: NodeSpec, _resolved):
        calls.append(node.node_id)
        if node.node_id == "gate":
            return NodeResult(
                status="ok",
                run_id=uuid.uuid4(),
                output={"execution_state": "skipped"},
                control_signal="skip",
            )
        return NodeResult(status="ok", run_id=uuid.uuid4(), output={"ran": True})

    graph = GraphSpec(
        nodes=(
            NodeSpec(node_id="gate", operator_id="if"),
            NodeSpec(
                node_id="downstream",
                operator_id="forge_roto_ref",
                input_ports={"input": PortContract.any()},
            ),
        ),
        edges=(Edge(from_node="gate", to_node="downstream", to_port="input"),),
    )
    wrapper = SkipPropagationDispatch(dispatch)
    results = await GraphExecutor(wrapper.dispatch).run(graph)

    assert calls == ["gate"]
    assert normalize_graph_results(results, terminal_node_id="downstream").status_vector == (
        "ok",
        "skipped",
    )


@pytest.mark.asyncio
async def test_lineage_flows_through_filter_primitive_artifact():
    filter_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    graph_mcp = _FakeMCP(roto_payload=_load_roto_capture("a"))

    results = await GraphExecutor(UnifiedDispatch(
        mcp_boundary=MCPToolBoundary(
            mcp=graph_mcp,
            artifact_id_factory=_uuid_factory(
                "11111111-1111-1111-1111-111111111111",
                "33333333-3333-3333-3333-333333333333",
            ),
        ),
        primitive_boundary=PrimitiveBoundary(
            artifact_id_factory=lambda: filter_id,
        ),
    ).dispatch).run(GREENSCREEN_FILTER_ROTO.graph)

    greenscreen = results["greenscreen"]
    filter_result = results["route_greenscreen"]
    roto = results["roto"]
    assert filter_result.artifact_id == filter_id
    assert filter_result.source_artifact_ids == (greenscreen.artifact_id,)
    assert roto.source_artifact_ids == (filter_result.artifact_id,)


@pytest.mark.asyncio
async def test_skip_propagation_wrapper_preserves_abort_after_error():
    calls: list[str] = []

    async def dispatch(node: NodeSpec, _resolved):
        calls.append(node.node_id)
        status = "error" if node.node_id == "source" else "ok"
        return NodeResult(status=status, run_id=uuid.uuid4())

    graph = GraphSpec(
        nodes=(
            NodeSpec(node_id="source", operator_id="forge_is_greenscreen"),
            NodeSpec(
                node_id="downstream",
                operator_id="forge_roto_ref",
                input_ports={"input": PortContract.any()},
            ),
        ),
        edges=(Edge(from_node="source", to_node="downstream", to_port="input"),),
    )
    wrapper = SkipPropagationDispatch(dispatch)
    results = await GraphExecutor(wrapper.dispatch).run(graph)

    assert calls == ["source"]
    assert wrapper.skipped_node_ids == ["downstream"]
    assert normalize_graph_results(results, terminal_node_id="downstream").status_vector == (
        "error",
        "skipped",
    )


def test_compare_strategy_routes_idempotent_vs_record_replay():
    records = admitted_records_for(GREENSCREEN_FILTER_ROTO.graph)
    assert compare_strategy_for(records) == "double_exec"

    non_idempotent = replace(records[0], idempotent_result=False)
    assert compare_strategy_for((non_idempotent, *records[1:])) == "record_replay"
