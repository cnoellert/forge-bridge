"""Bridge boundary adapter for M1 composition nodes.

``GraphExecutor`` is intentionally substrate-agnostic: it topo-sorts and hands
named input ``NodeResult``s to a dispatch callable. This module is that first
real dispatch callable for M1 Phase 2: cheap read/perception MCP operators
wrapped into bridge-internal ``NodeResult`` envelopes.

Generation/make operators are intentionally not admitted here. They need
submit/poll/cost/non-determinism handling and belong to M2, not this read-only
boundary.
"""
from __future__ import annotations

import asyncio
import inspect
import json
import uuid
from collections.abc import Callable, Mapping
from typing import Any

from forge_bridge.composition.graph_spec import NodeSpec
from forge_bridge.composition.node_result import NodeResult
from forge_bridge.graph.ports import infer_topology
from forge_bridge.mcp.arguments import normalize_tool_args

READ_PERCEPTION_OPERATORS: frozenset[str] = frozenset({
    "forge_is_greenscreen",
})


class UnsupportedCompositionNodeError(ValueError):
    """A node is outside M1's cheap read/perception boundary."""


class MCPToolBoundary:
    """Dispatch read/perception MCP tools and mint ``NodeResult`` envelopes."""

    def __init__(
        self,
        *,
        mcp: Any | None = None,
        allowed_operators: frozenset[str] = READ_PERCEPTION_OPERATORS,
        run_id: uuid.UUID | None = None,
        artifact_id_factory: Callable[[], uuid.UUID] = uuid.uuid4,
    ) -> None:
        self._mcp = mcp
        self._allowed_operators = allowed_operators
        self._run_id = run_id or uuid.uuid4()
        self._artifact_id_factory = artifact_id_factory

    def dispatch(
        self,
        node: NodeSpec,
        resolved_inputs: dict[str, NodeResult],
    ) -> NodeResult:
        """Execute ``node.operator_id`` and wrap the MCP payload.

        Source lineage is recorded from upstream ``NodeResult.artifact_id``
        values. The executor stays purely mechanical; the boundary mints the
        envelope and lineage.
        """
        if node.operator_id not in self._allowed_operators:
            raise UnsupportedCompositionNodeError(
                f"{node.operator_id!r} is outside M1 read/perception boundary"
            )

        mcp = self._mcp if self._mcp is not None else _default_mcp()
        arguments = _node_arguments(node)
        available = _maybe_list_tools(mcp)
        if available is not None:
            arguments = normalize_tool_args(node.operator_id, arguments, available)

        raw = _run_sync(mcp.call_tool(node.operator_id, arguments=arguments))
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
        )


def _default_mcp() -> Any:
    from forge_bridge.mcp.server import mcp

    return mcp


def _run_sync(value: Any) -> Any:
    if not inspect.isawaitable(value):
        return value
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(value)
    raise RuntimeError(
        "MCPToolBoundary.dispatch cannot await while an event loop is running"
    )


def _maybe_list_tools(mcp: Any) -> Any | None:
    list_tools = getattr(mcp, "list_tools", None)
    if list_tools is None:
        return None
    return _run_sync(list_tools())


def _node_arguments(node: NodeSpec) -> dict[str, Any]:
    raw = node.config.get("arguments", node.config.get("args", {}))
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise TypeError(f"node {node.node_id!r} arguments must be a mapping")
    return dict(raw)


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
    "READ_PERCEPTION_OPERATORS",
    "UnsupportedCompositionNodeError",
]
