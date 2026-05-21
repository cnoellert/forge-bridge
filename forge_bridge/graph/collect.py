"""Topology-converging collect graph primitive.

CollectNode consumes foreach iteration results and reconciles their body
outputs with generic topology rules. It is substrate-generic: domain field
names are not special-cased in the implementation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, ClassVar

from forge_bridge.graph.ports import (
    ChainWireCompatibilityError,
    PortContract,
    PortTopology,
    infer_topology,
)


_COLLECT_INTENT_RE = re.compile(r"^\s*collect\s*$", re.IGNORECASE)


class CollectError(ValueError):
    """Raised when collect receives an invalid iteration-result payload."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def is_collect_step(text: str) -> bool:
    """Return true when a chain step is a collect graph node."""
    return bool(isinstance(text, str) and _COLLECT_INTENT_RE.match(text))


def parse_collect_step(text: str) -> None:
    """Validate collect step syntax."""
    if not is_collect_step(text):
        raise CollectError("NOT_COLLECT_STEP", "Step is not a collect node.")
    return None


@dataclass(frozen=True)
class CollectNode:
    """Reconcile list[IterationResult] into one compatible manifest."""

    port_contract: ClassVar[PortContract] = PortContract(
        (PortTopology.iteration_results(),),
        PortTopology.manifest(),
    )

    def run(self, data: Any) -> dict[str, Any]:
        iterations = _extract_iterations(data)
        outputs = [_iteration_result(iteration) for iteration in iterations]
        reconciled = _reconcile_outputs(outputs)
        result = dict(reconciled)
        topology_probe = dict(result)
        topology_probe["collect"] = {}
        result["collect"] = {
            "input_count": len(iterations),
            "output_topology": infer_topology(topology_probe).to_dict(),
        }
        if "count" not in result:
            result["count"] = len(iterations)
        return result


def _extract_iterations(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        iterations = data
    elif isinstance(data, dict):
        iterations = data.get("iterations")
    else:
        iterations = None

    if not isinstance(iterations, list):
        raise CollectError(
            "INVALID_COLLECT_INPUT",
            "CollectNode requires list[IterationResult] input.",
        )
    if not all(isinstance(item, dict) for item in iterations):
        raise CollectError(
            "INVALID_COLLECT_INPUT",
            "CollectNode requires dict-shaped iteration results.",
        )
    return iterations


def _iteration_result(iteration: dict[str, Any]) -> dict[str, Any]:
    result = iteration.get("result")
    if not isinstance(result, dict):
        raise CollectError(
            "INVALID_ITERATION_RESULT",
            "IterationResult.result must be a dict.",
        )
    return result


def _reconcile_outputs(outputs: list[dict[str, Any]]) -> dict[str, Any]:
    if not outputs:
        return {"collection": []}

    reconciled: dict[str, Any] = {}
    keys = sorted({key for output in outputs for key in output})
    for key in keys:
        values = [output[key] for output in outputs if key in output]
        if all(isinstance(value, list) for value in values):
            merged: list[Any] = []
            for value in values:
                merged.extend(value)
            reconciled[key] = merged
            continue

        first = values[0]
        if all(value == first for value in values):
            reconciled[key] = first
            continue

        raise ChainWireCompatibilityError(
            step_index=-1,
            step_text="collect",
            expected=(infer_topology(first),),
            actual=infer_topology(values[-1]),
        )

    return reconciled
