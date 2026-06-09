from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

from mcp.types import TextContent

from forge_bridge.console._planner_front import run_planner_front
from forge_bridge.console._vocab_digest import (
    READ_PLANNER_ROLE_NAMES,
    STATUS_ALIASES,
    planner_vocabulary_digest,
)
from forge_bridge.core.vocabulary import STANDARD_ROLES, Status


def test_planner_status_alias_digest_matches_status_parser():
    for alias, canonical in STATUS_ALIASES.items():
        assert Status.from_string(alias).value == canonical


def test_planner_vocab_digest_projects_standard_roles():
    digest = planner_vocabulary_digest()

    for name in READ_PLANNER_ROLE_NAMES:
        role = STANDARD_ROLES[name]
        assert f"{name}(" in digest
        assert role.aliases["role_class"] in digest

    assert "background(" not in digest


def test_planner_grounding_includes_first_party_vocabulary_block():
    router = SimpleNamespace(
        acomplete=AsyncMock(return_value=json.dumps({"clarify": "Which project?"})),
    )
    mcp = SimpleNamespace(
        call_tool=AsyncMock(return_value=[
            TextContent(
                type="text",
                text=json.dumps({
                    "projects": [
                        {"id": "proj-port", "name": "portofino"},
                    ],
                }),
            )
        ])
    )
    tools = [
        SimpleNamespace(
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
    ]

    result = run_planner_front(
        [{"role": "user", "content": "which shots are in review"}],
        router=router,
        mcp=mcp,
        tools=tools,
    )
    # Run the coroutine without adding pytest-asyncio as a dependency of this file.
    import asyncio

    body = asyncio.run(result)

    assert body["stop_reason"] == "clarification_needed"
    grounding = router.acomplete.await_args.args[0]
    assert "VOCABULARY:" in grounding
    assert "Project -> Sequence -> Shot/Asset -> Version -> Media" in grounding
    assert "review" in grounding
    assert "published->delivered" in grounding
    assert "primary(track" in grounding
    assert "forge_list_shots(project_id, status?)" in grounding
