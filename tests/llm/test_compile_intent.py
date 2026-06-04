"""D1 substrate tests for LLMRouter.compile_intent."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from forge_bridge.llm.router import (
    CompileBudgetExceeded,
    CompileInvalidChainShape,
    CompileToolUnknown,
    CompileUnresolvableIntent,
    LLMRouter,
    RecursiveToolLoopError,
    _in_tool_loop,
    normalize_chain_shape,
)


def _tool(name: str = "forge_list_shots", description: str = "List shots."):
    return SimpleNamespace(name=name, description=description)


def test_normalize_chain_shape_reattaches_detached_args():
    steps, salvage = normalize_chain_shape([
        "flame_rename_shots",
        '{"params": {"sequence_name": "30sec_21", "prefix": "tv"}}',
    ])

    assert steps == [
        'flame_rename_shots {"params": {"sequence_name": "30sec_21", "prefix": "tv"}}'
    ]
    assert salvage == {
        "salvage_applied": True,
        "original_reason": "detached_args",
    }


@pytest.mark.parametrize(
    ("steps", "message"),
    [
        (
            ['{"params": {"sequence_name": "30sec_21"}}'],
            "detached args step at index 0",
        ),
        (
            [
                "flame_rename_shots prefix=tv",
                '{"params": {"sequence_name": "30sec_21"}}',
            ],
            "detached args step at index 1",
        ),
        (
            [
                "flame_rename_shots",
                '{"params": {"sequence_name": "30sec_21"}}',
                '{"params": {"prefix": "tv"}}',
            ],
            "detached args step at index 1",
        ),
        (
            ["rename the shots"],
            "non-tool step at index 0",
        ),
    ],
)
def test_normalize_chain_shape_leaves_unrepairable_shapes_invalid(steps, message):
    with pytest.raises(CompileInvalidChainShape) as exc_info:
        normalize_chain_shape(steps)

    assert message in exc_info.value.parse_error


def test_normalize_chain_shape_repairs_synthetic_json_list_raise_shape():
    steps, salvage = normalize_chain_shape([
        "flame_rename_shots",
        '{"args": {"sequence_name": "30sec_21", "prefix": "noise"}}',
    ])

    assert steps == [
        'flame_rename_shots {"args": {"sequence_name": "30sec_21", "prefix": "noise"}}'
    ]
    assert salvage["original_reason"] == "detached_args"


def test_normalize_chain_shape_salvages_trailing_empty_segment():
    steps, salvage = normalize_chain_shape(["forge_list_projects", ""])

    assert steps == ["forge_list_projects"]
    assert salvage == {
        "salvage_applied": True,
        "original_reason": "trailing_empty_segment",
    }


def test_normalize_chain_shape_rejects_mid_chain_empty_segment():
    with pytest.raises(CompileInvalidChainShape) as exc_info:
        normalize_chain_shape(["a_tool", "", "b_tool"])

    assert "empty step at index 1" in exc_info.value.parse_error


def test_normalize_chain_shape_clean_chain_has_no_salvage():
    steps, salvage = normalize_chain_shape(["a_tool", "b_tool"])

    assert steps == ["a_tool", "b_tool"]
    assert salvage is None


def test_normalize_chain_shape_multi_salvage_records_both_reasons():
    steps, salvage = normalize_chain_shape([
        "flame_rename_shots",
        '{"params": {"sequence_name": "30sec_21", "prefix": "tv"}}',
        "",
    ])

    assert steps == [
        'flame_rename_shots {"params": {"sequence_name": "30sec_21", "prefix": "tv"}}'
    ]
    assert salvage == {
        "salvage_applied": True,
        "original_reason": "detached_args+trailing_empty_segment",
    }


@pytest.mark.asyncio
async def test_compile_intent_json_list_bare_args_preserves_repairable_shape():
    router = LLMRouter()
    router._async_local = AsyncMock(
        return_value=(
            '['
            '{"tool_name": "flame_rename_shots"}, '
            '{"params": {"sequence_name": "30sec_21", "prefix": "tv"}}'
            ']'
        )
    )

    parsed = await router.compile_intent(
        "rename shots",
        tools=[_tool("flame_rename_shots", "Rename shots.")],
    )
    steps, salvage = normalize_chain_shape(parsed)

    assert parsed == [
        "flame_rename_shots",
        '{"params": {"sequence_name": "30sec_21", "prefix": "tv"}}',
    ]
    assert steps == [
        'flame_rename_shots {"params": {"sequence_name": "30sec_21", "prefix": "tv"}}'
    ]
    assert salvage == {
        "salvage_applied": True,
        "original_reason": "detached_args",
    }


@pytest.mark.asyncio
async def test_compile_intent_parses_valid_chain():
    router = LLMRouter()
    router._async_local = AsyncMock(
        return_value="forge_list_shots -> format_result"
    )

    steps = await router.compile_intent(
        "list shots",
        tools=[_tool("forge_list_shots"), _tool("format_result")],
        sensitive=True,
    )

    assert steps == ["forge_list_shots", "format_result"]


@pytest.mark.asyncio
async def test_compile_intent_raises_unresolvable_intent_on_empty():
    router = LLMRouter()
    router._async_local = AsyncMock(return_value="   ")

    with pytest.raises(CompileUnresolvableIntent) as exc_info:
        await router.compile_intent("list shots", tools=[_tool()])

    assert exc_info.value.raw_response == "   "


@pytest.mark.asyncio
async def test_compile_intent_raises_invalid_chain_shape():
    router = LLMRouter()
    router._async_local = AsyncMock(return_value="foo -> -> bar")

    with pytest.raises(CompileInvalidChainShape) as exc_info:
        await router.compile_intent("list shots", tools=[_tool()])

    assert "empty step" in exc_info.value.parse_error


@pytest.mark.asyncio
async def test_compile_intent_raises_tool_unknown():
    router = LLMRouter()
    router._async_local = AsyncMock(return_value='{"tool_name": "nonexistent_tool"}')

    with pytest.raises(CompileToolUnknown) as exc_info:
        await router.compile_intent("list shots", tools=[_tool("forge_list_shots")])

    assert exc_info.value.unknown_tool == "nonexistent_tool"
    assert exc_info.value.step_index == 0
    assert "nonexistent_tool" in exc_info.value.step_text


@pytest.mark.asyncio
async def test_compile_intent_raises_budget_exceeded():
    router = LLMRouter()
    router._async_local = AsyncMock(side_effect=asyncio.TimeoutError)

    with pytest.raises(CompileBudgetExceeded) as exc_info:
        await router.compile_intent("list shots", tools=[_tool()], max_seconds=0.1)

    assert exc_info.value.max_seconds == 0.1


@pytest.mark.asyncio
async def test_compile_intent_local_guard_fires_in_outer_tool_loop():
    router = LLMRouter()
    router._async_local = AsyncMock(return_value="forge_list_shots")
    token = _in_tool_loop.set(True)
    try:
        with pytest.raises(RecursiveToolLoopError) as exc_info:
            await router.compile_intent("list shots", tools=[_tool()])
    finally:
        _in_tool_loop.reset(token)

    assert "compile_intent() called from within complete_with_tools()" in str(
        exc_info.value
    )
    router._async_local.assert_not_called()


@pytest.mark.asyncio
async def test_compile_intent_does_not_modify_in_tool_loop_contextvar():
    router = LLMRouter()
    router._async_local = AsyncMock(return_value="forge_list_shots")
    token = _in_tool_loop.set(False)
    try:
        await router.compile_intent("list shots", tools=[_tool()])
        assert _in_tool_loop.get() is False
    finally:
        _in_tool_loop.reset(token)


@pytest.mark.asyncio
async def test_compile_intent_does_not_call_acomplete():
    router = LLMRouter()
    router._async_local = AsyncMock(return_value="forge_list_shots")

    with patch.object(
        LLMRouter,
        "acomplete",
        new=AsyncMock(side_effect=AssertionError("acomplete called")),
    ) as spy:
        await router.compile_intent("list shots", tools=[_tool()])

    spy.assert_not_awaited()


@pytest.mark.asyncio
async def test_compile_intent_system_override_replaces_default():
    router = LLMRouter()
    router._async_local = AsyncMock(return_value="forge_list_shots")

    await router.compile_intent(
        "list shots",
        tools=[_tool()],
        system="CUSTOM COMPILE PROMPT",
    )

    router._async_local.assert_awaited_once()
    assert router._async_local.await_args.args[1] == "CUSTOM COMPILE PROMPT"


@pytest.mark.asyncio
async def test_compile_intent_system_none_omits_pr15_language():
    from forge_bridge.console._tool_enforcement import (
        PR15_HARD_TOOL_INSTRUCTION,
    )

    router = LLMRouter()
    router._async_local = AsyncMock(return_value="forge_list_shots")

    await router.compile_intent("list shots", tools=[_tool()])

    system_prompt = router._async_local.await_args.args[1]

    # Grounded PR15 omission check — same distinctive-fragment list as the
    # compile-branch sibling test in test_chat_compile_branch.py. Both tests
    # exercise the same architectural contract (compile prompt PR15-free);
    # both grounded against _tool_enforcement.py source per
    # [[feedback-ground-specs-in-actual-files]] at the negative-assertion
    # layer (DT+Creative Stage 1b ratification 2026-05-28).
    for forbidden in [
        "tool-using agent",
        "answer from memory",
        "looks like a tool call",
        "structured format when using tools",
        "If you fail to call a tool",
    ]:
        assert (
            forbidden not in system_prompt
        ), f"PR15 fragment leaked: {forbidden!r}"
    assert (
        PR15_HARD_TOOL_INSTRUCTION not in system_prompt
    ), "PR15 HARD_TOOL instruction leaked"

    # Positive assertions preserved — these were not part of the F-D3-1 defect.
    assert "chain-step text" in system_prompt
    assert "forge_list_shots" in system_prompt
    assert "tool_name arg=value" in system_prompt
    assert "an args object is never its own step" in system_prompt
    assert "space-bearing entity name is a single quoted literal" in system_prompt
    assert "never normalize spaces to underscores" in system_prompt
    assert "never substitute a near-looking known entity" in system_prompt


@pytest.mark.asyncio
async def test_compile_intent_routes_cloud_without_acomplete():
    router = LLMRouter()
    router._async_cloud = AsyncMock(return_value="forge_list_shots")

    result = await router.compile_intent(
        "list shots",
        tools=[_tool()],
        sensitive=False,
    )

    assert result == ["forge_list_shots"]
    router._async_cloud.assert_awaited_once()


@pytest.mark.asyncio
async def test_compile_intent_emits_ollama_compile_log_line(caplog):
    router = LLMRouter(local_model="local-test-model")
    router._async_local = AsyncMock(return_value="forge_list_shots")
    caplog.set_level("INFO", logger="forge_bridge.llm.router")

    await router.compile_intent("list shots", tools=[_tool()])

    messages = [record.getMessage() for record in caplog.records]
    assert any("ollama-compile model=local-test-model" in msg for msg in messages)
    assert any("cache_prefix_hash=" in msg for msg in messages)
