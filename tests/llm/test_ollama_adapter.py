"""Wire-format unit tests for OllamaToolAdapter.

Coverage map:
    LLMTOOL-01  Ollama local path — schema translation, response parsing
    D-06        supports_parallel = False; coordinator slices tool_calls[:1]
    D-29        Soft allow-list WARNING on unrecognized model
    D-33        keep_alive='10m' on every chat request (research §6.8)
    D-35        usage_tokens = (prompt_eval_count, eval_count)
    research §3.3  role:tool message shape with tool_name field
"""
from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from forge_bridge.llm._adapters import (
    OllamaToolAdapter,
    ToolCallResult,
    _OLLAMA_KEEP_ALIVE,
    _OLLAMA_TOOL_MODELS,
    _ToolCall,
    _TurnResponse,
)
from forge_bridge.llm.router import LLMToolError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeTool:
    def __init__(self, name: str, description: str, input_schema: dict):
        self.name = name
        self.description = description
        self.inputSchema = input_schema


def _fake_response_dict(content: str = "", tool_calls: list | None = None,
                       prompt_eval_count: int = 0, eval_count: int = 0) -> dict:
    msg: dict = {"role": "assistant", "content": content}
    if tool_calls is not None:
        msg["tool_calls"] = tool_calls
    return {
        "message": msg,
        "prompt_eval_count": prompt_eval_count,
        "eval_count": eval_count,
        "done": True,
    }


# ---------------------------------------------------------------------------
# Compile tests
# ---------------------------------------------------------------------------


class TestOllamaToolAdapterCompile:
    def test_function_wrapper_format(self):
        client = MagicMock()
        adapter = OllamaToolAdapter(client, "qwen3:32b")
        t = _FakeTool("forge_list", "list things", {"type": "object", "properties": {}})
        compiled = adapter._compile_tools([t])
        assert len(compiled) == 1
        assert compiled[0]["type"] == "function"
        assert compiled[0]["function"]["name"] == "forge_list"
        assert compiled[0]["function"]["description"] == "list things"
        # NOTE: Ollama uses 'parameters' key, NOT 'input_schema'
        assert compiled[0]["function"]["parameters"] == {"type": "object", "properties": {}}

    def test_multiple_tools_all_wrapped(self):
        client = MagicMock()
        adapter = OllamaToolAdapter(client, "qwen3:32b")
        tools = [
            _FakeTool("flame_a", "a", {"type": "object"}),
            _FakeTool("forge_b", "b", {"type": "object"}),
        ]
        compiled = adapter._compile_tools(tools)
        assert all(c["type"] == "function" for c in compiled)
        assert [c["function"]["name"] for c in compiled] == ["flame_a", "forge_b"]

    def test_empty_list_returns_empty(self):
        client = MagicMock()
        adapter = OllamaToolAdapter(client, "qwen3:32b")
        assert adapter._compile_tools([]) == []


# ---------------------------------------------------------------------------
# Allow-list warning tests (D-29)
# ---------------------------------------------------------------------------


class TestOllamaToolAdapterAllowList:
    def test_allowlisted_model_no_warning(self, caplog):
        client = MagicMock()
        with caplog.at_level(logging.WARNING, logger="forge_bridge.llm._adapters"):
            OllamaToolAdapter(client, "qwen3:32b")
        warning_msgs = [r.message for r in caplog.records if r.levelno == logging.WARNING]
        assert not any("allow-list" in m for m in warning_msgs)

    def test_unknown_model_emits_warning(self, caplog):
        client = MagicMock()
        with caplog.at_level(logging.WARNING, logger="forge_bridge.llm._adapters"):
            OllamaToolAdapter(client, "phi3:mini")
        warning_msgs = [r.message for r in caplog.records if r.levelno == logging.WARNING]
        assert any("phi3:mini" in m and "allow-list" in m for m in warning_msgs), (
            f"expected warning with 'phi3:mini' and 'allow-list'; got: {warning_msgs}"
        )

    def test_all_documented_models_in_allowlist(self):
        """D-29 verbatim — the 5 production-acceptable models per research §3.5."""
        expected = {"qwen3:32b", "qwen3-coder:32b", "qwen2.5-coder:32b",
                    "llama3.1:70b", "mixtral:8x22b"}
        assert _OLLAMA_TOOL_MODELS == expected


# ---------------------------------------------------------------------------
# send_turn tests (request shape + response parsing)
# ---------------------------------------------------------------------------


class TestOllamaToolAdapterSendTurn:
    @pytest.mark.asyncio
    async def test_keep_alive_10m_sent_on_every_request(self):
        client = MagicMock()
        client.chat = AsyncMock(return_value=_fake_response_dict(content="done"))
        adapter = OllamaToolAdapter(client, "qwen3:32b")
        state = adapter.init_state(prompt="hi", system="sys", tools=[], temperature=0.1)
        await adapter.send_turn(state)
        kwargs = client.chat.call_args.kwargs
        assert kwargs["keep_alive"] == "10m"  # D-33 verbatim
        assert kwargs["keep_alive"] == _OLLAMA_KEEP_ALIVE

    @pytest.mark.asyncio
    async def test_dict_shape_tool_calls_parsed(self):
        client = MagicMock()
        client.chat = AsyncMock(return_value=_fake_response_dict(
            content="",
            tool_calls=[
                {"type": "function", "function": {"name": "forge_list", "arguments": {"k": "v"}}},
            ],
        ))
        adapter = OllamaToolAdapter(client, "qwen3:32b")
        state = adapter.init_state(prompt="show me", system="s", tools=[], temperature=0.1)
        resp = await adapter.send_turn(state)
        assert len(resp.tool_calls) == 1
        assert resp.tool_calls[0].tool_name == "forge_list"
        assert resp.tool_calls[0].arguments == {"k": "v"}
        # Composite ref `{idx}:{name}` per research §5.2 (Ollama has no opaque id)
        assert resp.tool_calls[0].ref == "0:forge_list"

    @pytest.mark.asyncio
    async def test_string_arguments_parsed_as_json(self):
        """Older Ollama responses or mocks send arguments as JSON strings."""
        client = MagicMock()
        client.chat = AsyncMock(return_value=_fake_response_dict(
            content="",
            tool_calls=[
                {"type": "function", "function": {"name": "forge_x", "arguments": '{"a": 1}'}},
            ],
        ))
        adapter = OllamaToolAdapter(client, "qwen3:32b")
        state = adapter.init_state(prompt="hi", system="s", tools=[], temperature=0.1)
        resp = await adapter.send_turn(state)
        assert resp.tool_calls[0].arguments == {"a": 1}  # parsed via json.loads

    @pytest.mark.asyncio
    async def test_usage_tokens_from_eval_counts(self):
        client = MagicMock()
        client.chat = AsyncMock(return_value=_fake_response_dict(
            content="done",
            prompt_eval_count=412,
            eval_count=78,
        ))
        adapter = OllamaToolAdapter(client, "qwen3:32b")
        state = adapter.init_state(prompt="hi", system="s", tools=[], temperature=0.1)
        resp = await adapter.send_turn(state)
        assert resp.usage_tokens == (412, 78)  # D-35

    @pytest.mark.asyncio
    async def test_terminal_response_empty_tool_calls(self):
        client = MagicMock()
        client.chat = AsyncMock(return_value=_fake_response_dict(content="final answer"))
        adapter = OllamaToolAdapter(client, "qwen3:32b")
        state = adapter.init_state(prompt="hi", system="s", tools=[], temperature=0.1)
        resp = await adapter.send_turn(state)
        assert resp.tool_calls == []  # terminal — coordinator exits
        assert resp.text == "final answer"


# ---------------------------------------------------------------------------
# append_results tests (research §3.3 protocol)
# ---------------------------------------------------------------------------


class TestOllamaToolAdapterAppendResults:
    def test_tool_messages_have_tool_name_field(self):
        """Research §3.3: role:tool messages include tool_name field for
        improved model recovery when multiple tools were called."""
        client = MagicMock()
        adapter = OllamaToolAdapter(client, "qwen3:32b")
        state = {"messages": [{"role": "user", "content": "hi"}],
                 "temperature": 0.1, "tools_compiled": []}
        turn_response = _TurnResponse(
            text="",
            tool_calls=[_ToolCall(ref="0:forge_x", tool_name="forge_x", arguments={"a": 1})],
            usage_tokens=(10, 5),
            raw=None,
        )
        new_state = adapter.append_results(state, turn_response, [
            ToolCallResult(tool_call_ref="0:forge_x", tool_name="forge_x",
                           content="result here", is_error=False),
        ])
        tool_msg = new_state["messages"][-1]
        assert tool_msg["role"] == "tool"
        assert tool_msg["tool_name"] == "forge_x"
        assert tool_msg["content"] == "result here"

    def test_order_preserved_across_results(self):
        """Ollama uses ORDER-based matching per research §5.2 — results must
        be appended in the SAME ORDER as the original tool_calls."""
        client = MagicMock()
        adapter = OllamaToolAdapter(client, "qwen3:32b")
        state = {"messages": [], "temperature": 0.1, "tools_compiled": []}
        turn_response = _TurnResponse(
            text="",
            tool_calls=[
                _ToolCall(ref="0:a", tool_name="a", arguments={}),
                _ToolCall(ref="1:b", tool_name="b", arguments={}),
            ],
            usage_tokens=(0, 0),
            raw=None,
        )
        new_state = adapter.append_results(state, turn_response, [
            ToolCallResult(tool_call_ref="0:a", tool_name="a", content="r1", is_error=False),
            ToolCallResult(tool_call_ref="1:b", tool_name="b", content="r2", is_error=False),
        ])
        # Order: assistant, tool(a), tool(b)
        tool_messages = [m for m in new_state["messages"] if m.get("role") == "tool"]
        assert [m["tool_name"] for m in tool_messages] == ["a", "b"]


# ---------------------------------------------------------------------------
# Error handling tests (Phase 8 cf221fe credential-leak rule)
# ---------------------------------------------------------------------------


class TestOllamaToolAdapterErrors:
    @pytest.mark.asyncio
    async def test_provider_exception_wrapped_as_LLMToolError(self):
        client = MagicMock()
        client.chat = AsyncMock(side_effect=ConnectionError("daemon at localhost:11434 unreachable; api key sk-xxx"))
        adapter = OllamaToolAdapter(client, "qwen3:32b")
        state = adapter.init_state(prompt="hi", system="s", tools=[], temperature=0.1)
        with pytest.raises(LLMToolError) as exc_info:
            await adapter.send_turn(state)
        # Phase 8 cf221fe: only type name in message, never str(exc) which could leak creds
        msg = str(exc_info.value)
        assert "ConnectionError" in msg
        assert "sk-xxx" not in msg
        assert "daemon at" not in msg
