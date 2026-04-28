---
phase: 15-fb-c-llmrouter-tool-call-loop
plan: 01
subsystem: infra
tags: [sanitization, refactor, single-source-of-truth, llmtool-06, fb-c, prerequisite]

# Dependency graph
requires:
  - phase: 07-tool-provenance-mcp-annotations
    provides: INJECTION_MARKERS tuple + _CONTROL_CHAR_RE regex inside forge_bridge/learning/sanitize.py
provides:
  - forge_bridge/_sanitize_patterns.py — single source of truth for INJECTION_MARKERS + _CONTROL_CHAR_RE (D-09)
  - forge_bridge/learning/sanitize.py — backwards-compat re-export shim (D-10) — Phase 7 callers unchanged
  - tests/test_sanitize.py::TestSanitizePatternsShim — same-object identity + count regression guard (T-15-01 + T-15-04 mitigations)
  - Unblocks Wave 2 plan 15-04 (_sanitize_tool_result implementation, LLMTOOL-06)
affects:
  - 15-02 (later wave 1 plans) — none (this plan is isolated to sanitize patterns)
  - 15-04 (Wave 2 _sanitize_tool_result) — direct consumer of forge_bridge._sanitize_patterns
  - any future llm/* sanitization helper

# Tech tracking
tech-stack:
  added: []  # No new dependencies — pure code reorganization
  patterns:
    - "Hoist patterns, NOT helpers — central pattern store with consumer-specific helper semantics (D-09)"
    - "Same-object identity assertion as regression guard against silent forks (TestSanitizePatternsShim)"
    - "noqa: F401, E402 pattern for re-export shims that legitimately import after module-level code"

key-files:
  created:
    - forge_bridge/_sanitize_patterns.py
  modified:
    - forge_bridge/learning/sanitize.py
    - tests/test_sanitize.py

key-decisions:
  - "Hoisted constants only — INJECTION_MARKERS tuple + _CONTROL_CHAR_RE pattern. Helpers (_sanitize_tag, apply_size_budget) deliberately stayed put because consumer rejection semantics diverge (REJECT for tags, REPLACE for tool results — D-11)."
  - "Re-export shim path uses two import statements (one per constant) with explicit noqa comments documenting the F401 (unused-in-module) and E402 (post-module-code import position) waivers. This makes the shim explicit and grep-able rather than hidden behind a wildcard import."
  - "Permanent regression guard lives in tests/test_sanitize.py::TestSanitizePatternsShim alongside the consumer it protects. Same-object identity assertions catch a future contributor accidentally re-declaring the constants in learning/sanitize.py."

patterns-established:
  - "Top-level utility module pattern: forge_bridge/_sanitize_patterns.py is a single-purpose module containing only the data primitives, no helpers. Future shared utility constants follow this shape (e.g., a future _logging_patterns.py or _http_patterns.py)."
  - "Backwards-compat re-export shim with noqa comments — when constants must move but callers must not change, replace the literal declaration with `from <new_home> import <name>  # noqa: F401, E402`."

requirements-completed: [LLMTOOL-06]

# Metrics
duration: 4min
completed: 2026-04-27
---

# Phase 15 Plan 01: Sanitization Patterns Single Source of Truth Summary

**Hoisted INJECTION_MARKERS tuple + _CONTROL_CHAR_RE regex from forge_bridge/learning/sanitize.py to a new top-level forge_bridge/_sanitize_patterns.py module, with the original sanitize.py converted to a re-export shim — zero caller updates required, same-object identity locked by a regression test class.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-04-27T02:34:15Z
- **Completed:** 2026-04-27T02:38:01Z
- **Tasks:** 3 (all autonomous, no checkpoints)
- **Files modified:** 3 (1 new, 2 modified — exactly matches plan output spec)

## Accomplishments

- `forge_bridge/_sanitize_patterns.py` is the single source of truth for `INJECTION_MARKERS` and `_CONTROL_CHAR_RE`, satisfying the FB-C D-09 mandate and the v1.4 ROADMAP "single source of truth" line item from STATE.md.
- `forge_bridge/learning/sanitize.py` is now a thin re-export shim — Phase 7 callers (`watcher.py`, `mcp/registry.py`, `tests/test_sanitize.py`) require ZERO updates (D-10 invariant verified by 49 passing tests in `test_watcher.py` + `test_mcp_registry.py` + 26 unchanged passing tests in `test_sanitize.py`).
- Wave 2 plan 15-04 (`_sanitize_tool_result()` implementation, LLMTOOL-06) is unblocked — it can now `from forge_bridge._sanitize_patterns import INJECTION_MARKERS, _CONTROL_CHAR_RE` without any cycle through `learning/`.
- New `TestSanitizePatternsShim` class in `tests/test_sanitize.py` locks the contract via same-object-identity assertions, providing a regression guard against future contributors silently forking the pattern set.

## Task Commits

Each task was committed atomically with TDD discipline (RED → GREEN per `tdd="true"` plan tasks):

1. **Task 1: Create `forge_bridge/_sanitize_patterns.py` with hoisted constants**
   - RED `94f7b94` (test): added failing tests for the new module
   - GREEN `db21f61` (feat): created the module with hoisted constants
2. **Task 2: Convert `learning/sanitize.py` constants into re-export shim**
   - RED `be5a338` (test): added failing same-object identity assertion
   - GREEN `5ef8bdf` (refactor): replaced the literal declarations with `from forge_bridge._sanitize_patterns import …  # noqa: F401, E402` re-exports
3. **Task 3: Add permanent identity assertion class to `tests/test_sanitize.py`** — `885e839` (test)

_Note: Task 1 and Task 2 each have a separate test → implementation commit pair per the plan's `tdd="true"` directive. Task 3 is a test-only addition (no implementation phase). The Task 3 commit also reconciled the temporary RED-phase scaffolding files (`tests/test_sanitize_patterns.py`, `tests/test_sanitize_shim_temp.py`) — see Deviations below._

## Files Created/Modified

- `forge_bridge/_sanitize_patterns.py` — NEW. Hoisted `INJECTION_MARKERS` tuple (8 entries verbatim from Phase 7) + `_CONTROL_CHAR_RE` compiled regex. Module docstring explicitly notes the consumer-semantic divergence (REJECT for tags, REPLACE for tool results) so future contributors don't try to centralize the helpers.
- `forge_bridge/learning/sanitize.py` — MODIFIED. Replaced two constant declarations (lines 49-62 in the original) with `from forge_bridge._sanitize_patterns import …  # noqa: F401, E402` re-exports. All other constants and helpers (`MAX_TAG_CHARS`, `SANITIZE_ALLOWLIST`, `_PROTECTED_META_KEYS`, `_truncate_for_log`, `_sanitize_tag`, `apply_size_budget`) remain identical.
- `tests/test_sanitize.py` — MODIFIED. Appended `TestSanitizePatternsShim` (3 tests: same-object identity for both constants + count-locked at 8). Existing `TestSanitizeTag`, `TestApplySizeBudget`, `TestAllowlistConstant` classes unchanged.

## Decisions Made

- **Hoist patterns, not helpers** (D-09 mandate). The two consumers — Phase 7 `_sanitize_tag()` and FB-C's upcoming `_sanitize_tool_result()` — have intentionally divergent rejection semantics (REJECT vs. REPLACE). Centralizing the helpers would force one or both consumers to fight a unified API; centralizing only the patterns gives each consumer authority over its own behavior.
- **Two separate import statements with explicit `noqa` comments** in the shim, rather than a wildcard re-export or a tuple unpacking trick. This makes the shim deliberate and grep-able. The `noqa: F401` waives the unused-in-module rule (consumers re-import via `learning.sanitize`); the `noqa: E402` waives the not-at-top-of-file rule (the entire point of a shim is the re-export sits where the literal declarations used to be).
- **Permanent regression guard lives next to the consumer it protects**, not in a new test file. `tests/test_sanitize.py::TestSanitizePatternsShim` runs in the same pytest session as the rest of the sanitize tests and fails loudly if a future contributor re-declares `INJECTION_MARKERS` or `_CONTROL_CHAR_RE` in `learning/sanitize.py` (the same-object identity check catches both forks and accidental copies).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — Missing critical functionality] Reconciled TDD-scaffolding test files in Task 3 commit**

- **Found during:** Task 3 (after Task 1 + Task 2 RED phases generated `tests/test_sanitize_patterns.py` and `tests/test_sanitize_shim_temp.py` as scaffolding)
- **Issue:** The plan's `<output>` section explicitly states "Files created/modified (3 — _sanitize_patterns.py NEW, learning/sanitize.py shim, test_sanitize.py extended)" — exactly 3 files. The TDD-mandated RED-phase tests for Tasks 1 and 2 generated 2 additional test files (`test_sanitize_patterns.py`, `test_sanitize_shim_temp.py`) whose coverage is fully consolidated in Task 3's permanent `TestSanitizePatternsShim` class.
- **Fix:** Deleted both temporary files in the Task 3 commit (`885e839`). The permanent regression guard now lives in `tests/test_sanitize.py::TestSanitizePatternsShim`. Coverage of "import from `_sanitize_patterns` succeeds" is provided transitively — the shim's same-object identity assertion fails fast if either module-level import path breaks.
- **Files modified:** Deleted `tests/test_sanitize_patterns.py`, `tests/test_sanitize_shim_temp.py`
- **Verification:** Final state is exactly 3 modified files (`git diff --stat 26b01f2…HEAD` confirms). `pytest tests/test_sanitize.py tests/test_watcher.py tests/test_mcp_registry.py -x -q` reports 78 passing tests.
- **Committed in:** `885e839` (Task 3 commit) — deletions explicitly documented in the commit message

---

**Total deviations:** 1 auto-fixed (1 missing critical functionality — output-spec compliance)
**Impact on plan:** Reconciliation only. The deleted files were TDD scaffolding produced as a mechanical side effect of `tdd="true"` execution; their coverage is preserved in the permanent test class. No scope creep — the deviation strictly enforces the plan's stated 3-file output.

## Issues Encountered

None. Plan executed cleanly. The only friction was a minor `bash` `&&`-chain short-circuit during the AC-verification batch (a `grep -c` returning `0` — the desired value — caused the chained block to exit), which I worked around by re-running each AC check individually. No deviation-worthy.

## TDD Gate Compliance

Plan task type is per-task `tdd="true"` (not plan-level `type: tdd`), so the per-task RED/GREEN sequence was:

| Task | RED commit | GREEN commit |
|------|-----------|--------------|
| Task 1 | `94f7b94` (test) | `db21f61` (feat) |
| Task 2 | `be5a338` (test) | `5ef8bdf` (refactor) |
| Task 3 | n/a (test-only addition; no implementation phase) | `885e839` (test) |

Both per-task RED commits demonstrably failed before the GREEN commits made them pass — `tests/test_sanitize_patterns.py` failed with `ModuleNotFoundError: No module named 'forge_bridge._sanitize_patterns'`, and `tests/test_sanitize_shim_temp.py` failed with `assert hoisted is shimmed` (different tuple objects). REFACTOR phases were not needed (the GREEN code was minimal and correct on first write).

## User Setup Required

None — no external service configuration required.

## Threat Flags

No new threat surface introduced beyond the plan's pre-declared `<threat_model>`. The plan's STRIDE register entries are accounted for:

- **T-15-01 (Tampering, mitigate)** — same-object identity assertion landed in `TestSanitizePatternsShim::test_injection_markers_is_same_object` and `test_control_char_re_is_same_object` (Task 3 commit `885e839`).
- **T-15-04 (DoS via missing patterns, mitigate)** — count assertion landed in `TestSanitizePatternsShim::test_injection_markers_count_locked` (`885e839`).
- T-15-02 (Information disclosure, accept) and T-15-03 (Elevation of privilege, accept) — no implementation needed; verified by D-10 caller invariant pass.

## Next Phase Readiness

- Wave 2 plan 15-04 (`_sanitize_tool_result()` for LLMTOOL-06) can now `from forge_bridge._sanitize_patterns import INJECTION_MARKERS, _CONTROL_CHAR_RE` directly. The pattern set is locked; the consumer-specific REPLACE semantics ship in 15-04 alongside `_TOOL_RESULT_MAX_BYTES = 8192` (D-08/D-11).
- No blockers or concerns for downstream Wave 1 plans — this plan is isolated to the sanitization pattern hoist and does not touch any other Wave 1 surface.

## Self-Check: PASSED

**Files claimed exist:**
- `forge_bridge/_sanitize_patterns.py` — FOUND
- `forge_bridge/learning/sanitize.py` — FOUND (modified)
- `tests/test_sanitize.py` — FOUND (extended)

**Commits claimed exist:**
- `94f7b94` (test RED Task 1) — FOUND
- `db21f61` (feat GREEN Task 1) — FOUND
- `be5a338` (test RED Task 2) — FOUND
- `5ef8bdf` (refactor GREEN Task 2) — FOUND
- `885e839` (test Task 3) — FOUND

**Final test state:** 78/78 passing across `test_sanitize.py` (29) + `test_watcher.py` + `test_mcp_registry.py` (49 combined). Same-object identity verified by `python -c` one-liner.

---
*Phase: 15-fb-c-llmrouter-tool-call-loop*
*Completed: 2026-04-27*
