---
phase: 02-mcp-server-rebuild
plan: "03"
subsystem: mcp
tags: [asyncio, importlib, fastmcp, hot-reload, synthesized-tools, watcher]

# Dependency graph
requires:
  - phase: 02-mcp-server-rebuild plan 01
    provides: registry.register_tool() with source tagging and synth_ prefix enforcement

provides:
  - forge_bridge.learning package (watcher.py + __init__.py)
  - _scan_once() — single poll pass detecting new/changed/deleted .py files
  - _load_fn() — importlib loader returning callable from synthesized .py file
  - watch_synthesized_tools() — asyncio polling loop for hot-loading synthesized tools
  - server.py _lifespan context manager launching watcher as background task

affects:
  - phase-03 (learning pipeline synthesis — watcher is the delivery mechanism)
  - any future plan adding synthesized tools (watcher auto-discovers them)

# Tech tracking
tech-stack:
  added: [importlib.util, hashlib.sha256, asynccontextmanager, asyncio.create_task]
  patterns:
    - asyncio background task launched in FastMCP lifespan context manager
    - SHA-256 polling for file change detection (no inotify/fsevents dependency)
    - importlib.util.spec_from_file_location for isolated module loading per synthesized file
    - register_tool(source="synthesized") enforces synth_ prefix via existing registry validation

key-files:
  created:
    - forge_bridge/learning/__init__.py
    - forge_bridge/learning/watcher.py
    - tests/test_watcher.py (replaced skipped stubs with 7 real tests)
  modified:
    - forge_bridge/mcp/server.py (asynccontextmanager import, _lifespan, lifespan=_lifespan)

key-decisions:
  - "SHA-256 polling (5s interval) chosen over filesystem events — no platform-specific dependencies, consistent cross-platform behavior"
  - "watcher.py imports register_tool inline (inside _scan_once) to avoid circular import at module load time"
  - "_lifespan defined before mcp = FastMCP() at module level — Python resolves _startup/_shutdown at call time not definition time"

patterns-established:
  - "Synthesized tool lifecycle: _load_fn (importlib) -> register_tool(source='synthesized') -> mcp.add_tool with meta={'_source': 'synthesized'}"
  - "Server lifespan pattern: asynccontextmanager wrapping _startup()/_shutdown() + background task with cancel/await on exit"

requirements-completed: [MCP-02, MCP-03, MCP-06]

# Metrics
duration: 2min
completed: 2026-04-15
---

# Phase 02 Plan 03: Synthesized Tool Watcher Summary

**Asyncio polling watcher hot-loads synth_* tools from ~/.forge-bridge/synthesized/ via SHA-256 diff + importlib, wired into FastMCP server lifespan as background task**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-04-15T03:10:57Z
- **Completed:** 2026-04-15T03:12:34Z
- **Tasks:** 2 completed
- **Files modified:** 4

## Accomplishments

- Created forge_bridge/learning/ package with watcher.py implementing full scan/load/register/remove cycle
- Replaced 3 skipped stub tests with 7 passing watcher tests covering all behavioral scenarios
- Added _lifespan context manager to server.py — watcher launches at server start, cancels cleanly on shutdown
- Full test suite remains green: 108 passed (was 101 + 3 skipped)

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement watcher.py and unskip watcher tests** - `d85b478` (feat)
2. **Task 2: Add lifespan to server.py for watcher background task** - `694936b` (feat)

**Plan metadata:** (final commit follows)

## Files Created/Modified

- `forge_bridge/learning/__init__.py` - Package init with docstring
- `forge_bridge/learning/watcher.py` - Asyncio watcher: SYNTHESIZED_DIR constant, watch_synthesized_tools(), _scan_once(), _load_fn(), _sha256()
- `tests/test_watcher.py` - 7 tests across 4 classes: loads new file, reloads changed file, removes deleted file, edge cases
- `forge_bridge/mcp/server.py` - Added asynccontextmanager import, _lifespan context manager, lifespan=_lifespan kwarg on FastMCP constructor

## Decisions Made

- SHA-256 polling (5-second interval) chosen over filesystem event APIs (inotify/kqueue/FSEvents) — no platform-specific dependencies, simpler code, acceptable latency for synthesized tools
- register_tool imported inline inside _scan_once() to avoid circular import at module load time (server.py imports watcher.py which would import registry.py which imports nothing from server.py — technically safe, but inline import makes the dependency explicit and avoids any future risk)
- _lifespan defined at module level before mcp = FastMCP() — Python resolves _startup/_shutdown at call time so forward reference is fine

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Watcher is live: any .py file dropped into ~/.forge-bridge/synthesized/ will be hot-loaded as a synth_* MCP tool within 5 seconds
- Phase 3 (learning pipeline) can synthesize tools to that directory and they will appear in the MCP tool list without server restart
- MCP-02, MCP-03, MCP-06 requirements all satisfied

---
*Phase: 02-mcp-server-rebuild*
*Completed: 2026-04-15*
