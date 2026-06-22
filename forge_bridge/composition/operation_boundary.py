"""Operation-dispatch boundary for federation peer operations.

This boundary is intentionally import-free with respect to forge-core,
Traffik, and Pipeline. The daemon edge injects the operation runner; composition
only translates ``NodeSpec``/``NodeResult`` envelopes into the narrow call
shape and maps the returned operation data back into a ``NodeResult``.
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
from forge_bridge.graph.ports import PortContract, PortTopology

OPERATION_INPUT_ERROR = "operation_invalid_input"
OPERATION_UNAVAILABLE = "operation_dispatch_unavailable"
OPERATION_EXCEPTION = "operation_dispatch_exception"

_OPTIONAL_METADATA_KEYS = (
    "bridge_asset_ids",
    "idempotency_key",
    "project_id",
    "requested_by",
)


class OperationDispatchBoundary:
    """Dispatch admitted operation nodes through an injected operation runner."""

    input_ports = {"step_plan": PortContract.manifest_gate()}
    output_port = PortTopology.manifest()

    def __init__(
        self,
        *,
        run_operation: Callable[..., Any] | None = None,
        run_id: uuid.UUID | None = None,
        artifact_id_factory: Callable[[], uuid.UUID] = uuid.uuid4,
    ) -> None:
        # Daemon-edge adapters must build the real forge_core OperationRequest:
        # state/step_plan live under params, while bridge_asset_ids and
        # idempotency_key are OperationRequest fields. Keep that mapping outside
        # composition; this boundary only owns the injected call seam.
        self._run_operation = run_operation
        self._run_id = run_id or uuid.uuid4()
        self._artifact_id_factory = artifact_id_factory

    async def dispatch(
        self,
        node: NodeSpec,
        resolved_inputs: dict[str, NodeResult],
    ) -> NodeResult:
        try:
            admission = admit_operator(node.operator_id)
        except AdmissionRejected as exc:
            raise UnsupportedCompositionNodeError(
                f"{node.operator_id!r} is not admitted to the operation boundary"
            ) from exc
        if admission.dispatch_kind != "operation":
            raise UnsupportedCompositionNodeError(
                f"{node.operator_id!r} is admitted but not an operation "
                f"(dispatch_kind={admission.dispatch_kind!r}); route via "
                "UnifiedDispatch"
            )

        arguments = _node_arguments(node)
        state = arguments.get("state")
        step_plan = _step_plan(arguments, resolved_inputs)
        srcs = _source_artifact_ids(resolved_inputs)
        if not isinstance(state, Mapping):
            return self._error(
                admission.resolved_class,
                srcs,
                reason_code=OPERATION_INPUT_ERROR,
                message="Operation dispatch requires arguments.state.",
            )
        if not isinstance(step_plan, Mapping):
            return self._error(
                admission.resolved_class,
                srcs,
                reason_code=OPERATION_INPUT_ERROR,
                message=(
                    "Operation dispatch requires a step_plan from the "
                    "step_plan edge or arguments.step_plan."
                ),
            )
        if self._run_operation is None:
            return self._error(
                admission.resolved_class,
                srcs,
                reason_code=OPERATION_UNAVAILABLE,
                message="No operation dispatch runner is configured.",
            )

        metadata = {
            key: arguments[key]
            for key in _OPTIONAL_METADATA_KEYS
            if key in arguments
        }
        try:
            result = self._run_operation(
                node.operator_id,
                state=dict(state),
                step_plan=dict(step_plan),
                receipt_path=node.config.get("receipt_path"),
                **metadata,
            )
            if inspect.isawaitable(result):
                result = await result
        except Exception as exc:  # noqa: BLE001
            return self._error(
                admission.resolved_class,
                srcs,
                reason_code=OPERATION_EXCEPTION,
                message=str(exc),
            )

        return self._result_to_node(
            result,
            resolved_class=admission.resolved_class,
            source_artifact_ids=srcs,
        )

    def _result_to_node(
        self,
        operation_result: Any,
        *,
        resolved_class: str,
        source_artifact_ids: tuple[uuid.UUID, ...],
    ) -> NodeResult:
        data = _operation_data(operation_result)
        status = _operation_status(operation_result, data)
        if status == "partial":
            return NodeResult(
                status="partial",
                run_id=self._run_id,
                artifact_id=self._artifact_id_factory(),
                output=data,
                output_topology={"kind": "manifest"},
                fidelity=_operation_fidelity(operation_result, data),
                source_artifact_ids=source_artifact_ids,
                resolved_class=resolved_class,
            )
        if status == "error":
            return self._error(
                resolved_class,
                source_artifact_ids,
                reason_code=_operation_reason(operation_result, data),
                message=_operation_message(operation_result, data),
            )
        return NodeResult(
            status="ok",
            run_id=self._run_id,
            artifact_id=self._artifact_id_factory(),
            output=data,
            output_topology={"kind": "manifest"},
            source_artifact_ids=source_artifact_ids,
            resolved_class=resolved_class,
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
            reason_code=reason_code,
            message=message,
            source_artifact_ids=source_artifact_ids,
            resolved_class=resolved_class,
            control_signal="skip",
        )


def _node_arguments(node: NodeSpec) -> dict[str, Any]:
    raw = node.config.get("arguments")
    if raw is None:
        raw = node.config.get("args")
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise TypeError(f"node {node.node_id!r} arguments must be a mapping")
    return dict(raw)


def _step_plan(
    arguments: dict[str, Any],
    resolved_inputs: dict[str, NodeResult],
) -> Any:
    edge = resolved_inputs.get("step_plan")
    if edge is not None:
        return edge.output
    return arguments.get("step_plan")


def _source_artifact_ids(
    resolved_inputs: dict[str, NodeResult],
) -> tuple[uuid.UUID, ...]:
    return tuple(
        result.artifact_id
        for result in resolved_inputs.values()
        if result.artifact_id is not None
    )


def _operation_data(operation_result: Any) -> dict[str, Any]:
    data = _get(operation_result, "data")
    if isinstance(data, Mapping):
        return dict(data)
    if isinstance(operation_result, Mapping):
        if isinstance(operation_result.get("data"), Mapping):
            return dict(operation_result["data"])
        return dict(operation_result)
    packet = _get(operation_result, "packet")
    if isinstance(packet, Mapping):
        return dict(packet)
    return {"result": operation_result}


def _operation_status(operation_result: Any, data: dict[str, Any]) -> str:
    raw = (
        _get(operation_result, "status")
        or _get(operation_result, "outcome")
        or data.get("status")
        or data.get("outcome")
    )
    token = str(getattr(raw, "value", raw or "")).lower()
    if token in {"succeeded", "success", "ok"}:
        return "ok"
    if token == "partial":
        return "partial"
    if token in {"failed", "failure", "error", "no_provider"}:
        return "error"
    if data.get("error") or data.get("failure"):
        return "error"
    return "error"


def _operation_fidelity(operation_result: Any, data: dict[str, Any]) -> dict[str, Any] | None:
    fidelity = (
        _get(operation_result, "partial_fidelity_report")
        or _get(operation_result, "fidelity")
        or data.get("partial_fidelity_report")
        or data.get("fidelity")
    )
    return dict(fidelity) if isinstance(fidelity, Mapping) else None


def _operation_reason(operation_result: Any, data: dict[str, Any]) -> str:
    value = (
        _get(operation_result, "error_code")
        or _get(operation_result, "reason_code")
        or data.get("error_code")
        or data.get("reason_code")
        or data.get("code")
        or "operation_failed"
    )
    return str(value)


def _operation_message(operation_result: Any, data: dict[str, Any]) -> str:
    value = (
        _get(operation_result, "error")
        or _get(operation_result, "message")
        or data.get("error")
        or data.get("message")
        or "Operation dispatch failed."
    )
    return str(value)


def _get(value: Any, key: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(key)
    return getattr(value, key, None)
