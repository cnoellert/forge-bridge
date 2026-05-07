"""forge_bridge.corpus._schema — Layer 1 record schema validation.

The canonical record shape is defined in
``A.5.3.2-INSTRUMENT-CONTRACT.md`` §3. This module is the
authoritative implementation of that shape: required fields, value
enums, type checks. Adding a required field or changing a value enum
is a ``SCHEMA_VERSION`` bump.

Validation strategy:

  - Walk the record top-down: top-level keys → block keys → leaf
    types. First failure raises ``SchemaValidationError`` with a
    descriptive message naming the offending field.
  - Strict on required keys; permissive on extra keys within blocks
    where the contract notes new fields are non-breaking schema
    additions (e.g., new backend keys under topology.backends).
  - No external library deps — the contract promises no new external
    libraries, and the validation rules are simple enough to express
    directly.
"""
from __future__ import annotations

from typing import Any

# Current schema version. Bumped when the record shape changes.
# Consumers (the reader, the comparator) MUST check this before
# processing records — see ``A.5.3.2-INSTRUMENT-CONTRACT.md`` §9
# "Schema version mismatch."
SCHEMA_VERSION = "1"


class SchemaValidationError(ValueError):
    """Raised when a record does not conform to the Layer 1 schema."""


class SchemaVersionMismatch(ValueError):
    """Raised by the reader when a Layer 1 file's header records a
    ``schema_version`` that does not match this reader's expected
    ``SCHEMA_VERSION``.

    Per ``A.5.3.2-INSTRUMENT-CONTRACT.md`` §9 the remediation message
    is ``"schema_version=N records require reader version M; upgrade
    or filter."`` — the reader formats N (record's version) and M
    (this reader's version) into the message at raise time. Hard
    error rather than skip-and-warn because the entire file's record
    shape is determined by ``schema_version`` — once it diverges,
    per-line skip is meaningless.

    Schema migrations write new files (per I-1); old files keep
    their original ``schema_version``. Encountering this exception
    means a consumer needs to upgrade its reader code or filter the
    file out of the consumed set, not that the file is corrupted.
    """


# Required top-level keys for a v1 capture record (per contract §3).
_REQUIRED_TOP_KEYS: frozenset[str] = frozenset({
    "schema_version",
    "capture_id",
    "captured_at",
    "source",
    "prompt",
    "candidate_set",
    "topology",
    "identity",
    "narrower",
})

_VALID_SOURCES: frozenset[str] = frozenset({"fixture", "runtime"})

_VALID_AMBIGUITY_STATES: frozenset[str] = frozenset({
    "single_survivor", "multi_survivor", "zero_survivor",
})

# Backends that v1 schema requires under ``topology.backends``.
# Adding a backend bumps ``SCHEMA_VERSION`` (per contract §3 — new
# keys are non-breaking schema additions, but adding a REQUIRED
# backend changes what every record must carry, which is breaking).
_REQUIRED_BACKENDS: frozenset[str] = frozenset({
    "flame_bridge", "ollama_local", "anthropic",
})

_REQUIRED_CANDIDATE_SET_KEYS: frozenset[str] = frozenset({
    "post_reachability", "post_pr14_filter",
})

_REQUIRED_TOPOLOGY_KEYS: frozenset[str] = frozenset({
    "probed_at", "backends",
})

_REQUIRED_IDENTITY_KEYS: frozenset[str] = frozenset({
    "narrower_version_hash",
    "registered_tools_snapshot_hash",
    "daemon_git_sha",
})

_REQUIRED_NARROWER_KEYS: frozenset[str] = frozenset({
    "decision", "pr20_condition_met", "collapse_occurred",
    "ambiguity_state", "latency_ms",
})


def validate_capture_record(record: Any) -> None:
    """Validate a Layer 1 capture record against the v1 schema.

    Returns None on success. Raises ``SchemaValidationError`` with a
    descriptive message on any contract violation. The first failure
    encountered raises; the function does not aggregate errors (PR 1
    keeps the validator simple; aggregate-error mode can be added
    later if analytics tooling needs it).

    See ``A.5.3.2-INSTRUMENT-CONTRACT.md`` §3 for the canonical shape.
    """
    if not isinstance(record, dict):
        raise SchemaValidationError(
            f"record must be a dict, got {type(record).__name__}"
        )

    missing = _REQUIRED_TOP_KEYS - record.keys()
    if missing:
        raise SchemaValidationError(
            f"record missing required top-level keys: {sorted(missing)}"
        )

    if record["schema_version"] != SCHEMA_VERSION:
        raise SchemaValidationError(
            f"schema_version mismatch: record has "
            f"{record['schema_version']!r}, validator expects "
            f"{SCHEMA_VERSION!r}"
        )

    if record["source"] not in _VALID_SOURCES:
        raise SchemaValidationError(
            f"source must be one of {sorted(_VALID_SOURCES)}, got "
            f"{record['source']!r}"
        )

    if not isinstance(record["prompt"], str) or not record["prompt"]:
        raise SchemaValidationError("prompt must be a non-empty string")

    _validate_candidate_set(record["candidate_set"])
    _validate_topology(record["topology"])
    _validate_identity(record["identity"])
    _validate_narrower(record["narrower"])


def _validate_candidate_set(cs: Any) -> None:
    if not isinstance(cs, dict):
        raise SchemaValidationError("candidate_set must be a dict")
    missing = _REQUIRED_CANDIDATE_SET_KEYS - cs.keys()
    if missing:
        raise SchemaValidationError(
            f"candidate_set missing keys: {sorted(missing)}"
        )
    for key in _REQUIRED_CANDIDATE_SET_KEYS:
        if not isinstance(cs[key], list):
            raise SchemaValidationError(
                f"candidate_set.{key} must be a list of tool names"
            )


def _validate_topology(topo: Any) -> None:
    if not isinstance(topo, dict):
        raise SchemaValidationError("topology must be a dict")
    missing = _REQUIRED_TOPOLOGY_KEYS - topo.keys()
    if missing:
        raise SchemaValidationError(
            f"topology missing keys: {sorted(missing)}"
        )
    backends = topo["backends"]
    if not isinstance(backends, dict):
        raise SchemaValidationError("topology.backends must be a dict")
    missing_backends = _REQUIRED_BACKENDS - backends.keys()
    if missing_backends:
        raise SchemaValidationError(
            f"topology.backends missing required backends: "
            f"{sorted(missing_backends)}. v1 schema requires "
            f"{sorted(_REQUIRED_BACKENDS)}."
        )
    for backend_name, backend_state in backends.items():
        if not isinstance(backend_state, dict):
            raise SchemaValidationError(
                f"topology.backends.{backend_name} must be a dict"
            )
        if "reachable" not in backend_state:
            raise SchemaValidationError(
                f"topology.backends.{backend_name} missing required "
                f"'reachable' key"
            )
        if not isinstance(backend_state["reachable"], bool):
            raise SchemaValidationError(
                f"topology.backends.{backend_name}.reachable must be "
                f"a bool"
            )


def _validate_identity(identity: Any) -> None:
    if not isinstance(identity, dict):
        raise SchemaValidationError("identity must be a dict")
    missing = _REQUIRED_IDENTITY_KEYS - identity.keys()
    if missing:
        raise SchemaValidationError(
            f"identity missing keys: {sorted(missing)}"
        )
    for key in _REQUIRED_IDENTITY_KEYS:
        val = identity[key]
        if not isinstance(val, str) or not val:
            raise SchemaValidationError(
                f"identity.{key} must be a non-empty string, got "
                f"{type(val).__name__}={val!r}"
            )


def _validate_narrower(narrower: Any) -> None:
    if not isinstance(narrower, dict):
        raise SchemaValidationError("narrower must be a dict")
    missing = _REQUIRED_NARROWER_KEYS - narrower.keys()
    if missing:
        raise SchemaValidationError(
            f"narrower missing keys: {sorted(missing)}"
        )
    if not isinstance(narrower["decision"], list):
        raise SchemaValidationError(
            "narrower.decision must be a list (possibly empty)"
        )
    if not isinstance(narrower["pr20_condition_met"], bool):
        raise SchemaValidationError(
            "narrower.pr20_condition_met must be a bool"
        )
    if not isinstance(narrower["collapse_occurred"], bool):
        raise SchemaValidationError(
            "narrower.collapse_occurred must be a bool"
        )
    if narrower["ambiguity_state"] not in _VALID_AMBIGUITY_STATES:
        raise SchemaValidationError(
            f"narrower.ambiguity_state must be one of "
            f"{sorted(_VALID_AMBIGUITY_STATES)}, got "
            f"{narrower['ambiguity_state']!r}"
        )
    if not isinstance(narrower["latency_ms"], (int, float)) or isinstance(
        narrower["latency_ms"], bool
    ):
        raise SchemaValidationError(
            "narrower.latency_ms must be a number"
        )
