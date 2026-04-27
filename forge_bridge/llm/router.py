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
from typing import Awaitable, Callable, Optional, TYPE_CHECKING

logger = logging.getLogger(__name__)

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


class LLMRouter:
    """
    Two-tier async LLM router for forge-bridge pipeline tools.

    Tier 1 (sensitive=True, default):
        -> local Ollama (local network, no data egress)
        -> Model: qwen2.5-coder:32b

    Tier 2 (sensitive=False):
        -> Anthropic Claude (cloud, non-sensitive queries only)
        -> Model: claude-opus-4-6

    Environment overrides:
        FORGE_LOCAL_LLM_URL    default: http://localhost:11434/v1
        FORGE_LOCAL_MODEL      default: qwen2.5-coder:32b
        FORGE_CLOUD_MODEL      default: claude-opus-4-6
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
            "FORGE_LOCAL_MODEL", "qwen2.5-coder:32b"
        )
        self.cloud_model = cloud_model or os.environ.get(
            "FORGE_CLOUD_MODEL", "claude-opus-4-6"
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
    ) -> str:
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

        Returns:
            Final assistant text from the terminal turn.

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
        registered_names = {t.name for t in tools}
        started = time.monotonic()
        prompt_tokens_total = 0
        completion_tokens_total = 0
        completed_iterations = 0

        # ---- Loop body (LLMTOOL-07 SET inside try/finally) ----------------

        async def _loop_body() -> str:
            nonlocal prompt_tokens_total, completion_tokens_total, completed_iterations
            nonlocal state

            for iteration in range(max_iterations):
                turn_start = time.monotonic()
                response = await adapter.send_turn(state)

                prompt_tokens_total += response.usage_tokens[0]
                completion_tokens_total += response.usage_tokens[1]
                completed_iterations = iteration + 1

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
                    except asyncio.TimeoutError:
                        msg = f"ERROR: tool '{call.tool_name}' timed out after {per_tool_budget:.1f}s"
                        results.append(ToolCallResult(
                            tool_call_ref=call.ref,
                            tool_name=call.tool_name,
                            content=_sanitize_tool_result(msg, max_bytes=effective_max_bytes),
                            is_error=True,
                        ))
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
                        status = "tool_error"

                    elapsed_ms = int((time.monotonic() - turn_start) * 1000)
                    logger.info(
                        "tool-call iter=%d tool=%s args_hash=%s prompt_tokens=%d "
                        "completion_tokens=%d elapsed_ms=%d status=%s",
                        iteration + 1, call.tool_name, args_hash,
                        response.usage_tokens[0], response.usage_tokens[1], elapsed_ms, status,
                    )

                # Update state with assistant turn + tool results.
                state = adapter.append_results(state, response, results)

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
                result = await asyncio.wait_for(_loop_body(), timeout=max_seconds)
                return result
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
        """
        if self._local_native_client is None:
            try:
                from ollama import AsyncClient
            except ImportError:
                raise RuntimeError(
                    "ollama package not installed. "
                    "Install LLM support: pip install forge-bridge[llm]"
                )
            host = self.local_url
            if host.endswith("/v1"):
                host = host[:-3]
            self._local_native_client = AsyncClient(host=host)
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
