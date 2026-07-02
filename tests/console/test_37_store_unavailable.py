"""#37 — store-degraded/unreachable surfacing on the tool-chain grounding path.

The deterministic tool-chain grounding path used to collapse "store is
degraded/unreachable" into the same ``None`` → ``MISSING_PROJECT_ID``
("which project?") that a genuine zero-projects result produces, masking an
infra failure as a user-disambiguation prompt. The LIVE planner-front path was
already fixed by #44 (``_ground_projects`` raises ``ProjectGroundingUnavailable``);
this exercises the tool-chain sibling, which MIRRORS the existing sentinel
idiom (``DISAMBIGUATION_KEY``) rather than raising.

Coverage:
  - resolver: explicit ``error`` / ``STORE_UNAVAILABLE`` code → sentinel dict
  - resolver: transport exception from ``call_tool`` → sentinel dict
  - resolver: healthy zero (``projects == []``, no error) → ``None`` (UNCHANGED)
  - ``resolve_required_params`` propagates the sentinel + writes no memory
  - chat handler: store error → 200 + ``stop_reason="store_unavailable"``, no tool call
  - ``execute_chain_step``: store error → ``store_unavailable`` error dict
  - regression: healthy-zero still yields MISSING_PROJECT_ID end-to-end
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

from forge_bridge.console._memory import _MEMORY
from forge_bridge.console._step import execute_chain_step
from forge_bridge.console._tool_chain import (
    STORE_UNAVAILABLE_KEY,
    _resolve_project_id,
    resolve_required_params,
)
from forge_bridge.console.app import build_console_app
from forge_bridge.console.manifest_service import ManifestService
from forge_bridge.console.read_api import ConsoleReadAPI


def _text_block(text: str):
    from mcp.types import TextContent
    return [TextContent(type="text", text=text)]


def _store_error_payload() -> str:
    # Mirrors mcp/tools.py:list_projects → _err(str(e), "STORE_UNAVAILABLE").
    return json.dumps({"error": "connection refused", "code": "STORE_UNAVAILABLE"})


# ── Unit: resolver surfaces store-unavailable, NOT None ──────────────────


@pytest.mark.asyncio
async def test_resolver_error_code_returns_store_unavailable_sentinel():
    mcp = AsyncMock()
    mcp.call_tool = AsyncMock(return_value=_text_block(_store_error_payload()))

    result = await _resolve_project_id(mcp)

    assert isinstance(result, dict)
    assert STORE_UNAVAILABLE_KEY in result
    assert result[STORE_UNAVAILABLE_KEY]["reason"] == "connection refused"


@pytest.mark.asyncio
async def test_resolver_transport_exception_returns_store_unavailable_sentinel():
    mcp = AsyncMock()
    mcp.call_tool = AsyncMock(side_effect=RuntimeError("socket down"))

    result = await _resolve_project_id(mcp)

    assert isinstance(result, dict)
    assert STORE_UNAVAILABLE_KEY in result


@pytest.mark.asyncio
async def test_resolver_error_without_code_still_surfaces():
    """A truthy ``error`` with no explicit code still means degraded."""
    mcp = AsyncMock()
    mcp.call_tool = AsyncMock(return_value=_text_block(
        json.dumps({"error": "boom"})
    ))

    result = await _resolve_project_id(mcp)

    assert isinstance(result, dict) and STORE_UNAVAILABLE_KEY in result


# ── Unit: healthy zero MUST stay None (scope limit / no regression) ──────


@pytest.mark.asyncio
async def test_resolver_healthy_zero_still_returns_none():
    mcp = AsyncMock()
    mcp.call_tool = AsyncMock(return_value=_text_block(
        json.dumps({"count": 0, "projects": []})
    ))

    result = await _resolve_project_id(mcp)

    assert result is None


# ── resolve_required_params: propagate sentinel, no memory write ─────────


@pytest.mark.asyncio
async def test_resolve_required_params_propagates_store_unavailable():
    assert _MEMORY.get("project_id") is None  # autouse fixture guarantee
    mcp = AsyncMock()
    mcp.call_tool = AsyncMock(return_value=_text_block(_store_error_payload()))

    out = await resolve_required_params("forge_list_versions", {}, mcp)

    assert STORE_UNAVAILABLE_KEY in out
    assert out[STORE_UNAVAILABLE_KEY]["type"] == "project"
    assert out[STORE_UNAVAILABLE_KEY]["reason"] == "connection refused"
    # A degraded store must NOT poison the memory cache.
    assert _MEMORY.get("project_id") is None


@pytest.mark.asyncio
async def test_resolve_required_params_healthy_zero_no_sentinel():
    mcp = AsyncMock()
    mcp.call_tool = AsyncMock(return_value=_text_block(
        json.dumps({"count": 0, "projects": []})
    ))

    out = await resolve_required_params("forge_list_versions", {}, mcp)

    assert out == {}
    assert STORE_UNAVAILABLE_KEY not in out


# ── _step consumer: store error → store_unavailable error dict ───────────


def _read_tool(name: str):
    return SimpleNamespace(
        name=name,
        description=f"test tool {name}",
        annotations=SimpleNamespace(readOnlyHint=True),
    )


@pytest.mark.asyncio
async def test_step_surfaces_store_unavailable():
    mcp = SimpleNamespace(
        call_tool=AsyncMock(return_value={"result": _store_error_payload()})
    )
    tool = _read_tool("forge_list_versions")

    result = await execute_chain_step(
        step_text="forge_list_versions",
        tools=[tool],
        mcp=mcp,
        inherited_context={},
    )

    assert "error" in result
    err = result["error"]
    assert err["type"] == "store_unavailable"
    assert err["stop_reason"] == "store_unavailable"
    assert "can't reach the project store" in err["message"]


@pytest.mark.asyncio
async def test_step_transport_exception_surfaces_store_unavailable():
    mcp = SimpleNamespace(call_tool=AsyncMock(side_effect=RuntimeError("down")))
    tool = _read_tool("forge_list_versions")

    result = await execute_chain_step(
        step_text="forge_list_versions",
        tools=[tool],
        mcp=mcp,
        inherited_context={},
    )

    assert result["error"]["type"] == "store_unavailable"
    assert result["error"]["stop_reason"] == "store_unavailable"


# ── Handler integration: honest message + stop_reason, no tool call ──────


def _passthrough_filter(tools, **_):
    return tools


def _make_handler_app(*, projects_payload: str):
    from mcp.types import TextContent, Tool, ToolAnnotations

    tools_list = [
        Tool(
            name=n,
            description=f"{n} description",
            inputSchema={"type": "object", "properties": {}, "required": []},
            annotations=ToolAnnotations(readOnlyHint=True),
        )
        for n in ["forge_list_versions", "flame_alpha", "flame_beta", "synth_gamma"]
    ]

    mock_router = MagicMock()
    mock_router.complete_with_tools = AsyncMock(return_value="UNREACHED")
    mock_router.system_prompt = "base"

    ms = ManifestService()
    mock_log = MagicMock()
    mock_log.snapshot.return_value = ([], 0)
    api = ConsoleReadAPI(
        execution_log=mock_log, manifest_service=ms, llm_router=mock_router,
    )
    app = build_console_app(api)

    async def fake_call_tool(name, arguments):
        if name == "forge_list_projects":
            return [TextContent(type="text", text=projects_payload)]
        if name == "forge_list_versions" and "project_id" not in arguments:
            return [TextContent(type="text", text=json.dumps({
                "error": "project_id is required",
                "code": "MISSING_PROJECT_ID",
            }))]
        return [TextContent(type="text", text=f"{name}-result:{arguments!r}")]

    list_p = patch(
        "forge_bridge.mcp.server.mcp.list_tools",
        new=AsyncMock(return_value=tools_list),
    )
    back_p = patch(
        "forge_bridge.console.handlers.filter_tools_by_reachable_backends",
        side_effect=_passthrough_filter,
    )
    call_p = patch(
        "forge_bridge.mcp.server.mcp.call_tool",
        new=AsyncMock(side_effect=fake_call_tool),
    )
    return list_p, back_p, call_p, app, mock_router


def test_handler_store_unavailable_surfaces_honest_message():
    list_p, back_p, call_p, app, mock_router = _make_handler_app(
        projects_payload=_store_error_payload(),
    )
    with list_p, back_p, call_p as call_mock:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": "forge fetch versions"},
            ]},
        )

    assert r.status_code == 200, r.text
    assert "X-Request-ID" in r.headers
    body = r.json()
    assert body["stop_reason"] == "store_unavailable"
    assert "can't reach the project store" in body["final_text"]
    assert body["messages"][-1]["content"] == body["final_text"]
    # Neither LLM nor the target tool ran — only the projects probe.
    mock_router.complete_with_tools.assert_not_called()
    call_mock.assert_called_once_with("forge_list_projects", {})


def test_handler_healthy_zero_still_missing_project_id():
    """Regression guard: a genuine healthy zero is UNCHANGED — still the
    PR22 MISSING_PROJECT_ID contract, NOT store_unavailable."""
    list_p, back_p, call_p, app, mock_router = _make_handler_app(
        projects_payload=json.dumps({"count": 0, "projects": []}),
    )
    with list_p, back_p, call_p:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [
                {"role": "user", "content": "forge fetch versions"},
            ]},
        )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("stop_reason") != "store_unavailable"
    tool_msg = body["messages"][-1]
    payload = json.loads(tool_msg["content"])
    assert payload["code"] == "MISSING_PROJECT_ID"
    mock_router.complete_with_tools.assert_not_called()
