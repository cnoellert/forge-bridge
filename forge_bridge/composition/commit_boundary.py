"""Commit boundary for ratified host mutations in M2 slice 3.

``GraphExecutor`` remains authority-blind. The caller constructs a dispatch
closure that carries the assent record into this boundary, where commit can
verify the held mutation plan against fresh host state and then apply exactly
once. The returned ``NodeResult`` is plain execution evidence; it never embeds
the assent object.
"""
from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

from forge_bridge.composition.boundary import (
    _extract_payload,
    _maybe_list_tools,
)
from forge_bridge.composition.graph_spec import NodeSpec
from forge_bridge.composition.node_result import NodeResult
from forge_bridge.graph.commit import CommitError, CommitNode
from forge_bridge.graph.mutation import MutationManifest, MutationManifestError
from forge_bridge.graph.ports import infer_topology
from forge_bridge.mcp.arguments import normalize_tool_args


DRIFT_OPERATOR_MESSAGE = (
    "could not apply — current state no longer matches what you approved"
)


class CommitBoundary:
    """Verify and apply a captured mutation manifest under ratified assent."""

    def __init__(
        self,
        *,
        mcp: Any | None = None,
        run_id: uuid.UUID | None = None,
        artifact_id_factory: Callable[[], uuid.UUID] = uuid.uuid4,
    ) -> None:
        self._mcp = mcp
        self._run_id = run_id or uuid.uuid4()
        self._artifact_id_factory = artifact_id_factory

    async def dispatch(
        self,
        node: NodeSpec,
        resolved_inputs: dict[str, NodeResult],
        *,
        assent_record: Any | None,
    ) -> NodeResult:
        """Run commit verification and the gated apply.

        ``assent_record`` is intentionally a call-time argument, supplied by the
        dispatch closure rather than the executor or graph spec.
        """

        try:
            held = _held_manifest(node)
        except (KeyError, MutationManifestError) as exc:
            return self._error_result(
                CommitError.MUTATION_MANIFEST_INVALID,
                str(exc),
                resolved_inputs,
            )

        target_tool = held.apply_counterpart["tool"]
        mcp = self._mcp if self._mcp is not None else _default_mcp()
        available = await _maybe_list_tools(mcp)
        if available is not None and target_tool not in _tool_names(available):
            return self._error_result(
                CommitError.APPLY_COUNTERPART_NOT_DECLARED,
                f"apply counterpart {target_tool!r} is not declared",
                resolved_inputs,
            )

        verify_params = _manifest_params(held, mode="verify")
        if available is not None:
            verify_params = normalize_tool_args(target_tool, verify_params, available)
        fresh_payload = _extract_payload(
            await mcp.call_tool(target_tool, arguments=verify_params)
        )
        try:
            fresh = MutationManifest.from_dict(fresh_payload)
        except MutationManifestError as exc:
            return self._error_result(
                CommitError.MUTATION_MANIFEST_INVALID,
                str(exc),
                resolved_inputs,
            )

        try:
            verification = CommitNode().verify(held, fresh, assent=assent_record)
        except TypeError as exc:
            return self._error_result(
                CommitError.ASSENT_INVALID,
                str(exc),
                resolved_inputs,
            )
        if not verification.matched:
            return self._error_result(
                CommitError.PLAN_STATE_DRIFT,
                DRIFT_OPERATOR_MESSAGE,
                resolved_inputs,
                drift_count=verification.drift_count,
                first_drift_index=verification.first_drift_index,
            )
        if assent_record is None or not verification.assent_valid:
            graph_intent_id = getattr(assent_record, "graph_intent_id", None)
            message = "AssentRecord is not in ratified state."
            if graph_intent_id:
                message = f"{message} graph_intent_id={graph_intent_id}"
            return self._error_result(
                CommitError.ASSENT_INVALID,
                message,
                resolved_inputs,
            )

        apply_params = _manifest_params(held, mode="apply")
        if available is not None:
            apply_params = normalize_tool_args(target_tool, apply_params, available)
        apply_payload = _extract_payload(
            await mcp.call_tool(target_tool, arguments=apply_params)
        )
        if isinstance(apply_payload, dict) and apply_payload.get("drift") is True:
            return self._error_result(
                CommitError.PLAN_STATE_DRIFT,
                DRIFT_OPERATOR_MESSAGE,
                resolved_inputs,
            )

        output = {
            "type": "commit_applied",
            "execution_state": "applied",
            "verified": True,
            "applied": True,
            "message": "applied",
            "count": len(held.resolved_plan),
            "apply_result": apply_payload,
        }
        return NodeResult(
            status="ok",
            run_id=self._run_id,
            artifact_id=self._artifact_id_factory(),
            output=output,
            output_topology=infer_topology(output).to_dict(),
            artifact_type="commit_result",
            source_artifact_ids=_source_artifact_ids(resolved_inputs),
            resolved_class="mcp.host_mutation",
        )

    def _error_result(
        self,
        reason_code: str,
        message: str,
        resolved_inputs: dict[str, NodeResult],
        *,
        drift_count: int | None = None,
        first_drift_index: int | None = None,
    ) -> NodeResult:
        error: dict[str, Any] = {
            "type": reason_code,
            "message": message,
        }
        if drift_count is not None:
            error["drift_count"] = drift_count
        if first_drift_index is not None:
            error["first_drift_index"] = first_drift_index
        return NodeResult(
            status="error",
            run_id=self._run_id,
            output={"error": error},
            reason_code=reason_code,
            message=message,
            source_artifact_ids=_source_artifact_ids(resolved_inputs),
            resolved_class="mcp.host_mutation",
        )


def _default_mcp() -> Any:
    from forge_bridge.mcp.server import mcp

    return mcp


def _held_manifest(node: NodeSpec) -> MutationManifest:
    raw = node.config.get("held") or node.config["manifest"]
    if isinstance(raw, MutationManifest):
        return raw
    return MutationManifest.from_dict(raw)


def _manifest_params(manifest: MutationManifest, *, mode: str) -> dict[str, Any]:
    params = dict(manifest.intent_parameters)
    params.update(manifest.apply_counterpart["parameter_overrides"])
    params["mode"] = mode
    params["resolved_plan"] = [item.to_dict() for item in manifest.resolved_plan]
    return params


def _tool_names(tools: Any) -> set[str]:
    return {
        str(name)
        for name in (
            getattr(tool, "name", None)
            for tool in tools
        )
        if name
    }


def _source_artifact_ids(
    resolved_inputs: dict[str, NodeResult],
) -> tuple[uuid.UUID, ...]:
    return tuple(
        result.artifact_id
        for result in resolved_inputs.values()
        if result.artifact_id is not None
    )


__all__ = [
    "CommitBoundary",
    "DRIFT_OPERATOR_MESSAGE",
]
