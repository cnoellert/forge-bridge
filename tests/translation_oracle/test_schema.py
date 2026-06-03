"""TF.3a Step 1 — schema lock tests.

Each test pins one ratified seam decision so a future edit that breaks it fails
loudly rather than silently regressing the instrument.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from forge_bridge.translation_oracle import (
    SCHEMA_VERSION,
    SchemaValidationError,
    validate_translation_case,
)


def _observed(provenance="instrumented-translation", **markers):
    base = {
        "capture_provenance": provenance,
        "observed_graph": ["flame_list_shots {}"],
        "observed_resolved_params": {},
        "outcome": "answered",
        "tool_forced": False,
        "tools_filtered": 2,
        "abort_reason": None,
        "tool_selected": "flame_list_shots",
    }
    base.update(markers)
    return base


def _label(**over):
    label = {
        "input": "rename the shots on 30sec_21 with prefix noise",
        "expected_graph": ["flame_rename_shots {sequence_name=30sec_21, prefix=noise}"],
        "expected_params": {"sequence_name": "30sec_21", "prefix": "noise"},
        "expected_verdict_pair": {"translation": "fail", "substrate": "pass"},
        "expected_classes": ["grounding"],
        "world_state": None,
        "expected_provenance": {"prefix": "filled-from-example"},
    }
    label.update(over)
    return label


def _case(*, label=None, observed=None):
    record = {"schema_version": SCHEMA_VERSION, "observed": observed or _observed()}
    if label is not None:
        record["label"] = label
    return record


# --- item 1: ObservedTrace required, Label optional (the 3a/3b boundary) -----

def test_label_free_case_is_valid():
    """A 3b record carries ObservedTrace only — must validate."""
    validate_translation_case(_case())  # no label key at all
    validate_translation_case(_case(label=None))  # explicit null


def test_labeled_case_is_valid():
    validate_translation_case(_case(label=_label()))


def test_observed_is_required():
    with pytest.raises(SchemaValidationError, match="observed is required"):
        validate_translation_case({"schema_version": SCHEMA_VERSION})


# --- item 2: capture_provenance is a required, enum'd ObservedTrace field ----

def test_capture_provenance_required():
    obs = _observed()
    del obs["capture_provenance"]
    with pytest.raises(SchemaValidationError, match="capture_provenance is required"):
        validate_translation_case(_case(observed=obs))


def test_capture_provenance_enum_enforced():
    with pytest.raises(SchemaValidationError, match="capture_provenance must be"):
        validate_translation_case(_case(observed=_observed(provenance="legibility")))


def test_seed_legibility_trace_may_be_sparse():
    """Seed traces carry sparse markers; only capture_provenance is required."""
    validate_translation_case(_case(observed={
        "capture_provenance": "seed-legibility",
        "observed_graph": ["flame_list_batch_groups {}"],
    }))


def test_existing_fieldless_corpus_row_still_validates():
    reference = (
        Path(__file__).parents[2]
        / "forge_bridge"
        / "translation_oracle"
        / "reference"
        / "cases.jsonl"
    )
    first = next(
        json.loads(line)
        for line in reference.read_text().splitlines()
        if line.strip() and not json.loads(line).get("_header")
    )

    assert "salvage_applied" not in first["observed"]
    assert "original_reason" not in first["observed"]
    validate_translation_case(first)


# --- Q1 locked floor: a present Label must carry a verdict-pair + world_state -

def test_label_requires_verdict_pair():
    label = _label()
    del label["expected_verdict_pair"]
    with pytest.raises(SchemaValidationError, match="expected_verdict_pair is required"):
        validate_translation_case(_case(label=label))


def test_label_requires_world_state_key_but_value_may_be_null():
    label = _label()
    del label["world_state"]
    with pytest.raises(SchemaValidationError, match="world_state key is required"):
        validate_translation_case(_case(label=label))
    # present-but-null is fine (text-sufficient input)
    validate_translation_case(_case(label=_label(world_state=None)))


def test_verdict_pair_values_enforced():
    with pytest.raises(SchemaValidationError, match="substrate must be"):
        validate_translation_case(_case(label=_label(
            expected_verdict_pair={"translation": "pass", "substrate": "ok"},
        )))


def test_honest_decline_verdict_pair_is_valid():
    """(translation=pass, substrate=gap) is the rewarded honest-decline cell —
    a translation SUCCESS, so it carries NO failure classes."""
    validate_translation_case(_case(label=_label(
        expected_verdict_pair={"translation": "pass", "substrate": "gap"},
        expected_classes=[],
    )))


# --- TF.2 §3-4 class tags + the classes<=>translation-FAIL consistency rule ---

def test_expected_classes_key_required():
    label = _label()
    del label["expected_classes"]
    with pytest.raises(SchemaValidationError, match="expected_classes key is required"):
        validate_translation_case(_case(label=label))


def test_expected_classes_value_enum_enforced():
    with pytest.raises(SchemaValidationError, match="expected_classes values"):
        validate_translation_case(_case(label=_label(expected_classes=["typo-class"])))


def test_translation_fail_requires_nonempty_classes():
    with pytest.raises(SchemaValidationError, match="non-empty when translation=fail"):
        validate_translation_case(_case(label=_label(
            expected_verdict_pair={"translation": "fail", "substrate": "pass"},
            expected_classes=[],
        )))


def test_translation_pass_requires_empty_classes():
    with pytest.raises(SchemaValidationError, match="empty when translation=pass"):
        validate_translation_case(_case(label=_label(
            expected_verdict_pair={"translation": "pass", "substrate": "pass"},
            expected_classes=["routing"],
        )))


def test_multi_tag_classes_accepted():
    """defect #2 = routing + extraction in one case (multi-tag, TF.2 §4)."""
    validate_translation_case(_case(label=_label(
        expected_classes=["routing", "extraction"],
        defect_ref="defect-2",
    )))


# --- well-formedness tier (room ratification): malformed graph short-circuits --

def test_wellformedness_failure_requires_fail_and_empty_classes():
    # malformed (serialization) — valid: fail + empty classes
    validate_translation_case(_case(label=_label(
        expected_well_formed=False,
        expected_verdict_pair={"translation": "fail", "substrate": "pass"},
        expected_classes=[],
    )))


def test_wellformedness_failure_rejects_content_classes():
    with pytest.raises(SchemaValidationError, match="requires empty expected_classes"):
        validate_translation_case(_case(label=_label(
            expected_well_formed=False,
            expected_classes=["routing"],  # content short-circuited — illegal
        )))


def test_wellformedness_failure_must_be_translation_fail():
    with pytest.raises(SchemaValidationError, match="requires translation=fail"):
        validate_translation_case(_case(label=_label(
            expected_well_formed=False,
            expected_verdict_pair={"translation": "pass", "substrate": "pass"},
            expected_classes=[],
        )))


# --- Q1/TF.1 §2: context-resolved params labeled unresolved-pending-dispatch -

def test_unresolved_context_param_accepted():
    validate_translation_case(_case(label=_label(
        input="rename this sequence with prefix noise",
        expected_params={"sequence_name": "unresolved-pending-dispatch"},
        expected_classes=["contextual"],
        world_state={"open_sequence": "30sec_edit 21_publish"},
        expected_provenance={"sequence_name": "unresolved", "prefix": "grounded-from-intent"},
    )))


# --- Q5 three-vocabulary rule: provenance must not borrow other instruments' --

def test_provenance_rejects_comprehension_vocab():
    """'loved' is comprehension's verdict vocab — must not validate here."""
    with pytest.raises(SchemaValidationError, match="expected_provenance"):
        validate_translation_case(_case(label=_label(
            expected_provenance={"prefix": "loved"},
        )))


# --- schema version --------------------------------------------------------

def test_schema_version_enforced():
    with pytest.raises(SchemaValidationError, match="schema_version must be"):
        validate_translation_case({"schema_version": "0", "observed": _observed()})
