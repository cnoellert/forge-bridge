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

from forge_bridge.graph.filter import (
    FilterNode,
    FilterPredicate,
    GraphInputError,
    PredicateParseError,
    evaluate_predicate,
    is_filter_step,
    parse_filter_step,
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
    "GraphInputError",
    "IfGateNode",
    "PredicateParseError",
    "ChainWireCompatibilityError",
    "PortContract",
    "PortTopology",
    "SelectError",
    "SelectIdentity",
    "SelectNode",
    "evaluate_predicate",
    "infer_topology",
    "is_filter_step",
    "is_if_step",
    "is_select_step",
    "parse_filter_step",
    "parse_if_step",
    "parse_select_step",
    "validate_chain_wire",
]
