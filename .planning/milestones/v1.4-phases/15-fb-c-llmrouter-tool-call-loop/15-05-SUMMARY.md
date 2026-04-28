---
phase: 15-fb-c-llmrouter-tool-call-loop
plan: 05
subsystem: llm
tags: [anthropic, ollama, tool-call, adapter, protocol, fb-c, llmtool-01, llmtool-02, llmtool-03]

# Dependency graph
requires:
  - phase: 15-fb-c-llmrouter-tool-call-loop (plan 03)
    provides: LLMToolError + RecursiveToolLoopError + LLMLoopBudgetExceeded exceptions on forge_bridge.llm.router
  - phase: 15-fb-c-llmrouter-tool-call-loop (plan 04)
    provides: _sanitize_tool_result + shared _sanitize_patterns module (independent — Wave 2 sibling)
provides:
  - _ToolAdapter Protocol contract (research §4.4)
  - AnthropicToolAdapter — native anthropic.AsyncAnthropic wire-format translator (LLMTOOL-02)
  - OllamaToolAdapter — native ollama.AsyncClient wire-format translator (LLMTOOL-01)
  - _TurnResponse / _ToolCall (mutable) + ToolCallResult (frozen) canonical dataclasses
  - _OLLAMA_TOOL_MODELS frozenset + _OLLAMA_KEEP_ALIVE='10m' constants (D-29, D-33)
  - _StubAdapter (D-37) + mock_ollama + 4 helper fixtures in tests/llm/conftest.py
affects: [15-fb-c-llmrouter-tool-call-loop plan 08 (coordinator consumes both adapters), 15-fb-c plan 09 (live integration), 16-fb-d (chat endpoint catches LLMToolError → HTTP 502)]

# Tech tracking
tech-stack:
  added: []  # zero new pip deps; anthropic + ollama already pinned via plan 15-02
  patterns:
    - "Provider-neutral adapter pattern: Protocol + 2 concrete classes with init_state/send_turn/append_results contract"
    - "Sticky per-session schema downgrade fallback for strict-mode 400s (Anthropic D-31)"
    - "Soft allow-list WARNING (not hard fail) for unverified Ollama tool models (D-29)"
    - "Phase 8 cf221fe credential-leak rule extended to provider-boundary exception wrapping (type(exc).__name__ never str(exc))"
    - "Composite tool-call ref scheme f'{idx}:{name}' for providers that lack opaque tool-use ids"

key-files:
  created:
    - forge_bridge/llm/_adapters.py — Protocol + 2 adapters + 3 dataclasses + 2 constants (~446 LOC)
    - tests/llm/__init__.py — package marker (project convention; mirrors tests/console, tests/mcp)
    - tests/llm/conftest.py — _StubAdapter + mock_ollama + helper fixtures (~168 LOC)
    - tests/llm/test_anthropic_adapter.py — 14 wire-format tests (~282 LOC)
    - tests/llm/test_ollama_adapter.py — 14 wire-format tests (~262 LOC)
  modified: []

key-decisions:
  - "Single _adapters.py module (not separate _anthropic_adapter.py + _ollama_adapter.py) — adapters total 446 LOC including dataclasses + Protocol; cleanly fits one file per Claude's-discretion guidance in 15-CONTEXT.md"
  - "Dataclasses live in _adapters.py (not a separate _types.py) — no import-cycle risk because LLMToolError comes from router.py, not from a common types module"
  - "tests/llm/__init__.py created to match the project's existing tests/console/__init__.py and tests/mcp/__init__.py convention; required for clean pytest collection"
  - "AnthropicToolAdapter sets `disable_parallel_tool_use=True` even when tools_payload is empty — keeps the wire-format invariant constant per turn (cheaper than conditional logic for zero behavior gain when tools=[])"

patterns-established:
  - "Provider-boundary exception wrapping: catch (Exception,) — log only `type(exc).__name__`, never `str(exc)` — wrap as LLMToolError(f'{provider} call failed: {exc_type}') from exc"
  - "Adapter Protocol contract: init_state(*, kw-only) → state; async send_turn(state) → _TurnResponse; append_results(state, response, results) → state. All state objects opaque to coordinator (adapter-internal dict shape)"
  - "Soft allow-list pattern: emit logger.warning at construction time when model is outside the verified set; do NOT raise. Production env vars are deterministic; artist experimentation friendly"

requirements-completed: [LLMTOOL-01, LLMTOOL-02, LLMTOOL-03]

# Metrics
duration: ~3min
completed: 2026-04-27
---

# Phase 15 (FB-C) Plan 05: Tool-Call Adapters Summary

**Provider-neutral _ToolAdapter Protocol + AnthropicToolAdapter (strict=True with sticky downgrade fallback) + OllamaToolAdapter (keep_alive='10m', soft allow-list WARNING) + _StubAdapter test fixture for the Wave 3 coordinator.**

## Performance

- **Duration:** ~3 min execution (plan was extensively pre-specified — implementation was largely transcription + verification)
- **Started:** 2026-04-27T02:57:10Z (Task 1 commit)
- **Completed:** 2026-04-27T03:00:57Z
- **Tasks:** 4 / 4 complete
- **Files created:** 5 (one over plan's listed 4 — `tests/llm/__init__.py` added per project convention; documented as Rule 3 deviation below)
- **LOC delivered:** 1,158 across 4 source files (446 module + 712 tests)

## Accomplishments

- Wire-format translation for both v1.4 supported providers (LLMTOOL-01 Ollama + LLMTOOL-02 Anthropic) shipped through one stable Protocol
- D-06 serial-only enforcement: `supports_parallel = False` on both adapters; Anthropic also sends `disable_parallel_tool_use=True` at top level
- D-31 strict mode + per-tool downgrade fallback: when Anthropic returns a 400 mentioning a forge tool name, that tool's `strict` flag is dropped and the request is retried once; downgrade is sticky for the session (logged + tracked in `_downgraded_tools` set)
- D-29 soft allow-list: `_OLLAMA_TOOL_MODELS` frozenset of 5 verified models; unrecognized models emit a single WARNING at adapter construction time (not per send_turn)
- D-33 `keep_alive="10m"` sent on every Ollama chat request — eliminates the 30s reload cliff mid-loop
- D-35 token-accounting normalization: both adapters return `(prompt_tokens, completion_tokens)` tuples on `_TurnResponse.usage_tokens`
- Phase 8 cf221fe credential-leak rule honored: provider exceptions are wrapped as `LLMToolError(f"...call failed: {type(exc).__name__}")` — never interpolating `str(exc)`
- D-37 `_StubAdapter` deterministic-replay fixture in place — Wave 3 plan 15-08's coordinator unit tests can now run without a live LLM
- Composite tool-call ref scheme `f"{idx}:{name}"` shipped for Ollama (which lacks opaque tool-use ids) — round-trips cleanly through `ToolCallResult.tool_call_ref`

## Task Commits

Each task was committed atomically (all `--no-verify` per parallel-execution context):

1. **Task 1: Create forge_bridge/llm/_adapters.py with Protocol, dataclasses, constants, and both adapter classes** — `cd4083a` (feat)
2. **Task 2: Create tests/llm/conftest.py with _StubAdapter and mock_ollama fixtures** — `5c53fbf` (test) — also includes `tests/llm/__init__.py` package marker
3. **Task 3: Create tests/llm/test_anthropic_adapter.py with wire-format unit tests** — `da2eb1a` (test) — 14 tests, all green
4. **Task 4: Create tests/llm/test_ollama_adapter.py with wire-format unit tests** — `a251025` (test) — 14 tests, all green

## Files Created/Modified

- `forge_bridge/llm/_adapters.py` (NEW, 446 LOC) — Protocol + 2 adapters + 3 dataclasses + 2 module-level constants. Exports: `_ToolAdapter`, `AnthropicToolAdapter`, `OllamaToolAdapter`, `_TurnResponse`, `_ToolCall`, `ToolCallResult`, `_OLLAMA_TOOL_MODELS`, `_OLLAMA_KEEP_ALIVE`. Imports `LLMToolError` concretely from `forge_bridge.llm.router` (plan 15-03 dependency).
- `tests/llm/__init__.py` (NEW, 1 LOC) — package marker mirroring `tests/console/__init__.py` and `tests/mcp/__init__.py`. Required for pytest to treat `tests/llm` as a discoverable test package.
- `tests/llm/conftest.py` (NEW, 168 LOC) — `_StubAdapter` (D-37 deterministic replay), `mock_ollama` fixture (mirrors `mock_anthropic`), `stub_adapter` / `make_terminal_turn` / `make_tool_call_turn` pytest fixtures, plus module-level `_make_terminal_turn` / `_make_tool_call_turn` helpers for direct import.
- `tests/llm/test_anthropic_adapter.py` (NEW, 282 LOC) — 4 test classes / 14 tests: schema translation, strict-mode default, downgrade tracking, response parsing, `disable_parallel_tool_use`, usage_tokens normalization, tool_result-first ordering (research §2.3), credential-leak posture for `LLMToolError`.
- `tests/llm/test_ollama_adapter.py` (NEW, 262 LOC) — 5 test classes / 14 tests: function-wrapper schema, allow-list warning emission, `keep_alive='10m'`, dict + string argument parsing, composite ref `{idx}:{name}`, `usage_tokens` from `prompt_eval_count` + `eval_count`, role:tool message shape with `tool_name` field, order preservation, credential-leak posture.

## Decisions Made

- **Single `_adapters.py` module:** kept Protocol + 2 adapters + 3 dataclasses + 2 constants in one file (446 LOC). The 80-LOC-per-adapter research estimate held; splitting would add `from forge_bridge.llm._anthropic_adapter import ...` import overhead for downstream coordinator code with no offsetting clarity gain. Matches Phase 8's `learning/storage.py` precedent (Protocol + concrete + dataclass colocated).
- **Dataclasses NOT extracted to `_types.py`:** the dataclasses are only consumed by adapter code and the coordinator (which will import them from the same `_adapters` module). No third consumer exists yet.
- **`tests/llm/__init__.py` matches project convention:** `tests/console/` and `tests/mcp/` both ship `__init__.py` files; `tests/llm/` follows suit. This is required for the conftest fixture discovery to work cleanly across the eventual ~5+ test files in this directory.
- **`disable_parallel_tool_use=True` is unconditional in Anthropic adapter:** even when `tools_payload == []`, the parameter is sent. Cheaper than conditional logic; the wire-format invariant matches D-06 verbatim ("serial tool execution by default") regardless of tool count.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added `tests/llm/__init__.py` package marker**
- **Found during:** Task 2 (creating tests/llm/conftest.py)
- **Issue:** Plan listed 4 files in `<verification>` "git diff --stat shows exactly 4 files modified/added", but `tests/llm/` did not exist as a Python package — without an `__init__.py`, pytest's collection would still work in default mode but the project's existing convention (`tests/console/__init__.py`, `tests/mcp/__init__.py`) is to mark every test subdirectory as a package. Following the convention prevents future relative-import ambiguity if test files need to share helpers.
- **Fix:** Added `tests/llm/__init__.py` with a one-line docstring matching `tests/console/__init__.py` shape.
- **Files modified:** `tests/llm/__init__.py` (new, 1 LOC)
- **Verification:** `pytest tests/llm/ -x -q` collects all 28 tests cleanly; full repo `pytest tests/test_llm.py tests/test_public_api.py -x -q` still passes (38 tests, no regression).
- **Committed in:** `5c53fbf` (Task 2 commit, alongside `tests/llm/conftest.py`)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Zero scope creep; convention-matching addition. The plan's `git diff --stat` line of "exactly 4 files" is now exactly 5 — `tests/llm/__init__.py` is documented above for downstream verification clarity.

## Issues Encountered

None. The plan was extensively pre-specified with verbatim source code blocks, structural verify commands, and acceptance criteria. Execution was largely transcription → run-verify → commit, which is the planner's intent for Wave 2 work.

## Verification Results

- `pytest tests/llm/ -x -q`: **28 passed** (all Wave 2 tests — 14 Anthropic + 14 Ollama)
- `pytest tests/test_llm.py tests/test_public_api.py -x -q`: **38 passed** (zero regression on prior LLMRouter + public-API tests)
- Cross-module import sanity: `python -c "from forge_bridge.llm._adapters import ...; from tests.llm.conftest import ..."` → succeeds

## TDD Gate Compliance

Tasks 1, 3, 4 carry `tdd="true"` in the plan frontmatter. Gate sequence in commit history:

- **Task 1 (RED):** Inline structural verify command in `<verify>` block doubled as the RED gate — verified-failure was implicit (file didn't exist before commit), then verified-pass after the file was written. The commit is `feat(15-05): add provider-neutral tool-call adapters` (`cd4083a`) — captures both creation and the verify pass since the verify is inline rather than a separate test file. This is acceptable per the plan's design where Task 1 ships the production module that Tasks 3/4 then test exhaustively.
- **Task 3 (RED → GREEN combined):** test file written; adapter from Task 1 already shipped, so all 14 tests passed on first run. Commit: `da2eb1a` (test).
- **Task 4 (RED → GREEN combined):** same shape — 14 tests passed on first run against existing adapter. Commit: `a251025` (test).

The TDD discipline here is: Task 1 creates the production code under direct structural verification; Tasks 3 and 4 then exhaustively cover the wire-format surface. The Plan's requirements gate (LLMTOOL-01/02/03) is satisfied by the combination — adapters exist and are tested.

## Threat Flags

None — plan's `<threat_model>` (T-15-19 through T-15-26) is fully covered by tests:
- **T-15-19** (credential leak in exception messages): tested by `TestAnthropicToolAdapterDowngrade::test_unrecoverable_provider_error_raises_LLMToolError` and `TestOllamaToolAdapterErrors::test_provider_exception_wrapped_as_LLMToolError`
- **T-15-20** (Anthropic strict-mode 400): tested by `TestAnthropicToolAdapterDowngrade::test_400_with_tool_name_triggers_downgrade_and_retry`
- **T-15-21** (parallel race): tested by `TestAnthropicToolAdapterSendTurn::test_disable_parallel_tool_use_true_sent` + `supports_parallel=False` on both adapters
- **T-15-22** (Ollama unload): tested by `TestOllamaToolAdapterSendTurn::test_keep_alive_10m_sent_on_every_request`
- **T-15-23** (silent unreliable model): tested by `TestOllamaToolAdapterAllowList::test_unknown_model_emits_warning`
- **T-15-24** / **T-15-25** / **T-15-26**: accept-disposition (no test required) — all are operationally-acceptable surfaces with documented logging signals.

No new security-relevant surfaces introduced beyond the threat model.

## User Setup Required

None — no external service configuration required. The new adapters use the existing pip-pinned `anthropic>=0.97,<1` (already in `[llm]` extra) and `ollama>=0.6.1,<1` (added by plan 15-02 if applicable; otherwise lazy-imported on first construction). All tests run without either package installed via the `mock_anthropic` / `mock_ollama` `sys.modules` patching pattern.

## Next Phase Readiness

**Wave 3 plan 15-08 (LLMRouter.complete_with_tools coordinator) is unblocked.** Specifically:

- Coordinator can `from forge_bridge.llm._adapters import _ToolAdapter, AnthropicToolAdapter, OllamaToolAdapter, ToolCallResult, _ToolCall, _TurnResponse` and instantiate either adapter based on the sensitivity bit
- Coordinator unit tests in `tests/llm/test_complete_with_tools.py` can `from tests.llm.conftest import _StubAdapter, _make_terminal_turn, _make_tool_call_turn` for deterministic loop-logic exercises (LLMTOOL-03 budget caps, LLMTOOL-04 repeat-call detection, hallucinated-tool injection)
- `_OLLAMA_TOOL_MODELS` and `_OLLAMA_KEEP_ALIVE` are public-named-but-private constants — coordinator does not import these (D-29's check is adapter-internal); Wave 3 doesn't need them
- The Protocol contract is the only coordinator dependency — no concrete adapter knowledge leaks into the coordinator code

**Wave 4 plan 15-09 (live integration tests) is also unblocked.** Both adapters can be exercised end-to-end against real Anthropic + real local Ollama via the env-gated test pattern (D-32).

## Self-Check: PASSED

All 6 expected files exist on disk:
- `forge_bridge/llm/_adapters.py`
- `tests/llm/__init__.py`
- `tests/llm/conftest.py`
- `tests/llm/test_anthropic_adapter.py`
- `tests/llm/test_ollama_adapter.py`
- `.planning/phases/15-fb-c-llmrouter-tool-call-loop/15-05-SUMMARY.md`

All 4 task commits present in `git log`: `cd4083a`, `5c53fbf`, `da2eb1a`, `a251025`.

---
*Phase: 15-fb-c-llmrouter-tool-call-loop*
*Plan: 05 (FB-C Wave 2 sibling — adapters)*
*Completed: 2026-04-27*
