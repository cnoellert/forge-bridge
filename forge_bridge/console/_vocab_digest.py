"""Compact first-party vocabulary grounding for the reads planner."""

from __future__ import annotations

from forge_bridge.core.vocabulary import STANDARD_ROLES, Status


READ_PLANNER_ROLE_NAMES: tuple[str, ...] = (
    "grade",
    "comp",
    "roto",
    "denoise",
    "prep",
    "raw",
    "primary",
    "reference",
    "matte",
)

STATUS_ALIASES: dict[str, str] = {
    "proposed": "pending",
    "wip": "in_progress",
    "work_in_progress": "in_progress",
    "ip": "in_progress",
    "pending_review": "review",
    "for_review": "review",
    "final": "delivered",
    "done": "delivered",
    "complete": "delivered",
    "omit": "archived",
    "invalidated": "archived",
}


def _status_line() -> str:
    values = ", ".join(status.value for status in Status)
    aliases = ", ".join(
        f"{alias}->{canonical}"
        for alias, canonical in sorted(STATUS_ALIASES.items())
    )
    return f"- statuses: {values}; aliases: {aliases}"


def _role_line() -> str:
    chunks: list[str] = []
    roles = (
        (name, STANDARD_ROLES[name])
        for name in READ_PLANNER_ROLE_NAMES
        if name in STANDARD_ROLES
    )
    for name, role in sorted(roles, key=lambda item: item[1].order):
        role_class = role.aliases.get("role_class", "role")
        aliases = [
            f"{key}={value}"
            for key, value in sorted(role.aliases.items())
            if key != "role_class"
        ]
        suffix = f"; {', '.join(aliases)}" if aliases else ""
        chunks.append(f"{name}({role_class}{suffix})")
    return "- roles: " + ", ".join(chunks)


def planner_vocabulary_digest() -> str:
    """Return token-tight first-party vocabulary for planner grounding."""
    return "\n".join([
        "VOCABULARY:",
        "- entities: Project -> Sequence -> Shot/Asset -> Version -> Media",
        "- relationships: member_of, version_of, references, peer_of; "
        "Version.parent_type selects Shot or Asset for version_of",
        "- predicate rule: status and role terms below are defined filters; "
        "tool-purpose terms may select tools; unknown or ambiguous filter terms "
        "must clarify, not widen",
        _status_line(),
        _role_line(),
    ])
