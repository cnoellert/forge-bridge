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
  4. **Scoped context propagation (PR32).** At most **one** caller
     param flows forward from the previous step's parsed result:
     ``project_id``, ``shot_id``, or ``version_id``, chosen by strict
     priority (``projects`` list → ``shots`` → ``versions``), each only
     when that list holds exactly one well-formed ``{id: str}``.
     Multi-value lists emit no context for that key — better to let
     the next step disambiguate via PR27 than to guess.
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


def extract_chain_context(result: Any) -> Dict[str, str]:
    """Deterministically extract a single context parameter from a tool result.

    Priority (first match wins — no multi-key merge):

      1. ``projects`` → ``project_id``
      2. ``shots`` → ``shot_id``
      3. ``versions`` → ``version_id``

    Rules:

      - Only propagate when exactly **one** item exists in the list.
      - Item must be a dict with a non-empty string ``id`` (after strip).
      - Return immediately on the first qualifying key; otherwise ``{}``.

    Defensive on input shape: non-dict input returns ``{}``.
    """
    if not isinstance(result, dict):
        return {}

    def _single_id(lst: Any) -> str | None:
        if (
            isinstance(lst, list)
            and len(lst) == 1
            and isinstance(lst[0], dict)
        ):
            _id = lst[0].get("id")
            if isinstance(_id, str) and _id.strip():
                return _id
        return None

    _id = _single_id(result.get("projects"))
    if _id is not None:
        return {"project_id": _id}

    _id = _single_id(result.get("shots"))
    if _id is not None:
        return {"shot_id": _id}

    _id = _single_id(result.get("versions"))
    if _id is not None:
        return {"version_id": _id}

    return {}
