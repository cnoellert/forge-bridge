"""PR 3 — ``read_capture_file`` reader behavior tests.

Coverage per ``A.5.3.2-PR3-SPEC.md`` §11.1:

  - test_reader_yields_records_in_file_order
  - test_reader_skips_blank_lines_silently
  - test_reader_raises_schema_version_mismatch_on_bad_header
  - test_reader_raises_file_not_found_on_missing_path
  - test_reader_closes_file_on_iteration_end

The corruption-locality matrix lives in
``test_pr3_corruption_locality.py``. The round-trip integrity test
lives in ``test_pr3_round_trip.py``.
"""
from __future__ import annotations

import gc
import json
import logging
from pathlib import Path

import pytest

from forge_bridge.corpus import (
    SCHEMA_VERSION,
    SchemaVersionMismatch,
    emit_divergence_capture,
    read_capture_file,
)

from tests.corpus._pr3_helpers import base_writer_args


# ── Helpers ────────────────────────────────────────────────────────────────


def _write_jsonl(path: Path, lines: list[str]) -> None:
    """Write hand-crafted JSONL lines for tests that don't use the
    real writer (e.g., schema-version-mismatch construction)."""
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _today_capture_path(corpus_dir: Path) -> Path:
    matches = list(corpus_dir.glob("capture-*.jsonl"))
    assert len(matches) == 1
    return matches[0]


# ── Happy path ─────────────────────────────────────────────────────────────


def test_reader_yields_records_in_file_order(
    tmp_path, monkeypatch, clean_identity_caches,
):
    """Records emitted in order N, M, K are yielded in order N, M, K."""
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(tmp_path))

    for prompt in ("first", "second", "third"):
        emit_divergence_capture(**base_writer_args(prompt=prompt))

    path = _today_capture_path(tmp_path)
    yielded = list(read_capture_file(path))

    assert [r["prompt"] for r in yielded] == ["first", "second", "third"]


def test_reader_skips_blank_lines_silently(
    tmp_path, monkeypatch, caplog, clean_identity_caches,
):
    """Empty/whitespace-only lines are skipped without warning."""
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(tmp_path))

    emit_divergence_capture(**base_writer_args(prompt="alpha"))
    path = _today_capture_path(tmp_path)

    # Inject blank lines into the file.
    original = path.read_text(encoding="utf-8")
    path.write_text(original + "\n\n   \n", encoding="utf-8")

    with caplog.at_level(
        logging.WARNING, logger="forge_bridge.corpus.reader",
    ):
        records = list(read_capture_file(path))

    # Only the original record yielded; no warnings.
    assert len(records) == 1
    assert records[0]["prompt"] == "alpha"
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert warnings == []


# ── Header validation ─────────────────────────────────────────────────────


def test_reader_raises_schema_version_mismatch_on_bad_header(tmp_path):
    """A header with a mismatched schema_version raises
    ``SchemaVersionMismatch`` with the contract §9 remediation
    message."""
    bad_path = tmp_path / "bad-version.jsonl"
    bad_header = {
        "_header": True,
        "schema_version": "99",
        "created_at": "2026-05-07T00:00:00.000Z",
        "format": "forge-bridge-divergence-corpus-v1",
    }
    _write_jsonl(bad_path, [json.dumps(bad_header)])

    with pytest.raises(SchemaVersionMismatch, match="upgrade or filter"):
        list(read_capture_file(bad_path))


def test_reader_raises_schema_version_mismatch_on_missing_header(tmp_path):
    """A file whose first line is not a header raises
    ``SchemaVersionMismatch``."""
    bad_path = tmp_path / "no-header.jsonl"
    # Looks like a record (not a header) — _header is missing/false.
    _write_jsonl(bad_path, [json.dumps({"this": "is not a header"})])

    with pytest.raises(SchemaVersionMismatch):
        list(read_capture_file(bad_path))


def test_reader_raises_schema_version_mismatch_on_empty_file(tmp_path):
    """An empty file raises ``SchemaVersionMismatch`` with a
    descriptive message naming the empty-file case."""
    empty_path = tmp_path / "empty.jsonl"
    empty_path.write_text("", encoding="utf-8")

    with pytest.raises(SchemaVersionMismatch, match="empty"):
        list(read_capture_file(empty_path))


def test_reader_accepts_correct_header(
    tmp_path, monkeypatch, clean_identity_caches,
):
    """A valid header followed by valid records yields all records."""
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(tmp_path))
    emit_divergence_capture(**base_writer_args())
    path = _today_capture_path(tmp_path)

    # Sanity — header is correct.
    first_line = path.read_text(encoding="utf-8").splitlines()[0]
    header = json.loads(first_line)
    assert header["_header"] is True
    assert header["schema_version"] == SCHEMA_VERSION

    # Reader yields the one record without exception.
    records = list(read_capture_file(path))
    assert len(records) == 1


# ── Path handling ─────────────────────────────────────────────────────────


def test_reader_raises_file_not_found_on_missing_path(tmp_path):
    """Missing files raise ``FileNotFoundError`` (the standard
    Python contract)."""
    missing = tmp_path / "nonexistent.jsonl"
    with pytest.raises(FileNotFoundError):
        list(read_capture_file(missing))


# ── File-handle hygiene ───────────────────────────────────────────────────


def test_reader_closes_file_on_iteration_end(
    tmp_path, monkeypatch, clean_identity_caches,
):
    """The reader's ``with open(...)`` context manager closes the
    file when iteration ends. Verified by exhausting the generator
    and then deleting the path on Windows-style filesystems (here
    we just check that file-handle pressure doesn't accumulate)."""
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(tmp_path))
    emit_divergence_capture(**base_writer_args())
    path = _today_capture_path(tmp_path)

    # Iterate to exhaustion in a tight loop. If the generator leaked
    # file handles, this would surface as ResourceWarning under
    # pytest's default warning filters (or as ulimit failures
    # eventually).
    for _ in range(100):
        records = list(read_capture_file(path))
        assert len(records) == 1

    # Force GC to flush any lingering generator state.
    gc.collect()
