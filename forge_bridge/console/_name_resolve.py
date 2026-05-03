"""PR29 — Deterministic name-based disambiguation (scoped, exact match).

PR27 surfaces a ``MULTIPLE_PROJECTS`` envelope when the system holds
2+ candidate projects. PR28 lets the caller resolve the ambiguity by
supplying a UUID. PR29 adds a second resolution path: an exact name
match against the SAME candidate list PR27 returned.

Hard constraints (mirror ``_tool_chain`` + ``_param_extract``):

  1. **Scoped to PR27 candidates.** This module never queries upstream
     and never reads from ``_MEMORY``. The candidate list passed in is
     the only source of truth — the same list the caller would see in
     the ``MULTIPLE_PROJECTS`` envelope's ``error.details.candidates``.
  2. **Exact match only.** Case-insensitive (``upper()`` / ``lower()``
     equivalent) and whitespace-trimmed. NO partials, NO substrings,
     NO scoring, NO Levenshtein, NO embeddings.
  3. **Single-match-or-fail.** Zero matches OR two-or-more matches both
     return ``None``. The caller falls through to the existing
     ``MULTIPLE_PROJECTS`` envelope. Ambiguity stays ambiguous — never
     pick the first.
  4. **No LLM involvement.** Pure dict comparison.
  5. **No memory writes.** Same path as the explicit-UUID injection
     (PR28) — caller params don't write to memory by design.
  6. **Defensive on candidate shape.** Skip entries whose ``name`` is
     missing or non-string; use ``id`` as the resolved value.
     Mirrors ``_resolve_project_id``'s strict candidate validation.

Why a separate module rather than a method on the candidate dict:
keeping the matcher standalone makes it trivially unit-testable and
keeps the chat handler's name-resolution branch a single import +
single function call. New future selectors (``project_code=``,
``shot_name=``) can drop in alongside this one without entangling
``_tool_chain`` or ``_param_extract``.
"""
from __future__ import annotations

from typing import Dict, List, Optional


def resolve_name_from_candidates(
    name: str,
    candidates: List[Dict[str, str]],
) -> Optional[str]:
    """Resolve ``project_id`` from ``candidates`` using an exact name match.

    Args:
        name: The user-supplied project name (typically extracted from the
            chat message via ``extract_explicit_params`` — already
            tokenized, but we re-strip + lower-case here for defensive
            robustness against future extractor changes).
        candidates: PR27 disambiguation candidate list. Each entry MUST
            have ``id`` (string); ``name`` is OPTIONAL (entries without
            a string ``name`` are skipped, never matched).

    Returns:
        - The matched candidate's ``id`` (string) when EXACTLY ONE
          candidate's name matches case-insensitively after trimming.
        - ``None`` for every other case: zero matches, two-or-more
          matches, non-string ``name`` input, empty/whitespace-only
          ``name`` input, or any malformed candidate.

    Rules:
      - Match is case-insensitive. ``"alpha"``, ``"Alpha"``, ``"ALPHA"``
        all match a candidate named ``"Alpha"``.
      - Leading and trailing whitespace on the input ``name`` is
        ignored. Inner whitespace IS significant — ``"foo bar"`` does
        not match ``"foobar"``.
      - Candidate names are also trimmed before comparison, so a
        candidate stored as ``" Alpha "`` would match ``"alpha"``.
      - Multiple candidates with the same name → ``None``. We never
        guess. The caller's escape hatch is to switch to a UUID.

    Why ``None`` (not raise): the call site is the chat handler's
    disambiguation branch, where the natural fall-through is the
    existing ``MULTIPLE_PROJECTS`` envelope. Returning ``None`` keeps
    the control flow flat at the call site (``if resolved_id: ...``)
    and avoids exception handling for a perfectly normal "no match"
    state.
    """
    if not isinstance(name, str):
        return None

    target = name.strip().lower()
    if not target:
        return None

    matches = [
        c for c in candidates
        if isinstance(c.get("name"), str)
        and c["name"].strip().lower() == target
    ]

    if len(matches) == 1:
        # ``id`` is the canonical handle the downstream tool consumes.
        # We rely on PR27's strict candidate validation
        # (``_resolve_project_id``) having already enforced ``id`` as a
        # non-empty string before the candidate ever reached us, so a
        # bare dict access here is safe — a malformed entry would have
        # collapsed the entire list to ``None`` upstream.
        return matches[0]["id"]

    return None
