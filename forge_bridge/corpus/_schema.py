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

from typing import Any, Final

from forge_bridge.corpus._sources import KNOWN_SOURCE_VALUES

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


# Universal required top-level keys for a v1 capture record. Every
# record_kind must carry these. Per A.5.3.2-PR7-SPEC.md §4.3.1
# (post-§4.3 amendment): ``record_kind`` is the discriminator that
# separates observation records (live arbitration emissions) from
# expectation records (PR 8 authored expectations). Legacy records
# persisted before PR 7 lack ``record_kind``; the reader synthesizes
# ``record_kind="observation"`` at read time (see reader.py + spec
# §4.4.2), so the validator sees ``record_kind`` on every record by
# the time it runs.
_REQUIRED_TOP_KEYS: frozenset[str] = frozenset({
    "schema_version",
    "capture_id",
    "captured_at",
    "record_kind",
})

# Observation-specific required keys. These were the original PR 1-3
# canonical record shape (per contract §3). At PR 7 they become
# observation-only because expectation records (PR 8) have a distinct
# shape that does NOT carry ``source`` or the arbitration-state
# fields. The validator checks these in the record_kind=="observation"
# branch.
_REQUIRED_OBSERVATION_KEYS: frozenset[str] = frozenset({
    "source",
    "prompt",
    "candidate_set",
    "topology",
    "identity",
    "narrower",
})

# Expectation records have no required keys beyond _REQUIRED_TOP_KEYS
# at PR 7 close. PR 8's seed driver will define the expectation
# record shape; required-keys-for-expectation may be added at that
# point. The structural prohibition at PR 7 is asymmetric: observation
# records require source ∈ KNOWN_SOURCE_VALUES; expectation records
# MUST NOT carry source at all (per spec §9.7).

# Known record_kind values. Per A.5.3.2-GATE-2-FRAMING.md §9.2,
# record_kind is governed STRUCTURALLY: adding a new value implies a
# new authority surface (not merely a new provenance class). Adding a
# third record_kind requires the corresponding helper, signature, and
# truth claim — all framing-level decisions.
_KNOWN_RECORD_KINDS: Final[frozenset[str]] = frozenset({
    "observation", "expectation",
})

# Expectation-specific required keys. PR 8 introduces these per
# A.5.3.2-PR8-SPEC.md §4.2 — the first PR to construct expectation
# records. The set is locked at framing-time minimum-viable per
# A.5.3.2-PR8-FRAMING.md §5.3 (Q2): three fields express the
# fixture-author's authored expectation (fixture identity, the
# prompt being exercised, the narrowing decision the author
# declares should result). Adding a fourth required field requires
# framing-level review per A.5.3.2-PR8-SPEC.md §7 phase-end
# conditions; cleanup PRs may not extend this set.
_REQUIRED_EXPECTATION_KEYS: Final[frozenset[str]] = frozenset({
    "fixture_id",
    "prompt",
    "expected_narrow",
})

# Source-class governance is delegated to ``KNOWN_SOURCE_VALUES`` in
# ``forge_bridge/corpus/_sources.py`` (imported at module top). The
# legacy ``_VALID_SOURCES = frozenset({"fixture", "runtime"})``
# constant was removed at PR 7 Step 5 per the §4.3 spec amendment:
# (1) "fixture" was a test-isolation pattern from PR 1-3 era, not a
# persisted production provenance class; carrying it in the schema's
# governance constant polluted the production ontology.
# (2) Maintaining a parallel _VALID_SOURCES alongside KNOWN_SOURCE_VALUES
# would violate Gate 2 framing's lockstep contract (carrier #14):
# adding a new source value would have required updating two
# governance surfaces, with drift inevitable.
# Single source of truth: KNOWN_SOURCE_VALUES in _sources.py.

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

    # ── record_kind enum (PR 7 §4.3.1, post-§4.3 amendment) ──────────────
    # record_kind discriminates observation records (live arbitration
    # emissions) from expectation records (PR 8 authored expectations).
    # Adding a third value implies a new authority surface — framing-
    # level decision per Gate 2 framing §9.2.
    record_kind = record["record_kind"]
    if record_kind not in _KNOWN_RECORD_KINDS:
        raise SchemaValidationError(
            f"record_kind must be one of {sorted(_KNOWN_RECORD_KINDS)}, "
            f"got {record_kind!r}"
        )

    # ── record-kind-conditional shape (PR 7 §4.3.1) ──────────────────────
    # Observation records carry the original PR 1-3 canonical fields plus
    # source ∈ KNOWN_SOURCE_VALUES (Gate 2 framing carrier #14).
    # Expectation records have a distinct shape — at PR 7 the only
    # structural requirement is "no source field"; PR 8's seed driver
    # defines the rest.
    if record_kind == "observation":
        missing_obs = _REQUIRED_OBSERVATION_KEYS - record.keys()
        if missing_obs:
            raise SchemaValidationError(
                f"observation record missing required keys: "
                f"{sorted(missing_obs)}"
            )

        if record["source"] not in KNOWN_SOURCE_VALUES:
            raise SchemaValidationError(
                f"observation record source must be one of "
                f"{sorted(KNOWN_SOURCE_VALUES)}, got {record['source']!r}"
            )

        if not isinstance(record["prompt"], str) or not record["prompt"]:
            raise SchemaValidationError("prompt must be a non-empty string")

        _validate_candidate_set(record["candidate_set"])
        _validate_topology(record["topology"])
        _validate_identity(record["identity"])
        _validate_narrower(record["narrower"])

    elif record_kind == "expectation":
        # ── No-source check (preserved from PR 7) ──────────────
        # Cleanup-pressure-resistance class member #7 (truth-
        # partitioning) — a unified record carrying both
        # expectation and observation fields destroys
        # falsifiability. The schema validator rejects expectation
        # records carrying a ``source`` field at the persistence
        # boundary. See A.5.3.2-PR8-SPEC.md §0 PR 8-local binding
        # statement #1.
        if "source" in record:
            raise SchemaValidationError(
                "expectation record must not carry a 'source' field; "
                f"found source={record['source']!r}"
            )

        # ── PR 8 required-keys check ───────────────────────────
        # Per A.5.3.2-PR8-SPEC.md §4.2 + framing §5.3 (Q2): the
        # minimum-viable expectation shape requires exactly three
        # fields (fixture_id, prompt, expected_narrow) plus the
        # universal top-level keys. Cleanup PRs adding a fourth
        # required field route through framing review.
        missing_exp = _REQUIRED_EXPECTATION_KEYS - record.keys()
        if missing_exp:
            raise SchemaValidationError(
                f"expectation record missing required keys: "
                f"{sorted(missing_exp)}"
            )

        # ── PR 8 per-field type validation ─────────────────────
        # Each PR 8-required field has a per-type contract. The
        # first failure raises (PR 1 convention — no aggregate-
        # error mode at this layer).
        if not isinstance(record["fixture_id"], str) or not record["fixture_id"]:
            raise SchemaValidationError(
                "expectation fixture_id must be a non-empty string"
            )
        if not isinstance(record["prompt"], str) or not record["prompt"]:
            raise SchemaValidationError(
                "expectation prompt must be a non-empty string"
            )
        if not isinstance(record["expected_narrow"], list):
            raise SchemaValidationError(
                "expectation expected_narrow must be a list"
            )
        if not all(
            isinstance(tool, str) for tool in record["expected_narrow"]
        ):
            raise SchemaValidationError(
                "expectation expected_narrow entries must be strings"
            )
        # The empty list is a valid expected_narrow value —
        # expresses "expected zero-survivor narrowing for this
        # prompt." See A.5.3.2-PR8-SPEC.md §4.2.2.


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
