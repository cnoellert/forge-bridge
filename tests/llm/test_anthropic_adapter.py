"""Wire-format unit tests for AnthropicToolAdapter.

Coverage map:
    LLMTOOL-02  Anthropic cloud path — schema translation, response parsing
    D-06        disable_parallel_tool_use=True at top level
    D-31        strict=True per tool by default + per-tool downgrade fallback
    D-35        usage_tokens = (input_tokens, output_tokens)
    research §2.3  Anthropic protocol hard rules (assistant content verbatim,
                   tool_result blocks FIRST in user content, tool_use_id matching)
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from forge_bridge.llm._adapters import (
    AnthropicToolAdapter,
    ToolCallResult,
    _ToolCall,
    _TurnResponse,
)
from forge_bridge.llm.router import LLMToolError


# ---------------------------------------------------------------------------
# Helpers — fake forge MCP Tool + fake Anthropic response objects
# ---------------------------------------------------------------------------


class _FakeTool:
    def __init__(self, name: str, description: str, input_schema: dict):
        self.name = name
        self.description = description
        self.inputSchema = input_schema


def _fake_block_text(text: str):
    b = MagicMock()
    b.type = "text"
    b.text = text
    return b


def _fake_block_tool_use(use_id: str, name: str, input_dict: dict):
    b = MagicMock()
    b.type = "tool_use"
    b.id = use_id
    b.name = name
    b.input = input_dict
    return b


def _fake_response(content_blocks: list, input_tokens: int = 100, output_tokens: int = 50):
    r = MagicMock()
    r.content = content_blocks
    r.usage.input_tokens = input_tokens
    r.usage.output_tokens = output_tokens
    return r


# ---------------------------------------------------------------------------
# Compile tests (research §5.1 schema translation table)
# ---------------------------------------------------------------------------


class TestAnthropicToolAdapterCompile:
    def test_single_tool_schema_translation(self):
        client = MagicMock()
        adapter = AnthropicToolAdapter(client, "claude-opus-4-7")
        t = _FakeTool("forge_list", "list things", {"type": "object", "properties": {}})
        compiled = adapter._compile_tools([t])
        assert len(compiled) == 1
        assert compiled[0]["name"] == "forge_list"
        assert compiled[0]["description"] == "list things"
        # Strict-mode tools must carry `additionalProperties: false` per
        # Anthropic API enforcement (corrected during v1.4 LLMTOOL-02 live UAT).
        assert compiled[0]["input_schema"] == {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        }

    def test_strict_true_by_default(self):
        client = MagicMock()
        adapter = AnthropicToolAdapter(client, "claude-opus-4-7")
        t = _FakeTool("forge_x", "x", {"type": "object"})
        compiled = adapter._compile_tools([t])
        assert compiled[0].get("strict") is True

    def test_downgraded_tool_omits_strict(self):
        client = MagicMock()
        adapter = AnthropicToolAdapter(client, "claude-opus-4-7")
        adapter._downgraded_tools.add("forge_bad")
        t1 = _FakeTool("forge_bad", "bad", {"type": "object"})
        t2 = _FakeTool("forge_good", "good", {"type": "object"})
        compiled = adapter._compile_tools([t1, t2])
        assert "strict" not in compiled[0]  # downgraded
        assert compiled[1].get("strict") is True  # not downgraded

    def test_multiple_tools_all_translated(self):
        client = MagicMock()
        adapter = AnthropicToolAdapter(client, "claude-opus-4-7")
        tools = [
            _FakeTool("flame_a", "a", {"type": "object"}),
            _FakeTool("forge_b", "b", {"type": "object"}),
            _FakeTool("synth_c", "c", {"type": "object"}),
        ]
        compiled = adapter._compile_tools(tools)
        assert [c["name"] for c in compiled] == ["flame_a", "forge_b", "synth_c"]

    def test_empty_list_returns_empty(self):
        client = MagicMock()
        adapter = AnthropicToolAdapter(client, "claude-opus-4-7")
        assert adapter._compile_tools([]) == []


# ---------------------------------------------------------------------------
# send_turn tests (response parsing + top-level params)
# ---------------------------------------------------------------------------


class TestAnthropicToolAdapterSendTurn:
    @pytest.mark.asyncio
    async def test_disable_parallel_tool_use_true_sent(self):
        client = MagicMock()
        client.messages.create = AsyncMock(return_value=_fake_response([_fake_block_text("hi")]))
        adapter = AnthropicToolAdapter(client, "claude-opus-4-7")
        state = adapter.init_state(prompt="hi", system="sys", tools=[], temperature=0.1)
        await adapter.send_turn(state)
        kwargs = client.messages.create.call_args.kwargs
        # D-06 (v1.4 corrected form): disable_parallel_tool_use lives inside
        # tool_choice, not as a top-level kwarg. Older Anthropic SDKs accepted
        # it at the top level; SDK 0.97+ requires the nested form.
        assert kwargs["tool_choice"] == {"type": "auto", "disable_parallel_tool_use": True}
        assert "disable_parallel_tool_use" not in kwargs

    @pytest.mark.asyncio
    async def test_usage_tokens_normalized(self):
        client = MagicMock()
        client.messages.create = AsyncMock(return_value=_fake_response(
            [_fake_block_text("hi")], input_tokens=412, output_tokens=78,
        ))
        adapter = AnthropicToolAdapter(client, "claude-opus-4-7")
        state = adapter.init_state(prompt="hi", system="sys", tools=[], temperature=0.1)
        resp = await adapter.send_turn(state)
        assert resp.usage_tokens == (412, 78)  # D-35

    @pytest.mark.asyncio
    async def test_tool_use_block_parsed_to_tool_call(self):
        client = MagicMock()
        client.messages.create = AsyncMock(return_value=_fake_response([
            _fake_block_text("I'll check that."),
            _fake_block_tool_use("toolu_abc123", "forge_list_staged", {"status": "proposed"}),
        ]))
        adapter = AnthropicToolAdapter(client, "claude-opus-4-7")
        t = _FakeTool("forge_list_staged", "list staged", {"type": "object"})
        state = adapter.init_state(prompt="show me", system="s", tools=[t], temperature=0.1)
        resp = await adapter.send_turn(state)
        assert resp.text == "I'll check that."
        assert len(resp.tool_calls) == 1
        assert resp.tool_calls[0].ref == "toolu_abc123"
        assert resp.tool_calls[0].tool_name == "forge_list_staged"
        assert resp.tool_calls[0].arguments == {"status": "proposed"}

    @pytest.mark.asyncio
    async def test_terminal_response_empty_tool_calls(self):
        client = MagicMock()
        client.messages.create = AsyncMock(return_value=_fake_response([_fake_block_text("done")]))
        adapter = AnthropicToolAdapter(client, "claude-opus-4-7")
        state = adapter.init_state(prompt="hi", system="s", tools=[], temperature=0.1)
        resp = await adapter.send_turn(state)
        assert resp.tool_calls == []  # terminal — coordinator exits loop
        assert resp.text == "done"


# ---------------------------------------------------------------------------
# append_results tests (research §2.3 protocol hard rules)
# ---------------------------------------------------------------------------


class TestAnthropicToolAdapterAppendResults:
    def test_assistant_text_and_tool_use_preserved_verbatim(self):
        client = MagicMock()
        adapter = AnthropicToolAdapter(client, "claude-opus-4-7")
        state = {"messages": [{"role": "user", "content": "hi"}], "system": "s",
                 "temperature": 0.1, "tools_source": []}
        # Build a fake response with a text and tool_use block.
        fake_response = _fake_response([
            _fake_block_text("plan"),
            _fake_block_tool_use("toolu_1", "forge_x", {"a": 1}),
        ])
        turn_response = _TurnResponse(
            text="plan",
            tool_calls=[_ToolCall(ref="toolu_1", tool_name="forge_x", arguments={"a": 1})],
            usage_tokens=(10, 5),
            raw=fake_response,
        )
        new_state = adapter.append_results(state, turn_response, [
            ToolCallResult(tool_call_ref="toolu_1", tool_name="forge_x",
                           content="result", is_error=False),
        ])
        # Last two messages: assistant + user with tool_result
        assistant = new_state["messages"][-2]
        assert assistant["role"] == "assistant"
        # Both text and tool_use blocks preserved
        block_types = [b["type"] for b in assistant["content"]]
        assert block_types == ["text", "tool_use"]

    def test_tool_result_first_in_user_content(self):
        """Research §2.3 rule 2: tool_result blocks MUST come FIRST."""
        client = MagicMock()
        adapter = AnthropicToolAdapter(client, "claude-opus-4-7")
        state = {"messages": [], "system": "s", "temperature": 0.1, "tools_source": []}
        fake_response = _fake_response([_fake_block_tool_use("toolu_1", "forge_x", {})])
        turn_response = _TurnResponse(
            text="",
            tool_calls=[_ToolCall(ref="toolu_1", tool_name="forge_x", arguments={})],
            usage_tokens=(0, 0),
            raw=fake_response,
        )
        new_state = adapter.append_results(state, turn_response, [
            ToolCallResult(tool_call_ref="toolu_1", tool_name="forge_x",
                           content="result", is_error=False),
        ])
        user = new_state["messages"][-1]
        assert user["role"] == "user"
        assert user["content"][0]["type"] == "tool_result"

    def test_tool_use_id_round_trips_to_tool_use_id(self):
        client = MagicMock()
        adapter = AnthropicToolAdapter(client, "claude-opus-4-7")
        state = {"messages": [], "system": "s", "temperature": 0.1, "tools_source": []}
        fake_response = _fake_response([_fake_block_tool_use("toolu_xyz", "f", {})])
        turn_response = _TurnResponse(
            text="",
            tool_calls=[_ToolCall(ref="toolu_xyz", tool_name="f", arguments={})],
            usage_tokens=(0, 0),
            raw=fake_response,
        )
        new_state = adapter.append_results(state, turn_response, [
            ToolCallResult(tool_call_ref="toolu_xyz", tool_name="f",
                           content="ok", is_error=False),
        ])
        user = new_state["messages"][-1]
        assert user["content"][0]["tool_use_id"] == "toolu_xyz"


# ---------------------------------------------------------------------------
# Per-tool downgrade tests (D-31)
# ---------------------------------------------------------------------------


class TestAnthropicToolAdapterDowngrade:
    @pytest.mark.asyncio
    async def test_400_with_tool_name_triggers_downgrade_and_retry(self):
        """First call raises BadRequestError mentioning forge_quirky.
        Second call (after downgrade) succeeds and returns a terminal response."""
        client = MagicMock()
        # First call: simulate Anthropic strict-mode 400 mentioning the tool.
        class FakeBadRequestError(Exception):
            pass
        bad = FakeBadRequestError("schema validation failed for tool 'forge_quirky'")

        # AsyncMock side_effect: first call raises, second returns terminal.
        client.messages.create = AsyncMock(side_effect=[
            bad,
            _fake_response([_fake_block_text("ok after downgrade")]),
        ])
        adapter = AnthropicToolAdapter(client, "claude-opus-4-7")
        t = _FakeTool("forge_quirky", "q", {"type": "object"})
        state = adapter.init_state(prompt="hi", system="s", tools=[t], temperature=0.1)
        resp = await adapter.send_turn(state)
        assert resp.text == "ok after downgrade"
        # Second call must NOT include strict for forge_quirky
        second_kwargs = client.messages.create.call_args_list[1].kwargs
        tools_payload = second_kwargs["tools"]
        assert "strict" not in tools_payload[0]
        # And the adapter remembers the downgrade for the rest of the session
        assert "forge_quirky" in adapter._downgraded_tools

    @pytest.mark.asyncio
    async def test_unrecoverable_provider_error_raises_LLMToolError(self):
        client = MagicMock()
        client.messages.create = AsyncMock(side_effect=RuntimeError("connection broken"))
        adapter = AnthropicToolAdapter(client, "claude-opus-4-7")
        state = adapter.init_state(prompt="hi", system="s", tools=[], temperature=0.1)
        with pytest.raises(LLMToolError) as exc_info:
            await adapter.send_turn(state)
        # Phase 8 cf221fe: only type name in message, never str(exc)
        assert "RuntimeError" in str(exc_info.value)
        assert "connection broken" not in str(exc_info.value)
