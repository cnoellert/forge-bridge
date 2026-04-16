---
phase: 04-api-surface-hardening
plan: "03"
subsystem: learning-pipeline
tags: [refactor, dependency-injection, tdd, api-hardening]
dependency_graph:
  requires: []
  provides: [SkillSynthesizer class at forge_bridge.learning.synthesizer]
  affects: [forge_bridge/learning/synthesizer.py, tests/test_synthesizer.py]
tech_stack:
  added: []
  patterns: [dependency-injection, eager-fallback-at-init, class-wrapping-prior-module-state]
key_files:
  created: []
  modified:
    - forge_bridge/learning/synthesizer.py
    - tests/test_synthesizer.py
decisions:
  - "Eager fallback at init (self._router = router or get_router()) chosen over lazy-fallback-at-call per PATTERNS.md recommendation; get_router() is itself lazy so no premature construction happens at import time"
  - "D-20 deferred to Phase 6 per user resolution #2: no bridge.py call site exists for synthesize() today; Phase 6 must wire promotion hook alongside LRN-02 set_execution_callback work"
metrics:
  duration: "~10 minutes"
  completed: "2026-04-16T21:12:46Z"
  tasks_completed: 1
  files_modified: 2
---

# Phase 4 Plan 03: SkillSynthesizer Class Introduction Summary

SkillSynthesizer class with injected router and synthesized_dir kwargs, removing module-level synthesize() per D-17/D-18/D-19 clean-break.

## What Was Built

Promoted the module-level `async def synthesize(...)` function in `forge_bridge/learning/synthesizer.py` into an instance method of a new `SkillSynthesizer` class. The class accepts optional `router` (LLMRouter) and `synthesized_dir` (Path) constructor kwargs, enabling Phase 6 to inject projekt-forge's `LLMRouter` instance without monkeypatching.

The module-level `synthesize()` function was removed entirely per D-19 (clean break, no backward-compat alias). All 6 existing `TestSynthesize` test methods were migrated to `TestSkillSynthesizer` using direct injection, eliminating all `monkeypatch.setattr` and `patch()` usage from those tests.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| RED | Failing tests for SkillSynthesizer | 06315ef | tests/test_synthesizer.py |
| GREEN | SkillSynthesizer implementation | 266aff8 | forge_bridge/learning/synthesizer.py |

## Key Decisions

1. **Eager fallback at init** — `self._router = router if router is not None else get_router()` runs at `__init__` time, not at first `synthesize()` call. Per PATTERNS.md recommendation: `get_router()` is itself lazy (returns cached singleton or constructs it), so no premature LLM client construction happens at module import time, only at `SkillSynthesizer()` construction time. This matches the `ExecutionLog.__init__` pattern already established in Phase 3.

2. **D-20 deferred to Phase 6** — No call site for `synthesize()` exists in `forge_bridge/bridge.py` (confirmed by grep; noted in RESEARCH.md §Open-Question #2). User resolution #2 explicitly approved this deferral. Phase 6 must introduce `bridge.set_execution_callback(...)` firing `SkillSynthesizer().synthesize(...)` alongside LRN-02's promotion-hook wiring.

## Test Count Before vs. After

| File | Before | After | Delta |
|------|--------|-------|-------|
| tests/test_synthesizer.py | 17 tests | 20 tests | +3 |

New tests added:
- `TestSkillSynthesizer::test_router_injection` — D-17 router kwarg stored on self, None falls back to get_router()
- `TestSkillSynthesizer::test_synth_dir_injection` — D-17 synthesized_dir kwarg stored on self, None falls back to SYNTHESIZED_DIR
- `test_module_level_synthesize_removed` — D-19 regression guard (module-level function gone)

## Deviations from Plan

None — plan executed exactly as written.

## Phase 6 Handoff (D-20)

No call site for `SkillSynthesizer.synthesize` exists in `forge_bridge/bridge.py`. Phase 6 must:
1. Introduce `bridge.set_execution_callback(...)` or equivalent promotion-hook mechanism (LRN-02)
2. Construct `SkillSynthesizer(router=configured_router)` using projekt-forge's `forge_config.yaml`-derived `LLMRouter` instance
3. Wire the promotion callback so that `bridge.py` fires `SkillSynthesizer(...).synthesize(raw_code, intent, count)` on threshold crossing

The `pre_synthesis_hook` kwarg slot (D-21, LRN-04) reserved in the constructor signature is not yet implemented — Phase 6 adds it without breaking the current D-17 shape.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. The existing three-stage validation chain (T-04-11: `_extract_function` → `_check_signature` → `_dry_run`) is preserved intact. Trust boundary between downstream caller and `SkillSynthesizer.__init__` (T-04-12/T-04-13) is unchanged from pre-Phase-4 behavior — only the call sites moved from module scope to instance method.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| forge_bridge/learning/synthesizer.py | FOUND |
| tests/test_synthesizer.py | FOUND |
| 04-03-SUMMARY.md | FOUND |
| Commit 06315ef (RED) | FOUND |
| Commit 266aff8 (GREEN) | FOUND |
| 20 tests passing | PASSED |
