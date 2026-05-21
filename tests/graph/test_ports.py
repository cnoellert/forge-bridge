"""Phase N — minimum typed-port compatibility contract."""
from __future__ import annotations

import asyncio
import json
import time
from types import SimpleNamespace

import pytest

from forge_bridge.console._engine import run_chain_steps
from forge_bridge.console._step import execute_chain_step
from forge_bridge.graph import (
    ChainWireCompatibilityError,
    FilterNode,
    FilterPredicate,
    GraphInputError,
    IfGateNode,
    PortContract,
    PortTopology,
    SelectError,
    SelectIdentity,
    SelectNode,
    infer_topology,
    validate_chain_wire,
)

from tests.console.test_pr30_chain import _text_block


def _wrapped_tool(name: str, properties: dict, required: list[str]):
    return SimpleNamespace(
        name=name,
        inputSchema={
            "$defs": {
                "WrappedInput": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
            "type": "object",
            "properties": {"params": {"$ref": "#/$defs/WrappedInput"}},
            "required": ["params"],
        },
    )


def _segment_tool():
    return _wrapped_tool(
        "flame_get_sequence_segments",
        {"sequence_name": {"type": "string"}},
        ["sequence_name"],
    )


def test_filter_node_port_declaration_is_readable_from_node():
    node = FilterNode(FilterPredicate("duration", ">", 1))

    assert node.port_contract.to_dict()["accepts"] == [
        {"kind": "list", "item_type": "item"},
    ]


def test_port_contract_has_sane_any_default():
    contract = PortContract.any()

    assert contract.accepts_topology(PortTopology.scalar())


def test_port_topologies_express_foreach_shapes():
    assert PortTopology.list_of("segment").to_dict() == {
        "kind": "list",
        "item_type": "segment",
    }
    assert PortTopology.iteration_results().to_dict() == {
        "kind": "list",
        "item_type": "IterationResult",
    }
    assert PortTopology.list_of("Y").to_dict() == {
        "kind": "list",
        "item_type": "Y",
    }


def test_chain_wire_accepts_same_shape_match():
    validate_chain_wire(
        step_index=1,
        step_text="filter(duration > 1)",
        contract=FilterNode.port_contract,
        actual=PortTopology.list_of("item"),
    )


def test_chain_wire_accepts_compatible_but_distinct_item_type():
    validate_chain_wire(
        step_index=1,
        step_text="filter(duration > 1)",
        contract=FilterNode.port_contract,
        actual=PortTopology.list_of("segment"),
    )


def test_filter_chain_validates_and_executes_across_canonical_pipeline():
    result = asyncio.run(execute_chain_step(
        step_text="filter(duration > 1)",
        tools=[],
        mcp=SimpleNamespace(),
        inherited_context={
            "__previous_result__": {
                "segments": [
                    {"seg_name": "a", "duration": 1},
                    {"seg_name": "b", "duration": 2},
                ],
            },
            "__previous_topology__": PortTopology.list_of("segment").to_dict(),
        },
        step_index=1,
    ))

    assert "error" not in result
    assert result["emitted_topology"] == {
        "kind": "list",
        "item_type": "segment",
    }


def test_chain_wire_rejects_topology_kind_mismatch():
    with pytest.raises(ChainWireCompatibilityError) as exc:
        validate_chain_wire(
            step_index=2,
            step_text="filter(duration > 1)",
            contract=FilterNode.port_contract,
            actual=PortTopology.scalar(),
        )

    assert exc.value.actual == PortTopology.scalar()


def test_chain_wire_rejects_item_type_mismatch():
    segment_only = PortContract(
        (PortTopology.list_of("segment"),),
        PortTopology.list_of("segment"),
    )

    with pytest.raises(ChainWireCompatibilityError):
        validate_chain_wire(
            step_index=2,
            step_text="foreach(rename ...)",
            contract=segment_only,
            actual=PortTopology.list_of("clip"),
        )


def test_chain_wire_error_envelope_carries_step_index_expected_and_actual():
    result = asyncio.run(execute_chain_step(
        step_text="filter(duration > 1)",
        tools=[],
        mcp=SimpleNamespace(),
        inherited_context={"__previous_result__": "not a collection"},
        step_index=4,
    ))

    assert result["error"]["type"] == "CHAIN_WIRE_COMPATIBILITY_ERROR"
    assert result["error"]["step_index"] == 4
    assert result["error"]["expected"] == [
        {"kind": "list", "item_type": "item"},
    ]
    assert result["error"]["actual"] == {"kind": "scalar"}


def test_chain_wire_validation_fires_at_dispatch_edge_not_chain_init():
    calls: list[str] = []

    class FakeMCP:
        async def call_tool(self, name, arguments):
            calls.append(name)
            return _text_block(json.dumps({
                "sequence": "30sec_21",
                "segments": [{"seg_name": "a", "duration": 1}],
            }))

    result = asyncio.run(run_chain_steps(
        steps=["get segments on 30sec 21", "if(proposed_changes exists)"],
        tools=[_segment_tool()],
        mcp=FakeMCP(),
        request_id="rid",
        client_ip="127.0.0.1",
        started=time.monotonic(),
    ))

    assert calls == ["flame_get_sequence_segments"]
    assert result["error"]["original_error"]["type"] == (
        "CHAIN_WIRE_COMPATIBILITY_ERROR"
    )


def test_chain_wire_check_for_step_two_happens_only_after_step_one_completes():
    class FakeMCP:
        async def call_tool(self, name, arguments):
            return _text_block(json.dumps({
                "sequence": "30sec_21",
                "segments": [
                    {"seg_name": "a", "duration": 1},
                    {"seg_name": "b", "duration": 2},
                ],
            }))

    result = asyncio.run(run_chain_steps(
        steps=["get segments on 30sec 21", "filter(duration > 1)"],
        tools=[_segment_tool()],
        mcp=FakeMCP(),
        request_id="rid",
        client_ip="127.0.0.1",
        started=time.monotonic(),
    ))

    assert result["status"] == "success"
    assert len(result["chain"]) == 2
    assert result["chain"][1]["result"]["segments"] == [
        {"seg_name": "b", "duration": 2},
    ]


def test_chain_wire_does_not_preflight_later_mismatch_before_prior_steps_execute():
    class FakeMCP:
        async def call_tool(self, name, arguments):
            return _text_block(json.dumps({
                "sequence": "30sec_21",
                "segments": [
                    {"seg_name": "a", "duration": 1},
                    {"seg_name": "b", "duration": 2},
                ],
            }))

    result = asyncio.run(run_chain_steps(
        steps=[
            "get segments on 30sec 21",
            "filter(duration > 1)",
            "if(proposed_changes exists)",
        ],
        tools=[_segment_tool()],
        mcp=FakeMCP(),
        request_id="rid",
        client_ip="127.0.0.1",
        started=time.monotonic(),
    ))

    assert result["status"] == "error"
    assert result["error"]["step_index"] == 2
    assert len(result["chain"]) == 2
    assert result["chain"][1]["result"]["segments"] == [
        {"seg_name": "b", "duration": 2},
    ]


def test_chain_wire_error_class_exists_and_raises():
    with pytest.raises(ChainWireCompatibilityError):
        validate_chain_wire(
            step_index=1,
            step_text="select a",
            contract=IfGateNode.port_contract,
            actual=PortTopology.list_of("segment"),
        )


def test_chain_wire_error_envelope_shape_complete():
    exc = ChainWireCompatibilityError(
        step_index=3,
        step_text="if(proposed_changes exists)",
        expected=IfGateNode.port_contract.accepts,
        actual=PortTopology.list_of("segment"),
    )

    assert exc.to_error() == {
        "type": "CHAIN_WIRE_COMPATIBILITY_ERROR",
        "message": exc.message,
        "step_index": 3,
        "step": "if(proposed_changes exists)",
        "expected": [{"kind": "manifest"}],
        "actual": {"kind": "list", "item_type": "segment"},
    }


def test_chain_wire_error_is_distinct_from_node_errors():
    assert not issubclass(ChainWireCompatibilityError, GraphInputError)
    assert not issubclass(ChainWireCompatibilityError, SelectError)

    result = asyncio.run(execute_chain_step(
        step_text="filter(duration > 1)",
        tools=[],
        mcp=SimpleNamespace(),
        inherited_context={"__previous_result__": "not a collection"},
        step_index=1,
    ))

    assert result["error"]["type"] == "CHAIN_WIRE_COMPATIBILITY_ERROR"


def test_select_node_declares_manifest_and_collection_inputs():
    contract = SelectNode(SelectIdentity("a")).port_contract

    assert contract.to_dict()["accepts"] == [
        {"kind": "list", "item_type": "item"},
        {"kind": "manifest"},
    ]


def test_infer_topology_names_common_collection_item_type():
    assert infer_topology({"segments": [{"seg_name": "a"}]}) == (
        PortTopology.list_of("segment")
    )
