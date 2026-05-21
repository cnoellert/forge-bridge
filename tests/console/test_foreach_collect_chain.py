"""Phase N — foreach/collect chain dispatch boundary."""
from __future__ import annotations

import asyncio
import json
import time
from types import SimpleNamespace

from forge_bridge.console._chain_parse import parse_chain
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


def _rename_tool():
    return _wrapped_tool(
        "flame_rename_shots",
        {
            "sequence_name": {"type": "string"},
            "prefix": {"type": "string"},
            "selected_segments": {"type": "array"},
            "dry_run": {"type": "boolean"},
        },
        ["sequence_name", "prefix"],
    )


def _segment_tool():
    return _wrapped_tool(
        "flame_get_sequence_segments",
        {"sequence_name": {"type": "string"}},
        ["sequence_name"],
    )


def _segments_payload(count: int = 2):
    return {
        "sequence": "30sec_21",
        "segments": [
            {
                "track_idx": 0,
                "record_in": str(index),
                "seg_name": f"seg_{index}",
                "duration": 99,
            }
            for index in range(count)
        ],
        "count": count,
    }


class RenameMCP:
    def __init__(self):
        self.calls: list[dict] = []

    async def call_tool(self, name, arguments):
        params = dict(arguments["params"])
        self.calls.append(params)
        selected = params.get("selected_segments") or []
        if selected:
            segment = selected[0]
            proposed = f"{params['prefix']}_{segment['seg_name']}"
        else:
            segment = {}
            proposed = params["prefix"]
        return _text_block(json.dumps({
            "dry_run": params.get("dry_run", False),
            "sequence": params.get("sequence_name"),
            "proposed_changes": [{
                "segment": segment.get("seg_name"),
                "proposed": proposed,
            }],
            "count": len(selected),
        }))


def test_chain_parse_preserves_arrows_inside_foreach_body():
    assert parse_chain(
        "get segments on 30sec 21 -> "
        "foreach(filter(duration > 1) -> rename shots) -> collect"
    ) == [
        "get segments on 30sec 21",
        "foreach(filter(duration > 1) -> rename shots)",
        "collect",
    ]


def test_chain_step_foreach_dispatches_one_iteration():
    mcp = RenameMCP()

    result = asyncio.run(execute_chain_step(
        step_text="foreach(rename shots with prefix genesis dry_run)",
        tools=[_rename_tool()],
        mcp=mcp,
        inherited_context={
            "sequence_name": "30sec_21",
            "__previous_result__": _segments_payload(1),
            "__previous_topology__": {"kind": "list", "item_type": "segment"},
        },
        step_index=1,
    ))

    assert result["tool"] == "graph_foreach"
    assert result["result"]["count"] == 1
    assert mcp.calls[0]["selected_segments"][0]["seg_name"] == "seg_0"


def test_chain_step_foreach_dispatches_n_iterations():
    mcp = RenameMCP()

    result = asyncio.run(execute_chain_step(
        step_text="foreach(rename shots with prefix genesis dry_run)",
        tools=[_rename_tool()],
        mcp=mcp,
        inherited_context={
            "sequence_name": "30sec_21",
            "__previous_result__": _segments_payload(3),
            "__previous_topology__": {"kind": "list", "item_type": "segment"},
        },
        step_index=1,
    ))

    assert result["result"]["count"] == 3
    assert [call["selected_segments"][0]["seg_name"] for call in mcp.calls] == [
        "seg_0",
        "seg_1",
        "seg_2",
    ]


def test_body_step_receives_iteration_item_topology_not_collection_topology():
    result = asyncio.run(execute_chain_step(
        step_text="foreach(if(proposed_changes exists))",
        tools=[],
        mcp=SimpleNamespace(),
        inherited_context={
            "__previous_result__": _segments_payload(1),
            "__previous_topology__": {"kind": "list", "item_type": "segment"},
        },
        step_index=4,
    ))

    assert result["error"]["type"] == "CHAIN_WIRE_COMPATIBILITY_ERROR"
    assert result["error"]["step_index"] == "4.0"
    assert result["error"]["actual"] == {
        "kind": "list",
        "item_type": "segment",
        "cardinality": "single",
    }


def test_body_step_chain_wire_error_does_not_double_fire_primitive_error():
    result = asyncio.run(execute_chain_step(
        step_text="foreach(if(proposed_changes exists))",
        tools=[],
        mcp=SimpleNamespace(),
        inherited_context={
            "__previous_result__": _segments_payload(1),
            "__previous_topology__": {"kind": "list", "item_type": "segment"},
        },
        step_index=2,
    ))

    assert result["error"]["type"] == "CHAIN_WIRE_COMPATIBILITY_ERROR"
    assert result["error"]["type"] != "invalid_manifest"


def test_body_step_primitive_error_remains_distinct_from_wire_error():
    result = asyncio.run(execute_chain_step(
        step_text="foreach(select missing)",
        tools=[],
        mcp=SimpleNamespace(),
        inherited_context={
            "__previous_result__": _segments_payload(1),
            "__previous_topology__": {"kind": "list", "item_type": "segment"},
        },
        step_index=2,
    ))

    assert result["error"]["type"] == "IDENTITY_NOT_FOUND"
    assert result["error"]["type"] != "CHAIN_WIRE_COMPATIBILITY_ERROR"


def test_body_step_error_envelope_carries_foreach_and_iteration_location():
    result = asyncio.run(execute_chain_step(
        step_text="foreach(select missing)",
        tools=[],
        mcp=SimpleNamespace(),
        inherited_context={
            "__previous_result__": _segments_payload(1),
            "__previous_topology__": {"kind": "list", "item_type": "segment"},
        },
        step_index=7,
    ))

    assert result["error"]["foreach_step_index"] == 7
    assert result["error"]["iteration_index"] == 0
    assert result["error"]["body_step"] == "select missing"


def test_iteration_context_mutation_does_not_leak_to_next_iteration():
    mcp = RenameMCP()

    async def mutating_call_tool(name, arguments):
        selected = arguments["params"]["selected_segments"]
        selected.append({"seg_name": "pollution"})
        return await RenameMCP().call_tool(name, arguments)

    mcp.call_tool = mutating_call_tool

    result = asyncio.run(execute_chain_step(
        step_text="foreach(rename shots with prefix genesis dry_run)",
        tools=[_rename_tool()],
        mcp=mcp,
        inherited_context={
            "sequence_name": "30sec_21",
            "__previous_result__": _segments_payload(2),
            "__previous_topology__": {"kind": "list", "item_type": "segment"},
        },
        step_index=1,
    ))

    first = result["result"]["iterations"][0]["result"]["count"]
    second = result["result"]["iterations"][1]["result"]["count"]
    assert (first, second) == (2, 2)


def test_chain_context_after_foreach_is_not_polluted_by_iteration_context():
    class ChainMCP(RenameMCP):
        async def call_tool(self, name, arguments):
            if name == "flame_get_sequence_segments":
                return _text_block(json.dumps(_segments_payload(2)))
            return await super().call_tool(name, arguments)

    result = asyncio.run(run_chain_steps(
        steps=[
            "get segments on 30sec 21",
            "foreach(rename shots with prefix genesis dry_run)",
            "collect",
        ],
        tools=[_segment_tool(), _rename_tool()],
        mcp=ChainMCP(),
        request_id="rid",
        client_ip="127.0.0.1",
        started=time.monotonic(),
    ))

    assert result["status"] == "success"
    assert len(result["chain"][-1]["result"]["proposed_changes"]) == 2


def test_collect_chain_step_converges_foreach_results():
    foreach_result = {
        "iterations": [
            {
                "index": 0,
                "item": {"seg_name": "a"},
                "result": {"changes": [{"name": "a"}], "status": "ok"},
                "emitted_topology": {"kind": "manifest"},
            },
            {
                "index": 1,
                "item": {"seg_name": "b"},
                "result": {"changes": [{"name": "b"}], "status": "ok"},
                "emitted_topology": {"kind": "manifest"},
            },
        ],
        "count": 2,
    }

    result = asyncio.run(execute_chain_step(
        step_text="collect",
        tools=[],
        mcp=SimpleNamespace(),
        inherited_context={
            "__previous_result__": foreach_result,
            "__previous_topology__": {
                "kind": "list",
                "item_type": "IterationResult",
            },
        },
        step_index=2,
    ))

    assert result["tool"] == "graph_collect"
    assert result["result"]["changes"] == [{"name": "a"}, {"name": "b"}]
    assert result["result"]["status"] == "ok"


def test_collect_chain_step_reports_mixed_shape_as_chain_wire_error():
    result = asyncio.run(execute_chain_step(
        step_text="collect",
        tools=[],
        mcp=SimpleNamespace(),
        inherited_context={
            "__previous_result__": {
                "iterations": [
                    {
                        "index": 0,
                        "item": {},
                        "result": {"status": "ok"},
                        "emitted_topology": {"kind": "manifest"},
                    },
                    {
                        "index": 1,
                        "item": {},
                        "result": {"status": "changed"},
                        "emitted_topology": {"kind": "manifest"},
                    },
                ],
            },
            "__previous_topology__": {
                "kind": "list",
                "item_type": "IterationResult",
            },
        },
        step_index=3,
    ))

    assert result["error"]["type"] == "CHAIN_WIRE_COMPATIBILITY_ERROR"
    assert result["error"]["step_index"] == 3


def test_foreach_body_uses_standard_resolver_categories():
    mcp = RenameMCP()

    asyncio.run(execute_chain_step(
        step_text="foreach(rename shots with prefix genesis dry_run)",
        tools=[_rename_tool()],
        mcp=mcp,
        inherited_context={
            "sequence_name": "30sec_21",
            "__previous_result__": _segments_payload(1),
            "__previous_topology__": {"kind": "list", "item_type": "segment"},
        },
        step_index=1,
    ))

    assert mcp.calls[0]["prefix"] == "genesis"
    assert mcp.calls[0]["dry_run"] is True


def test_iteration_item_available_to_body_resolver():
    mcp = RenameMCP()

    asyncio.run(execute_chain_step(
        step_text="foreach(rename shots with prefix archive dry_run)",
        tools=[_rename_tool()],
        mcp=mcp,
        inherited_context={
            "sequence_name": "30sec_21",
            "__previous_result__": _segments_payload(1),
            "__previous_topology__": {"kind": "list", "item_type": "segment"},
        },
        step_index=1,
    ))

    assert mcp.calls[0]["selected_segments"] == [
        _segments_payload(1)["segments"][0],
    ]


def test_body_resolver_matches_top_level_resolver_for_same_text():
    top = asyncio.run(execute_chain_step(
        step_text="rename shots with prefix archive dry_run",
        tools=[_rename_tool()],
        mcp=RenameMCP(),
        inherited_context={
            "sequence_name": "30sec_21",
            "__filtered_collection__": [_segments_payload(1)["segments"][0]],
        },
        step_index=0,
    ))
    body_mcp = RenameMCP()
    body = asyncio.run(execute_chain_step(
        step_text="foreach(rename shots with prefix archive dry_run)",
        tools=[_rename_tool()],
        mcp=body_mcp,
        inherited_context={
            "sequence_name": "30sec_21",
            "__previous_result__": _segments_payload(1),
            "__previous_topology__": {"kind": "list", "item_type": "segment"},
        },
        step_index=1,
    ))

    assert "error" not in top
    assert "error" not in body
    assert body_mcp.calls[0]["prefix"] == "archive"
