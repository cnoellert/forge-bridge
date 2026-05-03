"""PR15 — deterministic tool-calling enforcement.

Pure unit tests for ``forge_bridge/console/_tool_enforcement.py``. Behavior
inside the chat handler (system-prompt injection, malformed-text rejection)
is covered in ``test_chat_handler.py`` (PR15 section)."""
from __future__ import annotations

import pytest

from forge_bridge.console import _tool_enforcement as te


# ── system-prompt builder ────────────────────────────────────────────────


def test_build_prompt_stacks_base_with_enforcement_block():
    """Existing pipeline prompt MUST be preserved at the top of the stack."""
    base = "You are a VFX pipeline assistant."
    out = te.build_enforcement_system_prompt(base, tools_filtered=5)
    assert out.startswith(base)
    assert "You are a tool-using agent." in out
    assert "YOU MUST CALL IT" in out


def test_build_prompt_appends_hard_tool_instruction_when_only_one_tool():
    out = te.build_enforcement_system_prompt("base", tools_filtered=1)
    assert "exactly ONE tool" in out
    assert "MUST call this tool" in out


def test_build_prompt_omits_hard_tool_instruction_when_more_than_one_tool():
    """HARD-TOOL line is exclusive to the single-tool case."""
    out = te.build_enforcement_system_prompt("base", tools_filtered=2)
    assert "MUST call this tool" not in out
    out8 = te.build_enforcement_system_prompt("base", tools_filtered=8)
    assert "MUST call this tool" not in out8


def test_build_prompt_tolerates_none_or_empty_base():
    """A None or empty base must still produce a usable enforcement prompt."""
    out_none = te.build_enforcement_system_prompt(None, tools_filtered=4)
    out_empty = te.build_enforcement_system_prompt("", tools_filtered=4)
    out_ws = te.build_enforcement_system_prompt("   \n", tools_filtered=4)
    for out in (out_none, out_empty, out_ws):
        assert "tool-using agent" in out
        # Stripped: should not begin with the enforcement block's whitespace.
        assert out.strip().startswith("You are a tool-using agent.")


def test_build_prompt_defensive_against_non_string_base():
    """A non-string base (e.g. MagicMock from a unit test) must not blow up."""
    sentinel = object()  # not a string
    out = te.build_enforcement_system_prompt(sentinel, tools_filtered=4)
    assert "tool-using agent" in out


# ── tool-enforced predicate ──────────────────────────────────────────────


@pytest.mark.parametrize("count,expected", [
    (0, True), (1, True), (2, True), (3, True), (4, False), (8, False),
])
def test_is_tool_enforced_threshold(count, expected):
    assert te.is_tool_enforced(count) is expected


# ── output validation ────────────────────────────────────────────────────


def test_chat_template_token_leak_rejected():
    """Any chat-template token in the assistant text is malformed."""
    assert te.is_response_text_malformed_tool(
        '<|im_start|>{"name": "flame_ping", "arguments": {}}'
    )
    assert te.is_response_text_malformed_tool(
        "Sure! <|im_end|> here you go."
    )


def test_leading_tool_call_json_rejected():
    """A response that BEGINS with a name/arguments JSON object is malformed."""
    bad = '{"name": "forge_list_media", "arguments": {"status": "failed"}}'
    assert te.is_response_text_malformed_tool(bad)
    # Inside markdown is also malformed (the qwen2.5-coder pattern).
    fenced = '```json\n{"name": "flame_ping", "arguments": {}}\n```'
    assert te.is_response_text_malformed_tool(fenced)


def test_legitimate_text_response_not_flagged():
    """Plain assistant text must NOT be flagged."""
    for clean in [
        "Hello — there are 4 libraries: Default Library, WIP, Postings, Delivery.",
        "I checked the project and there are no shots yet.",
        "",
        None,
        "I'm not sure which tool to use here, can you clarify?",
    ]:
        assert te.is_response_text_malformed_tool(clean) is False, (
            f"false-positive: {clean!r}"
        )


def test_text_mentioning_tool_call_format_in_prose_not_flagged():
    """A mid-response mention of name/arguments in prose is NOT malformed —
    only a leading tool-call-shaped object is."""
    legit = (
        "I tried calling the tool. The expected format is "
        '{"name": "...", "arguments": {...}}, but I couldn\'t determine the args.'
    )
    assert te.is_response_text_malformed_tool(legit) is False


def test_non_string_input_returns_false():
    """Defensive: None, dicts, lists, ints — never raise, never flag."""
    for bad in (None, 42, {"x": 1}, [1, 2], object()):
        assert te.is_response_text_malformed_tool(bad) is False  # type: ignore[arg-type]
