"""PR 3 — round-trip writer/reader integrity tests.

Per ``A.5.3.2-PR3-SPEC.md`` §3 + §4: ``read(write(record)) ==
record`` is the strongest single verification that the writer's
serialization and the reader's parser agree on the on-disk format.
This is the load-bearing reason writer + reader ship together as a
single PR.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from forge_bridge.corpus import emit_divergence_capture, read_capture_file

from tests.corpus._pr3_helpers import base_writer_args


def _capture_path(corpus_dir: Path) -> Path:
    matches = list(corpus_dir.glob("capture-*.jsonl"))
    assert len(matches) == 1
    return matches[0]


# ── Single record ─────────────────────────────────────────────────────────


def test_round_trip_single_record(
    tmp_path, monkeypatch, clean_identity_caches,
):
    """Emit one record; read back; the yielded dict equals the
    serialized record on disk."""
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(tmp_path))

    emit_divergence_capture(**base_writer_args(prompt="round-trip-single"))
    path = _capture_path(tmp_path)

    yielded = list(read_capture_file(path))
    assert len(yielded) == 1

    # The record on disk parses identically to what the reader
    # yields (the reader's parsing is the canonical path).
    on_disk = json.loads(path.read_text(encoding="utf-8").splitlines()[1])
    assert yielded[0] == on_disk
    assert yielded[0]["prompt"] == "round-trip-single"


# ── Many records ──────────────────────────────────────────────────────────


def test_round_trip_many_records(
    tmp_path, monkeypatch, clean_identity_caches,
):
    """Emit N records; read back N records in the original order
    with content matching."""
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(tmp_path))

    n = 25
    for i in range(n):
        emit_divergence_capture(**base_writer_args(prompt=f"prompt-{i:03d}"))

    path = _capture_path(tmp_path)
    yielded = list(read_capture_file(path))

    assert len(yielded) == n
    assert [r["prompt"] for r in yielded] == [
        f"prompt-{i:03d}" for i in range(n)
    ]


# ── Daemon-restart simulation ─────────────────────────────────────────────


def test_round_trip_across_daemon_restart_simulation(
    tmp_path, monkeypatch, clean_identity_caches,
):
    """Emit some records, simulate a daemon restart by clearing
    process-local caches, emit more records to the same file. The
    reader sees all records in original order.

    The header is written once (on first emission). The simulated
    "restart" emission must not introduce a duplicate header,
    because the file already exists with content.
    """
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(tmp_path))

    for i in range(3):
        emit_divergence_capture(**base_writer_args(prompt=f"pre-restart-{i}"))

    # Simulate restart — clear identity caches (the daemon would
    # restart with a fresh process). The corpus file remains.
    from forge_bridge.corpus._identity import _reset_caches_for_tests
    _reset_caches_for_tests()

    for i in range(2):
        emit_divergence_capture(**base_writer_args(prompt=f"post-restart-{i}"))

    path = _capture_path(tmp_path)
    yielded = list(read_capture_file(path))

    # 5 records total, in original order. Header still 1.
    assert len(yielded) == 5
    assert [r["prompt"] for r in yielded] == [
        "pre-restart-0", "pre-restart-1", "pre-restart-2",
        "post-restart-0", "post-restart-1",
    ]

    raw_lines = path.read_text(encoding="utf-8").splitlines()
    header_count = sum(
        1 for l in raw_lines if json.loads(l).get("_header") is True
    )
    assert header_count == 1, (
        f"daemon-restart simulation produced {header_count} header "
        f"lines; expected exactly 1 (the writer must not duplicate "
        f"the header on subsequent emissions to an existing file)."
    )


# ── Unicode prompt ────────────────────────────────────────────────────────


def test_round_trip_with_unicode_prompt(
    tmp_path, monkeypatch, clean_identity_caches,
):
    """Non-ASCII content survives the writer's
    ``ensure_ascii=False`` choice (spec §12 decision 6).

    The grep-ability property — operators can ``grep -F 'プロジェクト'``
    against the on-disk file and find their prompt — depends on
    raw UTF-8 storage, not escaped ASCII (``\\uXXXX``).
    """
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(tmp_path))

    unicode_prompt = "list プロジェクト alpha — 漢字 — café"
    emit_divergence_capture(**base_writer_args(prompt=unicode_prompt))

    path = _capture_path(tmp_path)

    # Reader yields the prompt unchanged.
    yielded = list(read_capture_file(path))
    assert len(yielded) == 1
    assert yielded[0]["prompt"] == unicode_prompt

    # On-disk bytes contain the raw UTF-8 (grep-ability — verifies
    # ``ensure_ascii=False`` is respected).
    raw = path.read_text(encoding="utf-8")
    assert "プロジェクト" in raw
    assert "漢字" in raw
    assert "café" in raw
    # The escaped form must NOT appear.
    assert "\\u" not in raw, (
        "writer escaped non-ASCII content; ensure_ascii=False "
        "(spec §12 decision 6) is the correct setting for "
        "JSONL grep-ability."
    )
