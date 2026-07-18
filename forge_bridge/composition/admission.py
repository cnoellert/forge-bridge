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

DispatchKind = Literal[
    "mcp",
    "primitive",
    "foreach",
    "commit",
    "operation",
    "host_resolve",
    "generation",
]
StateOwner = Literal[
    "read_only",
    "peer_owned",
    "dcc_host",
    "bridge",
    "federated_transaction",
]


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
    state_owner: StateOwner = "read_only"

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
        if self.state_owner not in {
            "read_only",
            "peer_owned",
            "dcc_host",
            "bridge",
            "federated_transaction",
        }:
            raise AdmissionRejected(
                f"AdmissionRecord {self.operator_id!r} has invalid state_owner "
                f"{self.state_owner!r}"
            )


@dataclass(frozen=True)
class MutationCounterpartAdmission:
    """Reviewed authority facts for one commit-only MCP apply counterpart."""

    tool_name: str
    state_owner: StateOwner
    synchronous: bool
    verify_before_apply: bool
    assent_required: bool
    idempotent_apply: bool

    def __post_init__(self) -> None:
        if self.state_owner not in {
            "dcc_host",
            "peer_owned",
            "bridge",
            "federated_transaction",
        }:
            raise AdmissionRejected(
                f"Mutation counterpart {self.tool_name!r} must own dcc_host, "
                "peer_owned, bridge, or federated_transaction state"
            )
        declarations = {
            "synchronous": self.synchronous,
            "verify_before_apply": self.verify_before_apply,
            "assent_required": self.assent_required,
            "idempotent_apply": self.idempotent_apply,
        }
        missing = [
            name for name, value in declarations.items() if not isinstance(value, bool)
        ]
        if missing:
            raise AdmissionRejected(
                f"Mutation counterpart {self.tool_name!r} missing bool declarations: "
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
        state_owner="peer_owned",
    ),
    # Provisional pending #86: forge_assemble_deliverable_package commits an
    # entire package directory (plate, holdouts EXR, reference JSONs, manifest).
    # no_state_mutation=True uses the current permissive reading: no canonical
    # project-state mutation, not "no filesystem side effect". If #86 resolves
    # side effects as mutation, this entry and forge_roto_ref both flip False.
    AdmissionRecord(
        operator_id="forge_assemble_deliverable_package",
        resolved_class="mcp.synchronous_make",
        dispatch_kind="mcp",
        synchronous=True,
        returns_reference=True,
        no_state_mutation=True,
        idempotent_result=True,
        state_owner="peer_owned",
    ),
    AdmissionRecord(
        operator_id="format_result",
        resolved_class="mcp.chain_terminal_format",
        dispatch_kind="mcp",
        synchronous=True,
        returns_reference=False,
        # A reads-only terminal formatter: reads no host/canonical state and
        # applies no mutation (it renders the prior chain result as operator
        # text). idempotent_result=False — it routes to the Anthropic cloud
        # model, whose rendered prose is non-deterministic. (#153 slice 2b is
        # OFFLINE arg-parity only, so the cloud hop is not exercised here.)
        no_state_mutation=True,
        idempotent_result=False,
    ),
    AdmissionRecord(
        operator_id="flame_rename_shots",
        resolved_class="mcp.host_mutation_discover",
        dispatch_kind="mcp",
        synchronous=True,
        returns_reference=False,
        no_state_mutation=True,
        idempotent_result=False,
    ),
    *(
        AdmissionRecord(
            operator_id=tool_name,
            resolved_class="mcp.host_mutation_discover",
            dispatch_kind="mcp",
            synchronous=True,
            returns_reference=False,
            no_state_mutation=True,
            idempotent_result=True,
            state_owner="read_only",
        )
        for tool_name in (
            "forge_load_shot_resources",
            "forge_load_sequence_resources",
            "forge_refresh_shot_resources",
            "forge_switch_shot_resource_version",
        )
    ),
    AdmissionRecord(
        operator_id="forge_promote_shot_resource_stream",
        resolved_class="mcp.peer_mutation_discover",
        dispatch_kind="mcp",
        synchronous=True,
        returns_reference=False,
        no_state_mutation=True,
        idempotent_result=True,
        state_owner="read_only",
    ),
    AdmissionRecord(
        operator_id="forge_register_shot_resource_promotion",
        resolved_class="mcp.bridge_mutation_discover",
        dispatch_kind="mcp",
        synchronous=True,
        returns_reference=False,
        no_state_mutation=True,
        idempotent_result=True,
        state_owner="read_only",
    ),
    AdmissionRecord(
        operator_id="forge_publish_shot_resource_transaction",
        resolved_class="mcp.federated_transaction_discover",
        dispatch_kind="mcp",
        synchronous=True,
        returns_reference=False,
        no_state_mutation=True,
        idempotent_result=True,
        state_owner="read_only",
    ),
    AdmissionRecord(
        operator_id="forge_inspect_shot_resource_publish_transaction",
        resolved_class="mcp.publish_transaction_status",
        dispatch_kind="mcp",
        synchronous=True,
        returns_reference=False,
        no_state_mutation=True,
        idempotent_result=True,
        state_owner="read_only",
    ),
    AdmissionRecord(
        operator_id="forge_abort_shot_resource_publish_transaction",
        resolved_class="mcp.peer_mutation_discover",
        dispatch_kind="mcp",
        synchronous=True,
        returns_reference=False,
        no_state_mutation=True,
        idempotent_result=True,
        state_owner="read_only",
    ),
    AdmissionRecord(
        operator_id="traffik.editorial.apply_steps",
        resolved_class="pipeline.traffik.editorial.apply_steps",
        dispatch_kind="operation",
        synchronous=True,
        returns_reference=False,
        no_state_mutation=False,
        idempotent_result=False,
        state_owner="peer_owned",
    ),
    AdmissionRecord(
        operator_id="traffik.flame_delta.host_resolve",
        resolved_class="pipeline.traffik.flame_delta.host_resolve",
        dispatch_kind="operation",
        synchronous=True,
        returns_reference=False,
        no_state_mutation=True,
        idempotent_result=True,
    ),
    AdmissionRecord(
        operator_id="traffik.flame_sequence.ingest_edit_state",
        resolved_class="pipeline.traffik.flame_sequence.ingest_edit_state",
        dispatch_kind="operation",
        synchronous=True,
        returns_reference=False,
        # sibling-contractual: ingest reads live Flame -> EditState, writes nothing.
        no_state_mutation=True,
        idempotent_result=True,
    ),
    AdmissionRecord(
        operator_id="traffik.editorial.resolve_top_video_layer",
        resolved_class="pipeline.traffik.editorial.resolve_top_video_layer",
        dispatch_kind="operation",
        synchronous=True,
        returns_reference=False,
        no_state_mutation=True,
        idempotent_result=True,
    ),
    AdmissionRecord(
        operator_id="traffik.editorial.mark_timecode_range",
        resolved_class="pipeline.traffik.editorial.mark_timecode_range",
        dispatch_kind="operation",
        synchronous=True,
        returns_reference=False,
        no_state_mutation=True,
        idempotent_result=True,
    ),
    AdmissionRecord(
        operator_id="traffik.editorial.overwrite_insert",
        resolved_class="pipeline.traffik.editorial.overwrite_insert",
        dispatch_kind="operation",
        synchronous=True,
        returns_reference=False,
        no_state_mutation=True,
        idempotent_result=True,
    ),
    AdmissionRecord(
        operator_id="delta_to_manifest",
        resolved_class="host.resolve.delta_to_manifest",
        dispatch_kind="host_resolve",
        synchronous=True,
        returns_reference=False,
        no_state_mutation=True,
        idempotent_result=False,
    ),
    AdmissionRecord(
        operator_id="author_prompt",
        resolved_class="generators.author_prompt",
        dispatch_kind="generation",
        synchronous=True,
        returns_reference=False,
        no_state_mutation=True,
        idempotent_result=False,
        state_owner="peer_owned",
    ),
    AdmissionRecord(
        operator_id="literal_source",
        resolved_class="primitive.literal_source",
        dispatch_kind="primitive",
        synchronous=True,
        returns_reference=False,
        # A source node: emits a config-authored literal collection as its output
        # (the graph analog of the CLI hand-build feeding segments in). It reads no
        # host/canonical state and holds a fixed payload, so it is a pure read-only
        # value emitter — no_state_mutation + idempotent, same character as the
        # other value-transform primitives.
        no_state_mutation=True,
        idempotent_result=True,
    ),
    AdmissionRecord(
        operator_id="extract_context",
        resolved_class="primitive.extract_context",
        dispatch_kind="primitive",
        synchronous=True,
        returns_reference=False,
        # Emits the single inherited-context kwarg an upstream result forwards
        # (`extract_chain_context`) as a scalars dict; reads no host/canonical
        # state, so it is a pure read-only value emitter — same character as the
        # other value-transform primitives.
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
        operator_id="select_delta",
        resolved_class="primitive.select_delta",
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
    AdmissionRecord(
        operator_id="collect",
        resolved_class="primitive.collect",
        dispatch_kind="primitive",
        synchronous=True,
        returns_reference=False,
        # collect folds list[IterationResult] -> one manifest: a pure read-only
        # topology reconciliation, no host/canonical state mutation.
        no_state_mutation=True,
        idempotent_result=True,
    ),
    AdmissionRecord(
        operator_id="rename_delta_entry",
        resolved_class="primitive.rename_delta_entry",
        dispatch_kind="primitive",
        synchronous=True,
        returns_reference=False,
        # AUTHORS a single-entry rename TimelineDelta from one segment item; it
        # does NOT apply. A downstream commit owns host mutation, so this stays
        # no_state_mutation=True (same character as the other value-transform
        # primitives + foreach).
        no_state_mutation=True,
        idempotent_result=True,
    ),
    AdmissionRecord(
        operator_id="trim_delta_entry",
        resolved_class="primitive.trim_delta_entry",
        dispatch_kind="primitive",
        synchronous=True,
        returns_reference=False,
        # AUTHORS a single-entry relative-trim TimelineDelta from one segment item;
        # it does NOT apply. A downstream commit owns host mutation, so this stays
        # no_state_mutation=True (same character as rename_delta_entry + foreach).
        no_state_mutation=True,
        idempotent_result=True,
    ),
    AdmissionRecord(
        operator_id="join",
        resolved_class="primitive.join",
        dispatch_kind="primitive",
        synchronous=True,
        returns_reference=False,
        # Pairs a left collection with matching right items (name-match) and
        # emits the left enriched with its nested match: a pure read-only value
        # transform, no host/canonical state mutation.
        no_state_mutation=True,
        idempotent_result=True,
    ),
    AdmissionRecord(
        operator_id="guarded_zip",
        resolved_class="primitive.guarded_zip",
        dispatch_kind="primitive",
        synchronous=True,
        returns_reference=False,
        # Positional-binding fan-in with a name-correspondence safety check:
        # pairs left[i] with right[i] and emits the left enriched with its
        # nested pair. A pure read-only value transform, no host/canonical
        # state mutation. (A pairing mismatch abstains; it never mutates.)
        no_state_mutation=True,
        idempotent_result=True,
    ),
    AdmissionRecord(
        operator_id="pipeline.shot_resource.current",
        resolved_class="pipeline.shot_resource.current",
        dispatch_kind="operation",
        synchronous=True,
        returns_reference=False,
        no_state_mutation=True,
        idempotent_result=True,
        state_owner="read_only",
    ),
    AdmissionRecord(
        operator_id="pipeline.shot_resource.stream_promotion.validate",
        resolved_class="pipeline.shot_resource.stream_promotion.validate",
        dispatch_kind="operation",
        synchronous=True,
        returns_reference=False,
        no_state_mutation=True,
        idempotent_result=True,
        state_owner="read_only",
    ),
    AdmissionRecord(
        operator_id="pipeline.shot_resource.stream_promotion.registration_plan",
        resolved_class=(
            "pipeline.shot_resource.stream_promotion.registration_plan"
        ),
        dispatch_kind="operation",
        synchronous=True,
        returns_reference=False,
        no_state_mutation=True,
        idempotent_result=True,
        state_owner="read_only",
    ),
    AdmissionRecord(
        operator_id="pipeline.host_graph.inspect",
        resolved_class="pipeline.host_graph.inspect",
        dispatch_kind="operation",
        synchronous=True,
        returns_reference=False,
        no_state_mutation=True,
        idempotent_result=True,
        state_owner="read_only",
    ),
    AdmissionRecord(
        operator_id="pipeline.host_graph.list_node_types",
        resolved_class="pipeline.host_graph.list_node_types",
        dispatch_kind="operation",
        synchronous=True,
        returns_reference=False,
        no_state_mutation=True,
        idempotent_result=True,
        state_owner="read_only",
    ),
    AdmissionRecord(
        operator_id="pipeline.host_graph.describe_node_type",
        resolved_class="pipeline.host_graph.describe_node_type",
        dispatch_kind="operation",
        synchronous=True,
        returns_reference=False,
        no_state_mutation=True,
        idempotent_result=True,
        state_owner="read_only",
    ),
    AdmissionRecord(
        operator_id="pipeline.shot_output_graph.plan",
        resolved_class="pipeline.shot_output_graph.plan",
        dispatch_kind="operation",
        synchronous=True,
        returns_reference=False,
        no_state_mutation=True,
        idempotent_result=True,
        state_owner="read_only",
    ),
    AdmissionRecord(
        operator_id="pipeline.host_graph.verify",
        resolved_class="pipeline.host_graph.verify",
        dispatch_kind="operation",
        synchronous=True,
        returns_reference=False,
        no_state_mutation=True,
        idempotent_result=True,
        state_owner="read_only",
    ),
    AdmissionRecord(
        operator_id="commit",
        resolved_class="mcp.host_mutation",
        dispatch_kind="commit",
        synchronous=True,
        returns_reference=False,
        no_state_mutation=False,
        idempotent_result=False,
        state_owner="dcc_host",
    ),
)

ADMISSION_TABLE = MappingProxyType(
    {record.operator_id: record for record in _ADMISSION_RECORDS}
)

_MUTATION_COUNTERPART_RECORDS = (
    MutationCounterpartAdmission(
        tool_name="flame_rename_shots",
        state_owner="dcc_host",
        synchronous=True,
        verify_before_apply=True,
        assent_required=True,
        idempotent_apply=False,
    ),
    MutationCounterpartAdmission(
        tool_name="flame_create_reel",
        state_owner="dcc_host",
        synchronous=True,
        verify_before_apply=True,
        assent_required=True,
        idempotent_apply=False,
    ),
    MutationCounterpartAdmission(
        tool_name="forge_promote_shot_resource_stream",
        state_owner="peer_owned",
        synchronous=True,
        verify_before_apply=True,
        assent_required=True,
        idempotent_apply=True,
    ),
    MutationCounterpartAdmission(
        tool_name="forge_register_shot_resource_promotion",
        state_owner="bridge",
        synchronous=True,
        verify_before_apply=True,
        assent_required=True,
        idempotent_apply=True,
    ),
    MutationCounterpartAdmission(
        tool_name="forge_publish_shot_resource_transaction",
        state_owner="federated_transaction",
        synchronous=True,
        verify_before_apply=True,
        assent_required=True,
        idempotent_apply=True,
    ),
    MutationCounterpartAdmission(
        tool_name="forge_abort_shot_resource_publish_transaction",
        state_owner="peer_owned",
        synchronous=True,
        verify_before_apply=True,
        assent_required=True,
        idempotent_apply=True,
    ),
    *(
        MutationCounterpartAdmission(
            tool_name=tool_name,
            state_owner="dcc_host",
            synchronous=True,
            verify_before_apply=True,
            assent_required=True,
            idempotent_apply=True,
        )
        for tool_name in (
            "forge_apply_segment_delta",
            "forge_apply_segment_insert_delta",
            "forge_apply_segment_start_frame_delta",
            "forge_apply_segment_temporal_delta",
            "forge_apply_host_graph_plan",
            "forge_load_shot_resources",
            "forge_load_sequence_resources",
            "forge_refresh_shot_resources",
            "forge_switch_shot_resource_version",
        )
    ),
)

MUTATION_COUNTERPART_TABLE = MappingProxyType(
    {record.tool_name: record for record in _MUTATION_COUNTERPART_RECORDS}
)


def admit_operator(operator_id: str) -> AdmissionRecord:
    """Return the reviewed admission record for ``operator_id`` or fail closed."""

    record = ADMISSION_TABLE.get(operator_id)
    if record is None:
        raise AdmissionRejected(f"operator_id {operator_id!r} is not admitted")
    return record


def admit_mutation_counterpart(tool_name: str) -> MutationCounterpartAdmission:
    """Return one reviewed commit-only MCP counterpart or fail closed."""

    record = MUTATION_COUNTERPART_TABLE.get(tool_name)
    if record is None:
        raise AdmissionRejected(
            f"mutation counterpart {tool_name!r} is not admitted"
        )
    return record
