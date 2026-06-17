"""forge_bridge.composition — Milestone 1 "Wire-and-Run v0" composition engine.

A new internal package (carries its own ``__all__``; does NOT touch the
top-level ``forge_bridge.__all__`` of 19). The graph-native composition
substrate: ``GraphSpec`` (the node-id'd DAG IR of record), ``NodeResult`` (the
typed edge envelope), and ``GraphExecutor`` (the single topological executor).

See ``.planning/M1-WIRE-AND-RUN-SEAM-DESIGN.md``.
"""
from __future__ import annotations

from forge_bridge.composition.executor import DispatchFn, GraphExecutor
from forge_bridge.composition.graph_spec import (
    Edge,
    GraphCycleError,
    GraphEdgeCompatibilityError,
    GraphSpec,
    NodeSpec,
)
from forge_bridge.composition.node_result import NODE_STATUSES, NodeResult

__all__ = [
    "DispatchFn",
    "Edge",
    "GraphCycleError",
    "GraphEdgeCompatibilityError",
    "GraphExecutor",
    "GraphSpec",
    "NODE_STATUSES",
    "NodeResult",
    "NodeSpec",
]
