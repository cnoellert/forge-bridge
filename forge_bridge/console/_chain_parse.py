"""PR30 — Deterministic multi-step tool chaining.

The chat handler accepts a message, narrows the tool registry to
exactly one tool (PR14/PR20/PR21), resolves params (PR25–PR29), and
forces execution. PR30 lets the user explicitly chain multiple such
single-step requests in one message using ``->`` as the separator:

    list projects -> list versions project_name=chatTest

Rules (mirror the strict-determinism ethos of PR25–PR29):

  1. **Explicit syntax only.** The chain trigger is the literal token
     ``->``; no ``;``, no ``then``, no natural-language inference.
  2. **Sequential, left-to-right.** No branching, no parallelism, no
     loops. Each step's success is a precondition for the next.
  3. **No LLM planning.** The handler runs each step through the
     existing forced-execution pipeline — same filter, same resolver,
     same execution path as a single-step request.
  4. **Scoped context propagation.** Only ``project_id`` and
     ``shot_id`` flow forward, and ONLY when the previous step's
     result yielded exactly one such value. Multi-value results emit
     no context — better to let the next step disambiguate via PR27
     than to guess which entry is "the answer."
  5. **No memory writes from chain context.** Inherited context flows
     through the resolver as caller params; PR26's "explicit never
     writes memory" contract carries through unchanged.
  6. **Abort on first failure.** Any step error halts the chain — no
     "best effort" partial completion. The trace returns successful
     steps so far + the original error from the failing step.

This module owns ONLY the parsing + context-extraction primitives.
The chain executor (loop, error handling, response shaping) lives in
``handlers.py`` next to the existing single-step path so changes to
the per-step pipeline land in one place.
"""
from __future__ import annotations

from typing import Any, Dict, List


# ── Chain parsing ────────────────────────────────────────────────────────

# The ``->`` separator is the SOLE chain trigger. Other tokens that
# might look chain-like in natural language (``then``, ``and then``,
# ``;``) are intentionally NOT honored — the chain syntax must be
# unmistakable so the parser never has to guess intent. A future
# extension might admit additional separators, but each one must be
# explicitly added here and every constraint in the module docstring
# must continue to hold.
_CHAIN_SEPARATOR = "->"


def parse_chain(message: str) -> List[str]:
    """Split a message into ordered chain steps.

    Rules:
      - Split on ``->``.
      - Trim whitespace on each segment.
      - Drop empty segments (trailing ``->``, leading ``->``, doubled
        separators ``-> ->`` all collapse cleanly).
      - Return the list of trimmed step strings in original order.

    A message with no separator returns a single-element list — the
    chain executor treats ``len == 1`` as "not a chain" and falls
    through to the existing single-step path.

    Defensive on input shape: non-string / empty inputs return ``[]``
    rather than raising, so the caller can branch on length.
    """
    if not isinstance(message, str) or not message:
        return []
    return [s.strip() for s in message.split(_CHAIN_SEPARATOR) if s.strip()]


# ── Chain context extraction ─────────────────────────────────────────────

# Whitelist of context keys the chain may propagate. Each maps from a
# RESULT-shaped key ("projects" / "shots") to the corresponding caller
# PARAM key ("project_id" / "shot_id"). Adding a new propagated key
# requires (a) appending here and (b) confirming the downstream tool's
# requires/PR22 contract surfaces a structured ``MISSING_*`` when the
# key is absent — the chain context is OPTIONAL fill, never a hard
# requirement.
_CHAIN_CONTEXT_KEYS: Dict[str, str] = {
    # result key → param key
    "projects": "project_id",
    "shots": "shot_id",
}


def extract_chain_context(result: Any) -> Dict[str, str]:
    """Extract deterministic context values from a parsed tool result.

    Rules:
      - Inspects only the whitelisted result keys (``projects``,
        ``shots``). Other keys are ignored.
      - For each whitelisted key, extracts the contained entity's
        ``id`` ONLY when the result holds EXACTLY ONE entry. Zero
        entries or multiple entries yield no context (the chain step
        couldn't pick one without guessing).
      - Each extracted entry must be a dict with a non-empty string
        ``id``. Malformed entries are skipped (treated as "no
        propagatable id").
      - Returns a dict of the resulting param keys (``project_id``,
        ``shot_id``). Empty dict means "no context to propagate" —
        the next step will run with only its own caller params.

    Defensive on input shape: non-dict input returns ``{}``. The chain
    executor tolerates this — a step that returned a JSON list or a
    string still completes; it just doesn't seed context for the
    next step.

    DO NOT extend this to read top-level ``id`` fields or unrelated
    keys without a corresponding chain-registry update — silent
    propagation of values the user didn't ask for would re-introduce
    exactly the heuristic chaining PR30 forbids.
    """
    if not isinstance(result, dict):
        return {}

    context: Dict[str, str] = {}
    for result_key, param_key in _CHAIN_CONTEXT_KEYS.items():
        entries = result.get(result_key)
        if not isinstance(entries, list) or len(entries) != 1:
            # Zero or 2+ → ambiguous; skip. Non-list (e.g. None,
            # a dict, a string) → malformed shape; skip.
            continue
        only = entries[0]
        if not isinstance(only, dict):
            continue
        entity_id = only.get("id")
        if not isinstance(entity_id, str) or not entity_id:
            continue
        context[param_key] = entity_id

    return context
