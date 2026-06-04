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
        "batch": {
            "name": "PyAttribute:FCX_OFX_TEST",
            "opened": True,
            "current_iteration": "PyAttribute:FCX_OFX_TEST_001",
            "selected_nodes": [],
        },
        "timeline": {
            "active_sequence": "PyAttribute:30sec_edit 21",
            "current_shot": "PyAttribute:tst_020",
            "current_segment_name": "PyAttribute:tst_020_graded_L01",
            "selection": ["PyAttribute:tst_020", "PyAttribute:tst_030", "PyAttribute:tst_040"],
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
    assert e["flame.selection"] == ["tst_020", "tst_030", "tst_040"]
    # no wrapper string leaked anywhere into extracted
    assert not any(
        isinstance(v, str) and v.startswith("PyAttribute:") for v in e.values()
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
    # raw carries strictly more than extracted (current_segment_name, the
    # unreachable_api reason, batch internals) — not regenerable from extracted
    assert "current_segment_name" in raw["timeline"]
    assert "current_segment_name" not in str(ws["extracted"])
    assert raw["playhead_frame_reason"] == "unreachable_api"


# --- Gate 4: S2 -> S4 cross-phase contract (the load-bearing one) ------------

def _record_with(ws, compiled):
    return build_record(
        captured_at="t",
        provenance={"context_source": "flame", "capture_version": "1",
                    "capture_surface": "python_console", "capture_adapter": "v1"},
        prompt="rename this sequence with prefix tv",
        observed_translation={"compiled_graph": [compiled], "ratified_graph": None},
        outcome="blocked_at_ratify", world_state=ws,
    )


def test_s2_output_feeds_s4_mismatch_flags_wrong_resolution():
    ws = assemble_world_state(_probe_raw())  # focus active_sequence = 30sec_edit 21
    rec = _record_with(ws, "flame_rename_shots sequence_name=30sec_21 prefix=tv commit=true")
    cands = flag_contextual_failure_candidates(rec)
    assert [c["mode"] for c in cands] == ["wrong_resolution"]
    assert cands[0]["compiled_value"] == "30sec_21"
    assert cands[0]["focus_value"] == "30sec_edit 21"


def test_s2_output_feeds_s4_match_is_not_flagged():
    """If S2 left the wrapper in extracted, this matching case would ALSO flag
    (false positive) — so this is the test that proves the unwrap matters."""
    ws = assemble_world_state(_probe_raw())
    rec = _record_with(ws, 'flame_rename_shots sequence_name="30sec_edit 21" prefix=tv commit=true')
    assert flag_contextual_failure_candidates(rec) == []
