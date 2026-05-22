"""Substrate graph primitives.

This package is the explicit boundary between domain tools and graph
operations. Domain tools enumerate, inspect, preview, mutate, publish,
or format real production objects. Graph primitives transform execution
topology over already-structured values.

The model may help choose an intent. The graph layer executes typed
nodes deterministically. Future primitives such as if_then, foreach,
collect, and compare belong here, not in Flame-domain tool modules.

Graph primitives must reject unsupported input shapes mechanically.
They are not planners, parsers, or hidden domain tools.
"""

from forge_bridge.graph.collect import (
    CollectError,
    CollectNode,
    is_collect_step,
    parse_collect_step,
)
from forge_bridge.graph.commit import (
    CommitError,
    CommitNode,
    is_commit_step,
    parse_commit_step,
)
from forge_bridge.graph.filter import (
    FilterNode,
    FilterPredicate,
    GraphInputError,
    PredicateParseError,
    evaluate_predicate,
    is_filter_step,
    parse_filter_step,
)
from forge_bridge.graph.foreach import (
    ForEachNode,
    ForeachInputError,
    ForeachParseError,
    IterationResult,
    is_foreach_step,
    parse_foreach_step,
)
from forge_bridge.graph.if_gate import (
    IfGateNode,
    is_if_step,
    parse_if_step,
)
from forge_bridge.graph.ports import (
    ChainWireCompatibilityError,
    PortContract,
    PortTopology,
    infer_iteration_item_topology,
    infer_topology,
    validate_chain_wire,
)
from forge_bridge.graph.select import (
    SelectError,
    SelectIdentity,
    SelectNode,
    is_select_step,
    parse_select_step,
)

__all__ = [
    "FilterNode",
    "FilterPredicate",
    "CollectError",
    "CollectNode",
    "CommitError",
    "CommitNode",
    "ForEachNode",
    "ForeachInputError",
    "ForeachParseError",
    "GraphInputError",
    "IfGateNode",
    "IterationResult",
    "PredicateParseError",
    "ChainWireCompatibilityError",
    "PortContract",
    "PortTopology",
    "SelectError",
    "SelectIdentity",
    "SelectNode",
    "evaluate_predicate",
    "infer_topology",
    "infer_iteration_item_topology",
    "is_collect_step",
    "is_commit_step",
    "is_filter_step",
    "is_foreach_step",
    "is_if_step",
    "is_select_step",
    "parse_collect_step",
    "parse_commit_step",
    "parse_filter_step",
    "parse_foreach_step",
    "parse_if_step",
    "parse_select_step",
    "validate_chain_wire",
]
