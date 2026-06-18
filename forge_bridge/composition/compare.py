"""Compare legacy chain execution with graph execution.

The harness is intentionally outside ``GraphExecutor``. Legacy
``run_chain_steps`` aborts after the first failed step; the executor remains a
pure graph runner. ``AbortOnFirstErrorDispatch`` is the orchestration wrapper
that makes graph-side status vectors comparable without giving the executor a
side-effect policy.
"""
from __future__ import annotations

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
SKIPPED_REASON_CODE = "skipped_after_error"


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


class AbortOnFirstErrorDispatch:
    """Short-circuit downstream graph dispatch after an upstream error.

    ``skipped`` is a compare status token, not a fifth ``NodeResult`` status.
    The wrapper returns an ``error`` envelope tagged with
    ``SKIPPED_REASON_CODE`` so normalizers can represent the orchestration
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
        if any(result.status == "error" for result in resolved_inputs.values()):
            self.skipped_node_ids.append(node.node_id)
            return NodeResult(
                status="error",
                run_id=uuid.uuid4(),
                reason_code=SKIPPED_REASON_CODE,
                message="Skipped after upstream graph error.",
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

    This is the slice-1 route for admitted idempotent operators. The
    record-replay route is selected and tested separately because slice-1's
    concrete corpus is entirely idempotent.
    """

    legacy_body = await legacy_runner()
    aborting = AbortOnFirstErrorDispatch(dispatch)
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

    return "double_exec" if all(record.idempotent for record in records) else "record_replay"


def admitted_records_for(graph: GraphSpec) -> tuple[AdmissionRecord, ...]:
    """Return admission records for every node in graph order."""

    return tuple(admit_operator(node.operator_id) for node in graph.nodes)


def normalize_chain_body(
    body: dict[str, Any],
    *,
    expected_steps: int | None = None,
) -> CompareSnapshot:
    """Normalize ``run_chain_steps`` output into a status vector and terminal."""

    chain = body.get("chain") or []
    statuses: list[str] = ["ok"] * len(chain)
    terminal_output = chain[-1]["result"] if chain else None

    if body.get("status") == "error":
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
    terminal_output = terminal.output if terminal is not None else None
    if terminal is not None and _status_token(terminal) != "ok":
        terminal_output = None
    return CompareSnapshot(statuses, terminal_output)


def _status_token(result: NodeResult) -> str:
    if result.reason_code == SKIPPED_REASON_CODE:
        return "skipped"
    return result.status

