---
phase: 16-fb-d-chat-endpoint
plan: 01
subsystem: llm
tags: [llm-router, tool-call, agentic-loop, fb-c-extension, d-02a, pattern-b]

# Dependency graph
requires:
  - phase: 15-fb-c-llmrouter-tool-call-loop
    provides: LLMRouter.complete_with_tools() coordinator + Anthropic/Ollama adapters that already speak the messages list natively
provides:
  - "complete_with_tools(messages: list[dict] | None = None) keyword-only kwarg per D-02a Pattern B"
  - "Mutual-exclusion guard on prompt vs messages (T-16-01-01 mitigation) — both-set + neither-set both raise ValueError"
  - "AnthropicToolAdapter / OllamaToolAdapter / _ToolAdapter Protocol all forward messages= verbatim to state.messages"
  - "_StubAdapter.init_state accepts messages= and exposes messages_kwarg in state for test introspection"
  - "TestCompleteWithToolsMessagesKwarg test class pinning the D-02a contract (4 tests)"
affects:
  - 16-04-PLAN.md (FB-D chat handler — direct consumer of complete_with_tools(messages=...) without lossy stitching)
  - 16-05/06/07 (Web UI chat panel + parity tests reuse the chat handler)
  - projekt-forge v1.5 (Flame hooks chat client — same wire shape via cross-repo parity contract)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Keyword-only kwarg separator (* after prompt) to lock down the public surface against positional drift"
    - "Optional structured-history pass-through: caller decides shape, coordinator forwards verbatim, adapter does not auto-wrap"
    - "Mutual-exclusion guard ordering: recursive-loop guard fires FIRST (preserves T-16-01-03 ordering), then the new D-02a guard"

key-files:
  created: []
  modified:
    - "forge_bridge/llm/router.py — complete_with_tools signature + mutual-exclusion guards + adapter.init_state forwarding + Args docstring"
    - "forge_bridge/llm/_adapters.py — AnthropicToolAdapter.init_state, OllamaToolAdapter.init_state, _ToolAdapter Protocol all accept messages= kwarg"
    - "tests/llm/conftest.py — _StubAdapter.init_state accepts messages= and surfaces messages_kwarg in state (required so the coordinator's unconditional kwarg pass-through doesn't crash existing stub tests)"
    - "tests/llm/test_complete_with_tools.py — added TestMessagesKwargSignature (RED scaffold, 2 tests) and TestCompleteWithToolsMessagesKwarg (D-02a pin, 4 tests)"

key-decisions:
  - "Made `prompt` default to '' and added a keyword-only `*` separator after it, then placed `messages` at the end — preserves backwards-compat for every existing call site (all of which already pass `tools=...` by keyword)"
  - "Mutual-exclusion guard fires AFTER `_in_tool_loop.get()` but BEFORE `if not tools:` — preserves the recursive-call attribution per T-16-01-03 from the plan's threat register"
  - "Ollama adapter prepends the system message to a caller-supplied messages list ONLY if the caller didn't already include one — preserves Ollama's leading-system-message convention while letting callers override it"
  - "Updated _StubAdapter to accept the new kwarg (Rule 3 deviation, see below) — the coordinator's adapter.init_state(..., messages=messages) is unconditional, so any adapter without the kwarg would TypeError every existing stub-based test"

patterns-established:
  - "D-02a Pattern B: when a public surface needs to expose an internal capability the adapters already speak (here: structured messages list), extend the public method with an Optional kwarg + mutual-exclusion guard rather than parsing/stitching at the call site"
  - "Test pinning: a small RED scaffold (signature inspect-only) + a separate full-contract class is cleaner than one giant test class — RED commit is unambiguous, full pin lands in the next commit"

requirements-completed:
  - CHAT-05  # External-consumer parity (FB-D — partial; this plan is the prerequisite that lets the chat handler honor the wire-shape messages contract without lossy stitching. Full CHAT-05 closure depends on 16-04/06/07.)

# Metrics
duration: 4m16s
completed: 2026-04-27
---

# Phase 16 Plan 01: messages= kwarg on complete_with_tools (D-02a Pattern B) Summary

**Extended `LLMRouter.complete_with_tools()` with an optional `messages: list[dict] | None = None` kwarg + mutual-exclusion guard so FB-D's chat handler (plan 16-04) can pass through provider-shape `[user, assistant, tool]` history verbatim — no lossy stitching, no wire-vs-internal divergence.**

## Performance

- **Duration:** 4m 16s
- **Started:** 2026-04-27T17:31:55Z
- **Completed:** 2026-04-27T17:36:11Z
- **Tasks:** 2 (both TDD)
- **Files modified:** 4

## Accomplishments

- `LLMRouter.complete_with_tools()` now accepts `messages=` (D-02a Pattern B), with `prompt=` defaulting to `""` so messages-only callers can omit it. Keyword-only separator (`*`) locks the surface down against positional drift in future call sites.
- Mutual-exclusion guard wired in the correct order: `_in_tool_loop` recursive guard first, then D-02a both-set / neither-set checks, then the existing D-23 empty-tools check.
- All three adapter implementations (`AnthropicToolAdapter`, `OllamaToolAdapter`, the `_ToolAdapter` Protocol) and the test `_StubAdapter` accept the new kwarg and forward it verbatim to `state.messages`.
- 6 new tests (2 RED scaffold + 4 contract pin) lock the surface; all 23 pre-existing `test_complete_with_tools.py` tests pass without modification — backwards-compat proven.
- Unblocks plan 16-04 (FB-D chat handler) which directly consumes `complete_with_tools(messages=[...], tools=..., sensitive=True, ...)`.

## Task Commits

Each task was committed atomically following the TDD RED → GREEN flow:

1. **Task 1 RED: failing test for messages= kwarg signature** — `d41508e` (test)
2. **Task 1 GREEN: messages= kwarg implementation** — `9a9a56b` (feat)
3. **Task 2: TestCompleteWithToolsMessagesKwarg pin (4 tests)** — `e2a4694` (test)

_Plan metadata commit will be added by the orchestrator after the worktree returns._

## Files Created/Modified

- `forge_bridge/llm/router.py` — `complete_with_tools()` signature: added `*` keyword-only separator after `prompt: str = ""` and `messages: Optional[list[dict]] = None` at the end. Inserted D-02a mutual-exclusion guards. Updated `adapter.init_state(..., messages=messages)`. Extended Args docstring.
- `forge_bridge/llm/_adapters.py` — added `messages: Optional[list[dict]] = None` kwarg to `_ToolAdapter.init_state` Protocol, `AnthropicToolAdapter.init_state`, and `OllamaToolAdapter.init_state`. When `messages` is provided, both adapters skip the auto-wrap path and use the list verbatim. Ollama adapter prepends `system` only if caller did not include one.
- `tests/llm/conftest.py` — `_StubAdapter.init_state` accepts `messages=` and exposes `messages_kwarg` in state for test introspection. Required because the coordinator's `adapter.init_state(..., messages=messages)` call is unconditional — without the stub update, every existing `_StubAdapter`-based test would TypeError.
- `tests/llm/test_complete_with_tools.py` — added `TestMessagesKwargSignature` (RED scaffold, 2 inspect-only tests) and `TestCompleteWithToolsMessagesKwarg` (D-02a contract pin, 4 tests covering happy-path, both-set raises, neither-set raises, prompt-only backcompat).

## Decisions Made

- **Keyword-only separator (`*`) over positional-only:** every existing call site (FB-C tests, integration tests) already passes `tools=` by keyword. Locking everything past `prompt` to keyword-only is a binary-compatible tightening that prevents future positional-arg drift from masking signature changes.
- **Stub adapter update is in-scope:** the plan's verification claim that changes are "ONLY in router.py, _adapters.py, test_complete_with_tools.py" undercounts by one — the stub adapter has to evolve in lockstep with the production `_ToolAdapter` Protocol. Documenting this in the deviations section so plan 16-04's author knows the stub already accepts `messages=`.
- **Ollama adapter system-prompt handling on messages= path:** when caller supplies a messages list, the adapter prepends `system` only if the caller didn't already include one. This preserves Ollama's leading-system-message convention without overriding caller intent. Anthropic adapter has no equivalent issue (system is a separate top-level field, not a message).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated `_StubAdapter.init_state` in tests/llm/conftest.py to accept the new `messages=` kwarg**
- **Found during:** Task 1 GREEN (running existing tests after wiring `adapter.init_state(..., messages=messages)` in router.py)
- **Issue:** The coordinator now passes `messages=messages` unconditionally to `adapter.init_state()`. The plan's `<verification>` claims changes touch only router.py, _adapters.py, and test_complete_with_tools.py — but the test fixture `_StubAdapter` in `tests/llm/conftest.py` did not have `messages` in its signature, so every pre-existing `_StubAdapter`-based test (~23 tests) would have crashed with `TypeError: init_state() got an unexpected keyword argument 'messages'`.
- **Fix:** Added `messages: Optional[list[dict]] = None` to `_StubAdapter.init_state`, mirrored the production-adapter behaviour (verbatim use when provided, auto-wrap fallback when None), and surfaced `messages_kwarg` in state for test introspection. Added `from typing import Optional` to the conftest imports.
- **Files modified:** tests/llm/conftest.py
- **Verification:** All 27 tests in `test_complete_with_tools.py` pass (23 original + 2 RED scaffold + 4 contract pin); broader FB-C surface check `pytest tests/ -k "tool_call or complete_with_tools or adapter"` returns 56 passed, 2 skipped, 754 deselected.
- **Committed in:** 9a9a56b (Task 1 GREEN commit, alongside the production adapters)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary to keep existing tests passing. Stub-adapter scope is implicit in the `_ToolAdapter` Protocol contract — when the Protocol grows a kwarg, every implementor must follow. Plan 16-04's author should know the stub already accepts `messages=` so coordinator-stub tests for the chat handler can exercise the full D-02a surface without further fixture changes.

## Issues Encountered

None. The implementation matched the plan's <interfaces> sketch exactly. The pre-existing FB-C test conventions (`_StubAdapter` + `_FakeTool` + `_patch_adapters` + `_patch_clients` + `_make_terminal_turn`) were directly reusable.

## Tool Call Surface — What Plan 16-04 Sees

For the FB-D chat handler implementor:

```python
# Wire-shape messages list flows through verbatim — no stitching, no auto-wrap:
result = await llm_router.complete_with_tools(
    messages=[
        {"role": "user", "content": "what synthesis tools were created?"},
        {"role": "assistant", "content": "Let me check."},
        {"role": "tool", "content": "found 3 tools", "tool_call_id": "abc"},
    ],
    tools=tools,                   # required, keyword-only (D-22/D-23 still apply)
    sensitive=True,                # D-05: chat handler hardcodes True for v1.4
    max_iterations=body.max_iterations,   # caller-overridable per D-02
    max_seconds=120.0,             # FB-C inner cap; outer 125s is handler responsibility per D-14
    tool_result_max_bytes=8192,    # caller-overridable per D-02
)

# Mutual-exclusion errors map to HTTP 422 (validation_error) per D-17:
# ValueError("...mutually exclusive...") and ValueError("...must provide either...")
# both surface as Pydantic-style validation surfaces in the chat handler.
```

Roles accepted (per `OllamaToolAdapter.init_state` and `AnthropicToolAdapter.init_state`): `user | assistant | tool`. The Ollama adapter optionally prepends `system` only when the caller's first message isn't already a system message.

## Threat Surface Verification

The plan's `<threat_model>` listed three threat IDs. All three remain mitigated:

| Threat ID | Component | Mitigation Verified |
|-----------|-----------|---------------------|
| T-16-01-01 (T) | router.complete_with_tools messages= path | Mutual-exclusion guard is in place — `prompt and messages is not None` raises immediately. Test `test_complete_with_tools_prompt_and_messages_raises` pins this. |
| T-16-01-02 (I) | adapter.init_state messages forwarding | Caller content forwarded verbatim per D-15; no sanitization on the user-content path is by design. The existing `_sanitize_tool_result()` boundary on the tool-result path remains untouched. |
| T-16-01-03 (E) | recursive-loop guard interaction | `_in_tool_loop.get()` check fires BEFORE the new mutual-exclusion guard at router.py:335. Verified by ordering in the file (recursive-loop check at 335-339, D-02a guard at 341-352, D-23 empty-tools check at 354-358). |

## Next Phase Readiness

- Plan 16-02 (rate limiter) and 16-03 (chat models / Pydantic) can run in parallel — both are independent of this plan.
- Plan 16-04 (chat handler) is now unblocked. It can consume `complete_with_tools(messages=[...], tools=..., sensitive=True, ...)` directly.
- Plans 16-05 (Web UI), 16-06 (parity), 16-07 (UAT) all transitively benefit.

## Self-Check: PASSED

- `forge_bridge/llm/router.py` exists and contains `messages: Optional[list[dict]] = None` (1 occurrence) ✓
- `forge_bridge/llm/_adapters.py` exists and contains `messages: Optional[list[dict]]` (3 occurrences: Protocol + Anthropic + Ollama) ✓
- `tests/llm/test_complete_with_tools.py` contains `TestCompleteWithToolsMessagesKwarg` class with all 4 named tests ✓
- Commits `d41508e`, `9a9a56b`, `e2a4694` all present in `git log --oneline` ✓
- `pytest tests/llm/test_complete_with_tools.py -x -q` → 27 passed ✓
- `pytest tests/ -x -q -k "tool_call or complete_with_tools or adapter"` → 56 passed, 2 skipped ✓

---
*Phase: 16-fb-d-chat-endpoint*
*Plan: 01*
*Completed: 2026-04-27*
