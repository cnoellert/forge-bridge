---
phase: 04-api-surface-hardening
plan: "04"
subsystem: public-api
tags: [api-hardening, barrel-file, public-surface, version-bump, regression-guard]
dependency_graph:
  requires: ["04-01", "04-02", "04-03"]
  provides: [forge_bridge.__all__-11-name-surface, get_mcp-FastMCP-annotation, v1.0.0-version, test_public_api-regression-guards]
  affects: [forge_bridge/__init__.py, forge_bridge/mcp/__init__.py, pyproject.toml, tests/test_public_api.py]
tech_stack:
  added: []
  patterns: [barrel-file-with-grouped-imports, FastMCP-return-annotation, subprocess-grep-regression-guard]
key_files:
  created:
    - tests/test_public_api.py
  modified:
    - forge_bridge/__init__.py
    - forge_bridge/mcp/__init__.py
    - pyproject.toml
    - tests/test_llm.py
decisions:
  - "11-name __all__ declared at forge_bridge root (API-01/D-02): LLMRouter, get_router, ExecutionLog, SkillSynthesizer, register_tools, get_mcp, startup_bridge, shutdown_bridge, execute, execute_json, execute_and_read"
  - "Canonical vocabulary types (Project, Shot, Registry, Role, Status, etc.) intentionally NOT re-exported at root per D-03; import from forge_bridge.core"
  - "get_mcp() -> FastMCP return-type annotation added to forge_bridge/mcp/__init__.py (RESEARCH.md Open-Question #1)"
  - "Version bumped to 1.0.0 in pyproject.toml (PKG-02/D-23); git tag deferred per CONTEXT.md Deferred Ideas"
  - "test_optional_import_guard in test_llm.py fixed to restore forge_bridge.llm.router module reference after reimport (Rule 1 auto-fix for singleton isolation)"
metrics:
  duration: "~20 minutes"
  completed: "2026-04-16T22:00:00Z"
  tasks_completed: 1
  files_modified: 5
requirements_addressed: [API-01, API-04, API-05, PKG-02, PKG-03]
---

# Phase 04 Plan 04: Public API Barrel + Version Bump Summary

11-name `__all__` barrel in `forge_bridge/__init__.py`, `get_mcp() -> FastMCP` type annotation, pyproject.toml version bumped to `1.0.0`, and 13 cross-cutting tests in `tests/test_public_api.py` covering all 5 ROADMAP Phase 4 success criteria.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Wire public API barrel + FastMCP annotation + v1.0.0 + test suite | a79c62d | forge_bridge/__init__.py, forge_bridge/mcp/__init__.py, pyproject.toml, tests/test_public_api.py, tests/test_llm.py |

## What Was Built

### Part A: tests/test_public_api.py (NEW)

13 cross-cutting tests covering API-01, API-04, API-05, PKG-02, PKG-03:

1. `test_public_api_importable` — all 11 names import cleanly from forge_bridge root (ROADMAP SC #1)
2. `test_all_contract` — `set(forge_bridge.__all__) == {11 exact names}`, `len == 11` (D-01, D-02)
3. `test_core_types_not_reexported` — Project, Sequence, Shot, Asset, Version, Media, Stack, Layer, Registry, Role, Status not in `__all__` (D-03)
4. `test_get_mcp_returns_singleton` — `get_mcp() is server.mcp`, idempotent (D-04)
5. `test_lifecycle_renamed_no_alias` — `_startup`/`_shutdown` absent, `startup_bridge`/`shutdown_bridge` present (D-11)
6. `test_startup_bridge_signature` — parameters `['server_url', 'client_name']`, both default `None` (D-12)
7. `test_shutdown_bridge_signature` — zero parameters (D-13)
8. `test_startup_bridge_injection` — injected `server_url` beats env (D-12, async test)
9. `test_server_started_flag_default` — `_server_started is False` on fresh import (D-14)
10. `test_package_version` — `'version = "1.0.0"' in pyproject.toml` (PKG-02/D-23)
11. `test_no_forge_specific_strings` — subprocess grep for `portofino|assist-01|ACM_` returns exit 1 (ROADMAP SC #5)
12. `test_bridge_module_imports_clean` — `forge_bridge.bridge` imports without side-effect errors (D-17/D-18 guard)
13. `test_synthesizer_module_level_synthesize_removed` — no module-level `synthesize()` on synthesizer module (D-19 guard)

### Part B: forge_bridge/__init__.py (REWRITTEN)

Replaced the single-line docstring with the full barrel file:
- Consumer-facing docstring documenting the 11-name public API with `from forge_bridge import (...)` example
- 5 import groups (6 import lines, since learning pipeline uses two statements) with section comments
- `__all__` list with 11 names, grouped by subsystem with comments

### Part C: forge_bridge/mcp/__init__.py (AUGMENTED)

- Added `from __future__ import annotations`
- Added `from mcp.server.fastmcp import FastMCP`
- Changed `def get_mcp():` to `def get_mcp() -> FastMCP:` for Phase 5 type-checker quality

### Part D: pyproject.toml (VERSION BUMP)

`version = "0.1.0"` → `version = "1.0.0"` — single-line edit, no other fields changed.

## Phase 4 Gate Status

All 5 ROADMAP Phase 4 success criteria now have automated tests:

| ROADMAP SC | Test | Location |
|------------|------|----------|
| SC #1 — clean-venv import | `test_public_api_importable` | tests/test_public_api.py |
| SC #2 — LLMRouter no env | `test_router_accepts_injected_config` | tests/test_llm.py (Plan 01) |
| SC #3 — register_tools(source="builtin") | `test_register_tools_builtin_source` | tests/test_mcp_registry.py (Plan 02) |
| SC #4 — register_tools post-run raises | `test_register_tools_post_run_guard` | tests/test_mcp_registry.py (Plan 02) |
| SC #5 — grep portofino/assist-01/ACM_ zero | `test_no_forge_specific_strings` | tests/test_public_api.py |

Phase 4 is complete. Full test suite: **182 passed**.

## Verification Results

All acceptance criteria verified:

- `pytest tests/test_public_api.py -x -v` — 13 passed (all green)
- `pytest tests/ -x --no-header -q` — 182 passed (full suite, zero regressions)
- `python -c "import forge_bridge; assert len(forge_bridge.__all__) == 11"` — exits 0
- `grep -rn "portofino\|assist-01\|ACM_" forge_bridge/ --include="*.py"` — exit 1 (zero matches)
- `grep -c '^version = "1.0.0"' pyproject.toml` — 1
- `grep -n "def get_mcp() -> FastMCP:" forge_bridge/mcp/__init__.py` — match at line 10
- `get_mcp() is server.mcp` — True (singleton identity confirmed)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_optional_import_guard singleton isolation**
- **Found during:** Task 1 (full suite green check)
- **Issue:** `test_optional_import_guard` in `tests/test_llm.py` deleted `forge_bridge.llm.router` from `sys.modules` and reimported it without restoring the original module reference. Our new `forge_bridge/__init__.py` imports from this module, meaning the `get_router` function bound into synthesizer module and the fresh module reference in `sys.modules` were now different module objects. This broke singleton identity: `SkillSynthesizer()._router is not get_router()` when `test_optional_import_guard` ran before `test_router_injection` in the same process.
- **Fix:** Saved `sys.modules.get("forge_bridge.llm.router")` before the test manipulates it, and restored it in the `finally` block after the reimport. The test still exercises the import-without-openai behavior correctly while leaving module state clean for subsequent tests.
- **Files modified:** `tests/test_llm.py` (lines 150-163)
- **Commit:** a79c62d

## Phase 6 Handoff (carried forward from Plan 03)

No call site for `SkillSynthesizer.synthesize` exists in `forge_bridge/bridge.py`. Phase 6 must:
1. Introduce `bridge.set_execution_callback(...)` or equivalent promotion-hook mechanism (LRN-02/D-20)
2. Construct `SkillSynthesizer(router=configured_router)` using projekt-forge's `forge_config.yaml`-derived `LLMRouter` instance
3. Wire the promotion callback so that `bridge.py` fires `SkillSynthesizer(...).synthesize(raw_code, intent, count)` on threshold crossing

The `pre_synthesis_hook` kwarg slot (D-21, LRN-04) is not yet implemented — Phase 6 adds it without breaking the current D-17 shape.

## Release Workflow Note

`pyproject.toml` is at `1.0.0` but no git tag has been created per CONTEXT.md §Deferred Ideas. After `/gsd-verify-work` gives green, the release workflow must:
```bash
git tag -a v1.0.0 -m "forge-bridge v1.0.0 — Phase 4 API surface hardening complete"
git push origin v1.0.0
```
Phase 5's `forge-bridge>=1.0,<2.0` dependency will then resolve correctly.

## Clean-Venv Verification

Not run as a separate step (optional per plan). The `test_public_api_importable` test covers the import surface. The smoke test `python -c "from forge_bridge import LLMRouter, ExecutionLog, register_tools, get_mcp; print('ok')"` passes in the dev environment where `forge-bridge` is installed with `pip install -e .` — confirming the import works with the declared dependencies.

## Standing Regression Guards

Three standing guards established by this plan that prevent Phase 4 decisions from being silently reverted:

1. **`test_no_forge_specific_strings`** — subprocess `grep -r -E "portofino|assist-01|ACM_"` over the entire `forge_bridge/` package. Fires on any commit that re-adds banned forge-specific deployment tokens. This is the whole-package scope per user resolution #1.

2. **`test_all_contract`** — `set(forge_bridge.__all__) == {11 exact names}` plus `len == 11`. Catches both accidental additions (e.g., a private helper leaking in) and removals (e.g., someone deleting a public name without updating `__all__`).

3. **`test_lifecycle_renamed_no_alias`** — asserts `_startup` and `_shutdown` are absent from `forge_bridge.mcp.server`. Prevents anyone from adding backward-compat aliases that violate the D-11 clean break.

## Known Stubs

None.

## Threat Flags

None — this plan creates no new network endpoints, auth paths, file access patterns, or schema changes. The `__init__.py` barrel file exposes an explicit stable surface (T-04-15 mitigated by `test_all_contract`). The `test_no_forge_specific_strings` subprocess grep is the standing T-04-16 regression guard.

## Self-Check: PASSED

- `tests/test_public_api.py`: FOUND
- `forge_bridge/__init__.py`: FOUND, contains `__all__ = [`
- `forge_bridge/mcp/__init__.py`: FOUND, contains `def get_mcp() -> FastMCP:`
- `pyproject.toml`: FOUND, contains `version = "1.0.0"`
- `tests/test_llm.py`: FOUND (modified)
- Commit a79c62d: FOUND
- 182 tests passing: CONFIRMED
