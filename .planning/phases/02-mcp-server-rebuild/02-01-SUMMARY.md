---
phase: 02-mcp-server-rebuild
plan: "01"
subsystem: mcp
tags: [mcp, fastmcp, registry, namespace, source-tagging, tdd]

# Dependency graph
requires:
  - phase: 01-tool-parity-llm-router
    provides: forge_bridge/mcp/server.py with ~30 registered tools; test suite infrastructure

provides:
  - forge_bridge/mcp/registry.py — namespace enforcement and source tagging for all tool registration
  - tests/test_mcp_registry.py — 7 passing unit tests for registry module
  - tests/test_watcher.py — 3 skipped stubs documenting Plan 03 watcher requirements

affects:
  - 02-02 (server rebuild will call register_builtins via this registry)
  - 02-03 (watcher will call register_tool(source="synthesized") via this registry)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Registry pattern: wrap mcp.add_tool() with namespace guard + source metadata"
    - "TDD cycle: RED (ImportError) → GREEN (7 tests passing) committed separately"
    - "Wave 0 stub pattern: skipped tests as living documentation for future plans"
    - "Frozenset for prefix allowlists — immutable, fast membership testing"

key-files:
  created:
    - forge_bridge/mcp/registry.py
    - tests/test_mcp_registry.py
    - tests/test_watcher.py
  modified: []

key-decisions:
  - "register_builtins() is a stub in Plan 01 — filled when server.py is rebuilt in Plan 02"
  - "meta={'_source': source} is the source tagging mechanism — stored in Tool.meta, surfaced in tools/list response"
  - "synth_ prefix exclusively reserved for source='synthesized' — ValueError raised for all other sources"
  - "register_tools() must be called before mcp.run() — no ToolListChangedNotification sent"

patterns-established:
  - "All MCP tool registration routes through register_tool() — never call mcp.add_tool() directly from outside registry"
  - "Every tool name must start with flame_, forge_, or synth_ — enforced at registration time"
  - "Source tag is mandatory — passed as string literal: 'builtin', 'synthesized', or 'user-taught'"

requirements-completed: [MCP-01, MCP-04, MCP-05, MCP-06]

# Metrics
duration: 2min
completed: 2026-04-15
---

# Phase 2 Plan 01: Registry Module Summary

**Namespace-enforcing MCP tool registry with source tagging via meta={'_source'} and frozenset prefix allowlist, with TDD-verified synth_ reservation for synthesis pipeline only**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-04-15T03:07:34Z
- **Completed:** 2026-04-15T03:09:10Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Created `forge_bridge/mcp/registry.py` with _validate_name(), register_tool(), register_tools(), register_builtins()
- Created `tests/test_mcp_registry.py` with 7 unit tests covering all MCP-01/04/05/06 requirements
- Created `tests/test_watcher.py` with 3 skipped stubs as living docs for Plan 03 watcher requirements
- Full test suite remains green: 101 passed, 3 skipped, 0 failures

## Task Commits

Each task was committed atomically:

1. **Task 1: Create test files for registry and watcher** - `893d34c` (test)
2. **Task 2: Implement registry.py with namespace enforcement and source tagging** - `dd4eb86` (feat)

_Note: TDD tasks have separate RED (test) and GREEN (feat) commits_

## Files Created/Modified

- `forge_bridge/mcp/registry.py` — Namespace enforcement, source tagging, public registration API
- `tests/test_mcp_registry.py` — 7 unit tests for registry (all passing)
- `tests/test_watcher.py` — 3 skipped stubs for watcher (Plan 03)

## Decisions Made

- `register_builtins()` is a pass-through stub; actual builtin migration happens in Plan 02 when server.py is rebuilt
- Source tagging uses FastMCP's native `meta=` parameter rather than function attributes — appears in tools/list response
- `synth_` is exclusively reserved for `source="synthesized"` — static paths (builtin, user-taught) raise ValueError
- `register_tools()` is a pre-run API only — no notification sent, downstream consumers must call before `mcp.run()`

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Registry module complete; Plan 02 can call `register_builtins(mcp)` to migrate existing tool registrations
- Plan 03 watcher can call `register_tool(mcp, fn, name=stem, source="synthesized")` directly
- Test stubs in test_watcher.py are ready to unskip when watcher.py lands in Plan 03

---
*Phase: 02-mcp-server-rebuild*
*Completed: 2026-04-15*
