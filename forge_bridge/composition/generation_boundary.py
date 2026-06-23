"""Generation-dispatch boundary for terminal generation operators.

The graph composes the ``author_prompt`` capability, not the forge-generators
package. The package-specific runner is injected at the orchestration edge;
composition only validates invocation arguments and maps a terminal generation
artifact into a ``NodeResult``.
"""
from __future__ import annotations

import inspect
import uuid
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from forge_bridge.composition.admission import AdmissionRejected, admit_operator
from forge_bridge.composition.boundary import UnsupportedCompositionNodeError
from forge_bridge.composition.graph_spec import NodeSpec
from forge_bridge.composition.node_result import NodeResult

GENERATION_INPUT_ERROR = "generation_invalid_input"
GENERATION_UNAVAILABLE = "generation_dispatch_unavailable"
GENERATION_EXCEPTION = "generation_dispatch_exception"
GENERATION_FAILED = "generation_failed"


class GenerationDispatchBoundary:
    """Dispatch admitted generation nodes through an injected generation runner."""

    def __init__(
        self,
        *,
        run_generation: Callable[..., Any] | None = None,
        run_id: uuid.UUID | None = None,
        artifact_id_factory: Callable[[], uuid.UUID] = uuid.uuid4,
    ) -> None:
        self._run_generation = run_generation
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
                f"{node.operator_id!r} is not admitted to the generation boundary"
            ) from exc
        if admission.dispatch_kind != "generation":
            raise UnsupportedCompositionNodeError(
                f"{node.operator_id!r} is admitted but not a generation operator "
                f"(dispatch_kind={admission.dispatch_kind!r}); route via "
                "UnifiedDispatch"
            )

        arguments = _node_arguments(node)
        intent = _value_from_edge_or_args("intent", arguments, resolved_inputs)
        srcs = _source_artifact_ids(resolved_inputs)
        if not isinstance(intent, str) or not intent.strip():
            return self._error(
                admission.resolved_class,
                srcs,
                reason_code=GENERATION_INPUT_ERROR,
                message="Generation dispatch requires a non-empty intent.",
            )
        if self._run_generation is None:
            return self._error(
                admission.resolved_class,
                srcs,
                reason_code=GENERATION_UNAVAILABLE,
                message="No generation dispatch runner is configured.",
            )

        try:
            artifact = self._run_generation(
                node.operator_id,
                intent=intent.strip(),
                context=_value_from_edge_or_args(
                    "context", arguments, resolved_inputs
                ),
                target=_value_from_edge_or_args("target", arguments, resolved_inputs),
                style=_value_from_edge_or_args("style", arguments, resolved_inputs),
            )
            if inspect.isawaitable(artifact):
                artifact = await artifact
        except Exception as exc:  # noqa: BLE001
            return self._error(
                admission.resolved_class,
                srcs,
                reason_code=GENERATION_EXCEPTION,
                message=str(exc),
            )

        return self._artifact_to_node(
            artifact,
            resolved_class=admission.resolved_class,
            source_artifact_ids=srcs,
        )

    def _artifact_to_node(
        self,
        artifact: Any,
        *,
        resolved_class: str,
        source_artifact_ids: tuple[uuid.UUID, ...],
    ) -> NodeResult:
        data = _artifact_data(artifact)
        text = _artifact_text(artifact, data)
        output = {"text": text, "artifact": data}
        status = _artifact_status(artifact, data)
        if status == "error":
            return self._error(
                resolved_class,
                source_artifact_ids,
                reason_code=_artifact_reason(artifact, data),
                message=_artifact_message(artifact, data),
            )
        return NodeResult(
            status=status,
            run_id=self._run_id,
            artifact_id=self._artifact_id_factory(),
            output=output,
            output_topology={"kind": "manifest"},
            artifact_type=str(data.get("media_kind") or "text/plain"),
            fidelity=_artifact_fidelity(artifact, data) if status == "partial" else None,
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


def _value_from_edge_or_args(
    key: str,
    arguments: dict[str, Any],
    resolved_inputs: dict[str, NodeResult],
) -> Any:
    edge = resolved_inputs.get(key)
    if edge is not None:
        value = edge.output
        if isinstance(value, Mapping) and key in value:
            return value[key]
        return value
    return arguments.get(key)


def _source_artifact_ids(
    resolved_inputs: dict[str, NodeResult],
) -> tuple[uuid.UUID, ...]:
    return tuple(
        result.artifact_id
        for result in resolved_inputs.values()
        if result.artifact_id is not None
    )


def _artifact_data(artifact: Any) -> dict[str, Any]:
    if isinstance(artifact, Mapping):
        return dict(artifact)
    to_transport = getattr(artifact, "to_transport_dict", None)
    if callable(to_transport):
        return dict(to_transport())
    model_dump = getattr(artifact, "model_dump", None)
    if callable(model_dump):
        return dict(model_dump(mode="json", exclude_none=False))
    return dict(getattr(artifact, "__dict__", {"artifact": repr(artifact)}))


def _artifact_status(artifact: Any, data: dict[str, Any]) -> str:
    raw = _get(artifact, "lifecycle_state") or data.get("lifecycle_state")
    token = str(getattr(raw, "value", raw or "")).lower()
    if token in {"complete", "completed", "succeeded", "success", "ok"}:
        return "ok"
    if token == "partial":
        return "partial"
    return "error"


def _artifact_text(artifact: Any, data: dict[str, Any]) -> str:
    for source in (data, artifact):
        for key in ("text", "final_text"):
            value = _get(source, key)
            if isinstance(value, str) and value:
                return value
    locator = _get(artifact, "media_locator") or data.get("media_locator")
    if isinstance(locator, str) and locator:
        path = Path(locator.removeprefix("file://")).expanduser()
        if path.exists():
            return path.read_text(encoding="utf-8")
    return ""


def _artifact_fidelity(artifact: Any, data: dict[str, Any]) -> dict[str, Any] | None:
    value = (
        _get(artifact, "partial_fidelity_report")
        or data.get("partial_fidelity_report")
        or data.get("fidelity")
    )
    return dict(value) if isinstance(value, Mapping) else None


def _artifact_reason(artifact: Any, data: dict[str, Any]) -> str:
    value = (
        _get(artifact, "failure_reason")
        or data.get("failure_reason")
        or data.get("reason_code")
        or data.get("error_code")
        or GENERATION_FAILED
    )
    return str(value)


def _artifact_message(artifact: Any, data: dict[str, Any]) -> str:
    value = (
        _get(artifact, "failure_reason")
        or data.get("failure_reason")
        or data.get("message")
        or data.get("error")
        or "Generation dispatch failed."
    )
    return str(value)


def _get(value: Any, key: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(key)
    return getattr(value, key, None)
