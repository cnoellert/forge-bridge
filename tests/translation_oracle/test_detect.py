"""TF.3a — well-formedness detector tests (the gating Tier-1 check)."""
from __future__ import annotations

from forge_bridge.translation_oracle import compute_well_formed


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
