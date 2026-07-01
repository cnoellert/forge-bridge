"""Foreach boundary for re-entering the shared composition dispatch substrate."""
from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from forge_bridge.composition.graph_spec import NodeSpec
from forge_bridge.composition.node_result import NodeResult
from forge_bridge.graph.foreach import ForEachNode, ForeachInputError
from forge_bridge.graph.ports import infer_topology

ReenterDispatch = Callable[[NodeSpec, dict[str, NodeResult]], Awaitable[NodeResult]]


@dataclass
class ForeachBoundary:
    """Iterate a collection and re-enter shared dispatch for each item."""

    async def dispatch(
        self,
        node: NodeSpec,
        resolved_inputs: dict[str, NodeResult],
        *,
        reenter: ReenterDispatch,
    ) -> NodeResult:
        try:
            body_node = _body_node(node)
        except TypeError as exc:
            return _error(
                "invalid_foreach_config",
                str(exc),
                node,
                source_artifact_ids=_source_artifact_ids(resolved_inputs),
            )
        foreach = ForEachNode(body_node.operator_id)

        if len(resolved_inputs) != 1:
            return _error(
                "invalid_foreach_input",
                "Foreach requires exactly one upstream input.",
                node,
            )

        upstream = next(iter(resolved_inputs.values()))
        if not upstream.has_usable_output:
            return _error(
                "invalid_foreach_input",
                "Foreach requires a usable upstream output.",
                node,
                source_artifact_ids=_source_artifact_ids(resolved_inputs),
            )

        try:
            items = foreach.items(upstream.output)
        except ForeachInputError as exc:
            return _error(
                str(getattr(exc, "code", "invalid_foreach_input")).lower(),
                getattr(exc, "message", str(exc)),
                node,
                source_artifact_ids=_source_artifact_ids(resolved_inputs),
            )

        iterations = []
        body_port = _body_input_port(body_node)
        for index, item in enumerate(items):
            payload = foreach.iteration_payload(upstream.output, item, index=index)
            item_topology = infer_topology(payload)
            item_input = NodeResult(
                status="ok",
                run_id=uuid.uuid4(),
                artifact_id=uuid.uuid4(),
                output=payload,
                output_topology=item_topology.to_dict(),
                artifact_type=(
                    item_topology.item_type
                    if item_topology.kind == "list"
                    else item_topology.kind
                ),
                source_artifact_ids=_source_artifact_ids(resolved_inputs),
            )
            try:
                body_result = await reenter(body_node, {body_port: item_input})
            except Exception as exc:  # noqa: BLE001 - boundary converts body failure
                body_result = NodeResult(
                    status="error",
                    run_id=uuid.uuid4(),
                    reason_code=type(exc).__name__,
                    message=str(exc),
                )
            if not body_result.has_usable_output:
                return _foreach_error(
                    index,
                    body_node,
                    body_result,
                    node,
                    resolved_inputs,
                )
            if body_result.control_signal == "skip":
                return _error(
                    "unsupported_foreach_body_control_signal",
                    "Foreach body control signals are out of scope for slice 2b.",
                    node,
                    source_artifact_ids=_source_artifact_ids(resolved_inputs),
                )

            body_output = body_result.output
            if not isinstance(body_output, dict):
                body_output = {"value": body_output}
            iterations.append(foreach.wrap_result(
                index=index,
                item=item,
                result=body_output,
                emitted_topology=(
                    body_result.output_topology
                    or infer_topology(body_output).to_dict()
                ),
            ))

        envelope = foreach.envelope(iterations)
        topology = infer_topology(envelope)
        return NodeResult(
            status="ok",
            run_id=uuid.uuid4(),
            artifact_id=uuid.uuid4(),
            output=envelope,
            output_topology=topology.to_dict(),
            artifact_type=topology.item_type if topology.kind == "list" else topology.kind,
            source_artifact_ids=_source_artifact_ids(resolved_inputs),
            resolved_class="primitive.foreach",
        )


def _body_node(node: NodeSpec) -> NodeSpec:
    body = node.config.get("body")
    if not isinstance(body, NodeSpec):
        raise TypeError(f"foreach node {node.node_id!r} requires config['body']")
    return body


def _body_input_port(body_node: NodeSpec) -> str:
    if body_node.input_ports:
        return next(iter(body_node.input_ports))
    return "input"


def _source_artifact_ids(
    resolved_inputs: dict[str, NodeResult],
) -> tuple[uuid.UUID, ...]:
    return tuple(
        result.artifact_id
        for result in resolved_inputs.values()
        if result.artifact_id is not None
    )


def _error(
    reason_code: str,
    message: str,
    node: NodeSpec,
    *,
    source_artifact_ids: tuple[uuid.UUID, ...] = (),
    output: dict[str, Any] | None = None,
) -> NodeResult:
    return NodeResult(
        status="error",
        run_id=uuid.uuid4(),
        reason_code=reason_code,
        message=message,
        source_artifact_ids=source_artifact_ids,
        resolved_class="primitive.foreach",
        output=output,
    )


def _foreach_error(
    index: int,
    body_node: NodeSpec,
    body_result: NodeResult,
    node: NodeSpec,
    resolved_inputs: dict[str, NodeResult],
) -> NodeResult:
    return _error(
        body_result.reason_code or "foreach_body_error",
        body_result.message or "Foreach body iteration failed.",
        node,
        source_artifact_ids=_source_artifact_ids(resolved_inputs),
        output={
            "foreach_step": node.node_id,
            "iteration_index": index,
            "body_step": body_node.operator_id,
            "body_error": {
                "reason_code": body_result.reason_code,
                "message": body_result.message,
            },
        },
    )
