"""TF.3b observed-sourced verdict emission tests."""
from __future__ import annotations

from unittest.mock import patch

from forge_bridge.translation_oracle._corpus import REFERENCE_DIR, read_cases
from forge_bridge.translation_oracle._oracle import emit, verdict_frequency


def test_emit_malformed_observed_fails_and_short_circuits_content():
    observed = {
        "outcome": "chain_aborted",
        "abort_reason": "UNRESOLVED_REQUIRED_PARAM",
        "observed_graph": ["flame_rename_shots", '{"params": {"prefix": "tv"}}'],
        "well_formed": False,
    }
    label = {"expected_params": {"prefix": "tv"}}

    with patch(
        "forge_bridge.translation_oracle._oracle.detect_entity_value_fidelity"
    ) as detector:
        assert emit(observed, label=label) == {
            "translation": "fail",
            "substrate": "gap",
        }

    detector.assert_not_called()


def test_emit_well_formed_labeled_scores_content_with_entity_fidelity():
    observed = {
        "outcome": "answered",
        "abort_reason": None,
        "observed_graph": ['flame_get_sequence_segments sequence_name="30sec_21"'],
        "well_formed": True,
    }
    label = {"expected_params": {"sequence_name": "30sec_edit 21"}}

    assert emit(observed, label=label) == {
        "translation": "fail",
        "substrate": "pass",
    }


def test_emit_well_formed_label_free_keeps_content_unscored():
    observed = {
        "outcome": "answered",
        "abort_reason": None,
        "observed_graph": ["forge_list_shots project_id=wrong"],
        "well_formed": True,
    }

    with patch(
        "forge_bridge.translation_oracle._oracle.detect_entity_value_fidelity"
    ) as detector:
        assert emit(observed) == {
            "translation": "pass",
            "substrate": "pass",
        }

    detector.assert_not_called()


def test_verdict_frequency_counts_observed_sourced_frozen_manifestations():
    cases = read_cases(corpus_dir=REFERENCE_DIR)

    assert verdict_frequency(cases) == {
        "labeled_count": 15,
        "verdict_pairs": {
            "pass/pass": 4,
            "fail/pass": 0,
            "pass/gap": 1,
            "fail/gap": 10,
        },
    }


def test_verdict_frequency_counts_observed_sourced_postgate_manifestations():
    cases = read_cases(corpus_dir=REFERENCE_DIR / "postgate")

    assert verdict_frequency(cases) == {
        "labeled_count": 15,
        "verdict_pairs": {
            "pass/pass": 5,
            "fail/pass": 2,
            "pass/gap": 3,
            "fail/gap": 5,
        },
    }
