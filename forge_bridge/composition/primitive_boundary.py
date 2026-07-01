"""In-process graph primitives for the composition executor.

Primitive nodes are value transforms. Unlike operator dispatch, a primitive may
consume the upstream edge value as data. That does not relax the M1
operator-boundary rule: MCP/operator kwargs are still lowered only from static
configuration by the MCP boundary.
"""
from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Callable

from forge_bridge.composition.admission import admit_operator
from forge_bridge.composition.graph_spec import NodeSpec
from forge_bridge.composition.node_result import NodeResult
from forge_bridge.graph.collect import CollectError, CollectNode
from forge_bridge.graph.editorial_delta import RenameDeltaNode
from forge_bridge.graph.filter import (
    FilterNode,
    FilterPredicate,
    GraphInputError,
    PredicateParseError,
    parse_filter_step,
)
from forge_bridge.graph.if_gate import IfGateNode, parse_if_step
from forge_bridge.graph.ports import PortTopology, infer_topology


@dataclass
class PrimitiveBoundary:
    """Dispatch in-process graph primitives."""

    artifact_id_factory: Callable[[], uuid.UUID] = uuid.uuid4

    async def dispatch(
        self,
        node: NodeSpec,
        resolved_inputs: dict[str, NodeResult],
    ) -> NodeResult:
        admission = admit_operator(node.operator_id)
        if admission.dispatch_kind != "primitive":
            return _error(
                "not_primitive",
                f"Operator {node.operator_id!r} is not a primitive.",
                admission.resolved_class,
        )
        if node.operator_id == "filter":
            return _run_filter(
                node,
                resolved_inputs,
                admission.resolved_class,
                self.artifact_id_factory,
            )
        if node.operator_id == "if":
            return _run_if_gate(
                node,
                resolved_inputs,
                admission.resolved_class,
                self.artifact_id_factory,
            )
        if node.operator_id == "select_delta":
            return _run_select_delta(
                node,
                resolved_inputs,
                admission.resolved_class,
                self.artifact_id_factory,
            )
        if node.operator_id == "collect":
            return _run_collect(
                node,
                resolved_inputs,
                admission.resolved_class,
                self.artifact_id_factory,
            )
        if node.operator_id == "rename_delta_entry":
            return _run_rename_delta_entry(
                node,
                resolved_inputs,
                admission.resolved_class,
                self.artifact_id_factory,
            )
        return _error(
            "unknown_primitive",
            f"Primitive {node.operator_id!r} is not implemented.",
            admission.resolved_class,
        )


def _run_filter(
    node: NodeSpec,
    resolved_inputs: dict[str, NodeResult],
    resolved_class: str,
    artifact_id_factory: Callable[[], uuid.UUID],
) -> NodeResult:
    if len(resolved_inputs) != 1:
        return _error(
            "invalid_primitive_input",
            "Filter requires exactly one upstream input.",
            resolved_class,
        )
    upstream = next(iter(resolved_inputs.values()))
    if not upstream.has_usable_output:
        return _error(
            "invalid_primitive_input",
            "Filter requires a usable upstream output.",
            resolved_class,
            source_artifact_ids=_source_artifact_ids(resolved_inputs),
        )

    try:
        predicate = _filter_predicate(node.config)
        output = FilterNode(predicate).run(upstream.output)
    except (GraphInputError, PredicateParseError) as exc:
        return _error(
            getattr(exc, "code", "primitive_error"),
            getattr(exc, "message", str(exc)),
            resolved_class,
            source_artifact_ids=_source_artifact_ids(resolved_inputs),
        )

    topology = infer_topology(output)
    return NodeResult(
        status="ok",
        run_id=uuid.uuid4(),
        artifact_id=artifact_id_factory(),
        output=output,
        output_topology=topology.to_dict(),
        artifact_type=topology.item_type if topology.kind == "list" else topology.kind,
        source_artifact_ids=_source_artifact_ids(resolved_inputs),
        resolved_class=resolved_class,
    )


def _run_if_gate(
    node: NodeSpec,
    resolved_inputs: dict[str, NodeResult],
    resolved_class: str,
    artifact_id_factory: Callable[[], uuid.UUID],
) -> NodeResult:
    if len(resolved_inputs) != 1:
        return _error(
            "invalid_primitive_input",
            "IfGate requires exactly one upstream input.",
            resolved_class,
        )
    upstream = next(iter(resolved_inputs.values()))
    if not upstream.has_usable_output:
        return _error(
            "invalid_primitive_input",
            "IfGate requires a usable upstream output.",
            resolved_class,
            source_artifact_ids=_source_artifact_ids(resolved_inputs),
        )

    try:
        predicate = _if_predicate(node.config)
        output = IfGateNode(predicate).run(upstream.output)
    except (GraphInputError, PredicateParseError) as exc:
        return _error(
            getattr(exc, "code", "primitive_error"),
            getattr(exc, "message", str(exc)),
            resolved_class,
            source_artifact_ids=_source_artifact_ids(resolved_inputs),
        )

    topology = infer_topology(output)
    return NodeResult(
        status="ok",
        run_id=uuid.uuid4(),
        artifact_id=artifact_id_factory(),
        output=output,
        output_topology=topology.to_dict(),
        artifact_type=topology.item_type if topology.kind == "list" else topology.kind,
        source_artifact_ids=_source_artifact_ids(resolved_inputs),
        resolved_class=resolved_class,
        control_signal="skip" if output.get("execution_state") == "skipped" else None,
    )


def _run_select_delta(
    node: NodeSpec,
    resolved_inputs: dict[str, NodeResult],
    resolved_class: str,
    artifact_id_factory: Callable[[], uuid.UUID],
) -> NodeResult:
    if len(resolved_inputs) != 1:
        return _error(
            "invalid_primitive_input",
            "SelectDelta requires exactly one upstream input.",
            resolved_class,
        )
    upstream = next(iter(resolved_inputs.values()))
    srcs = _source_artifact_ids(resolved_inputs)
    if not upstream.has_usable_output:
        return _error(
            "invalid_primitive_input",
            "SelectDelta requires a usable upstream output.",
            resolved_class,
            source_artifact_ids=srcs,
        )
    if not isinstance(upstream.output, Mapping):
        return _error(
            "invalid_primitive_input",
            "SelectDelta requires an upstream manifest output.",
            resolved_class,
            source_artifact_ids=srcs,
        )

    deltas = upstream.output.get("deltas")
    if not isinstance(deltas, list):
        return _error(
            "missing_delta",
            "SelectDelta requires upstream output.deltas to be a list.",
            resolved_class,
            source_artifact_ids=srcs,
        )
    if not deltas:
        return _error(
            "missing_delta",
            "SelectDelta found no upstream deltas to select.",
            resolved_class,
            source_artifact_ids=srcs,
        )

    index = node.config.get("index", 0)
    if isinstance(index, bool) or not isinstance(index, int):
        return _error(
            "invalid_delta_selection",
            "SelectDelta index must be an integer.",
            resolved_class,
            source_artifact_ids=srcs,
        )
    if index < 0 or index >= len(deltas):
        return _error(
            "invalid_delta_selection",
            f"SelectDelta index {index} is outside {len(deltas)} available delta(s).",
            resolved_class,
            source_artifact_ids=srcs,
        )

    delta = deltas[index]
    if not isinstance(delta, Mapping):
        return _error(
            "invalid_delta_selection",
            "SelectDelta selected delta must be a manifest object.",
            resolved_class,
            source_artifact_ids=srcs,
        )

    return NodeResult(
        status="ok",
        run_id=uuid.uuid4(),
        artifact_id=artifact_id_factory(),
        output=dict(delta),
        output_topology=PortTopology.manifest().to_dict(),
        artifact_type="manifest",
        source_artifact_ids=srcs,
        resolved_class=resolved_class,
    )


def _run_collect(
    node: NodeSpec,
    resolved_inputs: dict[str, NodeResult],
    resolved_class: str,
    artifact_id_factory: Callable[[], uuid.UUID],
) -> NodeResult:
    if len(resolved_inputs) != 1:
        return _error(
            "invalid_primitive_input",
            "Collect requires exactly one upstream input.",
            resolved_class,
        )
    upstream = next(iter(resolved_inputs.values()))
    srcs = _source_artifact_ids(resolved_inputs)
    if not upstream.has_usable_output:
        return _error(
            "invalid_primitive_input",
            "Collect requires a usable upstream output.",
            resolved_class,
            source_artifact_ids=srcs,
        )

    try:
        output = CollectNode().run(upstream.output)
    except CollectError as exc:
        return _error(
            getattr(exc, "code", "primitive_error"),
            getattr(exc, "message", str(exc)),
            resolved_class,
            source_artifact_ids=srcs,
        )

    topology = infer_topology(output)
    return NodeResult(
        status="ok",
        run_id=uuid.uuid4(),
        artifact_id=artifact_id_factory(),
        output=output,
        output_topology=topology.to_dict(),
        artifact_type=topology.item_type if topology.kind == "list" else topology.kind,
        source_artifact_ids=srcs,
        resolved_class=resolved_class,
    )


def _run_rename_delta_entry(
    node: NodeSpec,
    resolved_inputs: dict[str, NodeResult],
    resolved_class: str,
    artifact_id_factory: Callable[[], uuid.UUID],
) -> NodeResult:
    if len(resolved_inputs) != 1:
        return _error(
            "invalid_primitive_input",
            "RenameDeltaEntry requires exactly one upstream input.",
            resolved_class,
        )
    upstream = next(iter(resolved_inputs.values()))
    srcs = _source_artifact_ids(resolved_inputs)
    if not upstream.has_usable_output:
        return _error(
            "invalid_primitive_input",
            "RenameDeltaEntry requires a usable upstream output.",
            resolved_class,
            source_artifact_ids=srcs,
        )

    new_name = node.config.get("new_name")
    sequence_name = node.config.get("sequence_name")
    if not isinstance(new_name, str) or not isinstance(sequence_name, str):
        return _error(
            "invalid_rename_config",
            "RenameDeltaEntry requires str config new_name + sequence_name.",
            resolved_class,
            source_artifact_ids=srcs,
        )

    try:
        segment = _extract_single_segment(upstream.output)
        output = RenameDeltaNode(
            new_name=new_name, sequence_name=sequence_name
        ).run(segment)
    except Exception as exc:  # noqa: BLE001 - boundary converts author failure
        return _error(
            "rename_delta_author_failed",
            f"{type(exc).__name__}: {exc}",
            resolved_class,
            source_artifact_ids=srcs,
        )

    topology = infer_topology(output)
    return NodeResult(
        status="ok",
        run_id=uuid.uuid4(),
        artifact_id=artifact_id_factory(),
        output=output,
        output_topology=topology.to_dict(),
        artifact_type=topology.item_type if topology.kind == "list" else topology.kind,
        source_artifact_ids=srcs,
        resolved_class=resolved_class,
    )


def _extract_single_segment(payload: Any) -> dict[str, Any]:
    """The one segment dict inside a foreach per-item payload.

    Foreach hands a body a collection-of-one payload (``{"segments": [seg], ...}``)
    for a keyed source, or the bare item for a manifest-like/list source. Pull the
    single segment dict out of whichever shape arrives.
    """
    if isinstance(payload, Mapping):
        if "seg_name" in payload:
            return dict(payload)
        segments = payload.get("segments")
        if isinstance(segments, list) and segments and isinstance(segments[0], Mapping):
            return dict(segments[0])
        raise ValueError("RenameDeltaEntry payload carries no segment.")
    if isinstance(payload, list) and payload and isinstance(payload[0], Mapping):
        return dict(payload[0])
    raise ValueError("RenameDeltaEntry requires a segment-shaped payload.")


def _filter_predicate(config: dict[str, Any]) -> FilterPredicate:
    predicate = config.get("predicate")
    if isinstance(predicate, FilterPredicate):
        return predicate
    if isinstance(predicate, dict):
        return FilterPredicate.from_dict(predicate)
    step_text = config.get("step_text")
    if isinstance(step_text, str):
        return parse_filter_step(step_text)
    raise PredicateParseError("missing_predicate", "Filter predicate is required.")


def _if_predicate(config: dict[str, Any]) -> FilterPredicate:
    predicate = config.get("predicate")
    if isinstance(predicate, FilterPredicate):
        return predicate
    if isinstance(predicate, dict):
        return FilterPredicate.from_dict(predicate)
    step_text = config.get("step_text")
    if isinstance(step_text, str):
        return parse_if_step(step_text)
    raise PredicateParseError("missing_predicate", "IfGate predicate is required.")


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
    resolved_class: str | None,
    *,
    source_artifact_ids: tuple[uuid.UUID, ...] = (),
) -> NodeResult:
    return NodeResult(
        status="error",
        run_id=uuid.uuid4(),
        reason_code=reason_code,
        message=message,
        source_artifact_ids=source_artifact_ids,
        resolved_class=resolved_class,
    )
