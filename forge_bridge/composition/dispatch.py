"""Unified dispatch for M2 slice-1 composition.

``GraphExecutor`` remains pure and receives only one async dispatch callable.
This object composes the admitted MCP half and the in-process primitive half
around it, using ``admission.py`` as the single routing table.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from forge_bridge.composition.admission import admit_operator
from forge_bridge.composition.boundary import MCPToolBoundary
from forge_bridge.composition.commit_boundary import CommitBoundary
from forge_bridge.composition.foreach_boundary import ForeachBoundary
from forge_bridge.composition.graph_spec import NodeSpec
from forge_bridge.composition.node_result import NodeResult
from forge_bridge.composition.operation_boundary import OperationDispatchBoundary
from forge_bridge.composition.primitive_boundary import PrimitiveBoundary


@dataclass
class UnifiedDispatch:
    """Route admitted graph nodes to their concrete boundary implementation."""

    mcp_boundary: MCPToolBoundary = field(default_factory=MCPToolBoundary)
    primitive_boundary: PrimitiveBoundary = field(default_factory=PrimitiveBoundary)
    foreach_boundary: ForeachBoundary = field(default_factory=ForeachBoundary)
    commit_boundary: CommitBoundary = field(default_factory=CommitBoundary)
    operation_boundary: OperationDispatchBoundary = field(
        default_factory=OperationDispatchBoundary
    )
    assent_record: Any | None = None

    async def dispatch(
        self,
        node: NodeSpec,
        resolved_inputs: dict[str, NodeResult],
    ) -> NodeResult:
        admission = admit_operator(node.operator_id)
        if admission.dispatch_kind == "mcp":
            return await self.mcp_boundary.dispatch(node, resolved_inputs)
        if admission.dispatch_kind == "primitive":
            return await self.primitive_boundary.dispatch(node, resolved_inputs)
        if admission.dispatch_kind == "foreach":
            return await self.foreach_boundary.dispatch(
                node,
                resolved_inputs,
                reenter=self.dispatch,
            )
        if admission.dispatch_kind == "commit":
            return await self.commit_boundary.dispatch(
                node,
                resolved_inputs,
                assent_record=self.assent_record,
            )
        if admission.dispatch_kind == "operation":
            return await self.operation_boundary.dispatch(node, resolved_inputs)
        raise AssertionError(f"Unhandled dispatch kind: {admission.dispatch_kind!r}")
