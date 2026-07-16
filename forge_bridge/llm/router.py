"""
forge_bridge.llm.router
-----------------------
Async LLM router for forge-bridge.

Routes LLM requests to local Ollama or cloud Anthropic Claude
based on data sensitivity.

Sensitive data (shot names, client info, file paths, SQL, openclip XML) -> local
Architecture / design reasoning, non-sensitive -> cloud

Usage:
    from forge_bridge.llm.router import LLMRouter

    router = LLMRouter()

    # Sensitive -- stays on local network (async)
    result = await router.acomplete(
        "Write a regex to extract shot name from: PROJ_0010_comp_v003",
        sensitive=True
    )

    # Non-sensitive -- uses Claude (sync wrapper, outside async context only)
    design = router.complete(
        "What's the best pattern for async Flame export callbacks?",
        sensitive=False
    )
"""

import asyncio
import collections
import contextvars
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional, TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    import ollama
    from anthropic import AsyncAnthropic
    from openai import AsyncOpenAI

    from forge_bridge.llm._adapters import _TurnResponse


# ---------------------------------------------------------------------------
# Phase A chat-contract realignment (2026-05-05)
#
# ChatTurnResult is the load-bearing return type of complete_with_tools().
# Chosen as a frozen dataclass over a 3-tuple because:
#
#   1. The contract is meant to be impossible to misuse — a named type
#      surfaces drift through every call site, not just at the unpack.
#   2. Future fields (usage_tokens, completed_iterations, terminal_reason)
#      are obvious next additions; positional unpacks would silently break
#      if a 4th tuple element were appended.
#   3. Self-documenting at every read: result.final_text is unambiguous;
#      result[0] is not.
#
# Mutation through this dataclass is forbidden — the router builds it once
# at the loop's terminal moment and hands ownership to the handler.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OrchestrationTerminationEnvelope:
    """Structured terminal payload emitted when Phase 24.4 K-fold canonical
    recurrence fires and the orchestrator takes deterministic termination
    authority over the agentic loop.

    Per `.planning/milestones/v1.6-PHASE-24-4-FRAMING.md` §5: the envelope
    distinguishes orchestration-decided termination from model-decided
    termination (Phase A canonical-schema success path) and from runtime
    budget exhaustion (LLMLoopBudgetExceeded → HTTP 504). It is NOT a
    failure — it is a policy-layer success.

    Anti-scope (framing §5.1, §10): the orchestrator MUST NOT synthesize
    conversational text in this envelope. ``accumulated_results`` carries
    the verbatim post-sanitization bytes that flowed back to the LLM; the
    downstream surface (chat handler / Console UI / CLI) decides how to
    present them to the operator.

    Fields:
        status: Always ``"orchestration_terminated"`` — the enum-like
            marker that distinguishes this envelope from canonical-schema
            success (``stop_reason="end_turn"``).
        trigger: Taxonomic name of the trigger that fired. v1.6 ships
            ``"k_fold_canonical"``; future triggers each get their own
            structurally-named string (framing §10.1).
        reason: Human-readable description of what the orchestrator
            observed (tool name + K count + recurrence shape). Telemetry +
            archaeology, NOT model-facing prose.
        iterations: 1-based count of iterations completed before the
            trigger fired. Matches the ``iter`` value in the K-th
            accumulated_results entry.
        accumulated_results: Every successful ``status=ok`` tool dispatch
            in this session, in invocation order. Each entry:
            ``{tool_name, args_hash, result_hash, content, iter}`` where
            ``content`` is the exact post-sanitization, post-truncation
            bytes shown to the LLM. Failed dispatches are NOT included —
            they live in ``ChatTurnResult.tool_trace``.
    """

    status: str
    trigger: str
    reason: str
    iterations: int
    accumulated_results: list[dict] = field(default_factory=list)


@dataclass(frozen=True)
class ChatTurnResult:
    """Structured return shape for ``LLMRouter.complete_with_tools()``.

    Phase A invariant: the chat endpoint cannot lose tool execution history.
    Every successful call surfaces the full conversation transcript and a
    structured trace of every tool that was invoked.

    Fields:
        final_text: The model's terminal assistant text. Identical to
            ``messages[-1]["content"]`` by construction in the model-
            terminated case. Empty string ``""`` when ``termination`` is
            populated (Phase 24.4 orchestration-terminated case — the
            orchestrator does NOT synthesize conversational text per
            framing §5.1).
        messages: Full transcript in OpenAI-style chat format —
            ``{role, content, tool_calls?, tool_call_id?, name?}``. Provider-
            native shapes (Anthropic content blocks) are normalized at the
            adapter boundary; no native format leaks past the router. In
            the model-terminated case, ``messages[-1]`` is the terminal
            assistant turn. In the orchestration-terminated case
            (``termination is not None``), ``messages`` is the transcript
            at the iteration where the trigger fired — ending with the
            K-th identical successful tool result, NOT a synthetic
            assistant turn (framing §10.1).
        tool_trace: One entry per tool invocation, in invocation order.
            Each entry: ``{tool_name, arguments, result, error, index}``.
            On success: ``error is None`` and ``result`` is the parsed value.
            On failure: ``result is None`` and ``error`` is a string. Never
            both populated, never both null. Empty when no tools were called.
        termination: Phase 24.4 — populated when the orchestrator's K-fold
            canonical-recurrence trigger fires, ``None`` otherwise. When
            populated, the loop terminated by orchestration policy, not
            by model choice and not by budget exhaustion. See
            ``OrchestrationTerminationEnvelope`` for field shape.
    """

    final_text: str
    messages: list[dict]
    tool_trace: list[dict] = field(default_factory=list)
    termination: Optional["OrchestrationTerminationEnvelope"] = None

# Default system prompt injected into every local call.
# Keeps Flame/pipeline context in scope without repeating it per-call.
# Deployment-specific strings (hostnames, DB creds, machine specs) are excluded —
# callers that need them can pass system_prompt= to LLMRouter() or acomplete().
_DEFAULT_SYSTEM_PROMPT = """
You are a VFX pipeline assistant embedded in a toolkit of Autodesk Flame
Python tools for shot management and publishing.

Key context:
- Flame version: 2026, Python API via `import flame`
- Shot naming convention: {project}_{shot}_{layer}_v{version}  e.g. PROJ_0010_comp_v003
- Openclip files: XML-based multi-version containers written by Flame's MIO
  reader. Use Flame's native bracket notation [0991-1017] for frame ranges,
  NOT printf %04d notation.

Respond with concise, production-ready Python unless asked otherwise.
""".strip()


# Default Ollama model used for sensitive (local-network) completions.
# qwen2.5-coder:14b is the Phase 24.3 swap from qwen2.5-coder:32b (which was the
# v1.4 conservative-bump-first baseline per Phase 15 D-28). Swap justified by
# .planning/milestones/v1.6-PHASE-24-3-BASELINE-32B.md — 32b cold prefix produced
# 0 tokens in the 120s budget, warm prefix dispatched correctly but never
# terminated (model looped on same flame_execute_python invocation).
# Override via the FORGE_LOCAL_MODEL env var or the local_model= kwarg on LLMRouter().
_DEFAULT_LOCAL_MODEL = "qwen2.5-coder:14b"

# Default Anthropic model used for non-sensitive (cloud) completions.
# claude-sonnet-4-6 is the Phase 17 (v1.4.x) bump from claude-opus-4-6 (deprecated;
# returned 500 from the live Anthropic API per v1.4 LLMTOOL-02 UAT). Verified
# passing in v1.4 LLMTOOL-02 UAT after the tool_choice + additionalProperties:
# false adapter fixes. See SEED-OPUS-4-7-TEMPERATURE-V1.5 for the next bump path.
# Override via the FORGE_CLOUD_MODEL env var or the cloud_model= kwarg on LLMRouter().
_DEFAULT_CLOUD_MODEL = "claude-sonnet-4-6"


# ---------------------------------------------------------------------------
# FB-C public exception classes (D-15..D-19, exported from forge_bridge.__all__)
#
# Caught by Phase 16 (FB-D) /api/v1/chat endpoint and mapped to HTTP status:
#   LLMLoopBudgetExceeded  -> HTTP 504 (gateway timeout)
#   RecursiveToolLoopError -> HTTP 500 (internal error — caller bug)
#   LLMToolError           -> HTTP 502 (bad gateway — provider failure)
#
# Module-cohesion placement (D-16): defined alongside LLMRouter in router.py,
# matching the Phase 8 StoragePersistence-next-to-ExecutionLog precedent in
# learning/storage.py. No separate _errors.py file.
# ---------------------------------------------------------------------------


class LLMLoopBudgetExceeded(RuntimeError):
    """Raised when complete_with_tools() exceeds its iteration or wall-clock cap.

    Attributes:
        reason: One of "max_iterations" | "max_seconds". Indicates which cap fired.
        iterations: Iterations completed before the cap fired. -1 if the wall-clock
                    timeout fired before the next iteration was counted.
        elapsed_s: Wall-clock seconds elapsed when the cap fired.

    Caught by Phase 16 (FB-D) and mapped to HTTP 504 (gateway timeout).
    Signature locked verbatim per FB-C D-18 / research §4.1.
    """

    def __init__(self, reason: str, iterations: int, elapsed_s: float):
        super().__init__(
            f"{reason} (iterations={iterations}, elapsed={elapsed_s:.1f}s)"
        )
        self.reason = reason
        self.iterations = iterations
        self.elapsed_s = elapsed_s


class RecursiveToolLoopError(RuntimeError):
    """Raised when complete_with_tools() or acomplete() detects a recursive call.

    Detection mechanism: the contextvar `_in_tool_loop` is set on entry to
    complete_with_tools() (via try/finally for cleanup); both acomplete() and
    complete_with_tools() check it on entry. A True value means the current
    coroutine is already inside an outer tool-call loop — typically a
    synthesized tool body that calls back into the LLM, which is exactly the
    recursive-synthesis attack surface LLMTOOL-07 (D-12..D-14) blocks.

    Belt-and-suspenders against the synthesizer's static AST blocklist
    (also extended in plan 15-06 to reject `forge_bridge.llm` imports).

    Caught by Phase 16 (FB-D) and mapped to HTTP 500 (internal error — caller bug).
    Per FB-C D-19, this exception carries no extra fields in v1.4.
    """


class LLMToolError(RuntimeError):
    """Raised by the coordinator on unrecoverable adapter / API errors.

    Examples:
        - Anthropic 5xx after SDK-internal retry budget is exhausted (research §6.7)
        - Ollama daemon unreachable mid-loop after retry
        - Schema-translation failures the adapter cannot recover from

    Distinct from per-tool errors (which the coordinator surfaces back to the LLM
    as `is_error=True` ToolCallResult and continues the loop per LLMTOOL-03 acceptance).
    LLMToolError aborts the session — there is no recovery path inside the loop.

    Caught by Phase 16 (FB-D) and mapped to HTTP 502 (bad gateway — provider failure).
    Per FB-C D-19, this exception carries no extra fields in v1.4. Future fields
    (e.g., chained anthropic.APIError) deferred to v1.5 if FB-D needs them.
    """


class CompileError(RuntimeError):
    """Base for all compile-stage structural failures."""


class CompileUnresolvableIntent(CompileError):
    """LLM produced no recognizable graph-intent."""

    def __init__(self, raw_response: str):
        super().__init__("compile_intent produced no recognizable graph-intent")
        self.raw_response = _truncate_compile_raw(raw_response)


class CompileInvalidChainShape(CompileError):
    """LLM output could not parse to list[str] chain steps."""

    def __init__(self, raw_response: str, parse_error: str):
        super().__init__(f"compile_intent produced invalid chain shape: {parse_error}")
        self.raw_response = _truncate_compile_raw(raw_response)
        self.parse_error = parse_error


class CompileToolUnknown(CompileError):
    """Compiled graph references a tool name not in the registered set."""

    def __init__(self, unknown_tool: str, step_index: int, step_text: str):
        super().__init__(
            f"compile_intent referenced unknown tool {unknown_tool!r} "
            f"at step {step_index}"
        )
        self.unknown_tool = unknown_tool
        self.step_index = step_index
        self.step_text = step_text


class CompileSeamViolation(CompileError):
    """Compiled graph produced host mutation without a paired commit step."""

    def __init__(self, offending_step_text: str, offending_step_index: int):
        super().__init__(
            "compile_intent produced a host-mutation step without a paired "
            f"commit step at index {offending_step_index}"
        )
        self.offending_step_text = offending_step_text
        self.offending_step_index = offending_step_index


class CompileBudgetExceeded(CompileError):
    """Wall-clock cap fired before compile_intent's LLM call returned."""

    def __init__(self, max_seconds: float, elapsed_s: float):
        super().__init__(
            f"compile_intent exceeded {max_seconds:.1f}s "
            f"(elapsed={elapsed_s:.1f}s)"
        )
        self.max_seconds = max_seconds
        self.elapsed_s = elapsed_s


# ---------------------------------------------------------------------------
# Phase 24.4 internal control-flow signal (NOT exported)
#
# Per `.planning/milestones/v1.6-PHASE-24-4-FRAMING.md` §5: when the K-fold
# canonical-recurrence trigger fires inside _loop_body, the orchestrator
# needs to unwind cleanly to the outer try/except so the caller receives a
# ChatTurnResult with the termination envelope populated — NOT an
# LLMLoopBudgetExceeded (HTTP 504) and NOT an unhandled exception (HTTP 500).
#
# This is a private signal class, not a public exception. Caught exactly
# once in complete_with_tools()'s outer try/except. Not added to
# forge_bridge.__all__ — handler code interacts with the termination
# envelope through ChatTurnResult.termination, never through this class.
# ---------------------------------------------------------------------------


class _OrchestrationTerminated(Exception):
    """Internal signal raised by _loop_body when the Phase 24.4 K-fold
    canonical trigger fires. Carries the assembled envelope so the outer
    handler can construct ChatTurnResult without re-deriving state.

    Anti-scope (framing §10.1): this signal is the ONLY mechanism that
    bypasses the model-decided ``return response.text`` path. It does NOT
    inject prompts, does NOT synthesize content, does NOT alter the
    transcript — it carries already-collected orchestration-layer state
    out of the loop.
    """

    def __init__(
        self,
        envelope: "OrchestrationTerminationEnvelope",
        state_messages: list[dict],
        completed_iterations: int,
    ):
        super().__init__(
            f"orchestration_terminated trigger={envelope.trigger} "
            f"iter={envelope.iterations}"
        )
        self.envelope = envelope
        self.state_messages = state_messages
        self.completed_iterations = completed_iterations


# ---------------------------------------------------------------------------
# FB-C recursive-synthesis guard (LLMTOOL-07, D-12..D-14)
# ---------------------------------------------------------------------------
#
# Belt-and-suspenders against synthesized tools that try to call back into the
# LLM (recursive synthesis attack surface — research §6.3). Three layers:
#
#   1. Static AST check at synthesis time (forge_bridge/learning/synthesizer.py
#      _check_safety() — extended in plan 15-06 Task 2 to reject any
#      synthesized code that imports from forge_bridge.llm).
#   2. Runtime ContextVar check at LLM-call time (this declaration). Set inside
#      complete_with_tools() by Wave 3 plan 15-08 via try/finally; checked on
#      entry to acomplete() (this plan Task 1) and complete_with_tools() (Wave 3).
#   3. Process-level safeguard via existing synthesizer quarantine (Phase 3 —
#      already shipped — bad code never makes it into the registered tool surface).

_in_tool_loop: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "_in_tool_loop", default=False
)


def _truncate_compile_raw(raw: str) -> str:
    text = "" if raw is None else str(raw)
    if len(text) <= 2048:
        return text
    return text[:2048]


def _tool_name(tool: Any) -> str | None:
    if isinstance(tool, dict):
        value = tool.get("name")
    else:
        value = getattr(tool, "name", None)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _tool_description(tool: Any) -> str:
    if isinstance(tool, dict):
        value = tool.get("description", "")
    else:
        value = getattr(tool, "description", "")
    return str(value or "").strip()


def _default_compile_system_prompt(tools: list) -> str:
    catalogue_lines = []
    for tool in tools:
        name = _tool_name(tool)
        if not name:
            continue
        description = _tool_description(tool)
        if description:
            catalogue_lines.append(f"- {name}: {description}")
        else:
            catalogue_lines.append(f"- {name}")
    catalogue = "\n".join(catalogue_lines) or "- (no tools supplied)"
    return (
        "You compile an operator's natural-language request into "
        "forge-bridge chain-step text.\n\n"
        "Return only the chain-step text. Use the literal `->` separator "
        "between ordered steps. Do not include explanations, Markdown, or "
        "extra natural language around the chain.\n\n"
        "Each step's arguments travel inline with its tool name "
        "(`tool_name arg=value ...`); an args object is never its own step.\n\n"
        "A space-bearing entity name is a single quoted literal: preserve the "
        "space exactly, never normalize spaces to underscores, and never "
        "substitute a near-looking known entity.\n\n"
        "Available tools:\n"
        f"{catalogue}\n\n"
        "`commit` is the authority-transition keyword: it is used only "
        "when a previewed host mutation is ready to cross into apply."
    )


def _strip_compile_fence(raw: str) -> str:
    text = raw.strip()
    if not text.startswith("```") or not text.endswith("```"):
        return text
    lines = text.splitlines()
    if len(lines) < 2:
        return text
    return "\n".join(lines[1:-1]).strip()


def _top_level_chain_segments(raw: str) -> list[str]:
    segments: list[str] = []
    start = 0
    depth = 0
    index = 0
    while index < len(raw):
        char = raw[index]
        if char == "(":
            depth += 1
            index += 1
            continue
        if char == ")":
            depth = max(0, depth - 1)
            index += 1
            continue
        if depth == 0 and raw.startswith("->", index):
            segments.append(raw[start:index].strip())
            index += 2
            start = index
            continue
        index += 1
    segments.append(raw[start:].strip())
    return segments


def _structured_compile_step_text(item: Any, available_names: set[str], index: int) -> str:
    if isinstance(item, str):
        text = item.strip()
        if not text:
            raise CompileInvalidChainShape(str(item), f"empty step at index {index}")
        return text
    if not isinstance(item, dict):
        raise CompileInvalidChainShape(
            json.dumps(item, default=str),
            f"step {index} is not a string or object",
        )
    tool_name = item.get("tool_name") or item.get("tool") or item.get("name")
    if not isinstance(tool_name, str) or not tool_name.strip():
        text = item.get("step") or item.get("step_text") or item.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()
        return json.dumps(item, default=str)
    tool_name = tool_name.strip()
    if tool_name not in available_names:
        raise CompileToolUnknown(tool_name, index, json.dumps(item, sort_keys=True))
    arguments = item.get("arguments") or item.get("args") or {}
    if not isinstance(arguments, dict) or not arguments:
        return tool_name
    args_text = " ".join(f"{key}={value}" for key, value in arguments.items())
    return f"{tool_name} {args_text}".strip()


def _is_bare_args_step(step: str) -> bool:
    return step.strip().startswith("{")


def _is_tool_name_only_step(step: str) -> bool:
    stripped = step.strip()
    if not stripped or len(stripped.split()) != 1:
        return False
    return "_" in stripped or stripped == "commit"


def _validate_chain_shape(steps: list[str]) -> None:
    for index, step in enumerate(steps):
        text = str(step).strip()
        if not text:
            raise CompileInvalidChainShape(str(step), f"empty step at index {index}")
        if _is_bare_args_step(text):
            raise CompileInvalidChainShape(
                text,
                f"detached args step at index {index}",
            )
        first = text.split(maxsplit=1)[0]
        if "_" not in first and first != "commit":
            raise CompileInvalidChainShape(
                text,
                f"non-tool step at index {index}",
            )


def _append_salvage_reason(salvage_record: dict | None, reason: str) -> dict:
    if salvage_record is None:
        return {
            "salvage_applied": True,
            "original_reason": reason,
        }
    existing = str(salvage_record.get("original_reason") or "")
    reasons = [part for part in existing.split("+") if part]
    reasons.append(reason)
    return {
        "salvage_applied": True,
        "original_reason": "+".join(reasons),
    }


def normalize_chain_shape(steps: list[str]) -> tuple[list[str], dict | None]:
    """Reattach a detached bare-args step to its immediately-preceding tool.

    The salvage invariant is intentionally narrow: reattach arguments already
    present in the emitted chain; never synthesize, merge, infer, or reorder.
    Repair only when exactly one attachment interpretation exists.
    """
    normalized: list[str] = []
    salvage_record: dict | None = None
    index = 0
    while index < len(steps):
        current = str(steps[index]).strip()
        next_step = str(steps[index + 1]).strip() if index + 1 < len(steps) else None
        next_next = (
            str(steps[index + 2]).strip()
            if index + 2 < len(steps)
            else None
        )
        if (
            _is_tool_name_only_step(current)
            and next_step is not None
            and _is_bare_args_step(next_step)
            and (next_next is None or not _is_bare_args_step(next_next))
        ):
            normalized.append(f"{current} {next_step}".strip())
            salvage_record = _append_salvage_reason(
                salvage_record,
                "detached_args",
            )
            index += 2
            continue
        normalized.append(current)
        index += 1

    if normalized and not normalized[-1]:
        while normalized and not normalized[-1]:
            normalized.pop()
        salvage_record = _append_salvage_reason(
            salvage_record,
            "trailing_empty_segment",
        )

    _validate_chain_shape(normalized)
    return normalized, salvage_record


def _parse_compile_output(raw, tools) -> list[str]:
    text = _strip_compile_fence("" if raw is None else str(raw))
    if not text:
        raise CompileUnresolvableIntent("" if raw is None else str(raw))

    available_names = {name for name in (_tool_name(tool) for tool in tools) if name}
    try:
        decoded = json.loads(text)
    except (TypeError, json.JSONDecodeError):
        decoded = None

    if decoded is not None:
        if isinstance(decoded, dict) and "steps" in decoded:
            raw_steps = decoded["steps"]
        elif isinstance(decoded, list):
            raw_steps = decoded
        elif isinstance(decoded, dict):
            raw_steps = [decoded]
        else:
            raise CompileInvalidChainShape(
                text, "structured output is not an object or list"
            )
        if not isinstance(raw_steps, list) or not raw_steps:
            raise CompileUnresolvableIntent(text)
        steps = [
            _structured_compile_step_text(item, available_names, index)
            for index, item in enumerate(raw_steps)
        ]
    else:
        steps = _top_level_chain_segments(text)

    if not steps:
        raise CompileUnresolvableIntent(text)
    return [step.strip() for step in steps]


class LLMRouter:
    """
    Two-tier async LLM router for forge-bridge pipeline tools.

    Tier 1 (sensitive=True, default):
        -> local Ollama (local network, no data egress)
        -> Model: qwen2.5-coder:14b

    Tier 2 (sensitive=False):
        -> Anthropic Claude (cloud, non-sensitive queries only)
        -> Model: claude-sonnet-4-6

    Environment overrides:
        FORGE_LOCAL_LLM_URL    default: http://localhost:11434/v1
        FORGE_LOCAL_MODEL      default: qwen2.5-coder:14b
        FORGE_CLOUD_MODEL      default: claude-sonnet-4-6
        FORGE_SYSTEM_PROMPT    default: built-in VFX pipeline prompt
        ANTHROPIC_API_KEY      required for cloud calls

    Constructor kwargs override env vars, which override hardcoded defaults.
    Env reads happen at instance construction time, not at module import.
    """

    def __init__(
        self,
        local_url: str | None = None,
        local_model: str | None = None,
        cloud_model: str | None = None,
        system_prompt: str | None = None,
    ) -> None:
        self.local_url = local_url or os.environ.get(
            "FORGE_LOCAL_LLM_URL", "http://localhost:11434/v1"
        )
        self.local_model = local_model or os.environ.get(
            "FORGE_LOCAL_MODEL", _DEFAULT_LOCAL_MODEL
        )
        self.cloud_model = cloud_model or os.environ.get(
            "FORGE_CLOUD_MODEL", _DEFAULT_CLOUD_MODEL
        )
        self.system_prompt = system_prompt or os.environ.get(
            "FORGE_SYSTEM_PROMPT", _DEFAULT_SYSTEM_PROMPT
        )
        self._local_client: Optional["AsyncOpenAI"] = None  # type: ignore[name-defined]
        self._cloud_client: Optional["AsyncAnthropic"] = None  # type: ignore[name-defined]
        # FB-C D-02: native ollama.AsyncClient slot for complete_with_tools().
        # The OpenAI-compat shim above (self._local_client) stays in place for
        # acomplete() — two clients in the router for two purposes per research §3.7.
        self._local_native_client: Optional["ollama.AsyncClient"] = None  # type: ignore[name-defined]

    # ------------------------------------------------------------------
    # Public async API
    # ------------------------------------------------------------------

    async def acomplete(
        self,
        prompt: str,
        sensitive: bool = True,
        system: Optional[str] = None,
        temperature: float = 0.1,
    ) -> str:
        """
        Generate a completion asynchronously.

        Args:
            prompt:      The user message / task description.
            sensitive:   True (default) -> local model (no data egress).
                         False -> Claude cloud.
            system:      Override system prompt. If None, uses self.system_prompt
                         for local calls, minimal prompt for cloud calls.
            temperature: Sampling temperature. Default 0.1 for deterministic
                         pipeline code generation.

        Returns:
            Model response string.

        Raises:
            RuntimeError: If the selected backend is unavailable.
            RecursiveToolLoopError: If called from within complete_with_tools()
                — the _in_tool_loop ContextVar is True. Belt-and-suspenders
                against the recursive-synthesis attack surface (LLMTOOL-07,
                D-12/D-13, research §6.3).
        """
        # FB-C D-13: belt-and-suspenders runtime guard against recursive synthesis.
        # If a synthesized tool body managed to bypass the synthesizer's static
        # AST blocklist (D-14, plan 15-06 Task 2) — e.g., via importlib dynamic
        # import — and called acomplete() from inside a tool-call loop, this
        # entry check stops the recursion before any provider call is made.
        if _in_tool_loop.get():
            raise RecursiveToolLoopError(
                "acomplete() called from within complete_with_tools() — "
                "recursive LLM call blocked. See LLMTOOL-07 / D-12..D-14 "
                "and forge_bridge/learning/synthesizer.py:_check_safety."
            )

        if sensitive:
            return await self._async_local(prompt, system, temperature)
        return await self._async_cloud(prompt, system, temperature)

    async def compile_intent(
        self,
        prompt: str,
        tools: list,
        *,
        sensitive: bool = True,
        system: Optional[str] = None,
        temperature: float = 0.1,
        max_seconds: float = 30.0,
    ) -> list[str]:
        """Compile NL into a deterministic chain-step list."""
        if _in_tool_loop.get():
            raise RecursiveToolLoopError(
                "compile_intent() called from within complete_with_tools() — "
                "recursive LLM call blocked. See LLMTOOL-07 / D-12..D-14 "
                "and S-3 ruling (Stage 1b 2026-05-27)."
            )

        sys_msg = system if system is not None else _default_compile_system_prompt(tools)
        started = time.monotonic()
        status = "success"
        raw = ""
        try:
            backend_call = (
                self._async_local(prompt, sys_msg, temperature)
                if sensitive
                else self._async_cloud(prompt, sys_msg, temperature)
            )
            raw = await asyncio.wait_for(backend_call, timeout=max_seconds)
            return _parse_compile_output(raw, tools)
        except asyncio.TimeoutError as exc:
            status = "budget_exceeded"
            raise CompileBudgetExceeded(max_seconds, time.monotonic() - started) from exc
        except CompileError:
            status = "compile_error"
            raise
        except Exception:
            status = "backend_error"
            raise
        finally:
            duration_ms = int((time.monotonic() - started) * 1000)
            cache_prefix = f"{sys_msg}\n{prompt[:256]}"
            cache_prefix_hash = hashlib.sha256(
                cache_prefix.encode("utf-8")
            ).hexdigest()[:8]
            prompt_tokens = len(f"{sys_msg}\n{prompt}".split())
            completion_tokens = len(str(raw or "").split())
            model = self.local_model if sensitive else self.cloud_model
            logger.info(
                "ollama-compile model=%s prompt_tokens=%d "
                "completion_tokens=%d duration_ms=%d cache_prefix_hash=%s "
                "status=%s",
                model,
                prompt_tokens,
                completion_tokens,
                duration_ms,
                cache_prefix_hash,
                status,
            )

    async def complete_with_tools(
        self,
        prompt: str = "",
        *,
        tools: list,
        sensitive: bool = True,
        system: Optional[str] = None,
        temperature: float = 0.1,
        max_iterations: int = 8,
        max_seconds: float = 120.0,
        tool_executor: Optional[Callable[[str, dict], Awaitable[str]]] = None,
        tool_result_max_bytes: Optional[int] = None,
        parallel: bool = False,
        messages: Optional[list[dict]] = None,
        message_callback: Optional[Callable[[dict], Awaitable[None]]] = None,
    ) -> ChatTurnResult:
        """Run the FB-C agentic tool-call loop end-to-end.

        Sends prompt + tool schemas to the LLM (Anthropic if sensitive=False,
        Ollama if sensitive=True — verbatim from acomplete sensitive routing).
        Parses tool_call requests from the response, executes each via the
        registered MCP tools (or a caller-supplied tool_executor), feeds
        results back, and repeats until the LLM returns a terminal response
        or a budget cap fires.

        All five LLMTOOL-03..07 safety nets are enforced here:
          - Iteration cap + wall-clock cap → LLMLoopBudgetExceeded (LLMTOOL-03)
          - Repeat-call detection: 3rd identical call injects synthetic is_error
            without invoking the tool (LLMTOOL-04 / D-07)
          - Tool result truncation at tool_result_max_bytes (LLMTOOL-05 / D-08)
          - Tool result sanitization via _sanitize_tool_result before LLM
            ever sees the content (LLMTOOL-06 / D-11)
          - Recursive-synthesis guard via _in_tool_loop ContextVar set inside
            this method (LLMTOOL-07 / D-12..D-14, layer 2 belt-and-suspenders)

        Args:
            prompt: User message. Defaults to "" so messages-only callers can
                omit it. Mutually exclusive with `messages` (D-02a) — passing
                both raises ValueError; passing neither raises ValueError.
            messages: Optional structured-history list of dicts in {role, content,
                tool_call_id?} shape (D-02a Pattern B — added in FB-D plan 16-01).
                Mutually exclusive with `prompt`. When provided, the coordinator
                uses this list verbatim as the initial state.messages without
                auto-wrapping `prompt` into a single user turn. Roles must match
                what the adapter recognises ("user" | "assistant" | "tool" for
                both Ollama and Anthropic adapters).
            tools: list[mcp.types.Tool] — registered tool surface for this loop
                (per D-22). Empty list raises ValueError (D-23).
            sensitive: True → Ollama (local); False → Anthropic (cloud).
                Verbatim from acomplete() routing (D-01).
            system: Override system prompt. Defaults to self.system_prompt
                for local, minimal prompt for cloud (matches acomplete).
            temperature: Sampling temperature.
            max_iterations: Hard iteration cap (D-03 default 8). Each iteration
                = one full round-trip (send turn → execute tools → append).
            max_seconds: Wall-clock cap (D-04 default 120s). Wraps the loop
                via asyncio.wait_for. Order of fire: wall-clock fires first.
            tool_executor: Optional caller-supplied async (name, args) → str.
                Defaults to forge_bridge.mcp.registry.invoke_tool (D-20/D-21,
                lazy-imported only when caller passes None).
            tool_result_max_bytes: Override the LLMTOOL-05 truncation cap
                per call. Defaults to _TOOL_RESULT_MAX_BYTES (8192) per D-08.
            parallel: Reserved for v1.5 (D-06). True raises NotImplementedError;
                v1.4 ships serial-only.
            message_callback: Optional Phase 24.3 streaming hook. When provided,
                fires once after each ``adapter.send_turn()`` with the OpenAI-
                shaped assistant message ({"role": "assistant", "content": ...,
                "tool_calls": [...]}) and once after each tool result with the
                OpenAI-shaped tool message ({"role": "tool", "tool_call_id":
                ..., "name": ..., "content": ...}). Callback failures are
                logged at WARN level but do NOT abort the loop — streaming is
                a delivery cadence, not a load-bearing protocol path. The
                input echo (caller's ``messages=`` argument) is NEVER emitted
                via this callback; only NEW messages produced during the loop.
                Bug-D salvage at _adapters.py:733 runs BEFORE the callback
                fires — salvaged tool_calls are present in the emitted
                assistant message per framing §3.2 + §7.

        Returns:
            ChatTurnResult — Phase A chat-contract realignment (2026-05-05).
            Frozen dataclass carrying the terminal text, the full normalized
            conversation transcript (OpenAI-style; provider-native shapes are
            flattened at the adapter boundary), and a structured tool_trace
            mirroring every invocation. ``messages[-1]`` is always the
            terminal assistant turn; ``tool_trace`` is empty when no tools
            were invoked. The system never collapses tool history into the
            text return — that was the bug Phase A fixes.

        Raises:
            ValueError: If tools is empty (D-23).
            NotImplementedError: If parallel=True (D-06 v1.5 path).
            RecursiveToolLoopError: If called from within an outer
                complete_with_tools() — the _in_tool_loop ContextVar guard
                fires (LLMTOOL-07 / D-13).
            LLMLoopBudgetExceeded: If max_iterations or max_seconds fires
                (LLMTOOL-03). reason field is "max_iterations" or "max_seconds".
            LLMToolError: On unrecoverable adapter / API errors (provider
                5xx after SDK retries exhausted).
        """
        # Imported here to avoid module-load circular import (the helper module
        # imports LLMToolError from this file).
        from forge_bridge.llm._adapters import (
            AnthropicToolAdapter,
            OllamaToolAdapter,
            ToolCallResult,
        )
        from forge_bridge.llm._sanitize import (
            _sanitize_tool_result,
            _TOOL_RESULT_MAX_BYTES,
        )

        # ---- Pre-loop validation (D-13, D-23, D-06) -----------------------

        # D-13 belt-and-suspenders: refuse to start a new tool-call loop from
        # within an existing one. Mirror of the acomplete() entry check.
        if _in_tool_loop.get():
            raise RecursiveToolLoopError(
                "complete_with_tools() called from within complete_with_tools() — "
                "recursive LLM call blocked. See LLMTOOL-07 / D-12..D-14."
            )

        # D-02a: prompt and messages are mutually exclusive — caller picks one shape.
        # Backwards-compat: prompt-only path remains the default; messages= is the
        # new structured-history surface added in FB-D plan 16-01.
        if prompt and messages is not None:
            raise ValueError(
                "complete_with_tools: prompt and messages are mutually exclusive — "
                "pass one or the other (D-02a)"
            )
        if not prompt and messages is None:
            raise ValueError(
                "complete_with_tools: must provide either prompt= or messages= (D-02a)"
            )

        # D-23: empty tools rejected before adapter init (defensive — no
        # silent fall-through to plain completion semantics).
        if not tools:
            raise ValueError(
                "complete_with_tools requires at least one tool; "
                "use acomplete() for plain completion"
            )

        # D-06: parallel=True is reserved for v1.5; advertised in the kwarg
        # surface to signal the trajectory.
        if parallel:
            raise NotImplementedError(
                "parallel=True reserved for v1.5; v1.4 ships serial-only "
                "(per D-06 — Flame's idle-event queue serializes anyway). "
                "See SEED-PARALLEL-TOOL-EXEC-V1.5 in .planning/seeds/."
            )

        # Resolve effective truncation cap (D-08 override path).
        effective_max_bytes = (
            tool_result_max_bytes
            if tool_result_max_bytes is not None
            else _TOOL_RESULT_MAX_BYTES
        )

        # Default tool executor: forge_bridge.mcp.registry.invoke_tool (D-21).
        # Lazy import — only when caller did NOT pass tool_executor.
        if tool_executor is None:
            from forge_bridge.mcp.registry import invoke_tool as _default_executor
            tool_executor = _default_executor

        # ---- Adapter selection (D-01 verbatim from acomplete routing) -----

        if sensitive:
            adapter = OllamaToolAdapter(self._get_local_native_client(), self.local_model)
            sys_msg = system if system is not None else self.system_prompt
        else:
            adapter = AnthropicToolAdapter(self._get_cloud_client(), self.cloud_model)
            sys_msg = system or "You are a VFX pipeline assistant."

        # ---- Loop state ---------------------------------------------------

        state = adapter.init_state(
            prompt=prompt,
            system=sys_msg,
            tools=tools,
            temperature=temperature,
            messages=messages,   # D-02a: structured history pass-through (may be None)
        )
        seen_calls: collections.Counter = collections.Counter()
        # Phase 24.4: K-fold canonical-recurrence counter — parallel trigger
        # to existing D-07 (failed-affordance repetition stays at K>=3 with
        # synthetic is_error injection). New trigger key extends the
        # (tool_name, args_canonical) shape with the post-sanitization
        # result_canonical bytes shown to the LLM, restricted to
        # status=ok dispatches. Threshold K>=2 per framing §9 Seam A.
        # When this fires, _OrchestrationTerminated is raised after the
        # iteration's streaming emits + state update so the SSE consumer
        # observes the K-th successful tool result before the terminal
        # event (framing §5, §8.3).
        seen_canonical_results: collections.Counter = collections.Counter()
        # Every successful status=ok dispatch in this session, in
        # invocation order. Becomes ``accumulated_results`` of the
        # OrchestrationTerminationEnvelope when the K-fold trigger fires.
        # Failed dispatches are NOT recorded here — they live in
        # tool_trace with ``error`` populated. Framing §3.1.3.
        accumulated_successful_results: list[dict] = []
        registered_names = {t.name for t in tools}
        started = time.monotonic()
        prompt_tokens_total = 0
        completion_tokens_total = 0
        completed_iterations = 0
        # Phase A.2: tool_trace accumulates one entry per tool invocation.
        # Built alongside the per-iteration ToolCallResult list so error/
        # success semantics line up exactly with what the LLM was told.
        tool_trace: list[dict] = []

        # ---- Loop body (LLMTOOL-07 SET inside try/finally) ----------------

        # Phase A.2: parse a sanitized tool-result string into structured form
        # when possible. JSON failures fall back to the raw string so callers
        # never lose visibility on tool output. The trace records the same
        # text the LLM saw (post-sanitization) — symmetric with `messages`.
        def _maybe_parse_result(content: str):
            if not isinstance(content, str):
                return content
            try:
                return json.loads(content)
            except (json.JSONDecodeError, ValueError):
                return content

        def _record_trace(
            tool_call_obj,
            *,
            result: Any = None,
            error: Optional[str] = None,
        ) -> None:
            """Append one tool_trace entry. Phase A.2 invariant: success has
            error is None, failure has result is None — never both populated."""
            tool_trace.append({
                "tool_name": tool_call_obj.tool_name,
                "arguments": dict(tool_call_obj.arguments) if tool_call_obj.arguments else {},
                "result": result,
                "error": error,
                "index": len(tool_trace),
            })

        async def _emit_stream_assistant(response: "_TurnResponse") -> None:
            """Phase 24.3 streaming hook — fires assistant message after each
            send_turn(). Bug-D salvage at _adapters.py:733 runs BEFORE this
            fires; salvaged tool_calls are already present on response.tool_calls
            and round-trip into the emitted assistant message via the same
            OpenAI shape adapter.to_chat_messages() emits at terminal moment."""
            if message_callback is None:
                return
            msg: dict[str, Any] = {
                "role": "assistant",
                "content": response.text or "",
            }
            if response.tool_calls:
                msg["tool_calls"] = [
                    {
                        "id": tc.ref,
                        "type": "function",
                        "function": {
                            "name": tc.tool_name,
                            "arguments": json.dumps(tc.arguments),
                        },
                    }
                    for tc in response.tool_calls
                ]
            try:
                await message_callback(msg)
            except Exception:
                logger.warning(
                    "message_callback raised on assistant emit; loop continues",
                    exc_info=True,
                )

        async def _emit_stream_tool(result: "ToolCallResult") -> None:
            """Phase 24.3 streaming hook — fires after each tool result is
            appended. Content matches what the LLM sees (post-sanitization)."""
            if message_callback is None:
                return
            try:
                await message_callback({
                    "role": "tool",
                    "tool_call_id": result.tool_call_ref,
                    "name": result.tool_name,
                    "content": result.content,
                })
            except Exception:
                logger.warning(
                    "message_callback raised on tool emit; loop continues",
                    exc_info=True,
                )

        async def _loop_body() -> str:
            nonlocal prompt_tokens_total, completion_tokens_total, completed_iterations
            nonlocal state

            # Phase 24.4: deferred-raise slot for K-fold canonical-recurrence
            # trigger. Set in the per-call success branch when the K-th
            # identical (tool_name, args_canonical, result_canonical) dispatch
            # is observed. Raised AFTER the iteration's streaming emits +
            # state update so SSE consumers observe the K-th tool result
            # before the terminal envelope event (framing §5, §8.3).
            pending_termination_envelope: Optional[
                "OrchestrationTerminationEnvelope"
            ] = None

            for iteration in range(max_iterations):
                turn_start = time.monotonic()
                response = await adapter.send_turn(state)

                prompt_tokens_total += response.usage_tokens[0]
                completion_tokens_total += response.usage_tokens[1]
                completed_iterations = iteration + 1

                # Phase 24.3 streaming hook — assistant message emit (history-grows,
                # message granularity). Fires for both terminal and continuing
                # turns; salvage already ran at the adapter so any rescued
                # tool_calls round-trip into the emitted shape. Per framing §7,
                # callback failures never abort the loop — streaming is delivery
                # cadence, not load-bearing protocol path.
                await _emit_stream_assistant(response)

                # Terminal: no more tool calls — emit terminal log + return text.
                if not response.tool_calls:
                    elapsed_ms = int((time.monotonic() - turn_start) * 1000)
                    logger.info(
                        "tool-call iter=%d tool= args_hash= prompt_tokens=%d "
                        "completion_tokens=%d elapsed_ms=%d status=terminal",
                        iteration + 1,
                        response.usage_tokens[0],
                        response.usage_tokens[1],
                        elapsed_ms,
                    )
                    return response.text

                # Process tool calls (serial — D-06: tool_calls[:1] for non-parallel).
                results: list[ToolCallResult] = []
                effective_calls = (
                    response.tool_calls if adapter.supports_parallel
                    else response.tool_calls[:1]
                )

                for call in effective_calls:
                    # D-26 args hash for log line (NEVER log raw args content).
                    args_canonical = json.dumps(call.arguments, sort_keys=True)
                    args_hash = hashlib.sha256(
                        args_canonical.encode("utf-8")
                    ).hexdigest()[:8]

                    # D-07 repeat-call detection.
                    repeat_key = (call.tool_name, args_canonical)
                    seen_calls[repeat_key] += 1
                    if seen_calls[repeat_key] >= 3:
                        synthetic = (
                            f"You have called {call.tool_name} with the same "
                            f"arguments {seen_calls[repeat_key]} times. "
                            "Try different arguments or stop calling this tool."
                        )
                        results.append(ToolCallResult(
                            tool_call_ref=call.ref,
                            tool_name=call.tool_name,
                            content=_sanitize_tool_result(synthetic, max_bytes=effective_max_bytes),
                            is_error=True,
                        ))
                        _record_trace(call, error=synthetic)
                        elapsed_ms = int((time.monotonic() - turn_start) * 1000)
                        logger.info(
                            "tool-call iter=%d tool=%s args_hash=%s prompt_tokens=%d "
                            "completion_tokens=%d elapsed_ms=%d status=repeat_blocked",
                            iteration + 1, call.tool_name, args_hash,
                            response.usage_tokens[0], response.usage_tokens[1], elapsed_ms,
                        )
                        continue

                    # Hallucinated tool name (research §4.3) — caught BEFORE invoke.
                    if call.tool_name not in registered_names:
                        msg = (
                            f"ERROR: tool '{call.tool_name}' is not registered. "
                            f"Available tools: {', '.join(sorted(registered_names))}"
                        )
                        results.append(ToolCallResult(
                            tool_call_ref=call.ref,
                            tool_name=call.tool_name,
                            content=_sanitize_tool_result(msg, max_bytes=effective_max_bytes),
                            is_error=True,
                        ))
                        _record_trace(call, error=msg)
                        elapsed_ms = int((time.monotonic() - turn_start) * 1000)
                        logger.info(
                            "tool-call iter=%d tool=%s args_hash=%s prompt_tokens=%d "
                            "completion_tokens=%d elapsed_ms=%d status=hallucinated",
                            iteration + 1, call.tool_name, args_hash,
                            response.usage_tokens[0], response.usage_tokens[1], elapsed_ms,
                        )
                        continue

                    # Per-tool sub-budget (D-05): max(1.0, min(30.0, remaining)).
                    remaining = max_seconds - (time.monotonic() - started)
                    per_tool_budget = max(1.0, min(30.0, remaining))

                    # D-34 belt-and-suspenders: catch SystemExit at the innermost
                    # layer BEFORE asyncio.wait_for sees it. asyncio re-raises
                    # BaseException (including SystemExit) from task callbacks even
                    # if a higher-up frame catches it — so we must convert
                    # SystemExit into a regular Exception inside the executor's
                    # own coroutine. This is the layer-2 defense (synthesizer
                    # blocklist is layer 1; Phase 3 quarantine is layer 3).
                    # The wrapper records "SystemExit" as a sentinel so the outer
                    # catch surfaces it to the LLM with the correct origin.
                    _system_exit_signal: dict = {"hit": False}

                    async def _safe_tool_call(_name=call.tool_name, _args=call.arguments):
                        try:
                            return await tool_executor(_name, _args)
                        except SystemExit:
                            _system_exit_signal["hit"] = True
                            # Convert to a regular Exception so asyncio.wait_for
                            # surfaces it normally and our outer except catches it.
                            raise RuntimeError("SystemExit") from None

                    # Tool execution wrapped in (Exception, SystemExit) per D-34.
                    status = "continuing"
                    try:
                        raw_result = await asyncio.wait_for(
                            _safe_tool_call(),
                            timeout=per_tool_budget,
                        )
                        result_text = _sanitize_tool_result(
                            str(raw_result), max_bytes=effective_max_bytes,
                        )
                        results.append(ToolCallResult(
                            tool_call_ref=call.ref,
                            tool_name=call.tool_name,
                            content=result_text,
                            is_error=False,
                        ))
                        _record_trace(
                            call,
                            result=_maybe_parse_result(result_text),
                        )
                        # Phase 24.4: K-fold canonical-recurrence trigger.
                        # Restricted to status=ok dispatches (this branch).
                        # Hash the EXACT post-sanitization bytes shown to
                        # the LLM (framing §4.1, §9 Seam C — orchestration
                        # reasons over model-visible state, not raw
                        # substrate payload). Key:
                        # (tool_name, args_canonical, result_text).
                        # Threshold K>=2 per framing §9 Seam A.
                        result_hash = hashlib.sha256(
                            result_text.encode("utf-8")
                        ).hexdigest()[:8]
                        accumulated_successful_results.append({
                            "tool_name": call.tool_name,
                            "args_hash": args_hash,
                            "result_hash": result_hash,
                            "content": result_text,
                            "iter": iteration + 1,
                        })
                        canonical_key = (
                            call.tool_name, args_canonical, result_text,
                        )
                        seen_canonical_results[canonical_key] += 1
                        if (
                            pending_termination_envelope is None
                            and seen_canonical_results[canonical_key] >= 2
                        ):
                            k_count = seen_canonical_results[canonical_key]
                            pending_termination_envelope = (
                                OrchestrationTerminationEnvelope(
                                    status="orchestration_terminated",
                                    trigger="k_fold_canonical",
                                    reason=(
                                        f"Tool {call.tool_name} dispatched "
                                        f"successfully {k_count} times with "
                                        "identical canonical arguments and "
                                        "identical canonical result. Loop "
                                        "terminated by orchestration policy."
                                    ),
                                    iterations=iteration + 1,
                                    accumulated_results=list(
                                        accumulated_successful_results
                                    ),
                                )
                            )
                    except asyncio.TimeoutError:
                        msg = f"ERROR: tool '{call.tool_name}' timed out after {per_tool_budget:.1f}s"
                        results.append(ToolCallResult(
                            tool_call_ref=call.ref,
                            tool_name=call.tool_name,
                            content=_sanitize_tool_result(msg, max_bytes=effective_max_bytes),
                            is_error=True,
                        ))
                        _record_trace(call, error=msg)
                        status = "tool_timeout"
                    except KeyError as exc:
                        # invoke_tool raises KeyError on hallucinated name — message
                        # already includes available-tool list per plan 15-07.
                        # (Defense-in-depth: we already check registered_names above,
                        # but the executor may know about a different surface.)
                        msg = f"ERROR: {exc!s}"  # KeyError msg is structural, no creds
                        results.append(ToolCallResult(
                            tool_call_ref=call.ref,
                            tool_name=call.tool_name,
                            content=_sanitize_tool_result(msg, max_bytes=effective_max_bytes),
                            is_error=True,
                        ))
                        _record_trace(call, error=msg)
                        status = "hallucinated"
                    except (Exception, SystemExit) as exc:  # D-34 belt-and-suspenders
                        # Phase 8 cf221fe: log type name only, never str(exc) which
                        # may carry credentials. The LLM gets the type name + a
                        # generic error message — enough to retry with corrected args.
                        # If the inner _safe_tool_call recorded a SystemExit hit,
                        # surface "SystemExit" as the type name (D-34 attribution).
                        if _system_exit_signal["hit"]:
                            exc_type = "SystemExit"
                        else:
                            exc_type = type(exc).__name__
                        msg = f"ERROR: tool {call.tool_name!r} raised {exc_type}"
                        results.append(ToolCallResult(
                            tool_call_ref=call.ref,
                            tool_name=call.tool_name,
                            content=_sanitize_tool_result(msg, max_bytes=effective_max_bytes),
                            is_error=True,
                        ))
                        _record_trace(call, error=msg)
                        status = "tool_error"

                    elapsed_ms = int((time.monotonic() - turn_start) * 1000)
                    logger.info(
                        "tool-call iter=%d tool=%s args_hash=%s prompt_tokens=%d "
                        "completion_tokens=%d elapsed_ms=%d status=%s",
                        iteration + 1, call.tool_name, args_hash,
                        response.usage_tokens[0], response.usage_tokens[1], elapsed_ms, status,
                    )

                # Phase 24.3 streaming hook — tool message emits (history-grows,
                # message granularity). One emit per ToolCallResult in this
                # iteration; content matches what the LLM sees (post-sanitization).
                # Order matches results[] order, which matches effective_calls
                # order. Per framing §7, callback failures never abort the loop.
                for r in results:
                    await _emit_stream_tool(r)

                # Update state with assistant turn + tool results.
                state = adapter.append_results(state, response, results)

                # Phase 24.4: K-fold canonical trigger was armed in the per-
                # call loop above — raise NOW (after streaming emits + state
                # update so the SSE consumer observes the K-th tool result
                # before the terminal envelope event). Carries the envelope
                # + state snapshot so the outer try/except constructs the
                # ChatTurnResult without re-deriving state. Framing §5, §6.
                if pending_termination_envelope is not None:
                    elapsed_ms = int((time.monotonic() - turn_start) * 1000)
                    last = pending_termination_envelope.accumulated_results[-1]
                    # k_count is K=2 by construction (trigger fires at K-th
                    # match per framing §9 Seam A — first K=2 hit terminates).
                    logger.info(
                        "tool-call iter=%d tool=%s args_hash=%s "
                        "result_hash=%s prompt_tokens=%d completion_tokens=%d "
                        "elapsed_ms=%d status=orchestration_terminated "
                        "trigger=k_fold_canonical k_count=2",
                        iteration + 1, last["tool_name"], last["args_hash"],
                        last["result_hash"],
                        response.usage_tokens[0], response.usage_tokens[1],
                        elapsed_ms,
                    )
                    raise _OrchestrationTerminated(
                        envelope=pending_termination_envelope,
                        state_messages=adapter.to_chat_messages(state, ""),
                        completed_iterations=iteration + 1,
                    )

            # Iteration cap exhausted (D-03).
            raise LLMLoopBudgetExceeded(
                "max_iterations", max_iterations, time.monotonic() - started,
            )

        # ---- LLMTOOL-07 ContextVar SET (try/finally for cleanup, D-12) ----

        token = _in_tool_loop.set(True)
        terminal_reason = "end_turn"
        try:
            try:
                # D-04 wall-clock cap wraps the entire loop.
                terminal_text = await asyncio.wait_for(
                    _loop_body(), timeout=max_seconds,
                )
                # Phase A: assemble ChatTurnResult at the terminal moment.
                # The adapter normalizes its provider-native state.messages to
                # OpenAI-style and appends the terminal assistant turn so the
                # consumer always has messages[-1] as the final reply.
                return ChatTurnResult(
                    final_text=terminal_text,
                    messages=adapter.to_chat_messages(state, terminal_text),
                    tool_trace=list(tool_trace),
                )
            except _OrchestrationTerminated as exc:
                # Phase 24.4 — K-fold canonical-recurrence trigger fired
                # inside _loop_body. Construct ChatTurnResult with the
                # termination envelope populated; final_text="" because the
                # orchestrator does NOT synthesize conversational text
                # (framing §5.1, §10.1). messages reflects the transcript
                # at the iteration where the trigger fired (state_messages
                # snapshotted at raise time so failed dispatches, salvaged
                # calls, and the K-th successful tool result are all
                # preserved). tool_trace carries the full session trace
                # (Phase A invariant — every tool invocation, success or
                # failure, available to downstream consumers).
                terminal_reason = "orchestration_terminated"
                return ChatTurnResult(
                    final_text="",
                    messages=exc.state_messages,
                    tool_trace=list(tool_trace),
                    termination=exc.envelope,
                )
            except asyncio.TimeoutError:
                terminal_reason = "max_seconds"
                raise LLMLoopBudgetExceeded(
                    "max_seconds", -1, time.monotonic() - started,
                ) from None
            except LLMLoopBudgetExceeded as exc:
                terminal_reason = exc.reason
                raise
            except RecursiveToolLoopError:
                terminal_reason = "recursive_call"
                raise
            except LLMToolError:
                terminal_reason = "tool_loop_error"
                raise
            except ValueError:
                terminal_reason = "value_error"
                raise
        finally:
            _in_tool_loop.reset(token)
            # D-25 per-session terminal log (always emitted, success or failure).
            logger.info(
                "tool-call session complete iter=%d elapsed_s=%.1f "
                "prompt_tokens_total=%d completion_tokens_total=%d reason=%s",
                completed_iterations,
                time.monotonic() - started,
                prompt_tokens_total,
                completion_tokens_total,
                terminal_reason,
            )

    def complete(self, prompt: str, **kwargs) -> str:
        """
        Sync convenience wrapper around acomplete().

        Do NOT call from inside an async context (e.g., MCP tool handlers).
        Use acomplete() directly instead. This wrapper uses asyncio.run() which
        creates its own event loop — it will raise RuntimeError if called from
        within a running event loop.

        Args:
            prompt: The user message / task description.
            **kwargs: Passed through to acomplete() (sensitive, system, temperature).

        Returns:
            Model response string.
        """
        return asyncio.run(self.acomplete(prompt, **kwargs))

    async def ahealth_check(self) -> dict:
        """
        Check availability of both backends asynchronously.

        Returns:
            dict with keys: local (bool), cloud (bool), local_model, cloud_model,
            and optional local_error / cloud_error strings.
        """
        status = {
            "local": False,
            "cloud": False,
            "local_model": self.local_model,
            "cloud_model": self.cloud_model,
        }
        try:
            client = self._get_local_client()
            await client.models.list()
            status["local"] = True
        except Exception as e:
            logger.warning(f"Local LLM unavailable: {e}")
            status["local_error"] = str(e)
        try:
            import anthropic as _anthropic  # noqa: F401
            status["cloud"] = bool(os.environ.get("ANTHROPIC_API_KEY"))
        except ImportError:
            status["cloud_error"] = "anthropic not installed"
        return status

    def health_check(self) -> dict:
        """Sync convenience wrapper around ahealth_check(). See ahealth_check() for details."""
        return asyncio.run(self.ahealth_check())

    # ------------------------------------------------------------------
    # Internal client accessors (lazy import guards)
    # ------------------------------------------------------------------

    def _get_local_client(self):
        if self._local_client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError:
                raise RuntimeError(
                    "openai package not installed. "
                    "Install LLM support: pip install forge-bridge[llm]"
                )
            self._local_client = AsyncOpenAI(
                base_url=self.local_url,
                api_key="ollama",  # Ollama ignores the key but AsyncOpenAI client requires one
            )
        return self._local_client

    def _get_cloud_client(self):
        if self._cloud_client is None:
            try:
                from anthropic import AsyncAnthropic
            except ImportError:
                raise RuntimeError(
                    "anthropic package not installed. "
                    "Install LLM support: pip install forge-bridge[llm]"
                )
            self._cloud_client = AsyncAnthropic()
        return self._cloud_client

    def _get_local_native_client(self):
        """Return the native ollama.AsyncClient (D-02), lazy-instantiated.

        Used by complete_with_tools() for the local/sensitive tool-call path.
        Distinct from _get_local_client() (OpenAI-compat shim, used by acomplete()):
          - acomplete() uses the shim because the wire format is identical for
            plain completions and the existing tests / pin (openai>=1.0) cover it.
          - complete_with_tools() uses the native client because the OpenAI shim
            drops tool_calls.function.arguments parsing quirks, hides
            message.thinking, and silently coerces error types (research §3.7).

        The native client takes host without the OpenAI /v1 suffix; we strip it
        from self.local_url if present (default self.local_url is
        "http://localhost:11434/v1" and the daemon is at "http://localhost:11434").

        Fast-fail connect timeout (SEED-FAST-FAIL-LLM-CONNECT-TIMEOUT-V1.5+,
        landed via bridge #173): ollama.AsyncClient passes ``timeout`` straight
        through to the underlying httpx.AsyncClient (verified against ollama
        0.6.1), so an explicit httpx.Timeout converts the ~75s OS-level TCP
        connect stall on an unreachable host into a 5s explicit failure. The
        read timeout stays at 120s — the LLM-loop wall-clock cap — so
        slow-but-responsive models are unaffected. No retries.
        """
        if self._local_native_client is None:
            try:
                from ollama import AsyncClient
            except ImportError:
                raise RuntimeError(
                    "ollama package not installed. "
                    "Install LLM support: pip install forge-bridge[llm]"
                )
            import httpx  # hard dependency of ollama; already installed

            host = self.local_url
            if host.endswith("/v1"):
                host = host[:-3]
            self._local_native_client = AsyncClient(
                host=host,
                timeout=httpx.Timeout(connect=5.0, read=120.0, write=10.0, pool=5.0),
            )
        return self._local_native_client

    # ------------------------------------------------------------------
    # Internal async backend methods
    # ------------------------------------------------------------------

    async def _async_local(
        self, prompt: str, system: Optional[str], temperature: float
    ) -> str:
        client = self._get_local_client()
        sys_msg = system if system is not None else self.system_prompt
        messages = []
        if sys_msg:
            messages.append({"role": "system", "content": sys_msg})
        messages.append({"role": "user", "content": prompt})

        try:
            resp = await client.chat.completions.create(
                model=self.local_model,
                messages=messages,
                temperature=temperature,
            )
            return resp.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"Local LLM call failed ({self.local_url}): {e}")

    async def _async_cloud(
        self, prompt: str, system: Optional[str], temperature: float
    ) -> str:
        client = self._get_cloud_client()
        sys_msg = system or "You are a VFX pipeline assistant."

        try:
            resp = await client.messages.create(
                model=self.cloud_model,
                max_tokens=4096,
                system=sys_msg,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.content[0].text
        except Exception as e:
            raise RuntimeError(f"Cloud LLM call failed: {e}")


# ---------------------------------------------------------------------------
# Convenience singleton -- import and use directly in forge-bridge tools
# ---------------------------------------------------------------------------
_router: Optional[LLMRouter] = None


def get_router() -> LLMRouter:
    """Return the shared LLMRouter singleton."""
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router
