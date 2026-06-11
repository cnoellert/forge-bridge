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

from dataclasses import dataclass
from typing import Any

from forge_bridge.console._vocab_digest import READ_PLANNER_ROLE_NAMES
from forge_bridge.core.vocabulary import STANDARD_ROLES, Status

# Semantic filter args this fence governs. Entity referents are out of scope.
SEMANTIC_FILTER_ARGS: tuple[str, ...] = ("status", "role")

# Read aggregations this fence can ground deterministically. The canonical
# value is the result key the reducer will inspect; aliases are operator
# vocabulary the planner may quote in its declaration.
GROUPABLE_FIELDS: dict[str, tuple[str, ...]] = {
    "sequence_id": ("sequence", "sequence id", "sequence_id", "sequence name"),
    "status": ("status", "state"),
    "role": ("role", "track"),
}
AGGREGATION_INTENTS: frozenset[str] = frozenset({
    "max_by_count",
    "min_by_count",
    "count",
    "count_by",
})


@dataclass(frozen=True)
class GroundedAggregation:
    """A model-declared read aggregation re-derived against bridge vocabulary."""

    intent: str
    group_field: str
    over: str


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


def _resolve_group_field(term: Any) -> str | None:
    """Re-derive a group-by field from operator vocabulary."""
    if not isinstance(term, str):
        return None
    base = term.lower().strip()
    if not base:
        return None
    candidates = (base, base.replace("_", " "), base.replace("-", " "))
    for candidate in candidates:
        for canonical, aliases in GROUPABLE_FIELDS.items():
            if candidate == canonical or candidate in aliases:
                return canonical
    return None


def _aggregation_clarify_question(term: str | None) -> str:
    phrase = f" by {term!r}" if term else ""
    return (
        f"I don't have a way to group shots{phrase} — I can group shots by "
        "status, sequence, or role. Which did you mean?"
    )


def ground_read_aggregation(
    aggregation: Any,
) -> tuple[GroundedAggregation | None, str | None]:
    """Gate a model-declared read aggregation against groupable vocabulary.

    Returns ``(grounded, None)`` when no clarification is needed. ``grounded``
    is ``None`` when the request did not declare an aggregation. Returns
    ``(None, question)`` when the declaration cannot be re-derived.

    The model's claimed ``group_field`` is advisory only: code derives the
    canonical result key from ``group_by`` and cross-checks any claimed field
    against that derivation.
    """
    if aggregation is None:
        return None, None
    if not isinstance(aggregation, dict):
        return None, _aggregation_clarify_question(None)
    if not aggregation:
        return None, None

    intent = aggregation.get("intent")
    over = aggregation.get("over") or "shot"
    group_by = aggregation.get("group_by")
    claimed = aggregation.get("group_field")
    term_label = group_by if isinstance(group_by, str) and group_by.strip() else None

    if intent not in AGGREGATION_INTENTS:
        return None, _aggregation_clarify_question(term_label)
    if over not in ("shot", "shots"):
        return None, _aggregation_clarify_question(term_label)

    derived = _resolve_group_field(group_by)
    claimed_derived = _resolve_group_field(claimed)
    if derived is None:
        return None, _aggregation_clarify_question(term_label)
    if claimed is not None and claimed_derived != derived:
        return None, _aggregation_clarify_question(term_label)

    return GroundedAggregation(
        intent=intent,
        group_field=derived,
        over="shot",
    ), None


def _aggregation_population(chain: list[dict],
                            aggregation: GroundedAggregation) -> list | None:
    if aggregation.over != "shot":
        return None
    for entry in chain:
        result = entry.get("result")
        if isinstance(result, dict) and isinstance(result.get("shots"), list):
            return result["shots"]
    return None


def _field_article(group_field: str) -> str:
    return {
        "sequence_id": "a sequence",
        "status": "a status",
        "role": "a role",
    }.get(group_field, group_field)


def ground_read_aggregation_absence(
    aggregation: GroundedAggregation | None,
    chain: list[dict],
    *,
    project_name: str,
) -> str | None:
    """Return a deterministic all-null grouping answer, or ``None``.

    v1 only owns the uniformly-null/absent grouping guard. If any item has a
    non-null group value, including a partial-null population, narration still
    computes the answer. Populated grouping remains v1.1 territory.
    """
    if aggregation is None:
        return None
    items = _aggregation_population(chain, aggregation)
    if items is None:
        return None

    field_article = _field_article(aggregation.group_field)
    count = len(items)
    if count == 0:
        return f"There are no shots in {project_name} to group by {field_article}."

    values = [
        item.get(aggregation.group_field)
        for item in items
        if isinstance(item, dict) and item.get(aggregation.group_field) is not None
    ]
    values = [value for value in values if str(value).strip()]
    if values:
        return None

    return (
        f"None of {project_name}'s {count} shots are assigned to "
        f"{field_article}."
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
