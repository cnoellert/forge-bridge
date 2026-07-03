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
    ExtractContextNode,
    FilterNode,
    ForEachNode,
    IfGateNode,
    extract_format_class,
    is_collect_step,
    is_commit_step,
    is_filter_step,
    is_foreach_step,
    is_format_step,
    is_if_step,
    is_select_step,
    is_stage_step,
    parse_foreach_step,
)
from forge_bridge.graph.ports import PortContract, PortTopology

_SAFE_NODE_RE = re.compile(r"[^0-9A-Za-z_]+")

#: The kwarg-input-port an MCP node nominates for edge-sourced scalars (#153).
#: Distinct from the "input" lineage port so the boundary reads only the
#: extractor's scalars dict, never the full prior result.
_KWARG_PORT = "inherited_kwargs"
#: The extractor's own single upstream-consuming input port.
_EXTRACTOR_INPUT_PORT = "input"

#: The reads-only terminal formatter operator (#153 slice 2b). Its ``data``
#: kwarg inherits the WHOLE prior result (a whole-payload handoff), authored by
#: a wrap-flavored extractor rather than the singleton-id extractor.
_FORMAT_RESULT_OP = "format_result"
#: The kwarg the format terminal fills with the whole prior result.
_FORMAT_DATA_KEY = "data"


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
        extractor: NodeSpec | None = None
        if index > 0:
            prior_id = nodes[-1].node_id
            port = _input_port(node)
            node = _with_input_port(node, port)
            edges.append(
                Edge(from_node=prior_id, to_node=node.node_id, to_port=port)
            )
            # #153 — value→kwarg binding. For every non-first MCP node, author a
            # visible extractor consuming the prior node's output and wire its
            # single-key scalars dict into a nominated kwarg-input-port. The
            # boundary merges it UNDER the static step-text args. Over-insertion
            # is safe: the extractor emits ``{}`` when nothing qualifies. The
            # prior→node lineage edge above is kept for lineage/topology.
            if _is_mcp(node.operator_id):
                # A format terminal inherits the WHOLE prior result under
                # ``data`` (legacy ``format_result.data = __previous_result__``),
                # so it gets a wrap-flavored extractor. Every other MCP node gets
                # the singleton-id/sequence extractor. Tool-name-aware
                # edge-authoring is VISIBLE in the GraphSpec, not a runtime branch
                # in the boundary.
                if node.operator_id == _FORMAT_RESULT_OP:
                    extractor = _wrap_extractor_node(index, _FORMAT_DATA_KEY)
                else:
                    extractor = _extractor_node(index)
                node = _with_kwarg_port(node, _KWARG_PORT)
                edges.append(
                    Edge(
                        from_node=prior_id,
                        to_node=extractor.node_id,
                        to_port=_EXTRACTOR_INPUT_PORT,
                    )
                )
                edges.append(
                    Edge(
                        from_node=extractor.node_id,
                        to_node=node.node_id,
                        to_port=_KWARG_PORT,
                    )
                )
        if extractor is not None:
            nodes.append(extractor)
        nodes.append(node)
    return GraphSpec(nodes=tuple(nodes), edges=tuple(edges))


def _is_mcp(operator_id: str) -> bool:
    """True when ``operator_id`` is an admitted MCP-dispatch operator."""
    try:
        return admit_operator(operator_id).dispatch_kind == "mcp"
    except AdmissionRejected:
        return False


def _extractor_node(index: int) -> NodeSpec:
    """Author the value-extractor node feeding step ``index``'s kwarg port."""
    return NodeSpec(
        node_id=f"extract_context#{index}",
        operator_id="extract_context",
        input_ports={_EXTRACTOR_INPUT_PORT: ExtractContextNode.port_contract},
        output_port=ExtractContextNode.port_contract.emits,
        config={},
    )


def _wrap_extractor_node(index: int, wrap_key: str) -> NodeSpec:
    """Author a whole-payload extractor: re-key the prior result under ``wrap_key``.

    Same class / same ``extract_context`` admission / same port contract as the
    singleton extractor — only ``config["wrap_key"]`` differs, which flips
    ``ExtractContextNode`` into wrap mode (``{wrap_key: <whole input>}``). Used
    for the ``format_result.data`` whole-payload handoff (#153 slice 2b).
    """
    return NodeSpec(
        node_id=f"extract_context#{index}",
        operator_id="extract_context",
        input_ports={_EXTRACTOR_INPUT_PORT: ExtractContextNode.port_contract},
        output_port=ExtractContextNode.port_contract.emits,
        config={"wrap_key": wrap_key},
    )


def _with_kwarg_port(node: NodeSpec, port: str) -> NodeSpec:
    """Declare ``port`` as the node's kwarg-input-port (value-edge sink)."""
    ports = dict(node.input_ports)
    ports[port] = PortContract.any()
    config = dict(node.config)
    config["kwarg_input_port"] = port
    return NodeSpec(
        node_id=node.node_id,
        operator_id=node.operator_id,
        input_ports=ports,
        output_port=node.output_port,
        backend_id=node.backend_id,
        config=config,
    )


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
    if is_format_step(step_text):
        return _format_result_node(step_text, index)
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
    if operator_id == _FORMAT_RESULT_OP:
        # The bare ``format_result`` tool-name form (no ``format as`` phrase);
        # route it through the same format-terminal author as the phrase form.
        return _format_result_node(step_text, index)
    return _admitted_node(
        index,
        operator_id,
        output_port=PortTopology.any(),
        config={
            "step_text": step_text,
            "arguments": _step_arguments(step_text),
        },
    )


def _format_result_node(step_text: str, index: int) -> NodeSpec:
    """Author the ``format_result`` terminal node.

    ``format`` rides the static-from-text path exactly as legacy does: parse it
    from the step text and inject it ONLY when the step text did not already
    supply one (mirrors legacy ``if "format" not in params``). ``data`` is NOT
    authored here — it inherits the whole prior result via the wrap-flavored
    extractor edge (authored in ``compile_chain_steps``), merged UNDER these
    static args so an explicit ``data`` in the step text still wins.
    """
    arguments = _step_arguments(step_text)
    format_class = extract_format_class(step_text)
    if format_class is not None and "format" not in arguments:
        arguments["format"] = format_class
    return _admitted_node(
        index,
        _FORMAT_RESULT_OP,
        output_port=PortTopology.any(),
        config={"step_text": step_text, "arguments": arguments},
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
