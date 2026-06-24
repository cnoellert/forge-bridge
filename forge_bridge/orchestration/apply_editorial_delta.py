"""Assent-required graph entrypoint for host-applying editorial deltas.

This is deliberately a sibling of ``run_graph``, not a parameter on it.
``run_graph`` remains structurally no-assent; this surface is the explicit
apply rail for graphs that culminate in a ratified host ``commit`` node.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from forge_bridge.composition.boundary import _extract_payload
from forge_bridge.composition.commit_boundary import CommitBoundary
from forge_bridge.composition.dispatch import UnifiedDispatch
from forge_bridge.composition.executor import GraphExecutor
from forge_bridge.composition.graph_spec import GraphSpec
from forge_bridge.composition.host_resolve_boundary import HostResolveBoundary
from forge_bridge.composition.node_result import NodeResult
from forge_bridge.composition.operation_boundary import OperationDispatchBoundary
from forge_bridge.orchestration.operation_runner import build_operation_runner


async def apply_editorial_delta(
    spec: GraphSpec,
    *,
    assent_record: Any,
    registry: Any | None = None,
    run_discover: Any | None = None,
    mcp: Any | None = None,
    receipt_dir: str | Path | None = None,
) -> dict[str, NodeResult]:
    """Run an editorial-delta apply graph through the assent-required rail."""

    operation_runner = build_operation_runner(registry, receipt_dir=receipt_dir)
    shared_mcp = mcp if mcp is not None else _default_mcp()
    discover = (
        run_discover
        if run_discover is not None
        else _mcp_run_discover(shared_mcp)
    )
    dispatch = UnifiedDispatch(
        operation_boundary=OperationDispatchBoundary(run_operation=operation_runner),
        host_resolve_boundary=HostResolveBoundary(run_discover=discover),
        commit_boundary=CommitBoundary(mcp=shared_mcp),
        assent_record=assent_record,
    )
    return await GraphExecutor(dispatch.dispatch).run(spec)


def _mcp_run_discover(mcp: Any):
    async def run_discover(tool_name: str, *, request: dict[str, Any]) -> Any:
        return _extract_payload(
            await mcp.call_tool(
                tool_name,
                arguments={**request, "mode": "discover"},
            )
        )

    return run_discover


def _default_mcp() -> Any:
    from forge_bridge.mcp.server import mcp

    return mcp


__all__ = ["apply_editorial_delta"]
