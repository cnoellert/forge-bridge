"""PR C — graph filter integration at the chain-step boundary."""
from __future__ import annotations

import asyncio
import json
import time
from types import SimpleNamespace

from forge_bridge.console._engine import run_chain_steps
from forge_bridge.console._step import execute_chain_step

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


def test_chain_step_filter_transforms_previous_enumeration_result():
    prior = {
        "sequence": "30sec_21",
        "segments": [
            {"name": "a", "duration": 1},
            {"name": "b", "duration": 2},
        ],
        "count": 2,
    }

    result = asyncio.run(execute_chain_step(
        step_text="filter(duration > 1)",
        tools=[],
        mcp=SimpleNamespace(),
        inherited_context={"__previous_result__": prior},
    ))

    assert result["tool"] == "graph_filter"
    assert result["result"]["segments"] == [{"name": "b", "duration": 2}]
    assert result["extracted_context"]["__filtered_collection__"] == [
        {"name": "b", "duration": 2},
    ]
    assert result["extracted_context"]["sequence_name"] == "30sec_21"


def test_chain_step_filter_unknown_predicate_returns_structured_error():
    result = asyncio.run(execute_chain_step(
        step_text="filter only the comp segments",
        tools=[],
        mcp=SimpleNamespace(),
        inherited_context={"__previous_result__": {"segments": []}},
    ))

    assert result["error"]["type"] == "UNKNOWN_FILTER_PREDICATE"
    assert result["error"]["details"]["code"] == "unknown_predicate"


def test_chain_step_filter_rejects_mutation_manifest_input():
    result = asyncio.run(execute_chain_step(
        step_text="filter(duration > 1)",
        tools=[],
        mcp=SimpleNamespace(),
        inherited_context={
            "__previous_result__": {
                "renamed": 1,
                "changes": [{"duration": 2}],
            },
        },
    ))

    assert result["error"]["type"] == "CHAIN_WIRE_COMPATIBILITY_ERROR"


def test_chain_filter_empty_result_propagates_to_downstream_rename():
    calls: list[tuple[str, dict]] = []
    segment_tool = _wrapped_tool(
        "flame_get_sequence_segments",
        {"sequence_name": {"type": "string"}},
        ["sequence_name"],
    )
    rename_tool = _wrapped_tool(
        "flame_rename_shots",
        {
            "sequence_name": {"type": "string"},
            "prefix": {"type": "string"},
            "selected_segments": {"type": "array"},
        },
        ["sequence_name", "prefix"],
    )
    segment_payload = {
        "sequence": "30sec_21",
        "segments": [
            {
                "track_idx": 0,
                "record_in": "1001",
                "seg_name": "a",
                "source_name": "plate_a",
                "duration": 1,
            },
        ],
        "count": 1,
    }

    class FakeMCP:
        async def call_tool(self, name, arguments):
            calls.append((name, arguments))
            if name == "flame_get_sequence_segments":
                return _text_block(json.dumps(segment_payload))
            if name == "flame_rename_shots":
                params = arguments["params"]
                assert params["selected_segments"] == []
                return _text_block(json.dumps({"renamed": 0}))
            return _text_block("{}")

    result = asyncio.run(run_chain_steps(
        steps=[
            "get segments on 30sec 21",
            "filter(duration > 999)",
            "rename shots with prefix genesis",
        ],
        tools=[segment_tool, rename_tool],
        mcp=FakeMCP(),
        request_id="rid",
        client_ip="127.0.0.1",
        started=time.monotonic(),
    ))

    assert result["status"] == "success"
    assert result["chain"][-1]["result"] == {"renamed": 0}
    assert calls[-1] == (
        "flame_rename_shots",
        {
            "params": {
                "sequence_name": "30sec_21",
                "prefix": "genesis",
                "selected_segments": [],
            },
        },
    )
