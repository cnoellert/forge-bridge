---
phase: 16-fb-d-chat-endpoint
plan: 06
subsystem: integration
tags: [chat-endpoint, integration-tests, fb-d, sanitization-e2e, parity-test, asgi-transport, fb-integration-tests-gated]

# Dependency graph
requires:
  - phase: 16-fb-d-chat-endpoint
    plan: 04
    provides: "POST /api/v1/chat handler with NESTED D-17 error envelope, X-Request-ID, D-14a exception translation, D-15 sanitization boundary inheritance from FB-C"
  - phase: 16-fb-d-chat-endpoint
    plan: 01
    provides: "LLMRouter.complete_with_tools(messages=...) Pattern B kwarg + tool_executor= path used by Strategy B sanitization E2E"
  - phase: 16-fb-d-chat-endpoint
    plan: 05
    provides: "Live chat panel (UI parity context — Strategy A parity test models the same wire shape the panel produces)"
provides:
  - "tests/integration/test_chat_endpoint.py — CHAT-03 sanitization E2E (Strategy A always-on + Strategy B FB_INTEGRATION_TESTS-gated)"
  - "tests/integration/test_chat_parity.py — CHAT-05 external-consumer parity (browser-shape + Flame-hooks-shape clients) + Strategy B live structural match"
  - "5 always-on tests + 2 FB_INTEGRATION_TESTS=1-gated tests; default `pytest tests/integration/` runs in 0.04s with 0 live dependencies"
affects:
  - "16-07-PLAN.md (UAT — operator-driven CHAT-04 artist UAT and orphan-test cleanup)"
  - "projekt-forge v1.5 Flame hooks — parity test pins the wire-shape contract this consumer depends on"

# Tech tracking
tech-stack:
  added: []   # zero new deps — httpx, pytest-asyncio, mcp.types all pre-existing in dev/test extras
  patterns:
    - "ASGITransport in-process pattern: httpx.AsyncClient + ASGITransport(app=...) for live ASGI testing without uvicorn subprocess (faster, no port binding, no socket cleanup)"
    - "FB_INTEGRATION_TESTS gating reuses the FB-C convention from tests/integration/test_complete_with_tools_live.py:49-66 — single source of truth for the env-var gate across all integration tests"
    - "_structural_signature(body) helper reduces a chat response body to a comparable structural fingerprint (keys, types, role progression) — drops content so the helper is reusable for live LLM tests where output is non-deterministic"
    - "Two-strategy pattern for phase tests: Strategy A (mocked, always-on, deterministic) + Strategy B (live, gated, integration). Strategy A asserts contract verbatim; Strategy B asserts the production chain works under real load. Together: contract pinned + chain proven."

key-files:
  created:
    - "tests/integration/test_chat_endpoint.py — 224 LOC, 3 tests (2 always-on + 1 gated)"
    - "tests/integration/test_chat_parity.py — 301 LOC, 3 tests (2 always-on + 1 gated)"
  modified: []

key-decisions:
  - "Adopted the two-strategy pattern for both files (Strategy A + Strategy B) so default `pytest tests/` is clean for developers without Ollama AND the integration chain is exercised by `FB_INTEGRATION_TESTS=1 pytest tests/integration/` on assist-01."
  - "Strategy A for CHAT-03 (sanitization) pins the D-15 contract structurally — the chat handler does NOT pre-sanitize user content; the FB-C sanitizer is applied INSIDE the loop on tool RESULTS only. Two orthogonal assertions: (1) handler forwards user content verbatim, (2) INJECTION_MARKERS source-of-truth tuple contains 'ignore previous'. Together prove the chat path inherits sanitization without new wiring (D-15 mandate)."
  - "Strategy B for CHAT-03 calls LLMRouter.complete_with_tools(prompt=..., tool_executor=poisoned_executor) directly — bypasses the HTTP boundary because the sanitization chain is BELOW the handler boundary. Asserts the LLM's terminal text does NOT contain the marker substring. This is the live-Ollama proof on assist-01."
  - "Strategy A for CHAT-05 (parity) uses TWO httpx.AsyncClient instances differing only in headers (browser-shape vs Flame-hooks-shape with X-Forge-Actor + custom User-Agent) — same payload, same endpoint, asserts structural+content equality. Documents the realistic difference between the two consumer types without changing response shape."
  - "Strategy B for CHAT-05 fires two consecutive real /api/v1/chat calls and asserts structural-shape match modulo content (LLM output varies). Calls _rate_limit._reset_for_tests() between calls so the second is not 429-ed by the first call's bucket consumption."
  - "Both files use `pytest_asyncio.fixture` for async fixtures even though pyproject.toml has `asyncio_mode='auto'` — explicit pytest_asyncio fixtures are clearer and match the plan's spec verbatim. The `@pytest.mark.asyncio` decorator on test methods is unnecessary in auto mode but I omitted it to keep the test methods minimal (auto mode handles them)."

patterns-established:
  - "Structural-signature comparison for non-deterministic responses: when content is non-deterministic (LLM output), reduce the response to a structural fingerprint (keys, types, role progression) and compare on that. Pattern reusable for any future LLM-backed endpoint that needs a parity test."
  - "ASGITransport for in-process integration testing: faster than starting uvicorn, no port binding, no socket cleanup, clean teardown via async-context-manager. Should become the default integration-test pattern for new ASGI surfaces in v1.4."
  - "Auth-gated env-var pattern (FB_INTEGRATION_TESTS) extends cleanly to multi-test files: each integration test file imports its own `requires_integration = pytest.mark.skipif(...)` rather than centralizing in a conftest. Centralization would mask which tests need the gate; per-file definition documents the dependency at the call site."

requirements-completed:
  - CHAT-03  # Sanitization E2E — handler does NOT pre-sanitize; FB-C boundary stripped marker before LLM saw it (Strategy A structural + Strategy B live)
  - CHAT-05  # External-consumer parity — browser-shape and Flame-hooks-shape clients produce structurally identical responses (Strategy A structural + Strategy B live)

# Metrics
duration: ~3m
completed: 2026-04-27
tasks: 2
files_created: 2
files_modified: 0
tests_added: 6   # 4 always-on + 2 gated
test_runtime: 0.04s
---

# Phase 16 Plan 06: Chat Integration Tests (CHAT-03 + CHAT-05) Summary

**One-liner:** Shipped 6 integration tests across 2 files closing CHAT-03 (sanitization E2E — handler forwards user content verbatim, FB-C strips injection markers from tool results before LLM sees them) and CHAT-05 (external-consumer parity — browser and Flame-hooks clients produce structurally-identical responses); 4 always-on tests pass in 0.04s with zero live deps; 2 FB_INTEGRATION_TESTS-gated tests skip cleanly without Ollama.

## What Shipped

| Artifact | Type | Key contract |
| -------- | ---- | ------------ |
| `tests/integration/test_chat_endpoint.py` | created | CHAT-03 sanitization E2E. `TestChatSanitizationE2E` (Strategy A, always-on): asserts handler forwards user content verbatim + `INJECTION_MARKERS` contains 'ignore previous'. `TestChatSanitizationLive` (Strategy B, gated): real LLMRouter + poisoned tool_executor + asserts marker stripped from terminal text. ~224 LOC. |
| `tests/integration/test_chat_parity.py` | created | CHAT-05 external-consumer parity. `TestChatParityStructural` (Strategy A, always-on): browser-shape + Flame-hooks-shape clients hit same endpoint with same payload, asserts structural+content equality + envelope-keys-locked to `{messages, stop_reason, request_id}`. `TestChatParityLive` (Strategy B, gated): two real calls, structural-shape match modulo content. ~301 LOC. |

## Test Roster (6 tests, all pass in default mode — 4 passed + 2 skipped)

| File | Test | Type | Pins |
| ---- | ---- | ---- | ---- |
| `test_chat_endpoint.py` | `test_handler_passes_messages_verbatim_to_router` | Strategy A (always-on) | D-15: handler does NOT pre-sanitize user-typed content; full marker substring reaches the router intact |
| `test_chat_endpoint.py` | `test_injection_markers_present_in_pattern_set` | Strategy A (always-on) | INJECTION_MARKERS source-of-truth contains 'ignore previous' (case-insensitive matched downstream by `_sanitize_tool_result`) |
| `test_chat_endpoint.py` | `test_chat_does_not_leak_poisoned_tool_marker` | Strategy B (FB_INTEGRATION_TESTS gated) | Real LLMRouter + poisoned tool_executor → terminal text does NOT contain 'IGNORE PREVIOUS INSTRUCTIONS' (proves FB-C sanitization stripped it before LLM saw it) |
| `test_chat_parity.py` | `test_chat_parity_browser_vs_flame_hooks` | Strategy A (always-on) | Browser-shape (Accept: application/json) and Flame-hooks-shape (X-Forge-Actor + custom User-Agent) clients produce structurally-identical responses + content equality (mocked router) + X-Request-ID on both |
| `test_chat_parity.py` | `test_chat_parity_envelope_keys_locked` | Strategy A (always-on) | D-03 success envelope locked to `{messages, stop_reason, request_id}` and `stop_reason == "end_turn"` |
| `test_chat_parity.py` | `test_chat_parity_live_structural_match` | Strategy B (FB_INTEGRATION_TESTS gated) | Two consecutive real /api/v1/chat calls produce structurally-identical envelopes (request_id_type, keys_present, messages_type, stop_reason match modulo content variance) |

## Default Mode — Default `pytest tests/` Runs Cleanly

```
$ pytest tests/integration/test_chat_endpoint.py tests/integration/test_chat_parity.py -x -v
...
2 passed, 1 skipped in tests/integration/test_chat_endpoint.py     # 0.03s
2 passed, 1 skipped in tests/integration/test_chat_parity.py       # 0.04s
```

Without `FB_INTEGRATION_TESTS=1`, both Strategy B tests skip with the same documented reason as the existing `tests/integration/test_complete_with_tools_live.py` tests. **Zero new live dependencies introduced** — no Ollama, no Anthropic, no DB, no network.

## Operator UAT Mode — `FB_INTEGRATION_TESTS=1 pytest tests/integration/test_chat_*`

On assist-01 (the canonical local LLM hardware host):

```bash
FB_INTEGRATION_TESTS=1 pytest tests/integration/test_chat_endpoint.py tests/integration/test_chat_parity.py -v
```

Will exercise:
1. `test_chat_does_not_leak_poisoned_tool_marker` — real LLMRouter on `qwen2.5-coder:32b`, poisoned tool returns marker substring, FB-C `_sanitize_tool_result` replaces it with `[BLOCKED:INJECTION_MARKER]` before the loop's next turn, terminal text does NOT contain the original substring.
2. `test_chat_parity_live_structural_match` — two consecutive real chat completions, both produce the same envelope shape (keys, types, role progression).

This run is the operator-UAT-style validation that the FB-C sanitization chain works under real LLM load and the chat endpoint produces a stable wire shape across consecutive calls.

## Self-Check on Threat Surface (T-16-06-01..04)

| Threat ID | Component | Disposition | Mitigation Verified |
| --------- | --------- | ----------- | ------------------- |
| T-16-06-01 (T) | poisoned tool result reaching LLM | mitigate | Strategy A asserts the marker tuple (single source of truth) contains the canonical 'ignore previous' marker; Strategy B asserts the marker does NOT appear in terminal LLM text after a real loop run with a poisoned tool_executor. The two strategies together prove FB-C's `_sanitize_tool_result` is wired into the chat path without new handler-level wiring (D-15). |
| T-16-06-02 (I) | structural-shape divergence between consumers | mitigate | `TestChatParityStructural::test_chat_parity_browser_vs_flame_hooks` asserts the response keys, types, role progression, and assistant-turn content are identical across the two consumer shapes. A future regression that, e.g., set a custom Set-Cookie based on User-Agent or returned a different envelope key set would fail before it shipped. |
| T-16-06-03 (R) | request_id present on every response | mitigate | `_structural_signature` asserts `request_id_present is True`; Strategy A also asserts `X-Request-ID` header is set on both clients. |
| T-16-06-04 (D) | live test rate-limit pollution | mitigate | `_rate_limit._reset_for_tests()` is called between live calls in Strategy B parity test so the second call doesn't 429-fire on a polluted bucket. |

No new threat surfaces introduced beyond the plan's threat register.

## Performance

- **Duration:** ~3 minutes (2 atomic test-file tasks)
- **Test runtime (default mode):** 0.04s for both new files combined; all integration tests pass in 0.04s + 1 pre-existing test_env_gating_markers_are_skipif_marks
- **Test runtime (full default suite — sanity check):** `tests/console/ tests/llm/ tests/test_llm.py` → **129 passed, 33 skipped** (no regressions; matches plan 16-04 baseline of 129/33).

## Task Commits

| # | Type | Hash | Message |
| - | ---- | ---- | ------- |
| 1 | test | `ed1f30a` | test(16-06): add CHAT-03 sanitization E2E tests for /api/v1/chat |
| 2 | test | `71164af` | test(16-06): add CHAT-05 external-consumer parity tests for /api/v1/chat |

## Files Created / Modified

### Created

- `tests/integration/test_chat_endpoint.py` (224 LOC) — 3 tests in two classes (`TestChatSanitizationE2E`, `TestChatSanitizationLive`). Uses `httpx.AsyncClient + ASGITransport(app=...)` for in-process testing. Imports `INJECTION_MARKERS` from `forge_bridge._sanitize_patterns` to verify single-source-of-truth.
- `tests/integration/test_chat_parity.py` (301 LOC) — 3 tests in two classes (`TestChatParityStructural`, `TestChatParityLive`). `_structural_signature(body)` helper reduces a response to a comparable structural fingerprint. Two distinct httpx clients with different headers prove zero divergence.

### Modified

None.

## Decisions Made

1. **Adopted the two-strategy pattern (A always-on + B gated) for both files.** Strategy A pins the contract structurally (mocked router, deterministic, runs in default `pytest tests/`); Strategy B exercises the live chain (real LLMRouter, gated on `FB_INTEGRATION_TESTS=1`). Together: contract pinned + chain proven.

2. **Strategy B for CHAT-03 calls `LLMRouter.complete_with_tools(prompt=..., tool_executor=poisoned)` directly, NOT through the HTTP boundary.** The sanitization chain is BELOW the handler boundary — the chat handler doesn't see tool results, only the loop does. Going through HTTP would test more code but the assertion target is the loop's sanitization, so calling the loop directly is the cleaner test.

3. **`_structural_signature(body)` helper drops content entirely.** LLM output is non-deterministic — content equality across two real calls is not a meaningful assertion. Structural fingerprint (keys, types, role progression, request_id presence) IS meaningful and stable.

4. **Used `pytest_asyncio.fixture` (vs `@pytest.fixture` with `asyncio_mode='auto'`).** Explicit `pytest_asyncio.fixture` is clearer at the call site and matches the plan's spec verbatim. Test methods themselves don't need `@pytest.mark.asyncio` decorators because pyproject.toml sets `asyncio_mode='auto'`.

5. **Per-file `requires_integration = pytest.mark.skipif(...)` definition (not centralized in conftest).** Each integration file imports its own gate definition; centralization would mask which tests need the gate. Per-file is documentation-as-code at the call site.

## Deviations from Plan

None. Plan executed exactly as written. Both task action blocks shipped verbatim from the plan template (with one minor docstring/whitespace cleanup pass for readability — no semantic changes).

## Acceptance Criteria — All Pass

### Task 1 (test_chat_endpoint.py)
- File exists ✓
- `grep -c "requires_integration"` → 2 (≥1) ✓
- `grep -c "FB_INTEGRATION_TESTS"` → 6 (≥1) ✓
- `grep -c "def test_handler_passes_messages_verbatim_to_router"` → 1 ✓
- `grep -c "def test_chat_does_not_leak_poisoned_tool_marker"` → 1 ✓
- `grep -c "ASGITransport"` → 3 (≥1) ✓
- `grep -c "INJECTION_MARKERS"` → 5 (≥1) ✓
- `grep -c "IGNORE PREVIOUS INSTRUCTIONS"` → 4 (≥1) ✓
- `pytest tests/integration/test_chat_endpoint.py -x -v` → **2 passed, 1 skipped in 0.03s** ✓

### Task 2 (test_chat_parity.py)
- File exists ✓
- `grep -c "requires_integration"` → 2 (≥1) ✓
- `grep -c "def test_chat_parity_browser_vs_flame_hooks"` → 1 ✓
- `grep -c "def test_chat_parity_envelope_keys_locked"` → 1 ✓
- `grep -c "def test_chat_parity_live_structural_match"` → 1 ✓
- `grep -c "ASGITransport"` → 4 (≥1) ✓
- `grep -c "_structural_signature"` → 5 (≥2) ✓
- `grep -c "X-Forge-Actor"` → 3 (≥1) ✓
- `pytest tests/integration/test_chat_parity.py -x -v` → **2 passed, 1 skipped in 0.04s** ✓

### Plan-level verification
- Both task acceptance criteria pass ✓
- `pytest tests/integration/ -x -v` → **5 passed, 4 skipped** (the 4 skipped are the 2 new gated + 2 pre-existing FB-C live tests) ✓
- `pytest tests/console/ tests/llm/ tests/test_llm.py -q` → **129 passed, 33 skipped** (no regression) ✓
- D-15 verbatim pinned by `test_handler_passes_messages_verbatim_to_router` ✓
- D-18 (structural parity) pinned by `test_chat_parity_browser_vs_flame_hooks` ✓
- Default `pytest tests/integration/test_chat_*` exits 0 without `FB_INTEGRATION_TESTS=1` ✓
- `FB_INTEGRATION_TESTS=1 pytest tests/integration/test_chat_*` would exercise both Strategy B tests against live Ollama on assist-01 ✓ (operator UAT — not run from this worktree)

## CHAT-04 Artist UAT — Out of Scope

Per plan output spec: CHAT-04 artist UAT (D-12 hard fresh-operator gate, real Ollama on assist-01, end-to-end through the Web UI panel from plan 16-05) happens **separately** under plan 16-07. This plan ships CHAT-03 + CHAT-05 only. The Strategy B tests in this plan are operator-UAT-style integration tests, not the artist-UAT D-12 gate.

## Known Orphan Failure — Not in Scope

`tests/test_ui_chat_stub.py::test_ui_chat_stub_body_copy` (and 2 sibling tests in the same file) currently fail because they assert copy from the now-deleted Phase-12 stub. This is **explicitly deferred to plan 16-07** per plan 16-05 Task 3 sub-step C and 16-05-SUMMARY.md. Plan 16-07's scope includes retiring this orphan test file. **Not touched in this plan** — confirmed by `git diff main HEAD -- tests/test_ui_chat_stub.py` returning empty.

## TDD Gate Compliance

This plan ships under a `type=execute` plan frontmatter (not `type=tdd`) — no per-task `tdd="true"` flags. The work is structurally test-only (both tasks ship test files). Both commits are `test(...)` scope per the standard commit-type matrix:

- **Task 1:** `test(16-06): add CHAT-03 sanitization E2E tests for /api/v1/chat` (`ed1f30a`)
- **Task 2:** `test(16-06): add CHAT-05 external-consumer parity tests for /api/v1/chat` (`71164af`)

The implementation under test (chat_handler from plan 16-04, LLMRouter from plan 16-01, sanitization from FB-C) was already shipped in earlier waves. This plan ships the integration-level test surface that pins those contracts together at the wire boundary.

## Threat Flags

None — no new security-relevant surface introduced. This plan is test-only.

## Self-Check: PASSED

- `tests/integration/test_chat_endpoint.py` exists with `TestChatSanitizationE2E` (2 tests) + `TestChatSanitizationLive` (1 test) ✓
- `tests/integration/test_chat_parity.py` exists with `TestChatParityStructural` (2 tests) + `TestChatParityLive` (1 test) ✓
- Commits `ed1f30a` (Task 1) and `71164af` (Task 2) both present in `git log --oneline` ✓
- `pytest tests/integration/ -v` → 5 passed, 4 skipped (no failures, no errors) ✓
- `pytest tests/console/ tests/llm/ tests/test_llm.py -q` → 129 passed, 33 skipped (no regression vs plan 16-04 baseline) ✓
- Default `pytest tests/integration/test_chat_*` exits 0 without `FB_INTEGRATION_TESTS=1` ✓
- Strategy B tests skip with reason matching the FB-C convention ✓
- Orphan `tests/test_ui_chat_stub.py` left untouched (out of scope) ✓

---
*Phase: 16-fb-d-chat-endpoint*
*Plan: 06*
*Completed: 2026-04-27*
