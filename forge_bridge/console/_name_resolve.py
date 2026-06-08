"""PR29/CR.2 — Deterministic name-based disambiguation (scoped).

PR27 established the project candidate set when the system holds 2+
candidate projects. PR28 lets the caller resolve the ambiguity by
supplying a UUID. PR29 adds a second resolution path against that SAME
candidate list. CR.2 relaxes the matcher for natural follow-up replies:
exact first, then unique prefix, then unique substring.

Hard constraints (mirror ``_tool_chain`` + ``_param_extract``):

  1. **Scoped to PR27 candidates.** This module never queries upstream
     and never reads from ``_MEMORY``. The candidate list passed in is
     the only source of truth — the same list the caller sees in the
     CR.2 ``clarification_needed`` envelope.
  2. **Deterministic scoped match.** Case-insensitive and whitespace-
     trimmed. Exact match first; if none, unique prefix; if none, unique
     substring. NO scoring, NO Levenshtein, NO embeddings.
  3. **Single-match-or-fail.** Zero matches OR two-or-more matches both
     return ``None``. The caller keeps ambiguity as a continuation prompt
     rather than guessing.
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
    """Resolve an id from ``candidates`` using deterministic scoped matching.

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
      - Leading and trailing whitespace on the input ``name`` is ignored.
        Exact match is attempted first. If that fails, a unique prefix or
        unique substring against the held candidate set may resolve.
      - Candidate names are also trimmed before comparison, so a
        candidate stored as ``" Alpha "`` would match ``"alpha"``.
      - Multiple candidates with the same name → ``None``. We never
        guess. The caller's escape hatch is to switch to a UUID.

    Why ``None`` (not raise): the call site is the chat handler's
    disambiguation branch, where the natural fall-through is the CR.2
    continuation prompt. Returning ``None`` keeps the control flow flat
    at the call site (``if resolved_id: ...``) and avoids exception
    handling for a perfectly normal "no match" state.
    """
    if not isinstance(name, str):
        return None

    target = name.strip().lower()
    if not target:
        return None

    valid = [
        c for c in candidates
        if isinstance(c.get("name"), str)
        and isinstance(c.get("id"), str)
        and c["id"]
    ]

    matches = [
        c for c in valid
        if c["name"].strip().lower() == target
    ]
    if not matches:
        matches = [
            c for c in valid
            if c["name"].strip().lower().startswith(target)
        ]
    if not matches:
        matches = [
            c for c in valid
            if target in c["name"].strip().lower()
        ]

    if len(matches) == 1:
        # ``id`` is the canonical handle the downstream tool consumes.
        return matches[0]["id"]

    return None
