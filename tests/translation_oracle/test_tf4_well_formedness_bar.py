"""TF.4 Slice #1 deterministic well-formedness recovery bar.

The bar is manifestation coverage, not arithmetic: text-arrow corpus
pass-through, JSON-list-of-strings, and JSON-list-bare-dict all converge
through the same production normalizer without a live model, daemon, or Flame.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from forge_bridge.llm.router import _parse_compile_output, normalize_chain_shape
from forge_bridge.translation_oracle._detect import compute_well_formed


def _reference_rows() -> list[dict]:
    reference = (
        Path(__file__).parents[2]
        / "forge_bridge"
        / "translation_oracle"
        / "reference"
        / "cases.jsonl"
    )
    rows: list[dict] = []
    for line in reference.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("_header"):
            continue
        rows.append(row)
    return rows


def _tool(name: str):
    return SimpleNamespace(name=name, description=f"{name} description")


def _assert_structurally_valid(steps: list[str]) -> None:
    well_formed, reason = compute_well_formed(steps)
    assert well_formed is True
    assert reason is None
    for step in steps:
        stripped = step.strip()
        assert not stripped.startswith("{")
        first = stripped.split(maxsplit=1)[0]
        assert "_" in first or first == "commit"


def test_tf4_detached_args_corpus_replay_flips_well_formed_false_to_true():
    detached_rows = [
        row
        for row in _reference_rows()
        if row["observed"].get("well_formed_reason") == "detached_args"
    ]

    assert len(detached_rows) == 4
    for row in detached_rows:
        observed = row["observed"]
        original_graph = observed["observed_graph"]
        before, before_reason = compute_well_formed(original_graph)

        normalized, salvage = normalize_chain_shape(original_graph)
        after, after_reason = compute_well_formed(normalized)

        assert observed["well_formed"] is False
        assert before is False
        assert before_reason == "detached_args"
        assert after is True
        assert after_reason is None
        assert salvage == {
            "salvage_applied": True,
            "original_reason": "detached_args",
        }
        assert len(normalized) == len(original_graph) - 1
        _assert_structurally_valid(normalized)


def test_tf4_detached_args_manifestations_are_enumerated_and_covered():
    """Covers text-arrow, JSON-list-of-strings, and JSON-list-bare-dict."""
    covered: set[str] = set()

    corpus_rows = [
        row
        for row in _reference_rows()
        if row["observed"].get("well_formed_reason") == "detached_args"
    ]
    for row in corpus_rows:
        normalized, salvage = normalize_chain_shape(row["observed"]["observed_graph"])
        assert salvage and salvage["original_reason"] == "detached_args"
        _assert_structurally_valid(normalized)
    covered.add("text-arrow corpus pass-through")

    normalized, salvage = normalize_chain_shape([
        "flame_rename_shots",
        '{"params": {"sequence_name": "30sec_21", "prefix": "tv"}}',
    ])
    assert salvage and salvage["original_reason"] == "detached_args"
    _assert_structurally_valid(normalized)
    covered.add("JSON-list-of-strings")

    parsed = _parse_compile_output(
        (
            '['
            '{"tool_name": "flame_rename_shots"}, '
            '{"params": {"sequence_name": "30sec_21", "prefix": "tv"}}'
            ']'
        ),
        tools=[_tool("flame_rename_shots")],
    )
    normalized, salvage = normalize_chain_shape(parsed)
    assert parsed == [
        "flame_rename_shots",
        '{"params": {"sequence_name": "30sec_21", "prefix": "tv"}}',
    ]
    assert salvage and salvage["original_reason"] == "detached_args"
    _assert_structurally_valid(normalized)
    covered.add("JSON-list-bare-dict")

    assert covered == {
        "text-arrow corpus pass-through",
        "JSON-list-of-strings",
        "JSON-list-bare-dict",
    }
