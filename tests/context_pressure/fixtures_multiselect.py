"""QUARANTINED HELD FIXTURE — live multi-selection capture (prepared instrument).

PROVENANCE: a REAL, read-only ``FOCUS_SNAPSHOT_PY`` capture taken on **portofino**,
**2026-06-05**, Flame **2026.2.2**, project ``013_13_13_2026_2_1_portofino``. Single
live ``get_value()`` dump (the post-3c8fc61 typed-selection path); no mutation, no
reconstruction — the values below are verbatim.

WHY IT EXISTS — the prepared-instrument 3rd state ([[feedback_ecological_validity_
after_converged_phase]]). It is the cross-context multi-selection case S4 cannot
detect today: **1 ``PySequence`` (media_panel) + 8 ``PySegment``s (timeline)**. When
the ``ambiguous`` + ``candidates[]`` arm is built POST-recapture (room DECISION #2 —
NOT before the Q3 gate), this is its driving fixture:
  - segment dimension: 8 selected ``PySegment``s of the required type → ``ambiguous``
    + ``candidates`` (which of the 8 is "this shot"?).
  - sequence dimension: exactly 1 selected ``PySequence`` → ``resolved`` (single).

HARD QUARANTINE: this is a TEST fixture, NEVER a measurement record. It must NOT be
written to ``records.jsonl`` or enter the context_pressure corpus — a test-session
capture is corpus poison (the cursor's standing warning). It exists only to exercise
analysis code; it carries no ``analysis`` layer and is not authored.

Names are the faithful ``str(PyAttribute)`` form (quoted) exactly as Flame returns
them; ``assemble_world_state`` unwraps the quotes downstream (so does ``_unwrap``).
"""
from __future__ import annotations


def multiselect_raw() -> dict:
    """The verbatim raw FOCUS_SNAPSHOT capture (S2 raw contract). See module docstring."""
    return {
        "project": "013_13_13_2026_2_1_portofino",
        "current_tab": "Timeline",
        "media_panel": {
            "selected": [
                {"type": "PySequence", "name": "'Backup'", "shot_name": "''"},
            ]
        },
        "batch": {
            "name": "'Untitled Batch'",
            "opened": True,
            "current_iteration": "'Untitled Batch_00'",
            "selected": [],
        },
        "timeline": {
            "active_sequence": "'Backup'",
            "current_shot": "''",
            "current_segment_name": "'202A/04*'",
            "selected": [
                {"type": "PySegment", "name": "'202A/04*'", "shot_name": "''"},
                {"type": "PySegment", "name": "'104/02'", "shot_name": "''"},
                {"type": "PySegment", "name": "'202B/01'", "shot_name": "''"},
                {"type": "PySegment", "name": "'101/06*'", "shot_name": "''"},
                {"type": "PySegment", "name": "'DRONE FOG 03'", "shot_name": "''"},
                {"type": "PySegment", "name": "'110/02'", "shot_name": "''"},
                {"type": "PySegment", "name": "'101/00 REHEARSAL'", "shot_name": "''"},
                {"type": "PySegment", "name": "'EARLY AM FOG 01'", "shot_name": "''"},
            ],
        },
        "playhead_frame": None,
        "playhead_frame_reason": "unreachable_api",
    }
