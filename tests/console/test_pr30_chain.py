"""PR30 — Integration + unit tests for deterministic multi-step tool chaining.

Drives ``POST /api/v1/chat`` with ``->``-separated messages through the chain
executor (``_execute_chain``) using PR28-style MCP mocks. Pure unit tests pin
``parse_chain`` edge contracts without HTTP.
"""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

from forge_bridge.console._chain_parse import parse_chain
from forge_bridge.console._memory import _MEMORY
from forge_bridge.console.app import build_console_app
from forge_bridge.console.manifest_service import ManifestService
from forge_bridge.console.read_api import ConsoleReadAPI

_FIXTURE_UUID_B = "11111111-2222-3333-4444-555555555555"


def _single_project_payload(project_id: str = "only-proj", name: str = "Only") -> str:
    return json.dumps({
        "count": 1,
        "projects": [{"id": project_id, "name": name, "code": name}],
    })


def _two_projects_payload() -> str:
    return json.dumps({
        "count": 2,
        "projects": [
            {"id": "proj-a", "name": "A", "code": "A"},
            {"id": "proj-b", "name": "B", "code": "B"},
        ],
    })


def _versions_payload() -> str:
    return json.dumps({"versions": [{"id": "ver-1", "name": "v1"}]})


def _text_block(text: str):
    from mcp.types import TextContent
    return [TextContent(type="text", text=text)]


def _passthrough_filter(tools, **_):
    return tools


def _make_chain_chat_app(
    *,
    fake_call_tool: Any,
) -> tuple[Any, Any, Any, Any, MagicMock]:
    """App + patches for chain integration tests (passthrough backend filter)."""
    from mcp.types import Tool

    tools_list = [
        Tool(
            name=n,
            description=f"{n} description",
            inputSchema={"type": "object", "properties": {}, "required": []},
        )
        for n in (
            "forge_list_projects",
            "forge_list_versions",
            "flame_alpha",
            "flame_beta",
        )
    ]

    mock_router = MagicMock()
    mock_router.complete_with_tools = AsyncMock(return_value="UNREACHED")
    mock_router.system_prompt = "base"

    ms = ManifestService()
    mock_log = MagicMock()
    mock_log.snapshot.return_value = ([], 0)
    api = ConsoleReadAPI(
        execution_log=mock_log,
        manifest_service=ms,
        llm_router=mock_router,
    )
    app = build_console_app(api)

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


# ── Chain messages: PR14 + PR21 narrow to one tool per step ───────────────

_MSG_TWO_STEP = "list forge projects -> list versions project_name=chatTest"
_MSG_PROPAGATE = "list forge projects -> list versions"
_MSG_TOO_LONG = (
    "list forge projects -> list versions -> "
    "list forge projects -> list versions"
)
_MSG_MULTI_THEN_VERSIONS = "list forge projects -> list versions"
_MSG_MEMORY = _MSG_PROPAGATE


# ── Integration tests (brief AC 1–7) ─────────────────────────────────────


def test_single_chain_two_steps_success():
    async def fake_call_tool(name, arguments):
        if name == "forge_list_projects":
            return _text_block(_single_project_payload())
        if name == "forge_list_versions":
            return _text_block(_versions_payload())
        return _text_block(json.dumps({"unexpected": name}))

    list_p, back_p, call_p, app, mock_router = _make_chain_chat_app(
        fake_call_tool=fake_call_tool,
    )
    with list_p, back_p, call_p:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": _MSG_TWO_STEP}]},
        )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "success"
    assert body["error"] is None
    assert len(body["chain"]) == 2
    assert body["chain"][0]["step"].strip().startswith("list forge projects")
    assert body["chain"][1]["step"].strip().startswith("list versions")
    mock_router.complete_with_tools.assert_not_called()


def test_chain_propagates_project_id():
    calls: list[tuple[str, dict]] = []

    async def fake_call_tool(name, arguments):
        calls.append((name, dict(arguments)))
        if name == "forge_list_projects":
            return _text_block(_single_project_payload("only-proj", "ChatProj"))
        if name == "forge_list_versions":
            return _text_block(_versions_payload())
        return _text_block("{}")

    list_p, back_p, call_p, app, _ = _make_chain_chat_app(
        fake_call_tool=fake_call_tool,
    )
    with list_p, back_p, call_p:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": _MSG_PROPAGATE}]},
        )

    assert r.status_code == 200, r.text
    version_calls = [c for c in calls if c[0] == "forge_list_versions"]
    assert len(version_calls) == 1
    assert version_calls[0][1].get("project_id") == "only-proj"


def test_chain_stops_on_error():
    async def fake_call_tool(name, arguments):
        if name == "forge_list_projects":
            return _text_block(_single_project_payload())
        if name == "forge_list_versions":
            raise RuntimeError("boom")
        return _text_block("{}")

    list_p, back_p, call_p, app, mock_router = _make_chain_chat_app(
        fake_call_tool=fake_call_tool,
    )
    with list_p, back_p, call_p:
        client = TestClient(app)
        resp = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": _MSG_TWO_STEP}]},
        )

    assert resp.status_code == 400
    payload = resp.json()
    assert payload["status"] == "error"
    err = payload["error"]
    assert err["code"] == "CHAIN_STEP_FAILED"
    assert err["step_index"] == 1
    assert "original_error" in err
    assert err["original_error"]["type"] == "RuntimeError"
    assert len(payload.get("chain", [])) == 1
    mock_router.complete_with_tools.assert_not_called()


def test_chain_rejects_long_chain():
    async def fake_call_tool(name, arguments):
        return _text_block("{}")

    list_p, back_p, call_p, app, mock_router = _make_chain_chat_app(
        fake_call_tool=fake_call_tool,
    )
    with list_p, back_p, call_p:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": _MSG_TOO_LONG}]},
        )

    assert r.status_code == 400, r.text
    payload = r.json()
    assert payload["status"] == "error"
    assert payload["chain"] == []
    assert payload["error"]["code"] == "CHAIN_TOO_LONG"
    assert payload["error"]["step_index"] is None
    assert payload["error"]["original_error"] is None
    assert isinstance(payload["request_id"], str)
    assert payload["request_id"]
    mock_router.complete_with_tools.assert_not_called()


def test_chain_ignores_multi_value_results():
    async def fake_call_tool(name, arguments):
        if name == "forge_list_projects":
            return _text_block(_two_projects_payload())
        if name == "forge_list_versions":
            return _text_block(_versions_payload())
        return _text_block("{}")

    list_p, back_p, call_p, app, _ = _make_chain_chat_app(
        fake_call_tool=fake_call_tool,
    )
    with list_p, back_p, call_p:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": _MSG_MULTI_THEN_VERSIONS}]},
        )

    assert r.status_code == 400, r.text
    payload = r.json()
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "CHAIN_STEP_FAILED"
    assert payload["error"]["step_index"] == 1
    assert payload["error"]["original_error"]["type"] == "MULTIPLE_PROJECTS"
    assert len(payload["chain"]) == 1


def test_chain_does_not_use_memory():
    _MEMORY.clear()

    async def fake_call_tool(name, arguments):
        if name == "forge_list_projects":
            return _text_block(_single_project_payload())
        if name == "forge_list_versions":
            return _text_block(_versions_payload())
        return _text_block("{}")

    list_p, back_p, call_p, app, _ = _make_chain_chat_app(
        fake_call_tool=fake_call_tool,
    )
    with list_p, back_p, call_p:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": _MSG_MEMORY}]},
        )

    assert r.status_code == 200, r.text
    assert _MEMORY.get("project_id") is None


def test_chain_respects_param_precedence():
    calls: list[tuple[str, dict]] = []

    async def fake_call_tool(name, arguments):
        calls.append((name, dict(arguments)))
        if name == "forge_list_projects":
            return _text_block(_single_project_payload("from-context", "Ctx"))
        if name == "forge_list_versions":
            return _text_block(_versions_payload())
        return _text_block("{}")

    step2 = f"list versions project_id={_FIXTURE_UUID_B}"
    msg = f"list forge projects -> {step2}"

    list_p, back_p, call_p, app, _ = _make_chain_chat_app(
        fake_call_tool=fake_call_tool,
    )
    with list_p, back_p, call_p:
        client = TestClient(app)
        r = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": msg}]},
        )

    assert r.status_code == 200, r.text
    version_calls = [c for c in calls if c[0] == "forge_list_versions"]
    assert len(version_calls) == 1
    assert version_calls[0][1].get("project_id") == _FIXTURE_UUID_B


# ── Unit: parse_chain ──────────────────────────────────────────────────────


def test_parse_chain_separator_only_returns_empty():
    assert parse_chain("->") == []
    assert parse_chain(" -> ") == []
    assert parse_chain("  ->   ->  ") == []


def test_parse_chain_trim_and_drop_empty_segments():
    assert parse_chain("  a -> b  ") == ["a", "b"]
    assert parse_chain("single") == ["single"]
    assert parse_chain("x ->") == ["x"]
    assert parse_chain("-> y") == ["y"]
