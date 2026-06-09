from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from mcp.types import TextContent, Tool, ToolAnnotations

from forge_bridge.console import _rate_limit
from forge_bridge.console._operation_front import (
    _OPERATION_SYSTEM,
    run_operation_front,
    validate_required_operation_args,
)
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
    return _operation_tool("flame_create_reel")


def _operation_tool(name: str) -> Tool:
    return Tool(
        name=name,
        description=f"Host-mutating operation tool {name}.",
        annotations=ToolAnnotations(readOnlyHint=False),
        inputSchema={"type": "object", "properties": {}, "required": []},
    )


def _text(payload: dict) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps(payload))]


async def _assent_count(session_factory) -> int:
    from sqlalchemy import select
    from forge_bridge.store.models import DBEntity

    async with session_factory() as session:
        result = await session.execute(
            select(DBEntity).where(DBEntity.entity_type == "assent_record")
        )
        return len(result.scalars().all())


def _operation_from_tool(name: str) -> str:
    return name.removeprefix("flame_")


def _required_name_key(operation: str) -> str:
    return {
        "create_reel": "reel_name",
        "create_reel_group": "reel_group_name",
        "create_library": "library_name",
    }[operation]


def _manifest(args: dict, *, tool_name: str = "flame_create_reel") -> dict:
    operation = _operation_from_tool(tool_name)
    name_key = _required_name_key(operation)
    name_value = args[name_key]
    target_type = args.get("target_type") or {
        "create_reel": "library",
        "create_reel_group": "desktop",
        "create_library": "workspace",
    }[operation]
    target_name = args.get("target_name") or "__default_workspace_library__"
    if target_name == "__default_workspace_library__":
        target_name = "Default Library"
    return {
        "type": "mutation_plan",
        "intent_parameters": {
            name_key: name_value,
            "target_type": target_type,
            "target_name": args.get("target_name"),
        },
        "resolved_plan": [{
            "identity": {
                "target_type": target_type,
                "target_name": target_name,
                name_key: name_value,
            },
            "payload": {
                "operation": operation,
                name_key: name_value,
            },
        }],
        "originating_capability": tool_name,
        "apply_counterpart": {
            "tool": tool_name,
            "parameter_overrides": {"mode": "apply"},
        },
    }


class CreateReelMCP:
    def __init__(self, *, tools: list[str] | None = None, fail_apply: bool = False):
        self.calls: list[tuple[str, dict]] = []
        self.tool_names = tools or ["flame_create_reel"]
        self.fail_apply = fail_apply
        self.created: list[dict] = []

    async def list_tools(self):
        return [_operation_tool(name) for name in self.tool_names]

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        params = dict(arguments)
        if params.get("mode") == "apply":
            if self.fail_apply:
                return _text({
                    "drift": True,
                    "drift_count": 1,
                    "first_drift_index": 0,
                    "message": "Plan/state drift detected during apply.",
                })
            operation = _operation_from_tool(name)
            name_key = _required_name_key(operation)
            created = {
                "created": True,
                name_key: params[name_key],
                "target_type": params.get("target_type", "library"),
                "target_name": "Default Library",
            }
            self.created.append(created)
            return _text(created)
        return _text(_manifest(params, tool_name=name))


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
    assert await _assent_count(session_factory) == 1


@pytest.mark.parametrize(
    ("operation", "name_key", "name_value", "tool_name", "description"),
    [
        (
            "create_reel_group",
            "reel_group_name",
            "client_review",
            "flame_create_reel_group",
            "create reel group 'client_review' on desktop 'current desktop'",
        ),
        (
            "create_library",
            "library_name",
            "plates",
            "flame_create_library",
            "create library 'plates' in workspace 'current workspace'",
        ),
    ],
)
async def test_operation_front_safe_grafts_preview_and_persist_intent(
    session_factory,
    operation,
    name_key,
    name_value,
    tool_name,
    description,
):
    router = SimpleNamespace(
        acomplete=AsyncMock(return_value=json.dumps({
            "operation": operation,
            "args": {name_key: name_value},
        })),
    )

    body = await run_operation_front(
        [{"role": "user", "content": f"create {operation} called {name_value}"}],
        router=router,
        session_factory=session_factory,
    )

    assert body["stop_reason"] == "preview_emitted"
    assert body["graph_intent_id"]
    preview = body["preview"]
    assert preview["summary"]["operation"] == operation
    assert preview["summary"]["description"] == description
    assert preview["steps"][0]["tool_name"] == tool_name
    assert preview["steps"][0]["args_preview"][name_key] == name_value

    async with session_factory() as session:
        repo = AssentRecordRepo(session)
        record = await repo.get_by_graph_intent_id(body["graph_intent_id"])
    assert record is not None
    assert record.status == "proposed"
    assert record.chain_steps[1] == "commit"
    assert tool_name in record.chain_steps[0]
    assert name_value in record.chain_steps[0]


async def test_operation_front_prompt_uses_concrete_example_not_name_placeholder():
    assert '"reel_name": "dailies"' in _OPERATION_SYSTEM
    assert '"reel_group_name": "client"' in _OPERATION_SYSTEM
    assert '"library_name": "plates"' in _OPERATION_SYSTEM
    assert '"reel_name": "<name>"' not in _OPERATION_SYSTEM
    assert "Never output a literal placeholder" in _OPERATION_SYSTEM


async def test_required_operation_arg_validator_rejects_empty_and_placeholder():
    required = ("reel_name",)

    assert validate_required_operation_args({"reel_name": "dailies"}, required) is None
    assert validate_required_operation_args({"reel_name": ""}, required) == "reel_name"
    assert validate_required_operation_args({"reel_name": "   "}, required) == "reel_name"
    assert validate_required_operation_args({"reel_name": "<name>"}, required) == "reel_name"
    assert validate_required_operation_args({"reel_name": "<reel_name>"}, required) == "reel_name"
    assert validate_required_operation_args({"reel_name": "<anything>"}, required) == "reel_name"


@pytest.mark.parametrize(
    ("required", "valid_key", "valid_value"),
    [
        (("reel_name",), "reel_name", "dailies"),
        (("reel_group_name",), "reel_group_name", "client"),
        (("library_name",), "library_name", "plates"),
    ],
)
async def test_required_operation_arg_validator_generalizes_unchanged(
    required,
    valid_key,
    valid_value,
):
    assert validate_required_operation_args({valid_key: valid_value}, required) is None
    assert validate_required_operation_args({valid_key: "<name>"}, required) == valid_key
    assert validate_required_operation_args({valid_key: ""}, required) == valid_key


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
    assert await _assent_count(session_factory) == 0


@pytest.mark.parametrize("bad_value", ["", "   ", "<name>", "<reel_name>"])
async def test_operation_front_placeholder_required_arg_clarifies_before_persist(
    session_factory,
    bad_value,
):
    router = SimpleNamespace(
        acomplete=AsyncMock(return_value=json.dumps({
            "operation": "create_reel",
            "args": {"reel_name": bad_value},
        })),
    )

    body = await run_operation_front(
        [{"role": "user", "content": "create a reel"}],
        router=router,
        session_factory=session_factory,
    )

    assert body["stop_reason"] == "clarification_needed"
    assert "What should the new reel be called?" == body["final_text"]
    assert "preview" not in body
    assert "graph_intent_id" not in body
    assert "<name>" not in json.dumps(body)
    assert await _assent_count(session_factory) == 0


@pytest.mark.parametrize(
    ("operation", "name_key", "clarify"),
    [
        ("create_reel_group", "reel_group_name", "What should the new reel group be called?"),
        ("create_library", "library_name", "What should the new library be called?"),
    ],
)
@pytest.mark.parametrize("bad_value", ["", "   ", "<name>", "<object_name>"])
async def test_operation_front_safe_graft_placeholder_args_clarify_before_persist(
    session_factory,
    operation,
    name_key,
    clarify,
    bad_value,
):
    router = SimpleNamespace(
        acomplete=AsyncMock(return_value=json.dumps({
            "operation": operation,
            "args": {name_key: bad_value},
        })),
    )

    body = await run_operation_front(
        [{"role": "user", "content": f"create {operation}"}],
        router=router,
        session_factory=session_factory,
    )

    assert body["stop_reason"] == "clarification_needed"
    assert clarify == body["final_text"]
    assert "preview" not in body
    assert "graph_intent_id" not in body
    assert "<name>" not in json.dumps(body)
    assert await _assent_count(session_factory) == 0


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


@pytest.mark.parametrize(
    ("operation", "name_key", "name_value", "tool_name"),
    [
        ("create_reel_group", "reel_group_name", "client_review", "flame_create_reel_group"),
        ("create_library", "library_name", "plates", "flame_create_library"),
    ],
)
async def test_ratified_operation_replay_applies_safe_grafts(
    session_factory,
    operation,
    name_key,
    name_value,
    tool_name,
):
    from forge_bridge.console._chat_compile import run_apply_branch

    router = SimpleNamespace(
        acomplete=AsyncMock(return_value=json.dumps({
            "operation": operation,
            "args": {name_key: name_value},
        })),
    )
    preview = await run_operation_front(
        [{"role": "user", "content": f"create {operation} called {name_value}"}],
        router=router,
        session_factory=session_factory,
    )
    async with session_factory() as session:
        repo = AssentRecordRepo(session)
        await repo.ratify(preview["graph_intent_id"], actor="operator")
        await session.commit()

    mcp = CreateReelMCP(tools=[tool_name])
    outcome = await run_apply_branch(
        graph_intent_id=preview["graph_intent_id"],
        session_factory=session_factory,
        tools=[_operation_tool(tool_name)],
        mcp=mcp,
        request_id=f"req-{operation}",
        client_ip="127.0.0.1",
        started=10.0,
    )

    assert outcome.regime == "apply_complete"
    assert [(name, args.get("mode")) for name, args in mcp.calls] == [
        (tool_name, None),
        (tool_name, "verify"),
        (tool_name, "apply"),
    ]
    assert mcp.calls[-1][1][name_key] == name_value
    assert outcome.chain_body["chain"][-1]["result"]["apply_result"]["created"] is True


async def test_apply_failure_probe_marks_assent_failed_without_partial_mutation(
    session_factory,
):
    from forge_bridge.console._chat_compile import run_apply_branch

    router = SimpleNamespace(
        acomplete=AsyncMock(return_value=json.dumps({
            "operation": "create_reel",
            "args": {
                "reel_name": "bad_target_probe",
                "target_type": "reel_group",
                "target_name": "does_not_exist",
            },
        })),
    )
    preview = await run_operation_front(
        [{"role": "user", "content": "create a reel in missing reel group"}],
        router=router,
        session_factory=session_factory,
    )
    async with session_factory() as session:
        repo = AssentRecordRepo(session)
        await repo.ratify(preview["graph_intent_id"], actor="operator")
        await session.commit()

    mcp = CreateReelMCP(fail_apply=True)
    outcome = await run_apply_branch(
        graph_intent_id=preview["graph_intent_id"],
        session_factory=session_factory,
        tools=[_create_reel_tool()],
        mcp=mcp,
        request_id="req-create-reel-failure",
        client_ip="127.0.0.1",
        started=10.0,
    )

    assert outcome.regime == "chain_aborted"
    assert outcome.assent_record["status"] == "failed"
    assert outcome.assent_record["apply_failure_reason"] == "drift_invalid"
    assert mcp.created == []


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
