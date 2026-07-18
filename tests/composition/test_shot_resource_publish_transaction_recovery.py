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
from forge_bridge.core.assent import AssentRecord
from forge_bridge.graph.commit import CommitError


_STATUS_TOOL = "forge_inspect_shot_resource_publish_transaction"
_ABORT_TOOL = "forge_abort_shot_resource_publish_transaction"
_TRANSACTION_ID = "txn-sh010-comp-artist-a-v002"


def _abort_plan(
    *,
    journal_sha256: str = "journal-sha-1",
    ready: bool = True,
    registration_started: bool = False,
) -> dict[str, Any]:
    return {
        "kind": "pipeline.shot_resource.publish_transaction_abort_plan",
        "schema_version": 1,
        "status": "ready" if ready else "blocked",
        "trust_status": "trusted" if ready else "review_required",
        "ready_for_abort": ready,
        "mutation_safe": True,
        "state_owner": "peer_owned",
        "canonical": "/show",
        "transaction_id": _TRANSACTION_ID,
        "journal_path": (
            f"/show/.forge/publish_transactions/{_TRANSACTION_ID}/journal.json"
        ),
        "journal_status": "failed",
        "journal_sha256": journal_sha256,
        "registered_count": 0,
        "registration_started": registration_started,
        "recommended_action": "retry_or_abort",
        "recovery_reason": "artifact apply failed before registration",
        "role_states": [
            {
                "role": "beauty",
                "stage_version_path": "/show/.forge/stage/beauty/v002",
                "stage_exists": True,
                "stage_owned": True,
                "final_version_path": "/show/sh010/beauty/v002",
                "final_exists": False,
                "final_owned": None,
            }
        ],
        "expected_cleaned_paths": ["/show/.forge/stage/beauty/v002"],
        "issues": (
            []
            if ready
            else [
                {
                    "code": "publish_transaction.abort_registration_uncertain",
                    "message": "Registration may have Bridge side effects.",
                }
            ]
        ),
    }


def _abort_manifest(
    *,
    journal_sha256: str = "journal-sha-1",
    ready: bool = True,
    registration_started: bool = False,
) -> dict[str, Any]:
    plan = _abort_plan(
        journal_sha256=journal_sha256,
        ready=ready,
        registration_started=registration_started,
    )
    return {
        "kind": (
            "pipeline.shot_resource.callable_publish_transaction_abort_result"
        ),
        "schema_version": 1,
        "operation_type": (
            "pipeline.shot_resource.publish_transaction.abort.callable"
        ),
        "type": "mutation_plan",
        "ok": True,
        "status": "ready",
        "trust_status": "trusted",
        "mutation_safe": True,
        "state_owner": "peer_owned",
        "abort_plan": plan,
        "intent_parameters": {
            "params": {
                "canonical": "/show",
                "transaction_id": _TRANSACTION_ID,
            },
            "idempotency_key": "transaction-abort-1",
        },
        "resolved_plan": [
            {
                "identity": {
                    "operation_type": (
                        "pipeline.shot_resource.publish_transaction.abort.callable"
                    ),
                    "transaction_id": _TRANSACTION_ID,
                    "journal_sha256": journal_sha256,
                },
                "payload": {"abort_plan": plan},
            }
        ],
        "originating_capability": _ABORT_TOOL,
        "apply_counterpart": {
            "tool": _ABORT_TOOL,
            "parameter_overrides": {},
        },
    }


def _abort_sequence() -> list[dict[str, Any]]:
    return [
        {
            "operator_id": _ABORT_TOOL,
            "arguments": {
                "params": {
                    "canonical": "/show",
                    "transaction_id": _TRANSACTION_ID,
                },
                "idempotency_key": "transaction-abort-1",
                "mode": "discover",
            },
            "inputs": [],
            "output_artifact_id": "publish-transaction-abort:held",
            "output_artifact_type": "mutation_plan",
        },
        {
            "operator_id": "commit",
            "arguments": {},
            "inputs": [
                {
                    "artifact_id": "publish-transaction-abort:held",
                    "artifact_type": "mutation_plan",
                    "metadata": {"role": "held"},
                }
            ],
            "output_artifact_id": "publish-transaction-abort:commit",
            "output_artifact_type": "commit_result",
        },
    ]


def _status_sequence() -> list[dict[str, Any]]:
    return [
        {
            "operator_id": _STATUS_TOOL,
            "arguments": {
                "params": {
                    "canonical": "/show",
                    "transaction_id": _TRANSACTION_ID,
                }
            },
            "inputs": [],
            "output_artifact_id": "publish-transaction:status",
            "output_artifact_type": "mcp_read_result",
        }
    ]


class _RecoveryMCP:
    def __init__(
        self,
        *,
        held: dict[str, Any] | None = None,
        fresh: dict[str, Any] | None = None,
        apply_drift: bool = False,
        replay: bool = False,
        registration_started: bool = False,
    ) -> None:
        self.held = copy.deepcopy(held or _abort_manifest())
        self.fresh = copy.deepcopy(fresh if fresh is not None else self.held)
        self.apply_drift = apply_drift
        self.replay = replay
        self.registration_started = registration_started
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.apply_count = 0

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
            SimpleNamespace(name=_STATUS_TOOL, inputSchema=schema),
            SimpleNamespace(name=_ABORT_TOOL, inputSchema=schema),
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]):
        self.calls.append((name, copy.deepcopy(arguments)))
        if name == _STATUS_TOOL:
            return {
                "ok": True,
                "status": "failed",
                "trust_status": "review_required",
                "read_only": True,
                "state_owner": "read_only",
                "transaction_id": _TRANSACTION_ID,
                "abort_allowed": True,
                "recommended_action": "retry_or_abort",
            }
        assert name == _ABORT_TOOL
        mode = arguments.get("mode", "discover")
        if mode == "discover":
            if self.registration_started:
                return {
                    "ok": False,
                    "status": "failed",
                    "trust_status": "review_required",
                    "state_owner": "peer_owned",
                    "stage": "plan",
                    "error": "Transaction is not eligible for automatic abort.",
                    "abort_plan": _abort_plan(
                        ready=False,
                        registration_started=True,
                    ),
                }
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
                    "mutation_safe": False,
                }
            return {
                "ok": True,
                "status": "succeeded",
                "trust_status": "trusted",
                "mode": "apply",
                "state_owner": "peer_owned",
                "idempotent_replay": self.replay,
                "abort_apply": {
                    "status": "aborted",
                    "trust_status": "trusted",
                    "cleaned_count": 1,
                    "idempotent_replay": self.replay,
                },
            }
        raise AssertionError(mode)


def _assent(status: str) -> AssentRecord:
    return AssentRecord(
        graph_intent_id="shot-resource-publish-transaction-abort",
        chain_steps=["abort shot-resource publish transaction", "commit"],
        status=status,
        decided_by="operator" if status == "ratified" else None,
    )


async def _run_abort(
    *,
    assent_status: str,
    fresh: dict[str, Any] | None = None,
    apply_drift: bool = False,
    replay: bool = False,
    registration_started: bool = False,
):
    mcp = _RecoveryMCP(
        fresh=fresh,
        apply_drift=apply_drift,
        replay=replay,
        registration_started=registration_started,
    )
    dispatch = UnifiedDispatch(
        mcp_boundary=MCPToolBoundary(mcp=mcp),
        commit_boundary=CommitBoundary(mcp=mcp),
        assent_record=_assent(assent_status),
    )
    results = await GraphExecutor(dispatch.dispatch).run(
        compile_operator_sequence(_abort_sequence())
    )
    return results, mcp


@pytest.mark.asyncio
async def test_status_is_an_admitted_read_only_graph_node() -> None:
    mcp = _RecoveryMCP()
    dispatch = UnifiedDispatch(mcp_boundary=MCPToolBoundary(mcp=mcp))

    results = await GraphExecutor(dispatch.dispatch).run(
        compile_operator_sequence(_status_sequence())
    )

    result = results[f"{_STATUS_TOOL}#0"]
    assert result.status == "ok"
    assert result.output["read_only"] is True
    assert result.output["abort_allowed"] is True
    assert result.resolved_class == "mcp.publish_transaction_status"
    assert [name for name, _arguments in mcp.calls] == [_STATUS_TOOL]


@pytest.mark.asyncio
@pytest.mark.parametrize("replay", [False, True])
async def test_abort_graph_verifies_and_applies_after_ratification(replay: bool) -> None:
    results, mcp = await _run_abort(assent_status="ratified", replay=replay)

    discovery = results[f"{_ABORT_TOOL}#0"].output
    commit = results["commit#1"].output
    assert discovery["state_owner"] == "peer_owned"
    assert commit["type"] == "commit_applied"
    assert commit["apply_result"]["abort_apply"]["status"] == "aborted"
    assert commit["apply_result"]["idempotent_replay"] is replay
    assert mcp.apply_count == 1
    assert [arguments["mode"] for name, arguments in mcp.calls if name == _ABORT_TOOL] == [
        "discover",
        "verify",
        "apply",
    ]


@pytest.mark.asyncio
async def test_abort_graph_refuses_unratified_apply() -> None:
    results, mcp = await _run_abort(assent_status="proposed")

    assert results["commit#1"].status == "error"
    assert results["commit#1"].reason_code == CommitError.ASSENT_INVALID
    assert mcp.apply_count == 0


@pytest.mark.asyncio
async def test_abort_graph_refuses_fresh_ownership_drift() -> None:
    results, mcp = await _run_abort(
        assent_status="ratified",
        fresh=_abort_manifest(
            journal_sha256="journal-sha-after-ownership-drift",
            ready=False,
        ),
    )

    assert results["commit#1"].status == "error"
    assert results["commit#1"].reason_code == CommitError.PLAN_STATE_DRIFT
    assert mcp.apply_count == 0


@pytest.mark.asyncio
async def test_abort_graph_refuses_apply_time_ownership_drift() -> None:
    results, mcp = await _run_abort(
        assent_status="ratified",
        apply_drift=True,
    )

    assert results["commit#1"].status == "error"
    assert results["commit#1"].reason_code == CommitError.PLAN_STATE_DRIFT
    assert mcp.apply_count == 1


@pytest.mark.asyncio
async def test_abort_discovery_refuses_after_registration_started() -> None:
    results, mcp = await _run_abort(
        assent_status="ratified",
        registration_started=True,
    )

    discovery = results[f"{_ABORT_TOOL}#0"]
    assert discovery.status == "error"
    assert discovery.output is None
    assert results["commit#1"].reason_code == CommitError.MUTATION_MANIFEST_INVALID
    assert mcp.apply_count == 0
