from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from sqlalchemy.orm.attributes import flag_modified

from forge_bridge.store.assent_record_repo import AssentRecordRepo
from forge_bridge.store.models import DBEntity
from tests.console.test_pr30_chain import _text_block
from tests.integration.test_a2_ratify_apply_flow import _app, _manifest


class DriftMCP:
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    async def list_tools(self):
        from mcp.types import Tool

        return [
            Tool(
                name="emit_plan",
                description="test tool emit_plan",
                inputSchema={"type": "object", "properties": {}, "required": []},
            )
        ]

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        manifest = _manifest()
        if len(self.calls) == 2:
            manifest["resolved_plan"] = [
                {"identity": {"name": "shot010"}, "payload": {"drift": True}}
            ]
        return _text_block(json.dumps(manifest))


@pytest.mark.asyncio
async def test_a3_drift_invalidation_marks_assent_failed(session_factory):
    router = SimpleNamespace(
        compile_intent=AsyncMock(return_value=["emit_plan", "commit"]),
    )
    mcp = DriftMCP()
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
            graph_intent_id = preview_response.json()["preview"]["graph_intent_id"]

            async with session_factory() as session:
                repo = AssentRecordRepo(session)
                record = await repo.get_by_graph_intent_id(graph_intent_id)
                db_entity = await session.get(DBEntity, record.id)
                db_entity.attributes["chain_steps"] = ["emit_plan", "commit "]
                flag_modified(db_entity, "attributes")
                await session.commit()

            ratify_response = await client.post(
                "/api/v1/ratify",
                json={"graph_intent_id": graph_intent_id, "actor": "test"},
            )

    assert ratify_response.status_code == 400, ratify_response.text
    body = ratify_response.json()
    assert body["status"] == "error"
    assert body["stop_reason"] == "chain_aborted"
    assert body["graph_intent_id"] == graph_intent_id
    error = body["error"]
    assert error["code"] == "CHAIN_STEP_FAILED"
    assert error["step_index"] == 1
    original = error["original_error"]
    assert original["type"] == "PLAN_STATE_DRIFT"
    assert original["drift_count"] == 1
    assert original["first_drift_index"] == 0

    async with session_factory() as session:
        repo = AssentRecordRepo(session)
        failed = await repo.get_by_graph_intent_id(graph_intent_id)

    assert failed.status == "failed"
    assert failed.decided_by == "test"
    assert failed.apply_failure_reason == "drift_invalid"
    assert failed.apply_result["error"]["original_error"]["type"] == "PLAN_STATE_DRIFT"
    assert [name for name, _ in mcp.calls] == ["emit_plan", "emit_plan"]
