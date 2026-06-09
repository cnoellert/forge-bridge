from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

from mcp.types import TextContent

from forge_bridge.console._planner_front import _PLANNER_SYSTEM, run_planner_front
from forge_bridge.console._vocab_digest import (
    READ_PLANNER_ROLE_NAMES,
    STATUS_ALIASES,
    planner_vocabulary_digest,
)
from forge_bridge.core.vocabulary import STANDARD_ROLES, Status


def _projects_text() -> list[TextContent]:
    return [
        TextContent(
            type="text",
            text=json.dumps({
                "projects": [
                    {"id": "proj-port", "name": "portofino"},
                ],
            }),
        )
    ]


def _list_shots_tool() -> SimpleNamespace:
    return SimpleNamespace(
        name="forge_list_shots",
        description="Forge: list shots.",
        annotations=SimpleNamespace(readOnlyHint=True, title="List shots"),
        inputSchema={
            "$defs": {
                "ListShotsInput": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string"},
                        "status": {"type": "string"},
                    },
                    "required": ["project_id"],
                },
            },
            "type": "object",
            "properties": {
                "params": {"$ref": "#/$defs/ListShotsInput"},
            },
            "required": ["params"],
        },
    )


def test_planner_status_alias_digest_matches_status_parser():
    for alias, canonical in STATUS_ALIASES.items():
        assert Status.from_string(alias).value == canonical


def test_planner_status_alias_digest_demotes_published_to_tool_language():
    digest = planner_vocabulary_digest()

    assert "published" not in STATUS_ALIASES
    assert "published->delivered" not in digest


def test_planner_vocab_digest_projects_standard_roles():
    digest = planner_vocabulary_digest()

    for name in READ_PLANNER_ROLE_NAMES:
        role = STANDARD_ROLES[name]
        assert f"{name}(" in digest
        assert role.aliases["role_class"] in digest

    assert "background(" not in digest


def test_planner_system_clarifies_unknown_or_ambiguous_predicates():
    assert "Filtering/selecting terms must be grounded before you plan" in (
        _PLANNER_SYSTEM
    )
    assert "Never silently drop an unknown filter term" in _PLANNER_SYSTEM
    assert "maps to more than one concept or layer" in _PLANNER_SYSTEM
    assert "If there is no filtering/selecting term, proceed without asking" in (
        _PLANNER_SYSTEM
    )


def test_planner_grounding_includes_first_party_vocabulary_block():
    router = SimpleNamespace(
        acomplete=AsyncMock(return_value=json.dumps({"clarify": "Which project?"})),
    )
    mcp = SimpleNamespace(
        call_tool=AsyncMock(return_value=_projects_text())
    )
    tools = [_list_shots_tool()]

    result = run_planner_front(
        [{"role": "user", "content": "which shots are in review"}],
        router=router,
        mcp=mcp,
        tools=tools,
    )

    body = asyncio.run(result)

    assert body["stop_reason"] == "clarification_needed"
    grounding = router.acomplete.await_args_list[0].args[0]
    assert "VOCABULARY:" in grounding
    assert "Project -> Sequence -> Shot/Asset -> Version -> Media" in grounding
    assert "unknown or ambiguous filter terms must clarify, not widen" in grounding
    assert "review" in grounding
    assert "published->delivered" not in grounding
    assert "primary(track" in grounding
    assert "forge_list_shots(project_id, status?)" in grounding


def test_planner_unknown_predicate_uses_clarify_channel_without_broad_read():
    router = SimpleNamespace(
        acomplete=AsyncMock(return_value=json.dumps({
            "clarify": (
                "I don't have a defined meaning for 'hero shots'. Do you mean "
                "approved shots, featured shots, or selected shots?"
            )
        })),
    )
    mcp = SimpleNamespace(call_tool=AsyncMock(return_value=_projects_text()))

    body = asyncio.run(run_planner_front(
        [{"role": "user", "content": "hero shots in portofino"}],
        router=router,
        mcp=mcp,
        tools=[_list_shots_tool()],
    ))

    assert body["stop_reason"] == "clarification_needed"
    assert "defined meaning for 'hero shots'" in body["final_text"]
    assert body["plan"] == []
    assert mcp.call_tool.await_count == 1
    assert mcp.call_tool.await_args_list[0].args[0] == "forge_list_projects"


def test_planner_no_qualifier_regression_still_plans_list_shots():
    router = SimpleNamespace(
        acomplete=AsyncMock(side_effect=[
            json.dumps({
                "plan": [{
                    "tool": "forge_list_shots",
                    "args": {"project_id": "proj-port"},
                }]
            }),
            "There are no shots in the fixture.",
        ]),
    )
    mcp = SimpleNamespace()
    mcp.call_tool = AsyncMock(side_effect=[
        _projects_text(),
        [
            TextContent(
                type="text",
                text=json.dumps({"project_id": "proj-port", "shots": []}),
            )
        ],
    ])

    body = asyncio.run(run_planner_front(
        [{"role": "user", "content": "show me the shots in portofino"}],
        router=router,
        mcp=mcp,
        tools=[_list_shots_tool()],
    ))

    assert body["stop_reason"] == "planner_front"
    assert body["plan"] == [{
        "tool": "forge_list_shots",
        "args": {"project_id": "proj-port"},
    }]
    assert body["chain"][0]["step"].startswith("forge_list_shots(")


def test_planner_grounding_exposes_published_as_tool_purpose_not_status_alias():
    router = SimpleNamespace(
        acomplete=AsyncMock(return_value=json.dumps({
            "plan": [{
                "tool": "forge_list_published_plates",
                "args": {"project_id": "proj-port"},
            }]
        })),
    )
    mcp = SimpleNamespace()
    mcp.call_tool = AsyncMock(side_effect=[
        _projects_text(),
        [
            TextContent(
                type="text",
                text=json.dumps({"project_id": "proj-port", "plates": []}),
            )
        ],
    ])
    tools = [
        SimpleNamespace(
            name="forge_list_published_plates",
            description="Forge: list video plates in the publish registry.",
            annotations=SimpleNamespace(
                readOnlyHint=True,
                title="List published video plates from the forge-bridge registry",
            ),
            inputSchema={
                "$defs": {
                    "ListPublishedPlatesInput": {
                        "type": "object",
                        "properties": {
                            "project_id": {"type": "string"},
                            "sequence_name": {"type": "string"},
                        },
                    },
                },
                "type": "object",
                "properties": {
                    "params": {"$ref": "#/$defs/ListPublishedPlatesInput"},
                },
            },
        )
    ]

    body = asyncio.run(run_planner_front(
        [{"role": "user", "content": "what's published on portofino"}],
        router=router,
        mcp=mcp,
        tools=tools,
    ))

    grounding = router.acomplete.await_args_list[0].args[0]
    assert "published->delivered" not in grounding
    assert "forge_list_published_plates(project_id?, sequence_name?)" in grounding
    assert body["plan"] == [{
        "tool": "forge_list_published_plates",
        "args": {"project_id": "proj-port"},
    }]
    assert body["chain"][0]["step"].startswith("forge_list_published_plates(")
