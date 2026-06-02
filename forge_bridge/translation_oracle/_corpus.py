"""TF.3a Step 3 — corpus data layer + coverage accounting.

Atomic-append JSONL (mirrors the comprehension/ topology) for the labeled
reference corpus, plus the [N] coverage accounting that decides whether the
corpus is *adequate* — by COVERAGE, not count (Q2 / Creative). Adequacy =
every verdict-pair cell x translation class x discovery multi-tag pattern x
D-series defect represented, with Tier-2 classes needing >=2 labeled instances
per cell (tune + holdout) and Tier-1 >=1.

The load-bearing guard (DT item 3): a Tier-1 class is only "covered" by an
``instrumented-translation`` trace — a ``seed-legibility`` trace lacks the
runtime markers a Tier-1 detector reads, so counting it would report GREEN on a
cell no Tier-1 detector can actually evaluate. Coverage is capability-checked,
not occupancy-counted.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Final, Optional

from forge_bridge.translation_oracle._schema import validate_translation_case

_DIR_ENV_VAR: Final[str] = "TRANSLATION_ORACLE_DIR"
_CASES_FILENAME: Final[str] = "cases.jsonl"

# Class -> detection tier (TF.2 §5). routing's defining defect (#2-a shadow) is
# Tier-1 (the tool_forced marker); its wrong-selection half is Tier-2 but the
# class is gated as Tier-1 here (instrumented capture is required for its
# dominant defect). grounding + entity-resolution are ground-truth/Tier-2.
_TIER1_CLASSES: Final[frozenset[str]] = frozenset({"extraction", "contextual", "routing"})
_TIER2_CLASSES: Final[frozenset[str]] = frozenset({"grounding", "entity-resolution"})

_TIER1_MIN: Final[int] = 1
_TIER2_MIN: Final[int] = 2

# Multi-tag patterns observed in discovery (TF.2 §4). Extend as discovery grows.
_DISCOVERY_MULTITAG: Final[list[frozenset[str]]] = [frozenset({"routing", "extraction"})]  # defect #2

# Every D-series defect must be represented (via label.defect_ref).
_DSERIES_DEFECTS: Final[list[str]] = ["defect-1", "defect-2", "defect-3"]

# verdict-pair (translation, substrate) -> matrix cell (TF.2 §2).
_VERDICT_CELLS: Final[dict[tuple[str, str], str]] = {
    ("pass", "pass"): "a",
    ("fail", "pass"): "b",
    ("pass", "gap"): "c",
    ("fail", "gap"): "d",
}


def _resolve_corpus_dir(corpus_dir: Optional[Path] = None) -> Path:
    if corpus_dir is not None:
        return Path(corpus_dir)
    raw = os.environ.get(_DIR_ENV_VAR)
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".forge-bridge" / "translation_oracle"


def append_case(case: dict, *, corpus_dir: Optional[Path] = None) -> Path:
    """Validate and atomic-append one TranslationCase to the corpus JSONL."""
    validate_translation_case(case)
    target_dir = _resolve_corpus_dir(corpus_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / _CASES_FILENAME
    needs_header = not (path.exists() and path.stat().st_size > 0)
    payload = ""
    if needs_header:
        payload += json.dumps({"_header": True, "schema_version": case["schema_version"]},
                              sort_keys=True) + "\n"
    payload += json.dumps(case, sort_keys=True) + "\n"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(payload)
        fh.flush()
    return path


def read_cases(*, corpus_dir: Optional[Path] = None) -> list[dict]:
    """Read all TranslationCases (skips the header and blank lines)."""
    path = _resolve_corpus_dir(corpus_dir) / _CASES_FILENAME
    if not path.exists():
        return []
    cases: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if isinstance(record, dict) and record.get("_header"):
            continue
        cases.append(record)
    return cases


def _cell_of(label: dict) -> Optional[str]:
    pair = label.get("expected_verdict_pair") or {}
    return _VERDICT_CELLS.get((pair.get("translation"), pair.get("substrate")))


def _is_instrumented(case: dict) -> bool:
    return (case.get("observed") or {}).get("capture_provenance") == "instrumented-translation"


def coverage_report(cases: list[dict]) -> dict:
    """Capability-checked coverage report over the LABELED cases.

    Label-free (3b) cases do not contribute — coverage is about the validation
    set. Returns a structured dict with per-dimension status, RED flags, and a
    single ``complete`` bool.
    """
    labeled = [c for c in cases if c.get("label") is not None]

    # --- verdict-pair cells -------------------------------------------------
    cell_counts: dict[str, int] = {c: 0 for c in ("a", "b", "c", "d")}
    for c in labeled:
        cell = _cell_of(c["label"])
        if cell:
            cell_counts[cell] += 1
    missing_cells = [c for c, n in cell_counts.items() if n == 0]

    # --- translation classes (tier-gated; Tier-1 needs instrumented) --------
    class_status: dict[str, dict] = {}
    red_flags: list[str] = []
    for cls in sorted(_TIER1_CLASSES | _TIER2_CLASSES):
        tier1 = cls in _TIER1_CLASSES
        minimum = _TIER1_MIN if tier1 else _TIER2_MIN
        tagged = [c for c in labeled if cls in (c["label"].get("expected_classes") or [])]
        # Tier-1: only instrumented traces count toward the requirement.
        counting = [c for c in tagged if _is_instrumented(c)] if tier1 else tagged
        met = len(counting) >= minimum
        class_status[cls] = {
            "tier": "tier-1" if tier1 else "tier-2",
            "minimum": minimum,
            "tagged": len(tagged),
            "counting": len(counting),
            "met": met,
        }
        if tier1 and tagged and len(counting) < minimum:
            red_flags.append(
                f"class {cls!r} is Tier-1 but {len(tagged) - len(counting)} of its "
                f"{len(tagged)} case(s) are seed-legibility (no runtime markers) — "
                f"false-green: a Tier-1 detector cannot evaluate them"
            )

    # --- discovery multi-tag patterns ---------------------------------------
    multitag_status: dict[str, int] = {}
    for pattern in _DISCOVERY_MULTITAG:
        n = sum(1 for c in labeled if pattern <= set(c["label"].get("expected_classes") or []))
        multitag_status["+".join(sorted(pattern))] = n

    # --- D-series defects ---------------------------------------------------
    defect_counts: dict[str, int] = {d: 0 for d in _DSERIES_DEFECTS}
    for c in labeled:
        ref = c["label"].get("defect_ref")
        if ref in defect_counts:
            defect_counts[ref] += 1

    complete = (
        not missing_cells
        and all(s["met"] for s in class_status.values())
        and all(n > 0 for n in multitag_status.values())
        and all(n > 0 for n in defect_counts.values())
        and not red_flags
    )
    return {
        "labeled_count": len(labeled),
        "verdict_cells": cell_counts,
        "missing_cells": missing_cells,
        "classes": class_status,
        "multi_tag": multitag_status,
        "defects": defect_counts,
        "red_flags": red_flags,
        "complete": complete,
    }
