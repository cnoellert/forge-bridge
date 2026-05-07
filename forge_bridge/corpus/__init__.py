"""forge_bridge.corpus — Layer 1 divergence corpus capture (Gate 1 skeleton).

PR 1 of the A.5.3.2 Gate 1 implementation sequence. Establishes the
package skeleton, the public API, the env-var gate, and the schema
validator. Capture invocation, identity hashes, topology snapshots,
the runtime probe writer, and call-site integration are deferred to
subsequent PRs (per ``A.5.3.2-GATE-1-SPEC.md`` §9).

Discipline check: if PR 1 is the only thing that ever lands, daemon
observable behavior is unchanged. No call sites import this package;
the env var defaults to disabled; the public emit function raises
NotImplementedError if called (rather than silently no-op'ing) so
accidental integration before PR 3 fails loudly.

See:

  - ``A.5.3.2-GATE-1-SPEC.md`` — binding spec for Gate 1.
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
    validate_capture_record,
)
from forge_bridge.corpus.reader import read_capture_file

__all__ = [
    "SCHEMA_VERSION",
    "SchemaValidationError",
    "divergence_capture_enabled",
    "emit_divergence_capture",
    "read_capture_file",
    "validate_capture_record",
]
