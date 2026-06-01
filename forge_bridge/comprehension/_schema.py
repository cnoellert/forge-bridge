"""Schema validation for conversational-read comprehension captures."""
from __future__ import annotations

from typing import Any, Final

SCHEMA_VERSION = "1"

VERDICT_VALUES: Final[frozenset[str]] = frozenset({
    "loved",
    "hated",
    "overstated",
    "omitted_context",
    "missed_intent",
})

_REQUIRED_KEYS: Final[frozenset[str]] = frozenset({
    "schema_version",
    "captured_at",
    "question",
    "chain",
    "answer",
    "wall_clock_ms",
    "model",
    "verdict",
})


class SchemaValidationError(ValueError):
    """Raised when a comprehension record does not match the v1 schema."""


class SchemaVersionMismatch(ValueError):
    """Raised when a capture file requires a different reader version."""


def validate_comprehension_record(record: Any) -> None:
    """Validate one v1 comprehension record.

    The verdict may be null at capture time or one of the five annotation
    values after review. Requiring a verdict would be a schema-version bump.
    """
    if not isinstance(record, dict):
        raise SchemaValidationError(
            f"record must be a dict, got {type(record).__name__}"
        )

    missing = sorted(_REQUIRED_KEYS.difference(record))
    if missing:
        raise SchemaValidationError(f"missing required field: {missing[0]}")

    if record["schema_version"] != SCHEMA_VERSION:
        raise SchemaValidationError(
            "schema_version must be "
            f"{SCHEMA_VERSION!r}, got {record['schema_version']!r}"
        )
    if not isinstance(record["captured_at"], str) or not record["captured_at"]:
        raise SchemaValidationError("captured_at must be a non-empty string")
    if not isinstance(record["question"], str):
        raise SchemaValidationError("question must be a string")
    if not isinstance(record["chain"], list):
        raise SchemaValidationError("chain must be a list")
    for index, entry in enumerate(record["chain"]):
        if not isinstance(entry, dict):
            raise SchemaValidationError(f"chain[{index}] must be a dict")
        for key in ("step", "result"):
            if key not in entry:
                raise SchemaValidationError(
                    f"chain[{index}] missing required field: {key}"
                )
        if not isinstance(entry["step"], str):
            raise SchemaValidationError(f"chain[{index}].step must be a string")
    if not isinstance(record["answer"], str):
        raise SchemaValidationError("answer must be a string")
    if not isinstance(record["wall_clock_ms"], int):
        raise SchemaValidationError("wall_clock_ms must be an int")
    if record["wall_clock_ms"] < 0:
        raise SchemaValidationError("wall_clock_ms must be >= 0")
    if not isinstance(record["model"], str):
        raise SchemaValidationError("model must be a string")
    verdict = record["verdict"]
    if verdict is not None and verdict not in VERDICT_VALUES:
        raise SchemaValidationError(
            "verdict must be null or one of: "
            + ", ".join(sorted(VERDICT_VALUES))
        )
