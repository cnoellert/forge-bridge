"""S2 (dev-box half) — focus-state assembler: raw preserves provenance,
extracted preserves meaning. Tested against Creative's four explicit gates,
with the probe #1-#3 values as the fixture.
"""
from __future__ import annotations

from forge_bridge.context_pressure import build_record
from forge_bridge.context_pressure._analysis import flag_contextual_failure_candidates
from forge_bridge.context_pressure._focus import assemble_world_state


def _probe_raw():
    """The probe #3 capture, in the S2 raw contract — PyAttribute-wrapped values
    (the worst case: if not unwrapped, S4 false-positives everything)."""
    return {
        "project": "PyAttribute:013_13_13_2026_2_1_portofino",
        "current_tab": "Timeline",
        "media_panel": {"selected": []},
        "batch": {
            "name": "PyAttribute:FCX_OFX_TEST",
            "opened": True,
            "current_iteration": "PyAttribute:FCX_OFX_TEST_001",
            "selected": [],
        },
        "timeline": {
            "active_sequence": "PyAttribute:30sec_edit 21",
            "current_shot": "PyAttribute:tst_020",
            "current_segment_name": "PyAttribute:tst_020_graded_L01",
            "selected": [
                {"type": "PySegment", "name": "PyAttribute:tst_020_graded_L01", "shot_name": "PyAttribute:tst_020"},
                {"type": "PySegment", "name": "PyAttribute:tst_030_graded_L01", "shot_name": "PyAttribute:tst_030"},
                {"type": "PySegment", "name": "PyAttribute:tst_040_graded_L01", "shot_name": "PyAttribute:tst_040"},
            ],
        },
        "playhead_frame": None,
        "playhead_frame_reason": "unreachable_api",
    }


# --- Gate 1: raw preservation ------------------------------------------------

def test_raw_preserved_verbatim():
    raw = _probe_raw()
    ws = assemble_world_state(raw)
    assert ws["raw"] is raw  # faithfully preserved, the recoverable surface
    assert ws["source"] == "flame"


# --- Gate 2: semantic extraction (PyAttribute wrappers removed) --------------

def test_extracted_is_unwrapped_semantic_value():
    ws = assemble_world_state(_probe_raw())
    e = ws["extracted"]
    assert e["flame.active_sequence"] == "30sec_edit 21"   # NOT "PyAttribute:30sec_edit 21"
    assert e["flame.current_shot"] == "tst_020"
    assert e["flame.open_batch"] == "FCX_OFX_TEST"
    assert e["flame.project"] == "013_13_13_2026_2_1_portofino"
    # typed selection (probe #5b shape): unwrapped name/shot_name, context-tagged
    assert e["flame.selected"] == [
        {"type": "PySegment", "name": "tst_020_graded_L01", "shot_name": "tst_020", "context": "timeline"},
        {"type": "PySegment", "name": "tst_030_graded_L01", "shot_name": "tst_030", "context": "timeline"},
        {"type": "PySegment", "name": "tst_040_graded_L01", "shot_name": "tst_040", "context": "timeline"},
    ]
    # no wrapper string leaked anywhere into extracted (scalar fields)
    assert not any(
        isinstance(v, str) and v.startswith("PyAttribute:") for v in e.values()
    )
    # ...nor inside the typed selection
    assert not any(
        str(x).startswith("PyAttribute:")
        for item in e["flame.selected"] for x in item.values()
    )


def test_unwrap_is_idempotent_on_clean_values():
    raw = _probe_raw()
    raw["timeline"]["active_sequence"] = "30sec_edit 21"  # already clean
    ws = assemble_world_state(raw)
    assert ws["extracted"]["flame.active_sequence"] == "30sec_edit 21"


def test_closed_batch_does_not_emit_open_batch():
    raw = _probe_raw()
    raw["batch"]["opened"] = False
    ws = assemble_world_state(raw)
    assert "flame.open_batch" not in ws["extracted"]


# --- Gate 3: round-trip recoverability ---------------------------------------

def test_extracted_recomputable_from_raw_but_not_vice_versa():
    raw = _probe_raw()
    ws = assemble_world_state(raw)
    # extracted is a pure function of raw — recompute, identical
    assert assemble_world_state(raw)["extracted"] == ws["extracted"]
    # raw carries strictly more than extracted (the unreachable_api reason,
    # batch internals, plus the raw nesting/provenance) — not regenerable from
    # extracted. current_segment_name now deliberately projects as the shot
    # fallback focus signal for S4.
    assert "current_segment_name" in raw["timeline"]
    assert ws["extracted"]["flame.current_segment_name"] == "tst_020_graded_L01"
    assert raw["playhead_frame_reason"] == "unreachable_api"


# --- Gate 4: S2 -> S4 cross-phase contract (the load-bearing one) ------------

def _record_with(ws, compiled):
    return build_record(
        captured_at="t",
        provenance={"context_source": "flame", "capture_version": "1",
                    "capture_surface": "python_console", "capture_adapter": "v1"},
        prompt="rename this sequence with prefix tv",
        observed_translation={"compiled_graph": [compiled], "ratified_graph": None},
        outcome="preview_emitted", world_state=ws,
    )


def test_s2_output_feeds_s4_mismatch_flags_wrong_referent():
    ws = assemble_world_state(_probe_raw())  # focus active_sequence = 30sec_edit 21
    rec = _record_with(ws, "flame_rename_shots sequence_name=30sec_21 prefix=tv commit=true")
    cands = flag_contextual_failure_candidates(rec)
    assert [c["mode"] for c in cands] == ["wrong_referent"]
    assert cands[0]["compiled_value"] == "30sec_21"
    assert cands[0]["focus_value"] == "30sec_edit 21"


def test_s2_output_feeds_s4_match_is_not_flagged():
    """If S2 left the wrapper in extracted, this matching case would ALSO flag
    (false positive) — so this is the test that proves the unwrap matters."""
    ws = assemble_world_state(_probe_raw())
    rec = _record_with(ws, 'flame_rename_shots sequence_name="30sec_edit 21" prefix=tv commit=true')
    assert flag_contextual_failure_candidates(rec) == []


# --- PRODUCTION SHAPE (probe #4 live finding): str(PyAttribute) single-quotes -

def _live_raw():
    """The ACTUAL raw shape live FOCUS_SNAPSHOT_PY emits (probe #4 + #5b, Flame
    2026.2.2): str(PyAttribute) wraps values in single quotes; typed selection is
    pulled via .get_value() (probe #5b) as {type, name, shot_name} per object,
    with empty-name segments possible. The dev-box fixture above used probe-_safe
    shape; THIS mirrors production (fixture-mirrors-production)."""
    return {
        "project": "013_13_13_2026_2_1_portofino",
        "current_tab": "Timeline",
        "media_panel": {"selected": []},
        "batch": {"name": "'FCX_METAL_TEST'", "opened": True, "current_iteration": "'FCX_METAL_TEST_001'", "selected": None},
        "timeline": {
            "active_sequence": "'30sec_edit 21'",      # single-quoted by str(PyAttribute)
            "current_shot": "'tst_020'",
            "current_segment_name": "'tst_020_graded_L01'",
            "selected": [
                {"type": "PySegment", "name": "'tst_010_graded'", "shot_name": "'tst_010'"},
                {"type": "PySegment", "name": "'tst_110_graded'", "shot_name": "'tst_110'"},
                {"type": "PySegment", "name": "''", "shot_name": "''"},   # gap/transition -> filtered
            ],
        },
        "playhead_frame": None,
        "playhead_frame_reason": "unreachable_api",
    }


def test_live_quoted_values_are_unwrapped_in_extracted():
    e = assemble_world_state(_live_raw())["extracted"]
    assert e["flame.active_sequence"] == "30sec_edit 21"   # quotes stripped
    assert e["flame.current_shot"] == "tst_020"
    assert e["flame.open_batch"] == "FCX_METAL_TEST"
    assert "'" not in "".join(str(v) for v in e.values() if isinstance(v, str))


def test_live_selection_typed_unwrapped_and_empty_filtered():
    e = assemble_world_state(_live_raw())["extracted"]
    assert e["flame.selected"] == [
        {"type": "PySegment", "name": "tst_010_graded", "shot_name": "tst_010", "context": "timeline"},
        {"type": "PySegment", "name": "tst_110_graded", "shot_name": "tst_110", "context": "timeline"},
    ]  # quotes stripped; the empty-name item filtered out


def test_live_shape_s4_match_is_not_flagged_the_probe4_regression():
    """The probe #4 CONTRACT FAILURE, pinned: a genuine match must NOT flag.
    With quoted focus + quote-stripped compiled, the buggy path false-positived."""
    ws = assemble_world_state(_live_raw())
    seq = ws["extracted"]["flame.active_sequence"]  # "30sec_edit 21" (clean)
    match = _record_with(ws, 'flame_rename_shots sequence_name="%s" prefix=tv commit=true' % seq)
    assert flag_contextual_failure_candidates(match) == []
    mismatch = _record_with(ws, "flame_rename_shots sequence_name=30sec_21 prefix=tv commit=true")
    assert [c["mode"] for c in flag_contextual_failure_candidates(mismatch)] == ["wrong_referent"]
