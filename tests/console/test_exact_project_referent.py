from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

from mcp.types import TextContent

from forge_bridge.console._planner_front import run_planner_front
from forge_bridge.console._project_referent import (
    ExactProjectReferent,
    resolve_exact_project_referent,
)


PROJECTS = [
    {"id": "proj-port", "name": "Portofino"},
    {"id": "proj-p36-a", "name": "P36 Summer"},
    {"id": "proj-p36-b", "name": "P36 Winter"},
    {"id": "proj-other", "name": "Project Molecule"},
]


def _projects_text(projects=PROJECTS) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps({"projects": projects}))]


def _published_plates_tool() -> SimpleNamespace:
    return SimpleNamespace(
        name="forge_list_published_plates",
        description="Forge: list published plates.",
        annotations=SimpleNamespace(readOnlyHint=True, title="List published plates"),
        inputSchema={
            "$defs": {"Input": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "shot_name": {"type": "string"},
                },
            }},
            "type": "object",
            "properties": {"params": {"$ref": "#/$defs/Input"}},
        },
    )


def test_exact_referent_is_casefolded_and_token_boundary_scoped():
    assert resolve_exact_project_referent(
        "latest plate for TST_020 in PORTOFINO?",
        PROJECTS,
    ) == ExactProjectReferent(id="proj-port", name="Portofino")
    assert resolve_exact_project_referent("work in port", PROJECTS) is None
    assert resolve_exact_project_referent("portofinoes", PROJECTS) is None


def test_exact_referent_prefers_longest_nested_full_name():
    projects = [
        {"id": "port", "name": "Portofino"},
        {"id": "test", "name": "Portofino Test"},
    ]

    assert resolve_exact_project_referent(
        "show Portofino Test plates",
        projects,
    ) == ExactProjectReferent(id="test", name="Portofino Test")


def test_exact_referent_keeps_duplicate_names_ambiguous():
    projects = [
        {"id": "a", "name": "Portofino"},
        {"id": "b", "name": " portofino "},
    ]

    assert resolve_exact_project_referent("shots in Portofino", projects) is None


def test_complex_read_sees_only_exact_project_and_binds_canonical_id():
    def route(prompt: str, **_kwargs) -> str:
        if "Tool results:" in prompt:
            return "The latest plate is v012."
        project_block = prompt.split("PROJECTS:\n", 1)[1].split("\n\nTOOLS:", 1)[0]
        visible_projects = json.loads(project_block)
        if len(visible_projects) != 1:
            return json.dumps({"clarify": "Which of the five projects?"})
        return json.dumps({
            "plan": [{
                "tool": "forge_list_published_plates",
                "args": {
                    "project_id": "model-selected-wrong-id",
                    "shot_name": "tst_020",
                },
            }],
            "filters": [],
            "aggregation": None,
            "presentation": None,
        })

    router = SimpleNamespace(acomplete=AsyncMock(side_effect=route))
    mcp = SimpleNamespace(call_tool=AsyncMock(side_effect=[
        _projects_text(),
        [TextContent(type="text", text=json.dumps({
            "plates": [{"shot_name": "tst_020", "version": 12}],
        }))],
    ]))

    body = asyncio.run(run_planner_front(
        [{
            "role": "user",
            "content": "what's the latest published plate for tst_020 in portofino",
        }],
        router=router,
        mcp=mcp,
        tools=[_published_plates_tool()],
    ))

    assert body["stop_reason"] == "planner_front"
    assert body["plan"] == [{
        "tool": "forge_list_published_plates",
        "args": {"project_id": "proj-port", "shot_name": "tst_020"},
    }]
    grounding = router.acomplete.await_args_list[0].args[0]
    assert 'EXACT_PROJECT_REFERENT:\n{"id": "proj-port", "name": "Portofino"}' in grounding
    assert '"proj-p36-a"' not in grounding
    assert mcp.call_tool.await_args_list[1].args == (
        "forge_list_published_plates",
        {"params": {"project_id": "proj-port", "shot_name": "tst_020"}},
    )


def test_no_exact_name_preserves_full_candidate_set_and_clarifies():
    router = SimpleNamespace(acomplete=AsyncMock(return_value=json.dumps({
        "clarify": "Which project do you mean: Portofino, P36 Summer, or P36 Winter?",
    })))
    mcp = SimpleNamespace(call_tool=AsyncMock(return_value=_projects_text()))

    body = asyncio.run(run_planner_front(
        [{"role": "user", "content": "what's the latest published plate?"}],
        router=router,
        mcp=mcp,
        tools=[_published_plates_tool()],
    ))

    assert body["stop_reason"] == "clarification_needed"
    grounding = router.acomplete.await_args.args[0]
    assert "EXACT_PROJECT_REFERENT" not in grounding
    assert all(project["id"] in grounding for project in PROJECTS)
    assert mcp.call_tool.await_count == 1
