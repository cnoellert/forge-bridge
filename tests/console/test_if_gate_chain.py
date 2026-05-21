"""Phase 25.2 — if-gate integration at chain-step and chain-engine boundaries."""
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


def test_chain_step_if_gate_reads_immediately_previous_manifest():
    prior = {
        "dry_run": True,
        "proposed_changes": [{"current": "old", "proposed": "new"}],
        "sequence": "30sec_21",
    }

    result = asyncio.run(execute_chain_step(
        step_text="if(proposed_changes exists)",
        tools=[],
        mcp=SimpleNamespace(),
        inherited_context={"__previous_result__": prior},
    ))

    assert result["tool"] == "graph_if_gate"
    assert result["result"]["execution_state"] == "passed"
    assert result["result"]["if_gate"]["matched"] is True
    assert result["extracted_context"]["__if_gate_skip_next__"] is False
    assert result["extracted_context"]["sequence_name"] == "30sec_21"


def test_chain_step_if_gate_missing_predicate_returns_structured_error():
    result = asyncio.run(execute_chain_step(
        step_text="if(only the changed shots)",
        tools=[],
        mcp=SimpleNamespace(),
        inherited_context={"__previous_result__": {"proposed_changes": []}},
    ))

    assert result["error"]["type"] == "UNKNOWN_IF_PREDICATE"
    assert result["error"]["details"]["code"] == "unknown_predicate"


def test_chain_if_gate_pass_allows_next_commit_step_to_execute():
    calls: list[tuple[str, dict]] = []
    rename_tool = _wrapped_tool(
        "flame_rename_shots",
        {
            "sequence_name": {"type": "string"},
            "prefix": {"type": "string"},
            "dry_run": {"type": "boolean"},
        },
        ["sequence_name", "prefix"],
    )

    class FakeMCP:
        async def call_tool(self, name, arguments):
            calls.append((name, arguments))
            params = arguments["params"]
            if params.get("dry_run") is True:
                return _text_block(json.dumps({
                    "dry_run": True,
                    "sequence": "30sec_21",
                    "proposed_changes": [
                        {"current": "old", "proposed": "genesis_0010"},
                    ],
                    "count": 1,
                }))
            return _text_block(json.dumps({"renamed": 1, "skipped": 0}))

    result = asyncio.run(run_chain_steps(
        steps=[
            "rename shots on 30sec 21 with prefix genesis dry_run",
            "if(proposed_changes exists)",
            "rename shots with prefix genesis commit",
        ],
        tools=[rename_tool],
        mcp=FakeMCP(),
        request_id="rid",
        client_ip="127.0.0.1",
        started=time.monotonic(),
    ))

    assert result["status"] == "success"
    assert result["chain"][1]["result"]["if_gate"]["matched"] is True
    assert result["chain"][-1]["result"] == {"renamed": 1, "skipped": 0}
    assert calls == [
        (
            "flame_rename_shots",
            {
                "params": {
                    "sequence_name": "30sec_21",
                    "prefix": "genesis",
                    "dry_run": True,
                },
            },
        ),
        (
            "flame_rename_shots",
            {
                "params": {
                    "sequence_name": "30sec_21",
                    "prefix": "genesis",
                    "dry_run": False,
                },
            },
        ),
    ]


def test_chain_if_gate_miss_suppresses_exactly_next_step_with_skipped_manifest():
    calls: list[tuple[str, dict]] = []
    rename_tool = _wrapped_tool(
        "flame_rename_shots",
        {
            "sequence_name": {"type": "string"},
            "prefix": {"type": "string"},
            "dry_run": {"type": "boolean"},
        },
        ["sequence_name", "prefix"],
    )

    class FakeMCP:
        async def call_tool(self, name, arguments):
            calls.append((name, arguments))
            return _text_block(json.dumps({
                "dry_run": True,
                "sequence": "30sec_21",
                "proposed_changes": [],
                "count": 0,
            }))

    result = asyncio.run(run_chain_steps(
        steps=[
            "rename shots on 30sec 21 with prefix genesis dry_run",
            "if(proposed_changes exists)",
            "rename shots with prefix genesis commit",
        ],
        tools=[rename_tool],
        mcp=FakeMCP(),
        request_id="rid",
        client_ip="127.0.0.1",
        started=time.monotonic(),
    ))

    assert result["status"] == "success"
    assert len(calls) == 1
    assert result["chain"][1]["result"]["execution_state"] == "skipped"
    assert result["chain"][1]["result"]["if_gate"]["matched"] is False
    assert result["chain"][2]["step"] == "rename shots with prefix genesis commit"
    assert result["chain"][2]["result"]["execution_state"] == "skipped"
    assert result["chain"][2]["result"]["skipped_step"] == (
        "rename shots with prefix genesis commit"
    )


def test_sequence_name_propagates_from_previous_result_when_step_text_lacks_it():
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
        },
        ["sequence_name", "prefix"],
    )

    class FakeMCP:
        async def call_tool(self, name, arguments):
            calls.append((name, arguments))
            if name == "flame_get_sequence_segments":
                return _text_block(json.dumps({
                    "sequence": "30sec_21",
                    "segments": [],
                    "count": 0,
                }))
            return _text_block(json.dumps({"renamed": 0, "skipped": 0}))

    result = asyncio.run(run_chain_steps(
        steps=[
            "get segments on 30sec 21",
            "rename shots with prefix genesis",
        ],
        tools=[segment_tool, rename_tool],
        mcp=FakeMCP(),
        request_id="rid",
        client_ip="127.0.0.1",
        started=time.monotonic(),
    ))

    assert result["status"] == "success"
    assert calls[-1] == (
        "flame_rename_shots",
        {"params": {"sequence_name": "30sec_21", "prefix": "genesis"}},
    )


def test_explicit_sequence_name_in_step_text_wins_over_propagation():
    calls: list[tuple[str, dict]] = []
    rename_tool = _wrapped_tool(
        "flame_rename_shots",
        {
            "sequence_name": {"type": "string"},
            "prefix": {"type": "string"},
        },
        ["sequence_name", "prefix"],
    )

    class FakeMCP:
        async def call_tool(self, name, arguments):
            calls.append((name, arguments))
            return _text_block(json.dumps({"renamed": 1, "skipped": 0}))

    result = asyncio.run(execute_chain_step(
        step_text="rename shots on 30sec 22 with prefix genesis",
        tools=[rename_tool],
        mcp=FakeMCP(),
        inherited_context={
            "__previous_result__": {
                "sequence": "30sec_21",
                "segments": [],
            },
        },
    ))

    assert result["result"] == {"renamed": 1, "skipped": 0}
    assert calls == [
        (
            "flame_rename_shots",
            {"params": {"sequence_name": "30sec_22", "prefix": "genesis"}},
        ),
    ]


def test_propagation_uses_sequence_field_from_immediately_preceding_step():
    calls: list[tuple[str, dict]] = []
    rename_tool = _wrapped_tool(
        "flame_rename_shots",
        {
            "sequence_name": {"type": "string"},
            "prefix": {"type": "string"},
        },
        ["sequence_name", "prefix"],
    )

    class FakeMCP:
        async def call_tool(self, name, arguments):
            calls.append((name, arguments))
            return _text_block(json.dumps({"renamed": 0, "skipped": 0}))

    result = asyncio.run(execute_chain_step(
        step_text="rename shots with prefix genesis",
        tools=[rename_tool],
        mcp=FakeMCP(),
        inherited_context={
            "__previous_result__": {
                "sequence": "30sec_21",
                "sequence_label": "not_a_sequence_name",
            },
        },
    ))

    assert result["result"] == {"renamed": 0, "skipped": 0}
    assert calls == [
        (
            "flame_rename_shots",
            {"params": {"sequence_name": "30sec_21", "prefix": "genesis"}},
        ),
    ]


def test_no_propagation_when_previous_result_has_no_sequence_field():
    rename_tool = _wrapped_tool(
        "flame_rename_shots",
        {
            "sequence_name": {"type": "string"},
            "prefix": {"type": "string"},
        },
        ["sequence_name", "prefix"],
    )

    class FakeMCP:
        async def call_tool(self, name, arguments):
            raise AssertionError("fallback should not execute without a sequence field")

    result = asyncio.run(execute_chain_step(
        step_text="rename shots with prefix genesis",
        tools=[rename_tool],
        mcp=FakeMCP(),
        inherited_context={
            "__previous_result__": {
                "segments": [],
                "count": 0,
            },
        },
    ))

    assert result["error"]["type"] == "UNRESOLVED_REQUIRED_PARAM"
    assert result["error"]["details"] == {
        "key": "sequence_name",
        "tool": "flame_rename_shots",
    }
