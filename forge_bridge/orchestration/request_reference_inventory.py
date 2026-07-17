"""Bridge-owned request reference facts and feasibility policy.

The inputs catalog is persisted as JSON, but planning needs a stable typed operand
for generation declarations' ``ReferenceRequirementSpec``.  This module derives
that operand without importing a sibling's feasibility oracle: contracts provide
source facts, while Bridge owns the hard-block judgment.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

from forge_contracts.generation import ReferenceRequirementSpec

_IMAGE_ARTIFACT_TYPES = frozenset(
    {
        "frame",
        "image",
        "image_sequence",
        "plate",
        "raster",
        "still",
    }
)
_IMAGE_SUFFIXES = frozenset(
    {
        ".bmp",
        ".cin",
        ".dpx",
        ".exr",
        ".gif",
        ".heic",
        ".jpeg",
        ".jpg",
        ".png",
        ".tif",
        ".tiff",
        ".webp",
    }
)


@dataclass(frozen=True)
class RequestReferenceInventory:
    """Typed facts about references supplied by one planning request."""

    reference_ids: frozenset[str] = frozenset()
    present_roles: frozenset[str] = frozenset()
    first_frame_reference_ids: frozenset[str] = frozenset()

    @property
    def reference_count(self) -> int:
        return len(self.reference_ids)

    @property
    def has_first_frame(self) -> bool:
        return bool(self.first_frame_reference_ids)

    @classmethod
    def from_inputs_catalog(
        cls,
        catalog: Mapping[str, Any] | None,
    ) -> RequestReferenceInventory:
        """Normalize the persisted catalog into reference facts.

        ``role_assignments`` is the canonical role manifest.  Serialized
        ``ArtifactRef`` role locations and the direct-tool ``metadata.role`` shape
        are accepted too, so a catalog can carry contract-native references without
        duplicating the role.  Assignments to absent IDs do not invent references.
        """

        if not isinstance(catalog, Mapping):
            return cls()

        raw_inputs = catalog.get("inputs")
        if not isinstance(raw_inputs, (list, tuple)):
            return cls()

        records: dict[str, dict[str, Any]] = {}
        aliases: dict[str, str] = {}

        for index, raw_item in enumerate(raw_inputs):
            if isinstance(raw_item, Mapping):
                item = raw_item
                reference_id = _reference_id(item, index)
                item_aliases = _reference_aliases(item, reference_id)
                roles = _item_roles(item)
                if item.get("trained_identity_id") is not None:
                    roles.add("identity")
                image_like = _is_image_like(item)
                explicit_first_frame = _explicit_first_frame(item)
            else:
                reference_id = _clean_token(raw_item) or f"input:{index}"
                item_aliases = {reference_id}
                roles = set()
                image_like = False
                explicit_first_frame = False

            record = records.setdefault(
                reference_id,
                {
                    "roles": set(),
                    "image_like": False,
                    "explicit_first_frame": False,
                },
            )
            record["roles"].update(roles)
            record["image_like"] = bool(record["image_like"] or image_like)
            record["explicit_first_frame"] = bool(
                record["explicit_first_frame"] or explicit_first_frame
            )
            for alias in item_aliases:
                aliases.setdefault(alias, reference_id)

        raw_assignments = catalog.get("role_assignments")
        if isinstance(raw_assignments, Mapping):
            for raw_role, raw_targets in raw_assignments.items():
                role = _clean_token(raw_role)
                if role is None:
                    continue
                for target in _assignment_targets(raw_targets):
                    reference_id = aliases.get(target)
                    if reference_id is not None:
                        records[reference_id]["roles"].add(role)

        present_roles: set[str] = set()
        first_frame_ids: set[str] = set()
        for reference_id, record in records.items():
            roles = record["roles"]
            present_roles.update(roles)
            # A first frame is not merely any image in the request.  It is an
            # image intentionally assigned to the structural slot (or explicitly
            # attested as the first frame) so identity/style references cannot be
            # silently repurposed by routing.
            if record["explicit_first_frame"] or ("structural" in roles and record["image_like"]):
                first_frame_ids.add(reference_id)

        return cls(
            reference_ids=frozenset(records),
            present_roles=frozenset(present_roles),
            first_frame_reference_ids=frozenset(first_frame_ids),
        )


@dataclass(frozen=True)
class ReferenceFeasibility:
    """Bridge's named judgment over declared requirements and request facts."""

    missing_roles: tuple[str, ...]
    reference_count: int
    max_references: int | None
    missing_first_frame: bool

    @property
    def exceeds_reference_limit(self) -> bool:
        return self.max_references is not None and self.reference_count > self.max_references

    @property
    def feasible(self) -> bool:
        return not (self.missing_roles or self.exceeds_reference_limit or self.missing_first_frame)

    @property
    def reason_codes(self) -> tuple[str, ...]:
        reasons: list[str] = []
        if self.missing_roles:
            reasons.append("missing_required_roles")
        if self.exceeds_reference_limit:
            reasons.append("reference_limit_exceeded")
        if self.missing_first_frame:
            reasons.append("input_first_frame_missing")
        return tuple(reasons)


def evaluate_reference_requirements(
    requirements: ReferenceRequirementSpec,
    inventory: RequestReferenceInventory,
) -> ReferenceFeasibility:
    """Apply Bridge's isolated hard-block policy to contract source facts."""

    missing_roles = tuple(sorted(set(requirements.required_roles) - inventory.present_roles))
    return ReferenceFeasibility(
        missing_roles=missing_roles,
        reference_count=inventory.reference_count,
        max_references=requirements.max_references,
        missing_first_frame=(requirements.requires_first_frame and not inventory.has_first_frame),
    )


def _clean_token(value: Any) -> str | None:
    if not isinstance(value, (str, int)):
        return None
    token = str(value).strip()
    return token or None


def _reference_id(item: Mapping[str, Any], index: int) -> str:
    for key in (
        "artifact_id",
        "payload_id",
        "source_artifact_id",
        "id",
        "trained_identity_id",
    ):
        token = _clean_token(item.get(key))
        if token is not None:
            return token
    locator = item.get("locator")
    if isinstance(locator, Mapping):
        token = _clean_token(locator.get("reference_id"))
        if token is not None:
            return token
    return f"input:{index}"


def _reference_aliases(item: Mapping[str, Any], reference_id: str) -> set[str]:
    aliases = {reference_id}
    for key in (
        "artifact_id",
        "payload_id",
        "source_artifact_id",
        "id",
        "trained_identity_id",
    ):
        token = _clean_token(item.get(key))
        if token is not None:
            aliases.add(token)
    locator = item.get("locator")
    if isinstance(locator, Mapping):
        token = _clean_token(locator.get("reference_id"))
        if token is not None:
            aliases.add(token)
    return aliases


def _roles(value: Any) -> set[str]:
    if isinstance(value, (str, int)):
        token = _clean_token(value)
        return {token} if token is not None else set()
    if not isinstance(value, Iterable) or isinstance(value, Mapping):
        return set()
    return {token for item in value if (token := _clean_token(item)) is not None}


def _item_roles(item: Mapping[str, Any]) -> set[str]:
    roles = _roles(item.get("role")) | _roles(item.get("roles"))
    metadata = item.get("metadata")
    if isinstance(metadata, Mapping):
        roles.update(_roles(metadata.get("role")))
        roles.update(_roles(metadata.get("roles")))
    locator = item.get("locator")
    if isinstance(locator, Mapping):
        roles.update(_roles(locator.get("role")))
    return roles


def _assignment_targets(value: Any) -> tuple[str, ...]:
    if isinstance(value, Mapping):
        for key in (
            "artifact_id",
            "payload_id",
            "reference_id",
            "source_artifact_id",
            "id",
            "trained_identity_id",
        ):
            token = _clean_token(value.get(key))
            if token is not None:
                return (token,)
        return ()
    if isinstance(value, (list, tuple, set, frozenset)):
        targets: list[str] = []
        for item in value:
            targets.extend(_assignment_targets(item))
        return tuple(targets)
    token = _clean_token(value)
    return (token,) if token is not None else ()


def _explicit_first_frame(item: Mapping[str, Any]) -> bool:
    for key in ("is_first_frame", "supplies_first_frame"):
        if item.get(key) is True:
            return True
    metadata = item.get("metadata")
    if isinstance(metadata, Mapping):
        return any(metadata.get(key) is True for key in ("is_first_frame", "supplies_first_frame"))
    return False


def _is_image_like(item: Mapping[str, Any]) -> bool:
    metadata = item.get("metadata")
    metadata = metadata if isinstance(metadata, Mapping) else {}
    for value in (
        item.get("artifact_type"),
        item.get("media_kind"),
        item.get("mime_type"),
        metadata.get("artifact_type"),
        metadata.get("media_kind"),
        metadata.get("mime_type"),
    ):
        token = _clean_token(value)
        if token is None:
            continue
        normalized = token.lower().replace("-", "_")
        if normalized.startswith("image/") or normalized in _IMAGE_ARTIFACT_TYPES:
            return True

    locator = item.get("locator")
    locator = locator if isinstance(locator, Mapping) else {}
    for value in (
        item.get("url"),
        item.get("uri"),
        item.get("path"),
        item.get("local_path"),
        metadata.get("url"),
        metadata.get("uri"),
        metadata.get("path"),
        metadata.get("local_path"),
        locator.get("target"),
    ):
        token = _clean_token(value)
        if token is None:
            continue
        path = token.split("?", 1)[0].split("#", 1)[0]
        if PurePosixPath(path).suffix.lower() in _IMAGE_SUFFIXES:
            return True
    return False
