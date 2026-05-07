"""forge_bridge.corpus.reader — Layer 1 record reader.

Opens a Layer 1 capture file (per ``A.5.3.2-GATE-1-SPEC.md`` §3.5),
validates the header record's ``schema_version``, and yields each
subsequent record as a parsed dict. Schema-version mismatch raises
``SchemaVersionMismatch`` per ``A.5.3.2-INSTRUMENT-CONTRACT.md`` §9.

PR 3 carrier sentence (verbatim, load-bearing — see
``A.5.3.2-PR3-SPEC.md`` §9, user framing 2026-05-07):

  Malformed or partial records should: fail locally, remain
  individually skippable, never invalidate the corpus globally. A
  corrupted line should not poison earlier records, later records,
  corpus loading, replay iteration. Otherwise persistence silently
  becomes fragility.

This is the corruption-locality contract. It complements the
writer-side atomic-append discipline (``_capture.py`` §6.5): the
writer minimizes corruption opportunity, the reader localizes
unavoidable corruption.

Implementation (per spec §5.3 + §9):

  - Header read: first non-empty line is parsed and asserted to
    have ``_header: True`` and ``schema_version == SCHEMA_VERSION``.
    Mismatch raises ``SchemaVersionMismatch`` with the contract §9
    remediation message.
  - Per-line reads: malformed lines (decode error, JSON parse
    error, schema validation failure) are caught, logged at
    WARNING, and skipped. Iteration continues.
  - Empty / whitespace-only lines: skipped silently (no warning).
  - Partial / unparseable lines: skip-with-warning per contract §9
    ("Skip record; log; continue").

The reader does NOT yield malformed-sentinel records, does NOT
expose a skip count, and does NOT attempt repair. See spec §9.3
for the rationale.

Layer 2 reader functions are deferred to Gate 4 (comparator).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterator

from forge_bridge.corpus._schema import (
    SCHEMA_VERSION,
    SchemaValidationError,
    SchemaVersionMismatch,
    validate_capture_record,
)

logger = logging.getLogger(__name__)


def _format_prefix(line: bytes | str, limit: int = 32) -> str:
    """Truncated line prefix for WARNING messages.

    Privacy posture per contract §8.4: never log the full line, since
    malformed runtime records may contain prompt fragments. First 32
    bytes/chars by default; ellipsis when truncated.
    """
    if isinstance(line, bytes):
        try:
            text = line.decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            text = repr(line[:limit])
    else:
        text = line
    text = text.rstrip("\n").rstrip("\r")
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def read_capture_file(path: Path) -> Iterator[dict]:
    """Open a Layer 1 capture file and yield each non-header record
    as a parsed dict.

    Skip malformed lines with a WARNING; never abort iteration
    mid-file. Empty / whitespace-only lines are skipped silently.

    Raises:
        FileNotFoundError: if ``path`` does not exist.
        SchemaVersionMismatch: if the header record's
            ``schema_version`` does not match this reader's
            ``SCHEMA_VERSION``.

    See module docstring for the corruption-locality contract this
    function implements.
    """
    # Open in binary mode so we can detect invalid-UTF-8 on a
    # per-line basis without aborting the whole file (Python text
    # mode would raise UnicodeDecodeError on read-line, which we
    # cannot localize to a single line).
    with path.open("rb") as fh:
        # ── Header ────────────────────────────────────────────────
        header_raw: bytes | None = None
        header_lineno = 0
        for lineno, raw_bytes in enumerate(fh, start=1):
            if raw_bytes.strip() == b"":
                continue
            header_raw = raw_bytes
            header_lineno = lineno
            break

        if header_raw is None:
            # Empty / whitespace-only file: no header, no records.
            # Treat as schema-version mismatch (the file is not a
            # well-formed Layer 1 capture file). The remediation
            # message names the empty-file case so the operator
            # understands what happened.
            raise SchemaVersionMismatch(
                f"capture file {path} is empty or has no header record; "
                f"reader expects schema_version={SCHEMA_VERSION!r}."
            )

        try:
            header = json.loads(header_raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise SchemaVersionMismatch(
                f"capture file {path} header (line {header_lineno}) is not "
                f"valid JSON: {type(exc).__name__}: {exc}. "
                f"Reader expects schema_version={SCHEMA_VERSION!r}."
            ) from exc

        if not isinstance(header, dict) or header.get("_header") is not True:
            raise SchemaVersionMismatch(
                f"capture file {path} first record (line {header_lineno}) "
                f"is not a header (missing or non-True ``_header`` key). "
                f"Reader expects schema_version={SCHEMA_VERSION!r}."
            )

        record_version = header.get("schema_version")
        if record_version != SCHEMA_VERSION:
            # Per contract §9 remediation message format.
            raise SchemaVersionMismatch(
                f"schema_version={record_version!r} records require "
                f"reader version {SCHEMA_VERSION!r}; upgrade or filter."
            )

        # ── Records ───────────────────────────────────────────────
        for lineno, raw_bytes in enumerate(fh, start=header_lineno + 1):
            if raw_bytes.strip() == b"":
                # Empty / whitespace-only lines are skipped silently.
                # Per spec §9.2 this is normal (pasted/edited JSONL
                # files often contain empty lines); WARNING would be
                # log spam.
                continue

            # Decode → parse → validate. Any per-line failure logs
            # WARNING and continues. Iteration never aborts mid-file
            # on a malformed line. Carrier sentence (verbatim):
            # "Otherwise persistence silently becomes fragility."
            try:
                line_text = raw_bytes.decode("utf-8")
            except UnicodeDecodeError as exc:
                logger.warning(
                    "skipping malformed line %d in %s: invalid UTF-8 "
                    "(%s); prefix=%r",
                    lineno, path, exc.reason,
                    _format_prefix(raw_bytes),
                )
                continue

            try:
                record = json.loads(line_text)
            except json.JSONDecodeError as exc:
                logger.warning(
                    "skipping malformed line %d in %s: JSON parse "
                    "error (%s); prefix=%r",
                    lineno, path, exc.msg,
                    _format_prefix(line_text),
                )
                continue

            try:
                validate_capture_record(record)
            except SchemaValidationError as exc:
                logger.warning(
                    "skipping malformed line %d in %s: schema "
                    "validation failed (%s); prefix=%r",
                    lineno, path, exc,
                    _format_prefix(line_text),
                )
                continue

            yield record
