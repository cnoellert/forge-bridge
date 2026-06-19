"""Admission table for the M2 slice-1 composition dispatch surface.

This is the single routing table for the slice. It is intentionally keyed on
``operator_id`` rather than graph-step text: the text grammars join this table
later, while the current compiler/executor path already carries operator ids.

The table records declared sibling/operator properties, not bridge-verified
facts. Bridge can require that every admission declares its compare-relevant
profile, but the truth of properties such as ``no_state_mutation`` remains a
sibling-contractual obligation until a concrete specimen proves otherwise.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

DispatchKind = Literal["mcp", "primitive", "foreach"]


class AdmissionRejected(ValueError):
    """Raised when an operator is not admitted to the slice-1 executor surface."""


@dataclass(frozen=True)
class AdmissionRecord:
    """A reviewed admission entry for one operator id."""

    operator_id: str
    resolved_class: str
    dispatch_kind: DispatchKind
    synchronous: bool
    returns_reference: bool
    no_state_mutation: bool
    idempotent_result: bool

    def __post_init__(self) -> None:
        declarations = {
            "synchronous": self.synchronous,
            "returns_reference": self.returns_reference,
            "no_state_mutation": self.no_state_mutation,
            "idempotent_result": self.idempotent_result,
        }
        missing = [
            name for name, value in declarations.items()
            if not isinstance(value, bool)
        ]
        if missing:
            raise AdmissionRejected(
                f"AdmissionRecord {self.operator_id!r} missing bool declarations: "
                f"{', '.join(missing)}"
            )


_ADMISSION_RECORDS: tuple[AdmissionRecord, ...] = (
    AdmissionRecord(
        operator_id="forge_is_greenscreen",
        resolved_class="mcp.read_perception",
        dispatch_kind="mcp",
        synchronous=True,
        returns_reference=False,
        no_state_mutation=True,
        idempotent_result=True,
    ),
    AdmissionRecord(
        operator_id="forge_roto_ref",
        resolved_class="mcp.synchronous_make",
        dispatch_kind="mcp",
        synchronous=True,
        returns_reference=True,
        no_state_mutation=True,
        idempotent_result=True,
    ),
    AdmissionRecord(
        operator_id="filter",
        resolved_class="primitive.filter",
        dispatch_kind="primitive",
        synchronous=True,
        returns_reference=False,
        no_state_mutation=True,
        idempotent_result=True,
    ),
    AdmissionRecord(
        operator_id="if",
        resolved_class="primitive.if_gate",
        dispatch_kind="primitive",
        synchronous=True,
        returns_reference=False,
        no_state_mutation=True,
        idempotent_result=True,
    ),
    AdmissionRecord(
        operator_id="foreach",
        resolved_class="primitive.foreach",
        dispatch_kind="foreach",
        synchronous=True,
        returns_reference=False,
        no_state_mutation=True,
        idempotent_result=True,
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
