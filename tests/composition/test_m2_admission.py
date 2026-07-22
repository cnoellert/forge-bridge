from __future__ import annotations

import pytest

from forge_bridge.composition.admission import (
    ADMISSION_TABLE,
    MUTATION_COUNTERPART_TABLE,
    AdmissionRecord,
    AdmissionRejected,
    admit_mutation_counterpart,
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
    assert editorial.state_owner == "peer_owned"
    step_capabilities = admit_operator("traffik.editorial.step_capabilities")
    assert step_capabilities.resolved_class == (
        "pipeline.traffik.editorial.step_capabilities"
    )
    assert step_capabilities.dispatch_kind == "operation"
    assert step_capabilities.no_state_mutation is True
    assert step_capabilities.idempotent_result is True
    assert step_capabilities.state_owner == "read_only"
    live_read = admit_operator("flame.editorial.read_edit_state")
    assert live_read.resolved_class == "pipeline.flame.editorial.read_edit_state"
    assert live_read.dispatch_kind == "operation"
    assert live_read.synchronous is True
    assert live_read.returns_reference is False
    assert live_read.no_state_mutation is True
    assert live_read.idempotent_result is True
    assert live_read.state_owner == "dcc_host"
    realization = admit_operator("flame.editorial.delta_realization")
    assert realization.resolved_class == (
        "pipeline.flame.editorial.delta_realization"
    )
    assert realization.dispatch_kind == "operation"
    assert realization.no_state_mutation is True
    assert realization.idempotent_result is True
    assert realization.state_owner == "read_only"
    for operation_id in (
        "traffik.editorial.resolve_top_video_layer",
        "traffik.editorial.mark_timecode_range",
        "traffik.editorial.overwrite_insert",
    ):
        operation = admit_operator(operation_id)
        assert operation.resolved_class == f"pipeline.{operation_id}"
        assert operation.dispatch_kind == "operation"
        assert operation.synchronous is True
        assert operation.returns_reference is False
        assert operation.no_state_mutation is True
        assert operation.idempotent_result is True
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
    resolve_top = admit_operator("traffik.editorial.resolve_top_video_layer")
    assert (
        resolve_top.resolved_class
        == "pipeline.traffik.editorial.resolve_top_video_layer"
    )
    assert resolve_top.dispatch_kind == "operation"
    assert resolve_top.synchronous is True
    assert resolve_top.returns_reference is False
    assert resolve_top.no_state_mutation is True
    assert resolve_top.idempotent_result is True
    mark_range = admit_operator("traffik.editorial.mark_timecode_range")
    assert (
        mark_range.resolved_class
        == "pipeline.traffik.editorial.mark_timecode_range"
    )
    assert mark_range.dispatch_kind == "operation"
    assert mark_range.synchronous is True
    assert mark_range.returns_reference is False
    assert mark_range.no_state_mutation is True
    assert mark_range.idempotent_result is True
    overwrite_insert = admit_operator("traffik.editorial.overwrite_insert")
    assert (
        overwrite_insert.resolved_class
        == "pipeline.traffik.editorial.overwrite_insert"
    )
    assert overwrite_insert.dispatch_kind == "operation"
    assert overwrite_insert.synchronous is True
    assert overwrite_insert.returns_reference is False
    assert overwrite_insert.no_state_mutation is True
    assert overwrite_insert.idempotent_result is True
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
    assert commit.state_owner == "dcc_host"

    for operation_id in (
        "pipeline.shot_resource.current",
        "pipeline.shot_resource.stream_promotion.validate",
        "pipeline.shot_resource.stream_promotion.registration_plan",
        "pipeline.host_graph.inspect",
        "pipeline.host_graph.list_node_types",
        "pipeline.host_graph.describe_node_type",
        "pipeline.shot_output_graph.plan",
        "pipeline.host_graph.verify",
    ):
        operation = admit_operator(operation_id)
        assert operation.dispatch_kind == "operation"
        assert operation.no_state_mutation is True
        assert operation.idempotent_result is True
        assert operation.state_owner == "read_only"


def test_grouped_host_graph_apply_is_a_reviewed_commit_only_counterpart():
    record = admit_mutation_counterpart("forge_apply_host_graph_plan")

    assert record.state_owner == "dcc_host"
    assert record.synchronous is True
    assert record.verify_before_apply is True
    assert record.assent_required is True
    assert record.idempotent_apply is True
    assert "forge_apply_host_graph_plan" not in ADMISSION_TABLE
    assert "forge_apply_host_graph_plan" in MUTATION_COUNTERPART_TABLE


@pytest.mark.parametrize(
    "tool_name",
    [
        "forge_load_shot_resources",
        "forge_load_sequence_resources",
        "forge_refresh_shot_resources",
        "forge_switch_shot_resource_version",
    ],
)
def test_shot_resource_tools_are_discovery_nodes_and_commit_only_counterparts(
    tool_name,
):
    discovery = admit_operator(tool_name)
    counterpart = admit_mutation_counterpart(tool_name)

    assert discovery.dispatch_kind == "mcp"
    assert discovery.no_state_mutation is True
    assert discovery.idempotent_result is True
    assert discovery.state_owner == "read_only"
    assert counterpart.state_owner == "dcc_host"
    assert counterpart.verify_before_apply is True
    assert counterpart.assent_required is True
    assert counterpart.idempotent_apply is True


def test_stream_promotion_is_a_reviewed_peer_owned_commit_counterpart():
    tool_name = "forge_promote_shot_resource_stream"
    discovery = admit_operator(tool_name)
    counterpart = admit_mutation_counterpart(tool_name)

    assert discovery.resolved_class == "mcp.peer_mutation_discover"
    assert discovery.dispatch_kind == "mcp"
    assert discovery.no_state_mutation is True
    assert discovery.idempotent_result is True
    assert discovery.state_owner == "read_only"
    assert counterpart.state_owner == "peer_owned"
    assert counterpart.verify_before_apply is True
    assert counterpart.assent_required is True
    assert counterpart.idempotent_apply is True


def test_stream_promotion_registration_is_a_bridge_owned_commit_counterpart():
    tool_name = "forge_register_shot_resource_promotion"
    discovery = admit_operator(tool_name)
    counterpart = admit_mutation_counterpart(tool_name)

    assert discovery.resolved_class == "mcp.bridge_mutation_discover"
    assert discovery.dispatch_kind == "mcp"
    assert discovery.no_state_mutation is True
    assert discovery.idempotent_result is True
    assert discovery.state_owner == "read_only"
    assert counterpart.state_owner == "bridge"
    assert counterpart.verify_before_apply is True
    assert counterpart.assent_required is True
    assert counterpart.idempotent_apply is True


def test_publish_transaction_is_a_reviewed_federated_commit_counterpart():
    tool_name = "forge_publish_shot_resource_transaction"
    discovery = admit_operator(tool_name)
    counterpart = admit_mutation_counterpart(tool_name)

    assert discovery.resolved_class == "mcp.federated_transaction_discover"
    assert discovery.dispatch_kind == "mcp"
    assert discovery.no_state_mutation is True
    assert discovery.idempotent_result is True
    assert discovery.state_owner == "read_only"
    assert counterpart.state_owner == "federated_transaction"
    assert counterpart.verify_before_apply is True
    assert counterpart.assent_required is True
    assert counterpart.idempotent_apply is True


def test_publish_transaction_recovery_has_reviewed_status_and_abort_boundaries():
    status = admit_operator("forge_inspect_shot_resource_publish_transaction")
    abort = admit_operator("forge_abort_shot_resource_publish_transaction")
    counterpart = admit_mutation_counterpart(
        "forge_abort_shot_resource_publish_transaction"
    )

    assert status.resolved_class == "mcp.publish_transaction_status"
    assert status.dispatch_kind == "mcp"
    assert status.no_state_mutation is True
    assert status.idempotent_result is True
    assert status.state_owner == "read_only"
    assert abort.resolved_class == "mcp.peer_mutation_discover"
    assert abort.dispatch_kind == "mcp"
    assert abort.no_state_mutation is True
    assert abort.idempotent_result is True
    assert abort.state_owner == "read_only"
    assert counterpart.state_owner == "peer_owned"
    assert counterpart.verify_before_apply is True
    assert counterpart.assent_required is True
    assert counterpart.idempotent_apply is True


def test_unknown_mutation_counterpart_fails_closed():
    with pytest.raises(AdmissionRejected):
        admit_mutation_counterpart("forge_apply_unreviewed_host_plan")


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
        "forge_load_shot_resources",
        "forge_load_sequence_resources",
        "forge_refresh_shot_resources",
        "forge_switch_shot_resource_version",
        "forge_promote_shot_resource_stream",
        "forge_register_shot_resource_promotion",
        "forge_publish_shot_resource_transaction",
        "forge_inspect_shot_resource_publish_transaction",
        "forge_abort_shot_resource_publish_transaction",
        "traffik.editorial.apply_steps",
        "traffik.editorial.step_capabilities",
        "flame.editorial.read_edit_state",
        "flame.editorial.delta_realization",
        "traffik.editorial.resolve_top_video_layer",
        "traffik.editorial.mark_timecode_range",
        "traffik.editorial.overwrite_insert",
        "traffik.flame_delta.host_resolve",
        "traffik.flame_sequence.ingest_edit_state",
        "traffik.editorial.resolve_top_video_layer",
        "traffik.editorial.mark_timecode_range",
        "traffik.editorial.overwrite_insert",
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
        "pipeline.shot_resource.current",
        "pipeline.shot_resource.stream_promotion.validate",
        "pipeline.shot_resource.stream_promotion.registration_plan",
        "pipeline.host_graph.inspect",
        "pipeline.host_graph.list_node_types",
        "pipeline.host_graph.describe_node_type",
        "pipeline.shot_output_graph.plan",
        "pipeline.host_graph.verify",
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
