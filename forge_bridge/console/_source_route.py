"""Source-routing helpers for compiled read graphs."""
from __future__ import annotations

import re
from typing import Any

from forge_bridge.llm.resolver import resolve_query_entities


_SHOT_ENTITY_READ_TOOLS = frozenset({
    "forge_get_shot",
    "forge_get_shot_stack",
    "forge_get_shot_versions",
    "forge_get_shot_lineage",
    "forge_list_shots",
})
_SEQUENCE_WITH_QUALIFIER_RE = re.compile(
    r"\b(?P<head>\d+[A-Za-z]{2,})(?:[_ -][A-Za-z]+)?[ _-](?P<tail>\d{1,4})\b"
)


def _tool_name(tool: Any) -> str | None:
    if isinstance(tool, dict):
        value = tool.get("name")
    else:
        value = getattr(tool, "name", None)
    return value if isinstance(value, str) and value else None


def _first_token(step: str) -> str:
    return step.split(maxsplit=1)[0] if step.strip() else ""


def _sequence_reference(user_prompt: str) -> str | None:
    entities = resolve_query_entities(user_prompt)
    sequence = entities.get("sequence_name")
    if isinstance(sequence, dict):
        source = sequence.get("source")
        if isinstance(source, str) and source.strip():
            return source.strip()
        value = sequence.get("value")
        if isinstance(value, str) and value.strip():
            return value.strip()

    match = _SEQUENCE_WITH_QUALIFIER_RE.search(user_prompt)
    if match:
        return match.group(0).strip()
    return None


def apply_source_routing(user_prompt: str, steps: list[str], tools: list) -> list[str]:
    """Route sequence-scoped forge shot reads to Flame sequence segment reads."""
    sequence_ref = _sequence_reference(user_prompt)
    if sequence_ref is None:
        return steps

    tool_names = {_tool_name(tool) for tool in tools}
    if "flame_get_sequence_segments" not in tool_names:
        return steps

    routed: list[str] = []
    for step in steps:
        tool_name = _first_token(step)
        if tool_name in _SHOT_ENTITY_READ_TOOLS:
            routed.append(f"flame_get_sequence_segments {sequence_ref}")
        else:
            routed.append(step)
    return routed
