"""forge_bridge.corpus — Layer 1 divergence corpus capture.

PR 1 + PR 2 + PR 3 of the A.5.3.2 Gate 1 implementation sequence.
Establishes the package skeleton, public API, env-var gate, schema
validator, identity helpers, topology snapshot, capture builder,
JSONL writer, and reader. Call-site integration (chat handler in
PR 4, chain step in PR 5) remains future work.

Discipline check (PR 3): the writer + reader are real
implementations, but no production code path imports this package.
The env var defaults to disabled. The structural asymmetry — ship
persistence, do not yet introduce institutional memory into the
running daemon — is the load-bearing PR 3 property and is enforced
by ``tests/corpus/test_pr3_discipline.py`` (zero production imports
of ``forge_bridge.corpus`` outside the package).

See:

  - ``A.5.3.2-GATE-1-SPEC.md`` — binding spec for Gate 1.
  - ``A.5.3.2-PR3-SPEC.md`` — binding spec for PR 3 (writer +
    reader + atomic-append discipline + corruption locality).
  - ``A.5.3.2-INSTRUMENT-CONTRACT.md`` — instrument shape +
    structural invariants.
  - ``A.5.3.2-FRAMING.md`` — phase shape + objective lock.
"""
from forge_bridge.corpus._capture import (
    divergence_capture_enabled,
    emit_divergence_capture,
)
from forge_bridge.corpus._schema import (
    SCHEMA_VERSION,
    SchemaValidationError,
    SchemaVersionMismatch,
    validate_capture_record,
)
from forge_bridge.corpus.reader import read_capture_file

__all__ = [
    "SCHEMA_VERSION",
    "SchemaValidationError",
    "SchemaVersionMismatch",
    "divergence_capture_enabled",
    "emit_divergence_capture",
    "read_capture_file",
    "validate_capture_record",
]
