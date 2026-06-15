"""Routing-real stage-node integration through the chain engine."""
from __future__ import annotations

import json
import time
import uuid
from types import SimpleNamespace

import pytest

from forge_bridge.console._engine import run_chain_steps
from forge_bridge.console.read_api import ConsoleReadAPI
from forge_bridge.mcp.tools import ListStagedInput, _list_staged_impl
from forge_bridge.store.staged_operations import StagedOpRepo

from tests.console.test_pr30_chain import _text_block


def _assessment(disposition: str) -> dict:
    return {
        "disposition": disposition,
        "verdict": "operator-should-not-see-this-as-parameter",
        "artifact": {
            "assessment_reason": f"assessment reason for {disposition}",
            "source_characterization_id": "src-char-1",
            "comp_characterization_id": "comp-char-1",
        },
    }


def _assess_tool():
    return SimpleNamespace(
        name="forge_assess_drift",
        annotations=SimpleNamespace(readOnlyHint=True),
        inputSchema={"type": "object", "properties": {}, "required": []},
    )


class AssessMCP:
    def __init__(self, disposition: str):
        self.disposition = disposition
        self.calls: list[tuple[str, dict]] = []

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return _text_block(json.dumps(_assessment(self.disposition)))


async def _staged_records(session_factory):
    async with session_factory() as session:
        repo = StagedOpRepo(session)
        records, _total = await repo.list()
        return records


async def _run_stage_chain(session_factory, *, disposition: str, review_kind: str):
    mcp = AssessMCP(disposition)
    predicate = (
        "if(disposition == drifted)"
        if review_kind == "ee_drift_review"
        else "if(disposition == abstained)"
    )
    result = await run_chain_steps(
        steps=[
            "forge_assess_drift",
            predicate,
            f"stage({review_kind})",
        ],
        tools=[_assess_tool()],
        mcp=mcp,
        request_id=f"req-{disposition}",
        client_ip="127.0.0.1",
        started=time.monotonic(),
        session_factory=session_factory,
    )
    return result, mcp


@pytest.mark.asyncio
async def test_stage_chain_gate_match_proposes_review_item(session_factory):
    result, mcp = await _run_stage_chain(
        session_factory,
        disposition="drifted",
        review_kind="ee_drift_review",
    )

    assert result["status"] == "success"
    assert mcp.calls == [("forge_assess_drift", {})]
    stage = result["chain"][2]
    assert stage["result"]["type"] == "staged_for_review"
    assert stage["result"]["disposition"] == "drifted"
    assert stage["result"]["review_kind"] == "ee_drift_review"
    assert list(stage["result"]) != [
        "type",
        "intent_parameters",
        "resolved_plan",
        "originating_capability",
        "apply_counterpart",
    ]

    records = await _staged_records(session_factory)
    assert len(records) == 1
    record = records[0]
    assert record.operation == "ee_review.drifted"
    assert record.proposer == "bridge.ee_routing"
    assert record.parameters["assessment_reason"] == "assessment reason for drifted"
    assert "verdict" not in record.parameters
    assert record.parameters["terminus"] == (
        "human_review_only — no downstream action fires on approval "
        "(action-real deferred)"
    )


@pytest.mark.asyncio
async def test_stage_chain_gate_miss_skips_stage_without_propose(session_factory):
    result, mcp = await _run_stage_chain(
        session_factory,
        disposition="clean",
        review_kind="ee_drift_review",
    )

    assert result["status"] == "success"
    assert mcp.calls == [("forge_assess_drift", {})]
    assert result["chain"][1]["result"]["if_gate"]["matched"] is False
    assert result["chain"][2]["result"]["execution_state"] == "skipped"
    assert await _staged_records(session_factory) == []


@pytest.mark.asyncio
async def test_stage_chain_abstained_branch_stages_needs_human_look(session_factory):
    result, _mcp = await _run_stage_chain(
        session_factory,
        disposition="abstained",
        review_kind="ee_needs_human_look",
    )

    assert result["status"] == "success"
    records = await _staged_records(session_factory)
    assert len(records) == 1
    assert records[0].operation == "ee_review.needs_human_look"
    assert records[0].proposer == "bridge.ee_routing"
    assert records[0].parameters["disposition"] == "abstained"


@pytest.mark.asyncio
async def test_stage_chain_commit_after_stage_fails_closed(session_factory):
    mcp = AssessMCP("drifted")

    result = await run_chain_steps(
        steps=[
            "forge_assess_drift",
            "if(disposition == drifted)",
            "stage(ee_drift_review)",
            "commit",
        ],
        tools=[_assess_tool()],
        mcp=mcp,
        request_id="req-commit-after-stage",
        client_ip="127.0.0.1",
        started=time.monotonic(),
        session_factory=session_factory,
    )

    assert result["status"] == "error"
    original = result["error"]["original_error"]
    assert original["type"] == "MUTATION_MANIFEST_INVALID"
    assert original["step"] == "commit"


@pytest.mark.asyncio
async def test_stage_review_item_lists_and_transitions(session_factory):
    await _run_stage_chain(
        session_factory,
        disposition="drifted",
        review_kind="ee_drift_review",
    )

    api = ConsoleReadAPI(
        execution_log=SimpleNamespace(snapshot=lambda: ([], 0)),
        manifest_service=SimpleNamespace(),
        session_factory=session_factory,
    )
    listed = json.loads(
        await _list_staged_impl(ListStagedInput(status="proposed"), api)
    )
    assert listed["data"][0]["parameters"]["assessment_reason"] == (
        "assessment reason for drifted"
    )

    op_id = uuid.UUID(listed["data"][0]["id"])
    async with session_factory() as session:
        repo = StagedOpRepo(session)
        approved = await repo.approve(op_id, approver="operator")
        rejected_seed = await repo.propose(
            operation="ee_review.needs_human_look",
            proposer="bridge.ee_routing",
            parameters={
                "assessment_reason": "needs look",
                "disposition": "abstained",
                "source_characterization_id": "src",
                "comp_characterization_id": "comp",
                "terminus": (
                    "human_review_only — no downstream action fires on "
                    "approval (action-real deferred)"
                ),
            },
        )
        rejected = await repo.reject(rejected_seed.id, actor="operator")
        await session.commit()

    assert approved.status == "approved"
    assert rejected.status == "rejected"
