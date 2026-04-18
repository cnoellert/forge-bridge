---
phase: 06-learning-pipeline-integration
plan: 04
subsystem: consumer-integration
tags: [projekt-forge, consumer-wiring, llm-router, execution-log, synthesizer, pre-synthesis-hook, storage-callback, v1.1.0]
requires:
  - forge_bridge >= 1.1.0 (ExecutionRecord, StorageCallback, PreSynthesisContext, PreSynthesisHook, LLMRouter, ExecutionLog, SkillSynthesizer)
  - forge-bridge v1.1.0 git tag on origin (created by plan 06-03 Task 3)
  - projekt_forge.config.forge_config.load_forge_config (existing YAML loader)
provides:
  - projekt_forge.learning.wiring.init_learning_pipeline(args) — consumer orchestrator
  - projekt_forge.learning.wiring.get_execution_log / get_synthesizer / get_router — accessors
  - projekt_forge.learning.wiring._persist_execution — async storage callback (EXT-03 stub)
  - projekt_forge.learning.wiring._build_pre_synthesis_context — async pre-synthesis hook
  - tests/test_learning_wiring.py — 8 tests (6 wiring + SC #1 + SC #4)
affects:
  - projekt_forge/__main__.py — _run_mcp_only and _run_mcp_server lifecycles now call init_learning_pipeline
  - projekt_forge/pyproject.toml — forge-bridge pin @v1.0.1 → @v1.1.0; tool.hatch.metadata.allow-direct-references = true added
tech-stack:
  added:
    - "forge-bridge 1.1.0 (upgrade from 1.0.1 — pulls in Phase 6 hook APIs)"
  patterns:
    - "Constructor injection at startup (Phase 4 pattern extended end-to-end)"
    - "Module-level _state dict populated by init_learning_pipeline (test-introspectable)"
    - "try/except-log-warning wrapper around init (T-06-16 DoS mitigation — MCP starts regardless)"
    - "async storage callback via fire-and-forget asyncio.ensure_future (forge-bridge 06-01 contract)"
    - "async pre_synthesis_hook returns frozen PreSynthesisContext (forge-bridge 06-02 contract)"
key-files:
  created:
    - /Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/learning/__init__.py
    - /Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/learning/wiring.py
    - /Users/cnoellert/Documents/GitHub/projekt-forge/tests/test_learning_wiring.py
  modified:
    - /Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/__main__.py
    - /Users/cnoellert/Documents/GitHub/projekt-forge/pyproject.toml
decisions:
  - "EXT-03 SQL backend stays deferred — _persist_execution is a logger-only stub. ExecutionRecord contract (D-03) is stable; only the callback body swaps when EXT-03 lands in v1.1.x. Documented verbatim in the _persist_execution docstring so a future implementer sees the migration path."
  - "forge-bridge pin stays in PEP 508 direct-reference form (@ git+https://...@v1.1.0) per REQUIREMENTS.md §Out of Scope — PyPI publishing deferred. A PEP 440 version spec would fail to resolve because no forge-bridge release exists on PyPI."
  - "Added [tool.hatch.metadata] allow-direct-references = true to projekt-forge pyproject.toml (Rule 3 auto-fix). Was flagged as follow-up in Plan 05-04 decisions; Plan 06-04's pip install -e . prerequisite made it blocking. Long-term fix instead of the 05-04 workaround (install from git tag directly)."
  - "Async tests in tests/test_learning_wiring.py carry explicit @pytest.mark.asyncio decorators. projekt-forge runs pytest-asyncio in strict mode (pyproject.toml configfile sets asyncio_mode=Mode.STRICT implicitly since no override). Bare async def test_... would have been uncollected."
  - "SC #4 test patches module-level forge_bridge.learning.synthesizer._dry_run (confirmed by inspection of installed 1.1.0 source), not synth._dry_run (not an instance attribute). End-to-end assertion unchanged: hook-injected constraint reaches acomplete's system= kwarg."
metrics:
  duration: "~25 minutes (projekt-forge edits + v1.1.0 install + test cycle + hatchling fix)"
  completed: "2026-04-18"
  tasks_complete: 4_of_4
  checkpoint_pending: false
  checkpoint_approved_by: cnoellert
  checkpoint_approved_at: "2026-04-18"
---

# Phase 6 Plan 04: Consumer wiring — projekt-forge consumes forge-bridge v1.1.0 learning pipeline

**One-liner:** projekt-forge's startup now constructs forge-bridge's LLMRouter + ExecutionLog + SkillSynthesizer from `forge_config.yaml`, registers an async storage callback, and installs a pre_synthesis_hook — closing Phase 6 end-to-end pending human verification.

## What Shipped

Three atomic commits in **projekt-forge** (external repo, normal commits on main), plus this SUMMARY on the forge-bridge worktree.

### Task 1 — `438b2a1` — New `projekt_forge.learning.wiring` module + pin bump

- **`projekt_forge/learning/__init__.py`** (new): package marker + docstring.
- **`projekt_forge/learning/wiring.py`** (new, 244 lines): the full consumer-side wiring:
  - `_build_llm_router(cfg)` — reads `cfg["llm"]` keys (all optional), passes `None` to `LLMRouter(...)` so the router's own env/default chain handles missing keys.
  - `_resolve_log_path(cfg)` — priority: `cfg["learning"]["log_path"]` > `$FORGE_PROJECT_ROOT/.forge/executions.jsonl` > `~/.forge-bridge/executions.jsonl` (D-15/D-16).
  - `_build_execution_log(cfg)` — constructs `ExecutionLog(log_path=..., threshold=...)`.
  - `async _persist_execution(record)` — storage callback. Logger-only stub; EXT-03 SQL migration path documented in-line.
  - `async _build_pre_synthesis_context(intent, params)` — returns `PreSynthesisContext(constraints=["do not import flame"], tags=[f"project:{FORGE_PROJECT_CODE}"] if env set else [])`.
  - `init_learning_pipeline(args)` — public orchestrator. Tolerates `load_forge_config` RuntimeError (falls through to env/defaults). Populates module-level `_state` dict.
  - Accessors: `get_router`, `get_execution_log`, `get_synthesizer`, `_reset_for_testing`.
- **`pyproject.toml`**:
  - forge-bridge pin bumped `@v1.0.1` → `@v1.1.0` (git-URL form preserved; no PEP 440 conversion).
  - **[Rule 3 auto-fix]** Added `[tool.hatch.metadata]` block with `allow-direct-references = true`. Hatchling refused to build metadata for a direct-reference dependency without this flag, blocking `pip install -e .`. This was flagged in Plan 05-04 as a future packaging fix; became unavoidable here.
- Reinstalled in the projekt-forge virtualenv: `forge-bridge 1.1.0` verified in site-packages.

### Task 2 — `13e5c76` — `__main__.py` lifecycle wiring

- Inserted a 5-line try/except block in both `_run_mcp_only` and `_run_mcp_server`, AFTER `configure(...)` and BEFORE `from projekt_forge.server.mcp import mcp`.
- Block imports `init_learning_pipeline` from the Task 1 module and invokes it. On any exception, logs `"learning pipeline init failed — continuing without it"` and continues — MCP server startup is not blocked by learning-pipeline failure (T-06-16 mitigation).
- AST verification: both functions' bodies contain `init_learning_pipeline`. Grep gates: exactly 2 hits for each of the three required patterns.

### Task 3 — `ac15cc3` — 8 tests, all green

New file `tests/test_learning_wiring.py` (278 lines). Autouse fixture resets `_state` before and after every test.

| # | Test | Assertion |
|---|------|-----------|
| 1 | `test_init_learning_pipeline_with_config` | Config values flow to router + log; accessors return the same instances. |
| 2 | `test_init_learning_pipeline_tolerates_missing_config` | `load_forge_config` raising `RuntimeError` does not crash init; log path falls back to `FORGE_PROJECT_ROOT/.forge/executions.jsonl`. |
| 3 | `test_init_registers_storage_callback` | `log.record(...)` + `asyncio.sleep(0)` → `"execution mirrored"` appears in caplog at INFO under `projekt_forge.learning.wiring`. |
| 4 | `test_pre_synthesis_hook_returns_projekt_forge_context` | `ctx.constraints == ["do not import flame"]`. |
| 5 | `test_pre_synthesis_hook_adds_project_tag_from_env` | `FORGE_PROJECT_CODE=ACM_12345` → `"project:ACM_12345" in ctx.tags`. |
| 6 | `test_synthesizer_constructed_with_router_and_hook` | `synth._router is get_router()`; `synth._pre_synthesis_hook is _build_pre_synthesis_context`. |
| 7 | **SC #1** — `test_two_execution_logs_at_different_paths_are_isolated` | Two `ExecutionLog`s at different paths keep independent `_counters` dicts and independent JSONL files — validates D-16 naming-discipline invariant without needing two live processes. |
| 8 | **SC #4** — `test_enriched_prompt_reaches_acomplete_end_to_end` | Builds real pipeline via `init_learning_pipeline()`, mocks `router.acomplete` + `synthesizer._dry_run` module-level, runs `await synth.synthesize(...)`, captures the `system=` kwarg, asserts `"do not import flame"` is present. Proves the hook-injected constraint propagates end-to-end. |

Local test run: **`8 passed, 1 warning in 0.03s`**. Full projekt-forge suite: **`422 passed, 3 xfailed`** — RWR-04 guard still satisfied (v1.1.0 resolves to site-packages).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocker] Added `tool.hatch.metadata.allow-direct-references = true` to projekt-forge pyproject.toml**

- **Found during:** Task 1 — `pip install -e .` with the new `@v1.1.0` pin.
- **Issue:** Hatchling raised `ValueError: Dependency #15 of field project.dependencies cannot be a direct reference unless field tool.hatch.metadata.allow-direct-references is set to true`.
- **Context:** Plan 05-04 decisions already flagged this as a follow-up ("projekt-forge pyproject.toml missing `tool.hatch.metadata.allow-direct-references = true`") and worked around it by installing forge-bridge from git tag directly. Plan 06-04's verification required `pip install -e .` to actually resolve the bumped pin, so the long-term fix became unavoidable.
- **Fix:** Added 6-line `[tool.hatch.metadata]` block with the flag. No other pyproject.toml changes.
- **Files modified:** `/Users/cnoellert/Documents/GitHub/projekt-forge/pyproject.toml`
- **Commit:** `438b2a1` (bundled with the pin bump and wiring module — atomic task commit).

**2. [Rule 1 - Bug in plan's test snippet] Added `@pytest.mark.asyncio` to async tests**

- **Found during:** Task 3 — test file author was about to write bare `async def test_...`.
- **Issue:** The plan's inline test source used `async def test_...` without decorators, implicitly assuming `asyncio_mode = auto`. projekt-forge has **no** `asyncio_mode` override, so pytest-asyncio 1.3.0 runs in default strict mode — bare async tests are skipped/uncollected silently.
- **Fix:** Added `@pytest.mark.asyncio` to the 4 async tests (tests 3, 4, 5, 8).
- **Files modified:** `/Users/cnoellert/Documents/GitHub/projekt-forge/tests/test_learning_wiring.py`
- **Commit:** `ac15cc3`

**3. [Rule 1 - Bug in plan's test snippet] Patched `_dry_run` at module scope, not instance scope**

- **Found during:** Task 3 SC #4 test — `patch.object(synth, "_dry_run", ...)` raised `AttributeError: ... does not have the attribute '_dry_run'`.
- **Issue:** The plan's snippet assumed `_dry_run` was an instance method on `SkillSynthesizer`. Inspection of the installed forge-bridge 1.1.0 source (`forge_bridge/learning/synthesizer.py`) shows `_dry_run` is a **module-level function** imported and called as `if not await _dry_run(fn_code, fn_name):`.
- **Fix:** Replaced `patch.object(synth, "_dry_run", ...)` with `patch("forge_bridge.learning.synthesizer._dry_run", _fake_dry_run)` where `_fake_dry_run` is a local async stub returning `True` (dry-run success). Same end-to-end invariant, correct target.
- **Files modified:** `/Users/cnoellert/Documents/GitHub/projekt-forge/tests/test_learning_wiring.py`
- **Commit:** `ac15cc3`

No architectural-level (Rule 4) deviations.

## Scope Note — ROADMAP SC #3 "projekt-forge's storage"

**Per plan Task 4 and CONTEXT.md §Out of Scope, the SUMMARY must propagate this verbatim or in equivalent words:**

> Phase 6 delivers storage as the projekt-forge log stream (logger-only stub in `_persist_execution`). EXT-03 upgrades this to a DB write in v1.1.x per CONTEXT.md §Out of scope and REQUIREMENTS.md §Future. The `ExecutionRecord` contract is stable; only the callback body swaps.

Concretely: SC #3 ("An execution routed through projekt-forge fires the storage callback and the event appears in projekt-forge's storage, not only in the JSONL file") is satisfied for Phase 6 by `_persist_execution` emitting an INFO log line (`"execution mirrored: code_hash=... intent=... promoted=..."`) under logger `projekt_forge.learning.wiring`. When EXT-03 lands, replace the body of `_persist_execution` with a `session.add + commit`; the stable `ExecutionRecord` contract (D-03) means no plumbing changes are required at the boundary.

## Verification Results

- [x] `grep '@v1\.1\.0' pyproject.toml` → 1 match
- [x] `grep '@v1\.0\.1' pyproject.toml` → 0 matches (old tag gone)
- [x] `grep 'forge-bridge>=' pyproject.toml` → 0 matches (git-URL form preserved)
- [x] `grep 'forge-bridge @ git+https' pyproject.toml` → 1 match
- [x] `git ls-remote --tags ... v1.1.0` → returns `df972506... refs/tags/v1.1.0` (precondition met)
- [x] `pip show forge-bridge | grep Version` → `Version: 1.1.0`
- [x] `python -c "from projekt_forge.learning.wiring import ...; print('OK')"` → `OK` (all 9 symbols present)
- [x] AST check: both `_run_mcp_only` and `_run_mcp_server` contain `init_learning_pipeline`
- [x] `python -c "import ast; ast.parse(...)"` → parses
- [x] `pytest tests/test_learning_wiring.py -x -v` → 8/8 passed
- [x] `pytest tests/ -x` → 422 passed, 3 xfailed (no regressions; RWR-04 guard green)
- [x] **Task 4 checkpoint (blocking)** — approved by cnoellert on 2026-04-18. Live-startup smoke test in `forge` conda env emitted all 3 expected INFO lines (LLMRouter configured, ExecutionLog configured, learning pipeline initialized); forge-bridge full suite 219 passed; projekt-forge full suite 425 passed once run in the correct env (initial 1 failure in conda `base` was an env gap — `aiosqlite` missing from projekt-forge's declared deps — not a Phase 6 regression).

## Known Stubs

- **`_persist_execution`** (projekt-forge `projekt_forge/learning/wiring.py`): logger-only body. Documented in-line with the exact EXT-03 migration block (`session.add + await session.commit()`). This is a **documented deferred** stub, not an unclosed-loop bug — CONTEXT.md §Out of scope defers EXT-03 to v1.1.x.

## Deferred Issues

None. All plan requirements met; auto-fixes were isolated and complete.

## Self-Check

All items verified during execution:

- [x] `/Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/learning/__init__.py` exists
- [x] `/Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/learning/wiring.py` exists
- [x] `/Users/cnoellert/Documents/GitHub/projekt-forge/tests/test_learning_wiring.py` exists
- [x] Commit `438b2a1` exists on projekt-forge main
- [x] Commit `13e5c76` exists on projekt-forge main
- [x] Commit `ac15cc3` exists on projekt-forge main

## Self-Check: PASSED
