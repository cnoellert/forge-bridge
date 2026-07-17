"""Project-list store health evidence at the state and MCP boundaries."""

from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from forge_bridge.server.protocol import project_list


@pytest.mark.asyncio
async def test_project_list_attests_to_successful_postgres_read(monkeypatch):
    from forge_bridge.server import router as router_module

    class ProjectRepo:
        def __init__(self, session):
            self.session = session

        async def list_all(self):
            return []

    @asynccontextmanager
    async def session_scope():
        yield object()

    monkeypatch.setattr(router_module, "ProjectRepo", ProjectRepo)
    monkeypatch.setattr(router_module, "get_session", session_scope)

    router = router_module.Router(MagicMock(), MagicMock())
    client = SimpleNamespace(client_name="test", session_id=uuid.uuid4())
    response = await router._handle_project_list(project_list(), client)

    assert response["result"] == {
        "projects": [],
        "store_health": {
            "status": "healthy",
            "source": "postgres",
            "read": "project.list",
        },
    }


class _ProjectClient:
    def __init__(self, result):
        self.result = result
        self.session_id = "session-1"

    async def request(self, _message):
        return self.result


@pytest.mark.asyncio
async def test_mcp_list_projects_preserves_store_health_evidence(monkeypatch):
    from forge_bridge.mcp import tools

    marker = {
        "status": "healthy",
        "source": "postgres",
        "read": "project.list",
    }
    monkeypatch.setattr(
        tools,
        "_client",
        lambda: _ProjectClient({"projects": [], "store_health": marker}),
    )

    payload = json.loads(await tools.list_projects())

    assert payload == {"count": 0, "projects": [], "store_health": marker}


@pytest.mark.asyncio
async def test_mcp_list_projects_rejects_unproven_empty_result(monkeypatch):
    from forge_bridge.mcp import tools

    monkeypatch.setattr(
        tools,
        "_client",
        lambda: _ProjectClient({"projects": []}),
    )

    payload = json.loads(await tools.list_projects())

    assert payload["code"] == "STORE_UNAVAILABLE"
    assert "healthy store marker" in payload["error"]
    assert "projects" not in payload


@pytest.mark.asyncio
async def test_mcp_list_projects_rejects_missing_projects_list(monkeypatch):
    from forge_bridge.mcp import tools

    monkeypatch.setattr(
        tools,
        "_client",
        lambda: _ProjectClient({
            "store_health": {"status": "healthy", "source": "postgres"},
        }),
    )

    payload = json.loads(await tools.list_projects())

    assert payload["code"] == "STORE_UNAVAILABLE"
    assert "no projects list" in payload["error"]
