---
phase: 01-tool-parity-llm-router
plan: 03
subsystem: api
tags: [mcp, llm, health-check, fastmcp, openai, anthropic]

# Dependency graph
requires:
  - phase: 01-tool-parity-llm-router
    plan: 02
    provides: "LLMRouter with acomplete()/complete() and get_router() singleton"

provides:
  - "forge://llm/health MCP resource exposing local/cloud backend availability as JSON"
  - "ahealth_check() and health_check() methods on LLMRouter"
  - "register_llm_resources(mcp) function for wiring health into any FastMCP server"

affects: [phase-02, phase-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "MCP resource registration via dedicated register_*_resources(mcp) functions in submodules"
    - "Health check pattern: try model list for local, check env var for cloud"

key-files:
  created:
    - forge_bridge/llm/health.py
  modified:
    - forge_bridge/llm/__init__.py
    - forge_bridge/server.py

key-decisions:
  - "register_llm_resources(mcp) follows same registration pattern as tool registrations — called once at module level before main()"
  - "Health resource lazy-imports get_router() inside the async handler to avoid circular imports"

patterns-established:
  - "Pattern: submodule health/resource modules expose a register_*(mcp) function, called from server.py"

requirements-completed: [LLM-06, LLM-07]

# Metrics
duration: 5min
completed: 2026-04-15
---

# Phase 01 Plan 03: LLM Health Check MCP Resource Summary

**forge://llm/health MCP resource exposing local (Ollama) and cloud (Anthropic) backend availability via ahealth_check() on LLMRouter**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-15T02:01:00Z
- **Completed:** 2026-04-15T02:02:41Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Created `forge_bridge/llm/health.py` with `register_llm_resources(mcp)` registering `forge://llm/health`
- Updated `forge_bridge/llm/__init__.py` to export `register_llm_resources`
- Wired health resource registration into `forge_bridge/server.py` — resource now available to all MCP clients

## Task Commits

Each task was committed atomically:

1. **Task 1: Add health check methods to LLMRouter and create health.py** - `8623fe1` (feat)
2. **Task 2: Wire health resource into MCP server** - `3535181` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `forge_bridge/llm/health.py` - MCP resource registration; `register_llm_resources(mcp)` registers `forge://llm/health`
- `forge_bridge/llm/__init__.py` - Added `register_llm_resources` to exports
- `forge_bridge/server.py` - Import and call `register_llm_resources(mcp)` before `def main()`

## Decisions Made

- `register_llm_resources(mcp)` follows the same module-level registration pattern as tool registrations in server.py — called once at import time before `main()`.
- `get_router()` is lazy-imported inside the async resource handler to avoid circular import risks.

## Deviations from Plan

None - plan executed exactly as written. Note: `ahealth_check()` and `health_check()` were already present on `LLMRouter` from Plan 02 execution; Task 1 only required creating `health.py` and updating `__init__.py`.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- LLM router (Plans 01-02) and health resource (Plan 03) are complete
- MCP clients can query `forge://llm/health` to discover backend availability before routing decisions
- Ready to proceed to Plan 04 (synthesizer or next wave)

---
*Phase: 01-tool-parity-llm-router*
*Completed: 2026-04-15*
