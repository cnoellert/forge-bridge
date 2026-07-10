"""Deterministic positional-binding graph primitive with identity validation.

GuardedZipNode pairs ``left[i]`` with ``right[i]`` — POSITIONAL binding, where
the artist's selection ORDER is authored intent and is never reordered. It is
the deliberate counterpart to ``join`` (``forge_bridge.graph.join``): ``join``
is identity / key-based association that is ORDER-INDEPENDENT (each left item is
paired with the one right item whose key value corresponds, wherever that right
item sits); ``guarded_zip`` is positional and trusts the order the operator
selected in.

Because positional binding is blind to identity, ``guarded_zip`` runs a safety
check: each pair's names must correspond. It compares ``left_item[left_key]`` to
``right_item[right_key]`` under a normalized (``casefold`` + ``strip``)
comparison BY DEFAULT, so cosmetic formatting differences never trigger a false
halt. Any inconsistency — unequal lengths, or a per-index name mismatch — is an
ABSTENTION, not an error: the graph executed correctly and simply declined to
produce an unsafe pairing from inconsistent selections. An abstention yields a
NodeResult with no usable output, so no downstream mutation fires.

A nesting-key collision (the ``into`` key already present on a left item) is a
real structured error (``GuardedZipError``), not an abstention, and fails
closed.

For identity / key-based association that ignores selection order, use ``join``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from forge_bridge.graph.ports import PortContract, PortTopology


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


class GuardedZipError(ValueError):
    """Raised for a config-invalid guarded_zip authoring error.

    Config-invalid ONLY — a compiler/author mistake: a missing/empty spec key,
    an unusable input shape, or a nesting-key collision. A per-index or length
    pairing MISMATCH is NOT a GuardedZipError; it is a ``GuardedZipAbstain``,
    which the boundary turns into an abstained NodeResult rather than an error.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class GuardedZipAbstain(Exception):
    """Signal that guarded_zip declined to produce a safe pairing.

    Raised for a pairing mismatch (unequal lengths, or a per-index name
    mismatch). Deliberately NOT a ``GuardedZipError``/``ValueError``: the
    boundary catches it and mints an ABSTAINED NodeResult (no usable output),
    mirroring the way ``if_gate`` signals a closed gate rather than an error.
    The graph executed correctly; the artist's selections were inconsistent.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class GuardedZipSpec:
    """Positional-binding pairing target consumed by GuardedZipNode."""

    left_key: str
    right_key: str = ""      # empty → use left_key
    into: str = "paired"
    # Safety-check strictness. When True (the default), BOTH sides of each name
    # comparison are coerced to casefolded, stripped strings, so cosmetic
    # formatting differences never trigger a false halt. Set False to require
    # exact value equality.
    # ponytail: this single bool IS the pluggable-strictness upgrade path — a
    # comparison DSL could live here later, but is deliberately not built now.
    normalize: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "left_key": self.left_key,
            "right_key": self.right_key,
            "into": self.into,
            "normalize": self.normalize,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GuardedZipSpec":
        left_key = data.get("left_key")
        if not isinstance(left_key, str) or not left_key:
            raise GuardedZipError(
                "guarded_zip_invalid_spec", "guarded_zip left_key is required."
            )
        return cls(
            left_key=left_key,
            right_key=data.get("right_key", "") or "",
            into=data.get("into", "paired") or "paired",
            normalize=bool(data.get("normalize", True)),
        )


@dataclass(frozen=True)
class GuardedZipNode:
    """Positional-binding node over two collection-shaped graph inputs."""

    port_contract: ClassVar[PortContract] = PortContract(
        (PortTopology.list_of("item"),),
        PortTopology.list_of("item"),
    )

    spec: GuardedZipSpec

    def run(self, left: Any, right: Any) -> dict[str, Any]:
        left_container_key, left_collection = _extract_collection(left, "left")
        _, right_collection = _extract_collection(right, "right")

        # Unequal lengths → abstain: the artist's selections cannot be safely
        # paired positionally. Not an error — the graph ran correctly.
        if len(left_collection) != len(right_collection):
            raise GuardedZipAbstain(
                "guarded_zip_length_mismatch",
                f"guarded_zip abstained: length mismatch "
                f"(left={len(left_collection)}, right={len(right_collection)})",
            )

        left_attr = self.spec.left_key
        right_attr = self.spec.right_key or self.spec.left_key

        paired: list[dict[str, Any]] = []
        for index, (left_item, right_item) in enumerate(
            zip(left_collection, right_collection)
        ):
            left_value = left_item.get(left_attr)
            right_value = right_item.get(right_attr)
            if self._norm(left_value) != self._norm(right_value):
                raise GuardedZipAbstain(
                    "guarded_zip_name_mismatch",
                    f"guarded_zip abstained at index {index}: "
                    f"left name {left_value!r} does not correspond to "
                    f"right name {right_value!r}",
                )
            # A preexisting nesting key IS a real authoring error, never a silent
            # clobber of the left item.
            if self.spec.into in left_item:
                raise GuardedZipError(
                    "guarded_zip_collision",
                    f"left item already has key '{self.spec.into}'",
                )
            paired.append({**left_item, self.spec.into: right_item})

        provenance = {
            "left_count": len(left_collection),
            "right_count": len(right_collection),
            "paired": len(paired),
            "left_key": left_attr,
            "right_key": right_attr,
            "normalize": self.spec.normalize,
        }

        if left_container_key is None:
            return {
                "collection": paired,
                "count": len(paired),
                "guarded_zip": provenance,
            }

        result = dict(left)
        result[left_container_key] = paired
        if isinstance(result.get("count"), int):
            result["count"] = len(paired)
        result["guarded_zip"] = provenance
        return result

    def _norm(self, value: Any) -> Any:
        # Coerce via str() on the normalize path so None / non-str values never
        # raise: a None-vs-something is simply a non-correspondence → abstain,
        # never a crash.
        # ponytail: None-vs-None comparing equal under normalization is accepted
        # for now.
        if self.spec.normalize:
            return str(value).casefold().strip()
        return value


def _extract_collection(data: Any, side: str) -> tuple[str | None, list[dict[str, Any]]]:
    if isinstance(data, list):
        if all(isinstance(item, dict) for item in data):
            return None, data
        raise GuardedZipError(
            "guarded_zip_invalid_input",
            f"GuardedZipNode requires list[dict] {side} collection input.",
        )

    if not isinstance(data, dict):
        raise GuardedZipError(
            "guarded_zip_invalid_input",
            f"GuardedZipNode requires a {side} collection.",
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

    raise GuardedZipError(
        "guarded_zip_invalid_input",
        f"GuardedZipNode could not find a single list[dict] {side} collection.",
    )
