"""Assent-required graph entrypoint for host-applying editorial deltas.

This is deliberately a sibling of ``run_graph``, not a parameter on it.
``run_graph`` remains structurally no-assent; this surface is the explicit
apply rail for graphs that culminate in a ratified host ``commit`` node.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

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
    receipt_dir: str | Path | None = None,
) -> dict[str, NodeResult]:
    """Run an editorial-delta apply graph through the assent-required rail."""

    operation_runner = build_operation_runner(registry, receipt_dir=receipt_dir)
    dispatch = UnifiedDispatch(
        operation_boundary=OperationDispatchBoundary(run_operation=operation_runner),
        host_resolve_boundary=HostResolveBoundary(run_discover=run_discover),
        commit_boundary=CommitBoundary(),
        assent_record=assent_record,
    )
    return await GraphExecutor(dispatch.dispatch).run(spec)


__all__ = ["apply_editorial_delta"]
