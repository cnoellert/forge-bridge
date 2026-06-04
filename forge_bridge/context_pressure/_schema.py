"""Schema validation for the Context Pressure Instrument (Phase X).

THE RECORD CAPTURES FACTS. ANALYSIS IS AUTHORED LATER. CAPTURE NEVER AUTHORS.

A ``ContextPressureRecord`` is a captured-observation (required) plus an
optional authored ``analysis`` overlay — the same captured/authored lock as the
translation_oracle's TranslationCase, one instrument downstream. The captured
half is what the operator did and what the desktop looked like; the analysis
half is an authored judgement of whether contextual resolution failed, written
by a distinct later pass (never at capture time).

The agnostic envelope / source-rich payload (Phase X discuss): the four envelope
fields (prompt / world_state / observed_translation / outcome) are DCC-agnostic;
the ``world_state`` payload (``{source, raw, extracted}``) is source-rich. The
over-capture lives in ``world_state.raw`` (the migration-if-wrong surface);
``extracted`` is a recomputable projection of ``raw``, never authored.

Distinct-instrument constraint: this is a FOURTH measurement instrument
alongside comprehension/, corpus/, and translation_oracle/. Own ``__all__``, own
versioned schema, net-new AUTHORED vocab (``FAILURE_CLASS_VALUES``). The observed
fact vocab (``OUTCOME_VALUES``) is aligned to the real runtime SSE taxa (ground
truth, legitimately shared) plus one net-new state for the executor-gap case.
"""
from __future__ import annotations

from typing import Any, Final

SCHEMA_VERSION = "1"

# --- vocabularies ------------------------------------------------------------

# context_source (Creative's provenance-from-day-one): which environment the
# record was captured in. Net-new; additive. Flame is the first deployment
# target; the envelope is reusable across the others.
CONTEXT_SOURCE_VALUES: Final[frozenset[str]] = frozenset({
    "flame",
    "cli",
    "forge_graph",
    "bridge_ui",
})

# outcome: the captured terminal FACT — the observed terminal SSE taxon, verbatim.
# Aligned EXACTLY to the runtime SSE taxa (zero transcode-mapping). Outcome records
# observation, not interpretation: an Option-B mutation's terminal observation is
# `preview_emitted` (it reached preview); nothing attempts ratification, so nothing
# is "blocked" — `blocked_at_ratify` would be interpretation and is deliberately
# NOT a value (room ruling, Fork 2). Analysis interprets these facts later.
OUTCOME_VALUES: Final[frozenset[str]] = frozenset({
    "chain_complete",
    "preview_emitted",
    "apply_complete",
    "chain_aborted",
    "compile_error",
    "error",
})

# failure_class: the AUTHORED evaluation vocab (net-new — the distinct-instrument
# constraint bites here). Seed minimal; the set grows ADDITIVELY as analysis
# observes real failures (measure-first — do NOT pre-lock a rich taxonomy).
# The two contextual-failure modes (S4 ratify-gate) map onto these:
#   (a) unresolved-ref  -> unresolved_reference
#   (b) confident-wrong -> wrong_referent (the IDX-13 / space-mangle class)
FAILURE_CLASS_VALUES: Final[frozenset[str]] = frozenset({
    "unresolved_reference",
    "wrong_referent",
    "ambiguous_reference",
    "missing_from_world_state",
})

_PROVENANCE_KEYS: Final[frozenset[str]] = frozenset({
    "context_source",
    "capture_version",
    "capture_surface",
    "capture_adapter",
})

_REQUIRED_KEYS: Final[frozenset[str]] = frozenset({
    "schema_version",
    "captured_at",
    "provenance",
    "prompt",
    "observed_translation",
    "outcome",
    "world_state",
    "analysis",
})


class SchemaValidationError(ValueError):
    """Raised when a context_pressure record does not match the v1 schema."""


class SchemaVersionMismatch(ValueError):
    """Raised when a capture file requires a different reader version."""


def _validate_provenance(prov: Any) -> None:
    if not isinstance(prov, dict):
        raise SchemaValidationError("provenance must be a dict")
    missing = sorted(_PROVENANCE_KEYS.difference(prov))
    if missing:
        raise SchemaValidationError(f"provenance missing required field: {missing[0]}")
    for key in _PROVENANCE_KEYS:
        if not isinstance(prov[key], str) or not prov[key]:
            raise SchemaValidationError(f"provenance.{key} must be a non-empty string")
    if prov["context_source"] not in CONTEXT_SOURCE_VALUES:
        raise SchemaValidationError(
            "provenance.context_source must be one of: "
            + ", ".join(sorted(CONTEXT_SOURCE_VALUES))
            + f"; got {prov['context_source']!r}"
        )


def _validate_observed_translation(obs: Any) -> None:
    if not isinstance(obs, dict):
        raise SchemaValidationError("observed_translation must be a dict")
    graph = obs.get("compiled_graph")
    if not isinstance(graph, list) or not all(isinstance(s, str) for s in graph):
        raise SchemaValidationError("observed_translation.compiled_graph must be a list of strings")
    ratified = obs.get("ratified_graph", None)
    if ratified is not None and (
        not isinstance(ratified, list) or not all(isinstance(s, str) for s in ratified)
    ):
        raise SchemaValidationError(
            "observed_translation.ratified_graph must be a list of strings or null"
        )


def _validate_world_state(ws: Any, context_source: str) -> None:
    if not isinstance(ws, dict):
        raise SchemaValidationError("world_state must be a dict")
    if ws.get("source") != context_source:
        # Defensive tripwire (inert under single-source capture today): a
        # multi-source/adapter bug would surface as source != context_source.
        raise SchemaValidationError(
            "world_state.source must equal provenance.context_source "
            f"({context_source!r}); got {ws.get('source')!r}"
        )
    if not isinstance(ws.get("raw"), dict):
        raise SchemaValidationError("world_state.raw must be a dict (the over-capture surface)")
    if not isinstance(ws.get("extracted"), dict):
        raise SchemaValidationError("world_state.extracted must be a dict")


def _validate_analysis(analysis: Any) -> None:
    # analysis is None until a distinct authoring pass runs. When present it
    # MUST carry authored_at — the no-copy validation backstop (a capture-time
    # copy that forgot to stamp is rejected; the structural protection is that
    # the capture factory has no path to write analysis at all).
    if analysis is None:
        return
    if not isinstance(analysis, dict):
        raise SchemaValidationError("analysis must be null or a dict")
    if not isinstance(analysis.get("authored_at"), str) or not analysis["authored_at"]:
        raise SchemaValidationError(
            "analysis.authored_at must be a non-empty string when analysis is present "
            "(observed context may inform authored analysis; it must never automatically "
            "become it)"
        )
    fc = analysis.get("failure_class", None)
    if fc is not None and fc not in FAILURE_CLASS_VALUES:
        raise SchemaValidationError(
            "analysis.failure_class must be null or one of: "
            + ", ".join(sorted(FAILURE_CLASS_VALUES))
            + f"; got {fc!r}"
        )
    if "referent" in analysis and not isinstance(analysis["referent"], (str, type(None))):
        raise SchemaValidationError("analysis.referent must be a string or null")
    wsr = analysis.get("world_state_resolvable", None)
    if wsr is not None and not isinstance(wsr, bool):
        raise SchemaValidationError("analysis.world_state_resolvable must be a bool or null")
    if "resolving_signal" in analysis and not isinstance(
        analysis["resolving_signal"], (str, type(None))
    ):
        raise SchemaValidationError("analysis.resolving_signal must be a string or null")


def validate_context_pressure_record(record: Any) -> None:
    """Validate one v1 ``ContextPressureRecord``.

    Required: the captured-observation fields + ``analysis`` key (value may be
    ``None`` = unanalyzed). Raises ``SchemaValidationError`` on any violation.
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
            f"schema_version must be {SCHEMA_VERSION!r}, got {record['schema_version']!r}"
        )
    if not isinstance(record["captured_at"], str) or not record["captured_at"]:
        raise SchemaValidationError("captured_at must be a non-empty string")
    _validate_provenance(record["provenance"])
    if not isinstance(record["prompt"], str):
        raise SchemaValidationError("prompt must be a string")
    _validate_observed_translation(record["observed_translation"])
    if record["outcome"] not in OUTCOME_VALUES:
        raise SchemaValidationError(
            "outcome must be one of: " + ", ".join(sorted(OUTCOME_VALUES))
            + f"; got {record['outcome']!r}"
        )
    _validate_world_state(record["world_state"], record["provenance"]["context_source"])
    _validate_analysis(record["analysis"])
