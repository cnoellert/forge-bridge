"""A.1 D3 compile-branch helper tests."""
from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import inspect
import pytest
from starlette.testclient import TestClient

from forge_bridge.console import _rate_limit
from forge_bridge.console import _chat_compile
from forge_bridge.console.app import build_console_app
from forge_bridge.console._chat_compile import (
    build_compile_system_prompt,
    build_preview_from_steps,
    run_compile_branch,
)
from forge_bridge.console.handlers import chat_handler
from forge_bridge.console.manifest_service import ManifestService
from forge_bridge.console.read_api import ConsoleReadAPI
from forge_bridge.llm.router import (
    CompileBudgetExceeded,
    CompileInvalidChainShape,
    CompileSeamViolation,
    CompileToolUnknown,
    CompileUnresolvableIntent,
)


def _tool(name: str, description: str):
    return SimpleNamespace(name=name, description=description)


def _authority_tool(name: str, *, read_only: bool):
    return SimpleNamespace(
        name=name,
        description=f"{name} description",
        annotations=SimpleNamespace(readOnlyHint=read_only),
    )


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    _rate_limit._reset_for_tests()
    yield
    _rate_limit._reset_for_tests()


def _mcp_tool(name: str, description: str):
    from mcp.types import Tool
    return Tool(
        name=name,
        description=description,
        inputSchema={"type": "object", "properties": {}, "required": []},
    )


def _chat_client(router, tools):
    ms = ManifestService()
    mock_log = MagicMock()
    mock_log.snapshot.return_value = ([], 0)
    api = ConsoleReadAPI(
        execution_log=mock_log,
        manifest_service=ms,
        llm_router=router,
    )
    app = build_console_app(api)
    patches = (
        patch(
            "forge_bridge.mcp.server.mcp.list_tools",
            new=AsyncMock(return_value=tools),
        ),
        patch(
            "forge_bridge.console.handlers.filter_tools_by_reachable_backends",
            new=AsyncMock(return_value=tools),
        ),
    )
    return TestClient(app), patches


def _post_chat(client, text: str):
    return client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "user", "content": text}]},
    )


def _post_sse(client, text: str):
    return client.post(
        "/api/v1/chat",
        json={"messages": [{"role": "user", "content": text}]},
        headers={"Accept": "text/event-stream"},
    )


def _parse_sse_stream(text: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    current_event: str | None = None
    current_data: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip("\r")
        if line.startswith("event:"):
            current_event = line[len("event:"):].strip()
        elif line.startswith("data:"):
            current_data = line[len("data:"):].strip()
        elif line == "" and current_event is not None and current_data is not None:
            events.append((current_event, json.loads(current_data)))
            current_event = None
            current_data = None
    if current_event is not None and current_data is not None:
        events.append((current_event, json.loads(current_data)))
    return events


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
    assert "tool_name arg=value" in prompt
    assert "an args object is never its own step" in prompt


def test_build_compile_system_prompt_omits_pr15_enforcement_language():
    """L7 contract: compile system prompt omits PR15 enforcement vocabulary.

    The chat handler deletes its enforced_system construction (S-1) on the
    grounds that compile_intent runs PR15-free. Asserts that property
    structurally on the prompt builder's output, grounded against
    _tool_enforcement.py's actual emitted strings (not conjectured PR15
    vocabulary). Per [[feedback-ground-specs-in-actual-files]] applied to
    negative-assertion layer (Creative refinement 2026-05-28).
    """
    from forge_bridge.console._tool_enforcement import (
        PR15_HARD_TOOL_INSTRUCTION,
    )

    prompt = build_compile_system_prompt([
        _tool("forge_list_shots", "List shots."),
        _tool("flame_rename_shots", "Rename shots."),
    ])

    # Distinctive PR15_ENFORCEMENT_PROMPT fragments — semantically unique
    # to PR15 enforcement language; cannot appear naturally in compile-stage
    # prose. Selected per Creative's Stage 1b ruling 2026-05-28: ground in
    # PR15 source semantics, not formatting mechanics.
    for forbidden in [
        "tool-using agent",
        "answer from memory",
        "looks like a tool call",
        "structured format when using tools",
        "If you fail to call a tool",
    ]:
        assert forbidden not in prompt, f"PR15 fragment leaked: {forbidden!r}"

    # Whole-constant assertion — PR15_HARD_TOOL_INSTRUCTION is a single-string
    # imperative; no formatting fragility, exact-match safe.
    assert (
        PR15_HARD_TOOL_INSTRUCTION not in prompt
    ), "PR15 HARD_TOOL instruction leaked"


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


def test_build_preview_from_steps_threads_graph_intent_id():
    preview = build_preview_from_steps(
        ["flame_rename_shots dry_run=False", "commit"],
        graph_intent_id="abc123def456",
    )

    assert list(preview) == ["kind", "graph_intent_id", "steps", "summary"]
    assert preview["graph_intent_id"] == "abc123def456"


def test_build_preview_from_steps_uses_execution_argument_parser():
    preview = build_preview_from_steps([
        'forge_generate_still grant_id=abc123def456 inputs="prompt text"',
        "commit",
    ])

    assert preview["steps"][0]["args_preview"] == {
        "grant_id": "abc123def456",
        "inputs": "prompt text",
    }


def test_build_preview_from_steps_surfaces_trusted_generation_cost():
    preview = build_preview_from_steps(
        ["forge_generate_still grant_id=abc123def456", "commit"],
        generation_cost_preview={
            "source": "generation_grant",
            "estimated_cost": {"amount": 1.5, "currency": "USD"},
        },
    )

    assert preview["summary"]["estimated_cost"] == {
        "amount": 1.5,
        "currency": "USD",
    }


@pytest.mark.asyncio
async def test_generation_preview_resolves_and_persists_grant_cost(session_factory):
    from forge_bridge.store.assent_record_repo import AssentRecordRepo
    from forge_bridge.store.generation_grant_repo import GenerationGrantRepo

    async with session_factory() as session:
        grant_repo = GenerationGrantRepo(session)
        proposed = await grant_repo.propose(
            operator_id="generate_still",
            backend_identity_triple={
                "provider": "fal",
                "model": "flux-pro",
                "revision": "2026-07-17",
            },
            estimated_cost={"amount": 1.5, "currency": "USD", "tier": "hero"},
            run_kind="direct_tool",
        )
        grant = await grant_repo.ratify(proposed.grant_id, actor="operator")
        await session.commit()

    steps = [
        (
            f"forge_generate_still grant_id={grant.grant_id} inputs=prompt "
            "estimated_cost=0"
        ),
        "commit",
    ]
    router = SimpleNamespace(compile_intent=AsyncMock(return_value=steps))
    outcome = await run_compile_branch(
        router=router,
        user_prompt="generate a still",
        tools=[_authority_tool("forge_generate_still", read_only=False)],
        mcp=SimpleNamespace(),
        request_id="req-generation-cost",
        client_ip="127.0.0.1",
        started=10.0,
        session_factory=session_factory,
    )

    assert outcome.regime == "compiled_mutating_preview"
    assert outcome.preview["summary"]["estimated_cost"] == {
        "amount": 1.5,
        "currency": "USD",
    }
    assert outcome.preview["steps"][0]["args_preview"]["grant_id"] == grant.grant_id

    async with session_factory() as session:
        assent = await AssentRecordRepo(session).get_by_graph_intent_id(
            outcome.graph_intent_id
        )
        unchanged_grant = await GenerationGrantRepo(session).get_by_grant_id(
            grant.grant_id
        )

    evidence = assent.metadata[_chat_compile.GENERATION_COST_PREVIEW_METADATA_KEY]
    assert evidence["source"] == "generation_grant"
    assert evidence["estimated_cost"] == {"amount": 1.5, "currency": "USD"}
    assert evidence["line_items"] == [{
        "step_index": 0,
        "tool_name": "forge_generate_still",
        "grant_id": grant.grant_id,
        "estimated_cost": {"amount": 1.5, "currency": "USD"},
    }]
    assert unchanged_grant.status == "ratified"


@pytest.mark.asyncio
async def test_generation_preview_keeps_mixed_currency_totals_separate(
    session_factory,
):
    from forge_bridge.store.generation_grant_repo import GenerationGrantRepo

    grant_ids: list[str] = []
    async with session_factory() as session:
        repo = GenerationGrantRepo(session)
        for amount, currency in ((2, "USD"), (100, "credits")):
            grant = await repo.propose(
                operator_id="generate_still",
                backend_identity_triple={
                    "provider": "test",
                    "model": currency,
                    "revision": "1",
                },
                estimated_cost={"amount": amount, "currency": currency},
                run_kind="direct_tool",
            )
            grant_ids.append(grant.grant_id)
        await session.commit()

    steps = [
        f"forge_generate_still grant_id={grant_ids[0]}",
        f"forge_generate_still grant_id={grant_ids[1]}",
        "commit",
    ]
    router = SimpleNamespace(compile_intent=AsyncMock(return_value=steps))
    outcome = await run_compile_branch(
        router=router,
        user_prompt="generate both",
        tools=[_authority_tool("forge_generate_still", read_only=False)],
        mcp=SimpleNamespace(),
        request_id="req-generation-mixed-cost",
        client_ip="127.0.0.1",
        started=10.0,
        session_factory=session_factory,
    )

    assert "estimated_cost" not in outcome.preview["summary"]
    assert outcome.preview["summary"]["estimated_costs"] == [
        {"amount": 2, "currency": "USD"},
        {"amount": 100, "currency": "credits"},
    ]


@pytest.mark.asyncio
async def test_run_compile_branch_non_mutating_executes_chain(monkeypatch):
    router = SimpleNamespace(
        compile_intent=AsyncMock(return_value=["forge_list_shots"])
    )
    chain_body = {
        "status": "success",
        "request_id": "req-1",
        "chain": [{"step": "forge_list_shots", "result": {"shots": []}}],
        "error": None,
    }
    run_chain = AsyncMock(return_value=chain_body)
    monkeypatch.setattr(_chat_compile, "run_chain_steps_with_shadow", run_chain)

    outcome = await run_compile_branch(
        router=router,
        user_prompt="list shots",
        tools=[_tool("forge_list_shots", "List shots.")],
        mcp=SimpleNamespace(),
        request_id="req-1",
        client_ip="127.0.0.1",
        started=10.0,
    )

    assert outcome.regime == "compiled_non_mutating"
    assert outcome.steps == ["forge_list_shots"]
    assert outcome.chain_body == chain_body
    assert outcome.preview is None
    assert outcome.compile_error is None
    assert outcome.salvage_applied is False
    assert outcome.salvage_reason is None
    run_chain.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_compile_branch_source_routing_uses_execution_tools(monkeypatch):
    compile_tools = [_tool("forge_get_shot", "Get shot details.")]
    execution_tools = [
        *compile_tools,
        _tool("flame_get_sequence_segments", "List Flame sequence segments."),
    ]
    router = SimpleNamespace(
        compile_intent=AsyncMock(return_value=["forge_get_shot"])
    )
    chain_body = {
        "status": "success",
        "request_id": "req-sr1",
        "chain": [{
            "step": "flame_get_sequence_segments 30sec_edit 21",
            "result": {"segments": []},
        }],
        "error": None,
    }
    run_chain = AsyncMock(return_value=chain_body)
    monkeypatch.setattr(_chat_compile, "run_chain_steps_with_shadow", run_chain)

    outcome = await run_compile_branch(
        router=router,
        user_prompt="what is the path to shot 10 on 30sec_edit 21",
        tools=compile_tools,
        execution_tools=execution_tools,
        mcp=SimpleNamespace(),
        request_id="req-sr1",
        client_ip="127.0.0.1",
        started=10.0,
    )

    assert outcome.regime == "compiled_non_mutating"
    assert outcome.steps == ["flame_get_sequence_segments 30sec_edit 21"]
    assert outcome.chain_body == chain_body
    router.compile_intent.assert_awaited_once()
    assert router.compile_intent.await_args.args[1] == compile_tools
    run_chain.assert_awaited_once()
    assert run_chain.await_args.kwargs["steps"] == [
        "flame_get_sequence_segments 30sec_edit 21"
    ]
    assert run_chain.await_args.kwargs["tools"] == execution_tools


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
    assert outcome.graph_intent_id is None
    assert outcome.assent_record_id is None
    run_chain.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_compile_branch_strips_commit_for_exact_read_tool(monkeypatch):
    router = SimpleNamespace(
        compile_intent=AsyncMock(return_value=["forge_list_shots", "commit"])
    )
    chain_body = {
        "status": "success",
        "request_id": "req-read",
        "chain": [{"step": "forge_list_shots", "result": {"shots": []}}],
        "error": None,
    }
    run_chain = AsyncMock(return_value=chain_body)
    monkeypatch.setattr(_chat_compile, "run_chain_steps_with_shadow", run_chain)

    outcome = await run_compile_branch(
        router=router,
        user_prompt="list shots",
        tools=[_authority_tool("forge_list_shots", read_only=True)],
        mcp=SimpleNamespace(),
        request_id="req-read",
        client_ip="127.0.0.1",
        started=10.0,
    )

    assert outcome.regime == "compiled_non_mutating"
    assert outcome.steps == ["forge_list_shots"]
    assert outcome.preview is None
    run_chain.assert_awaited_once()
    assert run_chain.await_args.kwargs["steps"] == ["forge_list_shots"]


@pytest.mark.asyncio
async def test_run_compile_branch_keeps_commit_for_exact_mutating_tool(monkeypatch):
    router = SimpleNamespace(
        compile_intent=AsyncMock(return_value=["flame_rename_shots", "commit"])
    )
    run_chain = AsyncMock()
    monkeypatch.setattr(_chat_compile, "run_chain_steps", run_chain)

    outcome = await run_compile_branch(
        router=router,
        user_prompt="rename shots",
        tools=[_authority_tool("flame_rename_shots", read_only=False)],
        mcp=SimpleNamespace(),
        request_id="req-mutate",
        client_ip="127.0.0.1",
        started=10.0,
    )

    assert outcome.regime == "compiled_mutating_preview"
    assert outcome.steps == ["flame_rename_shots", "commit"]
    assert outcome.preview["summary"]["requires_ratification"] is True
    run_chain.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_compile_branch_returns_compile_error_for_non_tool_step(
    monkeypatch,
):
    router = SimpleNamespace(
        compile_intent=AsyncMock(return_value=["list shots", "commit"])
    )
    run_chain = AsyncMock()
    monkeypatch.setattr(_chat_compile, "run_chain_steps", run_chain)

    outcome = await run_compile_branch(
        router=router,
        user_prompt="list shots",
        tools=[_authority_tool("forge_list_shots", read_only=True)],
        mcp=SimpleNamespace(),
        request_id="req-inexact",
        client_ip="127.0.0.1",
        started=10.0,
    )

    assert outcome.regime == "compile_error"
    assert isinstance(outcome.compile_error, CompileInvalidChainShape)
    assert outcome.steps == ["list shots", "commit"]
    run_chain.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_compile_branch_compile_error_preserves_detached_args_residual():
    router = SimpleNamespace(
        compile_intent=AsyncMock(return_value=[
            "flame_rename_shots prefix=tv",
            '{"params": {"sequence_name": "30sec_21"}}',
        ])
    )

    outcome = await run_compile_branch(
        router=router,
        user_prompt="rename shots",
        tools=[_tool("flame_rename_shots", "Rename shots.")],
        mcp=SimpleNamespace(),
        request_id="req-detached-residual",
        client_ip="127.0.0.1",
        started=10.0,
    )

    assert outcome.regime == "compile_error"
    assert isinstance(outcome.compile_error, CompileInvalidChainShape)
    assert outcome.steps == [
        "flame_rename_shots prefix=tv",
        '{"params": {"sequence_name": "30sec_21"}}',
    ]
    assert "detached args step" in outcome.compile_error.parse_error


@pytest.mark.asyncio
async def test_run_compile_branch_records_salvage_on_repaired_compile(monkeypatch):
    router = SimpleNamespace(
        compile_intent=AsyncMock(return_value=[
            "flame_rename_shots",
            '{"params": {"sequence_name": "30sec_21", "prefix": "tv"}}',
            "commit",
        ])
    )
    run_chain = AsyncMock()
    monkeypatch.setattr(_chat_compile, "run_chain_steps", run_chain)

    outcome = await run_compile_branch(
        router=router,
        user_prompt="rename shots",
        tools=[_authority_tool("flame_rename_shots", read_only=False)],
        mcp=SimpleNamespace(),
        request_id="req-salvage",
        client_ip="127.0.0.1",
        started=10.0,
    )

    assert outcome.regime == "compiled_mutating_preview"
    assert outcome.steps == [
        'flame_rename_shots {"params": {"sequence_name": "30sec_21", "prefix": "tv"}}',
        "commit",
    ]
    assert outcome.salvage_applied is True
    assert outcome.salvage_reason == "detached_args"
    run_chain.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_compile_branch_salvages_trailing_empty_segment(monkeypatch):
    router = SimpleNamespace(
        compile_intent=AsyncMock(return_value=["forge_list_projects", ""])
    )
    chain_body = {
        "status": "success",
        "request_id": "req-trailing",
        "chain": [{"step": "forge_list_projects", "result": {"projects": []}}],
        "error": None,
    }
    run_chain = AsyncMock(return_value=chain_body)
    monkeypatch.setattr(_chat_compile, "run_chain_steps_with_shadow", run_chain)

    outcome = await run_compile_branch(
        router=router,
        user_prompt="list projects",
        tools=[_tool("forge_list_projects", "List projects.")],
        mcp=SimpleNamespace(),
        request_id="req-trailing",
        client_ip="127.0.0.1",
        started=10.0,
    )

    assert outcome.regime == "compiled_non_mutating"
    assert outcome.steps == ["forge_list_projects"]
    assert outcome.salvage_applied is True
    assert outcome.salvage_reason == "trailing_empty_segment"
    run_chain.assert_awaited_once()
    assert run_chain.await_args.kwargs["steps"] == ["forge_list_projects"]


@pytest.mark.asyncio
async def test_run_compile_branch_rejects_mid_chain_empty_segment(monkeypatch):
    router = SimpleNamespace(
        compile_intent=AsyncMock(return_value=["a_tool", "", "b_tool"])
    )
    run_chain = AsyncMock()
    monkeypatch.setattr(_chat_compile, "run_chain_steps", run_chain)

    outcome = await run_compile_branch(
        router=router,
        user_prompt="bad chain",
        tools=[_tool("a_tool", "A tool."), _tool("b_tool", "B tool.")],
        mcp=SimpleNamespace(),
        request_id="req-mid-empty",
        client_ip="127.0.0.1",
        started=10.0,
    )

    assert outcome.regime == "compile_error"
    assert isinstance(outcome.compile_error, CompileInvalidChainShape)
    assert "empty step at index 1" in outcome.compile_error.parse_error
    assert outcome.steps == ["a_tool", "", "b_tool"]
    run_chain.assert_not_awaited()


def test_chat_compile_read_strip_does_not_use_fuzzy_narrowing_helpers():
    source = inspect.getsource(_chat_compile)

    assert "filter_tools_by_message" not in source
    assert "deterministic_narrow" not in source


@pytest.mark.asyncio
async def test_run_compile_branch_mutating_commit_creates_assent_record(
    session_factory,
    monkeypatch,
):
    from forge_bridge.store.assent_record_repo import AssentRecordRepo

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
        session_factory=session_factory,
    )

    assert outcome.regime == "compiled_mutating_preview"
    assert outcome.graph_intent_id is not None
    assert len(outcome.graph_intent_id) == 12
    assert outcome.assent_record_id is not None
    assert outcome.preview["graph_intent_id"] == outcome.graph_intent_id
    run_chain.assert_not_awaited()

    async with session_factory() as session:
        repo = AssentRecordRepo(session)
        record = await repo.get_by_graph_intent_id(outcome.graph_intent_id)

    assert record is not None
    assert record.id == outcome.assent_record_id
    assert record.status == "proposed"


@pytest.mark.asyncio
async def test_run_compile_branch_mutating_commit_is_idempotent_by_content(
    session_factory,
    monkeypatch,
):
    router = SimpleNamespace(
        compile_intent=AsyncMock(
            return_value=["flame_rename_shots dry_run=False", "commit"]
        )
    )
    monkeypatch.setattr(_chat_compile, "run_chain_steps", AsyncMock())

    first = await run_compile_branch(
        router=router,
        user_prompt="rename shots",
        tools=[_tool("flame_rename_shots", "Rename shots.")],
        mcp=SimpleNamespace(),
        request_id="req-1",
        client_ip="127.0.0.1",
        started=10.0,
        session_factory=session_factory,
    )
    second = await run_compile_branch(
        router=router,
        user_prompt="rename shots",
        tools=[_tool("flame_rename_shots", "Rename shots.")],
        mcp=SimpleNamespace(),
        request_id="req-2",
        client_ip="127.0.0.1",
        started=10.0,
        session_factory=session_factory,
    )

    assert second.graph_intent_id == first.graph_intent_id
    assert second.assent_record_id == first.assent_record_id


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
    assert outcome.compile_raw == error.raw_response


@pytest.mark.asyncio
async def test_run_compile_branch_compile_intent_raise_keeps_empty_steps():
    error = CompileToolUnknown("missing_tool", 0, "missing_tool")
    router = SimpleNamespace(compile_intent=AsyncMock(side_effect=error))

    outcome = await run_compile_branch(
        router=router,
        user_prompt="missing",
        tools=[_tool("forge_list_shots", "List shots.")],
        mcp=SimpleNamespace(),
        request_id="req-tool-unknown",
        client_ip="127.0.0.1",
        started=10.0,
    )

    assert outcome.regime == "compile_error"
    assert outcome.steps == []
    assert outcome.compile_error is error
    assert outcome.compile_raw is None


@pytest.mark.asyncio
async def test_run_compile_branch_invalid_chain_shape_threads_compile_raw():
    error = CompileInvalidChainShape(
        '{"steps": [{"params": {"project": "all"}}]}',
        "step 0 has no tool_name or step_text",
    )
    router = SimpleNamespace(compile_intent=AsyncMock(side_effect=error))

    outcome = await run_compile_branch(
        router=router,
        user_prompt="list projects",
        tools=[_tool("forge_list_projects", "List projects.")],
        mcp=SimpleNamespace(),
        request_id="req-raw",
        client_ip="127.0.0.1",
        started=10.0,
    )

    assert outcome.regime == "compile_error"
    assert outcome.steps == []
    assert outcome.compile_error is error
    assert outcome.compile_raw == error.raw_response


def test_chat_handler_json_regime_2_full_path(monkeypatch):
    router = SimpleNamespace(
        compile_intent=AsyncMock(return_value=["forge_list_shots"]),
        acomplete=AsyncMock(return_value="No shots were returned."),
        local_model="qwen-test",
    )
    tools = [_mcp_tool("forge_list_shots", "List shots.")]
    chain_body = {
        "status": "success",
        "request_id": "req-from-engine",
        "chain": [{"step": "forge_list_shots", "result": {"shots": []}}],
        "error": None,
    }
    monkeypatch.setattr(
        _chat_compile,
        "run_chain_steps_with_shadow",
        AsyncMock(return_value=chain_body),
    )
    emit_capture = MagicMock()
    monkeypatch.setattr(
        "forge_bridge.console.handlers.emit_comprehension_capture",
        emit_capture,
    )
    client, patches = _chat_client(router, tools)

    with patches[0], patches[1]:
        response = _post_chat(client, "list shots")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["stop_reason"] == "chain_complete"
    assert body["chain"] == chain_body["chain"]
    assert body["preview"] is None
    assert body["messages"] == [{
        "role": "assistant",
        "content": "No shots were returned.",
    }]
    emit_capture.assert_called_once_with(
        question="list shots",
        chain=chain_body["chain"],
        answer="No shots were returned.",
        wall_clock_ms=emit_capture.call_args.kwargs["wall_clock_ms"],
        model="qwen-test",
    )


def test_chat_handler_json_answer_failure_still_delivers_read(monkeypatch):
    router = SimpleNamespace(
        compile_intent=AsyncMock(return_value=["forge_list_shots"]),
        acomplete=AsyncMock(side_effect=RuntimeError("ollama down")),
    )
    chain_body = {
        "status": "success",
        "request_id": "req",
        "chain": [{"step": "forge_list_shots", "result": {"shots": []}}],
        "error": None,
    }
    monkeypatch.setattr(
        _chat_compile,
        "run_chain_steps_with_shadow",
        AsyncMock(return_value=chain_body),
    )
    client, patches = _chat_client(
        router, [_mcp_tool("forge_list_shots", "List shots.")]
    )

    with patches[0], patches[1]:
        response = _post_chat(client, "list shots")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["chain"] == chain_body["chain"]
    assert body["messages"] == []
    assert body["stop_reason"] == "chain_complete"


def test_chat_handler_json_answer_timeout_still_delivers_read(monkeypatch):
    from forge_bridge.console import _answer

    async def _sleep_past_bound(*_args, **_kwargs):
        await asyncio.sleep(60)

    monkeypatch.setattr(_answer, "_SYNTHESIS_TIMEOUT_S", 0.01)
    router = SimpleNamespace(
        compile_intent=AsyncMock(return_value=["forge_list_shots"]),
        acomplete=_sleep_past_bound,
    )
    chain_body = {
        "status": "success",
        "request_id": "req",
        "chain": [{"step": "forge_list_shots", "result": {"shots": []}}],
        "error": None,
    }
    monkeypatch.setattr(
        _chat_compile,
        "run_chain_steps_with_shadow",
        AsyncMock(return_value=chain_body),
    )
    client, patches = _chat_client(
        router, [_mcp_tool("forge_list_shots", "List shots.")]
    )

    with patches[0], patches[1]:
        response = _post_chat(client, "list shots")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["chain"] == chain_body["chain"]
    assert body["messages"] == []
    assert body["stop_reason"] == "chain_complete"


def test_chat_handler_json_chain_aborted_preserves_error_and_skips_answer(
    monkeypatch,
):
    router = SimpleNamespace(
        compile_intent=AsyncMock(return_value=["forge_list_shots"]),
        acomplete=AsyncMock(return_value="should not run"),
    )
    chain_body = {
        "status": "error",
        "request_id": "req",
        "chain": [],
        "error": {
            "code": "CHAIN_STEP_FAILED",
            "message": "step failed",
            "step_index": 0,
            "original_error": {"type": "RuntimeError", "message": "boom"},
        },
    }
    monkeypatch.setattr(
        _chat_compile,
        "run_chain_steps_with_shadow",
        AsyncMock(return_value=chain_body),
    )
    emit_capture = MagicMock()
    monkeypatch.setattr(
        "forge_bridge.console.handlers.emit_comprehension_capture",
        emit_capture,
    )
    client, patches = _chat_client(
        router, [_mcp_tool("forge_list_shots", "List shots.")]
    )

    with patches[0], patches[1]:
        response = _post_chat(client, "list shots")

    assert response.status_code == 400, response.text
    body = response.json()
    assert body["stop_reason"] == "chain_aborted"
    assert body["error"] == chain_body["error"]
    router.acomplete.assert_not_awaited()
    emit_capture.assert_called_once_with(
        question="list shots",
        chain=[],
        answer="",
        wall_clock_ms=0,
        model="unknown",
        outcome="chain_aborted",
    )


def test_chat_handler_json_regime_2_omits_final_text(monkeypatch):
    router = SimpleNamespace(
        compile_intent=AsyncMock(return_value=["forge_list_shots"])
    )
    monkeypatch.setattr(
        _chat_compile,
        "run_chain_steps",
        AsyncMock(return_value={
            "status": "success",
            "request_id": "req",
            "chain": [],
            "error": None,
        }),
    )
    client, patches = _chat_client(
        router, [_mcp_tool("forge_list_shots", "List shots.")]
    )

    with patches[0], patches[1]:
        response = _post_chat(client, "list shots")

    assert "final_text" not in response.json()


def test_chat_handler_json_regime_2_emits_tool_enforced_false(monkeypatch):
    router = SimpleNamespace(
        compile_intent=AsyncMock(return_value=["forge_list_shots"])
    )
    monkeypatch.setattr(
        _chat_compile,
        "run_chain_steps_with_shadow",
        AsyncMock(return_value={
            "status": "success",
            "request_id": "req",
            "chain": [],
            "error": None,
        }),
    )
    client, patches = _chat_client(
        router, [_mcp_tool("forge_list_shots", "List shots.")]
    )

    with patches[0], patches[1]:
        response = _post_chat(client, "list shots")

    body = response.json()
    assert body["tool_enforced"] is False
    assert body["tool_forced"] is False


def test_chat_handler_json_regime_3_full_path(monkeypatch):
    router = SimpleNamespace(
        compile_intent=AsyncMock(return_value=[
            "flame_rename_shots dry_run=False",
            "commit",
        ])
    )
    run_chain = AsyncMock()
    monkeypatch.setattr(_chat_compile, "run_chain_steps", run_chain)
    emit_capture = MagicMock()
    monkeypatch.setattr(
        "forge_bridge.console.handlers.emit_comprehension_capture",
        emit_capture,
    )
    tools = [_mcp_tool("flame_rename_shots", "Rename shots.")]
    client, patches = _chat_client(router, tools)

    with patches[0], patches[1]:
        response = _post_chat(client, "rename shots")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["stop_reason"] == "preview_emitted"
    assert body["chain"] == []
    assert body["preview"]["summary"]["requires_ratification"] is True
    assert "messages" not in body
    run_chain.assert_not_awaited()
    emit_capture.assert_called_once()
    assert emit_capture.call_args.kwargs["question"] == "rename shots"
    assert emit_capture.call_args.kwargs["answer"] == ""
    assert emit_capture.call_args.kwargs["outcome"] == "preview_emitted"
    assert emit_capture.call_args.kwargs["chain"][0]["step"] == (
        "flame_rename_shots dry_run=False"
    )


def test_chat_handler_json_regime_3_omits_final_text(monkeypatch):
    router = SimpleNamespace(
        compile_intent=AsyncMock(return_value=[
            "flame_rename_shots dry_run=False",
            "commit",
        ])
    )
    monkeypatch.setattr(_chat_compile, "run_chain_steps", AsyncMock())
    client, patches = _chat_client(
        router, [_mcp_tool("flame_rename_shots", "Rename shots.")]
    )

    with patches[0], patches[1]:
        response = _post_chat(client, "rename shots")

    assert "final_text" not in response.json()


def test_chat_handler_json_compile_error_422():
    router = SimpleNamespace(
        compile_intent=AsyncMock(
            side_effect=CompileToolUnknown("missing_tool", 0, "missing_tool")
        )
    )
    client, patches = _chat_client(
        router, [_mcp_tool("forge_list_shots", "List shots.")]
    )

    with patches[0], patches[1]:
        response = _post_chat(client, "list shots")

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "compile_tool_unknown"
    assert body["error"]["details"]["unknown_tool"] == "missing_tool"


def test_chat_handler_json_compile_budget_504():
    router = SimpleNamespace(
        compile_intent=AsyncMock(
            side_effect=CompileBudgetExceeded(30.0, 30.1)
        )
    )
    client, patches = _chat_client(
        router, [_mcp_tool("forge_list_shots", "List shots.")]
    )

    with patches[0], patches[1]:
        response = _post_chat(client, "list shots")

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "compile_budget_exceeded"


def test_chat_handler_json_compile_seam_violation_500():
    router = SimpleNamespace(
        compile_intent=AsyncMock(
            side_effect=CompileSeamViolation("flame_rename_shots", 0)
        )
    )
    client, patches = _chat_client(
        router, [_mcp_tool("flame_rename_shots", "Rename shots.")]
    )

    with patches[0], patches[1]:
        response = _post_chat(client, "rename shots")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "compile_seam_violation"


def test_chat_handler_json_preserves_pr14_pr20_pr30_short_circuits():
    router = SimpleNamespace(compile_intent=AsyncMock(return_value=["unused"]))
    client, patches = _chat_client(
        router, [_mcp_tool("forge_list_shots", "List shots.")]
    )

    with patches[0], patches[1]:
        macro_response = _post_chat(client, "list macros")
        chain_response = _post_chat(client, "forge_list_shots -> format_result")

    assert macro_response.status_code == 200
    assert macro_response.json()["status"] == "success"
    assert chain_response.status_code in {200, 400}
    router.compile_intent.assert_not_awaited()


def test_chat_handler_json_no_complete_with_tools_grep():
    source = inspect.getsource(chat_handler)
    assert "router.complete_with_tools" not in source


def test_chat_handler_json_no_build_orchestration_terminated_body_grep():
    import forge_bridge.console.handlers as handlers

    source = inspect.getsource(handlers)
    assert "_build_orchestration_terminated_body" not in source


def test_chat_handler_sse_regime_2_event_sequence(monkeypatch):
    router = SimpleNamespace(
        compile_intent=AsyncMock(return_value=["forge_list_shots"])
    )
    chain_body = {
        "status": "success",
        "request_id": "req",
        "chain": [{"step": "forge_list_shots", "result": {"shots": []}}],
        "error": None,
    }
    monkeypatch.setattr(
        _chat_compile,
        "run_chain_steps_with_shadow",
        AsyncMock(return_value=chain_body),
    )
    client, patches = _chat_client(
        router, [_mcp_tool("forge_list_shots", "List shots.")]
    )

    with patches[0], patches[1]:
        response = _post_sse(client, "list shots")

    assert response.status_code == 200, response.text
    events = _parse_sse_stream(response.text)
    assert [name for name, _ in events] == ["compile_complete", "chain_complete"]
    assert events[1][1]["chain"] == chain_body["chain"]


def test_chat_handler_sse_regime_3_event_sequence(monkeypatch):
    router = SimpleNamespace(
        compile_intent=AsyncMock(return_value=[
            "flame_rename_shots dry_run=False",
            "commit",
        ])
    )
    monkeypatch.setattr(_chat_compile, "run_chain_steps", AsyncMock())
    client, patches = _chat_client(
        router, [_mcp_tool("flame_rename_shots", "Rename shots.")]
    )

    with patches[0], patches[1]:
        response = _post_sse(client, "rename shots")

    events = _parse_sse_stream(response.text)
    assert [name for name, _ in events] == ["compile_complete", "preview_emitted"]
    assert events[1][1]["preview"]["summary"]["requires_ratification"] is True
    assert "final_text" not in events[1][1]


def test_chat_handler_sse_compile_error_event():
    router = SimpleNamespace(
        compile_intent=AsyncMock(side_effect=CompileUnresolvableIntent(""))
    )
    client, patches = _chat_client(
        router, [_mcp_tool("forge_list_shots", "List shots.")]
    )

    with patches[0], patches[1]:
        response = _post_sse(client, "???")

    events = _parse_sse_stream(response.text)
    assert [name for name, _ in events] == ["compile_error"]
    assert events[0][1]["error"]["code"] == "compile_unresolvable_intent"


def test_chat_handler_sse_chain_aborted_event(monkeypatch):
    router = SimpleNamespace(
        compile_intent=AsyncMock(return_value=["forge_list_shots"])
    )
    chain_body = {
        "status": "error",
        "request_id": "req",
        "chain": [],
        "error": {
            "code": "CHAIN_STEP_FAILED",
            "message": "step failed",
            "step_index": 0,
            "original_error": {"type": "boom"},
        },
    }
    monkeypatch.setattr(
        _chat_compile,
        "run_chain_steps",
        AsyncMock(return_value=chain_body),
    )
    client, patches = _chat_client(
        router, [_mcp_tool("forge_list_shots", "List shots.")]
    )

    with patches[0], patches[1]:
        response = _post_sse(client, "list shots")

    events = _parse_sse_stream(response.text)
    assert [name for name, _ in events] == ["compile_complete", "chain_aborted"]
    assert events[1][1]["error"]["code"] == "CHAIN_STEP_FAILED"
    assert events[1][1]["stop_reason"] == "chain_aborted"


def test_chat_handler_sse_compile_complete_intermediate_event(monkeypatch):
    router = SimpleNamespace(
        compile_intent=AsyncMock(return_value=["forge_list_shots"])
    )
    monkeypatch.setattr(
        _chat_compile,
        "run_chain_steps",
        AsyncMock(return_value={
            "status": "success",
            "request_id": "req",
            "chain": [],
            "error": None,
        }),
    )
    client, patches = _chat_client(
        router, [_mcp_tool("forge_list_shots", "List shots.")]
    )

    with patches[0], patches[1]:
        response = _post_sse(client, "list shots")

    events = _parse_sse_stream(response.text)
    assert events[0][0] == "compile_complete"
    assert events[0][1]["steps_count"] == 1


def test_chat_handler_sse_transport_error_event_unchanged():
    router = SimpleNamespace(
        compile_intent=AsyncMock(side_effect=RuntimeError("backend down"))
    )
    client, patches = _chat_client(
        router, [_mcp_tool("forge_list_shots", "List shots.")]
    )

    with patches[0], patches[1]:
        response = _post_sse(client, "list shots")

    events = _parse_sse_stream(response.text)
    assert [name for name, _ in events] == ["error"]
    assert events[0][1]["error"]["code"] == "internal_error"


def test_chat_handler_sse_no_event_message_grep():
    import forge_bridge.console.handlers as handlers

    source = inspect.getsource(handlers)
    assert "event: message" not in source
    assert "_on_message" not in source
    assert "message_callback" not in source


def test_chat_handler_sse_no_event_done_grep():
    import forge_bridge.console.handlers as handlers

    source = inspect.getsource(handlers)
    assert "event: done" not in source
    assert '"done"' not in source


def test_chat_compile_json_sse_terminal_state_parity(monkeypatch):
    router_json = SimpleNamespace(
        compile_intent=AsyncMock(return_value=[
            "flame_rename_shots dry_run=False",
            "commit",
        ])
    )
    router_sse = SimpleNamespace(
        compile_intent=AsyncMock(return_value=[
            "flame_rename_shots dry_run=False",
            "commit",
        ])
    )
    monkeypatch.setattr(_chat_compile, "run_chain_steps", AsyncMock())
    tools = [_mcp_tool("flame_rename_shots", "Rename shots.")]
    json_client, json_patches = _chat_client(router_json, tools)
    sse_client, sse_patches = _chat_client(router_sse, tools)

    with json_patches[0], json_patches[1]:
        json_response = _post_chat(json_client, "rename shots")
    with sse_patches[0], sse_patches[1]:
        sse_response = _post_sse(sse_client, "rename shots")

    json_body = json_response.json()
    terminal = _parse_sse_stream(sse_response.text)[-1][1]
    assert terminal["stop_reason"] == json_body["stop_reason"]
    assert terminal["preview"] == json_body["preview"]
    assert terminal["chain"] == json_body["chain"]
