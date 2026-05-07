"""forge_bridge.corpus._capture — Layer 1 divergence corpus capture.

Capture is emitted after arbitration decisions are finalized and must not structurally participate in the arbitration pipeline.

This module implements the runtime probe (env-var-gated) and the
test-fixture path that emits Layer 1 records per the A.5.3.2
instrument contract. The contract's structural invariants
(``A.5.3.2-INSTRUMENT-CONTRACT.md`` §2.2) are enforced here:

  - I-1: append-only writer; never mutates existing records.
  - I-2: records carry observations only; no outcome labels.
  - I-3: this module is imported by daemon code paths but only
         performs disk writes — no LLM calls, no comparator logic.

See ``A.5.3.2-INSTRUMENT-CONTRACT.md`` §3 for the canonical record
shape and ``A.5.3.2-GATE-1-SPEC.md`` §5 for the capture-invocation
contract this module implements.

PR 1 status: env-var gate implemented; ``emit_divergence_capture`` is
a stub that raises NotImplementedError. Capture builder + writer land
in PR 3.
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Per A.5.3.2-GATE-1-SPEC.md §6.
_ENV_VAR = "FORGE_BRIDGE_DIVERGENCE_CAPTURE"
_TRUTHY = frozenset({"1", "true", "yes"})
_FALSY = frozenset({"", "0", "false", "no"})

# Module state for one-time WARNING per unique invalid env-var value.
#
# Process-local by design. The warning is a UX nicety — surface typo'd
# env values without log spam — not a correctness mechanism. The set
# is shared across all callers within the process; in the daemon
# (single-threaded asyncio) this is safe without a lock because
# ``divergence_capture_enabled`` does not ``await`` between the
# membership check and the ``add()``. It is NOT safe for multi-
# threaded use, but the daemon does not use threads in the
# arbitration path.
#
# Test isolation: tests that exercise the invalid-value warning
# behavior must request the ``clean_warning_state`` fixture from
# ``tests/corpus/conftest.py``. Without it, prior tests in the same
# pytest process leave the set populated and the "warns once per
# unique value" assertion becomes order-dependent.
_warned_invalid_values: set[str] = set()


def divergence_capture_enabled() -> bool:
    """True iff the env-var gate is set to a recognized truthy value.

    Read at call time (not cached) so daemon restart is the supported
    way to flip the gate. Invalid values are treated as disabled and
    log a one-time WARNING per unique invalid value seen — avoids
    silent enablement on typo'd values without spamming the log.

    See ``A.5.3.2-GATE-1-SPEC.md`` §6 for the accepted value list.
    """
    raw = os.environ.get(_ENV_VAR, "")
    norm = raw.strip().lower()

    if norm in _TRUTHY:
        return True
    if norm in _FALSY:
        return False

    if raw not in _warned_invalid_values:
        _warned_invalid_values.add(raw)
        logger.warning(
            "%s=%r is not a recognized truthy/falsy value; "
            "treating as disabled. Accepted truthy: %s. "
            "Accepted falsy: %s.",
            _ENV_VAR, raw,
            sorted(_TRUTHY),
            sorted(v for v in _FALSY if v),
        )
    return False


def emit_divergence_capture(
    *,
    prompt: str,
    candidate_set_post_reachability: list[Any],
    candidate_set_post_pr14: list[Any],
    narrower_decision: list[Any],
    pr20_fired: bool,
    collapse_occurred: bool,
    ambiguity_state: str,
    narrower_latency_ms: float,
    source: str,
) -> None:
    """Fire-and-forget Layer 1 capture. See module docstring for the
    crystallizing sentence and architectural intent.

    PR 1 stub: raises NotImplementedError. The capture builder + writer
    land in PR 3. Stub-as-error rather than stub-as-noop is intentional
    — accidental integration before PR 3 fails loudly rather than
    silently dropping records.
    """
    raise NotImplementedError(
        "emit_divergence_capture is a PR 1 skeleton stub; the capture "
        "builder + writer land in PR 3. Do not integrate into call "
        "sites yet — the two arbitration call sites are added in PR 4 "
        "(chat handler) and PR 5 (chain step)."
    )
