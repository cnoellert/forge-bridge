"""Env-gated capture for conversational-read comprehension records."""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from forge_bridge.comprehension._schema import (
    SCHEMA_VERSION,
    validate_comprehension_record,
)

logger = logging.getLogger(__name__)

_ENV_VAR = "FORGE_BRIDGE_COMPREHENSION_CAPTURE"
_DIR_ENV_VAR = "FORGE_BRIDGE_COMPREHENSION_DIR"
_TRUTHY = frozenset({"1", "true", "yes"})
_FALSY = frozenset({"", "0", "false", "no"})
_warned_invalid_values: set[str] = set()


def comprehension_capture_enabled() -> bool:
    """Return True only for recognized truthy gate values."""
    raw = os.environ.get(_ENV_VAR, "")
    norm = raw.strip().lower()
    if norm in _TRUTHY:
        return True
    if norm in _FALSY:
        return False

    if raw not in _warned_invalid_values:
        _warned_invalid_values.add(raw)
        logger.warning(
            "%s=%r is not a recognized truthy/falsy value; treating as "
            "disabled. Accepted truthy: %s. Accepted falsy: %s.",
            _ENV_VAR,
            raw,
            sorted(_TRUTHY),
            sorted(v for v in _FALSY if v),
        )
    return False


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_capture_dir() -> Path:
    raw = os.environ.get(_DIR_ENV_VAR)
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".forge-bridge" / "comprehension"


def _serialize_line(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n"


def _make_header(captured_at: str) -> dict[str, Any]:
    return {
        "_header": True,
        "schema_version": SCHEMA_VERSION,
        "captured_at": captured_at,
    }


def _build_record(
    *,
    question: str,
    chain: list[dict],
    answer: str,
    wall_clock_ms: int,
    model: str,
    outcome: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "captured_at": _now_iso(),
        "outcome": outcome,
        "question": question,
        "chain": chain,
        "answer": answer,
        "wall_clock_ms": wall_clock_ms,
        "model": model,
        "verdict": None,
    }


def emit_comprehension_capture(
    *,
    question: str,
    chain: list[dict],
    answer: str,
    wall_clock_ms: int,
    model: str,
    outcome: str = "answered",
) -> None:
    """Append one comprehension record when the env gate is enabled.

    All errors are logged and swallowed. Capture failure must never become
    answer failure.
    """
    try:
        if not comprehension_capture_enabled():
            return None

        record = _build_record(
            question=question,
            chain=chain,
            answer=answer,
            wall_clock_ms=wall_clock_ms,
            model=model,
            outcome=outcome,
        )
        validate_comprehension_record(record)

        capture_dir = _resolve_capture_dir()
        capture_dir.mkdir(parents=True, exist_ok=True)
        date_part = record["captured_at"][:10]
        path = capture_dir / f"comprehension-{date_part}.jsonl"
        needs_header = not (path.exists() and path.stat().st_size > 0)

        record_line = _serialize_line(record)
        payload = record_line
        if needs_header:
            payload = _serialize_line(_make_header(record["captured_at"])) + record_line

        with path.open("a", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
    except Exception as exc:  # noqa: BLE001 - capture is observational only
        try:
            logger.warning(
                "comprehension capture write failed: error=%s: %s",
                type(exc).__name__,
                exc,
            )
        except Exception:  # noqa: BLE001
            pass
    return None
