"""Compile legacy chain-step text into ``GraphSpec``.

This is the text-front sibling of ``compile_operator_sequence``. It consumes
the exact ``chain_steps`` surface persisted on ratified apply records and
classifies graph primitives through the same ``forge_bridge.graph`` predicates
that the legacy chain engine uses. The compiler only makes the linear
``__previous_result__`` wire explicit; execution and authority stay in the
dispatch layer.
"""
from __future__ import annotations

import json
import re
import shlex
from collections.abc import Sequence
from typing import Any

from forge_bridge.composition.admission import AdmissionRejected, admit_operator
from forge_bridge.composition.graph_spec import Edge, GraphSpec, NodeSpec
from forge_bridge.graph import (
    CollectNode,
    CommitNode,
    FilterNode,
    ForEachNode,
    IfGateNode,
    is_collect_step,
    is_commit_step,
    is_filter_step,
    is_foreach_step,
    is_if_step,
    is_select_step,
    is_stage_step,
    parse_foreach_step,
)
from forge_bridge.graph.ports import PortContract, PortTopology

_SAFE_NODE_RE = re.compile(r"[^0-9A-Za-z_]+")


class ChainCompileError(ValueError):
    """Raised when a chain step cannot be represented by admitted graph IR."""


def compile_chain_steps(steps: Sequence[str]) -> GraphSpec:
    """Compile linear chain-step text into a degenerate ``GraphSpec``.

    Each adjacent pair is wired through a single ``input`` port, mirroring the
    legacy engine's ``__previous_result__`` handoff. Unknown or unadmitted
    operator tokens fail closed; the production apply path remains legacy in
    slice 4, so rejection here is an offline compiler finding.
    """

    nodes: list[NodeSpec] = []
    edges: list[Edge] = []
    for index, raw_step in enumerate(steps):
        step_text = _clean_step(raw_step, index)
        node = _node_for_step(step_text, index)
        if index > 0:
            port = _input_port(node)
            node = _with_input_port(node, port)
            edges.append(
                Edge(
                    from_node=nodes[-1].node_id,
                    to_node=node.node_id,
                    to_port=port,
                )
            )
        nodes.append(node)
    return GraphSpec(nodes=tuple(nodes), edges=tuple(edges))


def _node_for_step(step_text: str, index: int) -> NodeSpec:
    if is_foreach_step(step_text):
        return _admitted_node(
            index,
            "foreach",
            output_port=ForEachNode.port_contract.emits,
            config={
                "step_text": step_text,
                "body": _body_node(parse_foreach_step(step_text), index),
            },
        )
    if is_collect_step(step_text):
        return _admitted_node(
            index,
            "collect",
            input_ports={"input": CollectNode.port_contract},
            output_port=CollectNode.port_contract.emits,
            config={"step_text": step_text},
        )
    if is_commit_step(step_text):
        return _admitted_node(
            index,
            "commit",
            input_ports={"input": CommitNode.port_contract},
            output_port=CommitNode.port_contract.emits,
            config={"step_text": step_text},
        )
    if is_if_step(step_text):
        return _admitted_node(
            index,
            "if",
            input_ports={"input": IfGateNode.port_contract},
            output_port=IfGateNode.port_contract.emits,
            config={"step_text": step_text},
        )
    if is_stage_step(step_text):
        return _unadmitted_graph_step(step_text, "stage")
    if is_select_step(step_text):
        return _unadmitted_graph_step(step_text, "select")
    if is_filter_step(step_text):
        return _admitted_node(
            index,
            "filter",
            input_ports={"input": FilterNode.port_contract},
            output_port=FilterNode.port_contract.emits,
            config={"step_text": step_text},
        )

    operator_id = _first_token(step_text)
    if not operator_id:
        raise ChainCompileError(f"empty chain step at index {index}")
    return _admitted_node(
        index,
        operator_id,
        output_port=PortTopology.any(),
        config={
            "step_text": step_text,
            "arguments": _step_arguments(step_text),
        },
    )


def _body_node(step_text: str, parent_index: int) -> NodeSpec:
    body = _node_for_step(step_text, parent_index)
    return NodeSpec(
        node_id=f"{body.node_id}_body",
        operator_id=body.operator_id,
        input_ports=body.input_ports or {"item": PortContract.any()},
        output_port=body.output_port,
        backend_id=body.backend_id,
        config=body.config,
    )


def _admitted_node(
    index: int,
    operator_id: str,
    *,
    input_ports: dict[str, PortContract] | None = None,
    output_port: PortTopology,
    config: dict[str, Any],
) -> NodeSpec:
    try:
        admit_operator(operator_id)
    except AdmissionRejected as exc:
        raise ChainCompileError(
            f"chain step {index} operator {operator_id!r} is not admitted"
        ) from exc
    return NodeSpec(
        node_id=f"{_safe_node_name(operator_id)}#{index}",
        operator_id=operator_id,
        input_ports=dict(input_ports or {}),
        output_port=output_port,
        config=config,
    )


def _unadmitted_graph_step(step_text: str, operator_id: str) -> NodeSpec:
    try:
        admit_operator(operator_id)
    except AdmissionRejected as exc:
        raise ChainCompileError(
            f"graph step {step_text!r} is recognized as {operator_id!r} "
            "but is not admitted to composition"
        ) from exc
    raise AssertionError(f"Unhandled admitted graph step: {operator_id!r}")


def _input_port(node: NodeSpec) -> str:
    if node.input_ports:
        return next(iter(node.input_ports))
    return "input"


def _with_input_port(node: NodeSpec, port: str) -> NodeSpec:
    if port in node.input_ports:
        return node
    ports = dict(node.input_ports)
    ports[port] = PortContract.any()
    return NodeSpec(
        node_id=node.node_id,
        operator_id=node.operator_id,
        input_ports=ports,
        output_port=node.output_port,
        backend_id=node.backend_id,
        config=node.config,
    )


def _clean_step(step: str, index: int) -> str:
    if not isinstance(step, str):
        raise ChainCompileError(f"chain step {index} must be text")
    text = step.strip()
    if not text:
        raise ChainCompileError(f"empty chain step at index {index}")
    return text


def _first_token(step_text: str) -> str:
    return step_text.split(maxsplit=1)[0] if step_text.strip() else ""


def _step_arguments(step_text: str) -> dict[str, Any]:
    json_args = _json_arguments(step_text)
    token_args = _token_arguments(step_text)
    return {**json_args, **token_args}


def _json_arguments(step_text: str) -> dict[str, Any]:
    if "{" not in step_text:
        return {}
    try:
        decoded = json.loads(step_text[step_text.find("{"):])
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    if not isinstance(decoded, dict):
        return {}
    params = decoded.get("params", decoded)
    return dict(params) if isinstance(params, dict) else {}


def _token_arguments(step_text: str) -> dict[str, Any]:
    args: dict[str, Any] = {}
    try:
        tokens = shlex.split(step_text)
    except ValueError:
        return args
    for token in tokens[1:]:
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        if key:
            args[key] = _literal(value)
    return args


def _literal(value: str) -> Any:
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered == "null":
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def _safe_node_name(value: str) -> str:
    return _SAFE_NODE_RE.sub("_", value.strip()).strip("_").lower() or "step"


__all__ = ["ChainCompileError", "compile_chain_steps"]
