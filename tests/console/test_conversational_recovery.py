"""CR.2 conversational recovery locks.

Recoverable ambiguity should become a deterministic continuation prompt,
not a raw terminal error. These tests intentionally stay model-free: the
recovery layer only normalizes substrate-held candidates and next-turn
candidate matching.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from forge_bridge.console._recovery import (
    recovery_params_from_messages,
    referent_clarification,
    response_body,
    tool_action_label,
    tool_clarification,
)


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
