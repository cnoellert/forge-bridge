from __future__ import annotations

import pytest

from forge_bridge.composition.admission import (
    ADMISSION_TABLE,
    AdmissionRecord,
    AdmissionRejected,
    admit_operator,
)


def test_admission_accepts_slice_one_operator_ids():
    greenscreen = admit_operator("forge_is_greenscreen")
    roto = admit_operator("forge_roto_ref")
    deliverable = admit_operator("forge_assemble_deliverable_package")

    assert greenscreen.resolved_class == "mcp.read_perception"
    assert greenscreen.returns_reference is False
    assert roto.resolved_class == "mcp.synchronous_make"
    assert roto.dispatch_kind == "mcp"
    assert roto.returns_reference is True
    assert deliverable.resolved_class == "mcp.synchronous_make"
    assert deliverable.dispatch_kind == "mcp"
    assert deliverable.returns_reference is True
    assert deliverable.no_state_mutation is True
    assert deliverable.idempotent_result is True
    assert admit_operator("filter").resolved_class == "primitive.filter"
    assert admit_operator("if").resolved_class == "primitive.if_gate"
    assert admit_operator("foreach").dispatch_kind == "foreach"


def test_admission_fails_closed_for_unknown_operator():
    with pytest.raises(AdmissionRejected):
        admit_operator("forge_manifest_read")


def test_admission_table_is_operator_id_keyed_and_has_no_default():
    assert set(ADMISSION_TABLE) == {
        "forge_is_greenscreen",
        "forge_roto_ref",
        "forge_assemble_deliverable_package",
        "filter",
        "if",
        "foreach",
    }
    assert "filter(is_greenscreen == true)" not in ADMISSION_TABLE
    assert "if(disposition == pass)" not in ADMISSION_TABLE
    assert "foreach(forge_roto_ref)" not in ADMISSION_TABLE


def test_declaration_is_not_treated_as_truth():
    record = admit_operator("forge_is_greenscreen")
    assert record.synchronous is True
    assert record.no_state_mutation is True
    assert record.idempotent_result is True
    assert record.resolved_class == "mcp.read_perception"


def test_admission_record_missing_declaration_fails_closed():
    with pytest.raises(TypeError):
        AdmissionRecord(  # type: ignore[call-arg]
            operator_id="broken",
            resolved_class="mcp.read_perception",
            dispatch_kind="mcp",
            synchronous=True,
            returns_reference=False,
            no_state_mutation=True,
        )

    with pytest.raises(AdmissionRejected):
        AdmissionRecord(
            operator_id="broken",
            resolved_class="mcp.read_perception",
            dispatch_kind="mcp",
            synchronous=True,
            returns_reference=False,
            no_state_mutation=True,
            idempotent_result=None,  # type: ignore[arg-type]
        )
