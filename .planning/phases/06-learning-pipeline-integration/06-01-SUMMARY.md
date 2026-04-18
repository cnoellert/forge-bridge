---
phase: 06-learning-pipeline-integration
plan: 01
subsystem: learning-pipeline
tags: [execution-log, storage-callback, asyncio, dataclass, jsonl, lrn-02]

# Dependency graph
requires:
  - phase: 03-learning-pipeline
    provides: ExecutionLog class with JSONL persistence, normalize_and_hash, promotion counters
  - phase: 04-api-surface-hardening
    provides: constructor-injection pattern (LLMRouter) and single-callback/setter idiom (set_execution_callback in bridge.py)
provides:
  - ExecutionRecord frozen dataclass (5 fields mirroring JSONL schema)
  - StorageCallback type alias (Callable[[ExecutionRecord], None | Awaitable[None]])
  - ExecutionLog.set_storage_callback(fn | None) per-instance hook
  - Post-flush dispatch (sync try/except logger.warning, async ensure_future + add_done_callback)
  - _log_callback_exception module helper for async done-callbacks
  - JSONL payload built from asdict(record) — schema stays in sync with dataclass
affects:
  - 06-02 (pre_synthesis_hook follows the same hook-on-class setter pattern)
  - 06-03 (public __init__ re-exports will add ExecutionRecord to the barrel)
  - 06-04 (consumer wiring registers the storage callback in projekt-forge __main__.py)

# Tech tracking
tech-stack:
  added: []  # no new deps — uses stdlib inspect, asyncio, dataclasses
  patterns:
    - frozen dataclass for internal structural type (matches _BridgeConfig shape)
    - sync-or-async single-callback with registration-time dispatch-mode caching
    - best-effort mirror with source-of-truth isolation (JSONL append cannot be rolled back by callback failure)

key-files:
  created: []
  modified:
    - forge_bridge/learning/execution_log.py
    - tests/test_execution_log.py
    - tests/conftest.py

key-decisions:
  - "ExecutionRecord built FIRST, then JSONL write uses asdict(record) — no hand-built dict, no field drift"
  - "Dispatch mode (sync vs async) detected ONCE at set_storage_callback() via inspect.iscoroutinefunction, cached as _storage_callback_is_async — per-call dispatch never re-inspects"
  - "Callback dispatch fires AFTER fcntl.LOCK_UN (source-of-truth preserved on disk before best-effort mirror runs)"
  - "Docstring discipline: 'JSONL log is source-of-truth; the callback is a best-effort mirror' appears exactly once (in set_storage_callback docstring) — inline comment variant removed to satisfy acceptance criterion"
  - "tests/conftest.py sys.path injection added as Rule 3 blocker-fix: a non-editable forge-bridge 1.0.1 shadow install (from Plan 05-04) hid the new ExecutionRecord symbol from pytest"

patterns-established:
  - "Instance-scoped single-callback via setter method (mirrors bridge.py set_execution_callback but lives on a class, supports async, uses logger.warning instead of bare except pass)"
  - "asyncio.ensure_future + add_done_callback(_log_callback_exception) for fire-and-forget async dispatch with loggable exception surfacing"
  - "ExecutionRecord-as-contract: the dataclass IS the on-disk schema — consumers can type against it, JSONL writes use asdict(record) to prevent drift"

requirements-completed: [LRN-02]

# Metrics
duration: 5min
completed: 2026-04-18
---

# Phase 6 Plan 01: ExecutionLog set_storage_callback Summary

**Per-instance `set_storage_callback()` hook on `ExecutionLog` firing a frozen `ExecutionRecord` dataclass to a sync or async consumer after every JSONL append — with exception isolation that preserves the log-as-source-of-truth invariant.**

## Performance

- **Duration:** 5 min 3 sec
- **Started:** 2026-04-18T06:18:32Z
- **Completed:** 2026-04-18T06:23:35Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added frozen `ExecutionRecord` dataclass (code_hash, raw_code, intent, timestamp, promoted) that mirrors the JSONL on-disk schema exactly. `record()` now builds this dataclass first and writes `json.dumps(asdict(record))` so the in-memory and on-disk shapes cannot diverge.
- Added `ExecutionLog.set_storage_callback(fn | None)` per-instance setter. Sync-vs-async mode is detected once via `inspect.iscoroutinefunction` and cached in `_storage_callback_is_async`; per-call dispatch uses the cached flag. Passing `None` clears the callback (symmetric unset per CONTEXT.md Claude's Discretion).
- Added post-flush dispatch inside `record()`: sync path uses `try/except Exception` with `logger.warning(..., exc_info=True)`; async path uses `asyncio.ensure_future` + `add_done_callback(_log_callback_exception)`, and catches `RuntimeError` when there is no running loop. Both modes fire AFTER `fcntl.LOCK_UN` so JSONL persistence completes before the mirror runs.
- Added 5 new tests covering sync dispatch, async dispatch, exception isolation, None-clears, and full-record payload fidelity. All 21 tests in the module pass (16 existing + 5 new); the full repo suite is 212 pass / 0 fail.
- Fixed a Rule 3 test-resolution blocker: the conda env had `forge-bridge 1.0.1` non-editable in site-packages (from Plan 05-04's git-tag install) which shadowed the worktree source during pytest. Scoped `sys.path` injection in `tests/conftest.py` makes the repo's tests exercise local source without touching the site-packages install.

## Task Commits

Each task was committed atomically:

1. **Task 1: ExecutionRecord dataclass + set_storage_callback + dispatch** — `bc12dca` (feat)
2. **Task 2: Storage callback test coverage (+ conftest sys.path fix)** — `9b38673` (test)

_Note: Task 1 and Task 2 are both tagged TDD in the plan but the plan split implementation and test-writing across the two tasks rather than per-task RED/GREEN/REFACTOR. Existing test coverage protected Task 1; new test cases land in Task 2._

## Files Created/Modified

- `forge_bridge/learning/execution_log.py` — Added imports (`asyncio`, `inspect`, `asdict`, `Awaitable`, `Callable`, `Union`), `ExecutionRecord` frozen dataclass, `StorageCallback` type alias, `_log_callback_exception` module helper; extended `ExecutionLog.__init__` with two new instance attrs; added `set_storage_callback()` method; rewrote `record()` body to use `ExecutionRecord`-first construction with post-flush dispatch.
- `tests/test_execution_log.py` — Added `from unittest.mock import AsyncMock, MagicMock`; appended 5 new tests in a "Storage callback tests (LRN-02)" section at the end of the file.
- `tests/conftest.py` — Rule 3 fix: added `sys.path` prepend for the repo root so pytest resolves `forge_bridge` to the worktree source rather than the site-packages 1.0.1 shadow.

## Decisions Made

- **ExecutionRecord-first construction.** The plan's `<action>` (Change E) makes the dataclass the single source of the JSONL payload. Implemented verbatim: `json.dumps(asdict(record))` replaces the hand-built `rec = {...}` dict literal. This means if anyone adds a field to `ExecutionRecord`, both the callback and the JSONL file pick it up automatically; field drift is structurally impossible.
- **Docstring uniqueness (resolving a plan-internal conflict).** The plan's `<action>` Change D puts the phrase _"JSONL log is source-of-truth; the callback is a best-effort mirror"_ in `set_storage_callback`'s docstring AND Change E adds it as an inline comment in `record()`. The acceptance criterion `grep: ... matches exactly once`. Resolution: kept the docstring (honors PATTERNS §1 "docstring discipline"), trimmed the inline comment to `# Fire storage callback AFTER the JSONL flush completes (best-effort mirror).` Both semantic intents are preserved and the grep acceptance passes.
- **Instance attribute position in `__init__`.** Plan Change C says "append AFTER `self._replay()`" — followed exactly. This ordering means if `_replay()` ever raises, the callback fields stay unset (accessor methods would fail), but `_replay()`'s existing implementation only raises via `try/except OSError` that logs and returns, so the ordering is safe.
- **`ExecutionRecord` field ordering.** Plan locks the 5 fields and their order; followed exactly (code_hash, raw_code, intent, timestamp, promoted). Order matches the JSONL keys established in Phase 3.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added `sys.path` injection to `tests/conftest.py` to defeat site-packages shadow**
- **Found during:** Task 2 (first pytest run after adding new tests)
- **Issue:** `pytest tests/test_execution_log.py` failed with `ImportError: cannot import name 'ExecutionRecord' from 'forge_bridge.learning.execution_log'`. Root cause: the conda env has `forge-bridge 1.0.1` non-editable in `/Users/cnoellert/miniconda3/envs/forge/lib/python3.11/site-packages/forge_bridge/` (installed by Plan 05-04's git-tag step as the projekt-forge guard target). That install lacks the new symbol. Pytest's module resolution chose site-packages over the worktree source because the repo root was not on `sys.path`.
- **Fix:** Added 4 lines at the top of `tests/conftest.py` that compute `_REPO_ROOT = Path(__file__).resolve().parent.parent` and prepend it to `sys.path` before the first `from forge_bridge ...` import. Standard pytest-repo idiom; scoped to the test session; does not modify any install.
- **Files modified:** tests/conftest.py
- **Verification:** Before fix, `pytest tests/test_execution_log.py::test_storage_callback_fires_on_record` failed with ImportError. After fix, all 21 tests in the file pass and the full suite of 212 tests pass with no regressions. `python -c "from forge_bridge.learning.execution_log import ExecutionLog, ExecutionRecord; print('OK')"` (from worktree root) also prints OK.
- **Scope note:** The fix is test-only and does not change production behavior, the public API surface, or the site-packages install. It's the minimum change needed for the plan's `<verify>` pytest commands to exercise the code they're meant to verify. Plan 06-03 (which re-exports `ExecutionRecord` from `forge_bridge/__init__.py`) will still need a fresh install or editable-mode reinstall when it lands, but that's outside this plan's scope.
- **Committed in:** 9b38673 (Task 2 commit, together with the 5 new tests)

**2. [Rule 1 - Bug] Docstring phrase duplicated (plan-internal inconsistency)**
- **Found during:** Task 1 acceptance criteria grep
- **Issue:** Plan `<action>` blocks Change D (docstring) and Change E (inline comment in `record()`) both add the verbatim phrase _"JSONL log is source-of-truth; the callback is a best-effort mirror"_. The `<acceptance_criteria>` then requires `grep ... matches exactly once`. Literal execution of the two `<action>` blocks produces 2 matches and fails the criterion.
- **Fix:** Kept the docstring instance (which PATTERNS §1 "docstring discipline" explicitly requires) and collapsed the inline comment to `# Fire storage callback AFTER the JSONL flush completes (best-effort mirror).` — preserves the semantic anchor in the dispatch site without re-matching the exact grep string.
- **Files modified:** forge_bridge/learning/execution_log.py (comment only)
- **Verification:** `python3` regex check confirms 1 match; all 212 tests pass.
- **Committed in:** bc12dca (the Task 1 commit — caught and fixed before committing so the commit itself is clean)

---

**Total deviations:** 2 auto-fixed (1 Rule 3 blocking, 1 Rule 1 plan-internal bug)
**Impact on plan:** Both auto-fixes were necessary for the plan's own `<verify>` and `<acceptance_criteria>` blocks to pass. No scope creep; no public-API shape changes beyond what the plan specifies.

## Issues Encountered

- One "issue" was actually a plan-internal inconsistency between two `<action>` blocks and the `<acceptance_criteria>` grep count — resolved in favor of the PATTERNS §1 guidance. Documented as Deviation #2 above.
- The site-packages shadow from Plan 05-04 is an environmental artifact, not a code bug, and was handled as a scoped `conftest.py` test-only fix (Deviation #1).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plan 06-02 (pre_synthesis_hook on SkillSynthesizer) can proceed in parallel — it modifies `synthesizer.py` and `tests/test_synthesizer.py`; no overlap with this plan's files.
- Plan 06-03 (re-export `ExecutionRecord` + `PreSynthesisContext` from `forge_bridge/__init__.py`) depends on this plan and 06-02. When 06-03 runs, the `forge_bridge.__init__` will add `ExecutionRecord` to `__all__`; consumers can then `from forge_bridge import ExecutionRecord`. Today `from forge_bridge.learning.execution_log import ExecutionRecord` is the supported path.
- Plan 06-04 (projekt-forge consumer wiring) will call `execution_log.set_storage_callback(_persist_execution)` against this API. The contract shape matches the CONTEXT.md D-01..D-06 locked decisions.
- No blockers. No unresolved concerns.

## Self-Check: PASSED

- FOUND: forge_bridge/learning/execution_log.py (modified, contains ExecutionRecord, StorageCallback, _log_callback_exception, set_storage_callback)
- FOUND: tests/test_execution_log.py (modified, contains 5 new storage-callback tests)
- FOUND: tests/conftest.py (modified, sys.path repo-root injection)
- FOUND: bc12dca (feat(06-01): add ExecutionRecord + set_storage_callback to ExecutionLog)
- FOUND: 9b38673 (test(06-01): add storage-callback coverage for ExecutionLog)
- VERIFIED: `python -c "from forge_bridge.learning.execution_log import ExecutionLog, ExecutionRecord; print('OK')"` → OK
- VERIFIED: `python -c "from forge_bridge import ExecutionLog; print('OK')"` → OK (LRN-02 bridge-side public surface — plan 06-03 adds ExecutionRecord to barrel)
- VERIFIED: `pytest tests/test_execution_log.py -x` → 21 passed, 1 warning
- VERIFIED: `pytest tests/` → 212 passed, 2 warnings (0 failures, 0 errors)
- VERIFIED: Docstring phrase "JSONL log is source-of-truth; the callback is a best-effort mirror" appears exactly once in execution_log.py (the `set_storage_callback` docstring)
- VERIFIED: All 10 Task 1 grep acceptance criteria + all 6 Task 2 grep acceptance criteria pass

---
*Phase: 06-learning-pipeline-integration*
*Completed: 2026-04-18*
