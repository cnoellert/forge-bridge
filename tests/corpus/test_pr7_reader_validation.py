"""tests.corpus.test_pr7_reader_validation — PR 7 §5.1 reader
validation behavior.

Five tests exercising the reader's ``record_kind`` and source
ontology enforcement at the integration of PR 7 Step 5's schema
validator and Step 7's reader interpretation. The reader's job:
yield well-formed records, log WARNING + skip malformed records,
never abort iteration.

See ``forge_bridge/corpus/_sources.py`` module docstring for the
14 inherited carriers + binding framing clarification (verbatim).
The §5.5 legacy-record synthesis pair (verbatim, scope-local to
``reader.py``) is documented at the production module; legacy
synthesis is covered separately in
``test_pr7_legacy_record_synthesis.py``. This module covers the
contemporary-record validation surface.

Tests (per ``A.5.3.2-PR7-SPEC.md`` §5.1):

- test_reader_accepts_observation_record
- test_reader_accepts_expectation_record
- test_reader_skips_unknown_record_kind
- test_reader_skips_observation_with_unknown_source
- test_reader_skips_expectation_with_source_field

Test count: 5. Lands at PR 7 Step 7 per §6 step 7 (light-touch
review).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from forge_bridge.corpus import (
    SCHEMA_VERSION,
    read_capture_file,
)
from forge_bridge.corpus._capture import _build_capture_record

from tests.corpus._pr3_helpers import base_builder_args


# ── Helpers ────────────────────────────────────────────────────────────────


def _make_header(captured_at: str = "2026-05-09T12:00:00.000Z") -> dict:
    """Build a valid header record matching ``_capture._make_header``."""
    return {
        "_header": True,
        "schema_version": SCHEMA_VERSION,
        "created_at": captured_at,
        "format": "forge-bridge-divergence-corpus-v1",
    }


def _make_minimum_expectation_record(
    captured_at: str = "2026-05-09T12:00:00.001Z",
    capture_id: str = "expectation-test-uuid-001",
) -> dict:
    """Minimum-shape valid expectation record.

    Per PR 7 Step 5 schema work: expectation records require the
    universal keys (schema_version, capture_id, captured_at,
    record_kind). The 6 observation-specific keys (source,
    prompt, candidate_set, topology, identity, narrower) are
    scoped to observation records.

    Updated at PR 8 Step 2 (per A.5.3.2-PR8-SPEC.md §4.2 — the
    schema extension landing) to include the three PR 8-required
    fields: fixture_id, prompt, expected_narrow. The helper
    update is the mechanical consequence of the schema extension;
    the test bodies are unchanged.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "capture_id": capture_id,
        "captured_at": captured_at,
        "record_kind": "expectation",
        # PR 8 Step 2 — required expectation fields per
        # _schema.py::_REQUIRED_EXPECTATION_KEYS:
        "fixture_id": "fix-pr7-reader",
        "prompt": "reader validation probe",
        "expected_narrow": ["forge_list_staged"],
    }


def _write_jsonl(path: Path, records: list[dict]) -> None:
    """Write records as JSONL lines (compact, UTF-8, newline-terminated).

    Hand-crafted writer for tests that need control over record
    content (malformed cases, structural-asymmetry violations).
    Tests using the real writer go through
    ``emit_divergence_capture`` instead.
    """
    lines = [
        json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n"
        for r in records
    ]
    path.write_text("".join(lines), encoding="utf-8")


# ── Tests ──────────────────────────────────────────────────────────────────


def test_reader_accepts_observation_record(tmp_path, clean_identity_caches):
    """Header + minimum-shape observation record (constructed via
    ``_build_capture_record``) is yielded with
    ``record_kind="observation"``.

    The fixture goes through the production builder so the test
    record carries the same shape live arbitration emits — including
    the post-Step-6 ``fixture_id`` field always-present property.
    """
    record = _build_capture_record(**base_builder_args())
    path = tmp_path / "test-obs.jsonl"
    _write_jsonl(path, [_make_header(), record])

    yielded = list(read_capture_file(path))

    assert len(yielded) == 1
    assert yielded[0]["record_kind"] == "observation"
    assert yielded[0]["source"] == "runtime"
    assert yielded[0]["fixture_id"] is None


def test_reader_accepts_expectation_record(tmp_path):
    """Header + minimum-shape expectation record is yielded with
    ``record_kind="expectation"`` and no ``source`` field.

    The reader yields the record verbatim; no synthesis fires
    because ``record_kind`` is already present. The test's
    protected property: the reader does not transform expectation
    records — it passes them through unchanged after schema
    validation.

    Updated at PR 8 Step 2: PR 7's minimum-shape was 4 universal
    keys only; PR 8 extends with fixture_id, prompt,
    expected_narrow per A.5.3.2-PR8-SPEC.md §4.2. The
    ``"fixture_id" not in yielded[0]`` assertion was anchored on
    the PR 7-era shape and is removed; the protected property
    (reader passes records through unchanged) is preserved by
    asserting the record dict matches the input exactly.
    """
    record = _make_minimum_expectation_record()
    path = tmp_path / "test-exp.jsonl"
    _write_jsonl(path, [_make_header(), record])

    yielded = list(read_capture_file(path))

    assert len(yielded) == 1
    assert yielded[0]["record_kind"] == "expectation"
    assert "source" not in yielded[0]
    # PR 8 Step 2: reader passes the record through verbatim.
    # The PR 7-era "no fixture_id" assertion is obsolete (PR 8
    # extends the minimum shape); the protected property is
    # preserved by asserting the yielded record equals the input.
    assert yielded[0] == record


def test_reader_skips_unknown_record_kind(
    tmp_path, caplog, clean_identity_caches,
):
    """Record with ``record_kind="bogus"`` is skipped with a WARNING
    log; iteration continues without aborting.

    The Step 5 validator's ``_KNOWN_RECORD_KINDS`` enforcement is the
    underlying mechanism. Per Gate 2 framing §9.2, ``record_kind`` is
    governed structurally — a third value requires framing-level
    review and corresponding helper/signature/comparator updates.
    """
    record = _build_capture_record(**base_builder_args())
    record["record_kind"] = "bogus"
    path = tmp_path / "test-bogus-kind.jsonl"
    _write_jsonl(path, [_make_header(), record])

    with caplog.at_level(
        logging.WARNING, logger="forge_bridge.corpus.reader",
    ):
        yielded = list(read_capture_file(path))

    assert yielded == []
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "schema validation failed" in warnings[0].message


def test_reader_skips_observation_with_unknown_source(
    tmp_path, caplog, clean_identity_caches,
):
    """Observation record with ``source="phantom"`` is skipped with a
    WARNING log.

    The Step 5 validator enforces ``source ∈ KNOWN_SOURCE_VALUES`` on
    the observation branch. Adding a new source class requires
    framing-level review + synchronous update of multiple downstream
    surfaces (per ``_sources.py`` PROTECTED PROPERTY).
    """
    record = _build_capture_record(**base_builder_args())
    record["source"] = "phantom"
    path = tmp_path / "test-phantom-source.jsonl"
    _write_jsonl(path, [_make_header(), record])

    with caplog.at_level(
        logging.WARNING, logger="forge_bridge.corpus.reader",
    ):
        yielded = list(read_capture_file(path))

    assert yielded == []
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "schema validation failed" in warnings[0].message


def test_reader_skips_expectation_with_source_field(tmp_path, caplog):
    """Expectation record carrying a ``source`` field is skipped with
    a WARNING log.

    The Step 5 validator's expectation branch enforces the structural
    asymmetry: expectation records must NOT carry a ``source`` field.
    The asymmetry is the visible discriminator between the two truth
    classes; relaxing it would erode the partitioning Gate 2 framing
    establishes.
    """
    record = _make_minimum_expectation_record()
    record["source"] = "runtime"
    path = tmp_path / "test-expectation-with-source.jsonl"
    _write_jsonl(path, [_make_header(), record])

    with caplog.at_level(
        logging.WARNING, logger="forge_bridge.corpus.reader",
    ):
        yielded = list(read_capture_file(path))

    assert yielded == []
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "schema validation failed" in warnings[0].message
