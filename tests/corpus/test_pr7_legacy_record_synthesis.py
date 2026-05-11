"""tests.corpus.test_pr7_legacy_record_synthesis — PR 7 §5.1
legacy-record synthesis behavior.

Four tests exercising the read-time synthesis layer that PR 7 §4.4.2
introduces between ``json.loads`` and ``validate_capture_record``.

Pre-PR-7 records lack BOTH ``record_kind`` and ``fixture_id`` fields
(both are PR 7 additions). The reader synthesizes both together when
``record_kind`` is missing — the canonical legacy-record signal —
nested as a single conceptual unit:

    if "record_kind" not in record:
        record["record_kind"] = "observation"
        if "fixture_id" not in record:
            record["fixture_id"] = None

The fixture_id synthesis is **nested** inside the record_kind branch
(not unconditional) per the Step 7 review locks: it preserves PR 8's
design space on expectation-record shape, and it does not mask
hypothetical writer bugs that emit observation records lacking
``fixture_id``.

Tests (per ``A.5.3.2-PR7-SPEC.md`` §5.1):

- test_legacy_record_synthesized_as_observation
- test_legacy_file_unchanged_after_read (the §5.5 binding pair's
  byte-identicality enforcement)
- test_legacy_record_with_unknown_source_still_skipped
- test_mixed_legacy_and_contemporary_records (the mechanical guard
  against unconditional-fixture_id-synthesis regression: asserts
  contemporary expectation records yield without a synthesized
  ``fixture_id`` field)

Test count: 4. Lands at PR 7 Step 7 per §6 step 7 (light-touch
review).
"""
from __future__ import annotations

import hashlib
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


def _make_legacy_record(source: str = "runtime") -> dict:
    """Construct a pre-PR-7 record shape: observation fields present,
    ``record_kind`` and ``fixture_id`` absent.

    Built by constructing a contemporary observation record via
    ``_build_capture_record`` then stripping the two PR 7-introduced
    fields. Tracks schema evolution: if the observation-record shape
    changes in a future PR, this helper continues to produce a valid
    pre-PR-7 shape minus the two stripped fields.
    """
    record = _build_capture_record(**base_builder_args(source=source))
    del record["record_kind"]
    del record["fixture_id"]
    return record


def _write_jsonl(path: Path, records: list[dict]) -> None:
    """Write records as JSONL lines (compact, UTF-8, newline-terminated)."""
    lines = [
        json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n"
        for r in records
    ]
    path.write_text("".join(lines), encoding="utf-8")


# ── Tests ──────────────────────────────────────────────────────────────────


def test_legacy_record_synthesized_as_observation(
    tmp_path, clean_identity_caches,
):
    """A pre-PR-7 record (no ``record_kind``, no ``fixture_id``) is
    yielded with both fields synthesized.

    Synthesis: ``record_kind="observation"`` (§5.5 backward compat)
    AND ``fixture_id=None`` (Q3 structural-uniformity decision,
    nested under the record_kind branch).
    """
    record = _make_legacy_record()
    path = tmp_path / "test-legacy-synthesis.jsonl"
    _write_jsonl(path, [_make_header(), record])

    yielded = list(read_capture_file(path))

    assert len(yielded) == 1
    assert yielded[0]["record_kind"] == "observation"
    assert yielded[0]["fixture_id"] is None


def test_legacy_file_unchanged_after_read(tmp_path, clean_identity_caches):
    """The synthesis is in-memory only; file bytes are never modified.

    This is the §5.5 binding pair's mechanical enforcement (verbatim
    in ``reader.py`` module docstring + the synthesis-comment block):

        Legacy records may be interpreted through synthesized defaults
        at read time but are not rewritten or normalized in place by
        the reader.

    Run twice (full read + partial-read-via-iterator-takedown) to
    cover both consumption shapes.
    """
    record = _make_legacy_record()
    path = tmp_path / "test-byte-identicality.jsonl"
    _write_jsonl(path, [_make_header(), record])

    pre_bytes = path.read_bytes()
    pre_hash = hashlib.sha256(pre_bytes).hexdigest()

    # Full read.
    list(read_capture_file(path))

    post_bytes = path.read_bytes()
    post_hash = hashlib.sha256(post_bytes).hexdigest()
    assert post_bytes == pre_bytes
    assert post_hash == pre_hash

    # Partial read: take one record, then explicitly close the
    # generator. ``generator.close()`` raises ``GeneratorExit``
    # inside the generator, which propagates through the
    # ``with path.open(...)`` block, closing the file cleanly.
    # The reader never writes to the file regardless of when
    # iteration stops.
    gen = read_capture_file(path)
    next(gen)
    gen.close()

    post2_bytes = path.read_bytes()
    post2_hash = hashlib.sha256(post2_bytes).hexdigest()
    assert post2_bytes == pre_bytes
    assert post2_hash == pre_hash


def test_legacy_record_with_unknown_source_still_skipped(
    tmp_path, caplog, clean_identity_caches,
):
    """Synthesis assigns ``record_kind="observation"`` and
    ``fixture_id=None``, then the validator rejects the record on its
    unknown ``source`` value. Synthesis does not bypass validation.

    This test confirms the ordering: synthesis runs, then the
    validator runs against the synthesized record, then the WARNING
    log fires for schema validation failure.
    """
    record = _make_legacy_record(source="phantom")
    path = tmp_path / "test-legacy-bad-source.jsonl"
    _write_jsonl(path, [_make_header(), record])

    with caplog.at_level(
        logging.WARNING, logger="forge_bridge.corpus.reader",
    ):
        yielded = list(read_capture_file(path))

    assert yielded == []
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "schema validation failed" in warnings[0].message


def test_mixed_legacy_and_contemporary_records(
    tmp_path, clean_identity_caches,
):
    """Three records in one file:

    1. Legacy: synthesized ``record_kind="observation"`` AND
       synthesized ``fixture_id=None``.
    2. Contemporary observation (via ``_build_capture_record``):
       explicit ``record_kind="observation"``, explicit
       ``fixture_id=None`` (Q3 always-present field).
    3. Contemporary expectation (hand-crafted minimum-shape):
       explicit ``record_kind="expectation"``, **no** ``fixture_id``
       field — the reader does NOT synthesize ``fixture_id`` on
       expectation records (synthesis is nested under the
       ``record_kind not in record`` branch, not unconditional).

    The third assertion (``"fixture_id" not in yielded[2]``) is the
    mechanical guard against an unconditional-fixture_id-synthesis
    regression. If a future change relaxes the nested form to:

        if "record_kind" not in record:
            record["record_kind"] = "observation"
        if "fixture_id" not in record:
            record["fixture_id"] = None

    this test fails at the third assertion. The architectural
    intent (Q3 scoped to observation records; PR 8's design space
    preserved on expectation-record shape) is mechanically enforced
    here.
    """
    legacy = _make_legacy_record()
    observation = _build_capture_record(**base_builder_args())
    # Inline expectation record extended at PR 8 Step 2 per
    # A.5.3.2-PR8-SPEC.md §4.2 — the schema validator's
    # expectation branch now requires fixture_id, prompt, and
    # expected_narrow alongside the universal keys.
    expectation = {
        "schema_version": SCHEMA_VERSION,
        "capture_id": "expect-uuid-mixed",
        "captured_at": "2026-05-09T12:00:00.123Z",
        "record_kind": "expectation",
        "fixture_id": "fix-pr7-mixed",
        "prompt": "mixed-records reader probe",
        "expected_narrow": ["forge_list_staged"],
    }
    path = tmp_path / "test-mixed.jsonl"
    _write_jsonl(path, [_make_header(), legacy, observation, expectation])

    yielded = list(read_capture_file(path))

    assert len(yielded) == 3

    # 1. Legacy: both fields synthesized.
    assert yielded[0]["record_kind"] == "observation"
    assert yielded[0]["fixture_id"] is None

    # 2. Contemporary observation: explicit record_kind + explicit
    #    fixture_id (the builder's default-None for inactive scope).
    assert yielded[1]["record_kind"] == "observation"
    assert yielded[1]["fixture_id"] is None

    # 3. Contemporary expectation: explicit record_kind, fixture_id
    #    passed through verbatim (NOT synthesized to None by the
    #    reader). Mechanical guard against unconditional-synthesis
    #    regression — the reader must not blindly add or overwrite
    #    fixture_id on records that carry record_kind explicitly.
    #
    # PR 8 Step 2 update: the test's protected property is
    # preserved (no unconditional synthesis on contemporary
    # records). The PR 7-era assertion "fixture_id not in
    # yielded[2]" was anchored on the PR 7-era shape (expectation
    # records had no fixture_id); PR 8 extends the shape per
    # A.5.3.2-PR8-SPEC.md §4.2. The new assertion: the reader
    # passes the explicit fixture_id through unchanged.
    assert yielded[2]["record_kind"] == "expectation"
    assert yielded[2]["fixture_id"] == "fix-pr7-mixed"
    assert "source" not in yielded[2]
