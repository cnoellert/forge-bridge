from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from forge_bridge.console import _chat_compile
from forge_bridge.console._chat_compile import run_compile_branch
from forge_bridge.console._executor_route import apply_executor_routing
from forge_bridge.console.handlers import _apply_complete_body
from forge_bridge.store.assent_record_repo import AssentRecordRepo


def _tool(name: str, *, read_only: bool):
    return SimpleNamespace(
        name=name,
        description=f"{name} description",
        annotations=SimpleNamespace(readOnlyHint=read_only),
    )


def test_c2_rewrites_bare_rename_to_executor_commit():
    routed = apply_executor_routing(
        ["flame_rename_shots sequence_name=30sec_21 prefix=genesis"],
        [
            _tool("flame_rename_shots", read_only=False),
            _tool("forge_apply_rename", read_only=False),
        ],
    )

    assert routed == [
        "forge_apply_rename sequence_name=30sec_21 prefix=genesis",
        "commit",
    ]


def test_c2_read_step_is_unchanged():
    steps = ["forge_get_shot shot_id=tst_010"]

    assert apply_executor_routing(
        steps,
        [_tool("forge_get_shot", read_only=True)],
    ) is steps


def test_c2_missing_executor_registration_is_unchanged():
    steps = ["flame_rename_shots sequence_name=30sec_21 prefix=genesis"]

    assert apply_executor_routing(
        steps,
        [_tool("flame_rename_shots", read_only=False)],
    ) is steps


def test_c2_unmapped_mutating_tool_is_unchanged():
    steps = ["flame_set_start_frames sequence_name=30sec_21"]

    assert apply_executor_routing(
        steps,
        [_tool("flame_set_start_frames", read_only=False)],
    ) is steps


def test_c2_multi_mutation_chain_is_unchanged():
    steps = [
        "flame_rename_shots sequence_name=30sec_21 prefix=genesis",
        "flame_set_start_frames sequence_name=30sec_21",
    ]

    assert apply_executor_routing(
        steps,
        [
            _tool("flame_rename_shots", read_only=False),
            _tool("forge_apply_rename", read_only=False),
            _tool("flame_set_start_frames", read_only=False),
        ],
    ) is steps


def test_c2_misdeclared_executor_is_unchanged():
    steps = ["flame_rename_shots sequence_name=30sec_21 prefix=genesis"]

    assert apply_executor_routing(
        steps,
        [
            _tool("flame_rename_shots", read_only=False),
            _tool("forge_apply_rename", read_only=True),
        ],
    ) is steps


@pytest.mark.asyncio
async def test_c2_rename_compile_proposes_commit_bearing_executor_chain(
    session_factory,
    monkeypatch,
):
    router = SimpleNamespace(
        compile_intent=AsyncMock(
            return_value=[
                "flame_rename_shots sequence_name=30sec_21 prefix=genesis"
            ]
        )
    )
    monkeypatch.setattr(_chat_compile, "run_chain_steps", AsyncMock())

    outcome = await run_compile_branch(
        router=router,
        user_prompt="rename shots on 30sec 21 with prefix genesis",
        tools=[_tool("flame_rename_shots", read_only=False)],
        execution_tools=[
            _tool("flame_rename_shots", read_only=False),
            _tool("forge_apply_rename", read_only=False),
        ],
        mcp=SimpleNamespace(),
        request_id="req-c2",
        client_ip="127.0.0.1",
        started=10.0,
        session_factory=session_factory,
    )

    assert outcome.regime == "compiled_mutating_preview"
    assert outcome.steps == [
        "forge_apply_rename sequence_name=30sec_21 prefix=genesis",
        "commit",
    ]
    assert outcome.preview["summary"]["requires_ratification"] is True
    assert outcome.preview["steps"][1]["tool_name"] == "__commit__"
    assert outcome.graph_intent_id is not None
    _chat_compile.run_chain_steps.assert_not_awaited()

    async with session_factory() as session:
        repo = AssentRecordRepo(session)
        record = await repo.get_by_graph_intent_id(outcome.graph_intent_id)

    assert record is not None
    assert record.chain_steps == outcome.steps
    assert record.status == "proposed"


def test_c2_apply_complete_body_and_panel_surface_count():
    outcome = SimpleNamespace(
        graph_intent_id="abc123def456",
        chain_body={
            "status": "success",
            "chain": [
                {"step": "forge_apply_rename", "result": {"ok": True}},
                {
                    "step": "commit",
                    "result": {"type": "commit_applied", "count": 38},
                },
            ],
        },
    )

    body = _apply_complete_body(outcome, "json")

    assert body["count"] == 38
    template = Path(
        "forge_bridge/console/templates/chat/panel.html"
    ).read_text()
    assert "Renamed ${ratifyOutcome.apply_complete.count} shots." in template
