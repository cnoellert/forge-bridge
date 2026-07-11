"""Host-resolution boundary for peer-authored editorial deltas.

``delta_to_manifest`` is a representation transform with host I/O: a peer
authors host-neutral ``TimelineDelta`` entries, while the host executor's
discover mode authors the canonical ``MutationManifest``. Composition remains
peer-import-free; the discover callable is injected at the orchestration edge.
"""
from __future__ import annotations

import inspect
import uuid
from collections.abc import Callable, Mapping
from typing import Any

from forge_bridge.composition.admission import AdmissionRejected, admit_operator
from forge_bridge.composition.boundary import UnsupportedCompositionNodeError
from forge_bridge.composition.graph_spec import NodeSpec
from forge_bridge.composition.node_result import NodeResult
from forge_bridge.graph.mutation import MutationManifest, MutationManifestError
from forge_bridge.graph.ports import PortContract, PortTopology

HETEROGENEOUS_DELTA = "HETEROGENEOUS_DELTA"
UNSUPPORTED_DELTA_ACTION = "UNSUPPORTED_DELTA_ACTION"
UNRESOLVED_TARGET = "UNRESOLVED_TARGET"
HOST_DISCOVER_FAILED = "HOST_DISCOVER_FAILED"
HELD_FOR_REVIEW = "HELD_FOR_REVIEW"

_TRUSTED_EXECUTORS = frozenset({
    "forge_apply_segment_delta",
    "forge_apply_segment_insert_delta",
    "forge_apply_segment_start_frame_delta",
    "forge_apply_segment_temporal_delta",
})
_HOST_RESOLVE_SCHEMA_VERSION = 3

_UNRESOLVED_TARGET_CODES = frozenset({
    "identity_unresolved",
    "missing_flame_identity",
    "invalid_flame_identity",
})
_UNSUPPORTED_DELTA_CODES = frozenset({
    "unknown_delta_action",
    "object_type_requires_future_executor",
    "unknown_segment_fields",
    "no_segment_fields_changed",
})


class HostResolveBoundary:
    """Resolve peer-authored deltas into host-authored mutation manifests."""

    input_ports = {"deltas": PortContract.manifest_gate()}
    output_port = PortTopology.manifest()

    def __init__(
        self,
        *,
        run_discover: Callable[..., Any] | None = None,
        run_id: uuid.UUID | None = None,
        artifact_id_factory: Callable[[], uuid.UUID] = uuid.uuid4,
        **context_deps: Any,
    ) -> None:
        self._run_discover = run_discover
        self._run_id = run_id or uuid.uuid4()
        self._artifact_id_factory = artifact_id_factory
        self._context_deps = dict(context_deps)

    async def dispatch(
        self,
        node: NodeSpec,
        resolved_inputs: dict[str, NodeResult],
    ) -> NodeResult:
        try:
            admission = admit_operator(node.operator_id)
        except AdmissionRejected as exc:
            raise UnsupportedCompositionNodeError(
                f"{node.operator_id!r} is not admitted to the host-resolve boundary"
            ) from exc
        if admission.dispatch_kind != "host_resolve":
            raise UnsupportedCompositionNodeError(
                f"{node.operator_id!r} is admitted but not a host-resolve operator "
                f"(dispatch_kind={admission.dispatch_kind!r}); route via "
                "UnifiedDispatch"
            )

        srcs = _source_artifact_ids(resolved_inputs)
        try:
            (
                host_output,
                sequence_name,
                executors,
                entries,
            ) = _host_output_sequence_executors_and_entries(resolved_inputs)
        except ValueError as exc:
            reason_code = (
                HETEROGENEOUS_DELTA
                if "one sequence" in str(exc)
                else HOST_DISCOVER_FAILED
            )
            return self._error(
                admission.resolved_class,
                srcs,
                reason_code=reason_code,
                message=str(exc),
            )

        if not entries:
            held_result = _held_for_review(host_output)
            if held_result is not None:
                return self._error(
                    admission.resolved_class,
                    srcs,
                    reason_code=HELD_FOR_REVIEW,
                    message=held_result,
                )
            return NodeResult(
                status="ok",
                run_id=self._run_id,
                artifact_id=self._artifact_id_factory(),
                output={
                    "type": "host_resolve_empty",
                    "message": "nothing to dispatch",
                },
                output_topology=PortTopology.manifest().to_dict(),
                artifact_type="host_resolve_empty",
                source_artifact_ids=srcs,
                resolved_class=admission.resolved_class,
                control_signal="skip",
            )

        if len(executors) != 1:
            return self._error(
                admission.resolved_class,
                srcs,
                reason_code=HETEROGENEOUS_DELTA,
                message="delta_to_manifest requires one homogeneous executor.",
            )
        apply_tool = next(iter(executors))
        if apply_tool not in _TRUSTED_EXECUTORS:
            return self._error(
                admission.resolved_class,
                srcs,
                reason_code=HOST_DISCOVER_FAILED,
                message=f"executor {apply_tool!r} not trusted",
            )
        if self._run_discover is None:
            return self._error(
                admission.resolved_class,
                srcs,
                reason_code=HOST_DISCOVER_FAILED,
                message="No host discover runner is configured.",
            )

        request = {
            "sequence_name": sequence_name,
            "entries": [dict(entry) for entry in entries],
        }
        try:
            manifest = self._run_discover(
                apply_tool,
                request=request,
                **self._context_deps,
            )
            if inspect.isawaitable(manifest):
                manifest = await manifest
            discover_error = _discover_error_code(manifest)
            if discover_error is not None:
                return self._error(
                    admission.resolved_class,
                    srcs,
                    reason_code=_host_discover_reason_code(discover_error),
                    message=_discover_error_message(manifest),
                )
            manifest_dict = _manifest_dict(manifest)
        except Exception as exc:  # noqa: BLE001
            discover_error = _discover_error_code(exc)
            return self._error(
                admission.resolved_class,
                srcs,
                reason_code=_host_discover_reason_code(discover_error),
                message=str(exc),
            )
        if manifest_dict["apply_counterpart"]["tool"] != apply_tool:
            return self._error(
                admission.resolved_class,
                srcs,
                reason_code=HOST_DISCOVER_FAILED,
                message=(
                    "host discover returned apply_counterpart.tool "
                    f"{manifest_dict['apply_counterpart']['tool']!r}, expected "
                    f"{apply_tool!r}"
                ),
            )

        return NodeResult(
            status="ok",
            run_id=self._run_id,
            artifact_id=self._artifact_id_factory(),
            output=manifest_dict,
            output_topology=PortTopology.manifest().to_dict(),
            artifact_type="mutation_manifest",
            source_artifact_ids=srcs,
            resolved_class=admission.resolved_class,
        )

    def _error(
        self,
        resolved_class: str,
        source_artifact_ids: tuple[uuid.UUID, ...],
        *,
        reason_code: str,
        message: str,
    ) -> NodeResult:
        return NodeResult(
            status="error",
            run_id=self._run_id,
            output={"error": {"type": reason_code, "message": message}},
            reason_code=reason_code,
            message=message,
            source_artifact_ids=source_artifact_ids,
            resolved_class=resolved_class,
            control_signal="skip",
        )


def _host_output_sequence_executors_and_entries(
    resolved_inputs: dict[str, NodeResult],
) -> tuple[Mapping[str, Any], str | None, set[Any], list[dict[str, Any]]]:
    for result in resolved_inputs.values():
        if not result.has_usable_output or not isinstance(result.output, Mapping):
            continue
        host_output = result.output
        # The traffik.flame_delta.host_resolve operation surfaces OperationResult.data,
        # which nests the projected envelope under this string key. HostResolveBoundary
        # is already the projected-envelope consumer; promote to a visible extract node
        # only if a graph later needs to route the projection separately.
        if "flame_delta_host_resolve_payload" in host_output:
            wrapped = host_output["flame_delta_host_resolve_payload"]
            if not isinstance(wrapped, Mapping):
                raise ValueError(
                    "delta_to_manifest requires flame_delta_host_resolve_payload "
                    "to contain a projected envelope."
                )
            host_output = wrapped
        schema_version = host_output.get("schema_version")
        if schema_version != _HOST_RESOLVE_SCHEMA_VERSION:
            raise ValueError(
                "delta_to_manifest requires projected host-resolve schema_version 3."
            )

        deltas = host_output.get("deltas")
        if not isinstance(deltas, list):
            continue
        executors: set[Any] = set()
        entries: list[dict[str, Any]] = []
        for delta in deltas:
            if not isinstance(delta, Mapping):
                continue
            metadata = delta.get("metadata")
            if not isinstance(metadata, Mapping):
                raise ValueError("delta_to_manifest requires delta metadata.")
            delta_schema = metadata.get("host_resolve_schema_version")
            if delta_schema != _HOST_RESOLVE_SCHEMA_VERSION:
                raise ValueError(
                    "delta_to_manifest requires delta metadata "
                    "host_resolve_schema_version 3."
                )
            executors.add(metadata.get("executor"))
            changes = delta.get("changes", delta.get("entries", []))
            if isinstance(changes, list):
                entries.extend(
                    dict(entry)
                    for entry in changes
                    if isinstance(entry, Mapping)
                )

        sequence_ids = {
            str(delta.get("sequence_id") or delta.get("metadata", {}).get("sequence_name"))
            for delta in deltas
            if isinstance(delta, Mapping)
            and (
                delta.get("sequence_id") is not None
                or delta.get("metadata", {}).get("sequence_name") is not None
            )
        }
        if len(sequence_ids) > 1:
            raise ValueError("delta_to_manifest requires one sequence per envelope.")
        return (
            host_output,
            (next(iter(sequence_ids)) if sequence_ids else None),
            executors,
            entries,
        )
    return {}, None, set(), []


def _held_for_review(host_output: Mapping[str, Any]) -> str | None:
    plan = host_output.get("plan") or {}
    if not isinstance(plan, Mapping):
        return None
    plan_reason = str(plan.get("reason_code", ""))
    plan_output = plan.get("output") or {}
    if not isinstance(plan_output, Mapping):
        plan_output = {}
    summary = plan_output.get("summary") or {}
    if not isinstance(summary, Mapping):
        summary = {}
    held = summary.get("held_entry_count", 0)
    if not (plan_reason.endswith("review_required") or held):
        return None

    held_entries = plan_output.get("held_entries", [])
    details: list[str] = []
    if isinstance(held_entries, list):
        for entry in held_entries:
            if not isinstance(entry, Mapping):
                continue
            reason = str(entry.get("reason_code") or "review_required")
            message = str(entry.get("message") or "held for review")
            details.append(f"{reason}: {message}")
    if details:
        return "; ".join(details)
    return "host-resolve entries held for review."


def _manifest_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, MutationManifest):
        return value.to_dict()
    if not isinstance(value, Mapping):
        raise MutationManifestError(
            reason="not_a_dict",
            field_path="",
            expected="dict",
        )
    manifest = MutationManifest.from_dict(dict(value))
    return manifest.to_dict()


def _discover_error_code(value: Any) -> str | None:
    for key in ("code", "error_code", "reason_code"):
        field = _get(value, key)
        if isinstance(field, str) and field:
            return field
    error = _get(value, "error")
    if isinstance(error, Mapping):
        for key in ("code", "error_code", "reason_code", "type"):
            field = error.get(key)
            if isinstance(field, str) and field:
                return field
    return None


def _discover_error_message(value: Any) -> str:
    for key in ("message", "error"):
        field = _get(value, key)
        if isinstance(field, str) and field:
            return field
    error = _get(value, "error")
    if isinstance(error, Mapping):
        field = error.get("message")
        if isinstance(field, str) and field:
            return field
    return "Host discover failed."


def _host_discover_reason_code(error_code: str | None) -> str:
    if error_code in _UNRESOLVED_TARGET_CODES:
        return UNRESOLVED_TARGET
    if error_code in _UNSUPPORTED_DELTA_CODES or (
        isinstance(error_code, str)
        and error_code.startswith("segment_")
        and error_code.endswith("_requires_future_executor")
    ):
        return UNSUPPORTED_DELTA_ACTION
    return HOST_DISCOVER_FAILED


def _get(value: Any, key: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(key)
    return getattr(value, key, None)


def _source_artifact_ids(
    resolved_inputs: dict[str, NodeResult],
) -> tuple[uuid.UUID, ...]:
    return tuple(
        result.artifact_id
        for result in resolved_inputs.values()
        if result.artifact_id is not None
    )


__all__ = [
    "HETEROGENEOUS_DELTA",
    "HELD_FOR_REVIEW",
    "HOST_DISCOVER_FAILED",
    "HostResolveBoundary",
    "UNRESOLVED_TARGET",
    "UNSUPPORTED_DELTA_ACTION",
]
