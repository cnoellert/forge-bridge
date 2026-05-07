"""PR 3 — ``emit_divergence_capture`` writer behavior tests.

Coverage per ``A.5.3.2-PR3-SPEC.md`` §11.1:

  Standard writer behavior (I-1, I-2, I-3, I-5, signature contract):
    - test_writer_uses_append_mode_only
    - test_writer_no_mutation_api
    - test_writer_emit_appends_each_call
    - test_writer_writes_header_on_first_emission
    - test_writer_skips_header_on_subsequent_emissions
    - test_writer_creates_corpus_directory_if_missing
    - test_writer_honors_corpus_dir_env_var
    - test_writer_no_lazy_side_effects
    - test_writer_emits_no_evaluative_fields
    - test_writer_emits_no_semantic_fields
    - test_writer_returns_none_on_success
    - test_writer_logs_no_warning_on_success
    - test_writer_log_message_redacts_full_prompt

  Atomic-append discipline tests (§6.5):
    - test_writer_single_write_call_per_record
    - test_writer_bundles_header_with_first_record
    - test_writer_no_seek_or_truncate_or_continuation
    - test_writer_record_lost_on_write_failure
"""
from __future__ import annotations

import asyncio
import inspect
import json
import logging
import socket
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from forge_bridge.corpus import emit_divergence_capture
from forge_bridge.corpus import _capture as capture_module
from forge_bridge.corpus._schema import SCHEMA_VERSION

from tests.corpus._pr3_helpers import base_writer_args


# ── Helpers ────────────────────────────────────────────────────────────────


def _today_capture_path(corpus_dir: Path) -> Path:
    """Locate the capture-YYYY-MM-DD.jsonl file in ``corpus_dir``.
    Returns the unique match; fails if zero or more than one file
    exists. Used by tests that emit one or more records and then
    assert on the resulting file.
    """
    matches = list(corpus_dir.glob("capture-*.jsonl"))
    assert len(matches) == 1, (
        f"expected exactly one capture file in {corpus_dir}, "
        f"found {len(matches)}: {matches}"
    )
    return matches[0]


def _read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


# ── I-5: append-only executable ────────────────────────────────────────────


def test_writer_uses_append_mode_only():
    """Source-grep: the writer module never opens files with a
    non-append mode. ``r+``, ``w``, ``w+``, ``a+`` (read-back),
    ``rb+``, ``wb`` all forbidden."""
    src = Path(capture_module.__file__).read_text(encoding="utf-8")
    forbidden_modes = (
        '"r+"', "'r+'",
        '"w"', "'w'",
        '"w+"', "'w+'",
        '"a+"', "'a+'",
        '"wb"', "'wb'",
        '"rb+"', "'rb+'",
        '"wb+"', "'wb+'",
    )
    for needle in forbidden_modes:
        assert needle not in src, (
            f"writer source contains forbidden file mode {needle!r}; "
            f"only append modes are permitted (I-5)"
        )


def test_writer_no_mutation_api():
    """Introspection: the writer module exposes no public function
    whose name suggests mutation/rewrite/update behavior."""
    forbidden_substrings = (
        "update_capture", "mutate_capture", "rewrite_corpus",
        "merge_captures", "overwrite_capture", "replace_capture",
    )
    public_names = [n for n in dir(capture_module) if not n.startswith("_")]
    for forbidden in forbidden_substrings:
        for name in public_names:
            assert forbidden not in name, (
                f"writer module exposes forbidden mutation-API "
                f"name: {name!r} contains {forbidden!r}"
            )


def test_writer_emit_appends_each_call(tmp_path, monkeypatch, clean_identity_caches):
    """Emit N records to a fresh file, then M more. Read back; assert
    N+M records present in the original emit order. Nothing was
    overwritten; nothing was deduplicated."""
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(tmp_path))

    n, m = 3, 4
    for i in range(n):
        emit_divergence_capture(**base_writer_args(prompt=f"first-{i}"))
    for j in range(m):
        emit_divergence_capture(**base_writer_args(prompt=f"second-{j}"))

    path = _today_capture_path(tmp_path)
    lines = _read_lines(path)
    # 1 header + (n + m) records
    assert len(lines) == 1 + n + m

    records = [json.loads(l) for l in lines[1:]]
    prompts = [r["prompt"] for r in records]
    expected = (
        [f"first-{i}" for i in range(n)]
        + [f"second-{j}" for j in range(m)]
    )
    assert prompts == expected


# ── §6.4: header-write decision ────────────────────────────────────────────


def test_writer_writes_header_on_first_emission(
    tmp_path, monkeypatch, clean_identity_caches,
):
    """First emission to a fresh corpus directory writes a header
    record as the first line."""
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(tmp_path))

    emit_divergence_capture(**base_writer_args())
    path = _today_capture_path(tmp_path)
    lines = _read_lines(path)

    assert len(lines) == 2  # header + record
    header = json.loads(lines[0])
    assert header["_header"] is True
    assert header["schema_version"] == SCHEMA_VERSION
    assert header["format"] == "forge-bridge-divergence-corpus-v1"


def test_writer_skips_header_on_subsequent_emissions(
    tmp_path, monkeypatch, clean_identity_caches,
):
    """Second emission to an existing file appends only the record
    line — no duplicate header."""
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(tmp_path))

    emit_divergence_capture(**base_writer_args(prompt="first"))
    emit_divergence_capture(**base_writer_args(prompt="second"))

    path = _today_capture_path(tmp_path)
    lines = _read_lines(path)

    # 1 header + 2 records
    assert len(lines) == 3
    header_count = sum(
        1 for l in lines if json.loads(l).get("_header") is True
    )
    assert header_count == 1


# ── §6.1: corpus directory resolution ──────────────────────────────────────


def test_writer_creates_corpus_directory_if_missing(
    tmp_path, monkeypatch, clean_identity_caches,
):
    """The corpus directory is auto-created with parents=True when
    missing."""
    nested = tmp_path / "nonexistent" / "deeper"
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(nested))

    assert not nested.exists()
    emit_divergence_capture(**base_writer_args())
    assert nested.exists()
    assert nested.is_dir()


def test_writer_honors_corpus_dir_env_var(
    tmp_path, monkeypatch, clean_identity_caches,
):
    """Records land under the env-var-specified directory, not the
    default ``~/.forge-bridge/corpus/``."""
    custom = tmp_path / "custom-corpus"
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(custom))

    emit_divergence_capture(**base_writer_args())
    assert any(custom.glob("capture-*.jsonl"))


# ── I-3: no lazy side effects ──────────────────────────────────────────────


def test_writer_no_lazy_side_effects(
    tmp_path, monkeypatch, clean_identity_caches,
):
    """The writer must not: open network sockets, spawn asyncio
    tasks, instantiate the LLM router, or mutate the
    ``_tool_filter._cache``."""
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(tmp_path))

    from forge_bridge.console._tool_filter import _cache as flame_cache
    cache_before = dict(flame_cache)

    with patch("socket.socket", wraps=socket.socket) as patched_socket:
        with patch.object(asyncio, "create_task") as patched_create_task:
            emit_divergence_capture(**base_writer_args())

    assert patched_socket.call_count == 0
    assert patched_create_task.call_count == 0
    # No mutation of the flame reachability cache.
    assert dict(flame_cache) == cache_before


# ── I-1, I-2: descriptive-not-evaluative, observational-not-semantic ──────


_EVALUATIVE_DENYLIST = (
    "healthy", "preferred", "recommended", "fallback_worthy", "good", "bad",
)
_SEMANTIC_DENYLIST = (
    "compatibility_grade", "equivalence_class", "drift_score",
    "is_correct", "harm_assessment", "divergence_classification",
)


def _walk_keys(obj: Any) -> list[str]:
    """Recursively collect all dict keys in a nested structure."""
    keys: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            keys.append(str(k))
            keys.extend(_walk_keys(v))
    elif isinstance(obj, list):
        for item in obj:
            keys.extend(_walk_keys(item))
    return keys


def test_writer_emits_no_evaluative_fields(
    tmp_path, monkeypatch, clean_identity_caches,
):
    """The emitted record contains no key drawn from the
    evaluative-field denylist (I-1)."""
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(tmp_path))

    emit_divergence_capture(**base_writer_args())
    path = _today_capture_path(tmp_path)
    record = json.loads(_read_lines(path)[1])

    keys = _walk_keys(record)
    for forbidden in _EVALUATIVE_DENYLIST:
        for k in keys:
            assert forbidden not in k.lower(), (
                f"emitted record contains evaluative field name: "
                f"{k!r} matches denylist entry {forbidden!r} (I-1)"
            )


def test_writer_emits_no_semantic_fields(
    tmp_path, monkeypatch, clean_identity_caches,
):
    """The emitted record contains no key drawn from the
    semantic-field denylist (I-2 — Layer 2 territory)."""
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(tmp_path))

    emit_divergence_capture(**base_writer_args())
    path = _today_capture_path(tmp_path)
    record = json.loads(_read_lines(path)[1])

    keys = _walk_keys(record)
    for forbidden in _SEMANTIC_DENYLIST:
        for k in keys:
            assert forbidden not in k.lower(), (
                f"emitted record contains semantic field name: "
                f"{k!r} matches denylist entry {forbidden!r} (I-2)"
            )


# ── Signature contract ────────────────────────────────────────────────────


def test_writer_returns_none_on_success(
    tmp_path, monkeypatch, clean_identity_caches,
):
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(tmp_path))
    result = emit_divergence_capture(**base_writer_args())
    assert result is None


def test_writer_logs_no_warning_on_success(
    tmp_path, monkeypatch, caplog, clean_identity_caches,
):
    """Success path emits no WARNING (no log spam)."""
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(tmp_path))

    with caplog.at_level(logging.WARNING, logger="forge_bridge.corpus._capture"):
        emit_divergence_capture(**base_writer_args())

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert warnings == []


def test_writer_log_message_redacts_full_prompt(
    tmp_path, monkeypatch, caplog, clean_identity_caches,
):
    """When the writer logs a WARNING (e.g., on failure), the log
    message must NOT contain the full prompt — only the first 32
    chars per contract §8.4 privacy posture."""
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(tmp_path))

    long_prompt = (
        "this is a very long secret prompt that absolutely should not "
        "appear verbatim in the operator's log file because it might "
        "contain proprietary information about the project"
    )
    sensitive_tail = "proprietary information about the project"

    # Force a write failure so the WARNING path runs.
    with patch.object(Path, "open", side_effect=PermissionError("denied")):
        with caplog.at_level(
            logging.WARNING, logger="forge_bridge.corpus._capture",
        ):
            emit_divergence_capture(**base_writer_args(prompt=long_prompt))

    log_text = "\n".join(r.getMessage() for r in caplog.records)
    assert sensitive_tail not in log_text, (
        "WARNING log contains the full prompt; privacy posture "
        "(contract §8.4) requires only the first 32 chars."
    )


# ── §6.5: atomic-append discipline ─────────────────────────────────────────


def _make_write_counting_open(real_open):
    """Return an ``open`` replacement that wraps the file's
    ``write`` method so we can count calls. Used by atomic-append
    tests to verify the single-syscall property.
    """
    write_calls: list[str] = []

    def fake_open(self, *args, **kwargs):
        f = real_open(self, *args, **kwargs)
        original_write = f.write

        def counting_write(payload):
            write_calls.append(payload)
            return original_write(payload)

        f.write = counting_write
        return f

    return fake_open, write_calls


def test_writer_single_write_call_per_record(
    tmp_path, monkeypatch, clean_identity_caches,
):
    """§6.5: each emission to an existing (header-present) file
    performs exactly ONE ``file.write(...)`` call. The serialized
    record + ``\\n`` are concatenated and written in a single
    syscall."""
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(tmp_path))

    # First emission creates the file + writes header. We don't
    # count this call; we only count the second emission's write.
    emit_divergence_capture(**base_writer_args(prompt="first"))

    real_open = Path.open
    fake_open, write_calls = _make_write_counting_open(real_open)

    with patch.object(Path, "open", fake_open):
        emit_divergence_capture(**base_writer_args(prompt="second"))

    assert len(write_calls) == 1, (
        f"§6.5 violation: expected exactly 1 file.write() call per "
        f"emission to an existing file, got {len(write_calls)}: "
        f"{write_calls!r}"
    )
    assert write_calls[0].endswith("\n")


def test_writer_bundles_header_with_first_record(
    tmp_path, monkeypatch, clean_identity_caches,
):
    """§6.5: emission to a fresh (header-absent) file performs
    exactly ONE ``file.write(...)`` call containing both the header
    JSON and the record JSON.

    Pins the carrier invariant: *"corpus existence implies at least
    one truthful persisted capture."* The header + first-record
    bundling rule eliminates the transient impossible state where
    the corpus exists but contains no records.
    """
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(tmp_path))

    real_open = Path.open
    fake_open, write_calls = _make_write_counting_open(real_open)

    with patch.object(Path, "open", fake_open):
        emit_divergence_capture(**base_writer_args(prompt="first-ever"))

    assert len(write_calls) == 1, (
        f"§6.5 violation: expected exactly 1 file.write() call on "
        f"first-ever emission (header + record bundled), got "
        f"{len(write_calls)}: {write_calls!r}"
    )

    payload = write_calls[0]
    # The single write contains both the header and the record.
    assert '"_header":true' in payload, (
        "first-emission write payload missing the header line"
    )
    assert '"first-ever"' in payload, (
        "first-emission write payload missing the record's prompt"
    )
    # Header and record are separated by exactly one newline.
    # Payload ends with newline (record terminator).
    assert payload.endswith("\n")
    # Payload contains exactly two newlines: end of header + end of record.
    assert payload.count("\n") == 2, (
        f"first-emission payload has {payload.count('\\n')} newlines; "
        f"expected exactly 2 (end of header + end of record): "
        f"{payload!r}"
    )


def test_writer_no_seek_or_truncate_or_continuation():
    """§6.5: the writer source contains no ``.seek(``, ``.truncate(``,
    or ``.tell(`` calls. The writer never repositions the file
    pointer, never truncates, never reads its own write position."""
    src = Path(capture_module.__file__).read_text(encoding="utf-8")
    forbidden = (".seek(", ".truncate(", ".tell(")
    for needle in forbidden:
        assert needle not in src, (
            f"§6.5 violation: writer source contains {needle!r}. "
            f"Atomic-append discipline forbids partial-record "
            f"recovery, in-place repair, continuation writes, or "
            f"seek-and-reconstruct."
        )


def test_writer_record_lost_on_write_failure(
    tmp_path, monkeypatch, clean_identity_caches,
):
    """§6.5: when ``file.write()`` raises mid-call, the writer makes
    no recovery attempt. The record is considered lost.

    Pairs with the I-6 partial-write failure-invisibility test in
    test_pr3_failure_invisibility.py — that one verifies arbitration
    is unaffected; this one verifies the writer makes no attempt to
    retry, repair, or continue.
    """
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(tmp_path))

    # Make the FIRST write call raise.
    real_open = Path.open
    write_attempt_count = {"n": 0}

    def fake_open(self, *args, **kwargs):
        f = real_open(self, *args, **kwargs)

        def failing_write(payload):
            write_attempt_count["n"] += 1
            raise OSError("simulated mid-write failure")

        f.write = failing_write
        return f

    with patch.object(Path, "open", fake_open):
        # Must not raise (I-6 failure invisibility).
        emit_divergence_capture(**base_writer_args())

    # Exactly one write attempt — no retry, no continuation.
    assert write_attempt_count["n"] == 1, (
        f"§6.5 violation: writer attempted {write_attempt_count['n']} "
        f"writes after failure; expected 1 (no retry, no recovery)."
    )

    # The file may or may not exist (depending on the OS); but no
    # further write attempts were made. The writer accepts the
    # record-lost outcome without retry.
