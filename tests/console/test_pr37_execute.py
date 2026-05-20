"""PR37 — Direct ``execute_command`` path (no HTTP, no LLM by design)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from forge_bridge.console._constants import CHAIN_MAX_STEPS
from forge_bridge.console._execute import execute_command
from tests.console.test_pr30_chain import (
    _single_project_payload,
    _text_block,
    _two_projects_payload,
    _versions_payload,
)


def _passthrough_filter(tools, **_):
    return tools


def _tools_list(names: tuple[str, ...]) -> list:
    from mcp.types import Tool

    return [
        Tool(
            name=n,
            description=f"{n} description",
            inputSchema={"type": "object", "properties": {}, "required": []},
        )
        for n in names
    ]


@pytest.mark.asyncio
async def test_execute_single_step_pr31_envelope():
    tools = _tools_list(
        ("forge_list_projects", "forge_list_versions", "flame_alpha"),
    )
    mcp = MagicMock()
    mcp.list_tools = AsyncMock(return_value=tools)

    async def call_tool(name, arguments):
        if name == "forge_list_projects":
            return _text_block(_single_project_payload())
        return _text_block("{}")

    mcp.call_tool = AsyncMock(side_effect=call_tool)

    with patch(
        "forge_bridge.console._tool_filter.filter_tools_by_reachable_backends",
        new=AsyncMock(side_effect=_passthrough_filter),
    ):
        result = await execute_command("list forge projects", mcp=mcp)

    assert result["status"] == "success"
    assert result["error"] is None
    assert len(result["chain"]) == 1
    assert result["chain"][0]["step"] == "list forge projects"
    assert "request_id" in result


@pytest.mark.asyncio
async def test_execute_chain_multi_step():
    tools = _tools_list(
        ("forge_list_projects", "forge_list_versions", "flame_alpha"),
    )
    mcp = MagicMock()
    mcp.list_tools = AsyncMock(return_value=tools)

    async def call_tool(name, arguments):
        if name == "forge_list_projects":
            return _text_block(_single_project_payload())
        if name == "forge_list_versions":
            return _text_block(_versions_payload())
        return _text_block("{}")

    mcp.call_tool = AsyncMock(side_effect=call_tool)

    with patch(
        "forge_bridge.console._tool_filter.filter_tools_by_reachable_backends",
        new=AsyncMock(side_effect=_passthrough_filter),
    ):
        result = await execute_command(
            "list forge projects -> list versions project_name=Only",
            mcp=mcp,
        )

    assert result["status"] == "success"
    assert "chain" in result
    assert len(result["chain"]) == 2


@pytest.mark.asyncio
async def test_execute_empty_command():
    mcp = MagicMock()
    mcp.list_tools = AsyncMock(return_value=_tools_list(("forge_list_projects",)))
    mcp.call_tool = AsyncMock()

    with patch(
        "forge_bridge.console._tool_filter.filter_tools_by_reachable_backends",
        new=AsyncMock(side_effect=_passthrough_filter),
    ):
        result = await execute_command("", mcp=mcp)

    assert result["status"] == "error"
    assert result["error"]["code"] == "EMPTY_COMMAND"
    mcp.call_tool.assert_not_called()


@pytest.mark.asyncio
async def test_execute_chain_too_long():
    tools = _tools_list(
        ("forge_list_projects", "forge_list_versions", "flame_alpha"),
    )
    mcp = MagicMock()
    mcp.list_tools = AsyncMock(return_value=tools)
    mcp.call_tool = AsyncMock(return_value=_text_block("{}"))

    msg = " -> ".join(["list forge projects"] * (CHAIN_MAX_STEPS + 1))

    with patch(
        "forge_bridge.console._tool_filter.filter_tools_by_reachable_backends",
        new=AsyncMock(side_effect=_passthrough_filter),
    ):
        result = await execute_command(msg, mcp=mcp)

    assert result["status"] == "error"
    assert result["error"]["code"] == "CHAIN_TOO_LONG"
    assert "runaway guard" in result["error"]["message"]
    assert "pathological loop" in result["error"]["message"]


@pytest.mark.asyncio
async def test_execute_step_failure_envelope():
    tools = _tools_list(("forge_list_projects",))
    mcp = MagicMock()
    mcp.list_tools = AsyncMock(return_value=tools)

    async def call_tool(name, arguments):
        raise RuntimeError("boom")

    mcp.call_tool = AsyncMock(side_effect=call_tool)

    with patch(
        "forge_bridge.console._tool_filter.filter_tools_by_reachable_backends",
        new=AsyncMock(side_effect=_passthrough_filter),
    ):
        result = await execute_command("list forge projects", mcp=mcp)

    assert result["status"] == "error"
    assert result["error"]["code"] == "CHAIN_STEP_FAILED"


@pytest.mark.asyncio
async def test_execute_matches_chat_chain_engine_two_projects_ambiguity():
    """Same ambiguity as PR30 when two projects — deterministic step error."""
    tools = _tools_list(
        ("forge_list_projects", "forge_list_versions", "flame_alpha"),
    )
    mcp = MagicMock()
    mcp.list_tools = AsyncMock(return_value=tools)

    async def call_tool(name, arguments):
        if name == "forge_list_projects":
            return _text_block(_two_projects_payload())
        if name == "forge_list_versions":
            return _text_block(_versions_payload())
        return _text_block("{}")

    mcp.call_tool = AsyncMock(side_effect=call_tool)

    with patch(
        "forge_bridge.console._tool_filter.filter_tools_by_reachable_backends",
        new=AsyncMock(side_effect=_passthrough_filter),
    ):
        result = await execute_command(
            "list forge projects -> list versions",
            mcp=mcp,
        )

    assert result["status"] == "error"
    assert result["error"]["code"] == "CHAIN_STEP_FAILED"
