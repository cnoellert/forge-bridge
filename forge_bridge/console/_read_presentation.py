"""Deterministic presentation for validated pure-enumeration reads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GroundedListPresentation:
    """A planner declaration narrowed to a substrate-owned renderer."""

    entity: str
    field: str
    collection_key: str


@dataclass(frozen=True)
class DeterministicReadRender:
    """Rendered operator text plus machine-readable completeness evidence."""

    text: str
    evidence: dict[str, Any]


def ground_read_presentation(value: Any) -> GroundedListPresentation | None:
    """Validate the v1 pure-enumeration declaration.

    Unknown or malformed declarations are ineligible for deterministic rendering;
    callers retain the normal narrator fallback. The collection key is derived by
    Bridge and is never accepted from planner output.
    """
    if not isinstance(value, dict):
        return None
    if value.get("kind") != "list" or value.get("scope") != "all":
        return None
    entity = value.get("entity")
    field = value.get("field")
    if entity not in {"shot", "shots"} or field != "name":
        return None
    return GroundedListPresentation(
        entity="shot",
        field="name",
        collection_key="shots",
    )


def _normalized_label(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return " ".join(value.split()).strip() or None


def render_read_presentation(
    presentation: GroundedListPresentation | None,
    chain: list[dict],
) -> DeterministicReadRender | None:
    """Render one complete shot-name population without a narration call."""
    if presentation is None:
        return None
    if len(chain) != 1:
        return None

    populations: list[tuple[int, list[Any]]] = []
    for index, entry in enumerate(chain):
        if not isinstance(entry, dict):
            continue
        step = entry.get("step")
        result = entry.get("result")
        if not isinstance(step, str) or not step.startswith("forge_list_shots("):
            continue
        if not isinstance(result, dict):
            continue
        if "error" in result:
            continue
        items = result.get(presentation.collection_key)
        if isinstance(items, list):
            declared_count = result.get("count")
            if (
                isinstance(declared_count, int)
                and not isinstance(declared_count, bool)
                and declared_count != len(items)
            ):
                continue
            populations.append((index, items))

    if len(populations) != 1:
        return None

    source_step_index, items = populations[0]
    labels: list[str] = []
    missing_count = 0
    for item in items:
        label = (
            _normalized_label(item.get(presentation.field))
            if isinstance(item, dict)
            else None
        )
        if label is None:
            missing_count += 1
        else:
            labels.append(label)

    if not items:
        text = "No shots found."
    elif not labels:
        text = f"No shot names were present in the {len(items)} shot records."
    else:
        count_text = f"{len(labels)}"
        if missing_count:
            count_text += f" named, {missing_count} unnamed"
        text = f"Shot names ({count_text}):\n" + "\n".join(
            f"- {label}" for label in labels
        )

    return DeterministicReadRender(
        text=text,
        evidence={
            "kind": "deterministic_list",
            "entity": presentation.entity,
            "field": presentation.field,
            "scope": "all",
            "source_step_index": source_step_index,
            "total_items": len(items),
            "rendered_items": len(labels),
            "missing_items": missing_count,
            "source_population_complete": True,
            "all_requested_values_present": missing_count == 0,
        },
    )
