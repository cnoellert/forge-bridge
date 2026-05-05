"""PR40 — POST /api/v1/exec HTTP surface (serialization, timeout, parity)."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from httpx import ASGITransport
from starlette.testclient import TestClient

from forge_bridge.console._execute import execute_command
from forge_bridge.console.app import build_console_app
from forge_bridge.console.manifest_service import ManifestService, ToolRecord
from forge_bridge.console.read_api import ConsoleReadAPI
from tests.console.test_pr30_chain import (
    _single_project_payload,
    _text_block,
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


def _record(name: str) -> ToolRecord:
    return ToolRecord(
        name=name,
        origin="synthesized",
        namespace="synth",
        tags=("synthesized",),
    )


@pytest.fixture
def client(monkeypatch):
    ms = ManifestService()
    import asyncio as aio

    loop = aio.new_event_loop()
    try:
        loop.run_until_complete(ms.register(_record("forge_list_projects")))
    finally:
        loop.close()

    import forge_bridge.mcp.server as real_server
    from forge_bridge.console import _tool_filter

    async def _list_tools():
        return [MagicMock(name="forge_list_projects")]

    async def _reach():
        return {"flame_bridge": True}

    monkeypatch.setattr(
        real_server,
        "mcp",
        SimpleNamespace(list_tools=_list_tools),
    )
    monkeypatch.setattr(_tool_filter, "_get_backend_reachability", _reach)

    mock_log = MagicMock()
    mock_log.snapshot.return_value = ([], 0)
    api = ConsoleReadAPI(execution_log=mock_log, manifest_service=ms)
    app = build_console_app(api)
    return TestClient(app)


@pytest.fixture
def mock_mcp():
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
    return mcp


def test_exec_rejects_get(client):
    resp = client.get("/api/v1/exec")
    assert resp.status_code == 405


def test_exec_empty_input(client):
    resp = client.post("/api/v1/exec", json={"text": ""})
    body = resp.json()

    assert body["status"] == "error"
    assert body["error"]["code"] == "EMPTY_COMMAND"
    assert body["chain"] == []
    assert isinstance(body["request_id"], str)


def test_exec_timeout(monkeypatch, client):
    # Production budget is 60s; shrink for CI while preserving TIMEOUT semantics.
    monkeypatch.setattr(
        "forge_bridge.console.handlers._EXEC_HTTP_TIMEOUT",
        0.05,
    )

    async def slow_exec(_):
        await asyncio.sleep(1.0)

    monkeypatch.setattr(
        "forge_bridge.console.app.execute_command",
        slow_exec,
    )

    resp = client.post("/api/v1/exec", json={"text": "list projects"})
    body = resp.json()

    assert body["status"] == "error"
    assert body["error"]["code"] == "TIMEOUT"


def test_exec_passthrough(client, mock_mcp, monkeypatch):
    cmd = "list projects"

    with patch(
        "forge_bridge.console._tool_filter.filter_tools_by_reachable_backends",
        new=AsyncMock(side_effect=_passthrough_filter),
    ), patch(
        "forge_bridge.mcp.server.mcp",
        mock_mcp,
    ):
        expected = asyncio.run(execute_command(cmd))
        resp = client.post("/api/v1/exec", json={"text": cmd})
        actual = resp.json()

    assert actual["status"] == expected["status"]
    assert len(actual["chain"]) == len(expected["chain"])
    for a, e in zip(actual["chain"], expected["chain"]):
        assert a.get("tool") == e.get("tool")
        assert a.get("status") == e.get("status")


@pytest.mark.asyncio
async def test_exec_serialized_concurrency_serialization_test_verifies_max_concurrent_eq_1(
    monkeypatch,
):
    """Concurrency serialization test (verifies max_concurrent == 1)."""
    state = {"entered": 0, "max_concurrent": 0}

    async def tracked_exec(_):
        state["entered"] += 1
        state["max_concurrent"] = max(
            state["max_concurrent"],
            state["entered"],
        )
        await asyncio.sleep(0.2)
        state["entered"] -= 1
        return {
            "status": "success",
            "request_id": "x",
            "chain": [],
        }

    monkeypatch.setattr(
        "forge_bridge.console.app.execute_command",
        tracked_exec,
    )

    fake_read_api = MagicMock()
    fake_read_api.get_tools = AsyncMock(return_value=[])
    fake_read_api.get_tool = AsyncMock(return_value=None)
    fake_read_api.get_executions = AsyncMock(return_value=([], 0))
    fake_read_api.get_manifest = AsyncMock(
        return_value={"tools": [], "count": 0, "schema_version": "1"}
    )
    fake_read_api.get_health = AsyncMock(
        return_value={
            "status": "ok",
            "services": {
                "mcp": {"status": "ok", "detail": ""},
                "flame_bridge": {"status": "ok", "detail": ""},
                "ws_server": {"status": "ok", "detail": ""},
                "llm_backends": [],
                "watcher": {"status": "ok", "detail": ""},
                "storage_callback": {"status": "absent", "detail": ""},
                "console_port": {"status": "ok", "port": 9996, "detail": ""},
            },
            "instance_identity": {
                "execution_log": {"id_match": True, "detail": "canonical"},
                "manifest_service": {"id_match": True, "detail": "canonical"},
            },
        }
    )

    from forge_bridge.console.app import build_console_app

    app = build_console_app(fake_read_api)

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as ac:
        await asyncio.gather(
            ac.post("/api/v1/exec", json={"text": "a"}),
            ac.post("/api/v1/exec", json={"text": "a"}),
        )

    assert state["max_concurrent"] == 1


def test_forge_exec_logs_info(caplog, client, monkeypatch):
    monkeypatch.setattr(
        "forge_bridge.console.handlers._EXEC_HTTP_TIMEOUT",
        30.0,
    )
    async def fast_ok(text: str):
        return {
            "status": "success",
            "request_id": "rid",
            "chain": [],
            "error": None,
        }

    monkeypatch.setattr(
        "forge_bridge.console.app.execute_command",
        fast_ok,
    )

    with caplog.at_level("INFO", logger="forge.exec"):
        client.post("/api/v1/exec", json={"text": "noop"})

    assert any(
        r.name == "forge.exec"
        and r.levelname == "INFO"
        and "exec start rid=" in r.getMessage()
        for r in caplog.records
    )
