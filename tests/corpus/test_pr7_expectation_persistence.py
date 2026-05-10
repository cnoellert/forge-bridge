"""tests.corpus.test_pr7_expectation_persistence — PR 7 Step 8 tests.

Tests the ``_persist_expectation_record`` private helper introduced
in ``forge_bridge/corpus/_capture.py`` at PR 7 Step 8. The helper is
the third member of the expectation-persistence authority surface
(per Gate 2 framing §3.4); PR 7 ships the seam, PR 8 invokes it from
``emit_seed_expectation``.

Three of these five tests are authority-boundary load-bearing:

- ``test_helper_does_not_consult_dispatch_context`` — mechanical
  enforcement of the non-participation guard (risk #5 in spec §3).
  Without this test, a future PR could add a dispatch-context
  consultation here without regressing any test, eroding the three-
  authority-surface partitioning.
- ``test_helper_authority_pre_check_rejects_missing_record_kind`` —
  enforces the authority pre-check at the missing-field boundary.
- ``test_helper_authority_pre_check_rejects_observation_record`` —
  enforces the authority pre-check against a record the schema
  validator alone would accept. Without this test, a future PR
  could remove the pre-check without regressing any test.

The remaining two tests cover the writer-path mechanics:

- ``test_helper_persists_expectation_record`` — round-trip.
- ``test_helper_atomic_append`` — bundled-header-on-first-write
  discipline applies identically to expectation persistence.

See ``A.5.3.2-PR7-SPEC.md`` §4.2.6 (helper body), §5.1 (test
inventory), §6 step 8 (implementation step body).
"""
from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any, Optional

from forge_bridge.corpus._capture import (
    _build_capture_record,
    _persist_expectation_record,
    seed_dispatch_scope,
)
from forge_bridge.corpus._schema import SCHEMA_VERSION, validate_capture_record

from tests.corpus._pr3_helpers import base_builder_args


_LOGGER = "forge_bridge.corpus._capture"


# ── Helpers ────────────────────────────────────────────────────────────────


def _make_expectation_record(
    *,
    captured_at: str = "2026-05-10T12:00:00.000Z",
    capture_id: Optional[str] = None,
) -> dict[str, Any]:
    """Build a minimal valid expectation record.

    Per ``_schema.py`` post-PR-7-Step-5: the only structural
    requirements for an expectation record are the universal top
    keys (``schema_version``, ``capture_id``, ``captured_at``,
    ``record_kind``) plus the prohibition on a ``source`` field.
    PR 8's seed driver will define the operational expectation
    shape; PR 7 ships the seam only.

    ``captured_at`` defaults to a fixed value so byte-identical
    persistence assertions (test 2) are deterministic. Tests that
    want distinct date partitions or sequence determinism override
    the field explicitly.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "capture_id": capture_id or str(uuid.uuid4()),
        "captured_at": captured_at,
        "record_kind": "expectation",
    }


def _today_capture_path(corpus_dir: Path) -> Path:
    """Return the unique ``capture-YYYY-MM-DD.jsonl`` file in
    ``corpus_dir``. Fails if zero or more than one match. Mirrors
    the helper in ``test_pr7_dispatch_context.py``."""
    matches = list(corpus_dir.glob("capture-*.jsonl"))
    assert len(matches) == 1, (
        f"expected exactly one capture file in {corpus_dir}, "
        f"found {len(matches)}: {matches}"
    )
    return matches[0]


def _read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


# ── Test 1 — round-trip ────────────────────────────────────────────────────


def test_helper_persists_expectation_record(tmp_path, monkeypatch) -> None:
    """Step 8. The helper persists an expectation record that
    round-trips with ``record_kind="expectation"`` and no
    ``source`` field.

    Validates the basic happy path: a valid expectation record
    passed through the authority pre-check + schema validator
    lands on disk with the bundled header on first write, and the
    JSONL line deserializes back to the same record.
    """
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(tmp_path))

    record = _make_expectation_record(
        capture_id="exp-roundtrip",
        captured_at="2026-05-10T12:00:00.000Z",
    )

    _persist_expectation_record(record)

    path = _today_capture_path(tmp_path)
    lines = _read_lines(path)
    # 1 header + 1 record.
    assert len(lines) == 2

    persisted = json.loads(lines[1])
    assert persisted["record_kind"] == "expectation"
    assert "source" not in persisted
    assert persisted["capture_id"] == "exp-roundtrip"
    assert persisted["captured_at"] == "2026-05-10T12:00:00.000Z"


# ── Test 2 — non-participation guard (load-bearing, risk #5) ──────────────


def test_helper_does_not_consult_dispatch_context(monkeypatch, tmp_path) -> None:
    """Step 8. The helper is byte-identical inside vs. outside
    ``seed_dispatch_scope``.

    Mechanical enforcement of the non-participation guard
    (verbatim in the helper's docstring): "The narrow expectation
    persistence helper does not participate in provenance
    resolution. It consults no dispatch context, performs no
    source rewriting, and carries no observational semantics."

    Two emissions of the same input record, one outside any scope
    and one inside ``seed_dispatch_scope(fixture_id="...")``. The
    on-disk bytes must match exactly. If they diverge, the helper
    has begun participating in dispatch resolution — risk #5 from
    spec §3.

    The test uses two distinct corpus directories (one per
    emission) so the byte-comparison is on the helper's full
    output, not on append-vs-create discipline. Both files should
    contain the same header line + same record line.
    """
    record = _make_expectation_record(
        capture_id="exp-nonparticipation",
        captured_at="2026-05-10T12:00:00.000Z",
    )

    # Emission 1: outside any scope.
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(outside_dir))
    _persist_expectation_record(record)
    bytes_outside = _today_capture_path(outside_dir).read_bytes()

    # Emission 2: inside a seed dispatch scope.
    inside_dir = tmp_path / "inside"
    inside_dir.mkdir()
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(inside_dir))
    with seed_dispatch_scope(fixture_id="fix-nonparticipation"):
        _persist_expectation_record(record)
    bytes_inside = _today_capture_path(inside_dir).read_bytes()

    assert bytes_outside == bytes_inside, (
        "expectation persistence diverged between outside-scope and "
        "inside-scope emission — the non-participation guard has "
        "been violated. The helper has begun consulting dispatch "
        "context (risk #5)."
    )


# ── Test 3 — authority pre-check at missing-field boundary ────────────────


def test_helper_authority_pre_check_rejects_missing_record_kind(
    tmp_path, monkeypatch, caplog,
) -> None:
    """Step 8. A record dict missing ``record_kind`` is rejected
    by the authority pre-check.

    The pre-check fires BEFORE ``validate_capture_record`` (which
    would reject the same record on missing-required-key grounds).
    The test asserts the authority-oriented WARNING text appears
    in the log — proof the pre-check is the rejection site, not
    the schema validator.

    Failure-invisibility per I-6: the helper returns ``None``;
    nothing escapes. No record lands on disk.
    """
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(tmp_path))

    record_missing_kind = {
        "schema_version": SCHEMA_VERSION,
        "capture_id": "exp-missing-kind",
        "captured_at": "2026-05-10T12:00:00.000Z",
        # record_kind deliberately absent.
    }

    with caplog.at_level(logging.WARNING, logger=_LOGGER):
        result = _persist_expectation_record(record_missing_kind)

    assert result is None

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    message = warnings[0].getMessage()
    assert (
        "_persist_expectation_record persists authored "
        "expectation records only; received record_kind=None"
    ) in message, message

    # No record landed on disk: no capture file created.
    assert list(tmp_path.glob("capture-*.jsonl")) == []


# ── Test 4 — authority pre-check at well-formed-observation boundary ──────


def test_helper_authority_pre_check_rejects_observation_record(
    tmp_path, monkeypatch, caplog, clean_identity_caches,
) -> None:
    """Step 8. A well-formed observation record (one that would
    pass ``validate_capture_record`` directly) is rejected by the
    authority pre-check.

    This is the authority-class boundary's mechanical enforcement.
    The record is structurally valid — the schema validator alone
    would accept it. The pre-check rejects it because the helper's
    truth class is ``"expectation"``, not ``"observation"``.

    Without this test, a future PR could remove the pre-check and
    rely on the schema validator alone; the test fixture's
    record_kind is observation but otherwise complete, so schema
    validation would pass and the helper would persist it. The
    test fires when that authority-class collapse occurs.
    """
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(tmp_path))

    # Build a fully-valid observation record via the canonical builder.
    observation_record = _build_capture_record(
        **base_builder_args(prompt="exp-test-observation")
    )
    # Sanity check: this record is structurally valid against the
    # schema. The pre-check, not the validator, is what rejects it.
    validate_capture_record(observation_record)
    assert observation_record["record_kind"] == "observation"

    with caplog.at_level(logging.WARNING, logger=_LOGGER):
        result = _persist_expectation_record(observation_record)

    assert result is None

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    message = warnings[0].getMessage()
    assert (
        "_persist_expectation_record persists authored "
        "expectation records only; received record_kind='observation'"
    ) in message, message

    # No record landed on disk.
    assert list(tmp_path.glob("capture-*.jsonl")) == []


# ── Test 5 — atomic-append discipline ─────────────────────────────────────


def test_helper_atomic_append(tmp_path, monkeypatch) -> None:
    """Step 8. Three sequential emissions land in one file as
    one header line + three record lines.

    Validates the bundled-header-on-first-write discipline (spec
    §6.5) applies identically to expectation persistence. No
    orphan headers; no duplicate headers; no partial-record
    recovery.
    """
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(tmp_path))

    captured_at = "2026-05-10T12:00:00.000Z"
    records = [
        _make_expectation_record(
            capture_id=f"exp-atomic-{i}",
            captured_at=captured_at,
        )
        for i in range(3)
    ]

    for record in records:
        _persist_expectation_record(record)

    path = _today_capture_path(tmp_path)
    lines = _read_lines(path)

    # Exactly 1 header + 3 records.
    assert len(lines) == 4

    header = json.loads(lines[0])
    assert header.get("_header") is True

    persisted = [json.loads(line) for line in lines[1:]]
    assert all(r["record_kind"] == "expectation" for r in persisted)
    assert [r["capture_id"] for r in persisted] == [
        "exp-atomic-0",
        "exp-atomic-1",
        "exp-atomic-2",
    ]
