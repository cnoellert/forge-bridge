from __future__ import annotations

import json

import pytest
from mcp.types import TextContent, Tool, ToolAnnotations

from forge_bridge.console._chat_compile import run_apply_branch
from forge_bridge.store.assent_record_repo import AssentRecordRepo


PROJECT_ID = "11111111-2222-3333-4444-555555555555"


def _mutating_tool() -> Tool:
    return Tool(
        name="flame_tf1_mutate",
        description="Mutating TF.1 integrity probe.",
        annotations=ToolAnnotations(readOnlyHint=False),
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "sequence_name": {"type": "string"},
            },
            "required": ["project_id", "sequence_name"],
        },
    )


class CaptureMCP:
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return [TextContent(type="text", text=json.dumps({"ok": True}))]


@pytest.mark.asyncio
async def test_tf1_ratified_replay_preserves_explicit_and_fills_semantic_params(
    session_factory,
):
    step_text = (
        f"flame_tf1_mutate project_id={PROJECT_ID} "
        "using sequence 30sec 21"
    )
    async with session_factory() as session:
        repo = AssentRecordRepo(session)
        proposed = await repo.propose([step_text])
        ratified = await repo.ratify(proposed.graph_intent_id, actor="operator")
        await session.commit()

    mcp = CaptureMCP()
    outcome = await run_apply_branch(
        graph_intent_id=ratified.graph_intent_id,
        session_factory=session_factory,
        tools=[_mutating_tool()],
        mcp=mcp,
        request_id="req-tf1",
        client_ip="127.0.0.1",
        started=10.0,
    )

    assert outcome.regime == "apply_complete"
    assert mcp.calls == [
        (
            "flame_tf1_mutate",
            {
                "project_id": PROJECT_ID,
                "sequence_name": "30sec_21",
            },
        )
    ]
    assert outcome.chain_body["status"] == "success"
    assert outcome.chain_body["chain"][0]["result"] == {"ok": True}
    assert outcome.assent_record["status"] == "applied"


@pytest.mark.asyncio
async def test_tf1_unratified_mutation_still_blocks(
):
    from forge_bridge.console._step import execute_chain_step

    mcp = CaptureMCP()
    result = await execute_chain_step(
        step_text=(
            f"flame_tf1_mutate project_id={PROJECT_ID} "
            "using sequence 30sec 21"
        ),
        tools=[_mutating_tool()],
        mcp=mcp,
        inherited_context={},
    )

    assert result["error"]["type"] == "unauthorized_mutation"
    assert mcp.calls == []


@pytest.mark.asyncio
async def test_tf1_explicit_param_wins_same_key_collision(
    session_factory,
):
    step_text = (
        f"flame_tf1_mutate project_id={PROJECT_ID} "
        "sequence_name=explicit_seq "
        "using sequence 30sec 21"
    )
    async with session_factory() as session:
        repo = AssentRecordRepo(session)
        proposed = await repo.propose([step_text])
        ratified = await repo.ratify(proposed.graph_intent_id, actor="operator")
        await session.commit()

    mcp = CaptureMCP()
    outcome = await run_apply_branch(
        graph_intent_id=ratified.graph_intent_id,
        session_factory=session_factory,
        tools=[_mutating_tool()],
        mcp=mcp,
        request_id="req-tf1-collision",
        client_ip="127.0.0.1",
        started=10.0,
    )

    assert outcome.regime == "apply_complete"
    assert mcp.calls[0][1]["sequence_name"] == "explicit_seq"
    assert mcp.calls[0][1]["project_id"] == PROJECT_ID
