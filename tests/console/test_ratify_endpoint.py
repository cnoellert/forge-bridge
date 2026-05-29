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
from tests.console.test_chat_apply_dispatch import ApplyMCP


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    _rate_limit._reset_for_tests()
    yield
    _rate_limit._reset_for_tests()


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


@pytest.mark.asyncio
async def test_ratify_endpoint_ratifies_and_applies(session_factory):
    record = await _proposed_record(session_factory)
    mcp = ApplyMCP()
    app, patches = _client(session_factory, mcp)

    with patches[0], patches[1]:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.post(
                "/api/v1/ratify",
                content=json.dumps({
                    "graph_intent_id": record.graph_intent_id,
                    "actor": "local",
                }),
            )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["apply_complete"]["graph_intent_id"] == record.graph_intent_id

    async with session_factory() as session:
        repo = AssentRecordRepo(session)
        applied = await repo.get_by_graph_intent_id(record.graph_intent_id)
    assert applied.status == "applied"
    assert applied.decided_by == "local"


@pytest.mark.asyncio
async def test_ratify_endpoint_unknown_record_returns_404(session_factory):
    mcp = ApplyMCP()
    app, patches = _client(session_factory, mcp)

    with patches[0], patches[1]:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.post(
                "/api/v1/ratify",
                json={"graph_intent_id": "abc123def456", "actor": "local"},
            )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "assent_record_not_found"


@pytest.mark.asyncio
async def test_ratify_endpoint_already_applied_returns_409(session_factory):
    record = await _proposed_record(session_factory)
    mcp = ApplyMCP()
    app, patches = _client(session_factory, mcp)

    with patches[0], patches[1]:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            first = await client.post(
                "/api/v1/ratify",
                json={
                    "graph_intent_id": record.graph_intent_id,
                    "actor": "local",
                },
            )
            second = await client.post(
                "/api/v1/ratify",
                json={
                    "graph_intent_id": record.graph_intent_id,
                    "actor": "local",
                },
            )

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "assent_illegal_state"


@pytest.mark.asyncio
async def test_ratify_endpoint_missing_graph_intent_id_returns_400(session_factory):
    mcp = ApplyMCP()
    app, patches = _client(session_factory, mcp)

    with patches[0], patches[1]:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.post(
                "/api/v1/ratify",
                json={"actor": "local"},
            )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"
