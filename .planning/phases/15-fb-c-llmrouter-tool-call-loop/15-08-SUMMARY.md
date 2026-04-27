---
phase: 15-fb-c-llmrouter-tool-call-loop
plan: 08
subsystem: llm
tags: [coordinator, agentic-loop, fb-c, llmtool-03, llmtool-04, llmtool-05, llmtool-06, llmtool-07, central-wiring]

# Dependency graph
requires:
  - phase: 15-fb-c-llmrouter-tool-call-loop (plan 02) — _get_local_native_client lazy import for ollama.AsyncClient
  - phase: 15-fb-c-llmrouter-tool-call-loop (plan 03) — LLMLoopBudgetExceeded + RecursiveToolLoopError + LLMToolError exception classes
  - phase: 15-fb-c-llmrouter-tool-call-loop (plan 04) — _sanitize_tool_result + _TOOL_RESULT_MAX_BYTES constants
  - phase: 15-fb-c-llmrouter-tool-call-loop (plan 05) — AnthropicToolAdapter + OllamaToolAdapter + ToolCallResult / _ToolCall / _TurnResponse + _StubAdapter test fixture
  - phase: 15-fb-c-llmrouter-tool-call-loop (plan 06) — _in_tool_loop ContextVar + acomplete entry check + synthesizer AST guard
  - phase: 15-fb-c-llmrouter-tool-call-loop (plan 07) — forge_bridge.mcp.registry.invoke_tool default executor
provides:
  - LLMRouter.complete_with_tools(prompt, tools, sensitive=, ..., parallel=False) — public async agentic tool-call loop coordinator (the FB-C product surface)
  - All five LLMTOOL-03..07 acceptance criteria enforced in one place (budget caps, repeat-call detection, sanitization, truncation, recursive-synthesis guard)
  - D-24 per-turn structured log line + D-25 per-session terminal log line (both INFO; reason/status taxonomies locked)
  - D-26 args sha256 hashing for log lines (raw arg values NEVER reach logs)
  - 21 comprehensive coordinator unit tests across 10 classes (full LLMTOOL-03..07 acceptance via _StubAdapter)
affects:
  - Phase 16 (FB-D) chat endpoint — consumes complete_with_tools(), catches all 3 exception classes, maps to HTTP 504/500/502 per D-15
  - Plan 15-09 (Wave 4 live integration tests) — exercises this coordinator end-to-end against real Ollama / Anthropic backends

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Provider-neutral coordinator + thin adapters (D-01) — loop logic lives in router.py; provider wire-format lives in _adapters.py; no provider knowledge leaks into the coordinator"
    - "asyncio.wait_for double-wrap: outer wraps the entire loop body (D-04 wall-clock cap); inner wraps each tool_executor call (D-05 per-tool sub-budget)"
    - "ContextVar try/finally for LLMTOOL-07 layer 2 — _in_tool_loop.set(True) inside complete_with_tools, reset(token) in outer finally so cleanup runs even on exception"
    - "Per-tool sub-budget formula max(1.0, min(30.0, remaining_global_budget)) — prevents one slow tool from consuming the entire wall-clock budget"
    - "(Exception, SystemExit) belt-and-suspenders catch with inner _safe_tool_call wrapper to convert SystemExit→RuntimeError before asyncio.wait_for re-raises BaseException"
    - "Per-session terminal log line emitted unconditionally in finally — runs on success and every error path (reason taxonomy: end_turn / max_iterations / max_seconds / recursive_call / tool_loop_error / value_error)"
    - "json.dumps(args, sort_keys=True) for canonical args representation — used by both D-07 repeat-call detection (key) and D-26 args hashing (input)"

key-files:
  created:
    - tests/llm/test_complete_with_tools.py — 553 LOC, 21 tests across 10 classes
  modified:
    - forge_bridge/llm/router.py — +372 LOC: imports, 1 new public async method (complete_with_tools), nested _safe_tool_call wrapper, 6 stdlib imports added (collections, hashlib, json, time, Awaitable, Callable, TYPE_CHECKING)

key-decisions:
  - "Wrap tool_executor call in inner _safe_tool_call coroutine: catch SystemExit and re-raise as RuntimeError before asyncio.wait_for sees it. asyncio re-raises BaseException from task callbacks even when caught — Python's `python -c '...'` test confirmed this. The plan's spec had the catch wrapping the wait_for directly, which would have broken D-34. This is a Rule 1 fix discovered during Task 2 test execution."
  - "Sentinel dict (_system_exit_signal['hit']) records SystemExit hit so the outer except block surfaces 'SystemExit' as the type name — D-34 attribution preserved end-to-end. Without this, the LLM would see 'RuntimeError' which is the converted exception, masking the actual signal."
  - "Implementation followed plan verbatim for D-03..D-08, D-12..D-14, D-17..D-27 — every locked decision applied as specified. Only deviation was the SystemExit conversion (Rule 1 bug)."
  - "Two-commit Task 2 split: Rule 1 SystemExit fix went into a separate fix(...) commit (186c503) before the test commit (1126974), keeping the test commit clean as 'tests pass against shipped impl'."
  - "Plan-level verification confirms exactly 2 files modified (forge_bridge/llm/router.py + tests/llm/test_complete_with_tools.py) — git diff --stat baseline matches plan's <verification> block."

patterns-established:
  - "asyncio + SystemExit: when catching BaseException through asyncio.wait_for, an inner async wrapper is required because asyncio's task-callback machinery re-raises BaseException even when the outer frame catches it. Future code that needs to catch SystemExit/KeyboardInterrupt under asyncio MUST use this inner-wrapper pattern."
  - "Coordinator loop body as nested async function: closes over loop state (state, counters, started timestamp) while remaining wrappable by asyncio.wait_for. nonlocal declarations on state and counters are required because the inner function reassigns them."
  - "Stub adapter test pattern: replace adapter classes via patch.multiple at the lazy-import site (forge_bridge.llm._adapters.OllamaToolAdapter), patch _get_*_client methods on the router to skip provider SDK imports, run coordinator end-to-end against deterministic scripted _TurnResponse sequence."

requirements-completed: [LLMTOOL-03, LLMTOOL-04, LLMTOOL-05, LLMTOOL-06, LLMTOOL-07]

# Metrics
duration_seconds: ~9 min
completed_date: "2026-04-27"
tasks_completed: 2
files_changed: 2
tests_added: 21
loc_added: 922
---

# Phase 15 Plan 08: LLMRouter.complete_with_tools Coordinator Summary

**The FB-C product surface — `LLMRouter.complete_with_tools(prompt, tools, sensitive=, ..., parallel=False)` is now a public async method on `LLMRouter` that wires every Wave 1+2 helper into a single agentic tool-call loop, enforcing all five LLMTOOL-03..07 acceptance criteria in one place.**

## What Shipped

**2 files modified/created (922 insertions, 3 deletions):**

| File | Status | LOC | Purpose |
|------|--------|-----|---------|
| `forge_bridge/llm/router.py` | MODIFIED | +372 | New `complete_with_tools` async method (~340 LOC) + 6 stdlib imports (collections, hashlib, json, time, Awaitable, Callable, TYPE_CHECKING) |
| `tests/llm/test_complete_with_tools.py` | NEW | 553 | 21 coordinator unit tests across 10 classes — full LLMTOOL-03..07 acceptance via `_StubAdapter` |

## Tasks Completed

| Task | Name | Commit | Status |
|------|------|--------|--------|
| 1 | Implement LLMRouter.complete_with_tools coordinator | `1809b1d` | ✓ |
| (Rule 1 fix) | Convert SystemExit→RuntimeError before asyncio.wait_for | `186c503` | ✓ |
| 2 | Create comprehensive coordinator unit tests | `1126974` | ✓ |

## Test Results

- **21 / 21** tests pass in `tests/llm/test_complete_with_tools.py` (the new coordinator tests)
- **209 / 209** tests pass in the full FB-C Wave 1+2+3 sweep:
  - `pytest tests/llm/ tests/test_llm.py tests/test_synthesizer.py tests/test_mcp_registry.py tests/test_public_api.py tests/test_sanitize.py -x -q`
  - 21 (this plan) + 28 (plan 15-05 adapters) + 24 (plan 15-04 sanitize) + 10 (plan 15-06 recursive guard) + 7 (plan 15-07 invoke_tool) + Wave 0 baselines
- Zero regressions across the full Wave 1+2 surface

### Test class breakdown

| Class | Tests | Coverage |
|-------|-------|----------|
| `TestEmptyToolsRejection` | 1 | D-23 — ValueError on tools=[] before adapter init |
| `TestParallelKwargAdvertisement` | 1 | D-06 — NotImplementedError on parallel=True (v1.5 advertisement) |
| `TestLoopTermination` | 2 | LLMTOOL-01-style happy paths — immediate terminal + 2-turn (call → result → terminal) |
| `TestRepeatCallDetection` | 2 | LLMTOOL-04 / D-07 — 3rd identical call synthetic injection; 2-call legitimate pass-through |
| `TestBudgetCaps` | 3 | LLMTOOL-03 / D-03 (max_iterations) + D-04 (max_seconds, iterations=-1) + D-05 (per-tool sub-budget timeout) |
| `TestHallucinatedToolName` | 1 | research §4.3 — coordinator pre-check catches BEFORE invoke; available-tool list surfaced |
| `TestToolResultSanitization` | 3 | LLMTOOL-05/06 / D-08/D-11 — injection-marker REPLACE inline, 8192-byte default truncation, override kwarg |
| `TestToolErrorHandling` | 2 | LLMTOOL-03 + D-34 — ValueError continues loop with str(exc) NEVER leaked, SystemExit caught with type-attribution |
| `TestRecursiveGuardRuntime` | 3 | LLMTOOL-07 / D-12/D-13 — ContextVar SET during loop body, RESET after, RecursiveToolLoopError on nested call, finally cleanup on exception |
| `TestObservabilityLogs` | 3 | D-24/D-25/D-26 — per-session terminal log emitted, args hashed (NEVER raw shot_name/path), reason=max_iterations on iteration cap |

## Key Design Confirmations

### The coordinator is provider-neutral; the adapters are thin

Per D-01: ONE coordinator + TWO adapter modules. The 340-LOC coordinator handles every loop concern (iteration cap, wall-clock cap, per-tool sub-budget, repeat-call detection, sanitization, truncation, hallucinated-name handling, observability, recursive-synthesis guard, exception wrapping). The two adapters from plan 15-05 (446 LOC total) handle exactly one thing each: translating between canonical conversation state (`_TurnResponse`, `_ToolCall`, `ToolCallResult`) and the provider's wire format. Adding a third provider (OpenAI / Gemini / Mistral) is one new adapter — zero coordinator changes.

### LLMTOOL-07 belt-and-suspenders is now FULLY wired (3 layers)

This plan completes layer 2 of the recursive-synthesis defense:

1. **Layer 1 (static AST guard)** — plan 15-06 extended `_check_safety()` in `forge_bridge/learning/synthesizer.py` to reject any synthesized code importing from `forge_bridge.llm`. Caught at synthesis time before the file ever reaches the registered tool surface.
2. **Layer 2 (runtime ContextVar guard)** — plan 15-06 declared `_in_tool_loop` ContextVar at module level in `router.py` and added the entry check to `acomplete()`. **This plan completes the layer by adding the entry check to `complete_with_tools()` AND setting the ContextVar via `try/finally` inside `complete_with_tools()`'s body.** Cleanup runs even when the wall-clock cap fires mid-tool-call.
3. **Layer 3 (process-level safeguard)** — Phase 3 manifest-based quarantine — bad code never makes it into the registered tool surface. Already in production.

The three layers are independent: even if a synthesized tool body bypassed the static AST check via `importlib` dynamic imports, the runtime ContextVar would block it; even if a buggy ContextVar reset happened, the manifest quarantine catches the file at startup.

### asyncio + SystemExit edge case (Rule 1 fix)

The plan's `<action>` block had `except (Exception, SystemExit) as exc` directly wrapping `asyncio.wait_for(tool_executor(...), timeout=per_tool_budget)`. This **does not work** under Python 3.11+: asyncio's task-callback machinery re-raises `BaseException` (including `SystemExit`) even when the immediate enclosing frame catches it. The local `except` clause runs (and we observed `status=tool_error` logging), but `asyncio` ALSO surfaces the `SystemExit` to the event loop, which terminates the process with exit code 1.

**Fix:** Inner `_safe_tool_call` async wrapper inside the loop catches `SystemExit` and re-raises as `RuntimeError("SystemExit")` before `asyncio.wait_for` sees it. A sentinel dict (`_system_exit_signal`) records the SystemExit hit so the outer catch surfaces `"SystemExit"` as the exception type to the LLM (D-34 attribution preserved).

This is a Rule 1 (bug) fix discovered during Task 2 test execution. The implementation was structurally correct but ran into Python's specific BaseException re-raise semantics under `asyncio.wait_for`. Documented as a separate `fix(...)` commit (186c503) so the patch is auditable.

### Args hashing privacy posture (D-26)

Per CONTEXT.md `<specifics>`: forge-bridge's tool surface includes `flame_*` calls that pass shot names, project paths, and synthesis intent strings — any of which can be sensitive in a client-confidential post-production environment. The 8-hex sha256 prefix is enough to correlate repeat-call detection (D-07) with log lines without leaking content. Verified by `TestObservabilityLogs::test_per_turn_log_includes_args_hash_not_raw_args` — tool args `{"shot_name": "PROJ_secret_0010", "path": "/clients/acme"}` produce log lines containing `args_hash=...` BUT containing NEITHER the shot name NOR the path string anywhere in the captured log records.

### Wave 3 closes the FB-C coordinator surface; Wave 4 ships live integration tests

After this plan:
- All 5 LLMTOOL-03..07 acceptance criteria are deterministically tested against the `_StubAdapter`
- `forge_bridge.LLMLoopBudgetExceeded` / `RecursiveToolLoopError` / `LLMToolError` are exported from the public barrel (16→19 per plan 15-03)
- Phase 16 (FB-D) chat endpoint can `from forge_bridge import LLMRouter; from forge_bridge.llm.router import LLMLoopBudgetExceeded, RecursiveToolLoopError, LLMToolError` and map to HTTP 504/500/502 respectively

Wave 4 plan 15-09 will exercise this coordinator end-to-end against:
- Real Ollama on assist-01 (LLMTOOL-01 — gated by `FB_INTEGRATION_TESTS=1`)
- Real Anthropic API (LLMTOOL-02 — gated by `FB_INTEGRATION_TESTS=1` AND `ANTHROPIC_API_KEY`)

## Implementation Decisions Made

### Nested `_loop_body` async function for asyncio.wait_for wrapping

`_loop_body` is defined as a nested async function inside `complete_with_tools` so it can close over `state`, `seen_calls`, `started`, and the token counters while still being wrappable by `asyncio.wait_for(..., timeout=max_seconds)`. `nonlocal` declarations on `state`, `prompt_tokens_total`, `completion_tokens_total`, `completed_iterations` are required because the inner function reassigns them.

### Order-of-fire: wall-clock cap vs iteration cap

Per D-04 verbatim: when both could trip, the wall-clock fires first (it wraps the whole loop). The except-clause ordering reflects this: `asyncio.TimeoutError` (from the outer `wait_for`) is caught first, mapped to `LLMLoopBudgetExceeded(reason="max_seconds", iterations=-1)`. The inner loop's own raise of `LLMLoopBudgetExceeded(reason="max_iterations", ...)` propagates separately and is caught by the next except clause to set `terminal_reason = "max_iterations"`.

### Per-session terminal log emitted in `finally` (always)

D-25 specifies one terminal log line per session — emitted on success AND every error path. The `finally` block runs after the inner try/except chain has set `terminal_reason` to the appropriate value. The `_in_tool_loop.reset(token)` happens FIRST in the finally so even if log emission fails (e.g., logger handler crashes), the ContextVar is cleaned up.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] SystemExit re-raised by asyncio.wait_for despite explicit catch**

- **Found during:** Task 2 — `test_SystemExit_caught_per_d34_belt_and_suspenders` failed with `SystemExit: 1` even though the catch clause logged `status=tool_error`
- **Issue:** The plan's spec had `except (Exception, SystemExit) as exc:` wrapping `asyncio.wait_for(tool_executor(...))` directly. asyncio's task-callback machinery re-raises BaseException (SystemExit, KeyboardInterrupt) from completed tasks even when the immediate enclosing frame catches it — Python 3.11+ behavior verified via standalone repro:
  ```python
  try:
      await asyncio.wait_for(evil(), timeout=1.0)
  except (Exception, SystemExit) as exc:
      print(f'caught: {type(exc).__name__}')  # PRINTS this
  # ... but asyncio.run() still exits with code 1
  ```
- **Fix:** Inner `_safe_tool_call` async wrapper catches SystemExit and re-raises as RuntimeError before asyncio.wait_for sees it. Sentinel dict `_system_exit_signal["hit"]` records the SystemExit hit so the outer catch surfaces "SystemExit" as the exc_type to the LLM (D-34 attribution preserved). Test now passes.
- **Files modified:** `forge_bridge/llm/router.py`
- **Commit:** `186c503` (separate `fix(...)` commit so the diff is auditable)

This was a structural bug in the plan's `<action>` snippet caused by an interaction between Python 3.11+ asyncio task-callback machinery and BaseException — not a misread of the plan. The D-34 spec is preserved and verified by the test; only the implementation pattern needed adjustment.

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Zero scope drift. The fix is mechanical (inner wrapper), preserves the D-34 contract verbatim (LLM sees "SystemExit" via the wrapper-set sentinel), and is documented in this Summary + the standalone fix commit message.

## Cross-Plan Verification

- `pytest tests/llm/test_complete_with_tools.py -x -v` → **21/21 passed** (all coordinator unit tests)
- `pytest tests/llm/ tests/test_llm.py tests/test_synthesizer.py tests/test_mcp_registry.py tests/test_public_api.py tests/test_sanitize.py -x -q` → **209/209 passed** (full FB-C Wave 1+2+3 test sweep, zero regression)
- `python -c "import asyncio, inspect; from forge_bridge.llm.router import LLMRouter, _in_tool_loop; assert inspect.iscoroutinefunction(LLMRouter.complete_with_tools); assert _in_tool_loop.get() is False"` → exits 0 (cross-module sanity AFTER the test sweep — proves _in_tool_loop is not stuck True)
- `git diff --stat 52a9875..HEAD` → exactly 2 files modified (forge_bridge/llm/router.py +372/-3, tests/llm/test_complete_with_tools.py NEW +553)

## Plan Acceptance Criteria — All Met

- ✅ `grep -c "async def complete_with_tools" forge_bridge/llm/router.py` returns `1`
- ✅ `grep -c "_in_tool_loop.set(True)" forge_bridge/llm/router.py` returns `1`
- ✅ `grep -c "_in_tool_loop.reset(token)" forge_bridge/llm/router.py` returns `1`
- ✅ `grep -c "raise NotImplementedError" forge_bridge/llm/router.py` returns `1`
- ✅ `grep -c "raise ValueError" forge_bridge/llm/router.py` returns `1`
- ✅ `grep -c "asyncio.wait_for" forge_bridge/llm/router.py` returns `3` (≥2 required: per-tool wait_for + outer wall-clock + inner safe wrapper invocation)
- ✅ `grep -c "LLMLoopBudgetExceeded" forge_bridge/llm/router.py` returns `7` (class def + 2 raise sites + docstring + import + 3 references)
- ✅ `grep -c "(Exception, SystemExit)" forge_bridge/llm/router.py` returns `2` (1 catch + 1 comment) — exceeds spec's `1` minimum
- ✅ `grep -c "_sanitize_tool_result" forge_bridge/llm/router.py` returns `8` (used in 4+ result-building paths + import)
- ✅ `grep -c "hashlib.sha256" forge_bridge/llm/router.py` returns `1`
- ✅ `grep -c "json.dumps.*sort_keys=True" forge_bridge/llm/router.py` returns `1`
- ✅ `grep -c "tool-call session complete" forge_bridge/llm/router.py` returns `1`
- ✅ `grep -c "tool-call iter=" forge_bridge/llm/router.py` returns `4`
- ✅ `grep -c "from forge_bridge.mcp.registry import invoke_tool" forge_bridge/llm/router.py` returns `1`
- ✅ All 10 `class Test*` declarations present in `tests/llm/test_complete_with_tools.py`
- ✅ `grep -c "def test_" tests/llm/test_complete_with_tools.py` returns `21` (≥18 required)
- ✅ `pytest tests/llm/ tests/test_llm.py tests/test_synthesizer.py tests/test_mcp_registry.py tests/test_public_api.py -x -q` → 0 (full Wave 1+2+3 sweep clean)

## Threat Model Compliance

All threats T-15-37 through T-15-46 from the plan's `<threat_model>` are mitigated and tested:

| Threat | Status | Test |
|--------|--------|------|
| T-15-37 (prompt injection via tool result) | mitigated | TestToolResultSanitization::test_tool_result_passes_through_sanitizer |
| T-15-38 (runaway loop exhausts cloud credits) | mitigated | TestBudgetCaps::test_max_iterations + test_max_seconds |
| T-15-39 (synthesized tool sys.exit kills server) | mitigated | TestToolErrorHandling::test_SystemExit_caught_per_d34 (with Rule 1 fix) |
| T-15-40 (recursive synthesis via importlib) | mitigated | TestRecursiveGuardRuntime (3 tests) — layer 2 fully wired |
| T-15-41 (credentials in log lines / error messages) | mitigated | TestObservabilityLogs::test_per_turn_log_includes_args_hash_not_raw_args + TestToolErrorHandling::test_tool_exception_caught_loop_continues |
| T-15-42 (repeat-call infinite loop) | mitigated | TestRepeatCallDetection::test_third_identical_call_injects_synthetic |
| T-15-43 (single bad tool aborts session) | mitigated | TestToolErrorHandling::test_tool_exception_caught_loop_continues |
| T-15-44 (adapter raw response in logs) | accept | usage_tokens are integers, raw object never logged (verified by test_per_turn_log_includes_args_hash) |
| T-15-45 (hallucinated name reaches different surface) | mitigated | TestHallucinatedToolName + KeyError defense-in-depth catch |
| T-15-46 (_in_tool_loop stuck True after exception) | mitigated | TestRecursiveGuardRuntime::test_in_tool_loop_reset_even_on_exception |

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| `1809b1d` | feat | implement LLMRouter.complete_with_tools coordinator |
| `186c503` | fix | convert SystemExit to RuntimeError before asyncio.wait_for sees it (Rule 1) |
| `1126974` | test | comprehensive coordinator unit tests for complete_with_tools |

## What Phase 16 (FB-D) Will Consume Next

The chat endpoint (Phase 16) imports the FB-C coordinator surface verbatim:

```python
from forge_bridge import LLMRouter, LLMLoopBudgetExceeded, RecursiveToolLoopError, LLMToolError
from forge_bridge.mcp.registry import invoke_tool

router = get_router()  # singleton
try:
    answer = await router.complete_with_tools(
        prompt=user_message,
        tools=registered_mcp_tools,
        sensitive=True,  # local Ollama for sensitive client work
        # tool_executor defaults to invoke_tool — no override needed
    )
except LLMLoopBudgetExceeded:
    return Response(status=504, body={"error": "loop budget exceeded"})
except RecursiveToolLoopError:
    return Response(status=500, body={"error": "internal recursion"})
except LLMToolError as exc:
    return Response(status=502, body={"error": f"provider failure: {type(exc.__cause__).__name__}"})
```

The HTTP-status mapping is a one-line catch per exception type — exactly the discrimination D-15 was designed to enable. CHAT-03 (sanitization) overlaps with LLMTOOL-06 acceptance and is automatically satisfied by the wired sanitization boundary inside `complete_with_tools`.

## Next Phase Readiness

**Wave 4 plan 15-09 (live integration tests) is unblocked.** The coordinator's behavior is fully specified by the 21 unit tests; live tests in plan 15-09 only need to verify wire-format compatibility against real provider endpoints, not loop-logic correctness.

**Phase 16 (FB-D) chat endpoint is unblocked.** All exports needed (LLMRouter.complete_with_tools method + 3 exception classes from the public barrel + invoke_tool from mcp.registry) are in place and tested.

## Self-Check: PASSED

- ✅ `forge_bridge/llm/router.py` exists with `complete_with_tools` method (verified by inspect.iscoroutinefunction)
- ✅ `tests/llm/test_complete_with_tools.py` exists (553 LOC, 21 tests, 10 classes)
- ✅ Commit `1809b1d` exists in `git log` (Task 1 — coordinator impl)
- ✅ Commit `186c503` exists in `git log` (Rule 1 fix — SystemExit handling)
- ✅ Commit `1126974` exists in `git log` (Task 2 — coordinator tests)
- ✅ All Plan-level Acceptance Criteria pass (grep counts + pytest sweep)
- ✅ `pytest tests/llm/ tests/test_llm.py tests/test_synthesizer.py tests/test_mcp_registry.py tests/test_public_api.py tests/test_sanitize.py -x -q` exits 0 (209 tests)
- ✅ Cross-module sanity (`_in_tool_loop.get() is False` after sweep) passes
- ✅ `git diff --stat 52a9875..HEAD` shows exactly 2 files modified (matches plan's `<verification>` requirement)
- ✅ All 10 entries in T-15-37..T-15-46 threat register addressed (9 mitigated by tests, 1 accepted with verified posture)

---

*Phase: 15-fb-c-llmrouter-tool-call-loop*
*Plan: 08 (FB-C Wave 3 — central coordinator that closes the FB-C surface)*
*Completed: 2026-04-27*
