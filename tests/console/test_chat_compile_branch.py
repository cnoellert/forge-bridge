"""A.1 D3 compile-branch helper tests."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from forge_bridge.console import _chat_compile
from forge_bridge.console._chat_compile import (
    build_compile_system_prompt,
    build_preview_from_steps,
    run_compile_branch,
)
from forge_bridge.llm.router import CompileUnresolvableIntent


def _tool(name: str, description: str):
    return SimpleNamespace(name=name, description=description)


def test_build_compile_system_prompt_empty_tool_set_names_chain_syntax():
    prompt = build_compile_system_prompt([])

    assert "empty tool set" in prompt
    assert "->" in prompt
    assert "chain syntax" in prompt


def test_build_compile_system_prompt_renders_tool_catalogue():
    prompt = build_compile_system_prompt([
        _tool("forge_list_shots", "List shots."),
        _tool("format_result", "Format a tool result."),
    ])

    assert "forge_list_shots" in prompt
    assert "List shots." in prompt
    assert "format_result" in prompt
    assert "Format a tool result." in prompt
    assert "commit" in prompt
    assert "authority transition" in prompt


def test_build_preview_from_steps_non_mutating_shape():
    preview = build_preview_from_steps(["list shots"])

    assert preview == {
        "kind": "graph-intent-preview",
        "steps": [{
            "step_text": "list shots",
            "tool_name": "list",
            "args_preview": {},
            "would_mutate": False,
        }],
        "summary": {
            "total_steps": 1,
            "mutating_steps": 0,
            "requires_ratification": False,
        },
    }


def test_build_preview_from_steps_commit_requires_ratification():
    preview = build_preview_from_steps([
        "flame_rename_shots dry_run=False",
        "commit",
    ])

    assert preview["summary"]["requires_ratification"] is True
    assert preview["summary"]["mutating_steps"] == 1
    assert preview["steps"][1]["tool_name"] == "__commit__"
    assert preview["steps"][1]["would_mutate"] is True


@pytest.mark.asyncio
async def test_run_compile_branch_non_mutating_executes_chain(monkeypatch):
    router = SimpleNamespace(
        compile_intent=AsyncMock(return_value=["list shots"])
    )
    chain_body = {
        "status": "success",
        "request_id": "req-1",
        "chain": [{"step": "list shots", "result": {"shots": []}}],
        "error": None,
    }
    run_chain = AsyncMock(return_value=chain_body)
    monkeypatch.setattr(_chat_compile, "run_chain_steps", run_chain)

    outcome = await run_compile_branch(
        router=router,
        user_prompt="list shots",
        tools=[_tool("list", "List things.")],
        mcp=SimpleNamespace(),
        request_id="req-1",
        client_ip="127.0.0.1",
        started=10.0,
    )

    assert outcome.regime == "compiled_non_mutating"
    assert outcome.steps == ["list shots"]
    assert outcome.chain_body == chain_body
    assert outcome.preview is None
    assert outcome.compile_error is None
    run_chain.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_compile_branch_mutating_commit_returns_preview(monkeypatch):
    router = SimpleNamespace(
        compile_intent=AsyncMock(
            return_value=["flame_rename_shots dry_run=False", "commit"]
        )
    )
    run_chain = AsyncMock()
    monkeypatch.setattr(_chat_compile, "run_chain_steps", run_chain)

    outcome = await run_compile_branch(
        router=router,
        user_prompt="rename shots",
        tools=[_tool("flame_rename_shots", "Rename shots.")],
        mcp=SimpleNamespace(),
        request_id="req-2",
        client_ip="127.0.0.1",
        started=10.0,
    )

    assert outcome.regime == "compiled_mutating_preview"
    assert outcome.chain_body is None
    assert outcome.preview is not None
    assert outcome.preview["summary"]["requires_ratification"] is True
    run_chain.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_compile_branch_compile_error_returns_outcome():
    error = CompileUnresolvableIntent("")
    router = SimpleNamespace(compile_intent=AsyncMock(side_effect=error))

    outcome = await run_compile_branch(
        router=router,
        user_prompt="???",
        tools=[_tool("list", "List things.")],
        mcp=SimpleNamespace(),
        request_id="req-3",
        client_ip="127.0.0.1",
        started=10.0,
    )

    assert outcome.regime == "compile_error"
    assert outcome.steps == []
    assert outcome.preview is None
    assert outcome.chain_body is None
    assert outcome.compile_error is error
