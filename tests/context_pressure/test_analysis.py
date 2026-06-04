"""S4 — dual-mode contextual-failure analysis (the ratify-gated step).

Acceptance proves BREADTH (both failure modes detected + entering the failure
set), not merely the resolvable computation. The seed carries an IDX-13-shaped
mode-(b) case; a mode-(a)-only seed would green-light a half-blind analyzer.
"""
from __future__ import annotations

import pytest

from forge_bridge.context_pressure import (
    SchemaValidationError,
    read_records,
    validate_context_pressure_record,
)
from forge_bridge.context_pressure._analysis import (
    SEED_DIR,
    author_analysis,
    flag_contextual_failure_candidates,
    resolvable_delta,
)


def _seed():
    return read_records(corpus_dir=SEED_DIR)


def _by_prompt(records, needle):
    return next(r for r in records if needle in r["prompt"])


# --- Gate 1+2+4: dual-mode detection, IDX-13 seed, breadth ------------------

def test_seed_exercises_both_failure_modes():
    """The breadth gate: the flagged set across the seed contains BOTH modes."""
    modes = set()
    for r in _seed():
        for c in flag_contextual_failure_candidates(r):
            modes.add(c["mode"])
    assert modes == {"unresolved_reference", "wrong_resolution"}, (
        "seed must exercise both modes — a mode-(a)-only seed validates a half-blind analyzer"
    )


def test_idx13_mode_b_confident_wrong_resolution_flagged():
    """Mode (b): compiled concrete value != captured focus signal."""
    rec = _by_prompt(_seed(), "rename this sequence with prefix tv")
    cands = flag_contextual_failure_candidates(rec)
    assert len(cands) == 1
    c = cands[0]
    assert c["mode"] == "wrong_resolution"
    assert c["dimension"] == "sequence"
    assert c["compiled_value"] == "30sec_21"
    assert c["focus_value"] == "30sec_edit 21"
    assert c["focus_signal_present"] is True


def test_mode_a_unresolved_with_focus_present_is_resolvable_candidate():
    rec = _by_prompt(_seed(), "duration of this shot")
    c = flag_contextual_failure_candidates(rec)[0]
    assert c["mode"] == "unresolved_reference"
    assert c["compiled_value"] is None
    assert c["focus_signal_present"] is True  # world_state HAD it -> resolvable


def test_mode_a_unresolved_with_focus_absent_is_nonresolvable():
    rec = _by_prompt(_seed(), "prefix noise")
    c = flag_contextual_failure_candidates(rec)[0]
    assert c["mode"] == "unresolved_reference"
    assert c["focus_signal_present"] is False  # not captured -> not resolvable


def test_control_without_contextual_ref_is_not_flagged():
    rec = _by_prompt(_seed(), "rename shots on 30sec_edit 21")
    assert flag_contextual_failure_candidates(rec) == []


def test_correct_resolution_is_not_flagged():
    """compiled value == focus signal -> the model resolved correctly -> no flag."""
    rec = {
        "prompt": "rename this sequence with prefix tv",
        "observed_translation": {"compiled_graph": ['flame_rename_shots sequence_name="30sec_edit 21"'], "ratified_graph": None},
        "world_state": {"source": "flame", "raw": {}, "extracted": {"flame.active_sequence": "30sec_edit 21"}},
    }
    assert flag_contextual_failure_candidates(rec) == []


def test_mode_a_placeholder_and_segment_fallback_unresolved_for_right_reason():
    """R1-shape (synthetic, the live-corpus four-gap regression): all four fixes in
    one record — placeholder shot_id nulls to unresolved (not a coincidental
    param-key miss); empty current_shot is skipped so the shot focus falls through
    to current_segment_name. Locks the four-gap patch against future regression."""
    rec = _by_prompt(_seed(), "how long is this shot")
    cands = flag_contextual_failure_candidates(rec)
    assert len(cands) == 1
    c = cands[0]
    assert c["mode"] == "unresolved_reference"   # shot_id=UUID placeholder -> compiled None
    assert c["dimension"] == "shot"
    assert c["compiled_value"] is None           # gap #3 (shot_id read) + #4 (UUID nulled)
    assert c["focus_value"] == "seg_010A_01"     # gap #1 ("" skipped) + #2 (segment fallback)
    assert c["focus_signal_present"] is True


# --- Gate 3: candidate (auto) vs confirmation (authored) split --------------

def test_author_analysis_writes_layer_validates_and_does_not_mutate():
    rec = _by_prompt(_seed(), "rename this sequence with prefix tv")
    authored = author_analysis(
        rec, authored_at="2026-06-04T11:00:00Z", failure_class="wrong_referent",
        referent="30sec_edit 21", world_state_resolvable=True,
        resolving_signal="flame.active_sequence",
    )
    validate_context_pressure_record(authored)
    assert authored["analysis"]["failure_class"] == "wrong_referent"
    assert rec["analysis"] is None  # input untouched — distinct authoring pass


def test_author_analysis_requires_authored_at():
    rec = _by_prompt(_seed(), "rename this sequence with prefix tv")
    with pytest.raises(SchemaValidationError):
        author_analysis(rec, authored_at="", failure_class="wrong_referent")


# --- Gate 5: resolvable-delta over the UNION of both classes ----------------

def _authored_mix():
    seed = _seed()
    a = author_analysis(  # mode (b) wrong_referent, resolvable
        _by_prompt(seed, "rename this sequence with prefix tv"),
        authored_at="t", failure_class="wrong_referent", referent="30sec_edit 21",
        world_state_resolvable=True, resolving_signal="flame.active_sequence")
    b = author_analysis(  # mode (a) unresolved, resolvable
        _by_prompt(seed, "duration of this shot"),
        authored_at="t", failure_class="unresolved_reference", referent="tst_020",
        world_state_resolvable=True, resolving_signal="flame.current_shot")
    c = author_analysis(  # mode (a) unresolved, NOT resolvable (focus absent)
        _by_prompt(seed, "prefix noise"),
        authored_at="t", failure_class="unresolved_reference", referent=None,
        world_state_resolvable=False, resolving_signal=None)
    return [a, b, c]


def test_resolvable_delta_counts_union_of_both_classes():
    delta = resolvable_delta(_authored_mix())
    assert delta["total_contextual_failures"] == 3
    assert delta["world_state_resolvable_count"] == 2
    assert delta["resolvable_rate"] == pytest.approx(2 / 3)
    # the union: BOTH failure classes present, not just unresolved
    assert delta["by_failure_class"] == {"wrong_referent": 1, "unresolved_reference": 2}
    assert "flame.active_sequence" in delta["resolving_signal_ranking"]
    assert "flame.current_shot" in delta["resolving_signal_ranking"]


def test_delta_ignores_unanalyzed_records():
    """Captured-only records (analysis=None) do not enter the delta."""
    assert resolvable_delta(_seed())["total_contextual_failures"] == 0
