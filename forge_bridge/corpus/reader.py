"""forge_bridge.corpus.reader — Layer 1 record reader (Gate 1 stub).

The eventual reader (per ``A.5.3.2-GATE-1-SPEC.md`` §3.5) opens a
Layer 1 capture file, validates the header record's schema_version,
and yields each subsequent record as a parsed dict. Schema-version
mismatch raises a structured error per contract §9.

Layer 2 reader functions are deferred to Gate 4 (comparator).

PR 1 status: stub. Implementation lands in PR 3 alongside the writer
(the round-trip ``read(write(record)) == record`` verification
requires both halves).
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterator


def read_capture_file(path: Path) -> Iterator[dict]:
    """Open a Layer 1 capture file and yield each record as a dict.

    PR 1 stub: raises NotImplementedError. Implementation lands in
    PR 3 alongside the writer.
    """
    raise NotImplementedError(
        "read_capture_file lands in PR 3 alongside the writer."
    )
