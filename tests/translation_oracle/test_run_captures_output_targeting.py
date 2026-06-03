"""TF.4 post-gate capture output targeting tests."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from forge_bridge.translation_oracle import run_captures
from forge_bridge.translation_oracle._corpus import REFERENCE_DIR, read_cases
from forge_bridge.translation_oracle._schema import validate_translation_case


def _baseline_hash() -> str:
    return hashlib.sha256((REFERENCE_DIR / "cases.jsonl").read_bytes()).hexdigest()


def _label() -> dict:
    return {
        "input": "postgate seed case",
        "expected_graph": ["forge_list_projects"],
        "expected_params": {},
        "expected_verdict_pair": {"translation": "pass", "substrate": "pass"},
        "expected_classes": [],
        "expected_well_formed": True,
        "world_state": None,
        "defect_ref": None,
        "expected_provenance": {},
    }


def _observed() -> dict:
    return {
        "capture_provenance": "seed-legibility",
        "observed_graph": ["forge_list_projects"],
        "observed_resolved_params": {},
        "outcome": "answered",
        "tool_forced": False,
        "tools_filtered": 1,
        "abort_reason": None,
        "tool_selected": "forge_list_projects",
        "well_formed": True,
        "well_formed_reason": None,
    }


@pytest.mark.asyncio
async def test_build_with_output_dir_preserves_frozen_reference_and_round_trips(
    tmp_path: Path,
    monkeypatch,
):
    target = tmp_path / "postgate"
    before_hash = _baseline_hash()
    monkeypatch.setattr(run_captures, "AUTHORED_CASES", [{
        "id": "PG1",
        "source": "seed",
        "input": "postgate seed case",
        "label": _label(),
    }])
    monkeypatch.setattr(run_captures, "_load_seed_records", lambda: [])
    monkeypatch.setattr(
        run_captures,
        "_seed_observed_for",
        lambda input_text, seed_records: _observed(),
    )

    written, skipped = await run_captures.build(seed_only=True, corpus_dir=target)

    assert written == ["PG1"]
    assert skipped == []
    assert _baseline_hash() == before_hash
    cases = read_cases(corpus_dir=target)
    assert len(cases) == 1
    assert cases[0]["label"]["input"] == "postgate seed case"
    validate_translation_case(cases[0])


def test_slice_one_bar_still_reads_the_frozen_reference_file():
    detached_rows = [
        case
        for case in read_cases(corpus_dir=REFERENCE_DIR)
        if case["observed"].get("well_formed_reason") == "detached_args"
    ]

    assert len(detached_rows) == 4
