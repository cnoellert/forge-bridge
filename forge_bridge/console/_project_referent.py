"""Deterministic grounding for an explicitly named project referent."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


_WORD_RE = re.compile(r"[^\W_]+", flags=re.UNICODE)


@dataclass(frozen=True)
class ExactProjectReferent:
    """A unique full project-name mention grounded to its registry id."""

    id: str
    name: str

    def as_project(self) -> dict[str, str]:
        return {"id": self.id, "name": self.name}


def _tokens(value: str) -> tuple[str, ...]:
    return tuple(match.group(0).casefold() for match in _WORD_RE.finditer(value))


def _contains_phrase(
    message_tokens: tuple[str, ...],
    name_tokens: tuple[str, ...],
) -> bool:
    width = len(name_tokens)
    return any(
        message_tokens[index:index + width] == name_tokens
        for index in range(len(message_tokens) - width + 1)
    )


def resolve_exact_project_referent(
    message: Any,
    projects: list[dict],
) -> ExactProjectReferent | None:
    """Resolve one full project name explicitly present in ``message``.

    Matching is case-insensitive and token-boundary exact. If registered names
    nest, the longest full name wins. Duplicate longest matches remain ambiguous.
    Prefixes, substrings, and conversation history are intentionally out of scope.
    """
    if not isinstance(message, str):
        return None
    message_tokens = _tokens(message)
    if not message_tokens:
        return None

    matches: list[tuple[int, ExactProjectReferent]] = []
    for project in projects:
        if not isinstance(project, dict):
            continue
        project_id = project.get("id")
        name = project.get("name")
        if not isinstance(project_id, str) or not project_id:
            continue
        if not isinstance(name, str) or not name.strip():
            continue
        name_tokens = _tokens(name)
        if name_tokens and _contains_phrase(message_tokens, name_tokens):
            matches.append((
                len(name_tokens),
                ExactProjectReferent(id=project_id, name=name.strip()),
            ))

    if not matches:
        return None
    longest = max(width for width, _ in matches)
    most_specific = {
        referent.id: referent
        for width, referent in matches
        if width == longest
    }
    if len(most_specific) != 1:
        return None
    return next(iter(most_specific.values()))
