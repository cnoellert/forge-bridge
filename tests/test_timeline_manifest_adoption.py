"""Phase N+ timeline mutation manifest adoption tests."""
from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

from forge_bridge.console._step import execute_chain_step
from forge_bridge.tools import timeline

from tests.console.test_pr30_chain import _text_block


def _record(name: str = "seg_a", value: str = "genesis_0010_source_L01"):
    return {
        "identity": {
            "track_idx": 0,
            "record_in": "00:00:00:00",
            "seg_name": name,
            "source_name": "source_a",
            "sequence_name": "30sec_21",
        },
        "payload": {"segment_name": value},
    }


def _manifest(records=None):
    return {
        "type": "mutation_plan",
        "intent_parameters": {
            "sequence_name": "30sec_21",
            "prefix": "genesis",
            "increment": 10,
            "padding": 4,
            "start": 10,
        },
        "resolved_plan": records or [_record()],
        "originating_capability": "flame_rename_shots",
        "apply_counterpart": {
            "tool": "flame_rename_shots",
            "parameter_overrides": {"mode": "apply"},
        },
    }


async def _capture_rename(monkeypatch, params, response=None):
    captured = {}

    async def _fake_execute_json(code: str, *, main_thread: bool = False):
        captured["code"] = code
        captured["main_thread"] = main_thread
        return response if response is not None else _manifest()

    monkeypatch.setattr(timeline.bridge, "execute_json", _fake_execute_json)
    output = await timeline.rename_shots(params)
    captured["output"] = json.loads(output)
    return captured


def test_discover_mode_emits_mutation_plan_shape(monkeypatch):
    captured = asyncio.run(_capture_rename(
        monkeypatch,
        timeline.RenameInput(
            sequence_name="30sec_21",
            prefix="genesis",
            padding=4,
            dry_run=True,
        ),
    ))

    assert captured["output"]["type"] == "mutation_plan"
    assert captured["output"]["intent_parameters"] == {
        "sequence_name": "30sec_21",
        "prefix": "genesis",
        "increment": 10,
        "padding": 4,
        "start": 10,
    }
    assert captured["output"]["apply_counterpart"] == {
        "tool": "flame_rename_shots",
        "parameter_overrides": {"mode": "apply"},
    }
    code = captured["code"]
    assert "'track_idx': track_idx" in code
    assert "'record_in': str(seg.record_in)" in code
    assert "'seg_name': _seg_name(seg)" in code
    assert "'source_name': src" in code
    assert "'sequence_name': sequence_name" in code
    assert "'payload': {}" in code
    assert "'parameter_overrides': {'mode': 'apply'}" in code


def test_accumulator_merges_pass_payloads_into_one_change_record(monkeypatch):
    captured = asyncio.run(_capture_rename(
        monkeypatch,
        timeline.RenameInput(sequence_name="30sec_21", prefix="genesis"),
    ))
    code = captured["code"]

    assert "proposed_records = {}" in code
    assert "proposed_records[key] = rec" in code
    assert "['payload']['shot_name'] = shot_name" in code
    assert "['payload']['shot_name'] = bg_shot" in code
    assert "['payload']['segment_name'] = new_name" in code
    assert "'segment_name': ''" not in code
    assert "'shot_name': ''" not in code


def test_verify_mode_reruns_padding_resolution_and_emits_manifest(monkeypatch):
    captured = asyncio.run(_capture_rename(
        monkeypatch,
        timeline.RenameInput(
            sequence_name="30sec_21",
            prefix="genesis",
            mode="verify",
            resolved_plan=[_record()],
        ),
    ))
    code = captured["code"]

    assert "mode                = 'verify'" in code
    assert "resolved_plan_input = [{" in code
    assert "existing_padding_widths = []" in code
    assert "local_padding = existing_padding_widths[0]" in code
    assert "'type': 'mutation_plan'" in code


def test_apply_mode_drift_shape_and_mutation_gate_are_present(monkeypatch):
    drift = {
        "drift": True,
        "drift_count": 1,
        "first_drift_index": 0,
        "message": "Plan/state drift detected during apply.",
    }
    captured = asyncio.run(_capture_rename(
        monkeypatch,
        timeline.RenameInput(
            sequence_name="30sec_21",
            prefix="genesis",
            mode="apply",
            resolved_plan=[_record()],
        ),
        response=drift,
    ))

    assert captured["output"] == drift
    code = captured["code"]
    assert "if mode == 'apply':" in code
    assert "'drift': True" in code
    assert "if do_writes:" in code
    assert "seg.name.set_value(new_name)" in code


def test_mode_bridge_derives_from_dry_run_unless_explicit(monkeypatch):
    dry = asyncio.run(_capture_rename(
        monkeypatch,
        timeline.RenameInput(
            sequence_name="30sec_21",
            prefix="genesis",
            dry_run=True,
        ),
    ))
    live = asyncio.run(_capture_rename(
        monkeypatch,
        timeline.RenameInput(
            sequence_name="30sec_21",
            prefix="genesis",
            dry_run=False,
        ),
    ))
    explicit = asyncio.run(_capture_rename(
        monkeypatch,
        timeline.RenameInput(
            sequence_name="30sec_21",
            prefix="genesis",
            dry_run=False,
            mode="discover",
        ),
    ))

    assert "mode                = 'discover'" in dry["code"]
    assert "mode                = 'apply'" in live["code"]
    assert "mode                = 'discover'" in explicit["code"]


def test_multiscope_resolved_plan_groups_by_sequence_name(monkeypatch):
    other = _record("seg_b", "genesis_0020_source_L01")
    other["identity"]["sequence_name"] = "other_seq"

    captured = asyncio.run(_capture_rename(
        monkeypatch,
        timeline.RenameInput(
            sequence_name="30sec_21",
            prefix="genesis",
            mode="verify",
            resolved_plan=[_record(), other],
        ),
    ))
    code = captured["code"]

    assert "def _planned_groups():" in code
    assert "sequence_name = str(identity.get('sequence_name')" in code
    assert "for sequence_name, group_records in _planned_groups():" in code
    assert "'sequence_name': 'other_seq'" in code


def test_commit_step_clean_verify_dispatches_apply_and_returns_apply_result():
    calls = []

    class FakeMCP:
        async def call_tool(self, name, arguments):
            calls.append((name, arguments))
            if len(calls) == 1:
                return _text_block(json.dumps(_manifest()))
            return _text_block(json.dumps({"renamed": 1, "skipped": 0}))

    result = asyncio.run(execute_chain_step(
        step_text="commit",
        tools=[SimpleNamespace(name="flame_rename_shots")],
        mcp=FakeMCP(),
        inherited_context={
            "__previous_result__": _manifest(),
            "__previous_topology__": {"kind": "manifest"},
        },
        step_index=2,
    ))

    assert result["tool"] == "graph_commit"
    assert result["result"]["type"] == "commit_applied"
    assert result["result"]["applied"] is True
    assert result["result"]["apply_result"] == {"renamed": 1, "skipped": 0}
    assert [call[1]["mode"] for call in calls] == ["verify", "apply"]


def test_dual_drift_sources_normalize_to_same_plan_state_drift_envelope():
    async def _run(responses):
        class FakeMCP:
            def __init__(self):
                self.index = 0

            async def call_tool(self, name, arguments):
                response = responses[self.index]
                self.index += 1
                return _text_block(json.dumps(response))

        return await execute_chain_step(
            step_text="commit",
            tools=[SimpleNamespace(name="flame_rename_shots")],
            mcp=FakeMCP(),
            inherited_context={
                "__previous_result__": _manifest(),
                "__previous_topology__": {"kind": "manifest"},
            },
            step_index=2,
        )

    verify_drift_manifest = _manifest([
        _record("seg_a", "different"),
    ])
    apply_drift = {
        "drift": True,
        "drift_count": 1,
        "first_drift_index": 0,
        "message": "Plan/state drift detected during apply.",
    }

    verify_result = asyncio.run(_run([verify_drift_manifest]))
    apply_result = asyncio.run(_run([_manifest(), apply_drift]))

    expected = {
        "type": "PLAN_STATE_DRIFT",
        "message": "Mutation plan no longer matches current state.",
        "step_index": 2,
        "step": "commit",
        "drift_count": 1,
        "first_drift_index": 0,
    }
    assert verify_result["error"] == expected
    assert apply_result["error"] == expected
