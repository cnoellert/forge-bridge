"""Admission table for the M2 slice-1 composition dispatch surface.

This is the single routing table for the slice. It is intentionally keyed on
``operator_id`` rather than graph-step text: the text grammars join this table
later, while the current compiler/executor path already carries operator ids.

The table is an admission declaration, not proof of semantic truth. In
particular, a read/perception declaration does not prove an operator is harmless;
it only says this narrow slice has reviewed and admitted that operator id for
the corresponding dispatch class.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

DispatchKind = Literal["mcp", "primitive"]


class AdmissionRejected(ValueError):
    """Raised when an operator is not admitted to the slice-1 executor surface."""


@dataclass(frozen=True)
class AdmissionRecord:
    """A reviewed admission entry for one operator id."""

    operator_id: str
    resolved_class: str
    dispatch_kind: DispatchKind
    idempotent: bool
    declaration: str


_ADMISSION_RECORDS: tuple[AdmissionRecord, ...] = (
    AdmissionRecord(
        operator_id="forge_is_greenscreen",
        resolved_class="mcp.read_perception",
        dispatch_kind="mcp",
        idempotent=True,
        declaration="read/perception operator admitted for slice-1 compare",
    ),
    AdmissionRecord(
        operator_id="forge_roto_ref",
        resolved_class="mcp.read_perception",
        dispatch_kind="mcp",
        idempotent=True,
        declaration="read/perception operator admitted for slice-1 compare",
    ),
    AdmissionRecord(
        operator_id="filter",
        resolved_class="primitive.filter",
        dispatch_kind="primitive",
        idempotent=True,
        declaration="value-transform primitive admitted for slice-1 compare",
    ),
)

ADMISSION_TABLE = MappingProxyType(
    {record.operator_id: record for record in _ADMISSION_RECORDS}
)


def admit_operator(operator_id: str) -> AdmissionRecord:
    """Return the reviewed admission record for ``operator_id`` or fail closed."""

    record = ADMISSION_TABLE.get(operator_id)
    if record is None:
        raise AdmissionRejected(f"operator_id {operator_id!r} is not admitted")
    return record

