from __future__ import annotations

import pytest

from forge_bridge.composition.admission import (
    ADMISSION_TABLE,
    AdmissionRejected,
    admit_operator,
)


def test_admission_accepts_slice_one_operator_ids():
    assert admit_operator("forge_is_greenscreen").resolved_class == (
        "mcp.read_perception"
    )
    assert admit_operator("forge_roto_ref").dispatch_kind == "mcp"
    assert admit_operator("filter").resolved_class == "primitive.filter"


def test_admission_fails_closed_for_unknown_operator():
    with pytest.raises(AdmissionRejected):
        admit_operator("forge_manifest_read")


def test_admission_table_is_operator_id_keyed_and_has_no_default():
    assert set(ADMISSION_TABLE) == {"forge_is_greenscreen", "forge_roto_ref", "filter"}
    assert "filter(is_greenscreen == true)" not in ADMISSION_TABLE


def test_declaration_is_not_treated_as_truth():
    record = admit_operator("forge_is_greenscreen")
    assert record.declaration
    assert "proof" not in record.declaration.lower()
    assert record.resolved_class == "mcp.read_perception"

