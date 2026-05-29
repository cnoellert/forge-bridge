from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from forge_bridge.console._step import execute_chain_step
from forge_bridge.core.assent import AssentRecord
from forge_bridge.graph.ports import PortTopology
from tests.console.test_pr30_chain import _text_block


def _record(name: str, value: str) -> dict:
    return {
        "identity": {"name": name},
        "payload": {"value": value},
    }


def _manifest(records: list[dict] | None = None) -> dict:
    return {
        "type": "mutation_plan",
        "intent_parameters": {"request": "demo"},
        "resolved_plan": records or [_record("a", "one")],
        "originating_capability": "apply_plan",
        "apply_counterpart": {
            "tool": "apply_plan",
            "parameter_overrides": {"dry_run": False},
        },
    }


class VerifyMCP:
    def __init__(self, verify_result: dict, apply_result: dict | None = None):
        self.results = [verify_result, apply_result or {"applied": 1}]
        self.calls: list[tuple[str, dict]] = []

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        index = min(len(self.calls) - 1, len(self.results) - 1)
        return _text_block(json.dumps(self.results[index]))


def _tool():
    return SimpleNamespace(name="apply_plan")


def _context(manifest: dict) -> dict:
    return {
        "__previous_result__": manifest,
        "__previous_topology__": PortTopology.manifest().to_dict(),
    }


@pytest.mark.asyncio
async def test_commit_step_with_ratified_assent_applies():
    manifest = _manifest()
    mcp = VerifyMCP(manifest)
    assent = AssentRecord(
        graph_intent_id="abc123def456",
        chain_steps=["apply_plan", "commit"],
        status="ratified",
    )

    result = await execute_chain_step(
        step_text="commit",
        tools=[_tool()],
        mcp=mcp,
        inherited_context=_context(manifest),
        step_index=1,
        assent_record=assent,
    )

    assert "error" not in result
    assert result["result"]["type"] == "commit_applied"
    assert len(mcp.calls) == 2


@pytest.mark.asyncio
async def test_commit_step_with_proposed_assent_aborts_before_apply():
    manifest = _manifest()
    mcp = VerifyMCP(manifest)
    assent = AssentRecord(
        graph_intent_id="abc123def456",
        chain_steps=["apply_plan", "commit"],
        status="proposed",
    )

    result = await execute_chain_step(
        step_text="commit",
        tools=[_tool()],
        mcp=mcp,
        inherited_context=_context(manifest),
        step_index=1,
        assent_record=assent,
    )

    assert result["error"] == {
        "type": "ASSENT_INVALID",
        "message": "AssentRecord is not in ratified state.",
        "step_index": 1,
        "step": "commit",
        "graph_intent_id": "abc123def456",
    }
    assert len(mcp.calls) == 1
