"""Phase 25.3 — select graph primitive at the chain-step boundary."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

from forge_bridge.console._step import execute_chain_step


def test_chain_step_select_dispatches_and_consumes_previous_result():
    prior = {
        "segments": [
            {"seg_name": "genesis_0010", "duration": 99},
            {"seg_name": "genesis_0020", "duration": 99},
        ],
        "count": 2,
    }

    result = asyncio.run(execute_chain_step(
        step_text="select genesis_0010",
        tools=[],
        mcp=SimpleNamespace(),
        inherited_context={"__previous_result__": prior},
    ))

    assert result["tool"] == "graph_select"
    assert result["params"] == {"identity": {"target": "genesis_0010"}}
    assert result["result"]["segments"] == [{"seg_name": "genesis_0010", "duration": 99}]
    assert result["extracted_context"]["__filtered_collection__"] == [
        {"seg_name": "genesis_0010", "duration": 99},
    ]


def test_chain_step_select_propagates_sequence_name_context():
    prior = {
        "sequence": "30sec_21",
        "segments": [{"seg_name": "genesis_0010"}],
    }

    result = asyncio.run(execute_chain_step(
        step_text="select genesis_0010",
        tools=[],
        mcp=SimpleNamespace(),
        inherited_context={"__previous_result__": prior},
    ))

    assert result["extracted_context"]["sequence_name"] == "30sec_21"


def test_chain_step_select_error_envelope_shape_for_zero_match():
    result = asyncio.run(execute_chain_step(
        step_text="select missing",
        tools=[],
        mcp=SimpleNamespace(),
        inherited_context={"__previous_result__": {"segments": [{"seg_name": "a"}]}},
    ))

    assert result["error"]["type"] == "IDENTITY_NOT_FOUND"
    assert result["error"]["details"] == {"target": "missing"}


def test_chain_step_select_error_envelope_shape_for_ambiguity():
    result = asyncio.run(execute_chain_step(
        step_text="select dup",
        tools=[],
        mcp=SimpleNamespace(),
        inherited_context={
            "__previous_result__": {
                "segments": [{"seg_name": "dup"}, {"seg_name": "dup"}],
            },
        },
    ))

    assert result["error"]["type"] == "IDENTITY_AMBIGUOUS"
    assert result["error"]["details"] == {"target": "dup", "matches": 2}


def test_chain_step_select_requires_previous_result():
    result = asyncio.run(execute_chain_step(
        step_text="select genesis_0010",
        tools=[],
        mcp=SimpleNamespace(),
        inherited_context={},
    ))

    assert result["error"]["type"] == "GRAPH_INPUT_REQUIRED"
