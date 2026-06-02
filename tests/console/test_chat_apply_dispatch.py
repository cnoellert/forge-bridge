from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from forge_bridge.console import _rate_limit
from forge_bridge.console.app import build_console_app
from forge_bridge.console.manifest_service import ManifestService
from forge_bridge.console.read_api import ConsoleReadAPI
from forge_bridge.store.assent_record_repo import AssentRecordRepo
from tests.console.test_pr30_chain import _text_block


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    _rate_limit._reset_for_tests()
    yield
    _rate_limit._reset_for_tests()


def _tool(name: str, *, read_only: bool = False):
    from mcp.types import Tool, ToolAnnotations

    return Tool(
        name=name,
        description=f"test tool {name}",
        annotations=ToolAnnotations(readOnlyHint=read_only),
        inputSchema={"type": "object", "properties": {}, "required": []},
    )


def _manifest() -> dict:
    return {
        "type": "mutation_plan",
        "intent_parameters": {"request": "demo"},
        "resolved_plan": [{"identity": {"name": "a"}, "payload": {"value": "one"}}],
        "originating_capability": "emit_plan",
        "apply_counterpart": {
            "tool": "emit_plan",
            "parameter_overrides": {"dry_run": False},
        },
    }


class ApplyMCP:
    def __init__(self, tools=None):
        self.calls: list[tuple[str, dict]] = []
        self._tools = tools or [_tool("emit_plan")]

    async def list_tools(self):
        return self._tools

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        if len(self.calls) <= 2:
            return _text_block(json.dumps(_manifest()))
        return _text_block(json.dumps({"applied": 1}))


async def _passthrough_filter(tools):
    return tools


def _client(session_factory, mcp):
    api = ConsoleReadAPI(
        execution_log=MagicMock(),
        manifest_service=ManifestService(),
        llm_router=MagicMock(),
        session_factory=session_factory,
    )
    api._execution_log.snapshot.return_value = ([], 0)
    app = build_console_app(api, session_factory=session_factory)
    patches = (
        patch("forge_bridge.mcp.server.mcp", mcp),
        patch(
            "forge_bridge.console.handlers.filter_tools_by_reachable_backends",
            new=AsyncMock(side_effect=_passthrough_filter),
        ),
    )
    return app, patches


async def _proposed_record(session_factory):
    async with session_factory() as session:
        repo = AssentRecordRepo(session)
        record = await repo.propose(["emit_plan", "commit"])
        await session.commit()
        return record


async def _ratified_record(session_factory):
    record = await _proposed_record(session_factory)
    async with session_factory() as session:
        repo = AssentRecordRepo(session)
        ratified = await repo.ratify(record.graph_intent_id, actor="local")
        await session.commit()
        return ratified


def _parse_sse_stream(text: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    event = None
    data = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip("\r")
        if line.startswith("event:"):
            event = line[len("event:"):].strip()
        elif line.startswith("data:"):
            data = line[len("data:"):].strip()
        elif line == "" and event is not None and data is not None:
            events.append((event, json.loads(data)))
            event = None
            data = None
    if event is not None and data is not None:
        events.append((event, json.loads(data)))
    return events


@pytest.mark.asyncio
async def test_chat_apply_json_dispatch_applies_ratified_record(session_factory):
    record = await _ratified_record(session_factory)
    mcp = ApplyMCP()
    app, patches = _client(session_factory, mcp)

    with patches[0], patches[1]:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.post(
                "/api/v1/chat",
                json={"messages": [{
                    "role": "user",
                    "content": f"apply {record.graph_intent_id}",
                }]},
            )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["apply_complete"]["graph_intent_id"] == record.graph_intent_id
    assert body["apply_complete"]["stop_reason"] == "apply_complete"
    assert body["apply_complete"]["transport"] == "json"
    assert [(name, args.get("mode")) for name, args in mcp.calls] == [
        ("emit_plan", None),
        ("emit_plan", "verify"),
        ("emit_plan", "apply"),
    ]


@pytest.mark.asyncio
async def test_chat_apply_json_replay_uses_reachable_surface_not_apply_narrowing(
    session_factory,
):
    record = await _ratified_record(session_factory)
    mcp = ApplyMCP(tools=[
        _tool("emit_plan"),
        _tool("forge_apply_rename"),
    ])
    app, patches = _client(session_factory, mcp)

    with patches[0], patches[1]:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.post(
                "/api/v1/chat",
                json={"messages": [{
                    "role": "user",
                    "content": f"apply {record.graph_intent_id}",
                }]},
            )

    assert response.status_code == 200, response.text
    assert [name for name, _ in mcp.calls] == ["emit_plan", "emit_plan", "emit_plan"]


@pytest.mark.asyncio
async def test_chat_apply_sse_dispatch_emits_apply_complete(session_factory):
    record = await _ratified_record(session_factory)
    mcp = ApplyMCP()
    app, patches = _client(session_factory, mcp)

    with patches[0], patches[1]:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.post(
                "/api/v1/chat",
                json={"messages": [{
                    "role": "user",
                    "content": f"apply {record.graph_intent_id}",
                }]},
                headers={"Accept": "text/event-stream"},
            )

    events = _parse_sse_stream(response.text)
    assert [name for name, _ in events] == ["apply_complete"]
    assert events[0][1]["graph_intent_id"] == record.graph_intent_id
    assert events[0][1]["transport"] == "sse"


@pytest.mark.asyncio
async def test_chat_apply_unknown_record_returns_error(session_factory):
    mcp = ApplyMCP()
    app, patches = _client(session_factory, mcp)

    with patches[0], patches[1]:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.post(
                "/api/v1/chat",
                json={"messages": [{
                    "role": "user",
                    "content": "apply abc123def456",
                }]},
            )

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "assent_record_not_found"


@pytest.mark.asyncio
async def test_chat_apply_proposed_record_returns_illegal_state(session_factory):
    record = await _proposed_record(session_factory)
    mcp = ApplyMCP()
    app, patches = _client(session_factory, mcp)

    with patches[0], patches[1]:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.post(
                "/api/v1/chat",
                json={"messages": [{
                    "role": "user",
                    "content": f"apply {record.graph_intent_id}",
                }]},
            )

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "assent_illegal_state"
    assert body["error"]["details"]["current_status"] == "proposed"
