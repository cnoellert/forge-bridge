---
phase: 04-api-surface-hardening
plan: "01"
subsystem: llm-router
tags: [api-hardening, config-injection, env-cleanup, prompt-scrub]
requires: []
provides: [LLMRouter-injected-config, generic-system-prompt, publish-env-default]
affects: [forge_bridge.llm.router, forge_bridge.tools.publish, tests.test_llm]
tech_stack:
  added: []
  patterns: [arg-env-default-precedence, default_factory-deferred-env-read]
key_files:
  created: []
  modified:
    - forge_bridge/llm/router.py
    - forge_bridge/tools/publish.py
    - tests/test_llm.py
decisions:
  - "D-08 REMOVE: Module-level LOCAL_BASE_URL/LOCAL_MODEL/CLOUD_MODEL/SYSTEM_PROMPT constants deleted; env reads moved inside __init__"
  - "D-10: _DEFAULT_SYSTEM_PROMPT rewritten to remove portofino, assist-01, ACM_, flame-01, Backburner, cmdjob — only generic Flame API context retained"
  - "D-09 unchanged: get_router() singleton remains env-only (zero-config ambient path)"
  - "R-1: publish.py output_directory uses default_factory for deferred env read, consistent with D-06 philosophy"
  - "No test_tools.py edits required: no existing test asserted on /mnt/portofino literal"
metrics:
  duration_minutes: 15
  completed: "2026-04-16T21:13:24Z"
  tasks_completed: 2
  files_modified: 3
---

# Phase 04 Plan 01: LLMRouter Config Injection and Prompt Scrub Summary

Refactored `LLMRouter` to accept injected config via constructor kwargs (API-02), purged forge-specific deployment strings from the default system prompt and docstrings (PKG-03), removed module-level env-read constants (D-08 REMOVE), and generalized `publish.py` output_directory to use `FORGE_PUBLISH_ROOT` env var with `/mnt/publish` fallback (R-1).

## What Was Built

### Task 1: LLMRouter Injected Config (TDD)

**RED:** Replaced `test_env_var_override` (importlib.reload anti-pattern) with 5 new tests covering D-05/D-06/D-10 behaviors. Tests failed as expected — `LLMRouter` did not accept kwargs.

**GREEN:** Rewrote `forge_bridge/llm/router.py`:

- `__init__` now accepts `local_url`, `local_model`, `cloud_model`, `system_prompt` kwargs with `arg → env → hardcoded default` precedence (D-05, D-06)
- Removed module-level constants `LOCAL_BASE_URL`, `LOCAL_MODEL`, `CLOUD_MODEL`, `SYSTEM_PROMPT` entirely (D-08 REMOVE per user resolution #3)
- `_DEFAULT_SYSTEM_PROMPT` retained as module-level name (it is the hardcoded default, not an env-backed constant)
- Rewrote `_DEFAULT_SYSTEM_PROMPT` body: removed `portofino`, `assist-01`, `ACM_`, `flame-01`, `Backburner`, `cmdjob`, DB credentials, machine specs — kept Flame version, `import flame` note, shot-naming convention, openclip bracket notation, tone (D-10)
- Updated 6 attribute read sites in `ahealth_check`, `_get_local_client`, `_async_local`, `_async_cloud` to use `self.*` instead of module constants
- Scrubbed docstrings: module docstring, usage example (`ACM_` → `PROJ_`), class docstring (`assist-01` → `local Ollama`), env-override table (URL default updated to `localhost`) per user resolution #1
- `get_router()` singleton unchanged (D-09)

### Task 2: publish.py output_directory Generalization

Edited `forge_bridge/tools/publish.py`:

- Added `import os` at top of file
- Replaced `default="/mnt/portofino"` with `default_factory=lambda: os.environ.get("FORGE_PUBLISH_ROOT", "/mnt/publish")` in `PublishSequence.output_directory`
- Defers env read to instance construction (consistent with D-06 philosophy)
- No `tests/test_tools.py` edits required — no existing test asserted on the old `/mnt/portofino` literal

## Verification Results

All 5 plan verification checks passed:

1. `pytest tests/test_llm.py -x -v` — 12 passed (including 5 new D-05/D-06/D-10 tests)
2. `pytest tests/test_tools.py -x -v` — 10 passed (zero regressions)
3. `grep -rn "portofino|assist-01|ACM_|flame-01" forge_bridge/llm/router.py forge_bridge/tools/publish.py` — exit 1 (zero matches)
4. Injection smoke: `LLMRouter(local_url='http://x', local_model='m', ...).local_url` prints `http://x`
5. All `os.environ` calls in `router.py` are inside function bodies only — no module-top reads remain

## Deviations from Plan

None — plan executed exactly as written.

## Additional Notes

- `_DEFAULT_SYSTEM_PROMPT` is confirmed retained as a module-level name (it is in the D-08 keep list, only the env-backed constants were removed)
- `LLMRouter()` with no args constructs cleanly for `get_router()` consumers (D-09 path confirmed working via `test_default_fallback` and `test_acomplete_is_coroutine`)
- The `test_optional_import_guard`, `test_health_check_shape`, `test_llm_shim_import`, `test_llm_package_structure`, `test_acomplete_is_coroutine`, `test_complete_sync_wrapper`, `test_health_resource_registered` all still pass — no regressions

## Known Stubs

None.

## Threat Flags

None — changes are internal refactors only. No new network endpoints, auth paths, or file access patterns introduced. T-04-02 (information disclosure via `_DEFAULT_SYSTEM_PROMPT`) and T-04-03 (information disclosure via `/mnt/portofino`) are both mitigated as planned.

## Self-Check: PASSED

- `forge_bridge/llm/router.py` exists and contains `def __init__(self, local_url: str | None = None`
- `forge_bridge/tools/publish.py` exists and contains `default_factory=lambda: os.environ.get("FORGE_PUBLISH_ROOT"`
- `tests/test_llm.py` exists and contains `def test_env_fallback_at_init_time`
- Commits verified: `68b9725` (RED tests), `f82cb2f` (GREEN router), `2e8c551` (publish.py)
