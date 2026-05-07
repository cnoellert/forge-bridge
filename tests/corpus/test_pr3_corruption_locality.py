"""PR 3 — I-7 reader corruption-locality tests.

Per ``A.5.3.2-PR3-SPEC.md`` §9, verbatim from user framing
2026-05-07:

  Malformed or partial records should: fail locally, remain
  individually skippable, never invalidate the corpus globally. A
  corrupted line should not poison earlier records, later records,
  corpus loading, replay iteration. Otherwise persistence silently
  becomes fragility.

The canonical test pattern (§9.1):

  Three lines on disk:
    1. Valid record (passes schema validation).
    2. Malformed line (one of the modes below).
    3. Valid record (passes schema validation).

  The reader must produce, in order:
    1. Readable first record.
    2. Isolated failure or skip (logged WARNING; no yield).
    3. Readable third record.

Modes parametrized per §9.2:

  - truncated_json
  - invalid_utf8
  - schema_validation_failure
  - empty_whitespace_line  (→ silently skipped, no warning)
  - stray_header_mid_file
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from forge_bridge.corpus import (
    SCHEMA_VERSION,
    emit_divergence_capture,
    read_capture_file,
)

from tests.corpus._pr3_helpers import base_writer_args


_LOGGER = "forge_bridge.corpus.reader"


def _build_valid_records(
    tmp_path, monkeypatch, clean_identity_caches_fixture,
) -> tuple[Path, str, str, dict, dict]:
    """Emit two valid records via the real writer, return the
    on-disk file path + the header line + the two record lines.

    Used by tests below that hand-craft a malformed middle line and
    reconstruct a "valid + malformed + valid" file.
    """
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(tmp_path))
    emit_divergence_capture(**base_writer_args(prompt="record-one"))
    emit_divergence_capture(**base_writer_args(prompt="record-three"))

    path = next(tmp_path.glob("capture-*.jsonl"))
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3  # header + 2 records

    header_line = lines[0]
    record_one_line = lines[1]
    record_three_line = lines[2]
    record_one = json.loads(record_one_line)
    record_three = json.loads(record_three_line)
    return path, header_line, record_one_line, record_three_line, record_one, record_three


def _write_corrupted_file(
    path: Path,
    header_line: str,
    record_one_line: str,
    malformed_bytes: bytes,
    record_three_line: str,
) -> None:
    """Compose the canonical valid + malformed + valid file. Uses
    bytes mode so invalid-UTF-8 content can be tested directly."""
    payload = (
        header_line.encode("utf-8") + b"\n"
        + record_one_line.encode("utf-8") + b"\n"
        + malformed_bytes + b"\n"
        + record_three_line.encode("utf-8") + b"\n"
    )
    path.write_bytes(payload)


# ── Mode: truncated JSON ──────────────────────────────────────────────────


def test_reader_skips_truncated_json_record(
    tmp_path, monkeypatch, caplog, clean_identity_caches,
):
    path, header, r1, r3, _, _ = _build_valid_records(
        tmp_path, monkeypatch, clean_identity_caches,
    )

    truncated = b'{"schema_version":"1","capture_id":"abc",'  # mid-string
    _write_corrupted_file(path, header, r1, truncated, r3)

    with caplog.at_level(logging.WARNING, logger=_LOGGER):
        records = list(read_capture_file(path))

    assert len(records) == 2
    assert records[0]["prompt"] == "record-one"
    assert records[1]["prompt"] == "record-three"

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "JSON" in warnings[0].getMessage()


# ── Mode: invalid UTF-8 ───────────────────────────────────────────────────


def test_reader_skips_invalid_utf8_record(
    tmp_path, monkeypatch, caplog, clean_identity_caches,
):
    path, header, r1, r3, _, _ = _build_valid_records(
        tmp_path, monkeypatch, clean_identity_caches,
    )

    bad_utf8 = b"\xc3\x28 not a valid UTF-8 sequence"
    _write_corrupted_file(path, header, r1, bad_utf8, r3)

    with caplog.at_level(logging.WARNING, logger=_LOGGER):
        records = list(read_capture_file(path))

    assert len(records) == 2
    assert records[0]["prompt"] == "record-one"
    assert records[1]["prompt"] == "record-three"

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "UTF-8" in warnings[0].getMessage()


# ── Mode: schema-validation failure ───────────────────────────────────────


def test_reader_skips_schema_invalid_record(
    tmp_path, monkeypatch, caplog, clean_identity_caches,
):
    """Well-formed JSON dict that fails ``validate_capture_record``
    (e.g., missing required field)."""
    path, header, r1, r3, _, _ = _build_valid_records(
        tmp_path, monkeypatch, clean_identity_caches,
    )

    incomplete = json.dumps({
        "schema_version": SCHEMA_VERSION,
        # Missing every other required key.
        "source": "fixture",
    }).encode("utf-8")
    _write_corrupted_file(path, header, r1, incomplete, r3)

    with caplog.at_level(logging.WARNING, logger=_LOGGER):
        records = list(read_capture_file(path))

    assert len(records) == 2
    assert records[0]["prompt"] == "record-one"
    assert records[1]["prompt"] == "record-three"

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "schema" in warnings[0].getMessage().lower()


# ── Mode: empty / whitespace-only line ────────────────────────────────────


def test_reader_skips_empty_line_silently(
    tmp_path, monkeypatch, caplog, clean_identity_caches,
):
    """Empty/whitespace lines are skipped without warning (per
    §9.2: empty lines are normal in pasted/edited JSONL files)."""
    path, header, r1, r3, _, _ = _build_valid_records(
        tmp_path, monkeypatch, clean_identity_caches,
    )

    _write_corrupted_file(path, header, r1, b"   ", r3)

    with caplog.at_level(logging.WARNING, logger=_LOGGER):
        records = list(read_capture_file(path))

    assert len(records) == 2
    assert records[0]["prompt"] == "record-one"
    assert records[1]["prompt"] == "record-three"

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert warnings == [], (
        "empty/whitespace lines must be skipped silently — they are "
        "normal in pasted/edited JSONL files (spec §9.2)."
    )


# ── Mode: stray header mid-file ───────────────────────────────────────────


def test_reader_skips_stray_header_mid_file(
    tmp_path, monkeypatch, caplog, clean_identity_caches,
):
    """A ``{"_header": true, ...}`` line appearing on a non-first
    line is treated as malformed — the schema validator rejects
    records with ``_header`` set."""
    path, header, r1, r3, _, _ = _build_valid_records(
        tmp_path, monkeypatch, clean_identity_caches,
    )

    stray_header = json.dumps({
        "_header": True,
        "schema_version": SCHEMA_VERSION,
        "created_at": "2026-05-07T00:00:00.000Z",
        "format": "forge-bridge-divergence-corpus-v1",
    }).encode("utf-8")
    _write_corrupted_file(path, header, r1, stray_header, r3)

    with caplog.at_level(logging.WARNING, logger=_LOGGER):
        records = list(read_capture_file(path))

    assert len(records) == 2
    assert records[0]["prompt"] == "record-one"
    assert records[1]["prompt"] == "record-three"

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1


# ── Cross-cutting: iteration never aborts ─────────────────────────────────


def test_reader_iteration_never_raises_on_malformed_line(
    tmp_path, monkeypatch, clean_identity_caches,
):
    """Independent of the malformation mode, iterating
    ``read_capture_file`` to exhaustion never raises. The whole
    point of corruption locality."""
    path, header, r1, r3, _, _ = _build_valid_records(
        tmp_path, monkeypatch, clean_identity_caches,
    )

    # Pile every malformation into a single file to maximize chaos.
    payload = (
        header.encode("utf-8") + b"\n"
        + r1.encode("utf-8") + b"\n"
        + b'{"truncated json,\n'
        + b"\xc3\x28 invalid utf8\n"
        + b"\n"   # blank
        + b'{"missing_keys": true}\n'
        + r3.encode("utf-8") + b"\n"
    )
    path.write_bytes(payload)

    # Must not raise.
    records = list(read_capture_file(path))

    # The two valid records are recovered; everything else is
    # localized to its own line and skipped.
    assert len(records) == 2
    assert {r["prompt"] for r in records} == {"record-one", "record-three"}
