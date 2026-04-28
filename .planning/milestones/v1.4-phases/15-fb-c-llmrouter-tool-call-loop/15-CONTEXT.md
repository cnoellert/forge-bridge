# Phase 15 (FB-C): LLMRouter Tool-Call Loop — Context

**Gathered:** 2026-04-26
**Status:** Ready for planning
**Aliases:** FB-C (canonical cross-repo identifier per projekt-forge v1.5 dependency contract); `15` is the gsd-tooling numeric ID.

<domain>
## Phase Boundary

Build `LLMRouter.complete_with_tools(prompt, tools, sensitive=...)` — a provider-neutral
agentic loop coordinator + thin Anthropic + Ollama adapters, plus four cross-cutting
safety helpers. The coordinator owns the loop, the iteration cap, the wall-clock cap,
the tool registry lookup, the structured-error protocol, repeat-call detection, ingest-time
result truncation, the sanitization boundary on tool results, and a recursive-synthesis
guard. The adapters own one thing each: translating between canonical conversation
state and the provider's wire format.

**Surfaces shipped:**
- `LLMRouter.complete_with_tools()` async public method (sensitive routing preserved verbatim from `acomplete()`)
- `forge_bridge/llm/_adapters.py` — `AnthropicToolAdapter` + `OllamaToolAdapter`
- `forge_bridge/llm/_sanitize.py` — `_sanitize_tool_result()`
- `forge_bridge/_sanitize_patterns.py` — hoisted shared patterns (NEW top-level module)
- `forge_bridge/mcp/registry.py::invoke_tool(name, args)` — new public default executor
- Three new exceptions exported from `forge_bridge.__all__` (16→19): `LLMLoopBudgetExceeded`, `RecursiveToolLoopError`, `LLMToolError`
- Synthesizer safety blocklist update — flag `forge_bridge.llm` imports

**Out of scope for this phase:**
- `/api/v1/chat` HTTP endpoint (Phase 16 / FB-D)
- Web UI chat panel wiring (FB-D)
- Parallel tool execution within a single LLM turn (`parallel: bool = False` kwarg ships and raises `NotImplementedError`; v1.5 path)
- Cross-provider sensitive fallback (loop state is provider-specific; v1.5+)
- Message-history pruning (v1.4 ships ingest-time 8 KB truncation only; v1.5+ for true pruning)
- Default Ollama tool model bump from `qwen2.5-coder:32b` → `qwen3:32b` (SEED-DEFAULT-MODEL-BUMP-V1.4.x)
- Default cloud model bump from `claude-opus-4-6` → `claude-opus-4-7` (SEED-CLOUD-MODEL-BUMP-V1.4.x)
- Anthropic `client.beta.tool_runner()` adoption (rejected — beta + Anthropic-only)
- Anthropic OpenAI-compat shim for Ollama tool calling (rejected — drops reliability signals)
- Tool examples (Anthropic `input_examples`) on registered tools (SEED-TOOL-EXAMPLES-V1.5)
- Streaming responses (FB-D may revisit; FB-C is non-streaming)

</domain>

<decisions>
## Implementation Decisions

### Coordinator + Adapter Architecture (research §5.3)

- **D-01:** ONE provider-neutral coordinator + TWO thin adapter modules. Coordinator
  lives on `LLMRouter.complete_with_tools()`; adapters in `forge_bridge/llm/_adapters.py`
  as `AnthropicToolAdapter` and `OllamaToolAdapter` implementing the `_ToolAdapter`
  Protocol from research §4.4 (`init_state`, `send_turn`, `append_results`).
  - **Why:** loop logic (~80% of code) is identical across providers; duplicating it
    creates the LRN-05 drift hazard from Phase 8. Adding a third provider later is
    one new adapter, zero coordinator changes.

- **D-02:** Adapters use **native** provider clients:
  - Anthropic: existing `anthropic.AsyncAnthropic`, pin `anthropic>=0.97,<1`
  - Ollama: NEW `ollama.AsyncClient`, pin `ollama>=0.6.1,<1` (added to `[llm]` extra in `pyproject.toml`)
  - The OpenAI-compat shim (`AsyncOpenAI` against `localhost:11434/v1`) stays in place for `acomplete()` — two clients in the router for two purposes (research §3.7).
  - **Reject** `client.beta.messages.tool_runner()` — beta API, Anthropic-only, breaks parity with Ollama (research §1).

### Loop Caps (already roadmap-locked; restated here for the planner)

- **D-03:** `max_iterations: int = 8` (default). Hard iteration cap. Each iteration is one full round-trip (send turn, parse response, execute tools, append results).
- **D-04:** `max_seconds: float = 120.0` (default). Wall-clock cap implemented via `asyncio.wait_for(_loop_body(), timeout=max_seconds)` wrapping the entire loop. Order of fire when both could trip: wall-clock fires first (it wraps the whole loop).
- **D-05:** Per-tool sub-budget: `max(1.0, min(30.0, remaining_global_budget))`. Prevents one bad tool from consuming the entire wall-clock; 30s ceiling is empirical (forge tools <1s, `bridge.execute()` <5s, edge cases 10-20s).
- **D-06:** Serial tool execution. `OllamaToolAdapter.supports_parallel = False`; Anthropic adapter sets `disable_parallel_tool_use=true`. Coordinator processes ONLY `tool_calls[0]` per turn and ignores extras. `parallel: bool = False` kwarg ships on `complete_with_tools()` and raises `NotImplementedError` if `True` (advertises v1.5 path).
  - **Why:** Flame's idle-event queue serializes `bridge.execute()` anyway; parallel adds race-condition surface for zero throughput gain (research §6.4).

### Repeat-Call Detection (LLMTOOL-04)

- **D-07:** After **three** identical `(tool_name, json.dumps(args, sort_keys=True))` invocations within one session, the coordinator injects a synthetic `tool_result` with `is_error=True` and text `"You have called {tool} with the same arguments {n} times. Try different arguments or stop calling this tool."`. The original tool is NOT invoked the third time. State carried in `seen_calls: collections.Counter[tuple[str, str]]` initialized per `complete_with_tools()` call.
  - **Why ≥3 not ≥2:** 2-call loops are sometimes legitimate (model checks twice). 3 is unambiguously stuck (research §6.1).

### Result Truncation (LLMTOOL-05)

- **D-08:** Every tool result string is truncated to **8192 bytes** before feeding back to the LLM. Truncated content is suffixed with `\n[...truncated, full result was {n} bytes]`. Constant `_TOOL_RESULT_MAX_BYTES = 8192` lives in `forge_bridge/llm/_sanitize.py`. Overridable via `complete_with_tools(..., tool_result_max_bytes=N)` kwarg.

### Sanitization Boundary (LLMTOOL-06 + STATE.md "single source of truth" mandate)

- **D-09:** New top-level module `forge_bridge/_sanitize_patterns.py` is the single source of truth for shared sanitization primitives. Hoisted contents:
  - `INJECTION_MARKERS: tuple[str, ...]` (currently in `learning/sanitize.py:50`)
  - `_CONTROL_CHAR_RE: re.Pattern` (currently in `learning/sanitize.py:62`)
  - **Helpers do NOT move** — `_sanitize_tag()` stays in `learning/sanitize.py`; new `_sanitize_tool_result()` lives in `forge_bridge/llm/_sanitize.py`. Each helper module imports the patterns from `_sanitize_patterns.py`.
  - **Why:** minimum API surface, zero behavior change to Phase 7 watcher/registry code, neutral home between `learning/` and `llm/` consumers.

- **D-10:** `forge_bridge/learning/sanitize.py` becomes a thin re-export shim for backward compat. The module still exports `INJECTION_MARKERS` and `_CONTROL_CHAR_RE` (via `from forge_bridge._sanitize_patterns import ...`) so existing `learning.watcher` and `mcp.registry` callers need ZERO updates. Verified callers:
  - `forge_bridge/learning/watcher.py:17` — imports `_sanitize_tag, apply_size_budget` (unchanged)
  - `forge_bridge/mcp/registry.py:90` — references `_sanitize_tag` in comment only

- **D-11:** `_sanitize_tool_result(text: str) -> str` in `forge_bridge/llm/_sanitize.py`:
  1. Strip ASCII control chars except `\n`, `\t` (uses `_CONTROL_CHAR_RE` from `_sanitize_patterns`).
  2. Replace any case-insensitive match of an `INJECTION_MARKERS` substring with the literal token `[BLOCKED:INJECTION_MARKER]`. (Phase 7's `_sanitize_tag()` REJECTS the entire tag on marker hit; tool-result sanitization REPLACES inline because the result has authoritative content the LLM still needs to see — discarding the whole result silently would break the loop.)
  3. Truncate to `_TOOL_RESULT_MAX_BYTES` (8192) with the suffix from D-08.
  4. Runs on EVERY tool result before it leaves the coordinator for the LLM, regardless of provider.

### Recursive-Synthesis Guard (LLMTOOL-07)

- **D-12:** A `contextvars.ContextVar[bool]` named `_in_tool_loop` (default `False`) lives in `forge_bridge/llm/router.py`. Inside `complete_with_tools()`:
  ```python
  token = _in_tool_loop.set(True)
  try:
      return await _loop_body()
  finally:
      _in_tool_loop.reset(token)
  ```
- **D-13:** Both `acomplete()` and `complete_with_tools()` check `_in_tool_loop.get()` on entry; if `True`, raise `RecursiveToolLoopError`. Belt-and-suspenders against the synthesizer's static check.
- **D-14:** Synthesizer safety blocklist update (`forge_bridge/learning/synthesizer.py:108-116`) — add `forge_bridge.llm` and `LLMRouter` to the import-rejection list. Static AST check that flags any `Import`/`ImportFrom` whose module starts with `forge_bridge.llm`. Fixture-tested: a synthesized tool body containing `from forge_bridge.llm.router import LLMRouter` fails `_check_safety()` and is quarantined.

### Public API Growth (Area 5 — confirmed all-three export)

- **D-15:** Three new exceptions exported from `forge_bridge.__all__` (16→19):
  - `LLMLoopBudgetExceeded` — caught by FB-D, mapped to HTTP 504 (gateway timeout)
  - `RecursiveToolLoopError` — caught by FB-D, mapped to HTTP 500 (internal error — caller bug)
  - `LLMToolError` — caught by FB-D, mapped to HTTP 502 (bad gateway — provider failure)
  - **Why:** FB-D needs distinct HTTP status mapping per failure mode. Without exports, FB-D catches `RuntimeError` and loses the discrimination — regression vs. Phase 4's "explicit catchable contracts" precedent and Phase 8's `StoragePersistence` export pattern.

- **D-16:** All three exception classes live in `forge_bridge/llm/router.py` alongside `LLMRouter`. Matches existing module-cohesion pattern (Phase 8 put `StoragePersistence` next to `ExecutionLog` in `learning/storage.py`, not a separate `_errors.py`).

- **D-17:** `complete_with_tools()` is a **public method on `LLMRouter`**, symmetric with `acomplete()` and `complete()`. No module-level function alias. Sync wrapper `complete_with_tools_sync()` is NOT shipped — there is no precedent for sync use of an agentic loop, and the existing `complete()` sync wrapper exists for stateless one-shots.

- **D-18:** `LLMLoopBudgetExceeded` `__init__` signature per research §4.1:
  ```python
  class LLMLoopBudgetExceeded(RuntimeError):
      def __init__(self, reason: str, iterations: int, elapsed_s: float):
          super().__init__(f"{reason} (iterations={iterations}, elapsed={elapsed_s:.1f}s)")
          self.reason = reason          # "max_iterations" | "max_seconds"
          self.iterations = iterations  # -1 if wall-clock fired before iteration counted
          self.elapsed_s = elapsed_s
  ```
- **D-19:** `RecursiveToolLoopError(RuntimeError)` and `LLMToolError(RuntimeError)` — message-only exceptions, no extra fields in v1.4. Future fields (e.g., underlying `anthropic.APIError` chain on `LLMToolError`) deferred to v1.5 if FB-D needs them.

### Tool Registry Invocation Contract (Area 6)

- **D-20:** `complete_with_tools()` accepts `tool_executor: Callable[[str, dict], Awaitable[str]] | None = None` parameter. Signature: `async (tool_name: str, args: dict) -> str`. Coordinator handles all stringification/sanitization/truncation downstream.
- **D-21:** Default `tool_executor` is a NEW public function `forge_bridge.mcp.registry.invoke_tool(name: str, args: dict) -> Awaitable[str]`. Importable by FB-D, by tests, by future external consumers. Lazy-imported inside `complete_with_tools()` only when caller passes `None`.
- **D-22:** `tools` parameter type: `list[mcp.types.Tool]` — the existing forge-bridge MCP type. Coordinator extracts `name`/`description`/`inputSchema` from each Tool for adapter schema translation. The default `invoke_tool()` looks up by name against the registered MCP tool registry. Matches roadmap text verbatim.
- **D-23:** Empty `tools=[]` raises `ValueError("complete_with_tools requires at least one tool; use acomplete() for plain completion")` immediately (before the loop starts). Defensive; no silent fall-through to plain completion semantics.

### Per-Turn Observability (Area 8)

- **D-24:** Per-turn structured log line at `logger.info` level with key-value space-delimited fields:
  ```
  tool-call iter=1 tool=forge_list_staged args_hash=ab12cd34 prompt_tokens=412 completion_tokens=78 elapsed_ms=823 status=continuing
  ```
  - `iter` (1-indexed), `tool` (selected tool name on this turn — empty if terminal), `args_hash` (8-hex prefix of sha256 of `json.dumps(args, sort_keys=True)`), `prompt_tokens`/`completion_tokens` (from provider response usage), `elapsed_ms` (wall time of this turn), `status` ∈ `{continuing, terminal, repeat_blocked, hallucinated, tool_error, tool_timeout}`.
  - **Why:** matches Phase 8 LRN-05 + Phase 9 console log shape (greppable, single-line). `logger.info` (not `debug`) so production deployments see it without log-level gymnastics.

- **D-25:** Per-session terminal log line at end of every session (success or error) at `logger.info`:
  ```
  tool-call session complete iter=4 elapsed_s=18.3 prompt_tokens_total=1882 completion_tokens_total=421 reason=end_turn
  ```
  - `reason` ∈ `{end_turn, max_iterations, max_seconds, recursive_call, tool_loop_error, value_error}`.
  - One line per session is the operational unit for ops triage.

- **D-26:** Args are hashed (8-hex sha256 prefix), NOT logged verbatim. Args may contain shot names, paths, sensitive payloads (matches the existing `LLMRouter` sensitive-routing posture).
- **D-27:** **No ExecutionLog integration.** ExecutionLog is for `bridge.execute()` calls (per LRN-05); tool-loop is a separate observability concern. Tool calls inside the loop that hit `bridge.execute()` will still write ExecutionLog records via the existing Phase 6 hook — no double-counting at the loop level. Keeps the Phase 6/8 boundary clean.

### Locked Defaults (recos accepted inline — no separate discussion needed)

- **D-28 (Q1, Ollama default model):** Stay on `qwen2.5-coder:32b` for FB-C ship. Open `SEED-DEFAULT-MODEL-BUMP-V1.4.x.md` for the `qwen3:32b` bump after assist-01 UAT. Mirrors the conservative pattern from prior phases.
- **D-29 (Q2, Ollama allow-list):** `_OLLAMA_TOOL_MODELS = frozenset({"qwen3:32b", "qwen3-coder:32b", "qwen2.5-coder:32b", "llama3.1:70b", "mixtral:8x22b"})` lives in `forge_bridge/llm/_adapters.py`. **Soft warning** when `local_model` is not in the set — `logger.warning("local_model %r is not in _OLLAMA_TOOL_MODELS allow-list; tool-call reliability may be unverified")`. No hard fail (artist experimentation friendly; production env vars are deterministic).
- **D-30 (cloud model bump):** Stay on `claude-opus-4-6` for FB-C ship. Plant `SEED-CLOUD-MODEL-BUMP-V1.4.x.md` for the `claude-opus-4-7` bump as an isolated commit after FB-C UAT. Mirrors D-28's conservative pattern.
- **D-31 (Q3, Anthropic strict):** `strict: true` always-on per tool definition WITH per-tool downgrade fallback. If Anthropic returns a 400 mentioning schema validation for a specific forge tool, the adapter retries that tool with `strict: false` and emits `logger.warning("downgraded tool %r to strict=false after Anthropic 400; check inputSchema compatibility", name)`. The per-tool downgrade is sticky for the session (no flap).
- **D-32 (live integration tests):** Env-gated using the Phase 8 pattern.
  - `LLMTOOL-01` (Ollama integration): gated by `FB_INTEGRATION_TESTS=1`. Skipped otherwise.
  - `LLMTOOL-02` (Anthropic cloud): gated by `FB_INTEGRATION_TESTS=1` AND `ANTHROPIC_API_KEY` present. Skipped otherwise.
  - All other LLMTOOL-03..07 acceptance tests use a stub adapter (deterministic responses) and run in default `pytest tests/`.
- **D-33 (Ollama keep_alive):** Set `keep_alive: "10m"` on every Ollama tool-call request from `OllamaToolAdapter`. Existing `acomplete()` is unchanged. Eliminates the 30s reload cliff mid-loop (research §6.8).
- **D-34 (SystemExit defense):** Coordinator's tool-exec block catches `(Exception, SystemExit)` (NOT bare `Exception`). Synthesizer blocklist already disallows `os._exit`/`sys.exit` (verified `_DANGEROUS_CALLS` and `_DANGEROUS_ATTR_CALLS` at `forge_bridge/learning/synthesizer.py:108-116`) but belt-and-suspenders against any pre-existing tool that might call them (research §6.6).

### Token Accounting

- **D-35:** Coordinator tracks per-session counters from each provider's response usage:
  - Anthropic: `response.usage.input_tokens`, `response.usage.output_tokens`
  - Ollama: `response.prompt_eval_count`, `response.eval_count`
  - Adapter normalizes to `(prompt_tokens, completion_tokens)` in `_TurnResponse.usage_tokens`. Coordinator sums these into per-session totals exposed only via the D-25 terminal log line. **No public counter API surface in v1.4** — log lines are sufficient; programmatic access can land in v1.5 if FB-D needs it.

### Test Strategy

- **D-36:** Test layout follows existing conventions:
  - `tests/llm/test_complete_with_tools.py` — coordinator unit tests against a fake adapter (loop logic, repeat-call detection, sanitization, budget caps, hallucinated-tool injection, empty-tools ValueError).
  - `tests/llm/test_anthropic_adapter.py` — Anthropic adapter wire-format tests with mocked HTTP (no live API).
  - `tests/llm/test_ollama_adapter.py` — Ollama adapter wire-format tests with mocked HTTP.
  - `tests/llm/test_sanitize_tool_result.py` — `_sanitize_tool_result()` unit tests (control chars, injection markers, truncation).
  - `tests/llm/test_recursive_guard.py` — LLMTOOL-07 contextvar test + synthesizer blocklist test.
  - `tests/integration/test_complete_with_tools_live.py` — LLMTOOL-01/02 env-gated live tests.

- **D-37:** Stub adapter pattern for coordinator tests:
  ```python
  class _StubAdapter:
      """Deterministic adapter that replays a scripted sequence of _TurnResponse."""
      def __init__(self, scripted_responses: list[_TurnResponse]) -> None: ...
      supports_parallel = False
      def init_state(...) -> _StubState: ...
      async def send_turn(state) -> _TurnResponse: return scripted.pop(0)
      def append_results(...) -> _StubState: ...
  ```
  Lets every loop-logic test be deterministic without a live LLM. Enables LLMTOOL-04 (repeat-call) test via "stub LLM emits same tool_call three times" pattern verbatim per research §7.

### Claude's Discretion

- Exact filename split between `_adapters.py` (one file) vs. `_anthropic_adapter.py` + `_ollama_adapter.py` (separate files) — planner picks based on adapter LOC. Research estimates ~80 LOC each, so single file likely fits cleanly.
- Whether the dataclass `_TurnResponse`, `_ToolCall`, `ToolCallResult` live in `_adapters.py` or a separate `_types.py` — planner decides based on import-cycle considerations.
- Test fixture placement for the stub adapter — likely `tests/llm/conftest.py` to share across `test_complete_with_tools.py` cases.
- Whether to add a `--no-skip-llm-integration` pytest flag in addition to the env var — not required, env var is sufficient and matches Phase 8.
- The exact wording of the synthetic repeat-call message string in D-07 — planner can polish; the substance is locked.
- The exact `args_hash` algorithm beyond "8-hex sha256 prefix of `json.dumps(args, sort_keys=True)`" — planner can use existing `hashlib` patterns.

### Folded Todos

None — todo list was empty at phase open (`gsd-tools todo match-phase 15` returned 0 matches).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` §`Phase 15 (FB-C)` (lines 149-168) — phase goal, depends-on, success criteria, requirements mapping, parallelizable-with note
- `.planning/REQUIREMENTS.md` §LLMTOOL — LLMTOOL-01..07 (all this phase); CHAT-03 (FB-D) overlaps acceptance with LLMTOOL-06
- `.planning/STATE.md` — Key constraints section: sanitization-patterns single-source-of-truth mandate (FB-C ships the consolidation); `LLMLoopBudgetExceeded` export mandate (16→17 — D-15 grows further to 16→19); FB-A/FB-C parallelizable note

### Targeted FB-C research (load-bearing — single source of truth for FB-C)
- `.planning/research/FB-C-TOOL-CALL-LOOP.md` — 8-section deep-dive replacing the standard SUMMARY/STACK/FEATURES/ARCHITECTURE/PITFALLS quartet for FB-C
  - §1 Executive summary — coordinator + 2 adapters; pin choices
  - §2 Anthropic Messages API tool use — request/response shape, terminal conditions, strict mode (D-31)
  - §3 Ollama tool calling — wire format, model allow-list (D-29), keep_alive (D-33), reliability issues
  - §4 Provider-agnostic loop algorithm — coordinator skeleton, budget order-of-fire, error-surfacing protocol, adapter contract
  - §5 Sensitive routing & schema translation — schema-format translation table, adapter pattern recommendation
  - §6 Pitfalls — repeat-call (§6.1 → D-07), token budget (§6.2 → D-08/D-11), recursive synthesis (§6.3 → D-12..D-14), parallel race (§6.4 → D-06), prompt injection (§6.5 → D-11), SystemExit (§6.6 → D-34), Anthropic outage (§6.7), Ollama unload (§6.8 → D-33)
  - §7 LLMTOOL-04..07 acceptance — verbatim test acceptance for each new requirement
  - §8 Open questions — Q1..Q6 resolved in D-28..D-32 above

### Existing LLM router and clients (load-bearing — extending these)
- `forge_bridge/llm/router.py` — `LLMRouter` class (D-17 adds `complete_with_tools()` method; D-15..D-16 add three exception classes)
- `forge_bridge/llm/__init__.py` — currently exports nothing relevant; D-15 grows `forge_bridge/__init__.py` `__all__` (NOT `llm/__init__.py`)
- `forge_bridge/llm/health.py` — sibling pattern for module organization

### Sanitization (Phase 7 source — D-09/D-10 hoists patterns)
- `forge_bridge/learning/sanitize.py` — `INJECTION_MARKERS` (line 50), `_CONTROL_CHAR_RE` (line 62), `_sanitize_tag()` (line 80) — D-09 hoists patterns to `forge_bridge/_sanitize_patterns.py`; D-10 makes this file a thin re-export shim
- `forge_bridge/learning/watcher.py:17` — verified caller of `_sanitize_tag, apply_size_budget` (D-10 invariant: ZERO caller updates)
- `forge_bridge/mcp/registry.py:90` — `_sanitize_tag` reference in comment only

### Synthesizer (Phase 3 — D-14 extends safety blocklist)
- `forge_bridge/learning/synthesizer.py:108-116` — `_DANGEROUS_CALLS`, `_DANGEROUS_ATTR_CALLS` frozensets; `_check_safety()` (line 119) — D-14 adds `forge_bridge.llm` import detection at the AST level

### MCP registry (D-21 adds public `invoke_tool`)
- `forge_bridge/mcp/registry.py` — `register_tools()` (line 129), `register_builtins()` reference; D-21 adds new public `invoke_tool(name, args)` function alongside
- `forge_bridge/mcp/tools.py` — existing tool function shape; default `invoke_tool` looks up registered tools here
- `forge_bridge/mcp/__init__.py` — currently exports `register_tools`, `get_mcp`; verify whether `invoke_tool` should be re-exported here too

### Public API surface (D-15 grows `__all__` 16→19)
- `forge_bridge/__init__.py:55` — `__all__` barrel; current 16 names; growing by 3 (`LLMLoopBudgetExceeded`, `RecursiveToolLoopError`, `LLMToolError`)
- `pyproject.toml` `[project.optional-dependencies]` — `[llm]` extra; D-02 adds `ollama>=0.6.1,<1` alongside existing `openai`/`anthropic`

### Phase 13/14 prior context (parallelizable-but-related)
- `.planning/phases/13-fb-a-staged-operation-entity-lifecycle/13-CONTEXT.md` — D-08 (repo-as-single-write-authority) is the analog of D-21 (registry-as-single-tool-invocation-authority)
- `.planning/phases/14-fb-b-staged-ops-mcp-tools-read-api/14-CONTEXT.md` — D-15..D-17 (Pydantic input model + tool registration patterns) — FB-C's tools are coordinator-internal but the schema translation in §5.1 mirrors FB-B's input model conventions

### Phase 8 prior context (export pattern + integration test pattern)
- `.planning/milestones/v1.2-phases/08-sql-persistence-protocol/08-CONTEXT.md` — D-02..D-04 (Protocol export + module-cohesion) is the precedent for D-15..D-16 (exception export + module placement); D-32 env-gated integration test pattern matches Phase 8

### Project vocabulary and architecture
- `docs/VOCABULARY.md` — canonical-vocabulary spec; FB-C tools query this vocabulary via the registered MCP tool surface
- `docs/ARCHITECTURE.md` — design rationale (event-driven, append-only events) — informs why D-27 keeps tool-loop observability separate from ExecutionLog

### Codebase intel
- `.planning/codebase/STRUCTURE.md` — directory layout
- `.planning/codebase/CONVENTIONS.md` — naming patterns (`_lazy_*` import helpers, `from __future__ import annotations`, frozenset constants), import order, error envelope conventions
- `.planning/codebase/TESTING.md` — test conventions for D-36..D-37
- `.planning/codebase/ARCHITECTURE.md` — system design summary

### Forward-looking seeds (plant during planning)
- `SEED-DEFAULT-MODEL-BUMP-V1.4.x.md` — `qwen2.5-coder:32b` → `qwen3:32b` after assist-01 UAT (D-28)
- `SEED-CLOUD-MODEL-BUMP-V1.4.x.md` — `claude-opus-4-6` → `claude-opus-4-7` after FB-C UAT (D-30)
- `SEED-PARALLEL-TOOL-EXEC-V1.5.md` — flip `parallel: bool = True` after serial baseline UAT (D-06)
- `SEED-MESSAGE-PRUNING-V1.5.md` — true history pruning beyond 8 KB ingest truncation (already noted in REQUIREMENTS Out of Scope)
- `SEED-TOOL-EXAMPLES-V1.5.md` — Anthropic `input_examples` field on registered tools (already noted)
- `SEED-CMA-MEMORY-V1.5+.md` — Claude Managed Agents memory feature integration (already noted)
- `SEED-CROSS-PROVIDER-FALLBACK-V1.5.md` — explicit design when sensitive-fallback becomes a need (research §5.4)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`LLMRouter`** (`forge_bridge/llm/router.py:56`) — extend with `complete_with_tools()` method (D-17) plus three exception classes (D-15..D-19). The constructor's `local_url`/`local_model`/`cloud_model`/`system_prompt` precedence (constructor > env > default) is the model for any new `complete_with_tools` kwargs that need env-var overrides.
- **`AsyncAnthropic` lazy import** (`forge_bridge/llm/router.py:204-213`) — D-02 reuses this for the Anthropic adapter; the new `ollama.AsyncClient` mirrors the same lazy-import-with-RuntimeError-on-missing pattern.
- **`INJECTION_MARKERS`** (`forge_bridge/learning/sanitize.py:50`) — hoisted by D-09 to `_sanitize_patterns.py`. Current pattern set is sufficient — no new markers needed for tool-result sanitization (the threat surface is identical: text→prompt-injection).
- **`_CONTROL_CHAR_RE`** (`forge_bridge/learning/sanitize.py:62`) — hoisted by D-09. The regex `[\x00-\x1f\x7f]` covers everything `_sanitize_tool_result()` needs to strip (D-11 keeps `\n` and `\t` by re-allowing them after the strip).
- **`_check_safety()`** (`forge_bridge/learning/synthesizer.py:119`) — D-14 extends with `forge_bridge.llm` import rejection. The function already walks the AST for `ast.Call` nodes; D-14 adds a parallel walk for `ast.Import`/`ast.ImportFrom` nodes.
- **`register_tools()`** (`forge_bridge/mcp/registry.py:129`) — pattern for D-21's new `invoke_tool()` function. Both live in `registry.py`; both are public.
- **Phase 8 env-gated test pattern** — D-32 follows the same precedent (Phase 8 used live PG to verify SQL persistence end-to-end, gated on `FB_INTEGRATION_TESTS=1`).

### Established Patterns

- **Lazy import with RuntimeError on missing dep** — `LLMRouter._get_local_client` / `_get_cloud_client` (router.py:188-213). D-02's `ollama.AsyncClient` follows this verbatim.
- **Constructor kwargs > env vars > hardcoded defaults** — `LLMRouter.__init__` (router.py:79-99). Any new `complete_with_tools` runtime knobs use the same precedence.
- **Module-level frozenset constants** — `_DANGEROUS_CALLS` (synthesizer.py:108), `INJECTION_MARKERS` (sanitize.py:50), `STANDARD_ROLE_KEYS` (per CONVENTIONS.md). D-29's `_OLLAMA_TOOL_MODELS` follows the pattern.
- **Single-line key-value structured log** — Phase 8 LRN-05 + Phase 9 console handlers. D-24/D-25 match shape.
- **Credential leak prevention** — log `type(exc).__name__`, never `str(exc)` (Phase 8 cf221fe). Coordinator's exception handlers in D-34 follow this rule for any provider 5xx that might carry credentials.
- **Public exception classes inherit `RuntimeError`** — `ServerError`, `ConnectionError` (per CONVENTIONS.md). D-15..D-19 follow.
- **Safety blocklist as AST walk** (`synthesizer.py:127-143`) — D-14 extends in-place; no new helper, no new module.

### Integration Points

- **`forge_bridge/llm/router.py`** — add `complete_with_tools()` method, three exception classes, `_in_tool_loop` contextvar, `_get_local_native_client()` lazy import for `ollama.AsyncClient` (D-02, D-12, D-15..D-19).
- **`forge_bridge/llm/_adapters.py`** (NEW) — `_ToolAdapter` Protocol, `AnthropicToolAdapter`, `OllamaToolAdapter`, `_TurnResponse`, `_ToolCall`, `ToolCallResult` dataclasses, `_OLLAMA_TOOL_MODELS` constant.
- **`forge_bridge/llm/_sanitize.py`** (NEW) — `_sanitize_tool_result()`, `_TOOL_RESULT_MAX_BYTES = 8192`.
- **`forge_bridge/_sanitize_patterns.py`** (NEW top-level) — hoisted `INJECTION_MARKERS`, `_CONTROL_CHAR_RE` (D-09).
- **`forge_bridge/learning/sanitize.py`** — convert constants to re-export shim (D-10): `from forge_bridge._sanitize_patterns import INJECTION_MARKERS, _CONTROL_CHAR_RE`. Helpers (`_sanitize_tag`, `apply_size_budget`) stay in place.
- **`forge_bridge/learning/synthesizer.py`** — extend `_check_safety()` with import-rejection walk for `forge_bridge.llm` modules (D-14).
- **`forge_bridge/mcp/registry.py`** — add public `invoke_tool(name, args) -> Awaitable[str]` function (D-21).
- **`forge_bridge/__init__.py:55`** — extend `__all__` from 16 → 19 with `LLMLoopBudgetExceeded`, `RecursiveToolLoopError`, `LLMToolError` (D-15).
- **`pyproject.toml`** — add `ollama>=0.6.1,<1` to `[project.optional-dependencies].llm` (D-02).
- **Tests:**
  - `tests/llm/test_complete_with_tools.py` (NEW) — coordinator unit tests against `_StubAdapter` (D-37)
  - `tests/llm/test_anthropic_adapter.py` (NEW) — adapter wire-format tests
  - `tests/llm/test_ollama_adapter.py` (NEW) — adapter wire-format tests
  - `tests/llm/test_sanitize_tool_result.py` (NEW) — sanitization unit tests
  - `tests/llm/test_recursive_guard.py` (NEW) — contextvar + synthesizer blocklist tests (LLMTOOL-07)
  - `tests/llm/conftest.py` (NEW) — stub adapter fixture
  - `tests/integration/test_complete_with_tools_live.py` (NEW) — env-gated live tests (LLMTOOL-01/02)

### What FB-D Will Consume From This Phase

- `LLMRouter.complete_with_tools()` — the chat endpoint's primary call path
- `LLMLoopBudgetExceeded` — caught by `/api/v1/chat`, mapped to HTTP 504 (gateway timeout)
- `RecursiveToolLoopError` — caught by `/api/v1/chat`, mapped to HTTP 500 (internal error)
- `LLMToolError` — caught by `/api/v1/chat`, mapped to HTTP 502 (bad gateway)
- `_sanitize_tool_result()` — wired through CHAT-03 sanitization boundary (already overlapping acceptance)
- `forge_bridge.mcp.registry.invoke_tool()` — chat endpoint passes registered MCP tools as `complete_with_tools(tools=[...], tool_executor=invoke_tool)` (or omits `tool_executor` to use the default — same effect)

</code_context>

<specifics>
## Specific Ideas

- **Hoist patterns, NOT helpers.** Phase 7's `_sanitize_tag()` and FB-C's new `_sanitize_tool_result()` have different REJECTION semantics:
  - `_sanitize_tag(tag)` returns `None` (rejects the entire tag) on injection-marker hit.
  - `_sanitize_tool_result(text)` REPLACES the marker substring inline with `[BLOCKED:INJECTION_MARKER]` and returns the text.
  Reason: tag content is consumer-supplied metadata that's safely droppable; tool-result content is authoritative output the LLM still needs to see (a tool returned 8 KB of legitimate output with one bad substring → drop the whole result and the loop loses its decision input). Different consumers, different semantics, same pattern set.

- **Args hashing in logs is a privacy posture, not just brevity.** D-26 hashes args because forge-bridge's tool surface includes `flame_*` calls that pass shot names, project paths, and synthesis intent strings (any of which can be sensitive in a client-confidential post-production environment). The 8-hex prefix is enough to correlate repeat-call detection (D-07) with log lines without leaking content.

- **Belt-and-suspenders is the recurring pattern for the recursive-synthesis guard.** Three independent layers prevent recursive LLM calls:
  1. Static AST check at synthesis time (D-14 — synthesizer rejects code importing `forge_bridge.llm`)
  2. Runtime contextvar check at call time (D-12/D-13 — `_in_tool_loop` raises `RecursiveToolLoopError` on entry)
  3. Process-level safeguard via existing synthesizer quarantine (Phase 3) — bad code never makes it into the registered tool surface
  This is the pattern Phase 7's PROV-04 used for `readOnlyHint=False` (explicit at registration AND honored by client policy AND backed by the bridge.execute() boundary).

- **Provider-neutral coordinator + thin adapters is the v1.4 commitment that pays off in v1.5.** Adding OpenAI/Gemini/Mistral as a third provider is one new adapter (~80 LOC), zero coordinator changes. The architectural honesty here is that the loop logic IS the product; adapter code is plumbing.

- **No streaming in v1.4.** FB-C is non-streaming. FB-D may revisit if user-facing token streaming becomes a UX requirement — the loop coordinator can wrap a streaming inner call without changing the surface. This is research §2.5 verbatim.

- **The 8 KB result truncation cap is a v1.4 boundary; expect it to grow.** `manifest_read` returning sidecar metadata for 100+ synthesized tools could exceed 8 KB. The constant is overridable via constructor kwarg (D-08), so chat-endpoint deployments that need more headroom can opt up. Real pruning is a v1.5+ feature (research §6.2).

</specifics>

<deferred>
## Deferred Ideas

- **Default Ollama tool model bump** (`qwen2.5-coder:32b` → `qwen3:32b`) — D-28; `SEED-DEFAULT-MODEL-BUMP-V1.4.x.md`.
- **Default cloud model bump** (`claude-opus-4-6` → `claude-opus-4-7`) — D-30; `SEED-CLOUD-MODEL-BUMP-V1.4.x.md`. Isolated commit after FB-C UAT.
- **Parallel tool execution within a single LLM turn** — `parallel: bool = False` kwarg ships in v1.4 (D-06) and raises `NotImplementedError` if `True`. Flip after serial-baseline UAT. `SEED-PARALLEL-TOOL-EXEC-V1.5.md`.
- **Cross-provider sensitive fallback (cloud-fail → local)** — loop state is provider-specific (Anthropic message dicts ≠ Ollama message dicts). Mid-loop fallback would require state reconstruction. `SEED-CROSS-PROVIDER-FALLBACK-V1.5.md`. Already noted in v1.4 Out of Scope.
- **True message-history pruning** — for v1.4, ingest-time truncation at 8 KB per result (D-08) is sufficient. Real pruning (summarize old turns, drop early tool results) is a v1.5+ feature. `SEED-MESSAGE-PRUNING-V1.5.md`.
- **Tool examples (`input_examples` field on Anthropic tool definitions)** — defer to v1.4.x or v1.5; not needed because forge-bridge tools have terse parameter sets. `SEED-TOOL-EXAMPLES-V1.5.md`.
- **Claude Managed Agents memory feature integration** — orthogonal to FB-C; track for when forge-bridge wants persistent agent memory. `SEED-CMA-MEMORY-V1.5+.md`.
- **Anthropic `tool_runner()` beta helper adoption** — REJECTED for FB-C (research §1, §2.7). Not a target — the coordinator + adapters pattern IS the design. No SEED.
- **OpenAI compatibility shim for Ollama tool calls** — REJECTED for FB-C (research §3.7). Not a target. No SEED.
- **Streaming responses in `complete_with_tools()`** — non-streaming for FB-C; FB-D may revisit when user-facing token streaming becomes a UX requirement. No SEED — coordinator is wrap-able without API change.
- **Programmatic per-session token counter API** — D-35 keeps token totals in log lines only. If FB-D needs `router.last_session_tokens()` or similar, that's a v1.5 add. No SEED.
- **Sync wrapper `complete_with_tools_sync()`** — no precedent for sync use of an agentic loop. If a caller appears, design then. No SEED.

### Reviewed Todos (not folded)

None — todo list was empty at phase open (`gsd-tools todo match-phase 15` returned 0 matches).

</deferred>

---

*Phase: 15-fb-c-llmrouter-tool-call-loop*
*Context gathered: 2026-04-26*
