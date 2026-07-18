from __future__ import annotations

import copy
from types import SimpleNamespace
from typing import Any

import pytest

from forge_bridge.composition.boundary import MCPToolBoundary
from forge_bridge.composition.commit_boundary import CommitBoundary
from forge_bridge.composition.compiler import compile_operator_sequence
from forge_bridge.composition.dispatch import UnifiedDispatch
from forge_bridge.composition.executor import GraphExecutor
from forge_bridge.composition.operation_boundary import OperationDispatchBoundary
from forge_bridge.core.assent import AssentRecord
from forge_bridge.graph.commit import CommitError


_COPY_TOOL = "forge_promote_shot_resource_stream"
_REGISTER_TOOL = "forge_register_shot_resource_promotion"
_VALIDATE_OPERATION = "pipeline.shot_resource.stream_promotion.validate"
_PLAN_OPERATION = "pipeline.shot_resource.stream_promotion.registration_plan"


def _promotion_result() -> dict[str, Any]:
    return {
        "kind": "pipeline.shot_resource.stream_promotion_result",
        "schema_version": 1,
        "status": "passed",
        "trust_status": "trusted",
        "canonical": "/show",
        "shot": "sh010",
        "task": "comp",
        "target_stream": "main",
        "target_version": "v002",
        "action_results": [
            {
                "kind": "pipeline.shot_resource.stream_promotion_proof",
                "status": "passed",
                "trust_status": "trusted",
                "role": "comp",
                "target_stream": "main",
                "target_version": "v002",
                "target_path": "/show/sh010/comp/v002",
            }
        ],
    }


def _copy_manifest() -> dict[str, Any]:
    plan = {
        "kind": "pipeline.shot_resource.stream_promotion_plan",
        "schema_version": 1,
        "status": "ready",
        "ready_for_promotion": True,
        "mutation_safe": True,
        "shot": "sh010",
        "target_version": "v002",
        "actions": [],
    }
    return {
        "type": "mutation_plan",
        "status": "succeeded",
        "trust_status": "trusted",
        "intent_parameters": {
            "params": {"shot": "sh010"},
            "idempotency_key": "copy-1",
        },
        "resolved_plan": [
            {
                "identity": {
                    "operation_type": (
                        "pipeline.shot_resource.stream_promotion.callable"
                    ),
                    "shot": "sh010",
                    "target_version": "v002",
                },
                "payload": {"promotion_plan": plan},
            }
        ],
        "originating_capability": _COPY_TOOL,
        "apply_counterpart": {
            "tool": _COPY_TOOL,
            "parameter_overrides": {},
        },
    }


def _validation() -> dict[str, Any]:
    return {
        "kind": "pipeline.shot_resource.stream_promotion_validation_result",
        "schema_version": 1,
        "status": "passed",
        "trust_status": "trusted",
        "mutation_safe": True,
        "ready_for_registration": True,
        "promotion_result": _promotion_result(),
        "action_validations": [
            {
                "kind": (
                    "pipeline.shot_resource.stream_promotion_load_validation"
                ),
                "status": "passed",
                "trust_status": "trusted",
                "admitted": True,
                "role": "comp",
                "target_path": "/show/sh010/comp/v002",
            }
        ],
    }


def _registration_plan(*, target_version: str = "v002") -> dict[str, Any]:
    target_path = f"/show/sh010/comp/{target_version}"
    return {
        "kind": "pipeline.shot_resource.publish_registration_plan",
        "schema_version": 1,
        "status": "ready",
        "ready_for_registration": True,
        "mutation_safe": True,
        "candidate_count": 1,
        "candidates": [
            {
                "status": "ready",
                "trust_status": "trusted",
                "asset_registration": {
                    "name": f"sh010_comp_{target_version}",
                    "idempotency_key": f"register:{target_path}",
                },
                "location_registrations": [
                    {"path": target_path, "storage_type": "local"}
                ],
            }
        ],
        "issues": [],
    }


def _catalog_manifest(*, target_version: str = "v002") -> dict[str, Any]:
    plan = _registration_plan(target_version=target_version)
    return {
        "kind": (
            "pipeline.shot_resource.stream_promotion_registration_plan_result"
        ),
        "schema_version": 1,
        "operation_type": _PLAN_OPERATION,
        "type": "mutation_plan",
        "status": "ready",
        "trust_status": "trusted",
        "mutation_safe": True,
        "ready_for_registration": True,
        "registration_plan": plan,
        "intent_parameters": {
            "params": {
                "promotion_result": _promotion_result(),
                "validation_params": {"shot": "sh010"},
                "registration_params": {},
            },
            "idempotency_key": "register-1",
        },
        "resolved_plan": [
            {
                "identity": {
                    "operation_type": (
                        "pipeline.shot_resource.stream_promotion.registration.callable"
                    ),
                    "candidate_count": 1,
                },
                "payload": {"registration_plan": plan},
            }
        ],
        "originating_capability": _PLAN_OPERATION,
        "apply_counterpart": {
            "tool": _REGISTER_TOOL,
            "parameter_overrides": {},
        },
    }


def _operator_sequence() -> list[dict[str, Any]]:
    return [
        {
            "operator_id": _COPY_TOOL,
            "arguments": {
                "params": {"shot": "sh010"},
                "idempotency_key": "copy-1",
                "mode": "discover",
            },
            "inputs": [],
            "output_artifact_id": "promotion:held",
            "output_artifact_type": "mutation_plan",
        },
        {
            "operator_id": "commit",
            "inputs": [
                {
                    "artifact_id": "promotion:held",
                    "artifact_type": "mutation_plan",
                    "metadata": {"role": "held"},
                }
            ],
            "output_artifact_id": "promotion:commit",
            "output_artifact_type": "commit_result",
        },
        {
            "operator_id": _VALIDATE_OPERATION,
            "arguments": {},
            "inputs": [
                {
                    "artifact_id": "promotion:commit",
                    "artifact_type": "commit_result",
                    "metadata": {"role": "promotion_commit"},
                }
            ],
            "output_artifact_id": "promotion:validation",
            "output_artifact_type": (
                "pipeline.shot_resource.stream_promotion_validation_result"
            ),
        },
        {
            "operator_id": _PLAN_OPERATION,
            "arguments": {},
            "inputs": [
                {
                    "artifact_id": "promotion:commit",
                    "artifact_type": "commit_result",
                    "metadata": {"role": "promotion_commit"},
                },
                {
                    "artifact_id": "promotion:validation",
                    "artifact_type": (
                        "pipeline.shot_resource.stream_promotion_validation_result"
                    ),
                    "metadata": {"role": "promotion_validation"},
                },
            ],
            "output_artifact_id": "registration:held",
            "output_artifact_type": "mutation_plan",
        },
        {
            "operator_id": "commit",
            "inputs": [
                {
                    "artifact_id": "registration:held",
                    "artifact_type": "mutation_plan",
                    "metadata": {"role": "held"},
                }
            ],
            "output_artifact_id": "registration:commit",
            "output_artifact_type": "commit_result",
        },
    ]


class _MCP:
    def __init__(
        self,
        *,
        fresh_catalog: dict[str, Any] | None = None,
        catalog_apply_drift: bool = False,
    ) -> None:
        self.copy = _copy_manifest()
        self.catalog = _catalog_manifest()
        self.fresh_catalog = fresh_catalog or self.catalog
        self.catalog_apply_drift = catalog_apply_drift
        self.calls: list[tuple[str, str]] = []
        self.apply_counts = {_COPY_TOOL: 0, _REGISTER_TOOL: 0}

    async def list_tools(self):
        schema = {
            "type": "object",
            "properties": {
                "params": {"type": "object"},
                "mode": {"type": "string"},
                "resolved_plan": {"type": "array"},
                "idempotency_key": {"type": "string"},
            },
            "required": ["params"],
        }
        return [
            SimpleNamespace(name=_COPY_TOOL, inputSchema=schema),
            SimpleNamespace(name=_REGISTER_TOOL, inputSchema=schema),
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]):
        mode = str(arguments.get("mode") or "discover")
        self.calls.append((name, mode))
        if name == _COPY_TOOL:
            if mode in {"discover", "verify"}:
                return copy.deepcopy(self.copy)
            self.apply_counts[name] += 1
            return {
                "ok": True,
                "status": "succeeded",
                "trust_status": "trusted",
                "promotion_apply": _promotion_result(),
                "catalog_registration_status": "pending",
            }
        if name == _REGISTER_TOOL:
            if mode == "verify":
                return copy.deepcopy(self.fresh_catalog)
            self.apply_counts[name] += 1
            if self.catalog_apply_drift:
                return {
                    "ok": False,
                    "status": "failed",
                    "stage": "validation_drift",
                    "drift": True,
                }
            return {
                "ok": True,
                "status": "succeeded",
                "trust_status": "trusted",
                "catalog_registration_status": "registered",
                "registered_count": 1,
            }
        raise AssertionError(name)


def _assent(status: str) -> AssentRecord:
    return AssentRecord(
        graph_intent_id="stream-promotion-registration",
        chain_steps=[
            _COPY_TOOL,
            "commit",
            _VALIDATE_OPERATION,
            _PLAN_OPERATION,
            "commit",
        ],
        status=status,
        decided_by="operator" if status == "ratified" else None,
    )


async def _run(
    *,
    assent_status: str = "ratified",
    fresh_catalog: dict[str, Any] | None = None,
    catalog_apply_drift: bool = False,
):
    operation_calls: list[tuple[str, dict[str, Any]]] = []

    async def run_operation(operation_type: str, *, params: dict, **_kwargs):
        operation_calls.append((operation_type, copy.deepcopy(params)))
        if operation_type == _VALIDATE_OPERATION:
            assert params["promotion_commit"]["type"] == "commit_applied"
            return {"status": "success", "data": _validation()}
        if operation_type == _PLAN_OPERATION:
            assert params["promotion_commit"]["type"] == "commit_applied"
            assert params["promotion_validation"] == _validation()
            return {"status": "success", "data": _catalog_manifest()}
        raise AssertionError(operation_type)

    mcp = _MCP(
        fresh_catalog=fresh_catalog,
        catalog_apply_drift=catalog_apply_drift,
    )
    dispatch = UnifiedDispatch(
        mcp_boundary=MCPToolBoundary(mcp=mcp),
        operation_boundary=OperationDispatchBoundary(run_operation=run_operation),
        commit_boundary=CommitBoundary(mcp=mcp),
        assent_record=_assent(assent_status),
    )
    results = await GraphExecutor(dispatch.dispatch).run(
        compile_operator_sequence(_operator_sequence())
    )
    return results, mcp, operation_calls


@pytest.mark.asyncio
async def test_full_promotion_registration_graph_commits_both_state_owners():
    results, mcp, operation_calls = await _run()

    assert results["commit#1"].output["apply_result"][
        "catalog_registration_status"
    ] == "pending"
    assert results[f"{_VALIDATE_OPERATION}#2"].output["trust_status"] == "trusted"
    assert results[f"{_PLAN_OPERATION}#3"].output["type"] == "mutation_plan"
    assert results["commit#4"].output["apply_result"][
        "catalog_registration_status"
    ] == "registered"
    assert mcp.apply_counts == {_COPY_TOOL: 1, _REGISTER_TOOL: 1}
    assert [name for name, _params in operation_calls] == [
        _VALIDATE_OPERATION,
        _PLAN_OPERATION,
    ]
    assert mcp.calls == [
        (_COPY_TOOL, "discover"),
        (_COPY_TOOL, "verify"),
        (_COPY_TOOL, "apply"),
        (_REGISTER_TOOL, "verify"),
        (_REGISTER_TOOL, "apply"),
    ]


@pytest.mark.asyncio
async def test_catalog_commit_refuses_fresh_registration_plan_drift():
    results, mcp, _ = await _run(
        fresh_catalog=_catalog_manifest(target_version="v003")
    )

    assert results["commit#4"].status == "error"
    assert results["commit#4"].reason_code == CommitError.PLAN_STATE_DRIFT
    assert mcp.apply_counts[_REGISTER_TOOL] == 0


@pytest.mark.asyncio
async def test_catalog_commit_refuses_apply_time_validation_drift():
    results, mcp, _ = await _run(catalog_apply_drift=True)

    assert results["commit#4"].status == "error"
    assert results["commit#4"].reason_code == CommitError.PLAN_STATE_DRIFT
    assert mcp.apply_counts[_REGISTER_TOOL] == 1


@pytest.mark.asyncio
async def test_unratified_graph_refuses_before_either_mutation():
    results, mcp, operation_calls = await _run(assent_status="proposed")

    assert results["commit#1"].status == "error"
    assert results["commit#1"].reason_code == CommitError.ASSENT_INVALID
    assert results["commit#4"].status == "error"
    assert results["commit#4"].reason_code == CommitError.MUTATION_MANIFEST_INVALID
    assert mcp.apply_counts == {_COPY_TOOL: 0, _REGISTER_TOOL: 0}
    assert [name for name, _params in operation_calls] == [
        _VALIDATE_OPERATION,
        _PLAN_OPERATION,
    ]
