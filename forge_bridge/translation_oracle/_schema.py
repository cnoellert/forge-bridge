"""Schema validation for the TF.3a translation-fidelity oracle.

THE RECORD MODELS REALITY. LABELS MODEL EVALUATION. EVALUATION IS OPTIONAL;
REALITY IS NOT.

That single line is the architectural lock future readers will ask about, so
it lives here at the top: a ``TranslationCase`` is an ``ObservedTrace``
(required) plus an optional ``Label``. The ObservedTrace is a frozen snapshot
of what the translation layer actually did with an input; the Label is an
authored statement of what it *should* have done.

Why Label is optional — the TF.3a / TF.3b boundary (DT+Creative ratification,
2026-06-02):
  - In TF.3a (validation) a case carries BOTH. The oracle emits a verdict-pair
    from the ObservedTrace, and validation compares that emission against the
    Label.
  - In TF.3b (the run) there are NO labels — production inputs are unlabeled by
    nature. The oracle's job is to *generate* the thing the Label represented.
    A mandatory-Label schema would make a 3b record literally unwriteable.
  Therefore ObservedTrace is fundamental and Label is a 3a-only calibration
  overlay. Presence-of-Label is the validation-set discriminator. The oracle is
  ``emit(observed) -> verdict_pair`` — label-free — by construction.

Distinct-instrument constraint (Q5, "three-vocabulary rule"): this is a THIRD
measurement instrument alongside ``comprehension/`` (CR.1) and ``corpus/``
(v1.6 divergence). Its label vocabularies are net-new and MUST NOT reuse the
others' — the constraint bites at the field level, not just the package name.
Seed traces from ``comprehension/`` are *transcoded* into ``ObservedTrace`` (as
``capture_provenance="seed-legibility"``), never imported as a schema
dependency.
"""
from __future__ import annotations

from typing import Any, Final

SCHEMA_VERSION = "1"

# --- net-new vocabularies (distinct from comprehension/ and corpus/) ---------

# The verdict matrix (TF.2 §2): translation {pass, fail} x substrate {pass, gap}.
# honest-decline = (translation=pass, substrate=gap).
TRANSLATION_VERDICT_VALUES: Final[frozenset[str]] = frozenset({"pass", "fail"})
SUBSTRATE_VERDICT_VALUES: Final[frozenset[str]] = frozenset({"pass", "gap"})

# capture_provenance discriminator (DT item 2): a first-class ObservedTrace
# field, NOT metadata. Gates Tier-1 coverage (a seed-legibility trace lacks the
# runtime markers a Tier-1 detector reads, so it cannot fill a Tier-1 cell).
CAPTURE_PROVENANCE_VALUES: Final[frozenset[str]] = frozenset({
    "seed-legibility",
    "instrumented-translation",
})

# Per-param provenance (Q1/Q5). Distinct from comprehension's verdict vocab
# ({loved, hated, ...}) and corpus's divergence vocab.
PROVENANCE_VALUES: Final[frozenset[str]] = frozenset({
    "grounded-from-intent",
    "from-context",
    "filled-from-example",
    "unresolved",
})

# Tier-1 observed-signal markers (TF.2 §5). Recognized field names within an
# ObservedTrace; sparse-or-absent on seed-legibility traces, populated on
# instrumented-translation captures. Validated type-if-present (the schema does
# not force their presence — coverage gating is Step 3's job, not the
# validator's).
_OBSERVED_MARKER_TYPES: Final[dict[str, type | tuple[type, ...]]] = {
    "tool_forced": bool,
    "tools_filtered": int,
    "abort_reason": (str, type(None)),
    "tool_selected": (str, type(None)),
    "outcome": (str, type(None)),
    "observed_graph": list,
    "observed_resolved_params": dict,
}


class SchemaValidationError(ValueError):
    """Raised when a translation_oracle record does not match the v1 schema."""


class SchemaVersionMismatch(ValueError):
    """Raised when a capture file requires a different reader version."""


def _validate_observed_trace(observed: Any) -> None:
    if not isinstance(observed, dict):
        raise SchemaValidationError(
            f"observed must be a dict, got {type(observed).__name__}"
        )
    provenance = observed.get("capture_provenance")
    if provenance is None:
        raise SchemaValidationError(
            "observed.capture_provenance is required"
        )
    if provenance not in CAPTURE_PROVENANCE_VALUES:
        raise SchemaValidationError(
            "observed.capture_provenance must be one of: "
            + ", ".join(sorted(CAPTURE_PROVENANCE_VALUES))
            + f"; got {provenance!r}"
        )
    for field, expected_type in _OBSERVED_MARKER_TYPES.items():
        if field in observed and not isinstance(observed[field], expected_type):
            name = (
                expected_type.__name__
                if isinstance(expected_type, type)
                else "/".join(t.__name__ for t in expected_type)
            )
            raise SchemaValidationError(
                f"observed.{field} must be {name} when present"
            )


def _validate_verdict_pair(pair: Any) -> None:
    if not isinstance(pair, dict):
        raise SchemaValidationError("expected_verdict_pair must be a dict")
    if pair.get("translation") not in TRANSLATION_VERDICT_VALUES:
        raise SchemaValidationError(
            "expected_verdict_pair.translation must be one of: "
            + ", ".join(sorted(TRANSLATION_VERDICT_VALUES))
        )
    if pair.get("substrate") not in SUBSTRATE_VERDICT_VALUES:
        raise SchemaValidationError(
            "expected_verdict_pair.substrate must be one of: "
            + ", ".join(sorted(SUBSTRATE_VERDICT_VALUES))
        )


def _validate_label(label: Any) -> None:
    if not isinstance(label, dict):
        raise SchemaValidationError(
            f"label must be a dict when present, got {type(label).__name__}"
        )
    if not isinstance(label.get("input"), str):
        raise SchemaValidationError("label.input must be a string")
    if not isinstance(label.get("expected_graph"), list):
        raise SchemaValidationError("label.expected_graph must be a list")
    if not isinstance(label.get("expected_params"), dict):
        raise SchemaValidationError("label.expected_params must be a dict")
    # The locked floor (Q1): a present Label MUST carry a verdict-pair, so the
    # oracle can score honest-decline as a success rather than only right/wrong.
    if "expected_verdict_pair" not in label:
        raise SchemaValidationError(
            "label.expected_verdict_pair is required when a label is present"
        )
    _validate_verdict_pair(label["expected_verdict_pair"])
    # world_state: required key for contextual labels, nullable otherwise. The
    # key must exist (so a contextual case can never silently omit it); its
    # value may be null for text-sufficient inputs.
    if "world_state" not in label:
        raise SchemaValidationError("label.world_state key is required (may be null)")
    # expected_provenance: per-param map; each value from the DISTINCT vocab.
    provenance = label.get("expected_provenance", {})
    if not isinstance(provenance, dict):
        raise SchemaValidationError("label.expected_provenance must be a dict")
    for param, value in provenance.items():
        if value not in PROVENANCE_VALUES:
            raise SchemaValidationError(
                f"label.expected_provenance[{param!r}] must be one of: "
                + ", ".join(sorted(PROVENANCE_VALUES))
                + f"; got {value!r}"
            )


def validate_translation_case(record: Any) -> None:
    """Validate one v1 ``TranslationCase``.

    A case is ``{schema_version, observed, label?}``: ``observed`` (an
    ObservedTrace) is REQUIRED; ``label`` is OPTIONAL (absent or null = a 3b /
    unlabeled record). When a label is present it must carry a verdict-pair (the
    locked floor) and a ``world_state`` key.
    """
    if not isinstance(record, dict):
        raise SchemaValidationError(
            f"record must be a dict, got {type(record).__name__}"
        )
    if record.get("schema_version") != SCHEMA_VERSION:
        raise SchemaValidationError(
            f"schema_version must be {SCHEMA_VERSION!r}, "
            f"got {record.get('schema_version')!r}"
        )
    if "observed" not in record:
        raise SchemaValidationError("observed is required")
    _validate_observed_trace(record["observed"])
    label = record.get("label")
    if label is not None:
        _validate_label(label)
