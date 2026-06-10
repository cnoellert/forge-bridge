"""Reads-side grounding fence — the deterministic twin of the operation-front
gate (``validate_required_operation_args``).

Doctrine: model declares, code validates. The reads planner DECLARES the filter
terms it grounded (a ``filters`` array alongside its plan); this fence re-derives
every declaration against the *real* vocabulary (``Status.from_string`` / the
role registry) and never trusts the model's claim. A query qualifier that has no
defined status/role meaning ("urgent", "my") must clarify, not get invented into
a filter and stated as fact.

This is the precondition that makes Flame/vision vocab-widening safe: anything
outside the vocabulary clarifies instead of fabricating. It does NOT share code
with the op-front gate — that validates required-arg presence; this validates
semantic grounding. Different jobs, same posture.

Scope: semantic filter args (``status``, ``role``). NOT entity referents
(``project_id`` is Tier-1 referent-resolved upstream). Known limit: a qualifier
the model omits from BOTH the plan and the declaration is not caught — closing
that needs query re-parsing (hand-rolled NLU), out of scope. This fence
deterministically closes the fabrication case and the self-declared-ungrounded
case; that is the v1 boundary.
"""
from __future__ import annotations

from typing import Any

from forge_bridge.console._vocab_digest import READ_PLANNER_ROLE_NAMES
from forge_bridge.core.vocabulary import STANDARD_ROLES, Status

# Semantic filter args this fence governs. Entity referents are out of scope.
SEMANTIC_FILTER_ARGS: tuple[str, ...] = ("status", "role")


def _resolve_status(term: Any) -> str | None:
    """Re-derive the canonical status a term maps to, or ``None``.

    Tries the verbatim phrase, a whitespace->underscore normalization, and each
    whitespace token, so honest verbatim qualifiers like "in review" / "in
    progress" ground while invented terms ("urgent") do not.
    """
    if not isinstance(term, str):
        return None
    base = term.lower().strip()
    if not base:
        return None
    for candidate in (base, base.replace(" ", "_"), *base.split()):
        try:
            return Status.from_string(candidate).value
        except ValueError:
            continue
    return None


def _resolve_role(term: Any) -> str | None:
    """Re-derive the canonical role a term maps to, restricted to the roles the
    reads planner is allowed to filter by (``READ_PLANNER_ROLE_NAMES``)."""
    if not isinstance(term, str):
        return None
    base = term.lower().strip()
    if not base:
        return None
    for token in (base, *base.split()):
        for name in READ_PLANNER_ROLE_NAMES:
            role = STANDARD_ROLES.get(name)
            if role is None:
                continue
            if token == name:
                return role.name
            for key, value in role.aliases.items():
                if key != "role_class" and value.lower() == token:
                    return role.name
    return None


_RESOLVERS = {"status": _resolve_status, "role": _resolve_role}


def _clarify_question(term: str | None) -> str:
    statuses = "/".join(status.value for status in Status)
    roles = "/".join(READ_PLANNER_ROLE_NAMES)
    phrase = f" by {term!r}" if term else ""
    return (
        f"I don't have a way to filter{phrase} — I can filter by status "
        f"({statuses}) or role ({roles}). Which did you mean?"
    )


def ground_read_filters(plan: list, filters: Any) -> str | None:
    """Gate a reads plan against its declared filter grounding.

    Returns ``None`` when everything grounds (the caller proceeds to execute +
    narrate), or a clarify question string when any filter is ungrounded (the
    caller returns it via the existing clarify channel — no execute, no narrate).

    Three checks, all code-enforced:

    1+2. Each declared ``filters`` entry must re-derive: its ``term`` and its
         claimed ``value`` must both resolve to the SAME canonical status/role
         via the real vocabulary. A null arg/value, or a term/value that does
         not re-derive, is ungrounded.
    3.   Cross-check: every semantic filter arg the PLAN sets must be justified
         by a validated declaration (closes the set-the-filter / omit-the-
         declaration hole).
    """
    entries = filters if isinstance(filters, list) else []
    validated: dict[str, set[str]] = {arg: set() for arg in SEMANTIC_FILTER_ARGS}

    # Checks 1+2 — validate each self-declared filter against the vocabulary.
    for entry in entries:
        if not isinstance(entry, dict):
            return _clarify_question(None)
        term = entry.get("term")
        arg = entry.get("arg")
        value = entry.get("value")
        term_label = term if isinstance(term, str) and term.strip() else None
        # Self-declared ungrounded: null arg/value, or an arg we don't govern.
        if arg is None or value is None or arg not in _RESOLVERS:
            return _clarify_question(term_label)
        resolver = _RESOLVERS[arg]
        derived_term = resolver(term)
        derived_value = resolver(value)
        # Code re-derives; the model's claimed mapping is never trusted.
        if (derived_term is None or derived_value is None
                or derived_term != derived_value):
            return _clarify_question(term_label)
        validated[arg].add(derived_term)

    # Check 3 — every plan-set semantic filter arg needs a validated justification.
    for step in plan:
        if not isinstance(step, dict):
            continue
        args = step.get("args")
        if not isinstance(args, dict):
            continue
        for arg in SEMANTIC_FILTER_ARGS:
            if arg not in args:
                continue
            derived = _RESOLVERS[arg](args.get(arg))
            if derived is None or derived not in validated[arg]:
                return _clarify_question(None)

    return None
