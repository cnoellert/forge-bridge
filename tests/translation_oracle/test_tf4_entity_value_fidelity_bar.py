"""TF.4 Slice #2 deterministic entity value-fidelity bar.

The bar runs on the postgate corpus because entity fidelity is only visible
after the serialization gate is repaired.
"""
from __future__ import annotations

import json
from pathlib import Path

from forge_bridge.translation_oracle._detect import detect_entity_value_fidelity


def _postgate_cases() -> list[dict]:
    path = (
        Path(__file__).parents[2]
        / "forge_bridge"
        / "translation_oracle"
        / "reference"
        / "postgate"
        / "cases.jsonl"
    )
    cases: list[dict] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("_header"):
            continue
        cases.append(row)
    return cases


def test_tf4_entity_value_fidelity_flags_four_postgate_space_mangles():
    selected = [
        case
        for case in _postgate_cases()
        if case["label"].get("expected_params", {}).get("sequence_name")
        == "30sec_edit 21"
    ]

    assert len(selected) == 4
    for case in selected:
        faithful, reason = detect_entity_value_fidelity(
            case["observed"]["observed_graph"],
            case["label"]["expected_params"],
        )
        assert faithful is False
        assert reason == "30sec_edit 21"


def test_tf4_entity_value_fidelity_known_correct_postgate_case_passes():
    known_correct = [
        case
        for case in _postgate_cases()
        if case["label"].get("expected_params", {}).get("sequence_name")
        == "30sec_21"
    ]

    assert len(known_correct) == 1
    faithful, reason = detect_entity_value_fidelity(
        known_correct[0]["observed"]["observed_graph"],
        known_correct[0]["label"]["expected_params"],
    )
    assert faithful is True
    assert reason is None
