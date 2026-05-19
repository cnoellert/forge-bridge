"""Deterministic query-time entity resolution for chat prompts."""
from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


ResolvedEntity = dict[str, str]
ResolvedEntities = dict[str, ResolvedEntity]

_SEQ_CANDIDATE_RE = re.compile(
    r"\b(?P<head>\d+[A-Za-z]{2,})[ _-]?(?P<tail>\d{1,4})\b"
)
_EXPLICIT_ENTITY_RE = re.compile(
    r"\b(?P<label>sequence|reel)\s+"
    r"(?:named\s+|called\s+)?"
    r"(?P<value>[A-Za-z0-9][A-Za-z0-9_ -]*?[A-Za-z0-9])"
    r"(?=\s+(?:to|with|by|and|,)|[?.!]|$)",
    re.IGNORECASE,
)
_PREFIX_PATTERNS = (
    re.compile(
        r"\brename\b.*?\bto\s+[\"']?(?P<prefix>[A-Za-z][A-Za-z0-9_-]*)[\"']?\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bprefix\s+[\"']?(?P<prefix>[A-Za-z][A-Za-z0-9_-]*)[\"']?\b",
        re.IGNORECASE,
    ),
)
_SHOT_NAME_RE = re.compile(
    r"\bshot(?:\s+name)?\s+(?P<shot_name>[A-Za-z][A-Za-z0-9_-]*)\b",
    re.IGNORECASE,
)


def resolve_query_entities(
    query: str,
    *,
    desktop: Mapping[str, Any] | None = None,
) -> ResolvedEntities:
    """Resolve canonical entity arguments from an operator query.

    ``desktop`` is accepted for the eventual live-Flame validation pass. Phase
    24.11 keeps the resolver deterministic and local; when no registry match is
    available, it returns convention-normalized candidates.
    """
    if not isinstance(query, str) or not query.strip():
        return {}

    resolved: ResolvedEntities = {}
    for match in _EXPLICIT_ENTITY_RE.finditer(query):
        label = match.group("label").casefold()
        key = "sequence_name" if label == "sequence" else "reel_name"
        source = _clean_source(match.group("value"))
        seq_match = _SEQ_CANDIDATE_RE.search(source)
        if key == "sequence_name":
            if not seq_match:
                continue
            source = _clean_source(seq_match.group(0))
            value = _canonicalize_sequence_candidate(
                seq_match.group("head"), seq_match.group("tail"),
            )
        else:
            value = _canonicalize_entity_name(source)
        value = _match_known_entity(key, value, desktop) or value
        resolved.setdefault(key, _entity(value=value, source=source))

    if "sequence_name" not in resolved:
        match = _SEQ_CANDIDATE_RE.search(query)
        if match:
            source = _clean_source(match.group(0))
            value = _canonicalize_sequence_candidate(
                match.group("head"), match.group("tail"),
            )
            value = _match_known_entity("sequence_name", value, desktop) or value
            resolved["sequence_name"] = _entity(value=value, source=source)

    for prefix_pattern in _PREFIX_PATTERNS:
        prefix_match = prefix_pattern.search(query)
        if prefix_match:
            prefix = prefix_match.group("prefix").strip()
            resolved.setdefault("prefix", _entity(value=prefix, source=prefix))
            break

    shot_match = _SHOT_NAME_RE.search(query)
    if shot_match:
        shot_name = shot_match.group("shot_name").strip()
        resolved.setdefault("shot_name", _entity(value=shot_name, source=shot_name))

    return resolved


def resolved_entity_params(resolved: Mapping[str, Mapping[str, str]]) -> dict[str, str]:
    """Return the flat argument map suitable for forced tool execution."""
    params: dict[str, str] = {}
    for key, item in resolved.items():
        value = item.get("value")
        if isinstance(value, str) and value:
            params[key] = value
    return params


def enrich_user_message_with_resolved_entities(
    user_query: str,
    resolved: Mapping[str, Mapping[str, str]],
) -> str:
    """Prepend the resolved-entities context block to a user message."""
    if not resolved:
        return user_query

    lines = ["[Resolved entities from query]"]
    for key in sorted(resolved):
        item = resolved[key]
        value = item.get("value", "")
        source = item.get("source", "")
        if source and source != value:
            lines.append(f'{key}: "{value}"  (normalized from "{source}")')
        else:
            lines.append(f'{key}: "{value}"')
    lines.extend(["", f"User query: {user_query}"])
    return "\n".join(lines)


def enrich_messages_with_resolved_entities(
    messages: list[dict[str, Any]],
    resolved: Mapping[str, Mapping[str, str]],
) -> list[dict[str, Any]]:
    """Return a copy with the last user message enriched for the LLM path."""
    if not resolved:
        return messages

    enriched = [dict(message) for message in messages]
    for index in range(len(enriched) - 1, -1, -1):
        message = enriched[index]
        if message.get("role") != "user" or not isinstance(message.get("content"), str):
            continue
        message["content"] = enrich_user_message_with_resolved_entities(
            message["content"], resolved,
        )
        return enriched
    return enriched


def _entity(*, value: str, source: str) -> ResolvedEntity:
    return {"value": value, "source": source}


def _clean_source(value: str) -> str:
    return " ".join(value.strip().strip("\"'").split())


def _canonicalize_entity_name(value: str) -> str:
    compact = _clean_source(value)
    seq_match = _SEQ_CANDIDATE_RE.fullmatch(compact)
    if seq_match:
        return _canonicalize_sequence_candidate(
            seq_match.group("head"), seq_match.group("tail"),
        )
    return re.sub(r"\s+", "_", compact.strip())


def _canonicalize_sequence_candidate(head: str, tail: str) -> str:
    return f"{head.casefold()}_{tail}"


def _match_known_entity(
    key: str,
    value: str,
    desktop: Mapping[str, Any] | None,
) -> str | None:
    if not desktop:
        return None

    names = _known_names_for(key, desktop)
    folded = value.casefold().replace(" ", "_")
    for name in names:
        normalized = _canonicalize_entity_name(str(name))
        if normalized.casefold() == folded:
            return normalized
    return None


def _known_names_for(key: str, desktop: Mapping[str, Any]) -> list[Any]:
    candidates: list[Any] = []
    if key == "sequence_name":
        candidates.extend(_extract_names(desktop.get("sequences")))
        candidates.extend(_extract_names(desktop.get("sequence_names")))
    elif key == "reel_name":
        candidates.extend(_extract_names(desktop.get("reels")))
        candidates.extend(_extract_names(desktop.get("reel_names")))
    return candidates


def _extract_names(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        name = value.get("name") or value.get("sequence_name") or value.get("reel_name")
        return [name] if name else []
    if isinstance(value, (list, tuple)):
        names: list[Any] = []
        for item in value:
            names.extend(_extract_names(item))
        return names
    return []
