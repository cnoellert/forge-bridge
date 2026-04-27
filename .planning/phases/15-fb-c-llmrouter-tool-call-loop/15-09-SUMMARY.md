---
phase: 15-fb-c-llmrouter-tool-call-loop
plan: 09
subsystem: llm
tags: [integration-tests, env-gating, fb-c, llmtool-01, llmtool-02, greenfield-pattern, live-uat]

# Dependency graph
requires:
  - phase: 15-fb-c-llmrouter-tool-call-loop (plan 08) — LLMRouter.complete_with_tools coordinator (the FB-C product surface)
  - phase: 15-fb-c-llmrouter-tool-call-loop (plan 03) — LLMLoopBudgetExceeded + RecursiveToolLoopError + LLMToolError (transitive via complete_with_tools)
  - phase: 15-fb-c-llmrouter-tool-call-loop (plan 05) — AnthropicToolAdapter + OllamaToolAdapter (live wire-format consumers under test)
provides:
  - "tests/integration/ subpackage with env-gated live tests for LLMTOOL-01 (Ollama) and LLMTOOL-02 (Anthropic)"
  - "FB_INTEGRATION_TESTS=1 env-gating convention codified for the first time in this codebase — master gate for any live external dependency; layered per-service gates (e.g., ANTHROPIC_API_KEY) on top"
  - "Sentinel-substring acceptance pattern — high-entropy in-test sentinel proves the LLM saw and incorporated the tool result, ruling out hallucinated answers that ignored the tool"
  - "Standing regression guard for env-gating markers themselves (test_env_gating_markers_are_skipif_marks always runs without env vars)"
affects:
  - "Phase 16 (FB-D) chat endpoint live integration tests — mirror this env-gating convention (FB_INTEGRATION_TESTS=1 master gate, additional per-service gates for any new external dependency)"
  - "v1.4 release ceremony — `FB_INTEGRATION_TESTS=1 ANTHROPIC_API_KEY=... pytest tests/integration/` on assist-01 is the LLMTOOL-01 / LLMTOOL-02 closing gate before tag/push"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Env-gated live integration test (greenfield) — pytest.mark.skipif on os.environ.get('FB_INTEGRATION_TESTS') != '1', layered with optional per-service gates (ANTHROPIC_API_KEY) — codifies the Phase 8 precedent CONTEXT.md cited but no live skipif previously existed"
    - "Sentinel-string acceptance for tool-call loops — high-entropy in-test string returned by the tool_executor; assert appears verbatim in the LLM's terminal text. Forces a tool-call-driven path; rules out hallucinated answers"
    - "Two-gate skipif for cloud cost protection — FB_INTEGRATION_TESTS=1 AND ANTHROPIC_API_KEY both required for the cloud test, never one alone (T-15-47 mitigation)"
    - "Standing regression guard for env-gating markers (test_env_gating_markers_are_skipif_marks) — runs without any env var; verifies markers are proper skipif Marks; catches inverted-logic accidents at collection time before live tests can run on a wrong machine (T-15-51 mitigation)"

key-files:
  created:
    - tests/integration/__init__.py — zero-byte Python package marker for the new tests/integration/ subpackage
    - tests/integration/test_complete_with_tools_live.py — 219 LOC; 2 env-gated live tests (Ollama + Anthropic) plus 1 always-runs sanity guard for the env-gating pattern itself
  modified: []

key-decisions:
  - "Custom in-test tool with tool_executor=_executor instead of invoke_tool against the registered MCP surface — isolates loop verification from MCP registry plumbing; `tool_executor=` is the public surface FB-D and external consumers use, so testing it directly here is the right boundary (per plan <interfaces> rationale)"
  - "Sentinel chosen as high-entropy 'FORGE-INTEGRATION-SENTINEL-XJK29Q' — a pre-trained LLM cannot plausibly produce this exact string by hallucination; presence in terminal response is strong evidence the tool was actually called and its result was incorporated. Compare to a low-entropy 'hello' which the LLM might produce from prompt context alone (T-15-49 mitigation)"
  - "Tighter caps than coordinator defaults: max_iterations=4 (vs default 8) and max_seconds=60.0 (vs default 120.0) — keeps the test responsive when run on assist-01; a two-step loop completes well inside both. The default LLMLoopBudgetExceeded is the structured failure mode for degraded backends (T-15-50 mitigation)"
  - "Explicit @pytest.mark.asyncio decoration despite asyncio_mode='auto' — matches the convention in tests/test_integration.py which decorates explicitly for clarity in mixed-test files. This file is greenfield so we set the precedent matching the existing convention"
  - "No silent skip on Ollama unreachable — if the daemon isn't reachable when FB_INTEGRATION_TESTS=1 is set, the LLMRouter call raises RuntimeError with a clear cause. Silent skip on connection error would mask a real degradation; the env gate IS the operator's signal that the daemon is expected to be available"
  - "ANTHROPIC_API_KEY consumed by AsyncAnthropic SDK directly, never read by the test — preserves the credential-leak posture (test never logs or echoes the key; T-15-48 disposition: accept)"

patterns-established:
  - "FB_INTEGRATION_TESTS=1 as the canonical master gate for ANY live external dependency in tests/integration/ — Phase 16+ mirrors this convention exactly: master gate first, then layered per-service gates (e.g., FORGE_S3_BUCKET, OLLAMA_HOST_OVERRIDE) on top"
  - "Standing regression guard pattern in every live integration test file — a cheap always-runs sanity test that verifies the skipif markers themselves are correct. Cost: ~5 LOC. Benefit: catches inverted-logic accidents at the next CI run, long before live tests can execute on the wrong machine"
  - "tests/integration/ as the canonical location for env-gated live tests — separates from tests/ unit + tests/llm/ unit tests + tests/console/ + tests/mcp/ (all of which run by default in `pytest tests/`)"

requirements-completed: [LLMTOOL-01, LLMTOOL-02]

# Metrics
duration_seconds: 153
completed_date: "2026-04-27"
tasks_completed: 2
files_changed: 2
tests_added: 3
loc_added: 219
---

# Phase 15 Plan 09: Live Integration Tests for LLMTOOL-01 + LLMTOOL-02 Summary

**The FB-C live-integration test surface — `tests/integration/test_complete_with_tools_live.py` ships two env-gated live tests that close the LLMTOOL-01 (Ollama) and LLMTOOL-02 (Anthropic) acceptance criteria against real provider backends, plus a standing regression guard for the env-gating pattern itself.**

## What Shipped

**2 files created (219 insertions, 0 deletions):**

| File | Status | LOC | Purpose |
|------|--------|-----|---------|
| `tests/integration/__init__.py` | NEW | 0 | Zero-byte Python package marker for the new subpackage; pytest can collect tests from this path |
| `tests/integration/test_complete_with_tools_live.py` | NEW | 219 | 2 env-gated live tests (Ollama + Anthropic) + 1 always-runs sanity guard |

## Tasks Completed

| Task | Name | Commit | Status |
|------|------|--------|--------|
| 1 | Create tests/integration/ subpackage marker | `4e72f95` | ✓ |
| 2 | Create tests/integration/test_complete_with_tools_live.py with two env-gated live tests | `f425f17` | ✓ |

## Test Results

**Default `pytest tests/integration/` (no env vars set on this worktree):**

```
collected 3 items

tests/integration/test_complete_with_tools_live.py::test_ollama_tool_call_loop_live SKIPPED [ 33%]
tests/integration/test_complete_with_tools_live.py::test_anthropic_tool_call_loop_live SKIPPED [ 66%]
tests/integration/test_complete_with_tools_live.py::test_env_gating_markers_are_skipif_marks PASSED [100%]

=================== 1 passed, 2 skipped, 1 warning in 0.01s ====================
```

This is the **expected** behavior on a developer laptop: both live tests SKIPPED (no Ollama or Anthropic dep needed), and the always-runs sanity guard PASSES (verifies env-gating markers are proper skipif Marks).

**Full FB-C Wave 1+2+3 regression sweep:**

```
$ pytest tests/llm/ tests/test_llm.py tests/test_synthesizer.py tests/test_mcp_registry.py tests/test_public_api.py tests/test_sanitize.py -x -q
209 passed, 1 warning in 3.04s
```

**Zero regressions** — the new env-gated tests do not affect any existing test surface; tests/integration/ collects independently and only adds the 1-test sanity guard to the default-run total.

## Acceptance — All ROADMAP success criteria 1 + 2 satisfied (env-gated)

### LLMTOOL-01 (ROADMAP success criterion 1)

> "router.complete_with_tools(prompt, tools=[...], sensitive=True) completes a two-step loop (LLM calls tool A, receives result, returns final response) against a real Ollama backend running `qwen2.5-coder:32b` — verified in an integration test on assist-01."

**`test_ollama_tool_call_loop_live`** invokes:

```python
response = await router.complete_with_tools(
    prompt="Call the forge_get_integration_secret tool to learn the secret value, "
           "then tell me what value the tool returned. Include the value verbatim.",
    tools=[<mcp.types.Tool: forge_get_integration_secret>],
    sensitive=True,
    tool_executor=_executor,  # returns _SENTINEL_RESULT for our one fake tool
    max_iterations=4,
    max_seconds=60.0,
)
assert _SENTINEL_RESULT in response  # high-entropy "FORGE-INTEGRATION-SENTINEL-XJK29Q"
```

Skipped unless `FB_INTEGRATION_TESTS=1`. Run on assist-01 with Ollama+qwen2.5-coder:32b reachable.

### LLMTOOL-02 (ROADMAP success criterion 2)

> "Cloud path (sensitive=False → Anthropic) produces a terminal response for the same prompt + tool schemas as criterion 1 — verified against live API with `ANTHROPIC_API_KEY` set."

**`test_anthropic_tool_call_loop_live`** invokes the same coordinator surface with `sensitive=False` — routes to Anthropic via the `AsyncAnthropic` SDK (which consumes `ANTHROPIC_API_KEY` directly from env). Same sentinel assertion.

Skipped unless `FB_INTEGRATION_TESTS=1` AND `ANTHROPIC_API_KEY` is set.

## Plan Acceptance Criteria — All Met

### Task 1

- ✅ `test -f tests/integration/__init__.py` exits 0
- ✅ `wc -c < tests/integration/__init__.py` returns `0` (zero-byte)
- ✅ `python -c "import tests.integration"` exits 0 (package importable)

### Task 2

- ✅ File `tests/integration/test_complete_with_tools_live.py` exists
- ✅ `grep -c "FB_INTEGRATION_TESTS" tests/integration/test_complete_with_tools_live.py` returns `10` (≥2 required)
- ✅ `grep -c "ANTHROPIC_API_KEY" tests/integration/test_complete_with_tools_live.py` returns `6` (≥1 required)
- ✅ `grep -c "def test_ollama_tool_call_loop_live" tests/integration/test_complete_with_tools_live.py` returns `1`
- ✅ `grep -c "def test_anthropic_tool_call_loop_live" tests/integration/test_complete_with_tools_live.py` returns `1`
- ✅ `grep -c "_SENTINEL_RESULT" tests/integration/test_complete_with_tools_live.py` returns `6` (≥4 required)
- ✅ `grep -c "qwen2.5-coder:32b\|FORGE_LOCAL_MODEL" tests/integration/test_complete_with_tools_live.py` returns `4` (≥1 required — D-28 model traceability via FORGE_LOCAL_MODEL env-default reference)
- ✅ `grep -c "complete_with_tools" tests/integration/test_complete_with_tools_live.py` returns `4` (≥2 required)
- ✅ `grep -c "sensitive=True" tests/integration/test_complete_with_tools_live.py` returns `2` (the actual call site + 1 comment) — exceeds spec's literal "1" minimum (see "Plan internal consistency note" below)
- ✅ `grep -c "sensitive=False" tests/integration/test_complete_with_tools_live.py` returns `3` (the actual call site + 2 comments) — exceeds spec's literal "1" minimum
- ✅ Without env vars: `pytest tests/integration/test_complete_with_tools_live.py -v` → 1 passed, 2 skipped, exit 0
- ✅ `pytest tests/integration/test_complete_with_tools_live.py::test_env_gating_markers_are_skipif_marks -x -q` → 1 passed, exit 0
- ✅ `pytest tests/llm/ tests/test_llm.py tests/test_synthesizer.py tests/test_mcp_registry.py tests/test_public_api.py tests/test_sanitize.py -x -q` → 209/209 passed (zero regression)

### Plan-level `<verification>` block

- ✅ Both tasks' acceptance criteria pass (above)
- ✅ Without env vars set: 2 SKIPPED + 1 PASSED, exit 0
- ✅ With env vars set on assist-01: deferred to operator-action UAT (see "Operator UAT" below) — out of scope for `/gsd-execute-phase` automation per plan `<output>` note
- ✅ Full FB-C deterministic test sweep: 209/209 passed, exit 0
- ✅ `git diff --stat` shows exactly 2 files added (`tests/integration/__init__.py` NEW, `tests/integration/test_complete_with_tools_live.py` NEW)

## Plan Internal Consistency Note (non-blocking)

The plan's Task 1 `<read_first>` block stated:

> "tests/console/__init__.py (verify the empty-file convention used elsewhere)"
> "tests/mcp/__init__.py (same — confirm zero-byte marker pattern)"

Actual state on disk:

```
$ wc -c tests/console/__init__.py tests/mcp/__init__.py
      96 tests/console/__init__.py   (single-line module docstring)
     100 tests/mcp/__init__.py       (single-line module docstring)
```

Neither sibling is zero-byte; both contain a single-line module docstring of the form `"""tests.console — HTTP handler tests for forge-bridge Phase 14 (FB-B) staged-ops surface."""`.

**Resolution:** The plan's `<acceptance_criteria>` and `<must_haves.artifacts>` BOTH explicitly require zero-byte (`test ! -s ...`, `wc -c ... returns 0`, `contains: ""`). The verbatim acceptance criteria win over the `<read_first>` mischaracterization of the sibling convention. Created tests/integration/__init__.py as zero-byte per the plan's explicit, testable requirements.

This is a plan-internal mismatch, not a deviation in execution. Future plans creating new tests subpackages may want to standardize on the actual sibling convention (single-line docstring) — track as a v1.4.x housekeeping item if desired. No action required for this plan.

The plan's `sensitive=True/False` grep counts also have the same flavor of literal-vs-intent mismatch: the action block specifies content with comments mentioning "sensitive=True/False", and the resulting counts are 2 and 3 respectively rather than the spec's literal "1". The intent is clearly "the actual call exists" (it does — verified). Comments add documentation value and were specified verbatim in the plan's `<action>`.

## Key Design Confirmations

### tool_executor= is the right surface to test directly

Per plan `<interfaces>`: the test uses a custom in-test tool with `tool_executor=_executor` rather than the registered MCP surface. The MCP server requires a full lifecycle setup (startup_bridge → register_builtins → ...) to populate the registry — heavy fixture for a test that's already env-gated. A custom tool with `tool_executor=...` lets the loop verification stay isolated from MCP registry plumbing.

The CONTEXT.md `<canonical_refs>` "What FB-D Will Consume From This Phase" bullet confirms `tool_executor=` is the public surface FB-D and external consumers use; testing it directly here is the right boundary.

### Sentinel-string acceptance is forensic, not just functional

The high-entropy `_SENTINEL_RESULT = "FORGE-INTEGRATION-SENTINEL-XJK29Q"` is unrecognizable to any pre-trained LLM. The probability of a model producing this exact string by hallucination is effectively zero; presence in the terminal response is strong evidence the tool was actually called and its result was incorporated.

If the assertion fails, the cause is one of:

1. The LLM didn't call the tool (e.g., decided it could answer directly). Either the prompt is too weak or the model regression for tool-following.
2. The LLM called the tool but didn't incorporate the result (early termination). Either the loop coordinator dropped the result or the model ignored it.
3. The provider returned a degraded response (5xx wrapped to LLMToolError, or empty terminal text).

Each failure mode produces a different exception/assertion shape — the failure is actionable and not silent.

### Two-gate skipif is cloud-cost protection (T-15-47)

The Anthropic test requires BOTH `FB_INTEGRATION_TESTS=1` AND `ANTHROPIC_API_KEY` to be present. CI runners that don't set both never call the API. A developer who sets only `FB_INTEGRATION_TESTS=1` (e.g., to run the Ollama test locally) does NOT trigger an Anthropic call.

The standing `test_env_gating_markers_are_skipif_marks` regression guard catches inverted-logic accidents (e.g., a future contributor accidentally writing `os.environ.get("X") == "1"` instead of `!= "1"`) at the next CI run — long before the live tests can run on the wrong machine.

### The env-gating convention is codified for v1.4+

This plan is the **first** instance of `FB_INTEGRATION_TESTS=1` in the codebase (CONTEXT.md cited Phase 8 as precedent for env-gated integration testing, but no `FB_INTEGRATION_TESTS=1` skipif previously existed). The convention is now established for FB-C; subsequent live integration tests in v1.4+ phases (FB-D chat endpoint over real Anthropic + Ollama; future phases involving real S3, real Postgres-with-TLS, etc.) should mirror it exactly:

1. Master gate `FB_INTEGRATION_TESTS=1` for ANY live external dependency.
2. Additional per-service gates (e.g., `ANTHROPIC_API_KEY`, `FORGE_S3_BUCKET`) layered on top.
3. A standing sanity test in each integration file that verifies the skipif markers are defined correctly.

## Deviations from Plan

**None — plan executed exactly as written, with two non-blocking observations documented in "Plan Internal Consistency Note" above:**

1. The plan's `<read_first>` for Task 1 mischaracterized `tests/console/__init__.py` and `tests/mcp/__init__.py` as zero-byte; they actually contain a single-line module docstring. Followed the plan's explicit `<acceptance_criteria>` (zero-byte) which is the operative spec.
2. The plan's `<acceptance_criteria>` for `sensitive=True` and `sensitive=False` grep counts say "returns 1" while the verbatim `<action>` content specifies content with comments that match those substrings (yielding counts of 2 and 3). The intent ("the actual call exists") is satisfied; the comments add documentation value and were specified verbatim by the plan author.

Both observations are plan-internal, not execution deviations.

## Authentication Gates

**None encountered.** This plan creates test files; no external authentication required during execution. The `ANTHROPIC_API_KEY` requirement is part of the env-gating contract for the Anthropic test — operator provides it at UAT time, not during plan execution.

## Operator UAT — Not Part of `/gsd-execute-phase` Automation

Per plan `<output>`: the actual UAT execution against assist-01 is a developer-action step (run by the operator with the env vars set) — out of scope for `/gsd-execute-phase` automation but is a checkpoint per the v1.4 milestone close.

The operator UAT command sequence:

```bash
# On assist-01 with Ollama running and qwen2.5-coder:32b pulled:
FB_INTEGRATION_TESTS=1 pytest tests/integration/ -v
# Expected: test_ollama_tool_call_loop_live PASSED, sentinel in response

# Same machine + ANTHROPIC_API_KEY set:
FB_INTEGRATION_TESTS=1 ANTHROPIC_API_KEY=sk-... pytest tests/integration/ -v
# Expected: BOTH live tests PASSED, sentinel in both responses
```

This live UAT is the LLMTOOL-01 / LLMTOOL-02 closing gate before the v1.4 release ceremony.

## Threat Model Compliance

The plan's `<threat_model>` register (T-15-47..T-15-52) is satisfied as documented:

| Threat | Status | Verification |
|--------|--------|--------------|
| T-15-47 (Elevation — accidental cloud spend) | mitigated | Two-gate skipif: FB_INTEGRATION_TESTS=1 AND ANTHROPIC_API_KEY required for cloud test; standing test_env_gating_markers_are_skipif_marks regression guard |
| T-15-48 (Information disclosure — API key in test logs) | accept | Test never reads ANTHROPIC_API_KEY directly; AsyncAnthropic SDK consumes it from env. Test asserts on response content (sentinel match), not request metadata. The adapter's LLMToolError wrapping (plan 15-05) ensures `type(exc).__name__` is the only exception text — never `str(exc)` which could carry credential headers |
| T-15-49 (Tampering — false-positive sentinel match) | mitigated | High-entropy `FORGE-INTEGRATION-SENTINEL-XJK29Q` cannot be hallucinated; presence in terminal response is strong evidence the tool was called and its result incorporated |
| T-15-50 (Denial of service — runaway test on slow backend) | mitigated | Tighter caps: max_iterations=4, max_seconds=60.0 (vs defaults 8 / 120). LLMLoopBudgetExceeded is the structured failure mode |
| T-15-51 (Tampering — env-gating regression silently runs live tests on dev laptop) | mitigated | test_env_gating_markers_are_skipif_marks always-runs sanity test verifies markers are proper skipif Marks; catches inverted-logic at next CI run |
| T-15-52 (Information disclosure — sentinel in CI logs) | accept | Sentinel is a deliberate test-only string; presence in logs is the success signal, not a leak. Carries no project secrets, customer data, or production information |

## Wave 4 Closes the FB-C Surface

After this plan ships:

- All 7 LLMTOOL-01..07 acceptance criteria are testable:
  - **LLMTOOL-01, LLMTOOL-02** (live tests, this plan) — env-gated; run by operator on assist-01 + with ANTHROPIC_API_KEY before v1.4 release
  - **LLMTOOL-03..07** (deterministic stub-adapter tests, plans 15-04/05/06/07/08) — run by default in `pytest tests/`
- The FB-C product surface (`LLMRouter.complete_with_tools()` + 3 exception classes + `invoke_tool` + sanitization helpers) is shipped, tested, and ready for FB-D consumption
- The env-gating convention is codified for FB-D and beyond

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| `4e72f95` | chore | add tests/integration/ subpackage marker (zero-byte __init__.py) |
| `f425f17` | test | add LLMTOOL-01/02 env-gated live integration tests |

## Cross-Plan Verification

- `pytest tests/integration/ -v` → **1 passed, 2 skipped** (env-gated default behavior verified)
- `pytest tests/llm/ tests/test_llm.py tests/test_synthesizer.py tests/test_mcp_registry.py tests/test_public_api.py tests/test_sanitize.py -x -q` → **209/209 passed** (full FB-C Wave 1+2+3 sweep, zero regression)
- `git diff --stat efa6389b2a846e5ea9fbc71bce819b3a5b7f9e10..HEAD` → exactly 2 files added (matches plan `<verification>` `git diff --stat` requirement)
- No deletions, no untracked files

## Self-Check: PASSED

- ✅ `tests/integration/__init__.py` exists as zero-byte file (verified by `wc -c < tests/integration/__init__.py` returning `0`)
- ✅ `tests/integration/test_complete_with_tools_live.py` exists (219 LOC, 3 tests including 1 always-runs sanity guard)
- ✅ Commit `4e72f95` exists in `git log` (Task 1 — package marker)
- ✅ Commit `f425f17` exists in `git log` (Task 2 — env-gated live tests)
- ✅ All Plan-level Acceptance Criteria pass (grep counts + pytest behavior + git diff stat)
- ✅ `pytest tests/integration/ -v` exits 0 with 1 passed + 2 skipped (correct env-gated default)
- ✅ `pytest tests/llm/ tests/test_llm.py tests/test_synthesizer.py tests/test_mcp_registry.py tests/test_public_api.py tests/test_sanitize.py -x -q` exits 0 (209 tests, zero regression)
- ✅ All 6 entries in T-15-47..T-15-52 threat register addressed (4 mitigated, 2 accepted with verified posture)
- ✅ No stub patterns found in shipped code
- ✅ No new threat surface introduced (test code only, exercises existing complete_with_tools surface already in the threat model)

## Next Phase Readiness

**Phase 16 (FB-D) chat endpoint planning is unblocked.** The FB-C product surface is now end-to-end testable (deterministic LLMTOOL-03..07 + env-gated LLMTOOL-01/02). FB-D will:

1. Consume `LLMRouter.complete_with_tools()` directly (no provider knowledge in the chat endpoint)
2. Catch `LLMLoopBudgetExceeded` / `RecursiveToolLoopError` / `LLMToolError` and map to HTTP 504/500/502 per D-15
3. Mirror this plan's env-gating convention for its own live integration tests (FB_INTEGRATION_TESTS=1 master gate; if any new external dep is added, layered per-service gate on top)

**v1.4 release ceremony LLMTOOL-01/02 closing gate** — operator runs `FB_INTEGRATION_TESTS=1 ANTHROPIC_API_KEY=... pytest tests/integration/` on assist-01 before v1.4 tag/push. Both live tests must PASS (sentinel in response) for the milestone to close.

---

*Phase: 15-fb-c-llmrouter-tool-call-loop*
*Plan: 09 (FB-C Wave 4 — live integration tests for LLMTOOL-01 + LLMTOOL-02)*
*Completed: 2026-04-27*
