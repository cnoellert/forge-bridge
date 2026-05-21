"""Phase 25.3 — generic identity select graph primitive."""
from __future__ import annotations

import pytest

from forge_bridge.graph import (
    SelectError,
    SelectIdentity,
    SelectNode,
    is_select_step,
    parse_select_step,
)


def test_parse_select_step_extracts_identity_target():
    identity = parse_select_step("select genesis_0010")

    assert identity == SelectIdentity(target="genesis_0010")
    assert identity.to_dict() == {"target": "genesis_0010"}


def test_is_select_step_is_anchored_to_step_start():
    assert is_select_step("select genesis_0010")
    assert not is_select_step("please select genesis_0010")


def test_select_exact_match_against_raw_collection():
    result = SelectNode(SelectIdentity("genesis_0010")).run({
        "segments": [
            {"seg_name": "genesis_0010", "duration": 99},
            {"seg_name": "genesis_0020", "duration": 99},
        ],
        "count": 2,
    })

    assert result["segments"] == [{"seg_name": "genesis_0010", "duration": 99}]
    assert result["count"] == 1


def test_select_uses_first_present_canonical_field_per_entry():
    result = SelectNode(SelectIdentity("shot_fallback")).run({
        "segments": [
            {"seg_name": "seg_primary", "shot_name": "shot_fallback"},
            {"shot_name": "shot_fallback"},
        ],
    })

    assert result["segments"] == [{"shot_name": "shot_fallback"}]


def test_select_rejects_prefix_substring_match():
    with pytest.raises(SelectError) as exc:
        SelectNode(SelectIdentity("genesis_0010")).run({
            "segments": [{"seg_name": "genesis_0010_source_L01"}],
        })

    assert exc.value.code == "IDENTITY_NOT_FOUND"


def test_select_rejects_suffix_substring_match():
    with pytest.raises(SelectError) as exc:
        SelectNode(SelectIdentity("source_L01")).run({
            "segments": [{"seg_name": "genesis_0010_source_L01"}],
        })

    assert exc.value.code == "IDENTITY_NOT_FOUND"


def test_select_matches_second_canonical_field_when_first_absent():
    result = SelectNode(SelectIdentity("shot_0010")).run({
        "segments": [{"shot_name": "shot_0010"}],
    })

    assert result["segments"] == [{"shot_name": "shot_0010"}]


def test_select_single_match_returns_list_not_scalar():
    result = SelectNode(SelectIdentity("clip_a")).run([
        {"clip_name": "clip_a"},
    ])

    assert result["collection"] == [{"clip_name": "clip_a"}]


def test_select_zero_match_raises_identity_not_found_not_empty_list():
    with pytest.raises(SelectError) as exc:
        SelectNode(SelectIdentity("missing")).run({"segments": [{"seg_name": "a"}]})

    assert exc.value.code == "IDENTITY_NOT_FOUND"
    assert exc.value.details == {"target": "missing"}


def test_select_multi_match_raises_identity_ambiguous():
    with pytest.raises(SelectError) as exc:
        SelectNode(SelectIdentity("dup")).run({
            "segments": [{"seg_name": "dup"}, {"seg_name": "dup"}],
        })

    assert exc.value.code == "IDENTITY_AMBIGUOUS"
    assert exc.value.details == {"target": "dup", "matches": 2}


def test_select_operates_on_dry_run_manifest_proposed_changes():
    result = SelectNode(SelectIdentity("seg_0010")).run({
        "dry_run": True,
        "proposed_changes": [
            {"segment": "seg_0010", "proposed": "archive_0010"},
            {"segment": "seg_0020", "proposed": "archive_0020"},
        ],
        "count": 2,
    })

    assert result["proposed_changes"] == [
        {"segment": "seg_0010", "proposed": "archive_0010"},
    ]
    assert result["count"] == 1


def test_select_after_if_gate_open_reads_manifest_collection():
    result = SelectNode(SelectIdentity("seg_0010")).run({
        "execution_state": "passed",
        "proposed_changes": [{"segment": "seg_0010"}],
        "if_gate": {"matched": True},
    })

    assert result["proposed_changes"] == [{"segment": "seg_0010"}]


def test_select_after_if_gate_closed_returns_identity_not_found():
    with pytest.raises(SelectError) as exc:
        SelectNode(SelectIdentity("seg_0010")).run({
            "execution_state": "skipped",
            "proposed_changes": [],
            "if_gate": {"matched": False},
        })

    assert exc.value.code == "IDENTITY_NOT_FOUND"


def test_select_empty_upstream_returns_identity_not_found():
    with pytest.raises(SelectError) as exc:
        SelectNode(SelectIdentity("seg_0010")).run({"segments": []})

    assert exc.value.code == "IDENTITY_NOT_FOUND"


def test_select_non_empty_upstream_no_match_returns_identity_not_found():
    with pytest.raises(SelectError) as exc:
        SelectNode(SelectIdentity("seg_0010")).run({"segments": [{"seg_name": "other"}]})

    assert exc.value.code == "IDENTITY_NOT_FOUND"


def test_select_mixed_field_upstream_without_canonical_field_returns_not_found():
    with pytest.raises(SelectError) as exc:
        SelectNode(SelectIdentity("seg_0010")).run({"segments": [{"duration": 99}]})

    assert exc.value.code == "IDENTITY_NOT_FOUND"


def test_select_duplicate_identity_same_upstream_is_ambiguous():
    with pytest.raises(SelectError) as exc:
        SelectNode(SelectIdentity("node_a")).run({
            "nodes": [{"node_name": "node_a"}, {"node_name": "node_a"}],
        })

    assert exc.value.code == "IDENTITY_AMBIGUOUS"


def test_select_identity_matching_multiple_entries_is_ambiguous():
    with pytest.raises(SelectError) as exc:
        SelectNode(SelectIdentity("clip_a")).run({
            "clips": [{"clip_name": "clip_a"}, {"clip_name": "clip_a"}],
        })

    assert exc.value.code == "IDENTITY_AMBIGUOUS"


def test_select_ambiguity_payload_shape_names_match_count():
    with pytest.raises(SelectError) as exc:
        SelectNode(SelectIdentity("shot_a")).run({
            "shots": [{"shot_name": "shot_a"}, {"shot_name": "shot_a"}],
        })

    assert exc.value.details["target"] == "shot_a"
    assert exc.value.details["matches"] == 2
