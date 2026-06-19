"""Compare legacy chain execution with graph execution.

The harness is intentionally outside ``GraphExecutor``. Legacy
``run_chain_steps`` aborts/skips downstream steps outside the executor; the
executor remains a pure graph runner. ``SkipPropagationDispatch`` is the
orchestration wrapper that makes graph-side status vectors comparable without
giving the executor a side-effect policy.
"""
from __future__ import annotations

import copy
import re
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal

from forge_bridge.composition.admission import AdmissionRecord, admit_operator
from forge_bridge.composition.executor import GraphExecutor
from forge_bridge.composition.graph_spec import GraphSpec, NodeSpec
from forge_bridge.composition.node_result import NodeResult

DispatchCallable = Callable[[NodeSpec, dict[str, NodeResult]], Awaitable[NodeResult]]
CompareStrategy = Literal["double_exec", "record_replay"]
DID_NOT_RUN_REASON_CODE = "did_not_run_after_skip"
_ARTIFACT_ID_RE = re.compile(r"roto_[0-9a-f]{32}")
_UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CompareSnapshot:
    """Normalized execution surface for parity checks."""

    status_vector: tuple[str, ...]
    terminal_output: Any


@dataclass(frozen=True)
class CompareResult:
    """Result of one legacy-vs-graph compare run."""

    legacy: CompareSnapshot
    graph: CompareSnapshot

    @property
    def equivalent(self) -> bool:
        return self.legacy == self.graph


class SkipPropagationDispatch:
    """Short-circuit downstream graph dispatch after a non-flowing input.

    ``skipped`` is a compare status token, not a fifth ``NodeResult`` status.
    The wrapper returns an ``error`` envelope tagged with
    ``DID_NOT_RUN_REASON_CODE`` so normalizers can represent the orchestration
    decision while no concrete downstream boundary is invoked.
    """

    def __init__(self, dispatch: DispatchCallable) -> None:
        self._dispatch = dispatch
        self.skipped_node_ids: list[str] = []
        self.dispatched_node_ids: list[str] = []

    async def dispatch(
        self,
        node: NodeSpec,
        resolved_inputs: dict[str, NodeResult],
    ) -> NodeResult:
        if any(_non_flowing(result) for result in resolved_inputs.values()):
            self.skipped_node_ids.append(node.node_id)
            return NodeResult(
                status="error",
                run_id=uuid.uuid4(),
                reason_code=DID_NOT_RUN_REASON_CODE,
                message="Skipped after upstream graph control signal.",
                control_signal="skip",
            )
        self.dispatched_node_ids.append(node.node_id)
        return await self._dispatch(node, resolved_inputs)


async def compare_idempotent_paths(
    *,
    legacy_runner: Callable[[], Awaitable[dict[str, Any]]],
    graph: GraphSpec,
    dispatch: DispatchCallable,
    terminal_node_id: str,
    expected_steps: int | None = None,
) -> CompareResult:
    """Run both paths and compare normalized outputs.

    This is the slice-1 route for operators whose admitted declarations say
    they produce idempotent results. The record-replay route is selected and
    tested separately because slice-1's concrete corpus is result-idempotent.
    """

    legacy_body = await legacy_runner()
    aborting = SkipPropagationDispatch(dispatch)
    graph_results = await GraphExecutor(aborting.dispatch).run(graph)
    return CompareResult(
        legacy=normalize_chain_body(legacy_body, expected_steps=expected_steps),
        graph=normalize_graph_results(
            graph_results,
            terminal_node_id=terminal_node_id,
        ),
    )


def compare_strategy_for(records: tuple[AdmissionRecord, ...]) -> CompareStrategy:
    """Select compare mode from admitted operator properties."""

    return (
        "double_exec"
        if all(record.idempotent_result for record in records)
        else "record_replay"
    )


def admitted_records_for(graph: GraphSpec) -> tuple[AdmissionRecord, ...]:
    """Return admission records for every node in graph order."""

    return tuple(admit_operator(node.operator_id) for node in graph.nodes)


def normalize_chain_body(
    body: dict[str, Any],
    *,
    expected_steps: int | None = None,
) -> CompareSnapshot:
    """Normalize ``run_chain_steps`` output into a status vector and terminal."""

    status = body.get("status")
    if status not in {"success", "error"}:
        raise ValueError(f"Cannot normalize chain body status: {status!r}")

    chain = body.get("chain") or []
    statuses: list[str] = [_chain_step_status(entry) for entry in chain]
    terminal_output = normalize_terminal_output(chain[-1]["result"]) if chain else None
    if statuses and statuses[-1] != "ok":
        terminal_output = None

    if status == "error":
        step_index = int((body.get("error") or {}).get("step_index", len(chain)))
        while len(statuses) < step_index:
            statuses.append("ok")
        statuses.append("error")
        if expected_steps is not None:
            while len(statuses) < expected_steps:
                statuses.append("skipped")
        terminal_output = None

    return CompareSnapshot(tuple(statuses), terminal_output)


def normalize_graph_results(
    results: dict[str, NodeResult],
    *,
    terminal_node_id: str,
) -> CompareSnapshot:
    """Normalize ``GraphExecutor.run`` output into a comparable surface."""

    statuses = tuple(_status_token(result) for result in results.values())
    terminal = results.get(terminal_node_id)
    terminal_output = (
        normalize_terminal_output(terminal.output) if terminal is not None else None
    )
    if terminal is not None and _status_token(terminal) != "ok":
        terminal_output = None
    return CompareSnapshot(statuses, terminal_output)


def _status_token(result: NodeResult) -> str:
    if result.reason_code == DID_NOT_RUN_REASON_CODE:
        return "skipped"
    return result.status


def _chain_step_status(entry: dict[str, Any]) -> str:
    result = entry.get("result")
    if isinstance(result, dict) and "skipped_step" in result:
        return "skipped"
    return "ok"


def _non_flowing(result: NodeResult) -> bool:
    # Error folding is intentionally local to the orchestration wrapper for 2a:
    # boundaries do not all need to remint historical errors with a control
    # signal for compare parity to preserve abort semantics.
    return result.control_signal == "skip" or result.status == "error"


def normalize_terminal_output(value: Any) -> Any:
    """Normalize volatile execution envelope fields before parity comparison.

    This is deliberately surgical and capture-derived. It removes or
    canonicalizes provenance that differs across identical roto calls while
    preserving the content hashes that prove the resulting matte bytes are
    identical. A live daemon double-exec remains slice-5 work; this function is
    the slice-1 real-shape, real-volatility compare boundary.
    """

    normalized = copy.deepcopy(value)
    _normalize_in_place(normalized, ())
    return normalized


def _normalize_in_place(value: Any, path: tuple[str | int, ...]) -> None:
    if isinstance(value, dict):
        for key in list(value):
            child_path = (*path, key)
            if _strip_field(child_path):
                del value[key]
                continue
            if _canonicalize_field(child_path):
                value[key] = _canonicalize_token(str(value[key]))
                continue
            _normalize_in_place(value[key], child_path)
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _normalize_in_place(item, (*path, index))


def _strip_field(path: tuple[str | int, ...]) -> bool:
    return path in {
        ("content_hash",),
        ("graph_event_id",),
        ("request_id",),
    }


def _canonicalize_field(path: tuple[str | int, ...]) -> bool:
    if path == ("artifact", "artifact_id"):
        return True
    if path == ("artifact", "sequence_locator", "path"):
        return True
    if len(path) == 3 and path[0] == "artifact_refs" and path[2] in {
        "artifact_id",
        "locator",
    }:
        return True
    return False


def _canonicalize_token(value: str) -> str:
    value = _ARTIFACT_ID_RE.sub("roto_<artifact_id>", value)
    return _UUID_RE.sub("<uuid>", value)
