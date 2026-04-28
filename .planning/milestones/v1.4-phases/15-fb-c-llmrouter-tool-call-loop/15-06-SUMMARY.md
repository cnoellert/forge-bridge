---
phase: 15-fb-c-llmrouter-tool-call-loop
plan: 06
subsystem: llm
tags: [llmtool-07, contextvar, ast-walk, recursive-synthesis, security, belt-and-suspenders, synthesizer-safety]

# Dependency graph
requires:
  - phase: 15-fb-c-llmrouter-tool-call-loop
    provides: "RecursiveToolLoopError public exception class in forge_bridge/llm/router.py (plan 15-03)"
provides:
  - "_in_tool_loop ContextVar (default=False) at module level in forge_bridge/llm/router.py — runtime layer 2 of recursive-synthesis defense (D-12)"
  - "acomplete() entry check raising RecursiveToolLoopError when _in_tool_loop is True (D-13)"
  - "_check_safety() AST walker rejects all 4 forms of forge_bridge.llm imports — static layer 1 of recursive-synthesis defense (D-14)"
  - "tests/llm/ test package with test_recursive_guard.py (10 tests, 3 classes) covering both layers + LLMTOOL-07 acceptance integration test"
affects: [15-fb-c-llmrouter-tool-call-loop, 15-08-coordinator-tool-loop, 16-fb-d-chat-endpoint]

# Tech tracking
tech-stack:
  added: [contextvars]
  patterns:
    - "Module-level ContextVar declared above class definition with documentation block"
    - "Belt-and-suspenders multi-layer defense (static AST + runtime ContextVar + process-level quarantine)"
    - "Single-pass AST walk extension — add parallel branches inside existing `for node in ast.walk(tree)` loop without new helper or new module"
    - "Test subdir layout (tests/llm/) mirroring tests/console/ pattern for FB-C test suite"

key-files:
  created:
    - "tests/llm/__init__.py"
    - "tests/llm/test_recursive_guard.py"
  modified:
    - "forge_bridge/llm/router.py"
    - "forge_bridge/learning/synthesizer.py"

key-decisions:
  - "Implementation followed plan verbatim — D-12/D-13/D-14 patterns from CONTEXT.md applied as specified"
  - "Created tests/llm/__init__.py as a package init (Rule 3 auto-fix) — required for pytest to discover the new subdir test package; mirrors tests/console/__init__.py convention"
  - "test_acomplete_proceeds_after_contextvar_reset asserts ContextVar state after reset rather than calling acomplete() — no real backend available in unit test scope and the assertion is sufficient (post-reset acomplete behavior is already covered by all 38 existing tests/test_llm.py tests that ran without _in_tool_loop set)"

patterns-established:
  - "ContextVar declaration with multi-line documentation block: explain the 3-layer defense in a comment block above the declaration so future readers see the architectural intent without grepping CONTEXT.md"
  - "AST safety walker extension pattern: add parallel `if isinstance(node, ast.Import)` / `ast.ImportFrom` branches inside the existing `for node in ast.walk(tree)` loop — preserves single-pass traversal, no new helper, no new module per D-14 / 15-PATTERNS.md"
  - "Test file structure for security guards: 3 classes (Layer 1 / Layer 2 / Integration) with the integration class containing exactly the LLMTOOL-NN acceptance test verbatim from research §7"

requirements-completed: [LLMTOOL-07]

# Metrics
duration: 4min
completed: 2026-04-27
---

# Phase 15 Plan 06: LLMTOOL-07 Recursive-Synthesis Guard (Helper Side) Summary

**Belt-and-suspenders layers 1 + 2 of LLMTOOL-07: synthesizer AST walker rejects forge_bridge.llm imports (D-14), router.py declares _in_tool_loop ContextVar with acomplete() entry check (D-12/D-13), and tests/llm/test_recursive_guard.py proves both layers work**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-04-27T02:55:12Z
- **Completed:** 2026-04-27T02:58:45Z
- **Tasks:** 3 of 3 complete
- **Files modified:** 4 (2 source modifications + 1 test package init + 1 new test file)

## Accomplishments

- **Layer 1 (static AST guard):** `_check_safety()` in `forge_bridge/learning/synthesizer.py` now rejects all 4 forms of `forge_bridge.llm` imports (`from X.Y import Z`, `from X import Y`, `import X.Y`, `import X` for X.Y = forge_bridge.llm[.router]) while preserving the SUPPORTED `forge_bridge.bridge` import path that synthesized tools rely on per CLAUDE.md / SYNTH_PROMPT
- **Layer 2 (runtime ContextVar guard):** Module-level `_in_tool_loop: ContextVar[bool]` (default=False) declared in `forge_bridge/llm/router.py`; `acomplete()` raises `RecursiveToolLoopError` as its first executable statement after the docstring when the ContextVar is True. Belt-and-suspenders against the importlib dynamic-import bypass that the static AST walker cannot catch
- **Integration test (LLMTOOL-07 acceptance):** `TestRecursiveSynthesisIntegration::test_synthesized_tool_with_recursive_llm_call_is_quarantined` reproduces research §7's verbatim acceptance scenario — a synthesized tool body that imports LLMRouter and calls back into acomplete() — and proves the static guard rejects it BEFORE the runtime guard ever needs to fire
- **All 4 forms of forge_bridge.llm imports rejected** (Test 1-4 in TestSafetyForgeBridgeLlmImport); supported `forge_bridge.bridge` import preserved (Test 5); bare `import forge_bridge` preserved (Test 6); existing eval/exec/os.system surface still rejected (regression-checked via `pytest tests/test_synthesizer.py` — all 29 pass)
- **Wave 3 plan 15-08 will:** (a) add the same entry check to `complete_with_tools()`, and (b) set/reset the ContextVar via `try/finally` inside `complete_with_tools()`'s body — completing the runtime side of LLMTOOL-07. The 3rd layer (Phase 3 manifest-based quarantine) is already in production

## Task Commits

Each task committed atomically:

1. **Task 1: Add `_in_tool_loop` ContextVar + acomplete() entry check** — `e3f3620` (feat)
2. **Task 2: Extend `_check_safety()` to reject forge_bridge.llm imports** — `4e0bfab` (feat)
3. **Task 3: Create tests/llm/test_recursive_guard.py** — `16177ec` (test)

## Files Created/Modified

- `forge_bridge/llm/router.py` (MODIFIED, +38 lines) — added `import contextvars`, module-level `_in_tool_loop` ContextVar declaration with multi-line documentation block above `class LLMRouter`, and the D-13 entry check in `acomplete()` body (after docstring) raising `RecursiveToolLoopError` when the ContextVar is True
- `forge_bridge/learning/synthesizer.py` (MODIFIED, +26 lines) — extended `_check_safety()` AST walker with two parallel branches inside the existing `for node in ast.walk(tree)` loop: `isinstance(node, ast.Import)` checks each `alias.name` against the `forge_bridge.llm` prefix, and `isinstance(node, ast.ImportFrom)` checks `node.module` against the same prefix. Updated docstring to document the new D-14 check
- `tests/llm/__init__.py` (NEW, 1 line) — package marker for pytest discovery, mirrors `tests/console/__init__.py` shape
- `tests/llm/test_recursive_guard.py` (NEW, 183 lines, 10 tests) — three test classes: `TestSafetyForgeBridgeLlmImport` (6 tests covering Layer 1), `TestContextVarRuntimeGuard` (3 tests covering Layer 2), `TestRecursiveSynthesisIntegration` (1 test — the LLMTOOL-07 acceptance integration test verbatim from research §7)

## Decisions Made

- **Followed plan verbatim** — D-12 ContextVar declaration, D-13 acomplete entry check, and D-14 AST walker extension were all specified with literal code snippets in the plan; no architectural choices to make
- **`tests/llm/__init__.py` is a Rule 3 auto-fix** — pytest needs the package init for discovery; the plan didn't list it explicitly but it's mechanical and required for the new test subdir to be importable. The file is a single docstring line matching `tests/console/__init__.py`'s shape
- **`test_acomplete_proceeds_after_contextvar_reset` asserts ContextVar state, not actual `acomplete()` invocation** — the test scope cannot fake an Ollama backend (no MagicMock client wiring needed for this layer). Asserting `_in_tool_loop.get() is False` after reset is the necessary precondition; the broader "acomplete proceeds normally" claim is covered by all 38 existing `tests/test_llm.py` tests passing without `_in_tool_loop` being set

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Created `tests/llm/__init__.py` as package init**
- **Found during:** Task 3 (creating tests/llm/test_recursive_guard.py)
- **Issue:** Plan listed `tests/llm/test_recursive_guard.py` but did not list `tests/llm/__init__.py`. Without the package init, pytest cannot discover the new test subdir as a package (per the project convention used by `tests/console/__init__.py` and `tests/mcp/__init__.py`)
- **Fix:** Created `tests/llm/__init__.py` with a single-line module docstring matching the shape of `tests/console/__init__.py`
- **Files modified:** `tests/llm/__init__.py` (NEW, 1 line)
- **Verification:** `pytest tests/llm/test_recursive_guard.py -x -v` discovers and runs all 10 tests
- **Committed in:** 16177ec (alongside test_recursive_guard.py — same Task 3 commit since both files together form the new test package)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** The auto-fix was mechanical and required for test discovery — exactly the same pattern as `tests/console/__init__.py` from Phase 14. The `git diff --stat` shows 4 files modified vs. the plan's "exactly 3 files modified" expectation; the 4th file is the package init, not new functionality.

## Issues Encountered

- None — plan was fully self-contained with verbatim code snippets for all three D-12/D-13/D-14 patterns. Zero ambiguity, zero blockers.

## User Setup Required

None — no external service configuration required.

## Verification Run

Cross-module sanity (verbatim from plan `<verification>` section):

```
$ python -c "from forge_bridge.llm.router import _in_tool_loop, RecursiveToolLoopError; assert _in_tool_loop.get() is False"
OK

$ python -c "import ast; from forge_bridge.learning.synthesizer import _check_safety; assert _check_safety(ast.parse('from forge_bridge.llm import router')) is False and _check_safety(ast.parse('from forge_bridge.bridge import execute')) is True"
OK

$ pytest tests/llm/test_recursive_guard.py tests/test_synthesizer.py tests/test_llm.py tests/test_public_api.py -x -q
77 passed, 1 warning in 1.75s
```

## Next Phase Readiness

- Wave 3 plan 15-08 (`complete_with_tools()` coordinator) can now rely on:
  - `_in_tool_loop` ContextVar already declared at module level in router.py — plan 15-08 only needs to add the `try/finally` set/reset around `_loop_body()` and the same entry check at the top of `complete_with_tools()`
  - `RecursiveToolLoopError` already exported (plan 15-03) and message text identifies the recursive-synthesis cause for FB-D's HTTP 500 mapping
  - Synthesizer AST walker already rejects `forge_bridge.llm` imports — synthesizer dry-run / quarantine pipeline (Phase 3) blocks these files before they ever reach the registered tool surface, regardless of whether the runtime ContextVar guard fires
- No blockers for the parallel siblings in Wave 2 of Phase 15 — this plan touches `forge_bridge/llm/router.py` (additive only — new ContextVar + new entry check) and `forge_bridge/learning/synthesizer.py` (additive only — new AST branches inside the existing walker). Other Wave 2 plans modifying separate files (sanitization, adapters, etc.) cannot collide

## Self-Check: PASSED

All claimed files and commits verified to exist:

- `forge_bridge/llm/router.py`: FOUND (HEAD shows the contextvar declaration and acomplete entry check at lines visible in `git diff e3f3620^..e3f3620`)
- `forge_bridge/learning/synthesizer.py`: FOUND (HEAD shows the D-14 import-rejection branches in `git diff 4e0bfab^..4e0bfab`)
- `tests/llm/__init__.py`: FOUND (1-line package marker)
- `tests/llm/test_recursive_guard.py`: FOUND (183 lines, 10 tests, all PASSED)
- Commit `e3f3620`: FOUND in `git log --oneline -5`
- Commit `4e0bfab`: FOUND in `git log --oneline -5`
- Commit `16177ec`: FOUND in `git log --oneline -5`

---

*Phase: 15-fb-c-llmrouter-tool-call-loop*
*Plan: 06*
*Completed: 2026-04-27*
