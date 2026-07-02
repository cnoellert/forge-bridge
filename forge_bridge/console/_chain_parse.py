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
     Formatter terminal steps are the one additional path: the immediate
     previous result is passed privately as ``format_result.data`` only when
     the next selected tool is ``format_result``.
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

from typing import List


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
      - Split on ``->`` only at top-level parenthesis depth.
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
    steps: list[str] = []
    start = 0
    depth = 0
    index = 0
    while index < len(message):
        char = message[index]
        if char == "(":
            depth += 1
            index += 1
            continue
        if char == ")":
            depth = max(0, depth - 1)
            index += 1
            continue
        if depth == 0 and message.startswith(_CHAIN_SEPARATOR, index):
            step = message[start:index].strip()
            if step:
                steps.append(step)
            index += len(_CHAIN_SEPARATOR)
            start = index
            continue
        index += 1

    step = message[start:].strip()
    if step:
        steps.append(step)
    return steps


# ── Chain context extraction ─────────────────────────────────────────────

# ``extract_chain_context`` now has its single canonical author in the graph
# layer (`forge_bridge.graph.extract`) so the graph-native ``ExtractContextNode``
# can share it without importing "up" into ``console/``. Re-exported here so the
# legacy chain path (`_step.py`) and its tests keep importing it from this module
# byte-identically.
from forge_bridge.graph.extract import extract_chain_context  # noqa: E402,F401
