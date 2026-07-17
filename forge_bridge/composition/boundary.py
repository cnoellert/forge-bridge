"""Bridge boundary adapter for M1 composition nodes.

``GraphExecutor`` is intentionally substrate-agnostic: it topo-sorts and hands
named input ``NodeResult``s to a dispatch callable. This module is that first
real dispatch callable for M1/M2 composition: admitted MCP operators wrapped
into bridge-internal ``NodeResult`` envelopes. It requires an async MCP client.

The boundary owns invocation lowering: it translates ``node.config`` into MCP
kwargs, but never invents missing values. Static kwargs come from explicit
``config["arguments"]``/``config["args"]`` or, for compiled plans, from static
``inputs[].metadata.scalars``. Duplicate scalar keys across static inputs fail
closed because no input-order precedence contract exists. When FastMCP raises
its real ``ToolError`` for absent required fields, the boundary classifies the
failure from the advertised input schema rather than parsing Pydantic prose.

Edges may also carry kwarg *values* (#153): when a node nominates a
``config["kwarg_input_port"]``, the boundary sources that port's upstream
``NodeResult.output`` (a scalars dict authored by a visible ``ExtractContextNode``)
and merges it *under* the static kwargs — ``{**edge_scalars, **static}`` — so
step-text arguments always win, mirroring the legacy fold order
(``{**public_inherited, **static}`` in ``console/_step.py``). The merge is purely
mechanical; the which-key extraction meaning lives in the upstream node, never
here. Edges into ports the node does *not* nominate stay value-blind (lineage
only).

Asynchronous generation/make operators are intentionally not admitted here. They
need submit/poll/cost/non-determinism handling. Synchronous reference-producing
makes can be admitted through ``admission.py`` and still dispatch through this
MCP boundary.
"""
from __future__ import annotations

import json
import uuid
from collections.abc import Callable, Mapping
from typing import Any

from mcp.server.fastmcp.exceptions import ToolError

from forge_bridge.composition.admission import AdmissionRejected, admit_operator
from forge_bridge.composition.graph_spec import NodeSpec
from forge_bridge.composition.node_result import NodeResult
from forge_bridge.graph.ports import infer_topology
from forge_bridge.mcp.arguments import normalize_tool_args


class UnsupportedCompositionNodeError(ValueError):
    """A node is outside the admitted MCP composition boundary."""


class StaticScalarCollisionError(ValueError):
    """Two static inputs claim the same invocation argument without precedence."""

    def __init__(
        self,
        *,
        node_id: str,
        key: Any,
        first_input_index: int,
        second_input_index: int,
    ) -> None:
        self.node_id = node_id
        self.key = key
        self.first_input_index = first_input_index
        self.second_input_index = second_input_index
        super().__init__(
            f"node {node_id!r} static input scalar {key!r} is declared by "
            f"inputs {first_input_index} and {second_input_index}; "
            "no precedence contract is declared"
        )


class MCPToolBoundary:
    """Dispatch admitted MCP tools and mint ``NodeResult`` envelopes."""

    def __init__(
        self,
        *,
        mcp: Any | None = None,
        run_id: uuid.UUID | None = None,
        artifact_id_factory: Callable[[], uuid.UUID] = uuid.uuid4,
    ) -> None:
        self._mcp = mcp
        self._run_id = run_id or uuid.uuid4()
        self._artifact_id_factory = artifact_id_factory

    async def dispatch(
        self,
        node: NodeSpec,
        resolved_inputs: dict[str, NodeResult],
    ) -> NodeResult:
        """Execute ``node.operator_id`` and wrap the MCP payload.

        Source lineage is recorded from upstream ``NodeResult.artifact_id``
        values. The executor stays purely mechanical; the boundary mints the
        envelope and lineage.
        """
        try:
            admission = admit_operator(node.operator_id)
        except AdmissionRejected as exc:
            raise UnsupportedCompositionNodeError(
                f"{node.operator_id!r} is not admitted to the M2 dispatch surface"
            ) from exc
        if admission.dispatch_kind != "mcp":
            raise UnsupportedCompositionNodeError(
                f"{node.operator_id!r} is admitted but not an MCP operator "
                f"(dispatch_kind={admission.dispatch_kind!r}); route via "
                "UnifiedDispatch"
            )

        mcp = self._mcp if self._mcp is not None else _default_mcp()
        arguments = _node_arguments(node, resolved_inputs)
        available = await _maybe_list_tools(mcp)
        if available is not None:
            arguments = normalize_tool_args(node.operator_id, arguments, available)

        try:
            raw = await mcp.call_tool(node.operator_id, arguments=arguments)
        except ToolError:
            missing = _missing_required_arguments(
                node.operator_id,
                arguments,
                available,
            )
            if not missing:
                raise
            payload = _missing_required_argument_payload(missing)
        else:
            payload = _extract_payload(raw)
        status = _status_for_payload(payload)
        srcs = tuple(
            result.artifact_id
            for result in resolved_inputs.values()
            if result.artifact_id is not None
        )

        return NodeResult(
            status=status,
            run_id=self._run_id,
            artifact_id=self._artifact_id_factory(),
            output=payload if status in {"ok", "partial"} else None,
            output_topology=(
                infer_topology(payload).to_dict()
                if status in {"ok", "partial"}
                else None
            ),
            artifact_type=_artifact_type(payload),
            fidelity=_fidelity(payload),
            reason_code=_reason_code(payload),
            message=_message(payload),
            candidates=_candidates(payload),
            source_artifact_ids=srcs,
            resolved_class=admission.resolved_class,
        )


def _default_mcp() -> Any:
    from forge_bridge.mcp.server import mcp

    return mcp


async def _maybe_list_tools(mcp: Any) -> Any | None:
    list_tools = getattr(mcp, "list_tools", None)
    if list_tools is None:
        return None
    return await list_tools()


def _node_arguments(
    node: NodeSpec, resolved_inputs: dict[str, NodeResult]
) -> dict[str, Any]:
    # Legacy folds inherited context UNDER the static step-text args
    # (`{**public_inherited, **static}` in ``_step.py``): edge-sourced scalars
    # are lowest precedence, static step-text arguments win. Reproduce that fold
    # order here — ``{**edge_scalars, **static}``.
    static = _static_arguments(node)
    edge_scalars = _edge_scalars(node, resolved_inputs)
    return {**edge_scalars, **static}


def _static_arguments(node: NodeSpec) -> dict[str, Any]:
    if "arguments" in node.config:
        return _mapping_arguments(node, "arguments")
    if "args" in node.config:
        return _mapping_arguments(node, "args")

    kwargs: dict[str, Any] = {}
    scalar_sources: dict[Any, int] = {}
    for input_index, input_entry in enumerate(node.config.get("inputs") or []):
        if not isinstance(input_entry, Mapping):
            continue
        metadata = input_entry.get("metadata")
        if not isinstance(metadata, Mapping):
            continue
        scalars = metadata.get("scalars")
        if scalars is None:
            continue
        if not isinstance(scalars, Mapping):
            raise TypeError(
                f"node {node.node_id!r} metadata.scalars must be a mapping"
            )
        for key, value in scalars.items():
            if key in kwargs:
                raise StaticScalarCollisionError(
                    node_id=node.node_id,
                    key=key,
                    first_input_index=scalar_sources[key],
                    second_input_index=input_index,
                )
            kwargs[key] = value
            scalar_sources[key] = input_index
    return kwargs


def _edge_scalars(
    node: NodeSpec, resolved_inputs: dict[str, NodeResult]
) -> dict[str, Any]:
    """Read the nominated kwarg-input-port's upstream output as a scalars dict.

    Value-blind by default: only a port the node explicitly nominates via
    ``config["kwarg_input_port"]`` is read for kwargs; every other input edge
    stays lineage-only. The upstream ``ExtractContextNode`` owns the extraction
    meaning — this is a mechanical merge.
    """
    port = node.config.get("kwarg_input_port")
    if not isinstance(port, str) or not port:
        return {}
    result = resolved_inputs.get(port)
    if result is None or not result.has_usable_output:
        return {}
    output = result.output
    if not isinstance(output, Mapping):
        return {}
    return dict(output)


def _mapping_arguments(node: NodeSpec, key: str) -> dict[str, Any]:
    raw = node.config.get(key)
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise TypeError(f"node {node.node_id!r} arguments must be a mapping")
    return dict(raw)


def _missing_required_arguments(
    operator_id: str,
    arguments: Mapping[str, Any],
    tools: Any | None,
) -> tuple[str, ...]:
    """Return schema-proven missing fields after FastMCP raises ``ToolError``.

    FastMCP exposes validation failure as a raised ``ToolError`` whose message
    contains Pydantic prose. The schema is the stable protocol surface, so the
    boundary classifies only fields proven absent there and never parses the
    exception string.
    """

    if tools is None:
        return ()
    tool = next(
        (candidate for candidate in tools if candidate.name == operator_id),
        None,
    )
    schema = getattr(tool, "inputSchema", None)
    if not isinstance(schema, Mapping):
        return ()
    return _missing_schema_fields(schema, arguments, root=schema)


def _missing_schema_fields(
    schema: Mapping[str, Any],
    value: Any,
    *,
    root: Mapping[str, Any],
    prefix: str = "",
) -> tuple[str, ...]:
    resolved = _resolve_schema(schema, root)
    if not isinstance(resolved, Mapping) or not isinstance(value, Mapping):
        return ()

    missing: list[str] = []
    required = resolved.get("required") or []
    if isinstance(required, list):
        for key in required:
            if isinstance(key, str) and key not in value:
                missing.append(f"{prefix}{key}")

    properties = resolved.get("properties")
    if isinstance(properties, Mapping):
        for key, child_schema in properties.items():
            if key not in value or not isinstance(child_schema, Mapping):
                continue
            missing.extend(
                _missing_schema_fields(
                    child_schema,
                    value[key],
                    root=root,
                    prefix=f"{prefix}{key}.",
                )
            )
    return tuple(missing)


def _resolve_schema(
    schema: Mapping[str, Any],
    root: Mapping[str, Any],
) -> Mapping[str, Any]:
    ref = schema.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/$defs/"):
        resolved = (root.get("$defs") or {}).get(ref[len("#/$defs/"):])
        if isinstance(resolved, Mapping):
            return resolved

    for variant_key in ("anyOf", "oneOf"):
        variants = schema.get(variant_key)
        if not isinstance(variants, list):
            continue
        for variant in variants:
            if not isinstance(variant, Mapping) or variant.get("type") == "null":
                continue
            resolved = _resolve_schema(variant, root)
            if resolved.get("type") == "object" or "properties" in resolved:
                return resolved
    return schema


def _missing_required_argument_payload(missing: tuple[str, ...]) -> dict[str, Any]:
    if len(missing) == 1:
        message = f"Missing required argument: {missing[0]}"
    else:
        message = f"Missing required arguments: {', '.join(missing)}"
    return {
        "error": {
            "type": "missing_required_argument",
            "message": message,
        }
    }


def _extract_payload(raw: Any) -> Any:
    """Decode the FastMCP return shapes used by in-process and HTTP clients."""
    structured_content = getattr(raw, "structuredContent", None)
    if isinstance(structured_content, dict):
        return _loads_nested(structured_content.get("result", structured_content))

    content = getattr(raw, "content", None)
    if isinstance(content, (list, tuple)):
        text = "".join(getattr(block, "text", "") or "" for block in content)
        if text:
            return _loads_nested(text)

    if isinstance(raw, tuple) and len(raw) == 2:
        blocks, structured = raw
        if isinstance(structured, dict):
            return _loads_nested(structured.get("result", structured))
        if isinstance(blocks, (list, tuple)):
            text = "".join(getattr(block, "text", "") or "" for block in blocks)
            if text:
                return _loads_nested(text)

    if isinstance(raw, (list, tuple)):
        text = "".join(getattr(block, "text", "") or "" for block in raw)
        if text:
            return _loads_nested(text)
        return None

    return _loads_nested(raw)


def _loads_nested(value: Any) -> Any:
    for _ in range(3):
        if not isinstance(value, str):
            return value
        try:
            loaded = json.loads(value)
        except (TypeError, ValueError):
            return value
        if loaded == value:
            return value
        value = loaded
    return value


def _status_for_payload(payload: Any) -> str:
    if not isinstance(payload, dict):
        return "ok"
    explicit = payload.get("status")
    if explicit in {"ok", "partial", "abstained", "error"}:
        return str(explicit)
    if payload.get("disposition") == "abstained" or payload.get("abstained") is True:
        return "abstained"
    artifact = payload.get("artifact")
    if isinstance(artifact, dict) and artifact.get("abstention_reason"):
        return "abstained"
    if payload.get("verdict") in {"abstained", "inconclusive"}:
        return "abstained"
    if payload.get("error"):
        return "error"
    if payload.get("partial_fidelity_report"):
        return "partial"
    return "ok"


def _artifact_type(payload: Any) -> str | None:
    if isinstance(payload, dict):
        value = payload.get("artifact_type") or payload.get("type")
        if value is not None:
            return str(value)
    return "mcp_read_result"


def _fidelity(payload: Any) -> dict[str, Any] | None:
    if isinstance(payload, dict) and isinstance(
        payload.get("partial_fidelity_report"), dict
    ):
        return payload["partial_fidelity_report"]
    return None


def _reason_code(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    error = payload.get("error")
    if isinstance(error, dict):
        return str(error.get("code") or error.get("type") or "error")
    value = (
        payload.get("reason_code")
        or payload.get("reason")
        or payload.get("abstention_reason")
    )
    if value is None and isinstance(payload.get("artifact"), dict):
        value = payload["artifact"].get("abstention_reason")
    return str(value) if value is not None else None


def _message(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    error = payload.get("error")
    if isinstance(error, dict):
        value = error.get("message") or error.get("detail")
        return str(value) if value is not None else None
    value = payload.get("message") or payload.get("recommendation")
    return str(value) if value is not None else None


def _candidates(payload: Any) -> tuple[Any, ...]:
    if isinstance(payload, dict) and isinstance(payload.get("candidates"), list):
        return tuple(payload["candidates"])
    return ()


__all__ = [
    "MCPToolBoundary",
    "StaticScalarCollisionError",
    "UnsupportedCompositionNodeError",
]
