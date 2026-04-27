"""Provider-neutral tool-call adapter contract + Anthropic / Ollama implementations.

Per FB-C D-01: ONE coordinator (LLMRouter.complete_with_tools, plan 15-08) +
TWO thin adapter modules. The coordinator owns the loop logic (~80% of code);
the adapters own one thing each: translating between canonical conversation
state and the provider's wire format.

Per FB-C D-02: adapters use NATIVE provider clients (anthropic.AsyncAnthropic,
ollama.AsyncClient). The OpenAI-compat shim is preserved only for acomplete().

Per FB-C D-06: serial tool execution by default. supports_parallel=False on
both adapters; AnthropicToolAdapter additionally sends disable_parallel_tool_use=True.

Per FB-C D-29: _OLLAMA_TOOL_MODELS soft allow-list. Unrecognized model emits
WARNING (does NOT hard-fail).

Per FB-C D-31: Anthropic strict=true always-on per tool definition WITH per-tool
downgrade fallback when Anthropic returns 400 schema-validation errors.

Per FB-C D-33: Ollama keep_alive="10m" on every request (research §6.8).

Per FB-C D-35: token accounting normalized to (prompt_tokens, completion_tokens).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from forge_bridge.llm.router import LLMToolError

if TYPE_CHECKING:  # pragma: no cover
    import anthropic
    import mcp.types
    import ollama

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


# D-29: Ollama models with verified tool-calling reliability for forge-bridge.
# Soft allow-list — local_model not in this set emits WARNING but does NOT
# hard-fail (artist-experimentation friendly per CONTEXT.md D-29).
_OLLAMA_TOOL_MODELS: frozenset[str] = frozenset({
    "qwen3:32b",
    "qwen3-coder:32b",
    "qwen2.5-coder:32b",
    "llama3.1:70b",
    "mixtral:8x22b",
})

# D-33: Ollama keep_alive sent on every chat request (research §6.8).
_OLLAMA_KEEP_ALIVE: str = "10m"


# ---------------------------------------------------------------------------
# Canonical dataclasses (research §4.1, §4.4)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolCallResult:
    """One canonical tool-call result (frozen — Phase 8 ExecutionRecord precedent).

    Fields:
        tool_call_ref: Opaque provider-specific ref. Anthropic stuffs the toolu_*
                       id; Ollama stuffs a synthetic "{idx}:{name}" composite.
        tool_name: The name of the tool that was invoked (or attempted).
        content: Tool result content as a string (already sanitized by coordinator).
        is_error: True for tool exceptions / timeouts / hallucinated names /
                  repeat-call rejections.
    """

    tool_call_ref: str
    tool_name: str
    content: str
    is_error: bool


@dataclass
class _ToolCall:
    """One canonical tool-call request emitted by the LLM (mutable, hot-path).

    Fields:
        ref: Opaque provider-specific reference (round-trips to ToolCallResult).
        tool_name: The name the model wants to call.
        arguments: Parsed argument dict.
    """

    ref: str
    tool_name: str
    arguments: dict


@dataclass
class _TurnResponse:
    """One adapter-normalized response from the provider for a single turn.

    Fields:
        text: Assistant's plain text content (may be empty when only tool calls).
        tool_calls: Parsed _ToolCall list. EMPTY = loop terminal state.
        usage_tokens: (prompt_tokens, completion_tokens) per D-35.
        raw: Provider-native response object — adapter-internal use only.
    """

    text: str
    tool_calls: list[_ToolCall]
    usage_tokens: tuple[int, int]
    raw: object


# ---------------------------------------------------------------------------
# Adapter Protocol contract (research §4.4)
# ---------------------------------------------------------------------------


class _ToolAdapter(Protocol):
    """Provider-neutral tool-call adapter contract.

    Coordinator (LLMRouter.complete_with_tools) selects implementation by
    sensitivity bit: True → OllamaToolAdapter, False → AnthropicToolAdapter.
    Tests use _StubAdapter (D-37) in tests/llm/conftest.py for deterministic
    coordinator-logic exercises.
    """

    supports_parallel: bool

    def init_state(
        self,
        *,
        prompt: str,
        system: str,
        tools: list[Any],
        temperature: float,
    ) -> Any: ...

    async def send_turn(self, state: Any) -> _TurnResponse: ...

    def append_results(
        self,
        state: Any,
        response: _TurnResponse,
        results: list[ToolCallResult],
    ) -> Any: ...


# ---------------------------------------------------------------------------
# Anthropic adapter
# ---------------------------------------------------------------------------


class AnthropicToolAdapter:
    """Anthropic Messages API adapter (D-01, D-06, D-31, D-35)."""

    supports_parallel = False  # D-06

    def __init__(self, client: "anthropic.AsyncAnthropic", model: str) -> None:
        self._client = client
        self._model = model
        # D-31 sticky per-session downgrade tracking.
        self._downgraded_tools: set[str] = set()

    def init_state(
        self,
        *,
        prompt: str,
        system: str,
        tools: list[Any],
        temperature: float,
    ) -> dict:
        return {
            "messages": [{"role": "user", "content": prompt}],
            "system": system,
            "temperature": temperature,
            "tools_source": list(tools),
        }

    def _compile_tools(self, tools_source: list[Any]) -> list[dict]:
        """Translate forge MCP Tool list → Anthropic tools[] (research §5.1).

        D-31: strict=True by default; downgraded tools omit it.
        """
        compiled: list[dict] = []
        for tool in tools_source:
            entry: dict[str, Any] = {
                "name": tool.name,
                "description": tool.description or "",
                "input_schema": tool.inputSchema,
            }
            if tool.name not in self._downgraded_tools:
                entry["strict"] = True
            compiled.append(entry)
        return compiled

    async def send_turn(self, state: dict) -> _TurnResponse:
        """Send turn to Anthropic. On schema-validation 400, downgrade and retry.

        D-06: disable_parallel_tool_use=True at top level.
        D-35: usage_tokens = (input_tokens, output_tokens).
        Phase 8 cf221fe credential-leak rule: log type(exc).__name__ only.
        """
        tools_payload = self._compile_tools(state["tools_source"])

        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=4096,
                system=state["system"],
                messages=state["messages"],
                temperature=state["temperature"],
                tools=tools_payload,
                disable_parallel_tool_use=True,
            )
        except Exception as exc:  # noqa: BLE001 — credential-leak rule
            exc_type = type(exc).__name__
            err_str = str(exc)  # used ONLY for tool-name extraction; never logged
            for tool in state["tools_source"]:
                if tool.name in self._downgraded_tools:
                    continue
                if exc_type.endswith(("BadRequestError", "APIStatusError")) and tool.name in err_str:
                    logger.warning(
                        "downgraded tool %r to strict=false after Anthropic 400; "
                        "check inputSchema compatibility",
                        tool.name,
                    )
                    self._downgraded_tools.add(tool.name)
                    return await self.send_turn(state)  # one retry
            raise LLMToolError(f"Anthropic call failed: {exc_type}") from exc

        text_parts: list[str] = []
        tool_calls: list[_ToolCall] = []
        for block in response.content:
            block_type = getattr(block, "type", None)
            if block_type == "text":
                text_parts.append(block.text)
            elif block_type == "tool_use":
                tool_calls.append(_ToolCall(
                    ref=block.id,
                    tool_name=block.name,
                    arguments=dict(block.input) if block.input else {},
                ))

        usage = getattr(response, "usage", None)
        prompt_tokens = getattr(usage, "input_tokens", 0) if usage else 0
        completion_tokens = getattr(usage, "output_tokens", 0) if usage else 0

        return _TurnResponse(
            text="".join(text_parts),
            tool_calls=tool_calls,
            usage_tokens=(prompt_tokens, completion_tokens),
            raw=response,
        )

    def append_results(
        self,
        state: dict,
        response: _TurnResponse,
        results: list[ToolCallResult],
    ) -> dict:
        """Append assistant turn + tool_result blocks (research §2.3 hard rules)."""
        assistant_content: list[dict] = []
        for block in response.raw.content:
            block_type = getattr(block, "type", None)
            if block_type == "text":
                assistant_content.append({"type": "text", "text": block.text})
            elif block_type == "tool_use":
                assistant_content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })

        # tool_result blocks MUST come FIRST in user content (§2.3 rule 2).
        user_content: list[dict] = [
            {
                "type": "tool_result",
                "tool_use_id": r.tool_call_ref,
                "content": r.content,
                "is_error": r.is_error,
            }
            for r in results
        ]

        new_messages = list(state["messages"])
        new_messages.append({"role": "assistant", "content": assistant_content})
        new_messages.append({"role": "user", "content": user_content})

        return {**state, "messages": new_messages}


# ---------------------------------------------------------------------------
# Ollama adapter
# ---------------------------------------------------------------------------


class OllamaToolAdapter:
    """Ollama native tool-call adapter (D-02, D-06, D-29, D-33, D-35)."""

    supports_parallel = False  # D-06

    def __init__(self, client: "ollama.AsyncClient", model: str) -> None:
        self._client = client
        self._model = model
        if model not in _OLLAMA_TOOL_MODELS:
            logger.warning(
                "local_model %r is not in _OLLAMA_TOOL_MODELS allow-list; "
                "tool-call reliability may be unverified",
                model,
            )

    def init_state(
        self,
        *,
        prompt: str,
        system: str,
        tools: list[Any],
        temperature: float,
    ) -> dict:
        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return {
            "messages": messages,
            "temperature": temperature,
            "tools_compiled": self._compile_tools(tools),
        }

    @staticmethod
    def _compile_tools(tools: list[Any]) -> list[dict]:
        """Translate to Ollama function-wrapped form (research §3.1)."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.inputSchema,
                },
            }
            for tool in tools
        ]

    async def send_turn(self, state: dict) -> _TurnResponse:
        """Send turn to Ollama with keep_alive (D-33).

        D-35: usage_tokens = (prompt_eval_count, eval_count).
        """
        try:
            response = await self._client.chat(
                model=self._model,
                messages=state["messages"],
                tools=state["tools_compiled"],
                stream=False,
                keep_alive=_OLLAMA_KEEP_ALIVE,
                options={"temperature": state["temperature"]},
            )
        except Exception as exc:  # noqa: BLE001 — credential-leak rule
            raise LLMToolError(f"Ollama call failed: {type(exc).__name__}") from exc

        # Both dict-shape (older / mocked) and pydantic-model-shape (ollama>=0.6.1) supported.
        if isinstance(response, dict):
            message = response.get("message") or {}
        else:
            message = getattr(response, "message", None) or {}

        if isinstance(message, dict):
            text = message.get("content") or ""
            raw_tool_calls = message.get("tool_calls") or []
        else:
            text = getattr(message, "content", "") or ""
            raw_tool_calls = getattr(message, "tool_calls", None) or []

        tool_calls: list[_ToolCall] = []
        for idx, call in enumerate(raw_tool_calls):
            if isinstance(call, dict):
                fn = call.get("function") or {}
                name = fn.get("name", "") or ""
                args = fn.get("arguments") or {}
            else:
                fn = getattr(call, "function", None)
                name = getattr(fn, "name", "") if fn else ""
                args = getattr(fn, "arguments", None) or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:  # noqa: BLE001
                    args = {}
            tool_calls.append(_ToolCall(
                ref=f"{idx}:{name}",  # composite ref (research §5.2)
                tool_name=name,
                arguments=dict(args) if args else {},
            ))

        if isinstance(response, dict):
            prompt_tokens = response.get("prompt_eval_count", 0) or 0
            completion_tokens = response.get("eval_count", 0) or 0
        else:
            prompt_tokens = getattr(response, "prompt_eval_count", 0) or 0
            completion_tokens = getattr(response, "eval_count", 0) or 0

        return _TurnResponse(
            text=text,
            tool_calls=tool_calls,
            usage_tokens=(prompt_tokens, completion_tokens),
            raw=response,
        )

    def append_results(
        self,
        state: dict,
        response: _TurnResponse,
        results: list[ToolCallResult],
    ) -> dict:
        """Append assistant turn + role:tool messages (research §3.3)."""
        new_messages = list(state["messages"])

        assistant_msg: dict[str, Any] = {
            "role": "assistant",
            "content": response.text or "",
        }
        if response.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "type": "function",
                    "function": {"name": tc.tool_name, "arguments": tc.arguments},
                }
                for tc in response.tool_calls
            ]
        new_messages.append(assistant_msg)

        # ORDER preserved (Ollama uses ORDER-based matching per §3.3).
        for r in results:
            new_messages.append({
                "role": "tool",
                "tool_name": r.tool_name,
                "content": r.content,
            })

        return {**state, "messages": new_messages}
