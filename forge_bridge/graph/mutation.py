"""Mutation manifest wire contract."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ChangeRecord:
    identity: dict[str, Any]
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity": dict(self.identity),
            "payload": dict(self.payload),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChangeRecord":
        return cls(
            identity=dict(data["identity"]),
            payload=dict(data["payload"]),
        )


@dataclass(frozen=True)
class MutationManifest:
    """Self-describing mutation plan with declared apply authority."""

    type: str
    intent_parameters: dict[str, Any]
    resolved_plan: tuple[ChangeRecord, ...]
    originating_capability: str
    apply_counterpart: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "intent_parameters": dict(self.intent_parameters),
            "resolved_plan": [item.to_dict() for item in self.resolved_plan],
            "originating_capability": self.originating_capability,
            "apply_counterpart": {
                "tool": self.apply_counterpart["tool"],
                "parameter_overrides": dict(
                    self.apply_counterpart["parameter_overrides"],
                ),
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MutationManifest":
        error = validate_mutation_manifest(data)
        if error is not None:
            raise error
        return cls(
            type=data["type"],
            intent_parameters=dict(data["intent_parameters"]),
            resolved_plan=tuple(
                ChangeRecord.from_dict(item)
                for item in data["resolved_plan"]
            ),
            originating_capability=data["originating_capability"],
            apply_counterpart={
                "tool": data["apply_counterpart"]["tool"],
                "parameter_overrides": dict(
                    data["apply_counterpart"]["parameter_overrides"],
                ),
            },
        )


class MutationManifestError(ValueError):
    code = "MUTATION_MANIFEST_INVALID"

    def __init__(
        self,
        *,
        reason: str,
        field_path: str,
        expected: str | None = None,
    ) -> None:
        self.reason = reason
        self.field_path = field_path
        self.expected = expected
        message = f"{field_path}: {reason}"
        if expected is not None:
            message = f"{message}; expected {expected}"
        super().__init__(message)
        self.message = message

    def to_error(self) -> dict[str, Any]:
        error = {
            "type": self.code,
            "message": self.message,
            "reason": self.reason,
            "field_path": self.field_path,
        }
        if self.expected is not None:
            error["expected"] = self.expected
        return error


def validate_mutation_manifest(value: Any) -> MutationManifestError | None:
    """Return a structural error for invalid mutation-plan wire values."""
    if isinstance(value, MutationManifest):
        value = value.to_dict()
    if not isinstance(value, dict):
        return MutationManifestError(
            reason="not_a_dict",
            field_path="",
            expected="dict",
        )

    missing = _missing(value, "type")
    if missing is not None:
        return missing
    if value["type"] != "mutation_plan":
        return MutationManifestError(
            reason="wrong_type_string",
            field_path="type",
            expected='"mutation_plan"',
        )

    missing = _missing(value, "intent_parameters")
    if missing is not None:
        return missing
    if not isinstance(value["intent_parameters"], dict):
        return MutationManifestError(
            reason="not_a_dict",
            field_path="intent_parameters",
            expected="dict",
        )

    missing = _missing(value, "resolved_plan")
    if missing is not None:
        return missing
    plan = value["resolved_plan"]
    if not isinstance(plan, (list, tuple)):
        return MutationManifestError(
            reason="wrong_type_sequence",
            field_path="resolved_plan",
            expected="list or tuple",
        )
    for index, item in enumerate(plan):
        if isinstance(item, ChangeRecord):
            item = item.to_dict()
        item_path = f"resolved_plan[{index}]"
        if not isinstance(item, dict):
            return MutationManifestError(
                reason="not_a_dict",
                field_path=item_path,
                expected="dict",
            )
        missing = _missing(item, "identity", parent_path=item_path)
        if missing is not None:
            return missing
        if not isinstance(item["identity"], dict):
            return MutationManifestError(
                reason="not_a_dict",
                field_path=f"{item_path}.identity",
                expected="dict",
            )
        missing = _missing(item, "payload", parent_path=item_path)
        if missing is not None:
            return missing
        if not isinstance(item["payload"], dict):
            return MutationManifestError(
                reason="not_a_dict",
                field_path=f"{item_path}.payload",
                expected="dict",
            )

    missing = _missing(value, "originating_capability")
    if missing is not None:
        return missing
    if not _non_empty_str(value["originating_capability"]):
        return MutationManifestError(
            reason="wrong_type_string",
            field_path="originating_capability",
            expected="non-empty string",
        )

    missing = _missing(value, "apply_counterpart")
    if missing is not None:
        return missing
    apply = value["apply_counterpart"]
    if not isinstance(apply, dict):
        return MutationManifestError(
            reason="not_a_dict",
            field_path="apply_counterpart",
            expected="dict",
        )
    missing = _missing(apply, "tool", parent_path="apply_counterpart")
    if missing is not None:
        return missing
    if not _non_empty_str(apply["tool"]):
        return MutationManifestError(
            reason="wrong_type_string",
            field_path="apply_counterpart.tool",
            expected="non-empty string",
        )
    missing = _missing(apply, "parameter_overrides", parent_path="apply_counterpart")
    if missing is not None:
        return missing
    if not isinstance(apply["parameter_overrides"], dict):
        return MutationManifestError(
            reason="not_a_dict",
            field_path="apply_counterpart.parameter_overrides",
            expected="dict",
        )

    return None


def _missing(
    value: dict[str, Any],
    key: str,
    *,
    parent_path: str | None = None,
) -> MutationManifestError | None:
    if key in value:
        return None
    return MutationManifestError(
        reason="missing",
        field_path=f"{parent_path}.{key}" if parent_path else key,
    )


def _non_empty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value)
