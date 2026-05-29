"""A.2 D9 — end-to-end propose -> ratify -> apply flow."""
from __future__ import annotations

import json
from types import SimpleNamespace
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


def _tool(name: str):
    from mcp.types import Tool

    return Tool(
        name=name,
        description=f"test tool {name}",
        inputSchema={"type": "object", "properties": {}, "required": []},
    )


def _manifest() -> dict:
    return {
        "type": "mutation_plan",
        "intent_parameters": {"request": "demo"},
        "resolved_plan": [{"identity": {"name": "shot010"}, "payload": {}}],
        "originating_capability": "emit_plan",
        "apply_counterpart": {
            "tool": "emit_plan",
            "parameter_overrides": {"dry_run": False},
        },
    }


class RatifyApplyMCP:
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    async def list_tools(self):
        return [_tool("emit_plan")]

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        if len(self.calls) <= 2:
            return _text_block(json.dumps(_manifest()))
        return _text_block(json.dumps({"applied": 1}))


async def _passthrough_filter(tools):
    return tools


def _app(session_factory, router, mcp):
    api = ConsoleReadAPI(
        execution_log=MagicMock(),
        manifest_service=ManifestService(),
        llm_router=router,
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


@pytest.mark.asyncio
async def test_a2_preview_ratify_apply_happy_path(session_factory):
    router = SimpleNamespace(
        compile_intent=AsyncMock(return_value=["emit_plan", "commit"]),
    )
    mcp = RatifyApplyMCP()
    app, patches = _app(session_factory, router, mcp)

    with patches[0], patches[1]:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            preview_response = await client.post(
                "/api/v1/chat",
                json={"messages": [{
                    "role": "user",
                    "content": "rename demo shots and commit",
                }]},
            )

            assert preview_response.status_code == 200, preview_response.text
            preview_body = preview_response.json()
            preview = preview_body["preview"]
            graph_intent_id = preview["graph_intent_id"]
            assert preview_body["stop_reason"] == "preview_emitted"
            assert preview["summary"]["requires_ratification"] is True

            ratify_response = await client.post(
                "/api/v1/ratify",
                json={"graph_intent_id": graph_intent_id, "actor": "operator"},
            )

    assert ratify_response.status_code == 200, ratify_response.text
    ratify_body = ratify_response.json()
    assert ratify_body["apply_complete"]["graph_intent_id"] == graph_intent_id
    assert ratify_body["apply_complete"]["chain"]["status"] == "success"

    async with session_factory() as session:
        repo = AssentRecordRepo(session)
        record = await repo.get_by_graph_intent_id(graph_intent_id)

    assert record is not None
    assert record.status == "applied"
    assert record.decided_by == "operator"
    assert record.chain_steps == ["emit_plan", "commit"]
    assert record.apply_result["status"] == "success"
    router.compile_intent.assert_awaited_once()
    assert [name for name, _ in mcp.calls] == ["emit_plan", "emit_plan", "emit_plan"]
