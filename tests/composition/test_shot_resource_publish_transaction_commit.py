from __future__ import annotations

import copy
from types import SimpleNamespace
from typing import Any

import pytest

from forge_bridge.composition.admission import admit_mutation_counterpart
from forge_bridge.composition.boundary import MCPToolBoundary
from forge_bridge.composition.commit_boundary import CommitBoundary
from forge_bridge.composition.compiler import compile_operator_sequence
from forge_bridge.composition.dispatch import UnifiedDispatch
from forge_bridge.composition.executor import GraphExecutor
from forge_bridge.core.assent import AssentRecord
from forge_bridge.graph.commit import CommitError


_TOOL = "forge_publish_shot_resource_transaction"


def _manifest(*, version: str = "v002") -> dict[str, Any]:
    transaction_plan = {
        "kind": "pipeline.shot_resource.publish_transaction_plan",
        "schema_version": 1,
        "status": "ready",
        "trust_status": "trusted",
        "ready_for_apply": True,
        "mutation_safe": True,
        "transaction_id": "txn-sh010-comp-artist-a-v002",
        "canonical": "/show",
        "shot": "sh010",
        "task": "comp",
        "stream": "artist_a",
        "version": version,
        "roles": ["beauty", "matte"],
        "actions": [
            {
                "role": role,
                "source_manifest": {
                    "schema_version": 1,
                    "method": "path_size_xxh64",
                    "source_path": f"/capture/{role}.1001.exr",
                    "file_count": 1,
                    "total_size_bytes": 16,
                    "entries": [
                        {
                            "path": f"/capture/{role}.1001.exr",
                            "relative_path": f"{role}.1001.exr",
                            "size_bytes": 16,
                            "xxh64": f"digest-{role}",
                        }
                    ],
                },
                "final_version_path": f"/show/sh010/{role}/{version}",
            }
            for role in ("beauty", "matte")
        ],
    }
    return {
        "kind": "pipeline.shot_resource.callable_publish_transaction_result",
        "schema_version": 1,
        "type": "mutation_plan",
        "ok": True,
        "status": "ready",
        "trust_status": "trusted",
        "mutation_safe": True,
        "state_owner": "federated_transaction",
        "transaction_plan": transaction_plan,
        "intent_parameters": {
            "params": {
                "canonical": "/show",
                "shot": "sh010",
                "task": "comp",
                "stream": "artist_a",
            },
            "idempotency_key": "transaction-commit-1",
        },
        "resolved_plan": [
            {
                "identity": {
                    "operation_type": ("pipeline.shot_resource.publish_transaction.callable"),
                    "transaction_id": transaction_plan["transaction_id"],
                    "stream": "artist_a",
                    "version": version,
                    "roles": ["beauty", "matte"],
                },
                "payload": {"transaction_plan": transaction_plan},
            }
        ],
        "originating_capability": _TOOL,
        "apply_counterpart": {
            "tool": _TOOL,
            "parameter_overrides": {},
        },
    }


def _operator_sequence() -> list[dict[str, Any]]:
    return [
        {
            "operator_id": _TOOL,
            "arguments": {
                "params": {
                    "canonical": "/show",
                    "shot": "sh010",
                    "task": "comp",
                    "stream": "artist_a",
                },
                "idempotency_key": "transaction-commit-1",
                "mode": "discover",
            },
            "inputs": [],
            "output_artifact_id": "publish-transaction:held",
            "output_artifact_type": "mutation_plan",
        },
        {
            "operator_id": "commit",
            "arguments": {},
            "inputs": [
                {
                    "artifact_id": "publish-transaction:held",
                    "artifact_type": "mutation_plan",
                    "metadata": {"role": "held"},
                }
            ],
            "output_artifact_id": "publish-transaction:commit",
            "output_artifact_type": "commit_result",
        },
    ]


class _PublishTransactionMCP:
    def __init__(
        self,
        *,
        held: dict[str, Any],
        fresh: dict[str, Any] | None = None,
        apply_drift: bool = False,
        replay: bool = False,
    ) -> None:
        self.held = copy.deepcopy(held)
        self.fresh = copy.deepcopy(fresh if fresh is not None else held)
        self.apply_drift = apply_drift
        self.replay = replay
        self.calls: list[dict[str, Any]] = []
        self.apply_count = 0

    async def list_tools(self):
        return [
            SimpleNamespace(
                name=_TOOL,
                inputSchema={
                    "type": "object",
                    "properties": {
                        "params": {"type": "object"},
                        "mode": {"type": "string"},
                        "resolved_plan": {"type": "array"},
                        "idempotency_key": {"type": "string"},
                    },
                    "required": ["params"],
                },
            )
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]):
        assert name == _TOOL
        self.calls.append(copy.deepcopy(arguments))
        mode = arguments.get("mode", "discover")
        if mode == "discover":
            return copy.deepcopy(self.held)
        assert arguments["resolved_plan"] == self.held["resolved_plan"]
        if mode == "verify":
            return copy.deepcopy(self.fresh)
        if mode == "apply":
            self.apply_count += 1
            if self.apply_drift:
                return {
                    "ok": False,
                    "status": "failed",
                    "stage": "plan_drift",
                    "drift": True,
                    "mutation_safe": True,
                }
            return {
                "ok": True,
                "status": "succeeded",
                "trust_status": "trusted",
                "mode": "apply",
                "state_owner": "federated_transaction",
                "idempotent_replay": self.replay,
                "registered_count": 2,
                "transaction_apply": {
                    "status": "committed",
                    "trust_status": "trusted",
                    "registered_count": 2,
                },
            }
        raise AssertionError(mode)


def _assent(status: str) -> AssentRecord:
    return AssentRecord(
        graph_intent_id="shot-resource-publish-transaction-commit",
        chain_steps=["publish shot-resource transaction", "commit"],
        status=status,
        decided_by="operator" if status == "ratified" else None,
    )


async def _run(
    *,
    assent_status: str,
    fresh: dict[str, Any] | None = None,
    apply_drift: bool = False,
    replay: bool = False,
):
    held = _manifest()
    mcp = _PublishTransactionMCP(
        held=held,
        fresh=fresh,
        apply_drift=apply_drift,
        replay=replay,
    )
    dispatch = UnifiedDispatch(
        mcp_boundary=MCPToolBoundary(mcp=mcp),
        commit_boundary=CommitBoundary(mcp=mcp),
        assent_record=_assent(assent_status),
    )
    results = await GraphExecutor(dispatch.dispatch).run(
        compile_operator_sequence(_operator_sequence())
    )
    return results, mcp


@pytest.mark.asyncio
@pytest.mark.parametrize("replay", [False, True])
async def test_transaction_graph_verifies_and_commits_after_ratification(replay):
    results, mcp = await _run(assent_status="ratified", replay=replay)

    discovery = results[f"{_TOOL}#0"].output
    commit = results["commit#1"].output
    assert discovery["type"] == "mutation_plan"
    assert discovery["state_owner"] == "federated_transaction"
    assert commit["type"] == "commit_applied"
    assert commit["apply_result"]["transaction_apply"]["status"] == "committed"
    assert commit["apply_result"]["registered_count"] == 2
    assert commit["apply_result"]["idempotent_replay"] is replay
    assert mcp.apply_count == 1
    assert [arguments["mode"] for arguments in mcp.calls] == [
        "discover",
        "verify",
        "apply",
    ]
    assert admit_mutation_counterpart(_TOOL).state_owner == ("federated_transaction")


@pytest.mark.asyncio
async def test_transaction_graph_refuses_unratified_apply():
    results, mcp = await _run(assent_status="proposed")

    assert results["commit#1"].status == "error"
    assert results["commit#1"].reason_code == CommitError.ASSENT_INVALID
    assert mcp.apply_count == 0


@pytest.mark.asyncio
async def test_transaction_graph_refuses_fresh_plan_drift():
    results, mcp = await _run(
        assent_status="ratified",
        fresh=_manifest(version="v003"),
    )

    assert results["commit#1"].status == "error"
    assert results["commit#1"].reason_code == CommitError.PLAN_STATE_DRIFT
    assert mcp.apply_count == 0


@pytest.mark.asyncio
async def test_transaction_graph_refuses_apply_time_source_drift():
    results, mcp = await _run(
        assent_status="ratified",
        apply_drift=True,
    )

    assert results["commit#1"].status == "error"
    assert results["commit#1"].reason_code == CommitError.PLAN_STATE_DRIFT
    assert mcp.apply_count == 1
