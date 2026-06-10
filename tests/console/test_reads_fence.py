"""Reads grounding fence — the deterministic twin of the op-front gate.

Closes the doctrine violation: "which shots are urgent" must NOT fabricate an
out-of-vocab mapping (status=pending) and assert it as fact. The fence makes the
reads planner clarify on ungroundable filter terms. Tests assert the
plan/clarify DECISION (data-independent) at both the helper and the
``run_planner_front`` integration boundary.
"""
from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

from mcp.types import TextContent

from forge_bridge.console._planner_front import run_planner_front
from forge_bridge.console._reads_fence import (
    _resolve_role,
    _resolve_status,
    ground_read_filters,
)


# ── resolver re-derivation (code never trusts the model's claim) ───────────────

def test_status_resolver_grounds_canonical_and_verbatim_phrases():
    assert _resolve_status("review") == "review"
    assert _resolve_status("in review") == "review"        # verbatim phrase
    assert _resolve_status("in progress") == "in_progress"  # ws->underscore
    assert _resolve_status("wip") == "in_progress"          # alias


def test_status_resolver_rejects_out_of_vocab_terms():
    assert _resolve_status("urgent") is None
    assert _resolve_status("my") is None
    assert _resolve_status("") is None
    assert _resolve_status(None) is None


def test_role_resolver_grounds_known_roles_and_rejects_unknown():
    assert _resolve_role("grade") == "grade"
    assert _resolve_role("comp") == "comp"
    assert _resolve_role("hero") is None
    assert _resolve_role(None) is None


# ── ground_read_filters: the gate decision ────────────────────────────────────

def test_fence_proceeds_when_status_filter_grounds():
    # Case 1: "which shots are in review" → review resolves in-vocab → proceed.
    plan = [{"tool": "forge_list_shots",
             "args": {"project_id": "p", "status": "review"}}]
    filters = [{"term": "in review", "arg": "status", "value": "review"}]
    assert ground_read_filters(plan, filters) is None


def test_fence_clarifies_on_fabricated_status_mapping():
    # Case 2: "which shots are urgent" → model invents urgent->pending → clarify.
    plan = [{"tool": "forge_list_shots",
             "args": {"project_id": "p", "status": "pending"}}]
    filters = [{"term": "urgent", "arg": "status", "value": "pending"}]
    msg = ground_read_filters(plan, filters)
    assert msg is not None
    assert "urgent" in msg
    assert "filter by status" in msg


def test_fence_clarifies_on_self_declared_null_qualifier():
    # Case 3: "show me my shots" → "my" declared null → clarify.
    plan = [{"tool": "forge_list_shots", "args": {"project_id": "p"}}]
    filters = [{"term": "my", "arg": None, "value": None}]
    msg = ground_read_filters(plan, filters)
    assert msg is not None
    assert "my" in msg


def test_fence_proceeds_with_no_qualifier():
    # Case 4: "show me the shots in portofino" → filters [] → proceed.
    plan = [{"tool": "forge_list_shots", "args": {"project_id": "p"}}]
    assert ground_read_filters(plan, []) is None
    # Absent filters key (legacy plan shape) must also proceed when no semantic
    # filter arg is set.
    assert ground_read_filters(plan, None) is None


def test_fence_closes_set_filter_omit_declaration_hole():
    # Plan sets status but declares no justification → cross-check clarifies.
    plan = [{"tool": "forge_list_shots",
             "args": {"project_id": "p", "status": "pending"}}]
    assert ground_read_filters(plan, []) is not None


def test_fence_clarifies_when_value_does_not_rederive_to_term():
    # Term grounds but the claimed value disagrees → ungrounded.
    plan = [{"tool": "forge_list_shots",
             "args": {"project_id": "p", "status": "pending"}}]
    filters = [{"term": "review", "arg": "status", "value": "pending"}]
    assert ground_read_filters(plan, filters) is not None


# ── integration: the fence runs inside run_planner_front, before execute ───────

def _projects_text() -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps(
        {"projects": [{"id": "proj-port", "name": "portofino"}]}))]


def _list_shots_tool() -> SimpleNamespace:
    return SimpleNamespace(
        name="forge_list_shots",
        description="Forge: list shots.",
        annotations=SimpleNamespace(readOnlyHint=True, title="List shots"),
        inputSchema={
            "$defs": {"ListShotsInput": {
                "type": "object",
                "properties": {"project_id": {"type": "string"},
                               "status": {"type": "string"}},
                "required": ["project_id"]}},
            "type": "object",
            "properties": {"params": {"$ref": "#/$defs/ListShotsInput"}},
            "required": ["params"]},
    )


def test_planner_front_fence_clarifies_without_executing_on_fabrication():
    # Model authors a plan + a fabricated urgent->pending mapping. The fence
    # must clarify BEFORE the tool executes and before narration.
    router = SimpleNamespace(acomplete=AsyncMock(return_value=json.dumps({
        "plan": [{"tool": "forge_list_shots",
                  "args": {"project_id": "proj-port", "status": "pending"}}],
        "filters": [{"term": "urgent", "arg": "status", "value": "pending"}],
    })))
    mcp = SimpleNamespace(call_tool=AsyncMock(return_value=_projects_text()))

    body = asyncio.run(run_planner_front(
        [{"role": "user", "content": "which shots are urgent in portofino"}],
        router=router, mcp=mcp, tools=[_list_shots_tool()]))

    assert body["stop_reason"] == "clarification_needed"
    assert body["plan"] == []
    assert "urgent" in body["final_text"]
    # Only project grounding ran — forge_list_shots was NOT executed.
    assert mcp.call_tool.await_count == 1
    assert mcp.call_tool.await_args_list[0].args[0] == "forge_list_projects"
    # The answer-pass (2nd acomplete) never ran — fabrication never narrated.
    assert router.acomplete.await_count == 1


def test_planner_front_fence_proceeds_on_grounded_status():
    # Grounded read still executes + narrates (no regression).
    router = SimpleNamespace(acomplete=AsyncMock(side_effect=[
        json.dumps({
            "plan": [{"tool": "forge_list_shots",
                      "args": {"project_id": "proj-port", "status": "review"}}],
            "filters": [{"term": "in review", "arg": "status",
                         "value": "review"}],
        }),
        "There are no shots in review.",
    ]))
    mcp = SimpleNamespace(call_tool=AsyncMock(side_effect=[
        _projects_text(),
        [TextContent(type="text", text=json.dumps(
            {"project_id": "proj-port", "shots": []}))],
    ]))

    body = asyncio.run(run_planner_front(
        [{"role": "user", "content": "which shots are in review in portofino"}],
        router=router, mcp=mcp, tools=[_list_shots_tool()]))

    assert body["stop_reason"] == "planner_front"
    assert body["plan"][0]["tool"] == "forge_list_shots"
    assert body["chain"][0]["step"].startswith("forge_list_shots(")
    assert router.acomplete.await_count == 2  # planned + narrated
