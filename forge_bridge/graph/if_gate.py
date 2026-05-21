"""Deterministic manifest-level execution gate primitive.

IfGateNode is topology-preserving over execution manifests. It never filters
raw collections and never evaluates per-item predicates. A predicate miss
preserves the manifest in flow and marks it ``execution_state="skipped"`` so
downstream visibility remains explicit.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, ClassVar

from forge_bridge.graph.filter import (
    FilterPredicate,
    GraphInputError,
    PredicateParseError,
    evaluate_predicate,
    parse_filter_step,
)
from forge_bridge.graph.ports import PortContract


_IF_INTENT_RE = re.compile(r"^\s*if(?:\s*\(|\s+)", re.IGNORECASE)
_IF_CALL_RE = re.compile(
    r"^\s*if\s*(?:\(\s*)?(?P<body>[^)]*?)(?:\s*\))?\s*$",
    re.IGNORECASE,
)


def is_if_step(text: str) -> bool:
    """Return true when a chain step is an if-gate node."""
    return bool(isinstance(text, str) and _IF_INTENT_RE.search(text))


def parse_if_step(text: str) -> FilterPredicate:
    """Parse an if step into the shared flat predicate AST.

    IfGateNode reuses FilterPredicate exactly; filter and if-gate differ in
    graph semantics, not predicate representation.
    """
    if not is_if_step(text):
        raise PredicateParseError("not_if_step", "Step is not an if-gate graph node.")

    match = _IF_CALL_RE.match(text.strip())
    body = match.group("body").strip() if match else ""
    if not body:
        raise PredicateParseError("unknown_predicate", "No if-gate predicate found.")
    return parse_filter_step(f"filter({body})")


@dataclass(frozen=True)
class IfGateNode:
    """Unary manifest-level execution gate."""

    port_contract: ClassVar[PortContract] = PortContract.manifest_gate()

    predicate: FilterPredicate

    def run(self, manifest: Any) -> dict[str, Any]:
        if not isinstance(manifest, dict):
            raise GraphInputError(
                "invalid_manifest",
                "IfGateNode requires a previous execution manifest.",
            )

        matched = evaluate_predicate(
            self.predicate,
            manifest,
            empty_values_absent=True,
        )
        result = dict(manifest)
        result["execution_state"] = "passed" if matched else "skipped"
        result["if_gate"] = {
            "matched": matched,
            "predicate": self.predicate.to_dict(),
        }
        return result
