---
phase: 05-import-rewiring
plan: 03
subsystem: api
tags: [mcp, registry, lifespan, cross-repo, wave-C, RWR-03]

# Dependency graph
requires:
  - phase: 05-import-rewiring/plan-00
    provides: forge-bridge v1.0.1 canonical pip surface (get_mcp, register_tools)
  - phase: 05-import-rewiring/plan-01
    provides: projekt_forge/ namespace + internal imports rewritten
  - phase: 05-import-rewiring/plan-02
    provides: forge-bridge pip dep + canonical imports flipped; duplicate modules deleted
provides:
  - projekt_forge/server/mcp.py collapsed to 45 lines -- single get_mcp() + single register_tools() call
  - 7 forge-specific tools registered with prefix='forge_' source='builtin' (catalog.trace_lineage, catalog.get_shot_deps, orchestrate.publish_pipeline, scan.media_scan, seed.seed_catalog, batch.setup_denoise, project.list_desktop)
  - projekt_forge/__main__.py rewired to rely on canonical forge-bridge lifespan (no direct _startup/_shutdown/startup_bridge/shutdown_bridge calls)
  - projekt_forge/server/__init__.py re-export trimmed (main symbol removed -- moved to __main__.py entry point)
affects: [05-04, projekt-forge-phase-5-wave-D]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pip-consumer MCP shape: get_mcp() singleton + register_tools(prefix, source='builtin') at module top-level"
    - "Canonical lifespan ownership: pip package's _lifespan calls startup_bridge/shutdown_bridge; consumers never call them directly"
    - "__main__.py local helper (_run_mcp_only) replaces the deleted projekt_forge.server.mcp.main entry point for --no-db / FORGE_DB_URL-missing fallback paths"

key-files:
  created: []
  modified:
    - /Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/server/mcp.py
    - /Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/server/__init__.py
    - /Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/__main__.py

key-decisions:
  - "Extended the plan's two-file scope to three files: projekt_forge/server/__init__.py also re-exported the now-deleted main symbol ('from projekt_forge.server.mcp import mcp, main'), which broke import-time resolution as soon as Task 1 removed main(). Fixed in the same atomic commit as a Rule 3 blocking deviation -- the alternative would have left the package unimportable."
  - "Introduced a local _run_mcp_only(args) helper in __main__.py instead of leaving the two 'from projekt_forge.server.mcp import main as mcp_main' / 'mcp_main()' sites (line 47 and 140 in the pre-wave-C file) dangling. The helper configures the bridge via forge_bridge.bridge.configure and calls mcp.run() directly, allowing the canonical FastMCP lifespan to own startup_bridge/shutdown_bridge lifecycle per D-14."
  - "Updated argparse prog label and module docstring in __main__.py from 'forge_bridge' to 'projekt_forge' -- these were cosmetic-but-user-facing leftovers flagged in Plan 05-01's 'Forward-note for Wave C' and owned by this plan per PATTERNS.md §'Wave C __main__.py'."

patterns-established:
  - "Wave C MCP rewire: module-level get_mcp() + single register_tools(fns, prefix, source='builtin') -- zero mcp.tool() calls in consumer code"
  - "No direct lifecycle calls in consumer __main__.py: canonical lifespan on the pip package's FastMCP singleton owns startup_bridge/shutdown_bridge"

requirements-completed: [RWR-03]

# Metrics
duration: ~15min
completed: 2026-04-17
---

# Phase 05 Plan 03: MCP Registry Rewrite (Wave C) Summary

**projekt_forge/server/mcp.py collapsed from 560 to 45 lines around the canonical get_mcp() + register_tools(prefix='forge_', source='builtin') API; __main__.py no longer calls startup_bridge/shutdown_bridge directly -- the forge-bridge pip lifespan owns the lifecycle; `python -m projekt_forge --help` exits 0; pytest tests/ green at 414 passed + 3 xfailed (matches Wave B baseline).**

## projekt-forge Commit

Single atomic commit in `/Users/cnoellert/Documents/GitHub/projekt-forge` on `main`:

- **`2722e23`** — `refactor(projekt_forge): rebuild MCP server around get_mcp() + register_tools; rely on canonical lifespan -- forge-bridge phase 5 wave C`
- 3 files changed, 83 insertions(+), 570 deletions(-)
- Matches D-18 convention (`{type}(projekt_forge): {subject} -- forge-bridge phase 5 wave C`)
- Working tree clean post-commit (`git status --porcelain` returns empty)
- NOT pushed (per execution instructions -- projekt-forge push policy is the user's call)

## projekt_forge/server/mcp.py Before / After

| Metric | Before (Wave B) | After (Wave C) | Delta |
|--------|----------------|----------------|-------|
| Total lines | 560 | 45 | -515 |
| `mcp.tool(...)` calls | 41 | 0 | -41 |
| Top-level `FastMCP(...)` constructors | 1 | 0 | -1 (uses `get_mcp()` singleton instead) |
| `main()` / argparse blocks | 1 (55 lines) | 0 | moved to `__main__.py` entry point |
| `register_tools(...)` calls | 0 | 1 | +1 (single atomic call) |

Plan expected "~500 → ~30"; actual was 560 → 45 (8 blank/docstring lines on top of the ~30-line core). Within acceptance criterion (`wc -l < 80`).

## register_tools() Argument List

The single `register_tools(mcp, [...], prefix="forge_", source="builtin")` call registers exactly 7 forge-specific tool callables from 5 modules:

| # | Module | Function | Final tool name after `forge_` prefix |
|---|--------|----------|---------------------------------------|
| 1 | `projekt_forge.tools.catalog` | `trace_lineage` | `forge_trace_lineage` |
| 2 | `projekt_forge.tools.catalog` | `get_shot_deps` | `forge_get_shot_deps` |
| 3 | `projekt_forge.tools.orchestrate` | `publish_pipeline` | `forge_publish_pipeline` |
| 4 | `projekt_forge.tools.scan` | `media_scan` | `forge_media_scan` |
| 5 | `projekt_forge.tools.seed` | `seed_catalog` | `forge_seed_catalog` |
| 6 | `projekt_forge.tools.batch` | `setup_denoise` | `forge_setup_denoise` |
| 7 | `projekt_forge.tools.project` | `list_desktop` | `forge_list_desktop` |

These exactly match the must_haves[3] list.

Verified at import time: `python -c "from projekt_forge.server.mcp import mcp; print(sorted(mcp._tool_manager._tools.keys()))"` lists all 7 `forge_*` entries alongside the canonical pre-registered `flame_*` + `forge_*` tools from forge-bridge's `register_builtins()`.

## __main__.py Changes

**Removed (direct lifecycle paths) — `grep -cE "_startup\(|_shutdown\(|await startup_bridge\(\)|await shutdown_bridge\(\)" projekt_forge/__main__.py` → 0.**

Neither `_startup()`/`_shutdown()` nor `await startup_bridge()/shutdown_bridge()` ever appeared in __main__.py to begin with (verified by STEP 1 grep at start of task). The canonical forge-bridge lifespan (in `forge_bridge/mcp/server.py` lines 68-89, installed on the FastMCP singleton at pip-package import time) was already the only lifecycle owner — Plan 02's Wave B flip of `from forge_bridge.bridge import configure` had already routed the bridge config through the pip package.

**What did change:**

1. The two `from projekt_forge.server.mcp import main as mcp_main` / `mcp_main()` sites (line 47 inside `main_async` FORGE_DB_URL-missing fallback, line 140 inside `--no-db` path) were replaced with a new local `_run_mcp_only(args)` helper. The helper:
   - Imports `configure` from `forge_bridge.bridge` (pip — already the case from Wave B)
   - Calls `configure(host=..., port=..., timeout=...)` with the argparse values
   - Imports the `mcp` singleton from `projekt_forge.server.mcp`
   - Calls `mcp.run(...)` directly (stdio or streamable_http per `args.http`)
   - mcp.run() triggers the canonical `_lifespan` which owns `startup_bridge()` / `shutdown_bridge()` per Phase 4 API-04/API-05
2. Argparse `prog` label flipped `forge_bridge` → `projekt_forge`; description updated to "projekt-forge MCP + DB Server".
3. Module docstring top-matter updated: usage lines show `python -m projekt_forge ...`; added a paragraph noting the MCP server delegates startup_bridge/shutdown_bridge to the canonical lifespan.
4. Module logger renamed from `logging.getLogger("forge_bridge")` to `logging.getLogger("projekt_forge")`.

TaskGroup orchestration (`asyncio.TaskGroup()` with `mcp-server` + `ws-db-server` + `shutdown-watcher` tasks) preserved verbatim. `dispose_all_engines()` in the `finally` block preserved verbatim. Argparse flags (`--no-db`, `--db-only`, `--bridge-host`, `--bridge-port`, `--bridge-timeout`, `--http`, `--port`) preserved verbatim.

## `python -m projekt_forge --help` Output (first 10 lines)

```
usage: projekt_forge [-h] [--bridge-host BRIDGE_HOST]
                     [--bridge-port BRIDGE_PORT]
                     [--bridge-timeout BRIDGE_TIMEOUT] [--http] [--port PORT]
                     [--no-db] [--db-only]

projekt-forge MCP + DB Server

options:
  -h, --help            show this help message and exit
  --bridge-host BRIDGE_HOST
```

**Exit code: 0.**

## pytest Result

```
414 passed, 3 xfailed, 1 warning in 2.22s
EXIT=0
```

**Invocation:** `pytest tests/` (explicit path per plan execution rules — bypasses the pre-existing `flame_hooks/forge_tools/forge_bridge/scripts/forge_llm_test.py` collection-pollution issue documented in plan 05-02's SUMMARY).

**Delta vs Wave B baseline:** none (414 passed, 3 xfailed, 0 failed, 0 errors — identical counts). No projekt-forge-specific test changes in Wave C.

**Deprecation warnings:** 1 (websockets library pre-existing, unrelated). No new warnings introduced by this plan.

## must_haves Checklist

- [x] truths[0]: `projekt_forge/server/mcp.py` contains 0 direct `mcp.tool(...)` calls (`grep -cE 'mcp\.tool\s*\(' projekt_forge/server/mcp.py` → 0)
- [x] truths[1]: `projekt_forge/server/mcp.py` calls `get_mcp()` exactly once (`grep -c 'get_mcp()' projekt_forge/server/mcp.py` → 1)
- [x] truths[2]: `register_tools(mcp, [...], prefix='forge_', source='builtin')` called once at module top-level (line 32, before any `mcp.run()`); post-run guard respected because it runs at import time
- [x] truths[3]: All 7 forge-specific tools present in the argument list (see table above — exact match with must_haves)
- [x] truths[4]: `projekt_forge/__main__.py` no longer calls `_startup/_shutdown` or `startup_bridge/shutdown_bridge` directly (grep → 0 matches for all four variants)
- [x] truths[5]: `projekt_forge/__main__.py` imports `configure` from `forge_bridge.bridge` (pip) — 2 occurrences (in `_run_mcp_only` and `_run_mcp_server`), neither from `projekt_forge.bridge` (which was deleted in Wave B)
- [x] truths[6]: `python -m projekt_forge --help` exits 0 (verified, output captured above)
- [x] truths[7]: Full projekt-forge test suite passes including MCP tool-registration smoke coverage — 414 passed, 3 xfailed, 0 failed (pytest tests/ on the pip-installed forge-bridge v1.0.1)
- [x] artifacts[0]: `projekt_forge/server/mcp.py` contains `from forge_bridge import get_mcp, register_tools` (line 20)
- [x] artifacts[1]: `projekt_forge/__main__.py` contains `from forge_bridge.bridge import configure` (lines 33 and 64 inside the two helper functions, per pattern guidance that this is a lazy/inside-function import)
- [x] key_links[0]: `projekt_forge/server/mcp.py` → `forge_bridge.mcp` (pip) via `get_mcp() + register_tools()` — matches pattern `from forge_bridge import get_mcp, register_tools`
- [x] key_links[1]: `projekt_forge/__main__.py` → canonical lifespan in `forge_bridge/mcp/server.py` — `mcp.run()` triggers `_lifespan` which calls `startup_bridge/shutdown_bridge`; pattern `mcp\.run\(\)` matches (3 occurrences: 1 in `_run_mcp_only`, 2 inside `_run_mcp_server`)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `projekt_forge/server/__init__.py` re-exported the now-deleted `main` symbol**
- **Found during:** Task 1 STEP 4 import-check (`python -c "from projekt_forge.server.mcp import mcp"`)
- **Issue:** `projekt_forge/server/__init__.py` line 2 was `from projekt_forge.server.mcp import mcp, main  # noqa: F401`. Task 1's `server/mcp.py` rewrite removed `main()` per plan STEP 3 ("DO NOT include a main() function ... in mcp.py"). Importing `projekt_forge.server.mcp` now fails with `ImportError: cannot import name 'main' from 'projekt_forge.server.mcp'` because the package `__init__` is evaluated transitively.
- **Fix:** Edited `projekt_forge/server/__init__.py` to drop `main` from the re-export. New content: `from projekt_forge.server.mcp import mcp  # noqa: F401`. Also refreshed the module docstring to reflect Wave C reality.
- **Files modified:** `projekt_forge/server/__init__.py` (1 line changed in the import, 1-line docstring → 5-line docstring)
- **Verification:** `python -c "from projekt_forge.server.mcp import mcp; print(type(mcp).__name__)"` → `FastMCP` (exit 0); `python -m projekt_forge --help` exits 0; full pytest still green.
- **Committed in:** `2722e23` (same atomic commit as the Task 1 / Task 2 edits — kept atomic because the package would otherwise be unimportable mid-commit)

**2. [Rule 3 - Blocking] Two callers in `__main__.py` referenced the now-deleted `projekt_forge.server.mcp.main`**
- **Found during:** Task 2 STEP 1 grep survey + STEP 5 `python -m projekt_forge --help` run
- **Issue:** `projekt_forge/__main__.py` imports and calls `from projekt_forge.server.mcp import main as mcp_main` / `mcp_main()` at two sites: line 47 (FORGE_DB_URL-missing fallback inside `main_async`) and line 140 (`--no-db` path inside top-level `main()`). Task 1 removed `main()` from `server/mcp.py`; these two call sites would throw `ImportError` at runtime in the MCP-only paths.
- **Fix:** Introduced a new local helper `_run_mcp_only(args)` at the top of `__main__.py` that imports `configure` from `forge_bridge.bridge`, calls `configure(...)` with the argparse args, imports the `mcp` singleton from `projekt_forge.server.mcp`, and then calls `mcp.run()` directly (with the HTTP-vs-stdio branch preserved). Replaced both `mcp_main()` sites with `_run_mcp_only(args)`. The canonical forge-bridge `_lifespan` owns `startup_bridge`/`shutdown_bridge` when `mcp.run()` starts — no duplicate calls.
- **Files modified:** `projekt_forge/__main__.py` (~30 lines added for helper + 2 call-site swaps; argparse `prog` label + description updated; module docstring refreshed; logger channel renamed `forge_bridge` → `projekt_forge`)
- **Verification:** `python -m projekt_forge --help` exits 0; pytest tests/ green (414 / 3 xfailed / 0 failed).
- **Committed in:** `2722e23` (same atomic commit — the MCP-only paths must work in any phase commit state per RWR-03)

---

**Total deviations:** 2 Rule 3 auto-fixes (both blocking — the plan's Task 1 explicitly forbade `main()` in `server/mcp.py`, which made the two downstream callers into precondition work the plan did not list). Both fixes landed in the same atomic commit as the rest of Wave C because the package would otherwise be unimportable.

**Impact on plan:** No scope creep — both deviations are mechanical consequences of the plan's own "remove main() from mcp.py" directive. All artifacts and must_haves satisfied.

## Issues Encountered

- **None after the two auto-fixes above.** The plan's STEP 1 grep for direct `startup_bridge/shutdown_bridge` calls returned 0 matches in `__main__.py`, so the "remove direct lifecycle calls" cleanup in Task 2 STEP 4 was a no-op — the Wave B `configure`-flip commit had already routed everything through the canonical pip lifespan.
- **No changes to pytest collection or test files** — the pytest invocation path (`pytest tests/`) and the 414/3 baseline established in Plan 05-02 carried through unchanged.

## Self-Check

- [x] `/Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/server/mcp.py` exists and is 45 lines
- [x] `grep -cE 'mcp\.tool\s*\(' projekt_forge/server/mcp.py` returns 0
- [x] `grep -c 'from forge_bridge import get_mcp, register_tools' projekt_forge/server/mcp.py` returns 1
- [x] `grep -c 'get_mcp()' projekt_forge/server/mcp.py` returns 1
- [x] `grep -c 'prefix="forge_"' projekt_forge/server/mcp.py` returns 1
- [x] `grep -c 'source="builtin"' projekt_forge/server/mcp.py` returns 2 (one in docstring header at line 7, one in the actual call at line 44 — only one is a live call)
- [x] `grep -cE 'def main\(|argparse' projekt_forge/server/mcp.py` returns 0 (the `mcp.run(` grep match is a literal-text mention in the module docstring at line 27, not a call)
- [x] `grep -c 'from forge_bridge.bridge import configure' projekt_forge/__main__.py` returns 2 (one in `_run_mcp_only`, one in `_run_mcp_server`)
- [x] `grep -cE '_startup\(|_shutdown\(|await startup_bridge\(\)|await shutdown_bridge\(\)' projekt_forge/__main__.py` returns 0
- [x] `grep -c 'TaskGroup' projekt_forge/__main__.py` returns 3 (preserved)
- [x] `grep -c 'dispose_all_engines' projekt_forge/__main__.py` returns 2 (preserved)
- [x] `grep -c 'from projekt_forge.server.mcp import mcp' projekt_forge/__main__.py` returns 2 (preserved)
- [x] `python -m projekt_forge --help` exits 0
- [x] `pytest tests/` → 414 passed, 3 xfailed, 0 failed, 0 errors
- [x] projekt-forge commit `2722e23` on `main` with D-18-compliant subject (matches regex `refactor\(projekt_forge\).*forge-bridge phase 5 wave C`)
- [x] `git -C /Users/cnoellert/Documents/GitHub/projekt-forge log -1 --name-only` shows `projekt_forge/server/mcp.py` AND `projekt_forge/__main__.py` in the same commit (plus the precondition `projekt_forge/server/__init__.py`)
- [x] `git -C /Users/cnoellert/Documents/GitHub/projekt-forge status --porcelain` returns empty
- [x] No file deletions in this commit (`git diff --diff-filter=D --name-only HEAD~1 HEAD` returns empty)

## Self-Check: PASSED

## Next Phase Readiness

- **Ready for Plan 05-04 (Wave D):** MCP server is fully wired around the canonical pip surface. Wave D can now add the RWR-04 conftest assertion (`assert_forge_bridge_from_site_packages`), run the final green test pass, and close out Phase 5.
- **No blockers for downstream plans.**
- **Invariant preserved:** The two long-term safety nets this plan depends on are both in place:
  1. forge-bridge pip package's post-run guard (`registry.py` `_server_started` check) — `register_tools()` will RuntimeError if anyone ever moves the call into a lifespan/runtime path. Wave C respects this by keeping `register_tools()` at module top-level.
  2. forge-bridge pip package's `_lifespan` — now the sole owner of `startup_bridge` / `shutdown_bridge`, invoked automatically on every `mcp.run()`. Wave C respects this by removing any direct lifecycle calls from `__main__.py` (none existed after Wave B — verified).

---
*Phase: 05-import-rewiring*
*Plan: 03*
*Completed: 2026-04-17*
