from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from forge_bridge.console._step import execute_chain_step
from tests.console.test_pr30_chain import _text_block


def _tool(name: str, *, read_only: bool, description: str | None = None):
    return SimpleNamespace(
        name=name,
        description=description if description is not None else f"{name} tool",
        annotations=SimpleNamespace(readOnlyHint=read_only),
        inputSchema={"type": "object", "properties": {}, "required": []},
    )


@pytest.mark.asyncio
async def test_di2_exact_read_step_resolves_to_one_tool_and_executes():
    mcp = SimpleNamespace(
        call_tool=AsyncMock(return_value=_text_block('{"path": "/shots/010"}'))
    )
    tools = [
        _tool("forge_get_shot_stack", read_only=True),
        _tool("forge_get_shot", read_only=True),
        _tool("forge_get_shot_versions", read_only=True),
        _tool("forge_get_shot_lineage", read_only=True),
    ]

    result = await execute_chain_step(
        step_text="forge_get_shot shot=10",
        tools=tools,
        mcp=mcp,
        inherited_context={},
    )

    assert result["tool"] == "forge_get_shot"
    assert result["result"] == {"path": "/shots/010"}
    mcp.call_tool.assert_awaited_once()
    assert mcp.call_tool.await_args.args[0] == "forge_get_shot"


@pytest.mark.asyncio
async def test_di2_exact_mutating_step_reaches_di1_gate_and_blocks():
    mcp = SimpleNamespace(call_tool=AsyncMock(return_value=_text_block("{}")))
    tools = [
        _tool("flame_list_start_frames", read_only=True),
        _tool("flame_set_start_frames", read_only=False),
        _tool("flame_set_segment_attribute", read_only=False),
    ]

    result = await execute_chain_step(
        step_text="flame_set_start_frames sequence_name=30sec",
        tools=tools,
        mcp=mcp,
        inherited_context={},
    )

    assert result["error"]["type"] == "unauthorized_mutation"
    assert result["classification"] == "mutating"
    assert result["tool"] == "flame_set_start_frames"
    mcp.call_tool.assert_not_awaited()


@pytest.mark.asyncio
async def test_di2_ambiguous_surface_does_not_leak_tool_identifiers():
    mcp = SimpleNamespace(call_tool=AsyncMock(return_value=_text_block("{}")))
    tools = [
        _tool(
            "forge_get_staged",
            read_only=True,
            description="forge_get_staged: get one staged operation",
        ),
        _tool(
            "forge_list_staged",
            read_only=True,
            description="forge_list_staged: list staged operations",
        ),
    ]

    result = await execute_chain_step(
        step_text="list projects",
        tools=tools,
        mcp=mcp,
        inherited_context={},
    )

    error = result["error"]
    rendered = f"{error}"
    assert error["type"] == "tool_selection_ambiguous"
    assert "candidates" not in error
    assert "outcomes" in error
    assert "forge_get_staged" not in rendered
    assert "forge_list_staged" not in rendered
    mcp.call_tool.assert_not_awaited()
