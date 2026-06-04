"""S1 — capture factory (structural no-copy) + atomic-append corpus I/O."""
from __future__ import annotations

import pytest

from forge_bridge.context_pressure import (
    SchemaValidationError,
    append_record,
    build_record,
    read_records,
)


def _captured_fields() -> dict:
    return {
        "captured_at": "2026-06-04T10:00:00Z",
        "provenance": {
            "context_source": "flame",
            "capture_version": "1",
            "capture_surface": "python_console",
            "capture_adapter": "sgtk_console_v1",
        },
        "prompt": "what's the duration of shot 10 on 30sec_edit 21",
        "observed_translation": {"compiled_graph": ["forge_get_shot shot=10"], "ratified_graph": None},
        "outcome": "chain_complete",
        "world_state": {"source": "flame", "raw": {"x": 1}, "extracted": {}},
    }


def test_build_record_sets_analysis_none_and_validates():
    rec = build_record(**_captured_fields())
    assert rec["analysis"] is None
    assert rec["schema_version"] == "1"


def test_build_record_has_no_analysis_parameter():
    # The structural no-copy teeth: capture CANNOT author. Passing analysis is a
    # TypeError, not a silently-accepted field.
    with pytest.raises(TypeError):
        build_record(analysis={"authored_at": "t"}, **_captured_fields())


def test_build_record_rejects_invalid_fields():
    fields = _captured_fields()
    fields["outcome"] = "nope"
    with pytest.raises(SchemaValidationError):
        build_record(**fields)


def test_append_then_read_round_trips(tmp_path):
    rec = build_record(**_captured_fields())
    append_record(rec, corpus_dir=tmp_path)
    got = read_records(corpus_dir=tmp_path)
    assert got == [rec]


def test_append_writes_header_once(tmp_path):
    rec = build_record(**_captured_fields())
    append_record(rec, corpus_dir=tmp_path)
    append_record(rec, corpus_dir=tmp_path)
    path = tmp_path / "records.jsonl"
    lines = [ln for ln in path.read_text().splitlines() if ln.strip()]
    headers = [ln for ln in lines if '"_header"' in ln]
    assert len(headers) == 1
    assert read_records(corpus_dir=tmp_path) == [rec, rec]


def test_read_missing_corpus_returns_empty(tmp_path):
    assert read_records(corpus_dir=tmp_path / "nope") == []


def test_append_rejects_invalid_record(tmp_path):
    bad = build_record(**_captured_fields())
    bad["outcome"] = "answered"
    with pytest.raises(SchemaValidationError):
        append_record(bad, corpus_dir=tmp_path)
