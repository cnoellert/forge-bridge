"""POST /api/v1/exec {"tool": ...} — deterministic exact-name dispatch.

Bypasses the chain-engine resolver + ``filter_tools_by_reachable_backends`` so a
health probe like ``flame_ping`` dispatches even when its backend (Flame) is
down — the condition the reachability filter would otherwise hide by removing the
tool from the resolvable set. Backs the doctor flame_bridge probe (#61 follow-on).
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from forge_bridge.console.handlers import _dispatch_tool_by_name, _extract_structured


def _tools(names: tuple[str, ...]) -> list:
    from mcp.types import Tool, ToolAnnotations

    return [
        Tool(
            name=n,
            description=f"{n} desc",
            annotations=ToolAnnotations(readOnlyHint=True),
            inputSchema={"type": "object", "properties": {}, "required": []},
        )
        for n in names
    ]


def test_extract_structured_decodes_json_string_result():
    # FastMCP wraps a schema-bearing tool as (content_blocks, {"result": <str>}).
    raw = ([], {"result": '{"connected": false, "bridge_url": "http://x:9999"}'})
    assert _extract_structured(raw) == {
        "connected": False,
        "bridge_url": "http://x:9999",
    }


def test_extract_structured_from_text_blocks():
    block = MagicMock()
    block.text = '{"b": 2}'
    assert _extract_structured([block]) == {"b": 2}


@pytest.mark.asyncio
async def test_dispatch_tool_success_pr31_envelope():
    mcp = MagicMock()
    mcp.list_tools = AsyncMock(
        return_value=_tools(("flame_ping", "forge_list_projects"))
    )
    # flame_ping's Flame-down body — JSON string, structured-wrapped.
    mcp.call_tool = AsyncMock(
        return_value=([], {"result": '{"connected": false, "bridge_url": "http://127.0.0.1:9999"}'})
    )
    with patch("forge_bridge.mcp.server.mcp", mcp), patch(
        "forge_bridge.mcp.arguments.normalize_tool_args", lambda n, a, t: {}
    ):
        env = await _dispatch_tool_by_name("flame_ping")

    assert env["status"] == "success"
    assert env["error"] is None
    assert env["chain"][0]["tool"] == "flame_ping"
    # Decoded to a dict — the shape the doctor probe parses (connected/bridge_url).
    assert env["chain"][0]["result"] == {
        "connected": False,
        "bridge_url": "http://127.0.0.1:9999",
    }
    mcp.call_tool.assert_awaited_once()


@pytest.mark.asyncio
async def test_dispatch_unknown_tool_is_unknown_action_not_called():
    mcp = MagicMock()
    mcp.list_tools = AsyncMock(return_value=_tools(("forge_list_projects",)))
    mcp.call_tool = AsyncMock()
    with patch("forge_bridge.mcp.server.mcp", mcp):
        env = await _dispatch_tool_by_name("flame_ping")

    assert env["status"] == "error"
    assert env["error"]["code"] == "unknown_action"
    assert env["chain"] == []
    mcp.call_tool.assert_not_called()


@pytest.mark.asyncio
async def test_dispatch_tool_raise_is_execution_failed():
    mcp = MagicMock()
    mcp.list_tools = AsyncMock(return_value=_tools(("flame_ping",)))
    mcp.call_tool = AsyncMock(side_effect=RuntimeError("boom"))
    with patch("forge_bridge.mcp.server.mcp", mcp), patch(
        "forge_bridge.mcp.arguments.normalize_tool_args", lambda n, a, t: {}
    ):
        env = await _dispatch_tool_by_name("flame_ping")

    assert env["status"] == "error"
    assert env["error"]["code"] == "execution_failed"
    assert "boom" in env["error"]["message"]
