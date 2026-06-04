"""Context Pressure Instrument — capture factory + atomic-append corpus I/O.

The structural half of the no-copy lock lives here: ``build_record`` has NO
``analysis`` parameter — the capture path cannot author analysis, by
construction. ``analysis`` is set to ``None`` and only a distinct later
authoring pass (S4) may populate it. (The schema's ``authored_at``-required
check is the validation backstop; this missing-parameter is the real teeth.)

Atomic-append JSONL with a one-line header, mirroring corpus/ and
comprehension/. The runtime corpus defaults to the per-machine
``~/.forge-bridge/context_pressure/`` dir; pass ``corpus_dir`` for tests or a
committed seed set.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Final, Optional

from forge_bridge.context_pressure._schema import (
    SCHEMA_VERSION,
    validate_context_pressure_record,
)

_DIR_ENV_VAR: Final[str] = "CONTEXT_PRESSURE_DIR"
_RECORDS_FILENAME: Final[str] = "records.jsonl"


def build_record(
    *,
    captured_at: str,
    provenance: dict,
    prompt: str,
    observed_translation: dict,
    outcome: str,
    world_state: dict,
) -> dict:
    """Assemble a captured ContextPressureRecord with ``analysis=None``.

    NOTE: there is intentionally no ``analysis`` parameter. The capture path is
    structurally incapable of authoring analysis — observed context may inform
    authored analysis later, but must never automatically become it. The record
    is validated before return.
    """
    record = {
        "schema_version": SCHEMA_VERSION,
        "captured_at": captured_at,
        "provenance": provenance,
        "prompt": prompt,
        "observed_translation": observed_translation,
        "outcome": outcome,
        "world_state": world_state,
        "analysis": None,
    }
    validate_context_pressure_record(record)
    return record


def _resolve_dir(corpus_dir: Optional[Path] = None) -> Path:
    if corpus_dir is not None:
        return Path(corpus_dir)
    raw = os.environ.get(_DIR_ENV_VAR)
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".forge-bridge" / "context_pressure"


def append_record(record: dict, *, corpus_dir: Optional[Path] = None) -> Path:
    """Validate and atomic-append one record to the corpus JSONL."""
    validate_context_pressure_record(record)
    target_dir = _resolve_dir(corpus_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / _RECORDS_FILENAME
    needs_header = not (path.exists() and path.stat().st_size > 0)
    payload = ""
    if needs_header:
        payload += json.dumps(
            {"_header": True, "schema_version": record["schema_version"]}, sort_keys=True
        ) + "\n"
    payload += json.dumps(record, sort_keys=True) + "\n"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(payload)
        fh.flush()
    return path


def read_records(*, corpus_dir: Optional[Path] = None) -> list[dict]:
    """Read all records (skips the header line and blank lines)."""
    path = _resolve_dir(corpus_dir) / _RECORDS_FILENAME
    if not path.exists():
        return []
    records: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record: Any = json.loads(line)
        if isinstance(record, dict) and record.get("_header"):
            continue
        records.append(record)
    return records
