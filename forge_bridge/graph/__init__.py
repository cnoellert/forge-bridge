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
    is_filter_step,
    parse_filter_step,
)

__all__ = [
    "FilterNode",
    "FilterPredicate",
    "GraphInputError",
    "PredicateParseError",
    "is_filter_step",
    "parse_filter_step",
]
