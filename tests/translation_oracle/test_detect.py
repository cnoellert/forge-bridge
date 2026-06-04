"""TF.3a — well-formedness detector tests (the gating Tier-1 check)."""
from __future__ import annotations

import forge_bridge.translation_oracle as translation_oracle
from forge_bridge.translation_oracle import (
    compute_well_formed,
    detect_entity_value_fidelity,
)


def test_translation_oracle_exports_consumed_detectors_only():
    assert "compute_well_formed" in translation_oracle.__all__
    assert "detect_entity_value_fidelity" in translation_oracle.__all__
    assert "emit" not in translation_oracle.__all__
    assert len(translation_oracle.__all__) == 19


def test_clean_graph_is_well_formed():
    wf, reason = compute_well_formed(["flame_list_batch_groups {}"])
    assert wf is True and reason is None


def test_inline_args_are_well_formed():
    wf, reason = compute_well_formed(['flame_rename_shots {"params": {"sequence_name": "x"}}'])
    assert wf is True and reason is None


def test_detached_args_is_malformed():
    """The dominant serialization failure: tool-name and args as separate steps."""
    wf, reason = compute_well_formed(
        ["flame_rename_shots", '{"params": {"sequence_name": "30sec_21", "prefix": "tv"}}'])
    assert wf is False and reason == "detached_args"


def test_prose_step_is_malformed():
    wf, reason = compute_well_formed(
        ["flame_list_batch_groups", "extract currently open batch group name"])
    assert wf is False and reason == "non_tool_step"


def test_compile_error_empty_graph_is_malformed():
    wf, reason = compute_well_formed([], outcome="compile_error")
    assert wf is False and reason == "invalid_chain_shape"


def test_empty_decline_graph_is_well_formed():
    """An honest-decline empty graph is well-formed (no malformed step)."""
    wf, reason = compute_well_formed([], outcome="chain_aborted")
    assert wf is True and reason is None


def test_known_tools_gate_catches_unknown_first_token():
    wf, reason = compute_well_formed(
        ["totally_made_up_tool {}"], known_tools={"flame_list_batch_groups"})
    assert wf is False and reason == "non_tool_step"


def test_entity_value_fidelity_passes_when_expected_values_are_emitted():
    faithful, reason = detect_entity_value_fidelity(
        ['flame_rename_shots sequence_name="30sec_21" prefix="tv"'],
        {"sequence_name": "30sec_21", "prefix": "tv"},
    )

    assert faithful is True
    assert reason is None


def test_entity_value_fidelity_flags_conflated_entity_value():
    faithful, reason = detect_entity_value_fidelity(
        ["flame_rename_shots sequence_name=30sec_21 prefix=noise"],
        {"sequence_name": "30sec_edit 21", "prefix": "noise"},
    )

    assert faithful is False
    assert reason == "30sec_edit 21"


def test_entity_value_fidelity_is_param_location_blind_but_exact():
    faithful, reason = detect_entity_value_fidelity(
        ["forge_list_shots project_id=30sec_edit_21 status=pending"],
        {"sequence_name": "30sec_edit 21"},
    )

    assert faithful is False
    assert reason == "30sec_edit 21"


def test_entity_value_fidelity_does_not_substring_match():
    faithful, reason = detect_entity_value_fidelity(
        ["forge_list_shots project_id=30sec_edit_21"],
        {"sequence_name": "30sec"},
    )

    assert faithful is False
    assert reason == "30sec"


def test_entity_value_fidelity_is_routing_orthogonal():
    faithful, reason = detect_entity_value_fidelity(
        ['forge_list_shots project_id="30sec_edit 21"'],
        {"sequence_name": "30sec_edit 21"},
    )

    assert faithful is True
    assert reason is None
