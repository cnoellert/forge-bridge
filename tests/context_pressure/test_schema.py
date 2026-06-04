"""S1 — ContextPressureRecord schema contract."""
from __future__ import annotations

import copy

import pytest

from forge_bridge.context_pressure import (
    SchemaValidationError,
    validate_context_pressure_record,
)


def _valid_record() -> dict:
    return {
        "schema_version": "1",
        "captured_at": "2026-06-04T10:00:00Z",
        "provenance": {
            "context_source": "flame",
            "capture_version": "1",
            "capture_surface": "python_console",
            "capture_adapter": "sgtk_console_v1",
        },
        "prompt": "rename this sequence with prefix tv",
        "observed_translation": {
            "compiled_graph": [
                "flame_rename_shots sequence_name=30sec_21 prefix=tv commit=true"
            ],
            "ratified_graph": None,
        },
        "outcome": "blocked_at_ratify",
        "world_state": {
            "source": "flame",
            "raw": {"flame_context": {"project": "p"}, "timeline": {"clip": "30sec_edit 21"}},
            "extracted": {"flame.active_sequence": "30sec_edit 21"},
        },
        "analysis": None,
    }


def test_valid_record_passes():
    validate_context_pressure_record(_valid_record())


@pytest.mark.parametrize(
    "key",
    ["schema_version", "captured_at", "provenance", "prompt",
     "observed_translation", "outcome", "world_state", "analysis"],
)
def test_missing_required_key_raises(key):
    rec = _valid_record()
    del rec[key]
    with pytest.raises(SchemaValidationError):
        validate_context_pressure_record(rec)


def test_bad_context_source_raises():
    rec = _valid_record()
    rec["provenance"]["context_source"] = "maya"
    with pytest.raises(SchemaValidationError):
        validate_context_pressure_record(rec)


def test_provenance_requires_all_four_day_one_fields():
    for field in ("capture_version", "capture_surface", "capture_adapter"):
        rec = _valid_record()
        del rec["provenance"][field]
        with pytest.raises(SchemaValidationError):
            validate_context_pressure_record(rec)


def test_bad_outcome_raises():
    rec = _valid_record()
    rec["outcome"] = "answered"  # comprehension's vocab, NOT this instrument's
    with pytest.raises(SchemaValidationError):
        validate_context_pressure_record(rec)


def test_world_state_source_must_equal_context_source():
    rec = _valid_record()
    rec["world_state"]["source"] = "cli"  # diverges from provenance.context_source
    with pytest.raises(SchemaValidationError):
        validate_context_pressure_record(rec)


def test_world_state_raw_and_extracted_must_be_dicts():
    for sub in ("raw", "extracted"):
        rec = _valid_record()
        rec["world_state"][sub] = ["not", "a", "dict"]
        with pytest.raises(SchemaValidationError):
            validate_context_pressure_record(rec)


def test_compiled_graph_must_be_list_of_strings():
    rec = _valid_record()
    rec["observed_translation"]["compiled_graph"] = [{"step": "x"}]
    with pytest.raises(SchemaValidationError):
        validate_context_pressure_record(rec)


# --- the no-copy lock: validation backstop -----------------------------------

def test_analysis_null_is_valid():
    validate_context_pressure_record(_valid_record())  # analysis is None


def test_analysis_present_requires_authored_at():
    rec = _valid_record()
    rec["analysis"] = {"failure_class": "wrong_referent", "referent": "30sec_edit 21"}
    with pytest.raises(SchemaValidationError):
        validate_context_pressure_record(rec)


def test_authored_analysis_with_stamp_is_valid():
    rec = _valid_record()
    rec["analysis"] = {
        "authored_at": "2026-06-04T11:00:00Z",
        "failure_class": "wrong_referent",
        "referent": "30sec_edit 21",
        "world_state_resolvable": True,
        "resolving_signal": "flame.active_sequence",
    }
    validate_context_pressure_record(rec)


def test_bad_failure_class_raises():
    rec = _valid_record()
    rec["analysis"] = {"authored_at": "t", "failure_class": "made_up_class"}
    with pytest.raises(SchemaValidationError):
        validate_context_pressure_record(rec)


def test_world_state_resolvable_must_be_bool():
    rec = _valid_record()
    rec["analysis"] = {"authored_at": "t", "world_state_resolvable": "yes"}
    with pytest.raises(SchemaValidationError):
        validate_context_pressure_record(rec)


def test_validation_does_not_mutate_input():
    rec = _valid_record()
    before = copy.deepcopy(rec)
    validate_context_pressure_record(rec)
    assert rec == before
