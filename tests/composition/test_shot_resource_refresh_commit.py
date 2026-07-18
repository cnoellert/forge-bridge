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


_TOOLS = (
    "forge_refresh_shot_resources",
    "forge_switch_shot_resource_version",
)


def _manifest(tool_name: str, *, version: int = 2) -> dict[str, Any]:
    operation_type = (
        "pipeline.shot_resource.refresh"
        if tool_name == "forge_refresh_shot_resources"
        else "pipeline.shot_resource.switch_version"
    )
    refresh_plan = {
        "schema_version": 1,
        "operation_type": operation_type,
        "target": {"dcc": "Nuke", "instance_id": "nuke-live-1"},
        "shot": "sh010",
        "component": "plate",
        "from_version": 1,
        "to_version": version,
        "actions": [
            {
                "action": "replace",
                "package_id": "sh010:plate",
                "path": f"/show/sh010/plate/v{version:03d}",
            }
        ],
    }
    return {
        "type": "mutation_plan",
        "status": "succeeded",
        "trust_status": "trusted",
        "intent_parameters": {
            "target": {"dcc": "Nuke", "instance_id": "nuke-live-1"},
            "params": {"dcc": "Nuke", "shot": "sh010", "component": "plate"},
        },
        "resolved_plan": [
            {
                "identity": {
                    "operation_type": operation_type,
                    "shot": "sh010",
                    "component": "plate",
                    "to_version": version,
                },
                "payload": {"refresh_plan": refresh_plan},
            }
        ],
        "originating_capability": tool_name,
        "apply_counterpart": {
            "tool": tool_name,
            "parameter_overrides": {},
        },
    }


def _operator_sequence(tool_name: str) -> list[dict[str, Any]]:
    return [
        {
            "operator_id": tool_name,
            "arguments": {
                "target": {"dcc": "Nuke", "instance_id": "nuke-live-1"},
                "params": {"dcc": "Nuke", "shot": "sh010", "component": "plate"},
                "mode": "discover",
            },
            "inputs": [],
            "output_artifact_id": "shot-refresh:held",
            "output_artifact_type": "mutation_plan",
        },
        {
            "operator_id": "commit",
            "arguments": {},
            "inputs": [
                {
                    "artifact_id": "shot-refresh:held",
                    "artifact_type": "mutation_plan",
                    "metadata": {"role": "held"},
                }
            ],
            "output_artifact_id": "shot-refresh:commit",
            "output_artifact_type": "commit_result",
        },
    ]


class _RefreshMCP:
    def __init__(
        self,
        tool_name: str,
        *,
        held: dict[str, Any],
        fresh: dict[str, Any] | None = None,
        apply_drift: bool = False,
    ) -> None:
        self.tool_name = tool_name
        self.held = copy.deepcopy(held)
        self.fresh = copy.deepcopy(fresh if fresh is not None else held)
        self.apply_drift = apply_drift
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.apply_count = 0

    async def list_tools(self):
        return [
            SimpleNamespace(
                name=self.tool_name,
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target": {"type": "object"},
                        "params": {"type": "object"},
                        "mode": {"type": "string"},
                        "resolved_plan": {"type": "array"},
                    },
                    "required": ["target", "params"],
                },
            )
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]):
        assert name == self.tool_name
        self.calls.append((name, copy.deepcopy(arguments)))
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
                    "status": "refused",
                    "stage": "plan_drift",
                    "drift": True,
                }
            return {
                "ok": True,
                "status": "succeeded",
                "trust_status": "trusted",
                "mode": "apply",
            }
        raise AssertionError(mode)


def _assent(status: str) -> AssentRecord:
    return AssentRecord(
        graph_intent_id="shot-resource-refresh-commit",
        chain_steps=["refresh shot resources", "commit"],
        status=status,
        decided_by="operator" if status == "ratified" else None,
    )


async def _run(
    tool_name: str,
    *,
    assent_status: str,
    fresh: dict[str, Any] | None = None,
    apply_drift: bool = False,
):
    held = _manifest(tool_name)
    mcp = _RefreshMCP(
        tool_name,
        held=held,
        fresh=fresh,
        apply_drift=apply_drift,
    )
    dispatch = UnifiedDispatch(
        mcp_boundary=MCPToolBoundary(mcp=mcp),
        commit_boundary=CommitBoundary(mcp=mcp),
        assent_record=_assent(assent_status),
    )
    results = await GraphExecutor(dispatch.dispatch).run(
        compile_operator_sequence(_operator_sequence(tool_name))
    )
    return results, mcp


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name", _TOOLS)
async def test_refresh_graph_verifies_and_applies_once_after_ratification(tool_name):
    results, mcp = await _run(tool_name, assent_status="ratified")

    assert results[f"{tool_name}#0"].output["type"] == "mutation_plan"
    assert results["commit#1"].output["type"] == "commit_applied"
    assert results["commit#1"].output["count"] == 1
    assert mcp.apply_count == 1
    assert [arguments["mode"] for _name, arguments in mcp.calls] == [
        "discover",
        "verify",
        "apply",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name", _TOOLS)
async def test_refresh_graph_refuses_unratified_apply(tool_name):
    results, mcp = await _run(tool_name, assent_status="proposed")

    assert results["commit#1"].status == "error"
    assert results["commit#1"].reason_code == CommitError.ASSENT_INVALID
    assert mcp.apply_count == 0
    assert [arguments["mode"] for _name, arguments in mcp.calls] == [
        "discover",
        "verify",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name", _TOOLS)
async def test_refresh_graph_refuses_fresh_plan_drift(tool_name):
    results, mcp = await _run(
        tool_name,
        assent_status="ratified",
        fresh=_manifest(tool_name, version=3),
    )

    assert results["commit#1"].status == "error"
    assert results["commit#1"].reason_code == CommitError.PLAN_STATE_DRIFT
    assert mcp.apply_count == 0
    assert [arguments["mode"] for _name, arguments in mcp.calls] == [
        "discover",
        "verify",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name", _TOOLS)
async def test_refresh_graph_refuses_apply_time_drift(tool_name):
    results, mcp = await _run(
        tool_name,
        assent_status="ratified",
        apply_drift=True,
    )

    assert results["commit#1"].status == "error"
    assert results["commit#1"].reason_code == CommitError.PLAN_STATE_DRIFT
    assert mcp.apply_count == 1
    assert [arguments["mode"] for _name, arguments in mcp.calls] == [
        "discover",
        "verify",
        "apply",
    ]
