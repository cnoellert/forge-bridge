"""Shared fixtures for tests/llm/ — FB-C LLMRouter tool-call loop tests.

Provides:
    _StubAdapter (D-37) — deterministic adapter that replays a scripted
        sequence of _TurnResponse. Used by Wave 3 plan 15-08's coordinator
        unit tests (tests/llm/test_complete_with_tools.py) so loop logic
        can be exercised without a live LLM.

    mock_ollama — patches sys.modules['ollama'] with a MagicMock. Mirrors
        the existing mock_anthropic fixture in tests/conftest.py:55-64 so
        tests can run without the ollama package installed.

    stub_adapter — pytest fixture that returns the _StubAdapter class
        (callers instantiate with their scripted sequence).
"""
from __future__ import annotations

from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from forge_bridge.llm._adapters import _ToolCall, _TurnResponse, ToolCallResult


# ---------------------------------------------------------------------------
# Stub adapter for deterministic coordinator tests (D-37)
# ---------------------------------------------------------------------------


class _StubAdapter:
    """Deterministic adapter that replays a scripted sequence of _TurnResponse.

    Lets every loop-logic test be deterministic without a live LLM. Used by
    Wave 3 plan 15-08's tests/llm/test_complete_with_tools.py to exercise:
      - happy-path two-turn loop (LLMTOOL-01-style: tool call → result → terminal)
      - LLMTOOL-04 repeat-call detection (stub emits same tool_call three times)
      - LLMTOOL-03 budget caps (stub emits enough turns to exhaust max_iterations)
      - hallucinated tool name (stub emits a tool_name not in the registered list)
      - tool execution failure (coordinator catches; stub keeps emitting)

    Per D-37: scripted_responses is consumed in order. If the loop overruns
    the script, IndexError surfaces — that's a test bug (the script must
    cover every send_turn the loop will perform).
    """

    supports_parallel = False  # matches both real adapters (D-06)

    def __init__(self, scripted_responses: list[_TurnResponse]) -> None:
        self._scripted: list[_TurnResponse] = list(scripted_responses)
        # Public for tests to inspect what the coordinator appended.
        self.appended_results: list[list[ToolCallResult]] = []
        self.last_state: dict | None = None

    def init_state(
        self,
        *,
        prompt: str,
        system: str,
        tools: list,
        temperature: float,
        messages: Optional[list[dict]] = None,    # D-02a (FB-D plan 16-01)
    ) -> dict:
        # D-02a: mirror the production adapters — when messages is provided,
        # the stub records it verbatim; otherwise auto-wrap prompt.
        history = (
            list(messages)
            if messages is not None
            else [{"role": "user", "content": prompt}]
        )
        return {
            "prompt": prompt,
            "system": system,
            "tools": list(tools),
            "temperature": temperature,
            "history": history,
            # Public for tests to inspect what init_state received via the
            # D-02a messages= kwarg path (None when auto-wrap path was taken).
            "messages_kwarg": messages,
        }

    async def send_turn(self, state: dict) -> _TurnResponse:
        if not self._scripted:
            raise IndexError(
                "_StubAdapter scripted sequence exhausted — extend the test's "
                "scripted_responses list to cover this turn."
            )
        self.last_state = state
        return self._scripted.pop(0)

    def append_results(
        self,
        state: dict,
        response: _TurnResponse,
        results: list[ToolCallResult],
    ) -> dict:
        # Record what the coordinator handed us so tests can assert on it.
        self.appended_results.append(list(results))
        new_history = list(state["history"])
        new_history.append({"role": "assistant", "content": response.text})
        for r in results:
            new_history.append({
                "role": "tool",
                "tool_name": r.tool_name,
                "content": r.content,
                "is_error": r.is_error,
            })
        return {**state, "history": new_history}


@pytest.fixture
def stub_adapter():
    """Return the _StubAdapter class. Tests instantiate with their scripted list:

        def test_x(stub_adapter):
            adapter = stub_adapter([_TurnResponse(text="hi", tool_calls=[], usage_tokens=(0,0), raw=None)])
            ...
    """
    return _StubAdapter


# ---------------------------------------------------------------------------
# Module mocks (mirror tests/conftest.py::mock_anthropic — sys.modules patching)
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_ollama():
    """Patch ollama at module level so tests run without the package installed.

    Mirrors the mock_anthropic fixture in tests/conftest.py:55-64. Individual
    tests configure mock_ollama.AsyncClient.return_value as needed.
    """
    mock = MagicMock()
    with patch.dict("sys.modules", {"ollama": mock}):
        yield mock


# ---------------------------------------------------------------------------
# Convenience builders for tests
# ---------------------------------------------------------------------------


def _make_terminal_turn(text: str = "done", prompt_tokens: int = 10, completion_tokens: int = 5) -> _TurnResponse:
    """Build a terminal _TurnResponse (empty tool_calls = loop exits)."""
    return _TurnResponse(
        text=text,
        tool_calls=[],
        usage_tokens=(prompt_tokens, completion_tokens),
        raw=None,
    )


def _make_tool_call_turn(
    tool_name: str,
    args: dict,
    ref: str = "stub_ref_0",
    text: str = "",
    prompt_tokens: int = 20,
    completion_tokens: int = 10,
) -> _TurnResponse:
    """Build a _TurnResponse with a single tool_call (loop continues)."""
    return _TurnResponse(
        text=text,
        tool_calls=[_ToolCall(ref=ref, tool_name=tool_name, arguments=args)],
        usage_tokens=(prompt_tokens, completion_tokens),
        raw=None,
    )


@pytest.fixture
def make_terminal_turn():
    """Fixture exposing _make_terminal_turn for inline test convenience."""
    return _make_terminal_turn


@pytest.fixture
def make_tool_call_turn():
    """Fixture exposing _make_tool_call_turn for inline test convenience."""
    return _make_tool_call_turn
