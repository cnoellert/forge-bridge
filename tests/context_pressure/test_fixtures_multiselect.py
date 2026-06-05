"""Keeper test for the QUARANTINED held multi-selection fixture.

This does NOT test the ``ambiguous``/``candidates`` arm — that arm has no S4 path
yet and is deferred POST-recapture (room DECISION #2). It asserts only what is
testable TODAY: the capture/assemble path handles a real cross-context
multi-selection faithfully, and the fixture stays well-formed for when the
ambiguous detector is built. See ``fixtures_multiselect.py`` for provenance + the
hard-quarantine note (this is never a ``records.jsonl`` line).
"""
from __future__ import annotations

from forge_bridge.context_pressure._focus import assemble_world_state
from tests.context_pressure.fixtures_multiselect import multiselect_raw


def test_held_multiselect_assembles_cross_context():
    sel = assemble_world_state(multiselect_raw())["extracted"]["flame.selected"]
    seqs = [d for d in sel if d["type"] == "PySequence"]
    segs = [d for d in sel if d["type"] == "PySegment"]
    # 1 PySequence (media_panel) + 8 PySegment (timeline) = the cross-context case
    assert len(seqs) == 1 and seqs[0]["name"] == "Backup"
    assert len(segs) == 8                      # >=2 same-type-in-context: the future AMBIGUOUS case
    assert {d["context"] for d in sel} == {"media_panel", "timeline"}
    # names unwrapped (no residual str(PyAttribute) quotes)
    assert all(not d["name"].startswith("'") for d in sel)


def test_held_fixture_is_not_a_corpus_record():
    """Quarantine guard: a held capture carries no authored analysis layer — it is a
    test fixture, not a measurement record."""
    raw = multiselect_raw()
    assert "analysis" not in raw            # not an authored corpus record
    assert "prompt" not in raw              # not an interaction capture line
