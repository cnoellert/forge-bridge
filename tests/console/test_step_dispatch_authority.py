from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from forge_bridge.console._step import execute_chain_step


def _tool(name: str, *, read_only: bool):
    return SimpleNamespace(
        name=name,
        description=f"test tool {name}",
        annotations=SimpleNamespace(readOnlyHint=read_only),
    )


@pytest.mark.asyncio
async def test_chain_step_blocks_mutating_tool_before_call_tool():
    """1C: routing-selected mutating tool is blocked before dispatch."""
    mcp = SimpleNamespace(call_tool=AsyncMock(return_value={"unreached": True}))
    tool = _tool("flame_set_start_frames", read_only=False)

    result = await execute_chain_step(
        step_text="flame_set_start_frames sequence_name=30sec",
        tools=[tool],
        mcp=mcp,
        inherited_context={},
    )

    assert result == {
        "error": {
            "type": "unauthorized_mutation",
            "message": (
                "Request stopped before execution. "
                "Tool: `flame_set_start_frames`. "
                "Classification: mutating. "
                "This path permits read operations only. "
                "Use a ratified operation if you intend to modify project state."
            ),
        },
        "classification": "mutating",
        "tool": "flame_set_start_frames",
    }
    mcp.call_tool.assert_not_awaited()


@pytest.mark.asyncio
async def test_chain_step_allows_read_tool_to_call_tool():
    mcp = SimpleNamespace(call_tool=AsyncMock(return_value={"result": '{"ok":true}'}))
    tool = _tool("forge_ping", read_only=True)

    result = await execute_chain_step(
        step_text="forge_ping",
        tools=[tool],
        mcp=mcp,
        inherited_context={},
    )

    assert result["tool"] == "forge_ping"
    assert result["result"] == {"ok": True}
    mcp.call_tool.assert_awaited_once()
