from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from mcp.types import TextContent, Tool, ToolAnnotations

from forge_bridge.console import _rate_limit
from forge_bridge.console._operation_front import run_operation_front
from forge_bridge.console.app import build_console_app
from forge_bridge.console.manifest_service import ManifestService
from forge_bridge.console.read_api import ConsoleReadAPI
from forge_bridge.store.assent_record_repo import AssentRecordRepo


pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    _rate_limit._reset_for_tests()
    yield
    _rate_limit._reset_for_tests()


def _create_reel_tool() -> Tool:
    return Tool(
        name="flame_create_reel",
        description="Create a Flame reel in a library or reel group.",
        annotations=ToolAnnotations(readOnlyHint=False),
        inputSchema={"type": "object", "properties": {}, "required": []},
    )


def _text(payload: dict) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps(payload))]


def _manifest(args: dict) -> dict:
    target_name = args.get("target_name") or "__default_workspace_library__"
    if target_name == "__default_workspace_library__":
        target_name = "Default Library"
    return {
        "type": "mutation_plan",
        "intent_parameters": {
            "reel_name": args["reel_name"],
            "target_type": args.get("target_type", "library"),
            "target_name": args.get("target_name"),
        },
        "resolved_plan": [{
            "identity": {
                "target_type": args.get("target_type", "library"),
                "target_name": target_name,
                "reel_name": args["reel_name"],
            },
            "payload": {
                "operation": "create_reel",
                "reel_name": args["reel_name"],
            },
        }],
        "originating_capability": "flame_create_reel",
        "apply_counterpart": {
            "tool": "flame_create_reel",
            "parameter_overrides": {"mode": "apply"},
        },
    }


class CreateReelMCP:
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    async def list_tools(self):
        return [_create_reel_tool()]

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        params = dict(arguments)
        if params.get("mode") == "apply":
            return _text({
                "created": True,
                "reel_name": params["reel_name"],
                "target_type": params.get("target_type", "library"),
                "target_name": "Default Library",
            })
        return _text(_manifest(params))


async def test_operation_front_create_reel_preview_persists_intent(session_factory):
    router = SimpleNamespace(
        acomplete=AsyncMock(return_value=json.dumps({
            "operation": "create_reel",
            "args": {"reel_name": "dailies"},
        })),
    )

    body = await run_operation_front(
        [{"role": "user", "content": "create a reel called dailies"}],
        router=router,
        session_factory=session_factory,
    )

    assert body["stop_reason"] == "preview_emitted"
    assert body["graph_intent_id"]
    preview = body["preview"]
    assert preview["summary"]["requires_ratification"] is True
    assert preview["summary"]["description"] == (
        "create reel 'dailies' in library 'default workspace library'"
    )
    assert preview["steps"][0]["tool_name"] == "flame_create_reel"
    assert preview["steps"][0]["args_preview"] == {
        "reel_name": "dailies",
        "target_type": "library",
        "target_name": "default workspace library",
    }

    async with session_factory() as session:
        repo = AssentRecordRepo(session)
        record = await repo.get_by_graph_intent_id(body["graph_intent_id"])
    assert record is not None
    assert record.status == "proposed"
    assert record.chain_steps[1] == "commit"
    assert "flame_create_reel" in record.chain_steps[0]
    assert "dailies" in record.chain_steps[0]


async def test_operation_front_missing_name_uses_clarify_channel(session_factory):
    router = SimpleNamespace(
        acomplete=AsyncMock(return_value=json.dumps({
            "clarify": "What should the new reel be called?",
        })),
    )

    body = await run_operation_front(
        [{"role": "user", "content": "create a reel"}],
        router=router,
        session_factory=session_factory,
    )

    assert body["stop_reason"] == "clarification_needed"
    assert "preview" not in body
    assert "graph_intent_id" not in body


async def test_unratified_operation_preview_does_not_call_flame(session_factory):
    router = SimpleNamespace(
        acomplete=AsyncMock(return_value=json.dumps({
            "operation": "create_reel",
            "args": {"reel_name": "dailies"},
        })),
    )
    mcp = CreateReelMCP()

    body = await run_operation_front(
        [{"role": "user", "content": "create a reel called dailies"}],
        router=router,
        session_factory=session_factory,
    )

    assert body["stop_reason"] == "preview_emitted"
    assert mcp.calls == []


async def test_ratified_operation_replay_applies_create_reel(session_factory):
    from forge_bridge.console._chat_compile import run_apply_branch

    router = SimpleNamespace(
        acomplete=AsyncMock(return_value=json.dumps({
            "operation": "create_reel",
            "args": {"reel_name": "dailies"},
        })),
    )
    preview = await run_operation_front(
        [{"role": "user", "content": "create a reel called dailies"}],
        router=router,
        session_factory=session_factory,
    )
    async with session_factory() as session:
        repo = AssentRecordRepo(session)
        await repo.ratify(preview["graph_intent_id"], actor="operator")
        await session.commit()

    mcp = CreateReelMCP()
    outcome = await run_apply_branch(
        graph_intent_id=preview["graph_intent_id"],
        session_factory=session_factory,
        tools=[_create_reel_tool()],
        mcp=mcp,
        request_id="req-create-reel",
        client_ip="127.0.0.1",
        started=10.0,
    )

    assert outcome.regime == "apply_complete"
    assert [(name, args.get("mode")) for name, args in mcp.calls] == [
        ("flame_create_reel", None),
        ("flame_create_reel", "verify"),
        ("flame_create_reel", "apply"),
    ]
    assert mcp.calls[-1][1]["reel_name"] == "dailies"
    assert outcome.chain_body["chain"][-1]["result"]["apply_result"]["created"] is True


async def test_operation_front_http_branch_returns_preview(session_factory):
    router = SimpleNamespace(
        acomplete=AsyncMock(return_value=json.dumps({
            "operation": "create_reel",
            "args": {"reel_name": "dailies"},
        })),
    )
    api = ConsoleReadAPI(
        execution_log=MagicMock(),
        manifest_service=ManifestService(),
        llm_router=router,
        session_factory=session_factory,
    )
    api._execution_log.snapshot.return_value = ([], 0)
    app = build_console_app(api, session_factory=session_factory)

    with patch("forge_bridge.mcp.server.mcp", CreateReelMCP()):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.post(
                "/api/v1/chat?operation_front=true",
                json={"messages": [{
                    "role": "user",
                    "content": "create a reel called dailies",
                }]},
            )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["stop_reason"] == "preview_emitted"
    assert body["preview"]["graph_intent_id"] == body["graph_intent_id"]
    assert body["preview"]["steps"][0]["args_preview"]["reel_name"] == "dailies"
