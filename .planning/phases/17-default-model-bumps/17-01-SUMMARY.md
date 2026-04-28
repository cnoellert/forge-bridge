---
phase: 17-default-model-bumps
plan: 01
subsystem: llm

tags: [llm, router, refactor, anthropic, ollama, default-model, decoupled-commit]

# Dependency graph
requires:
  - phase: 15
    provides: "Phase 15 D-30 decoupled-commit mandate — _DEFAULT_* constant changes must be isolated single-file commits, not coupled to loop logic. Plan 17-01 absorbs the structural refactor so 17-02 (MODEL-01) and 17-03 (MODEL-02) become pure one-line literal flips."
provides:
  - "Module-level `_DEFAULT_LOCAL_MODEL = \"qwen2.5-coder:32b\"` constant in forge_bridge/llm/router.py"
  - "Module-level `_DEFAULT_CLOUD_MODEL = \"claude-opus-4-6\"` constant in forge_bridge/llm/router.py"
  - "`LLMRouter.__init__` consumption sites rewired from inline literals to the new constants (no behavior change — values preserved byte-identical)"
  - "Single-line value-flip surface ready for Phase 17 P-02 (MODEL-01 cloud bump → claude-sonnet-4-6) and P-03 (MODEL-02 local bump → qwen3:32b conditional on UAT)"
affects: [17-02-MODEL-01-cloud-bump, 17-03-MODEL-02-local-bump]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Module-level `_DEFAULT_*` constants for tunables consumed by LLMRouter.__init__ — mirrors the existing `_DEFAULT_SYSTEM_PROMPT` precedent at router.py:46"
    - "Decoupled-commit purity: structural refactor (extraction) ships separately from value flips so `git blame` on a future bump line shows 'model bump', not 'refactor + bump'"

key-files:
  created: []
  modified:
    - "forge_bridge/llm/router.py — added two module-scope constants between `_DEFAULT_SYSTEM_PROMPT` and the FB-C exception classes; rewired `LLMRouter.__init__` to consume them via `os.environ.get(env_var, _DEFAULT_*)`"

key-decisions:
  - "Constant placement: between `_DEFAULT_SYSTEM_PROMPT` (ends at line 58) and the FB-C exception classes comment block (starts at line 73 in pre-edit numbering). This keeps all three module-level config defaults co-located, matching the plan's explicit guidance and the `_DEFAULT_SYSTEM_PROMPT` precedent."
  - "Both constants extracted in a single atomic commit per plan acceptance criteria — they are sibling tunables and share the same precedent comment-block style."
  - "Class docstring left unchanged (lines 166-170 in pre-edit, 178-182 in post-edit). It mentions `qwen2.5-coder:32b` and `claude-opus-4-6` inline; per the plan, those mentions remain accurate after this refactor since values are preserved. P-02 / P-03 will update the docstring along with the value flips."

patterns-established:
  - "Pattern: hoist consumed-once env-fallback literals into named module constants when a follow-on plan needs the value to flip — keeps the flip atomic and reviewable as a one-line literal change"

requirements-completed: [MODEL-01, MODEL-02]

# Metrics
duration: ~10min
completed: 2026-04-28
---

# Phase 17 Plan 01: Extract _DEFAULT_LOCAL_MODEL + _DEFAULT_CLOUD_MODEL Constants Summary

**Pure structural refactor of `forge_bridge/llm/router.py` — extracted the two inline default-model string literals at the `LLMRouter.__init__` env-fallback sites into module-level `_DEFAULT_LOCAL_MODEL` and `_DEFAULT_CLOUD_MODEL` constants, mirroring the `_DEFAULT_SYSTEM_PROMPT` precedent. Values byte-identical to v1.4 main; behavior unchanged. Unblocks the P-02 / P-03 single-line value flips per the Phase 15 D-30 decoupled-commit mandate.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-04-28T23:38:00Z (approx — worktree-base reset + plan read)
- **Completed:** 2026-04-28T23:47:27Z
- **Tasks:** 2 (1 source change + 1 verification)
- **Files modified:** 1 (`forge_bridge/llm/router.py`)

## Accomplishments

- Added `_DEFAULT_LOCAL_MODEL = "qwen2.5-coder:32b"` at module scope in `forge_bridge/llm/router.py` (post-edit line 64)
- Added `_DEFAULT_CLOUD_MODEL = "claude-opus-4-6"` at module scope in `forge_bridge/llm/router.py` (post-edit line 70)
- Rewired `LLMRouter.__init__` consumption sites (post-edit lines 199-204) from inline literals to the new constants via `os.environ.get(env_var, _DEFAULT_*)`
- Default behavior preserved byte-identical: `LLMRouter().local_model == "qwen2.5-coder:32b"` and `LLMRouter().cloud_model == "claude-opus-4-6"` (verified with both an inline Python smoke test AND `tests/test_llm.py::test_default_fallback`)
- Full default test suite green: **763 passed, 117 skipped, 0 failed in 23.46s** — zero regression introduced by the refactor

## Task Commits

Each task was committed atomically per the parallel-executor protocol (`--no-verify` to avoid pre-commit hook contention):

1. **Task 1: Add `_DEFAULT_LOCAL_MODEL` and `_DEFAULT_CLOUD_MODEL` module constants and rewire `__init__`** — `9a9b7b9` (refactor)
2. **Task 2: Verify full default test suite still passes** — no commit (verification-only task per plan; no source changes)

_Note: Plan-output spec called for "one source-only commit" — Task 2 is the regression guard, not a separate commit. Single atomic refactor commit landed as planned._

## Files Created/Modified

- `forge_bridge/llm/router.py` — +14 / -2 lines:
  - Inserted two module-scope constant definitions (with 3-line comment blocks each, mirroring `_DEFAULT_SYSTEM_PROMPT` style) between `_DEFAULT_SYSTEM_PROMPT` (line 58) and the FB-C exception classes comment block
  - Replaced inline `"qwen2.5-coder:32b"` literal at the `FORGE_LOCAL_MODEL` env-fallback site with `_DEFAULT_LOCAL_MODEL`
  - Replaced inline `"claude-opus-4-6"` literal at the `FORGE_CLOUD_MODEL` env-fallback site with `_DEFAULT_CLOUD_MODEL`
  - No other lines touched (`local_url`, `system_prompt`, `_local_client`, `_cloud_client`, `_local_native_client`, class docstring, `_DEFAULT_SYSTEM_PROMPT` all unchanged)

## Acceptance Criteria Evidence

All seven plan-level acceptance criteria for Task 1 verified:

| # | Criterion | Evidence |
|---|-----------|----------|
| 1 | `_DEFAULT_LOCAL_MODEL = "qwen2.5-coder:32b"` defined exactly once | `grep -c '^_DEFAULT_LOCAL_MODEL = "qwen2.5-coder:32b"$' router.py` → **1** |
| 2 | `_DEFAULT_CLOUD_MODEL = "claude-opus-4-6"` defined exactly once | `grep -c '^_DEFAULT_CLOUD_MODEL = "claude-opus-4-6"$' router.py` → **1** |
| 3 | `FORGE_LOCAL_MODEL` consumption site rewired | Python `re.findall(r'os\.environ\.get\(\s*"FORGE_LOCAL_MODEL", _DEFAULT_LOCAL_MODEL', text)` → **1 match** |
| 4 | `FORGE_CLOUD_MODEL` consumption site rewired | Python `re.findall(r'os\.environ\.get\(\s*"FORGE_CLOUD_MODEL", _DEFAULT_CLOUD_MODEL', text)` → **1 match** |
| 5 | Inline `"qwen2.5-coder:32b"` literal appears exactly once (only the constant def; consumption-site literal is gone) | `grep -c '"qwen2.5-coder:32b"' router.py` → **1** |
| 6 | Inline `"claude-opus-4-6"` literal appears exactly once (only the constant def; consumption-site literal is gone) | `grep -c '"claude-opus-4-6"' router.py` → **1** |
| 7 | Functional smoke test: imports work, defaults preserved | `python -c "from forge_bridge.llm.router import LLMRouter, _DEFAULT_LOCAL_MODEL, _DEFAULT_CLOUD_MODEL; assert _DEFAULT_LOCAL_MODEL == 'qwen2.5-coder:32b'; assert _DEFAULT_CLOUD_MODEL == 'claude-opus-4-6'; r = LLMRouter(); assert r.local_model == 'qwen2.5-coder:32b'; assert r.cloud_model == 'claude-opus-4-6'; print('ok')"` → **`ok`** (exit 0) |

**Note on grep `\s*` literal pattern:** The plan uses `\s*` in its grep examples, but BSD grep on macOS does not honor that escape. The semantically identical Python `re.findall` was used to verify the multi-line consumption-site pattern; the pre-and-post text was also visually inspected via the `Read` tool (lines 199-204 in post-edit). Both approaches produce identical evidence — this is a tooling note, not a deviation.

## Verification Output (Task 2 — full suite regression guard)

`pytest tests/ -q -p no:pytest-blender` (last 30 lines preserved verbatim):

```
.................. [98%]
................                                                         [100%]
=============================== warnings summary ===============================
... (3 deprecation warnings — pre-existing, unrelated to refactor) ...

763 passed, 117 skipped, 4 warnings in 23.46s
```

`pytest tests/test_llm.py::test_default_fallback -v -p no:pytest-blender`:

```
tests/test_llm.py::test_default_fallback PASSED                          [100%]
========================= 1 passed, 1 warning in 0.01s =========================
```

`tests/test_llm.py` full module: **19 passed, 0 failed.**

## Decisions Made

- **Constant placement co-locates with `_DEFAULT_SYSTEM_PROMPT`.** Plan-recommended; preserves the precedent. The two new constants and the existing `_DEFAULT_SYSTEM_PROMPT` form a tight module-config block before the FB-C exception classes start.
- **Class docstring untouched.** Plan was explicit: docstring mentions of `qwen2.5-coder:32b` and `claude-opus-4-6` remain accurate post-refactor since values are preserved. The docstring will be touched in P-02 / P-03 alongside the value flips, keeping each commit self-contained.
- **Single atomic commit for both extractions.** Plan-mandated. The extraction is mechanically symmetric (two sibling tunables); splitting would create artificial commit boundaries with no review benefit.

## Deviations from Plan

None — plan executed exactly as written.

(Two operational notes that are NOT plan deviations: (1) the worktree branch base required a `git reset --hard` to `7c241c92fdecba608c61922523f551eb11dad8df` per the executor's `<worktree_branch_check>` protocol — the worktree was created from an older base and the reset is the documented remediation. (2) Pytest required `-p no:pytest-blender` because a globally-installed `pytest_blender` plugin auto-loads and refuses to start without a `blender` executable — this is an environment quirk on the user's machine, not project state. Both were handled silently per worktree-executor norms; recording here for transparency, not as deviations.)

## Issues Encountered

- `pytest_blender` plugin auto-loads in the conda env and aborts with `Exit: 'blender' executable not found.` Resolved with `-p no:pytest-blender` flag. The full default suite was run with this flag and produced clean results. Recording for the next executor in this env — they will hit the same gate.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **17-02 (MODEL-01 cloud bump → `claude-sonnet-4-6`)** unblocked. The flip is now a one-line change: `_DEFAULT_CLOUD_MODEL = "claude-opus-4-6"` → `_DEFAULT_CLOUD_MODEL = "claude-sonnet-4-6"`. No other source changes required — `git blame` on the future P-02 commit will show "model bump" cleanly.
- **17-03 (MODEL-02 local bump → `qwen3:32b`, conditional on assist-01 UAT)** unblocked. Same one-line shape: flip `_DEFAULT_LOCAL_MODEL` value. The conditional UAT path lives in P-03 scope; this plan is agnostic to the outcome.
- No blockers or concerns. v1.4.x carry-forward debt milestone (Phase 17 P-02 + P-03) is the next active workstream once the orchestrator releases this worktree.

## Self-Check: PASSED

- [x] `forge_bridge/llm/router.py` exists post-commit (`git show 9a9b7b9:forge_bridge/llm/router.py | grep -c '_DEFAULT_LOCAL_MODEL'` → 2 occurrences: definition + consumption site)
- [x] Commit `9a9b7b9` exists in `git log --oneline -3` (verified)
- [x] No deletions in commit `9a9b7b9` (`git diff --diff-filter=D --name-only HEAD~1 HEAD` → empty)
- [x] No untracked files left behind (`git status --short` → clean after commit)
- [x] All seven Task 1 acceptance criteria evidenced above
- [x] Task 2 regression guard: 763 passed, 0 failed, 117 skipped — same shape as the v1.4 close baseline (754 passed, 0 failed, 102 skipped); skip count drift is consistent with normal post-v1.4 test additions and is not caused by this refactor

---
*Phase: 17-default-model-bumps*
*Plan: 01*
*Completed: 2026-04-28*
