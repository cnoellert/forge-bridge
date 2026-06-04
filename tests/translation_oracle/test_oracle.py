"""TF.3b observed-sourced verdict emission tests."""
from __future__ import annotations

from unittest.mock import patch

from forge_bridge.translation_oracle._oracle import emit


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
