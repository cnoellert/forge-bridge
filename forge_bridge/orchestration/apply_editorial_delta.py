"""Assent-required graph entrypoint for host-applying editorial deltas.

This is deliberately a sibling of ``run_graph``, not a parameter on it.
``run_graph`` remains structurally no-assent; this surface is the explicit
apply rail for graphs that culminate in a ratified host ``commit`` node.

``preview_editorial_delta`` is its read-only twin: same operation->host_resolve
path, no assent and no apply, so the operator can inspect the held mutation
manifest before ratifying.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from forge_bridge.composition.boundary import _extract_payload
from forge_bridge.composition.commit_boundary import CommitBoundary
from forge_bridge.composition.dispatch import UnifiedDispatch
from forge_bridge.composition.executor import GraphExecutor
from forge_bridge.composition.graph_spec import GraphSpec
from forge_bridge.composition.host_resolve_boundary import HostResolveBoundary
from forge_bridge.composition.node_result import NodeResult
from forge_bridge.composition.operation_boundary import OperationDispatchBoundary
from forge_bridge.orchestration.operation_runner import build_operation_runner

DEFAULT_APPLY_RECEIPT_DIR = Path.home() / ".forge-bridge" / "apply-receipts"


async def apply_editorial_delta(
    spec: GraphSpec,
    *,
    assent_record: Any,
    registry: Any | None = None,
    run_discover: Any | None = None,
    mcp: Any | None = None,
    receipt_dir: str | Path | None = None,
) -> dict[str, NodeResult]:
    """Run an editorial-delta apply graph through the assent-required rail."""

    dispatch = _build_dispatch(
        assent_record=assent_record,
        registry=registry,
        run_discover=run_discover,
        mcp=mcp,
        receipt_dir=receipt_dir,
    )
    results = await GraphExecutor(dispatch.dispatch).run(spec)
    # ponytail: re-apply can't double-mutate — fresh discover fails closed
    # (MUTATION_MANIFEST_INVALID or PLAN_STATE_DRIFT), so no dedup key. Uncovered:
    # a TOCTOU race on the same in-flight assent (needs locking, not a key).
    _sink_apply_receipt(spec, results, assent_record, receipt_dir)
    return results


async def preview_editorial_delta(
    spec: GraphSpec,
    *,
    registry: Any | None = None,
    run_discover: Any | None = None,
    mcp: Any | None = None,
    receipt_dir: str | Path | None = None,
) -> dict[str, NodeResult]:
    """Resolve an editorial-delta graph to its held manifest WITHOUT applying.

    Runs the same operation->host_resolve path the apply rail uses, but with no
    assent: the ``delta_to_manifest`` NodeResult is the operator preview (the
    mutation manifest on success, or a typed ``reason_code`` for an
    unsupported/unresolved delta). A ``commit`` node, if present in the spec,
    runs its non-mutating verify and then fail-closes at the assent gate — it
    never applies.
    """

    dispatch = _build_dispatch(
        assent_record=None,
        registry=registry,
        run_discover=run_discover,
        mcp=mcp,
        receipt_dir=receipt_dir,
    )
    return await GraphExecutor(dispatch.dispatch).run(spec)


def _build_dispatch(
    *,
    assent_record: Any | None,
    registry: Any | None,
    run_discover: Any | None,
    mcp: Any | None,
    receipt_dir: str | Path | None,
) -> UnifiedDispatch:
    operation_runner = build_operation_runner(registry, receipt_dir=receipt_dir)
    shared_mcp = mcp if mcp is not None else _default_mcp()
    discover = (
        run_discover
        if run_discover is not None
        else _mcp_run_discover(shared_mcp)
    )
    return UnifiedDispatch(
        operation_boundary=OperationDispatchBoundary(run_operation=operation_runner),
        host_resolve_boundary=HostResolveBoundary(run_discover=discover),
        commit_boundary=CommitBoundary(mcp=shared_mcp),
        assent_record=assent_record,
    )


def _sink_apply_receipt(
    spec: GraphSpec,
    results: dict[str, NodeResult],
    assent_record: Any,
    receipt_dir: str | Path | None,
) -> None:
    """Write a 3-layer provenance receipt when a commit actually applied.

    Links the host apply result (layer 3), the held mutation manifest + assent
    decision (layer 2), and the upstream operation output (layer 1). Only
    grounded facts are written — absent layers are simply omitted, never faked;
    ``source_operation_type`` is read from the actual operation node's
    ``operator_id``, not assembled.
    """

    commit = _find_output(results, lambda o: o.get("type") == "commit_applied")
    if commit is None or assent_record is None:
        return

    manifest = _find_output(results, lambda o: "apply_counterpart" in o)
    source_operation_type = _source_operation_type(spec, results)

    receipt: dict[str, Any] = {
        "operation_type": "host_authorized_delta_application",
        "target_host": "flame",
        "assent_record_id": str(getattr(assent_record, "id", None)),
        "graph_intent_id": getattr(assent_record, "graph_intent_id", None),
        "applied_count": commit.get("count"),
        "apply_result": commit.get("apply_result"),
    }
    if manifest is not None:
        intent = manifest.get("intent_parameters") or {}
        receipt["target_sequence_id"] = intent.get("sequence_name")
        receipt["manifest"] = manifest
    if source_operation_type is not None:
        receipt["source_operation_type"] = source_operation_type

    base = Path(receipt_dir) if receipt_dir is not None else DEFAULT_APPLY_RECEIPT_DIR
    base = base.expanduser()
    base.mkdir(parents=True, exist_ok=True)
    # assent id keys the receipt: re-apply overwrites the same file (and fails closed).
    path = base / f"{receipt['assent_record_id']}.json"
    path.write_text(json.dumps(receipt, indent=2, default=str), encoding="utf-8")


def _source_operation_type(
    spec: GraphSpec,
    results: dict[str, NodeResult],
) -> str | None:
    """The operator_id of the node whose output carried the editorial deltas."""
    for node in spec.nodes:
        result = results.get(node.node_id)
        output = result.output if result is not None else None
        if isinstance(output, dict) and "deltas" in output:
            return node.operator_id
    return None


def _find_output(results: dict[str, NodeResult], pred) -> dict[str, Any] | None:
    for result in results.values():
        output = result.output
        if isinstance(output, dict) and pred(output):
            return output
    return None


def _mcp_run_discover(mcp: Any):
    async def run_discover(tool_name: str, *, request: dict[str, Any]) -> Any:
        return _extract_payload(
            await mcp.call_tool(
                tool_name,
                arguments={**request, "mode": "discover"},
            )
        )

    return run_discover


def _default_mcp() -> Any:
    from forge_bridge.mcp.server import mcp

    return mcp


__all__ = ["apply_editorial_delta", "preview_editorial_delta"]
