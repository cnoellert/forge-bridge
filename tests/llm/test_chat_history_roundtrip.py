"""Phase A regression tests — `complete_with_tools()` MUST return a structured
result that round-trips full tool execution history.

These tests pin the Phase A contract: the router cannot lose tool activity.

Phase A.1: messages must include every assistant(tool_calls) and role:tool
           message that the loop produced; messages[-1] must be the final
           assistant turn.

Phase A.2: tool_trace must record every invoked tool with success/error
           semantics; constructed inside the router, never reconstructed
           downstream.

Tests fail on current main because:
  - complete_with_tools() returns `str`, not ChatTurnResult — the import alone
    fails today.
  - Even with the import bypassed, the return value has no `.messages` or
    `.tool_trace` fields to inspect.

Tests pass after Phase A lands.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from forge_bridge.llm._adapters import _ToolCall, _TurnResponse, ToolCallResult
from forge_bridge.llm.router import ChatTurnResult, LLMRouter

# Reuse the existing stub adapter scaffolding (D-37) — same pattern as
# tests/llm/test_complete_with_tools.py so the test surface is consistent.
from tests.llm.conftest import (
    _StubAdapter,
    _make_terminal_turn,
    _make_tool_call_turn,
)


class _FakeTool:
    """Minimal MCP Tool stand-in (mirrors test_complete_with_tools.py:55)."""

    def __init__(self, name: str, description: str = "test", input_schema=None):
        self.name = name
        self.description = description
        self.inputSchema = input_schema or {"type": "object", "properties": {}}


def _patch_adapters(stub_adapter_instance):
    """Replace both adapter classes with a factory yielding the stub."""
    factory = MagicMock(return_value=stub_adapter_instance)
    return patch.multiple(
        "forge_bridge.llm._adapters",
        OllamaToolAdapter=factory,
        AnthropicToolAdapter=factory,
    )


def _patch_clients(router: LLMRouter) -> None:
    router._get_local_native_client = MagicMock(return_value=MagicMock())
    router._get_cloud_client = MagicMock(return_value=MagicMock())
    router._get_local_client = MagicMock(return_value=MagicMock())


# ---------------------------------------------------------------------------
# Phase A.1 — return-shape contract
# ---------------------------------------------------------------------------


class TestChatTurnResultShape:
    """The router returns a structured ChatTurnResult — never a bare string."""

    @pytest.mark.asyncio
    async def test_returns_chat_turn_result_dataclass(self):
        """complete_with_tools returns a ChatTurnResult with the three named
        fields, never a bare string. Fails on main: returns `str`."""
        adapter = _StubAdapter([_make_terminal_turn(text="hello")])
        router = LLMRouter()
        _patch_clients(router)
        with _patch_adapters(adapter):
            result = await router.complete_with_tools(
                "hi",
                tools=[_FakeTool("forge_x")],
                tool_executor=AsyncMock(return_value="ignored"),
            )
        assert isinstance(result, ChatTurnResult), (
            f"expected ChatTurnResult, got {type(result).__name__}"
        )
        assert hasattr(result, "final_text")
        assert hasattr(result, "messages")
        assert hasattr(result, "tool_trace")

    @pytest.mark.asyncio
    async def test_terminal_only_loop_returns_text_and_assistant_message(self):
        """No tool calls fired: messages still ends with the assistant turn,
        tool_trace is empty."""
        adapter = _StubAdapter([_make_terminal_turn(text="answer")])
        router = LLMRouter()
        _patch_clients(router)
        with _patch_adapters(adapter):
            result = await router.complete_with_tools(
                "hi",
                tools=[_FakeTool("forge_x")],
                tool_executor=AsyncMock(return_value="ignored"),
            )
        assert result.final_text == "answer"
        assert isinstance(result.messages, list) and result.messages
        assert result.messages[-1]["role"] == "assistant"
        assert result.messages[-1]["content"] == "answer"
        assert result.tool_trace == []


# ---------------------------------------------------------------------------
# Phase A.1 — tool history MUST appear in messages (the bug Phase A fixes)
# ---------------------------------------------------------------------------


class TestToolHistoryPreservation:
    """The data-loss bug is here: when the loop runs, intermediate tool_use
    and tool_result messages must be in the returned messages list."""

    @pytest.mark.asyncio
    async def test_one_tool_call_then_terminal_records_full_history(self):
        """Turn 1: tool call. Turn 2: terminal text. Both the assistant
        tool_calls turn AND the tool result must appear in messages.
        Fails on main: messages would only contain user + final assistant."""
        adapter = _StubAdapter([
            _make_tool_call_turn("forge_list", {"k": "v"}, ref="r1"),
            _make_terminal_turn(text="final"),
        ])
        router = LLMRouter()
        _patch_clients(router)
        executor = AsyncMock(return_value="ROW_DATA")
        with _patch_adapters(adapter):
            result = await router.complete_with_tools(
                "show me",
                tools=[_FakeTool("forge_list")],
                tool_executor=executor,
            )
        assert result.final_text == "final"
        # messages MUST include the assistant's tool_calls turn AND the tool
        # result message. Order: user → assistant(tool_calls) → tool → assistant(final).
        roles = [m.get("role") for m in result.messages]
        assert "tool" in roles, (
            f"messages dropped the tool_result entry: {result.messages!r}"
        )
        assert any(
            m.get("role") == "assistant" and m.get("tool_calls")
            for m in result.messages
        ), f"messages dropped the assistant tool_calls entry: {result.messages!r}"
        # Final entry MUST be the terminal assistant turn (contract: messages[-1]
        # is always the final assistant text).
        assert result.messages[-1]["role"] == "assistant"
        assert result.messages[-1]["content"] == "final"

    @pytest.mark.asyncio
    async def test_tool_result_content_round_trips_into_messages(self):
        """The tool's actual return value must be findable in the returned
        messages list — not collapsed away."""
        adapter = _StubAdapter([
            _make_tool_call_turn("forge_list", {}, ref="r1"),
            _make_terminal_turn(text="ok"),
        ])
        router = LLMRouter()
        _patch_clients(router)
        executor = AsyncMock(return_value="UNIQUE_TOOL_PAYLOAD_42")
        with _patch_adapters(adapter):
            result = await router.complete_with_tools(
                "show me",
                tools=[_FakeTool("forge_list")],
                tool_executor=executor,
            )
        joined = " ".join(
            m.get("content", "") for m in result.messages
            if isinstance(m.get("content"), str)
        )
        assert "UNIQUE_TOOL_PAYLOAD_42" in joined, (
            f"tool result content was lost: {result.messages!r}"
        )


# ---------------------------------------------------------------------------
# Phase A.2 — tool_trace contract
# ---------------------------------------------------------------------------


class TestToolTraceRecording:
    """tool_trace is the structured sibling of message-level tool activity.
    Constructed inside the router (D-trace-1)."""

    @pytest.mark.asyncio
    async def test_tool_trace_records_success(self):
        """A successful tool call: result populated, error is None."""
        adapter = _StubAdapter([
            _make_tool_call_turn("forge_list", {"a": 1}, ref="r1"),
            _make_terminal_turn(text="done"),
        ])
        router = LLMRouter()
        _patch_clients(router)
        with _patch_adapters(adapter):
            result = await router.complete_with_tools(
                "x",
                tools=[_FakeTool("forge_list")],
                tool_executor=AsyncMock(return_value="GOOD"),
            )
        assert len(result.tool_trace) == 1
        entry = result.tool_trace[0]
        assert entry["tool_name"] == "forge_list"
        assert entry["arguments"] == {"a": 1}
        assert entry["result"] is not None
        assert entry["error"] is None
        assert entry["index"] == 0

    @pytest.mark.asyncio
    async def test_tool_trace_records_error(self):
        """A failing tool call: error populated (non-None string), result is None.
        The failure-visibility invariant: a failed tool MUST appear in
        tool_trace AND in messages — never collapsed into a successful
        final_text."""
        adapter = _StubAdapter([
            _make_tool_call_turn("forge_list", {}, ref="r1"),
            _make_terminal_turn(text="recovered"),
        ])
        router = LLMRouter()
        _patch_clients(router)
        executor = AsyncMock(side_effect=RuntimeError("boom"))
        with _patch_adapters(adapter):
            result = await router.complete_with_tools(
                "x",
                tools=[_FakeTool("forge_list")],
                tool_executor=executor,
            )
        assert len(result.tool_trace) == 1
        entry = result.tool_trace[0]
        assert entry["tool_name"] == "forge_list"
        assert entry["error"] is not None
        assert isinstance(entry["error"], str) and entry["error"]
        assert entry["result"] is None
        # Failure must also appear in messages (parallel surface).
        tool_msgs = [m for m in result.messages if m.get("role") == "tool"]
        assert len(tool_msgs) == 1, (
            f"failed tool call missing from messages: {result.messages!r}"
        )

    @pytest.mark.asyncio
    async def test_tool_trace_index_monotonic_across_chain(self):
        """Multi-tool chain: indices are 0, 1, 2, ... in invocation order."""
        adapter = _StubAdapter([
            _make_tool_call_turn("forge_a", {}, ref="r1"),
            _make_tool_call_turn("forge_b", {}, ref="r2"),
            _make_terminal_turn(text="end"),
        ])
        router = LLMRouter()
        _patch_clients(router)
        with _patch_adapters(adapter):
            result = await router.complete_with_tools(
                "x",
                tools=[_FakeTool("forge_a"), _FakeTool("forge_b")],
                tool_executor=AsyncMock(return_value="ok"),
            )
        assert [e["index"] for e in result.tool_trace] == [0, 1]
        assert [e["tool_name"] for e in result.tool_trace] == ["forge_a", "forge_b"]
