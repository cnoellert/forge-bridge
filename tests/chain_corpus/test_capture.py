from __future__ import annotations

from pathlib import Path

import pytest

from forge_bridge.chain_corpus import (
    CAPTURE_DIR_ENV,
    CAPTURE_ENV,
    canonical_hash,
    emit_compile_record,
    start_trace_capture,
    variety_tags_for,
)
from forge_bridge.chain_corpus._schema import (
    ChainCorpusSchemaError,
    validate_compile_record,
    validate_trace_record,
)
from forge_bridge.chain_corpus.reader import (
    coverage_report,
    read_compile_file,
    read_trace_file,
)


class _FakeMCP:
    def __init__(self, results):
        self._results = list(results)

    async def call_tool(self, tool_name, arguments=None):
        return self._results.pop(0)


def test_canonical_hash_uses_full_sha256_and_sorted_json():
    left = canonical_hash({"b": 2, "a": 1})
    right = canonical_hash({"a": 1, "b": 2})

    assert left == right
    assert len(left) == 64


def test_variety_tags_are_fact_derived():
    tags = variety_tags_for(
        [
            "forge_is_greenscreen shot_id=batch",
            "filter(is_greenscreen == true)",
            "foreach(forge_roto_ref shot_id=gs_010)",
            "collect",
        ],
        regime="compiled_non_mutating",
        salvage_applied=True,
    )

    assert "multi_step" in tags
    assert "filter" in tags
    assert "foreach" in tags
    assert "collect" in tags
    assert "op_mix_filter_foreach_collect" in tags
    assert "bug_d_salvage" in tags


def test_schema_rejects_malformed_compile_record():
    with pytest.raises(ChainCorpusSchemaError):
        validate_compile_record({
            "schema_version": "1",
            "captured_at": "now",
            "request_id": "req",
            "regime": "compiled_non_mutating",
            "chain_steps": "not-a-list",
            "salvage_applied": False,
            "salvage_reason": None,
            "variety_tags": [],
            "source": "captured",
            "replayable": True,
        })


def test_schema_rejects_short_trace_hash():
    with pytest.raises(ChainCorpusSchemaError):
        validate_trace_record({
            "schema_version": "1",
            "captured_at": "now",
            "request_id": "req",
            "tool_name": "forge_ping",
            "args_hash": "abc",
            "result_hash": "0" * 64,
            "result": {},
        })


@pytest.mark.asyncio
async def test_trace_recorder_marks_same_tool_args_hash_collision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv(CAPTURE_ENV, "1")
    monkeypatch.setenv(CAPTURE_DIR_ENV, str(tmp_path))
    recorder = start_trace_capture(
        request_id="req-collision",
        mcp=_FakeMCP([{"count": 1}, {"count": 2}]),
    )

    await recorder.mcp.call_tool("forge_list_shots", {"project_id": "p"})
    await recorder.mcp.call_tool("forge_list_shots", {"project_id": "p"})

    assert recorder.has_collision is True
    trace_file = next(tmp_path.glob("chain-trace-*.jsonl"))
    assert len(read_trace_file(trace_file)) == 2


@pytest.mark.asyncio
async def test_trace_recorder_allows_repeat_static_identical_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv(CAPTURE_ENV, "1")
    monkeypatch.setenv(CAPTURE_DIR_ENV, str(tmp_path))
    recorder = start_trace_capture(
        request_id="req-static",
        mcp=_FakeMCP([{"ok": True}, {"ok": True}]),
    )

    await recorder.mcp.call_tool("forge_roto_ref", {"shot_id": "gs_010"})
    await recorder.mcp.call_tool("forge_roto_ref", {"shot_id": "gs_010"})

    assert recorder.has_collision is False


def test_emit_compile_round_trips_through_reader(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv(CAPTURE_ENV, "1")
    monkeypatch.setenv(CAPTURE_DIR_ENV, str(tmp_path))

    emit_compile_record(
        request_id="req-compile",
        regime="compiled_non_mutating",
        chain_steps=["forge_is_greenscreen shot_id=gs_010"],
        salvage_applied=False,
        salvage_reason=None,
        replayable=True,
    )

    compile_file = next(tmp_path.glob("chain-compile-*.jsonl"))
    rows = read_compile_file(compile_file)
    assert rows[0]["request_id"] == "req-compile"
    assert rows[0]["replayable"] is True


def test_reader_coverage_counts_captured_only():
    report = coverage_report([
        {
            "source": "captured",
            "variety_tags": ["multi_step", "foreach"],
        },
        {
            "source": "seed",
            "variety_tags": ["commit", "if_gate"],
        },
    ])

    assert report["counts"]["multi_step"] == 1
    assert report["counts"]["foreach"] == 1
    assert report["counts"]["commit"] == 0
    assert "captured compile facts" in report["limit"]
