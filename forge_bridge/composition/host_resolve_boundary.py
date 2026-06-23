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

_APPLY_TOOL_BY_DELTA_CLASS: dict[tuple[str, str], str] = {
    ("updated", "segment"): "flame_rename_shots",
}


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
        entries = _delta_entries(resolved_inputs)
        delta_classes = {
            (str(entry.get("action")), str(entry.get("object_type")))
            for entry in entries
        }
        if len(delta_classes) != 1:
            return self._error(
                admission.resolved_class,
                srcs,
                reason_code=HETEROGENEOUS_DELTA,
                message="delta_to_manifest requires one homogeneous delta class.",
            )

        delta_class = next(iter(delta_classes))
        apply_tool = _APPLY_TOOL_BY_DELTA_CLASS.get(delta_class)
        if apply_tool is None:
            return self._error(
                admission.resolved_class,
                srcs,
                reason_code=UNSUPPORTED_DELTA_ACTION,
                message=(
                    "delta_to_manifest does not support "
                    f"action={delta_class[0]!r} object_type={delta_class[1]!r}."
                ),
            )
        if self._run_discover is None:
            return self._error(
                admission.resolved_class,
                srcs,
                reason_code=UNRESOLVED_TARGET,
                message="No host discover runner is configured.",
            )

        request = {
            "entries": [
                {
                    "identity": dict(entry.get("metadata") or {}),
                    "intent": dict(entry.get("after") or {}),
                }
                for entry in entries
            ]
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
                    reason_code=(
                        UNRESOLVED_TARGET
                        if discover_error == "identity_unresolved"
                        else HOST_DISCOVER_FAILED
                    ),
                    message=_discover_error_message(manifest),
                )
            manifest_dict = _manifest_dict(manifest)
        except Exception as exc:  # noqa: BLE001
            discover_error = _discover_error_code(exc)
            return self._error(
                admission.resolved_class,
                srcs,
                reason_code=(
                    UNRESOLVED_TARGET
                    if discover_error == "identity_unresolved"
                    else HOST_DISCOVER_FAILED
                ),
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


def _delta_entries(resolved_inputs: dict[str, NodeResult]) -> list[dict[str, Any]]:
    for result in resolved_inputs.values():
        if not result.has_usable_output or not isinstance(result.output, Mapping):
            continue
        deltas = result.output.get("deltas")
        if not isinstance(deltas, list):
            continue
        entries: list[dict[str, Any]] = []
        for delta in deltas:
            if isinstance(delta, Mapping) and isinstance(delta.get("entries"), list):
                entries.extend(
                    dict(entry)
                    for entry in delta["entries"]
                    if isinstance(entry, Mapping)
                )
            elif isinstance(delta, Mapping):
                entries.append(dict(delta))
        return entries
    return []


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
    "HOST_DISCOVER_FAILED",
    "HostResolveBoundary",
    "UNRESOLVED_TARGET",
    "UNSUPPORTED_DELTA_ACTION",
]
