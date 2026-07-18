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


_TOOL = "forge_promote_shot_resource_stream"


def _manifest(*, target_version: str = "v002") -> dict[str, Any]:
    promotion_plan = {
        "kind": "pipeline.shot_resource.stream_promotion_plan",
        "schema_version": 1,
        "status": "ready",
        "ready_for_promotion": True,
        "mutation_safe": True,
        "canonical": "/show",
        "shot": "sh010",
        "task": "comp",
        "source_stream": "artist_a",
        "source_version": "v002",
        "target_stream": "main",
        "target_version": target_version,
        "actions": [
            {
                "action_type": "stream_version_promote",
                "status": "ready",
                "role": "plate",
                "source_path": "/show/sh010/plate/_streams/artist_a/v002",
                "target_path": f"/show/sh010/plate/{target_version}",
            }
        ],
    }
    return {
        "type": "mutation_plan",
        "status": "succeeded",
        "trust_status": "trusted",
        "intent_parameters": {
            "params": {
                "canonical": "/show",
                "shot": "sh010",
                "task": "comp",
                "source_stream": "artist_a",
                "source_version": "v002",
                "target_stream": "main",
            },
            "idempotency_key": "promotion-commit-1",
        },
        "resolved_plan": [
            {
                "identity": {
                    "operation_type": (
                        "pipeline.shot_resource.stream_promotion.callable"
                    ),
                    "shot": "sh010",
                    "task": "comp",
                    "source_stream": "artist_a",
                    "source_version": "v002",
                    "target_stream": "main",
                    "target_version": target_version,
                },
                "payload": {"promotion_plan": promotion_plan},
            }
        ],
        "originating_capability": _TOOL,
        "apply_counterpart": {"tool": _TOOL, "parameter_overrides": {}},
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
                    "source_stream": "artist_a",
                    "source_version": "v002",
                    "target_stream": "main",
                },
                "idempotency_key": "promotion-commit-1",
                "mode": "discover",
            },
            "inputs": [],
            "output_artifact_id": "promotion:held",
            "output_artifact_type": "mutation_plan",
        },
        {
            "operator_id": "commit",
            "arguments": {},
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
    ]


class _PromotionMCP:
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
                }
            return {
                "ok": True,
                "status": "succeeded",
                "trust_status": "trusted",
                "mode": "apply",
                "idempotent_replay": self.replay,
                "catalog_registration_required": True,
                "catalog_registration_status": "pending",
            }
        raise AssertionError(mode)


def _assent(status: str) -> AssentRecord:
    return AssentRecord(
        graph_intent_id="shot-resource-promotion-commit",
        chain_steps=["promote shot-resource stream", "commit"],
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
    mcp = _PromotionMCP(
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
async def test_promotion_graph_verifies_and_applies_once_after_ratification(replay):
    results, mcp = await _run(assent_status="ratified", replay=replay)

    assert results[f"{_TOOL}#0"].output["type"] == "mutation_plan"
    assert results["commit#1"].output["type"] == "commit_applied"
    assert results["commit#1"].output["apply_result"][
        "catalog_registration_status"
    ] == "pending"
    assert results["commit#1"].output["apply_result"][
        "idempotent_replay"
    ] is replay
    assert mcp.apply_count == 1
    assert [arguments["mode"] for arguments in mcp.calls] == [
        "discover",
        "verify",
        "apply",
    ]


@pytest.mark.asyncio
async def test_promotion_graph_refuses_unratified_apply():
    results, mcp = await _run(assent_status="proposed")

    assert results["commit#1"].status == "error"
    assert results["commit#1"].reason_code == CommitError.ASSENT_INVALID
    assert mcp.apply_count == 0


@pytest.mark.asyncio
async def test_promotion_graph_refuses_fresh_plan_drift():
    results, mcp = await _run(
        assent_status="ratified",
        fresh=_manifest(target_version="v003"),
    )

    assert results["commit#1"].status == "error"
    assert results["commit#1"].reason_code == CommitError.PLAN_STATE_DRIFT
    assert mcp.apply_count == 0


@pytest.mark.asyncio
async def test_promotion_graph_refuses_apply_time_drift():
    results, mcp = await _run(
        assent_status="ratified",
        apply_drift=True,
    )

    assert results["commit#1"].status == "error"
    assert results["commit#1"].reason_code == CommitError.PLAN_STATE_DRIFT
    assert mcp.apply_count == 1
