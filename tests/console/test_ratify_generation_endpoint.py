"""POST /api/v1/ratify-generation + MCP ratify tool tests (#146)."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import httpx
import pytest

from forge_bridge.console import _rate_limit
from forge_bridge.console.app import build_console_app
from forge_bridge.console.manifest_service import ManifestService
from forge_bridge.console.read_api import ConsoleReadAPI
from forge_bridge.mcp.tools import (
    RatifyGenerationGrantInput,
    _ratify_generation_grant_impl,
)
from forge_bridge.store.generation_grant_repo import GenerationGrantRepo

_TRIPLE = {"surface": "higgsfield-api", "path": "video-v1", "revision": "1"}


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    _rate_limit._reset_for_tests()
    yield
    _rate_limit._reset_for_tests()


def _app(session_factory):
    api = ConsoleReadAPI(
        execution_log=MagicMock(),
        manifest_service=ManifestService(),
        llm_router=MagicMock(),
        session_factory=session_factory,
    )
    api._execution_log.snapshot.return_value = ([], 0)
    return build_console_app(api, session_factory=session_factory)


async def _proposed(session_factory) -> str:
    async with session_factory() as session:
        grant = await GenerationGrantRepo(session).propose(
            operator_id="generate_video_from_image",
            backend_identity_triple=_TRIPLE,
            estimated_cost={"currency": "USD", "amount": 1.5},
            run_kind="generation",
        )
        await session.commit()
        return grant.grant_id


async def test_endpoint_ratifies_and_returns_to_dict(session_factory):
    grant_id = await _proposed(session_factory)
    app = _app(session_factory)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/api/v1/ratify-generation",
            content=json.dumps({"grant_id": grant_id, "actor": "cnoellert"}),
        )

    assert response.status_code == 200, response.text
    body = response.json()
    # Canonical grant.to_dict() shape returned directly (NO apply wrapper).
    assert body["grant_id"] == grant_id
    assert body["entity_type"] == "generation_grant"
    assert body["status"] == "ratified"
    assert body["decided_by"] == "cnoellert"
    assert body["estimated_cost"] == {"currency": "USD", "amount": 1.5}
    # Pure transition — nothing applied.
    assert "apply_complete" not in body
    assert "apply_result" not in body

    # And the store reflects the ratified transition.
    async with session_factory() as session:
        grant = await GenerationGrantRepo(session).get_by_grant_id(grant_id)
        assert grant.status == "ratified"


async def test_endpoint_unknown_grant_returns_404(session_factory):
    app = _app(session_factory)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/api/v1/ratify-generation",
            content=json.dumps({"grant_id": "ffffffffffff", "actor": "x"}),
        )
    assert response.status_code == 404


async def test_endpoint_bad_grant_id_returns_400(session_factory):
    app = _app(session_factory)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/api/v1/ratify-generation",
            content=json.dumps({"grant_id": "NOT-HEX", "actor": "x"}),
        )
    assert response.status_code == 400


async def test_mcp_tool_ratifies(session_factory):
    grant_id = await _proposed(session_factory)
    out = await _ratify_generation_grant_impl(
        RatifyGenerationGrantInput(grant_id=grant_id, actor="cnoellert"),
        session_factory,
    )
    body = json.loads(out)
    # _envelope_json wraps the canonical grant.to_dict() under "data".
    data = body.get("data", body)
    assert data["grant_id"] == grant_id
    assert data["status"] == "ratified"

    async with session_factory() as session:
        grant = await GenerationGrantRepo(session).get_by_grant_id(grant_id)
        assert grant.status == "ratified"


async def test_mcp_tool_unknown_grant_errors(session_factory):
    out = await _ratify_generation_grant_impl(
        RatifyGenerationGrantInput(grant_id="ffffffffffff", actor="x"),
        session_factory,
    )
    body = json.loads(out)
    assert body["error"]["code"] == "grant_not_found"
