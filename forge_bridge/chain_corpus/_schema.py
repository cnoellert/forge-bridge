"""Schema guards for the dormant chain-corpus capture surface."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

SCHEMA_VERSION = "1"

COMPILE_REGIMES = frozenset({
    "chain_aborted",
    "clarification_needed",
    "compile_error",
    "compiled_mutating_preview",
    "compiled_non_mutating",
})
SOURCES = frozenset({"captured", "seed"})


class ChainCorpusSchemaError(ValueError):
    """Raised when a chain-corpus row is not schema-valid."""


class ChainCorpusVersionError(ChainCorpusSchemaError):
    """Raised when a chain-corpus row uses an unsupported schema version."""


def validate_compile_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and return a compile JSONL record."""

    _require_version(record)
    _require_string(record, "captured_at")
    _require_string(record, "request_id")
    regime = _require_string(record, "regime")
    if regime not in COMPILE_REGIMES:
        raise ChainCorpusSchemaError(f"unknown compile regime: {regime!r}")
    chain_steps = record.get("chain_steps")
    if not isinstance(chain_steps, list) or not all(
        isinstance(step, str) for step in chain_steps
    ):
        raise ChainCorpusSchemaError("chain_steps must be a list[str]")
    if not isinstance(record.get("salvage_applied"), bool):
        raise ChainCorpusSchemaError("salvage_applied must be bool")
    salvage_reason = record.get("salvage_reason")
    if salvage_reason is not None and not isinstance(salvage_reason, str):
        raise ChainCorpusSchemaError("salvage_reason must be str|null")
    tags = record.get("variety_tags")
    if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
        raise ChainCorpusSchemaError("variety_tags must be a list[str]")
    source = _require_string(record, "source")
    if source not in SOURCES:
        raise ChainCorpusSchemaError(f"unknown source: {source!r}")
    if not isinstance(record.get("replayable"), bool):
        raise ChainCorpusSchemaError("replayable must be bool")
    return dict(record)


def validate_trace_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and return a chain-trace JSONL record."""

    _require_version(record)
    _require_string(record, "captured_at")
    _require_string(record, "request_id")
    _require_string(record, "tool_name")
    _require_hash(record, "args_hash")
    _require_hash(record, "result_hash")
    if "result" not in record:
        raise ChainCorpusSchemaError("trace record missing result")
    return dict(record)


def _require_version(record: Mapping[str, Any]) -> None:
    version = record.get("schema_version")
    if version != SCHEMA_VERSION:
        raise ChainCorpusVersionError(
            f"unsupported chain-corpus schema_version: {version!r}"
        )


def _require_string(record: Mapping[str, Any], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value:
        raise ChainCorpusSchemaError(f"{key} must be a non-empty string")
    return value


def _require_hash(record: Mapping[str, Any], key: str) -> str:
    value = _require_string(record, key)
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ChainCorpusSchemaError(f"{key} must be a full sha256 hex digest")
    return value
