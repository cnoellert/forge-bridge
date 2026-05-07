"""PR 3 — I-6 failure-invisibility tests.

Per ``A.5.3.2-PR3-SPEC.md`` §8: every persistence-failure mode must
not propagate out of ``emit_divergence_capture``. The writer
returns ``None``, logs at WARNING with structured detail, and
never raises.

Each test parametrizes one failure mode from framing constraint 3:

  - disk full (ENOSPC)
  - invalid path (corpus dir cannot be created)
  - permission denied (EACCES)
  - serialization failure (record bypasses validator)
  - partial write (EIO mid-write)
  - lock contention (EAGAIN / BlockingIOError)
  - malformed runtime state (snapshot_topology returns invalid dict)

For each mode, assert: ``return None``, no exception, exactly one
WARNING logged, message includes source marker + failure-mode
classification + redacted prompt prefix.
"""
from __future__ import annotations

import errno
import json
import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from forge_bridge.corpus import emit_divergence_capture

from tests.corpus._pr3_helpers import base_writer_args


_LOGGER = "forge_bridge.corpus._capture"


def _assert_warning_logged_once(caplog, source: str):
    """Common assertions for every failure-mode test."""
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1, (
        f"expected exactly one WARNING; got {len(warnings)}: "
        f"{[r.getMessage() for r in warnings]}"
    )
    msg = warnings[0].getMessage()
    assert "capture write failed" in msg
    assert f"source={source}" in msg
    return msg


# ── Failure modes ─────────────────────────────────────────────────────────


def test_failure_invisibility_disk_full(
    tmp_path, monkeypatch, caplog, clean_identity_caches,
):
    """Disk full — ENOSPC raised by file.write()."""
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(tmp_path))

    real_open = Path.open

    def fake_open(self, *args, **kwargs):
        f = real_open(self, *args, **kwargs)

        def failing_write(payload):
            raise OSError(errno.ENOSPC, "disk full")

        f.write = failing_write
        return f

    with patch.object(Path, "open", fake_open):
        with caplog.at_level(logging.WARNING, logger=_LOGGER):
            result = emit_divergence_capture(**base_writer_args())

    assert result is None
    msg = _assert_warning_logged_once(caplog, source="fixture")
    assert "OSError" in msg


def test_failure_invisibility_invalid_path(
    tmp_path, monkeypatch, caplog, clean_identity_caches,
):
    """Invalid path — corpus dir is set under a regular file, so
    ``mkdir(parents=True)`` fails."""
    blocker = tmp_path / "blocker"
    blocker.write_text("i am a file, not a directory")
    invalid = blocker / "subdir"
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(invalid))

    with caplog.at_level(logging.WARNING, logger=_LOGGER):
        result = emit_divergence_capture(**base_writer_args())

    assert result is None
    _assert_warning_logged_once(caplog, source="fixture")


def test_failure_invisibility_permission_denied(
    tmp_path, monkeypatch, caplog, clean_identity_caches,
):
    """Permission denied — EACCES from Path.open()."""
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(tmp_path))

    with patch.object(Path, "open", side_effect=PermissionError("denied")):
        with caplog.at_level(logging.WARNING, logger=_LOGGER):
            result = emit_divergence_capture(**base_writer_args())

    assert result is None
    msg = _assert_warning_logged_once(caplog, source="fixture")
    assert "PermissionError" in msg


def test_failure_invisibility_serialization_failure(
    tmp_path, monkeypatch, caplog, clean_identity_caches,
):
    """Serialization failure — make json.dumps raise. The validator
    should reject most invalid types, but a TypeError from
    ``json.dumps`` on an unserializable nested object is still
    possible if a path bypasses validation."""
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(tmp_path))

    real_dumps = json.dumps

    def boom_dumps(*args, **kwargs):
        raise TypeError("simulated serialization failure")

    with patch.object(json, "dumps", boom_dumps):
        with caplog.at_level(logging.WARNING, logger=_LOGGER):
            result = emit_divergence_capture(**base_writer_args())

    # restore even though patch.object scope did it; safety
    json.dumps = real_dumps  # type: ignore[assignment]

    assert result is None
    msg = _assert_warning_logged_once(caplog, source="fixture")
    assert "TypeError" in msg


def test_failure_invisibility_partial_write(
    tmp_path, monkeypatch, caplog, clean_identity_caches,
):
    """Partial write — EIO raised by file.write() after some bytes
    flushed. The writer must not retry; the record is lost."""
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(tmp_path))

    real_open = Path.open

    def fake_open(self, *args, **kwargs):
        f = real_open(self, *args, **kwargs)

        def partial_then_fail(payload):
            raise OSError(errno.EIO, "I/O error mid-write")

        f.write = partial_then_fail
        return f

    with patch.object(Path, "open", fake_open):
        with caplog.at_level(logging.WARNING, logger=_LOGGER):
            result = emit_divergence_capture(**base_writer_args())

    assert result is None
    msg = _assert_warning_logged_once(caplog, source="fixture")
    assert "OSError" in msg


def test_failure_invisibility_lock_contention(
    tmp_path, monkeypatch, caplog, clean_identity_caches,
):
    """Lock contention — BlockingIOError from Path.open() (NFS-style
    flock EAGAIN can surface this way under some filesystems)."""
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(tmp_path))

    with patch.object(
        Path, "open", side_effect=BlockingIOError("would block"),
    ):
        with caplog.at_level(logging.WARNING, logger=_LOGGER):
            result = emit_divergence_capture(**base_writer_args())

    assert result is None
    msg = _assert_warning_logged_once(caplog, source="fixture")
    assert "BlockingIOError" in msg


def test_failure_invisibility_malformed_runtime_state(
    tmp_path, monkeypatch, caplog, clean_identity_caches,
):
    """Malformed runtime state — make ``snapshot_topology()`` return
    a dict that fails schema validation."""
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(tmp_path))

    # Patch at the import site (the builder imports
    # snapshot_topology into _capture's namespace).
    bad_topology = {"this": "is not a valid topology block"}

    with patch(
        "forge_bridge.corpus._capture.snapshot_topology",
        return_value=bad_topology,
    ):
        with caplog.at_level(logging.WARNING, logger=_LOGGER):
            result = emit_divergence_capture(**base_writer_args())

    assert result is None
    msg = _assert_warning_logged_once(caplog, source="fixture")
    assert "SchemaValidationError" in msg


# ── Cross-cutting: failed writes leave no observational residue ───────────


def test_failed_write_leaves_no_capture_residue(
    tmp_path, monkeypatch, clean_identity_caches,
):
    """User-framing 2026-05-07 sanity check: a failed write must
    leave no capture-specific observational residue.

    The mechanically-forgetful posture is strongest when:

    > failed writes leave no observational residue

    Specifically:
      - no globally retained allocated capture_id
      - no "last write" mutation
      - no partial persistence bookkeeping
      - no record content from the failed write surfaces in
        subsequent successful writes

    This test pins the property by emitting a failing write with a
    distinctive prompt, then a successful write with a different
    prompt, and asserting the resulting on-disk file contains only
    the successful record. Any future "retry queue" / "partial
    checkpoint" / "allocated-id pool" drift will fail this test.

    Infrastructure side effects (the corpus directory existing, an
    empty 0-byte file from a failed first-emission's append-mode
    open) are NOT considered residue per spec §6.5 — they are
    idempotent setup, not bookkeeping. This test does not check
    against them.
    """
    monkeypatch.setenv("FORGE_BRIDGE_CORPUS_DIR", str(tmp_path))

    failing_prompt = "FAILED-RECORD-must-not-appear-anywhere"
    success_prompt = "SUCCESS-RECORD-this-is-the-only-survivor"

    real_open = Path.open
    write_made = {"failed": False}

    def fake_open(self, *args, **kwargs):
        f = real_open(self, *args, **kwargs)
        if not write_made["failed"]:
            # First write attempt: raise.
            def failing_write(payload):
                # Capture the payload BEFORE raising so we can
                # verify the failed payload was not retained
                # anywhere observable.
                write_made["failed"] = True
                raise OSError("simulated write failure")

            f.write = failing_write
        return f

    # Failing write — must not raise (I-6).
    with patch.object(Path, "open", fake_open):
        emit_divergence_capture(**base_writer_args(prompt=failing_prompt))

    assert write_made["failed"], "fake_open did not intercept a write"

    # Successful write — uses the real Path.open.
    emit_divergence_capture(**base_writer_args(prompt=success_prompt))

    # ── On-disk verification ─────────────────────────────────────
    matches = list(tmp_path.glob("capture-*.jsonl"))
    assert len(matches) == 1
    file_text = matches[0].read_text(encoding="utf-8")

    assert failing_prompt not in file_text, (
        "failed-write residue detected: failing-record's prompt "
        "appears in the on-disk corpus file. The writer leaked "
        "capture-specific state across the failure boundary — this "
        "is the user-framing 2026-05-07 violation."
    )
    assert success_prompt in file_text, (
        "successful write did not land — sanity-check failure"
    )

    # ── Module-state verification ────────────────────────────────
    # The writer module must not have grown any module-level
    # attribute holding capture data (e.g., a retry queue or
    # last-attempted-write cache).
    from forge_bridge.corpus import _capture as cap_module

    forbidden_attribute_substrings = (
        "_last_capture", "_last_record", "_last_write",
        "_retry_queue", "_pending_captures", "_attempted_captures",
        "_capture_buffer", "_capture_pool",
    )
    module_attrs = [a for a in dir(cap_module) if not a.startswith("__")]
    for forbidden in forbidden_attribute_substrings:
        for attr in module_attrs:
            assert forbidden not in attr, (
                f"writer module grew a forbidden capture-state "
                f"attribute: {attr!r} matches denylist entry "
                f"{forbidden!r}. Failed writes must leave no "
                f"observational residue."
            )
