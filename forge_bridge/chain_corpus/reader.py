"""Reader and coverage report for the chain corpus."""
from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from forge_bridge.chain_corpus._schema import (
    validate_compile_record,
    validate_trace_record,
)

REQUIRED_COVERAGE_TAGS = (
    "multi_step",
    "op_mix_filter_foreach_collect",
    "if_gate",
    "foreach",
    "bug_d_salvage",
    "clarification_reentry",
    "empty_degenerate",
    "mutating_preview",
    "commit",
)
COVERAGE_LIMIT = (
    "Coverage is based only on captured compile facts and cannot prove both "
    "branches of an if-gate or data-dependent foreach output diversity."
)


def read_compile_file(path: str | Path) -> list[dict[str, Any]]:
    """Read and validate a chain-compile JSONL file."""

    return [
        validate_compile_record(record)
        for record in _read_records(path)
    ]


def read_trace_file(path: str | Path) -> list[dict[str, Any]]:
    """Read and validate a chain-trace JSONL file."""

    return [
        validate_trace_record(record)
        for record in _read_records(path)
    ]


def coverage_report(
    compile_records: Iterable[dict[str, Any]],
    *,
    floor: int = 1,
) -> dict[str, Any]:
    """Return a captured-only variety coverage summary."""

    counter: Counter[str] = Counter()
    captured = 0
    for record in compile_records:
        if record.get("source") != "captured":
            continue
        captured += 1
        counter.update(record.get("variety_tags") or [])

    counts = {tag: counter.get(tag, 0) for tag in REQUIRED_COVERAGE_TAGS}
    missing = [tag for tag, count in counts.items() if count < floor]
    return {
        "source": "captured",
        "floor": floor,
        "captured_records": captured,
        "counts": counts,
        "missing": missing,
        "pass": not missing,
        "limit": COVERAGE_LIMIT,
    }


def _read_records(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("_header") is True:
                continue
            records.append(row)
    return records
