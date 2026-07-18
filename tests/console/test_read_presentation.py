from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

from mcp.types import TextContent

from forge_bridge.console._planner_front import run_planner_front
from forge_bridge.console._read_presentation import (
    GroundedListPresentation,
    ground_read_presentation,
    render_read_presentation,
)


def _declaration(**overrides):
    value = {
        "kind": "list",
        "entity": "shot",
        "field": "name",
        "scope": "all",
    }
    value.update(overrides)
    return value


def _projects_text() -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps({
        "projects": [{"id": "proj-port", "name": "portofino"}],
    }))]


def _list_shots_tool() -> SimpleNamespace:
    return SimpleNamespace(
        name="forge_list_shots",
        description="Forge: list shots.",
        annotations=SimpleNamespace(readOnlyHint=True, title="List shots"),
        inputSchema={
            "$defs": {"ListShotsInput": {
                "type": "object",
                "properties": {"project_id": {"type": "string"}},
                "required": ["project_id"],
            }},
            "type": "object",
            "properties": {"params": {"$ref": "#/$defs/ListShotsInput"}},
            "required": ["params"],
        },
    )


def _plan(presentation):
    return json.dumps({
        "plan": [{
            "tool": "forge_list_shots",
            "args": {"project_id": "proj-port"},
        }],
        "filters": [],
        "aggregation": None,
        "presentation": presentation,
    })


def test_presentation_grounding_accepts_only_complete_shot_name_lists():
    grounded = ground_read_presentation(_declaration())

    assert grounded == GroundedListPresentation(
        entity="shot",
        field="name",
        collection_key="shots",
    )
    assert ground_read_presentation(_declaration(entity="shots")) == grounded
    assert ground_read_presentation(_declaration(field="status")) is None
    assert ground_read_presentation(_declaration(entity="project")) is None
    assert ground_read_presentation(_declaration(scope="first_10")) is None
    assert ground_read_presentation(_declaration(kind="summary")) is None
    assert ground_read_presentation("list shot names") is None


def test_renderer_preserves_source_order_and_reports_unnamed_rows():
    grounded = ground_read_presentation(_declaration())
    chain = [{
        "step": "forge_list_shots({})",
        "result": {"shots": [
            {"id": "s10", "name": " SHOT_010 "},
            {"id": "s2", "name": "SHOT_002"},
            {"id": "missing"},
            {"id": "spaced", "name": "SHOT   003"},
        ]},
    }]

    rendered = render_read_presentation(grounded, chain)

    assert rendered is not None
    assert rendered.text == (
        "Shot names (3 named, 1 unnamed):\n"
        "- SHOT_010\n"
        "- SHOT_002\n"
        "- SHOT 003"
    )
    assert rendered.evidence == {
        "kind": "deterministic_list",
        "entity": "shot",
        "field": "name",
        "scope": "all",
        "source_step_index": 0,
        "total_items": 4,
        "rendered_items": 3,
        "missing_items": 1,
        "source_population_complete": True,
        "all_requested_values_present": False,
    }


def test_renderer_requires_exactly_one_successful_shot_population():
    grounded = ground_read_presentation(_declaration())
    valid = {
        "step": "forge_list_shots({})",
        "result": {"shots": [{"name": "SHOT_001"}]},
    }

    assert render_read_presentation(grounded, []) is None
    assert render_read_presentation(grounded, [valid, valid]) is None
    assert render_read_presentation(grounded, [{
        "step": "forge_list_projects({})",
        "result": {"shots": [{"name": "SHOT_001"}]},
    }]) is None
    assert render_read_presentation(grounded, [{
        "step": "forge_list_shots({})",
        "result": {"error": "store unavailable"},
    }]) is None
    assert render_read_presentation(grounded, [{
        "step": "forge_list_shots({})",
        "result": {"count": 2, "shots": [{"name": "SHOT_001"}]},
    }]) is None


def test_planner_front_renders_every_shot_name_without_narrator_call():
    names = [f"SHOT_{index:03d}" for index in range(60)]
    router = SimpleNamespace(acomplete=AsyncMock(return_value=_plan(_declaration())))
    mcp = SimpleNamespace(call_tool=AsyncMock(side_effect=[
        _projects_text(),
        [TextContent(type="text", text=json.dumps({
            "project_id": "proj-port",
            "count": len(names),
            "shots": [
                {"id": f"shot-{index}", "name": name}
                for index, name in enumerate(names)
            ],
        }))],
    ]))

    body = asyncio.run(run_planner_front(
        [{"role": "user", "content": "list every shot name in portofino"}],
        router=router,
        mcp=mcp,
        tools=[_list_shots_tool()],
    ))

    assert body["stop_reason"] == "planner_front"
    assert body["final_text"].splitlines() == [
        "Shot names (60):",
        *(f"- {name}" for name in names),
    ]
    assert body["deterministic_render"] == {
        "kind": "deterministic_list",
        "entity": "shot",
        "field": "name",
        "scope": "all",
        "source_step_index": 0,
        "total_items": 60,
        "rendered_items": 60,
        "missing_items": 0,
        "source_population_complete": True,
        "all_requested_values_present": True,
    }
    assert router.acomplete.await_count == 1
    assert mcp.call_tool.await_count == 2


def test_invalid_presentation_falls_back_to_normal_narration():
    router = SimpleNamespace(acomplete=AsyncMock(side_effect=[
        _plan(_declaration(field="status")),
        "Narrated fallback.",
    ]))
    mcp = SimpleNamespace(call_tool=AsyncMock(side_effect=[
        _projects_text(),
        [TextContent(type="text", text=json.dumps({
            "shots": [{"id": "s1", "name": "SHOT_001"}],
        }))],
    ]))

    body = asyncio.run(run_planner_front(
        [{"role": "user", "content": "summarize the shot statuses"}],
        router=router,
        mcp=mcp,
        tools=[_list_shots_tool()],
    ))

    assert body["final_text"] == "Narrated fallback."
    assert "deterministic_render" not in body
    assert router.acomplete.await_count == 2


def test_empty_shot_population_renders_without_narrator_call():
    router = SimpleNamespace(acomplete=AsyncMock(return_value=_plan(_declaration())))
    mcp = SimpleNamespace(call_tool=AsyncMock(side_effect=[
        _projects_text(),
        [TextContent(type="text", text=json.dumps({"shots": []}))],
    ]))

    body = asyncio.run(run_planner_front(
        [{"role": "user", "content": "list every shot name in portofino"}],
        router=router,
        mcp=mcp,
        tools=[_list_shots_tool()],
    ))

    assert body["final_text"] == "No shots found."
    assert body["deterministic_render"]["total_items"] == 0
    assert router.acomplete.await_count == 1
