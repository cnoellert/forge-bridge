"""CR.2 conversational recovery locks.

Recoverable ambiguity should become a deterministic continuation prompt,
not a raw terminal error. These tests intentionally stay model-free: the
recovery layer only normalizes substrate-held candidates and next-turn
candidate matching.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

from forge_bridge.console import _rate_limit
from forge_bridge.console._memory import _MEMORY
from forge_bridge.console._recovery import (
    recovery_context_from_messages,
    recovery_params_from_messages,
    referent_clarification,
    response_body,
    tool_action_label,
    tool_clarification,
)
from forge_bridge.console.app import build_console_app
from forge_bridge.console.manifest_service import ManifestService
from forge_bridge.console.read_api import ConsoleReadAPI


@pytest.fixture(autouse=True)
def _reset_state():
    _rate_limit._reset_for_tests()
    _MEMORY.clear()
    yield
    _MEMORY.clear()
    _rate_limit._reset_for_tests()


def test_cr2_tool_label_prefers_runtime_annotation_title():
    tool = SimpleNamespace(
        name="forge_get_shot",
        description="forge_get_shot: Get the shot by id.",
        annotations=SimpleNamespace(title="Get shot details"),
    )

    assert tool_action_label(tool) == "Get shot details"


def test_cr2_tool_clarification_uses_operator_labels_not_tool_ids():
    tools = [
        SimpleNamespace(
            name="forge_get_shot",
            description="forge_get_shot: Get the shot by id.",
            annotations=SimpleNamespace(title="Get shot details"),
        ),
        SimpleNamespace(
            name="flame_get_sequence_segments",
            description="flame_get_sequence_segments: Get visible timeline segments.",
            annotations=SimpleNamespace(title="Get timeline segments"),
        ),
    ]

    clarification = tool_clarification(tools)

    rendered = json.dumps(clarification)
    assert clarification["kind"] == "tool"
    assert clarification["candidates"] == [
        {"label": "Get shot details"},
        {"label": "Get timeline segments"},
    ]
    assert "forge_get_shot" not in rendered
    assert "flame_get_sequence_segments" not in rendered


def test_cr2_next_turn_reentry_resolves_held_candidate_prefix():
    prior = referent_clarification(
        key="project_id",
        candidates=[
            {"id": "proj-portofino", "name": "013_13_13_2026_2_1_portofino"},
            {"id": "proj-backup", "name": "Backup"},
        ],
    )
    messages = [
        {"role": "user", "content": "forge fetch versions"},
        {
            "role": "assistant",
            "content": prior["prompt"],
            "clarification_needed": prior,
        },
        {"role": "user", "content": "013_13"},
    ]

    assert recovery_params_from_messages(messages, "013_13") == {
        "project_id": "proj-portofino"
    }
    context = recovery_context_from_messages(messages, "013_13")
    assert context is not None
    assert context["intent_text"] == "forge fetch versions"


def test_cr2_next_turn_reentry_fails_closed_on_ambiguous_partial():
    prior = referent_clarification(
        key="project_id",
        candidates=[
            {"id": "proj-alpha", "name": "Project Alpha"},
            {"id": "proj-alpha-backup", "name": "Project Alpha Backup"},
        ],
    )
    messages = [
        {"role": "user", "content": "forge fetch versions"},
        {
            "role": "assistant",
            "content": prior["prompt"],
            "clarification_needed": prior,
        },
        {"role": "user", "content": "Alpha"},
    ]

    assert recovery_params_from_messages(messages, "Alpha") == {}


RECOVERY_CORPUS = [
    pytest.param(
        "flame-up/multiple-projects",
        referent_clarification(
            key="project_id",
            candidates=[
                {"id": "project-a", "name": "Project A"},
                {"id": "project-b", "name": "Project B"},
            ],
        ),
        id="multiple-projects",
    ),
    pytest.param(
        "flame-down/unresolved-sequence",
        referent_clarification(key="sequence_name", candidates=[]),
        id="unresolved-sequence",
    ),
    pytest.param(
        "ambiguous-tool-selection",
        tool_clarification([
            SimpleNamespace(
                name="forge_get_shot",
                description="forge_get_shot: Get the shot by id.",
                annotations=SimpleNamespace(title="Get shot details"),
            ),
            SimpleNamespace(
                name="forge_list_shots",
                description="forge_list_shots: List shots.",
                annotations=SimpleNamespace(title="List shots"),
            ),
        ]),
        id="ambiguous-tool",
    ),
]


@pytest.mark.parametrize(("condition", "clarification"), RECOVERY_CORPUS)
def test_cr2_corpus_recoverable_cases_are_continuations(condition, clarification):
    body = response_body(
        request_id=f"req-{condition}",
        clarification=clarification,
        messages=[{"role": "user", "content": "recover this"}],
    )

    rendered = json.dumps(body)
    assert body["status"] == "clarification_needed"
    assert body["stop_reason"] == "clarification_needed"
    assert body["messages"][-1]["content"] == clarification["prompt"]
    assert "MULTIPLE_PROJECTS" not in rendered
    assert "UNRESOLVED_REQUIRED_PARAM" not in rendered
    assert "tool_selection_ambiguous" not in rendered


def _tool(name: str, required: list[str] | None = None):
    from mcp.types import Tool, ToolAnnotations

    required = required or []
    properties = {key: {"type": "string"} for key in required}
    return Tool(
        name=name,
        description=f"{name} description",
        annotations=ToolAnnotations(
            readOnlyHint=True,
            title=name.replace("_", " ").title(),
        ),
        inputSchema={
            "type": "object",
            "properties": properties,
            "required": required,
        },
    )


def _build_reentry_app(project_names: list[str]):
    from mcp.types import TextContent

    tools = [
        _tool("forge_list_shots", ["project_id"]),
        _tool("flame_alpha"),
        _tool("synth_gamma"),
    ]
    router = MagicMock()
    router.compile_intent = AsyncMock(return_value=[
        "forge_manifest_read",
        "format_result",
    ])
    router.complete_with_tools = AsyncMock()
    router.acomplete = AsyncMock(return_value="Shot A001 is available.")
    router.system_prompt = "base"

    log = MagicMock()
    log.snapshot.return_value = ([], 0)
    api = ConsoleReadAPI(
        execution_log=log,
        manifest_service=ManifestService(),
        llm_router=router,
    )
    app = build_console_app(api)

    projects = [
        {"id": f"proj-{index}", "name": name}
        for index, name in enumerate(project_names)
    ]

    async def fake_call_tool(name, arguments):
        if name == "forge_list_projects":
            return [TextContent(
                type="text",
                text=json.dumps({
                    "count": len(projects),
                    "projects": projects,
                }),
            )]
        if name == "forge_list_shots":
            return [TextContent(
                type="text",
                text=json.dumps({
                    "count": 1,
                    "shots": [{"id": "shot-001", "name": "A001"}],
                    "arguments": arguments,
                }),
            )]
        return [TextContent(type="text", text=json.dumps({"ok": True}))]

    list_patch = patch(
        "forge_bridge.mcp.server.mcp.list_tools",
        new=AsyncMock(return_value=tools),
    )
    backends_patch = patch(
        "forge_bridge.console.handlers.filter_tools_by_reachable_backends",
        side_effect=lambda tools, **_: tools,
    )
    call_patch = patch(
        "forge_bridge.mcp.server.mcp.call_tool",
        new=AsyncMock(side_effect=fake_call_tool),
    )
    return app, router, list_patch, backends_patch, call_patch


@pytest.mark.parametrize(
    "reply",
    [
        "013_13_13_2026_2_1_portofino",
        "013_13",
        "portofino",
    ],
)
def test_cr2_reentry_replays_prior_intent_with_resolved_referent(reply):
    app, router, list_patch, backends_patch, call_patch = _build_reentry_app([
        "013_13_13_2026_2_1_portofino",
        "Backup",
    ])

    with list_patch, backends_patch, call_patch as call_mock:
        client = TestClient(app)
        first = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "list shots"}]},
        )
        assert first.status_code == 200, first.text
        first_body = first.json()
        assert first_body["stop_reason"] == "clarification_needed"
        assert "clarification_needed" in first_body["messages"][-1]

        second = client.post(
            "/api/v1/chat",
            json={"messages": first_body["messages"] + [
                {"role": "user", "content": reply},
            ]},
        )

    assert second.status_code == 200, second.text
    body = second.json()
    assert body["stop_reason"] == "tool_forced"
    assert body["tool_forced"] is True
    assert body["final_text"] == "Shot A001 is available."
    assert body["tool_trace"][0]["tool_name"] == "forge_list_shots"
    assert body["tool_trace"][0]["arguments"] == {"project_id": "proj-0"}
    assert "clarification_needed" not in body
    router.compile_intent.assert_not_called()
    assert _MEMORY.get("project_id") is None
    assert [
        call.args[0]
        for call in call_mock.await_args_list
    ] == ["forge_list_projects", "forge_list_shots"]


def test_cr2_reentry_ambiguous_reply_stays_clarified_without_compile():
    app, router, list_patch, backends_patch, call_patch = _build_reentry_app([
        "Project Alpha",
        "Project Alpha Backup",
    ])

    with list_patch, backends_patch, call_patch:
        client = TestClient(app)
        first = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "list shots"}]},
        )
        first_body = first.json()
        second = client.post(
            "/api/v1/chat",
            json={"messages": first_body["messages"] + [
                {"role": "user", "content": "Alpha"},
            ]},
        )

    assert second.status_code == 200, second.text
    body = second.json()
    assert body["stop_reason"] == "clarification_needed"
    assert body["clarification_needed"]["resolve_hint"]["key"] == "project_id"
    router.compile_intent.assert_not_called()


def test_cr2_reentry_current_explicit_param_wins_over_recovered_candidate():
    app, _router, list_patch, backends_patch, call_patch = _build_reentry_app([
        "013_13_13_2026_2_1_portofino",
        "Backup",
    ])

    with list_patch, backends_patch, call_patch:
        client = TestClient(app)
        first = client.post(
            "/api/v1/chat",
            json={"messages": [{"role": "user", "content": "list shots"}]},
        )
        first_body = first.json()
        second = client.post(
            "/api/v1/chat",
            json={"messages": first_body["messages"] + [
                {"role": "user", "content": (
                    "project_id=11111111-1111-1111-1111-111111111111"
                )},
            ]},
        )

    assert second.status_code == 200, second.text
    assert second.json()["tool_trace"][0]["arguments"] == {
        "project_id": "11111111-1111-1111-1111-111111111111"
    }


def test_cr2_console_client_preserves_clarification_metadata_on_wire():
    from importlib.resources import files

    source = (
        files("forge_bridge")
        / "console"
        / "static"
        / "forge-chat.js"
    ).read_text(encoding="utf-8")

    assert "out.clarification_needed = m.clarification_needed" in source
    assert "clarification_needed: m.clarification_needed" in source
