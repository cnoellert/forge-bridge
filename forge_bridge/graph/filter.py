"""Deterministic filter graph primitive.

Flat predicate AST only. No nested predicates, no OR semantics, no
aliases, no normalization, no caching. The node accepts enumeration
collections and returns enumeration collections.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


class PredicateParseError(ValueError):
    """Raised when a filter step cannot be projected into a flat predicate."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class GraphInputError(ValueError):
    """Raised when a graph node receives an invalid graph input shape."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class FilterPredicate:
    """Flat predicate AST consumed by FilterNode."""

    field: str
    operator: str
    value: str | int | float | bool | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"field": self.field, "operator": self.operator}
        if self.operator != "exists":
            data["value"] = self.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FilterPredicate":
        field = data.get("field")
        operator = data.get("operator")
        if not isinstance(field, str) or not field:
            raise PredicateParseError("invalid_predicate", "Predicate field is required.")
        if operator not in _OPERATORS:
            raise PredicateParseError("unknown_operator", f"Unsupported filter operator: {operator!r}")
        return cls(field=field, operator=operator, value=data.get("value"))


_FILTER_INTENT_RE = re.compile(
    r"\b(filter|where)\b|(?<![=])\bonly\b",
    re.IGNORECASE,
)
_FILTER_CALL_RE = re.compile(
    r"(?:\b(?:filter|where|only)\b\s*)+"
    r"(?:\(\s*)?(?P<body>[^)]*?)(?:\s*\))?\s*$",
    re.IGNORECASE,
)
_EXISTS_RE = re.compile(
    r"^(?P<field>[A-Za-z_][A-Za-z0-9_]*)\s+exists$",
    re.IGNORECASE,
)
_PREDICATE_RE = re.compile(
    r"^(?P<field>[A-Za-z_][A-Za-z0-9_]*)\s*"
    r"(?P<operator>>=|<=|==|!=|>|<|contains)\s*"
    r"(?P<value>.+?)$",
    re.IGNORECASE,
)
_OPERATORS = frozenset({"==", "!=", ">", ">=", "<", "<=", "contains", "exists"})
_MUTATION_MARKERS = frozenset({
    "changes",
    "deleted",
    "disconnected",
    "dry_run",
    "opened",
    "previous",
    "proposed_changes",
    "propagated",
    "renamed",
    "shots_assigned",
})
_PREFERRED_COLLECTION_KEYS = (
    "segments",
    "clips",
    "reels",
    "items",
    "iterations",
    "nodes",
    "projects",
    "shots",
    "versions",
    "results",
)


def is_filter_step(text: str) -> bool:
    return bool(isinstance(text, str) and _FILTER_INTENT_RE.search(text))


def parse_filter_step(text: str) -> FilterPredicate:
    """Parse a filter step into a flat predicate AST.

    Unknown shapes fail loud. This is keyword-triggered semantic
    extraction, not a structural query parser.
    """
    if not is_filter_step(text):
        raise PredicateParseError("not_filter_step", "Step is not a filter graph node.")

    stripped_text = text.strip()
    if "((" in stripped_text or "))" in stripped_text:
        raise PredicateParseError(
            "nested_predicate_not_supported",
            "Nested predicates are out of scope.",
        )

    match = _FILTER_CALL_RE.search(stripped_text)
    body = match.group("body").strip() if match else ""
    if not body:
        raise PredicateParseError("unknown_predicate", "No filter predicate found.")
    if re.search(r"\bor\b", body, re.IGNORECASE):
        raise PredicateParseError("or_not_supported", "OR predicates are out of scope.")
    if "(" in body or ")" in body:
        raise PredicateParseError("nested_predicate_not_supported", "Nested predicates are out of scope.")

    exists = _EXISTS_RE.match(body)
    if exists:
        return FilterPredicate(field=exists.group("field"), operator="exists")

    pred = _PREDICATE_RE.match(body)
    if not pred:
        raise PredicateParseError("unknown_predicate", f"Could not parse filter predicate: {body!r}")

    operator = pred.group("operator").lower()
    if operator not in _OPERATORS:
        raise PredicateParseError("unknown_operator", f"Unsupported filter operator: {operator!r}")
    return FilterPredicate(
        field=pred.group("field"),
        operator=operator,
        value=_parse_literal(pred.group("value")),
    )


@dataclass(frozen=True)
class FilterNode:
    """Generic filter node over enumeration collections."""

    predicate: FilterPredicate

    def run(self, data: Any) -> dict[str, Any]:
        key, collection = _extract_enumeration(data)
        filtered = [item for item in collection if self._matches(item)]
        if key is None:
            return {
                "collection": filtered,
                "count": len(filtered),
                "predicate": self.predicate.to_dict(),
            }

        result = dict(data)
        result[key] = filtered
        if isinstance(result.get("count"), int):
            result["count"] = len(filtered)
        result["filter"] = {
            "collection": key,
            "input_count": len(collection),
            "output_count": len(filtered),
            "predicate": self.predicate.to_dict(),
        }
        return result

    def selected_collection(self, data: Any) -> list[dict[str, Any]]:
        key, collection = _extract_enumeration(data)
        if key is None:
            return [item for item in collection if self._matches(item)]
        return [item for item in collection if self._matches(item)]

    def _matches(self, item: dict[str, Any]) -> bool:
        value = item.get(self.predicate.field)
        operator = self.predicate.operator
        if operator == "exists":
            return value not in (None, "")
        if operator == "contains":
            return str(self.predicate.value) in str(value or "")
        if operator == "==":
            return _coerce_comparable(value) == _coerce_comparable(self.predicate.value)
        if operator == "!=":
            return _coerce_comparable(value) != _coerce_comparable(self.predicate.value)
        left = _coerce_number(value)
        right = _coerce_number(self.predicate.value)
        if left is None or right is None:
            return False
        if operator == ">":
            return left > right
        if operator == ">=":
            return left >= right
        if operator == "<":
            return left < right
        if operator == "<=":
            return left <= right
        raise PredicateParseError("unknown_operator", f"Unsupported filter operator: {operator!r}")


def _extract_enumeration(data: Any) -> tuple[str | None, list[dict[str, Any]]]:
    if isinstance(data, list):
        if all(isinstance(item, dict) for item in data):
            return None, data
        raise GraphInputError("invalid_collection", "FilterNode requires list[dict] enumeration input.")

    if not isinstance(data, dict):
        raise GraphInputError("invalid_collection", "FilterNode requires an enumeration collection.")

    if _MUTATION_MARKERS & set(data):
        raise GraphInputError(
            "non_enumeration_input",
            "FilterNode rejects mutation manifests; filter must follow enumeration nodes.",
        )

    for key in _PREFERRED_COLLECTION_KEYS:
        value = data.get(key)
        if isinstance(value, list) and all(isinstance(item, dict) for item in value):
            return key, value

    list_keys = [
        key for key, value in data.items()
        if isinstance(value, list) and all(isinstance(item, dict) for item in value)
    ]
    if len(list_keys) == 1:
        key = list_keys[0]
        return key, data[key]

    raise GraphInputError("invalid_collection", "FilterNode could not find a single list[dict] collection.")


def _parse_literal(value: str) -> str | int | float | bool:
    stripped = value.strip().strip("\"'")
    if stripped.casefold() == "true":
        return True
    if stripped.casefold() == "false":
        return False
    try:
        return int(stripped)
    except ValueError:
        pass
    try:
        return float(stripped)
    except ValueError:
        return stripped


def _coerce_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _coerce_comparable(value: Any) -> Any:
    number = _coerce_number(value)
    if number is not None:
        return number
    if isinstance(value, str):
        folded = value.casefold()
        if folded == "true":
            return True
        if folded == "false":
            return False
        return value
    return value
