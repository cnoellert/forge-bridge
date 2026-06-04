"""Context Pressure Instrument (Phase X) — operator-pressure capture corpus.

A FOURTH measurement instrument, distinct from comprehension/ (CR.1), corpus/
(v1.6 divergence), and translation_oracle/ (TF.3): own ``__all__``, own versioned
schema, net-new authored vocabulary. Captures operator intent paired with live
desktop world-state so contextual-resolution failures become analyzable — the
evidence that justifies (or rejects) future desktop-contextual-resolution work.

Captured facts vs authored analysis are locked apart (the TranslationCase lock,
one instrument downstream): ``build_record`` cannot author; only a distinct
later pass writes ``analysis``.
"""
from forge_bridge.context_pressure._analysis import (
    SEED_DIR,
    author_analysis,
    flag_contextual_failure_candidates,
    resolvable_delta,
)
from forge_bridge.context_pressure._capture import (
    append_record,
    build_record,
    read_records,
)
from forge_bridge.context_pressure._schema import (
    CONTEXT_SOURCE_VALUES,
    FAILURE_CLASS_VALUES,
    OUTCOME_VALUES,
    SCHEMA_VERSION,
    SchemaValidationError,
    SchemaVersionMismatch,
    validate_context_pressure_record,
)

__all__ = [
    "CONTEXT_SOURCE_VALUES",
    "FAILURE_CLASS_VALUES",
    "OUTCOME_VALUES",
    "SCHEMA_VERSION",
    "SEED_DIR",
    "SchemaValidationError",
    "SchemaVersionMismatch",
    "append_record",
    "author_analysis",
    "build_record",
    "flag_contextual_failure_candidates",
    "read_records",
    "resolvable_delta",
    "validate_context_pressure_record",
]
