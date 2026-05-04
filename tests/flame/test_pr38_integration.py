"""PR38 — Flame :func:`run_command_from_flame` integration."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from forge_bridge.flame.integration import run_command_from_flame
from tests.console.test_pr30_chain import (
    _single_project_payload,
    _text_block,
    _versions_payload,
)


def _passthrough_filter(tools, **_):
    return tools


def _tools_list() -> list:
    from mcp.types import Tool

    names = (
        "forge_list_projects",
        "forge_list_versions",
        "flame_alpha",
    )
    return [
        Tool(
            name=n,
            description=f"{n} description",
            inputSchema={"type": "object", "properties": {}, "required": []},
        )
        for n in names
    ]


@pytest.fixture
def flame_exec_env():
    tools = _tools_list()

    async def fake_call_tool(name, arguments):
        if name == "forge_list_projects":
            return _text_block(_single_project_payload())
        if name == "forge_list_versions":
            return _text_block(_versions_payload())
        return _text_block("{}")

    call_mock = AsyncMock(side_effect=fake_call_tool)
    list_p = patch(
        "forge_bridge.mcp.server.mcp.list_tools",
        new=AsyncMock(return_value=tools),
    )
    call_p = patch(
        "forge_bridge.mcp.server.mcp.call_tool",
        new=call_mock,
    )
    back_p = patch(
        "forge_bridge.console._tool_filter.filter_tools_by_reachable_backends",
        new=AsyncMock(side_effect=_passthrough_filter),
    )
    with list_p, call_p, back_p:
        yield call_mock


def test_flame_executes_basic_command(flame_exec_env):
    call_mock = flame_exec_env
    result = run_command_from_flame("list forge projects")

    assert result["status"] in {"success", "error"}
    assert "chain" in result
    assert call_mock.await_count >= 1


def test_flame_injects_context(flame_exec_env):
    result = run_command_from_flame(
        "list forge versions",
        context={"project_name": "Only"},
    )

    assert result["status"] in {"success", "error"}
    assert len(result["chain"]) == 1


def test_flame_does_not_override_explicit(flame_exec_env):
    """PR26: first ``project_id=`` in the merged message wins (command over suffix)."""
    call_mock = flame_exec_env
    override = "11111111-1111-1111-1111-111111111111"
    ctx_id = "22222222-2222-2222-2222-222222222222"

    result = run_command_from_flame(
        f"list forge versions project_id={override}",
        context={"project_id": ctx_id},
    )

    assert result["status"] in {"success", "error"}
    versions_calls = [
        c for c in call_mock.call_args_list
        if c.args and c.args[0] == "forge_list_versions"
    ]
    assert versions_calls
    assert versions_calls[0].args[1].get("project_id") == override
    assert versions_calls[-1].args[1].get("project_id") == override


def test_empty_command_returns_error():
    result = run_command_from_flame("")

    assert result["status"] == "error"
    assert result["error"]["code"] == "EMPTY_COMMAND"
    assert isinstance(result["request_id"], str)
    assert len(result["request_id"]) > 0


def test_empty_command_has_request_id():
    result = run_command_from_flame("   ")

    assert result["status"] == "error"
    assert result["error"]["code"] == "EMPTY_COMMAND"
    assert isinstance(result["request_id"], str)
    assert len(result["request_id"]) > 0


def test_success_has_request_id(flame_exec_env):
    result = run_command_from_flame("list forge projects")

    assert isinstance(result["request_id"], str)
    assert len(result["request_id"]) > 0


def test_context_only_command_rejected():
    result = run_command_from_flame(
        "   ",
        context={"project_id": "abc"},
    )

    assert result["status"] == "error"
    assert result["error"]["code"] == "EMPTY_COMMAND"
