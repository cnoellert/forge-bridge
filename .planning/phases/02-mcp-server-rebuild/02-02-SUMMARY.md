---
phase: 02-mcp-server-rebuild
plan: "02"
subsystem: mcp
tags: [fastmcp, registry, tool-registration, mcp-server]

# Dependency graph
requires:
  - phase: 02-mcp-server-rebuild/02-01
    provides: register_tool(), register_tools(), register_builtins() stub, namespace enforcement, source tagging

provides:
  - register_builtins() fully populated with all ~42 tool registrations (13 forge pipeline + 8 forge publish + 21 flame HTTP bridge)
  - server.py stripped of all direct mcp.tool() calls — single register_builtins(mcp) entry point
  - forge_bridge.mcp public API: register_tools and get_mcp exportable from __init__.py

affects: [02-03, synthesizer, user-taught-tools, projekt-forge-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "All builtin tool registrations centralised in register_builtins() in registry.py"
    - "server.py is configuration-only: creates mcp instance, calls register_builtins, defines lifecycle"
    - "Public API exposed via forge_bridge.mcp.__init__ — downstream consumers import from package not submodule"

key-files:
  created:
    - forge_bridge/mcp/__init__.py
  modified:
    - forge_bridge/mcp/registry.py
    - forge_bridge/mcp/server.py

key-decisions:
  - "register_builtins() structure: forge pipeline tools first, then forge publish workflow tools, then flame HTTP bridge tools (in try/except), then LLM resources"
  - "flame_snapshot_timeline stays under flame_ prefix even though it wraps forge_bridge.mcp.tools.snapshot_timeline — preserves backwards compatibility"
  - "__init__.py exposes get_mcp() as function (not attribute) to allow future lazy initialisation"

patterns-established:
  - "Tool registration order in register_builtins(): forge_* pipeline → forge_* publish → flame_* HTTP bridge → LLM resources"
  - "Flame HTTP bridge imports wrapped in try/except ImportError with warning log — graceful degradation when forge_bridge.tools absent"

requirements-completed: [MCP-01, MCP-05]

# Metrics
duration: 8min
completed: 2026-04-14
---

# Phase 02 Plan 02: MCP Server Rebuild Summary

**All ~42 MCP tool registrations centralised in register_builtins() in registry.py; server.py reduced to lifecycle-only with zero direct mcp.tool() calls; forge_bridge.mcp exports register_tools and get_mcp as public API**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-14T05:30:51Z
- **Completed:** 2026-04-14T05:38:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Populated register_builtins() with all tool registrations migrated 1:1 from server.py — exact names, annotations, and source="builtin" on every tool
- Rebuilt server.py to 110 lines from 528 — all tool registration code removed, replaced with single register_builtins(mcp) call
- Created __init__.py exporting register_tools and get_mcp as the documented public API for downstream consumers (projekt-forge, synthesizer)
- 108 tests pass with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Populate register_builtins() with all existing tool registrations** - `82afd3d` (feat)
2. **Task 2: Rebuild server.py and update __init__.py exports** - `c40953d` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `forge_bridge/mcp/registry.py` - register_builtins() fully populated with all ~42 tool registrations
- `forge_bridge/mcp/server.py` - Rebuilt: removed 39 mcp.tool() calls, added register_builtins(mcp)
- `forge_bridge/mcp/__init__.py` - Created: exports register_tools and get_mcp

## Decisions Made

- flame_snapshot_timeline registered under flame_ prefix despite wrapping forge_bridge.mcp.tools.snapshot_timeline — backwards compatibility takes priority over naming consistency
- __init__.py uses function get_mcp() rather than exposing mcp directly — allows future lazy init without breaking callers
- Flame HTTP bridge tools remain in a try/except ImportError block within register_builtins() — same graceful degradation as before, just moved to registry

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. The migration was purely mechanical — every annotation dict was copied verbatim from server.py to the corresponding register_tool() call in register_builtins().

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Registry is now the single source of truth for all tool registrations
- register_tools() and get_mcp() are importable from forge_bridge.mcp — ready for synthesizer integration in Plan 03
- No regressions: 108/108 tests pass

---
*Phase: 02-mcp-server-rebuild*
*Completed: 2026-04-14*
