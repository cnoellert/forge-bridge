"""Translation-fidelity oracle (TF.3a) — the labeled reference corpus, frozen
observed traces, detectors, and the verdict-pair oracle.

A THIRD measurement instrument, distinct from ``comprehension/`` (CR.1) and
``corpus/`` (v1.6 divergence): own ``__all__``, own versioned schema, net-new
label vocabularies. See ``_schema`` for the architectural lock (ObservedTrace
required, Label optional — the TF.3a/TF.3b boundary).
"""
from forge_bridge.translation_oracle._capture import (
    capture_observed_trace,
    observed_trace_from_compile_outcome,
)
from forge_bridge.translation_oracle._schema import (
    CAPTURE_PROVENANCE_VALUES,
    PROVENANCE_VALUES,
    SCHEMA_VERSION,
    SUBSTRATE_VERDICT_VALUES,
    TRANSLATION_VERDICT_VALUES,
    SchemaValidationError,
    SchemaVersionMismatch,
    validate_translation_case,
)

__all__ = [
    "CAPTURE_PROVENANCE_VALUES",
    "PROVENANCE_VALUES",
    "SCHEMA_VERSION",
    "SUBSTRATE_VERDICT_VALUES",
    "TRANSLATION_VERDICT_VALUES",
    "SchemaValidationError",
    "SchemaVersionMismatch",
    "capture_observed_trace",
    "observed_trace_from_compile_outcome",
    "validate_translation_case",
]
