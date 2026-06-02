"""TF.3a Step 4 — seed transcode tests.

Fixtures mirror the REAL comprehension record shape (verified against
~/.forge-bridge/comprehension/comprehension-2026-06-01.jsonl): question,
chain[{step,result}], answer, model, outcome, verdict, wall_clock_ms.
"""
from __future__ import annotations

import pytest

from forge_bridge.translation_oracle import (
    SCHEMA_VERSION,
    validate_translation_case,
)
from forge_bridge.translation_oracle._transcode import (
    TranscodeError,
    transcode_comprehension_record,
)


def _comprehension_record(*, question="What batch groups are on the desktop",
                          chain=None, outcome="answered"):
    return {
        "schema_version": "1",
        "captured_at": "2026-06-01T00:00:00+00:00",
        "outcome": outcome,
        "question": question,
        "chain": chain if chain is not None else [
            {"step": "flame_list_batch_groups {}", "result": []},
        ],
        "answer": "There are no batch groups.",
        "wall_clock_ms": 12,
        "model": "qwen2.5-coder:14b",
        "verdict": None,
    }


def test_transcode_produces_valid_seed_legibility_observed_trace():
    obs = transcode_comprehension_record(_comprehension_record())
    assert obs["capture_provenance"] == "seed-legibility"
    assert obs["observed_graph"] == ["flame_list_batch_groups {}"]
    assert obs["tool_selected"] == "flame_list_batch_groups"
    # the case is valid label-free (3b shape)
    validate_translation_case({"schema_version": SCHEMA_VERSION, "observed": obs})


def test_transcode_carries_coarse_outcome_but_no_fine_markers():
    obs = transcode_comprehension_record(_comprehension_record(outcome="chain_aborted"))
    assert obs["outcome"] == "chain_aborted"   # coarse: an abort happened
    assert obs["abort_reason"] is None         # fine reason was never captured
    assert obs["tools_filtered"] is None       # never captured
    assert obs["tool_forced"] is False


def test_transcode_extracts_params_via_partial_extractor():
    rec = _comprehension_record(chain=[
        {"step": "forge_get_project project_id=7f1e2d3c-1111-2222-3333-444455556666",
         "result": {}},
    ])
    obs = transcode_comprehension_record(rec)
    assert obs["observed_resolved_params"]["0"] == {
        "project_id": "7f1e2d3c-1111-2222-3333-444455556666"
    }


def test_transcode_rejects_malformed_null_question():
    with pytest.raises(TranscodeError, match="question is null"):
        transcode_comprehension_record(_comprehension_record(question=None))


def test_transcode_handles_empty_chain():
    obs = transcode_comprehension_record(_comprehension_record(chain=[]))
    assert obs["observed_graph"] == []
    assert obs["tool_selected"] is None
