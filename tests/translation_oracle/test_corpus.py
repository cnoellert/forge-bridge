"""TF.3a Step 3 — corpus data layer + coverage accounting tests.

The load-bearing test is the Tier-1 false-green guard: a seed-legibility trace
tagged with a Tier-1 class must NOT count as coverage (it lacks the runtime
markers the detector reads).
"""
from __future__ import annotations

from forge_bridge.translation_oracle import (
    REFERENCE_DIR,
    SCHEMA_VERSION,
    append_case,
    coverage_report,
    read_cases,
)


def _case(*, classes, translation="fail", substrate="pass",
          provenance="instrumented-translation", defect_ref=None, labeled=True,
          well_formed=True):
    case = {
        "schema_version": SCHEMA_VERSION,
        "observed": {"capture_provenance": provenance, "observed_graph": ["x {}"]},
    }
    if labeled:
        case["label"] = {
            "input": "i",
            "expected_graph": ["x {}"],
            "expected_params": {},
            "expected_verdict_pair": {"translation": translation, "substrate": substrate},
            "expected_classes": classes,
            "expected_well_formed": well_formed,
            "world_state": None,
            "defect_ref": defect_ref,
        }
    return case


def test_append_and_read_round_trip(tmp_path):
    append_case(_case(classes=["grounding"]), corpus_dir=tmp_path)
    append_case(_case(classes=[], translation="pass", substrate="pass"), corpus_dir=tmp_path)
    cases = read_cases(corpus_dir=tmp_path)
    assert len(cases) == 2
    # header line is skipped, not returned
    assert all("_header" not in c for c in cases)


def test_append_validates(tmp_path):
    import pytest
    from forge_bridge.translation_oracle import SchemaValidationError
    bad = {"schema_version": SCHEMA_VERSION}  # missing observed
    with pytest.raises(SchemaValidationError):
        append_case(bad, corpus_dir=tmp_path)


def test_empty_corpus_is_incomplete():
    report = coverage_report([])
    assert report["complete"] is False
    assert set(report["missing_cells"]) == {"a", "b", "c", "d"}


def test_tier1_seed_legibility_is_a_false_green_guard():
    """A seed-legibility trace tagged 'extraction' (Tier-1) must NOT count —
    it lacks the markers the extraction detector reads. RED, not GREEN."""
    seed_only = [_case(classes=["extraction"], provenance="seed-legibility")]
    report = coverage_report(seed_only)
    ext = report["classes"]["extraction"]
    assert ext["tagged"] == 1        # the case is tagged...
    assert ext["counting"] == 0      # ...but does not count toward coverage
    assert ext["met"] is False
    assert any("false-green" in flag for flag in report["red_flags"])


def test_tier1_instrumented_counts():
    instrumented = [_case(classes=["extraction"], provenance="instrumented-translation")]
    report = coverage_report(instrumented)
    assert report["classes"]["extraction"]["counting"] == 1
    assert report["classes"]["extraction"]["met"] is True


def test_tier2_requires_two_instances():
    one = [_case(classes=["grounding"])]
    assert coverage_report(one)["classes"]["grounding"]["met"] is False
    two = [_case(classes=["grounding"]), _case(classes=["grounding"])]
    assert coverage_report(two)["classes"]["grounding"]["met"] is True


def test_label_free_cases_do_not_contribute():
    report = coverage_report([_case(classes=["x"], labeled=False)])
    assert report["labeled_count"] == 0


def test_complete_corpus_reports_green():
    cases = [
        # cell a (pass/pass) + cell c (pass/gap): translation successes, no classes
        _case(classes=[], translation="pass", substrate="pass"),
        _case(classes=[], translation="pass", substrate="gap"),
        # multi-tag routing+extraction (Tier-1, instrumented) + cell d + space-mangle
        _case(classes=["routing", "extraction"], defect_ref="space-mangle"),
        _case(classes=["routing", "extraction"], substrate="gap",
              defect_ref="capability-gap-misroute"),  # cell d
        # contextual (Tier-1, instrumented) + defect-3
        _case(classes=["contextual"], defect_ref="defect-3"),
        # grounding x2 (Tier-2)
        _case(classes=["grounding"]),
        _case(classes=["grounding"]),
        # entity-resolution x2 (Tier-2)
        _case(classes=["entity-resolution"]),
        _case(classes=["entity-resolution"]),
        # well-formedness tier (serialization) — the gating tier
        _case(classes=[], well_formed=False, defect_ref="serialization"),
    ]
    report = coverage_report(cases)
    assert report["red_flags"] == []
    assert report["missing_cells"] == []
    assert report["complete"] is True, report


def test_reference_corpus_well_formedness_fails_stay_frozen_at_six():
    cases = read_cases(corpus_dir=REFERENCE_DIR)

    assert coverage_report(cases)["well_formedness_fails"] == 6


def test_postgate_corpus_well_formedness_fails_follow_observed_trace():
    cases = read_cases(corpus_dir=REFERENCE_DIR / "postgate")

    assert coverage_report(cases)["well_formedness_fails"] == 3
