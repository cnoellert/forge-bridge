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
    rename = admit_operator("flame_rename_shots")
    assert rename.resolved_class == "mcp.host_mutation_discover"
    assert rename.dispatch_kind == "mcp"
    assert rename.no_state_mutation is True
    assert rename.idempotent_result is False
    editorial = admit_operator("traffik.editorial.apply_steps")
    assert editorial.resolved_class == "pipeline.traffik.editorial.apply_steps"
    assert editorial.dispatch_kind == "operation"
    assert editorial.synchronous is True
    assert editorial.returns_reference is False
    assert editorial.no_state_mutation is False
    assert editorial.idempotent_result is False
    host_resolve_operation = admit_operator("traffik.flame_delta.host_resolve")
    assert (
        host_resolve_operation.resolved_class
        == "pipeline.traffik.flame_delta.host_resolve"
    )
    assert host_resolve_operation.dispatch_kind == "operation"
    assert host_resolve_operation.synchronous is True
    assert host_resolve_operation.returns_reference is False
    assert host_resolve_operation.no_state_mutation is True
    assert host_resolve_operation.idempotent_result is True
    delta = admit_operator("delta_to_manifest")
    assert delta.resolved_class == "host.resolve.delta_to_manifest"
    assert delta.dispatch_kind == "host_resolve"
    assert delta.synchronous is True
    assert delta.returns_reference is False
    assert delta.no_state_mutation is True
    assert delta.idempotent_result is False
    author = admit_operator("author_prompt")
    assert author.resolved_class == "generators.author_prompt"
    assert author.dispatch_kind == "generation"
    assert author.synchronous is True
    assert author.returns_reference is False
    assert author.no_state_mutation is True
    assert author.idempotent_result is False
    assert admit_operator("filter").resolved_class == "primitive.filter"
    assert admit_operator("if").resolved_class == "primitive.if_gate"
    select_delta = admit_operator("select_delta")
    assert select_delta.resolved_class == "primitive.select_delta"
    assert select_delta.dispatch_kind == "primitive"
    assert select_delta.no_state_mutation is True
    assert select_delta.idempotent_result is True
    assert admit_operator("foreach").dispatch_kind == "foreach"
    commit = admit_operator("commit")
    assert commit.resolved_class == "mcp.host_mutation"
    assert commit.dispatch_kind == "commit"
    assert commit.no_state_mutation is False
    assert commit.idempotent_result is False


def test_admission_fails_closed_for_unknown_operator():
    with pytest.raises(AdmissionRejected):
        admit_operator("forge_manifest_read")


def test_admission_table_is_operator_id_keyed_and_has_no_default():
    assert set(ADMISSION_TABLE) == {
        "forge_is_greenscreen",
        "forge_roto_ref",
        "forge_assemble_deliverable_package",
        "format_result",
        "flame_rename_shots",
        "traffik.editorial.apply_steps",
        "traffik.flame_delta.host_resolve",
        "traffik.flame_sequence.ingest_edit_state",
        "delta_to_manifest",
        "author_prompt",
        "extract_context",
        "filter",
        "if",
        "select_delta",
        "foreach",
        "collect",
        "rename_delta_entry",
        "trim_delta_entry",
        "literal_source",
        "join",
        "guarded_zip",
        "commit",
    }
    assert "filter(is_greenscreen == true)" not in ADMISSION_TABLE
    assert "if(disposition == pass)" not in ADMISSION_TABLE
    assert "foreach(forge_roto_ref)" not in ADMISSION_TABLE


def test_unknown_traffik_operator_fails_closed():
    with pytest.raises(AdmissionRejected):
        admit_operator("traffik.editorial.preview_steps")


def test_unknown_generation_operator_fails_closed():
    with pytest.raises(AdmissionRejected):
        admit_operator("generate_video")


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
