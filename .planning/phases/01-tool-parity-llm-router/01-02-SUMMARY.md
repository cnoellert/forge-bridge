---
phase: 01-tool-parity-llm-router
plan: 02
subsystem: llm
tags: [openai, anthropic, asyncio, async, llm-router, optional-deps]

# Dependency graph
requires: []
provides:
  - forge_bridge/llm/ async LLM routing package with acomplete() coroutine
  - Sync complete() wrapper (asyncio.run) for use outside async contexts
  - Lazy import guards for openai/AsyncOpenAI and anthropic/AsyncAnthropic
  - Env-var configuration for all hardcoded hostnames and system prompt
  - Backwards-compatible shim at forge_bridge/llm_router.py
  - Module-level singleton via get_router()
affects:
  - Phase 2 tool porting (any tool needing LLM generation must use acomplete(), not complete())
  - Phase 3 synthesizer (uses LLMRouter.acomplete() with sensitive=True for local routing)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Async-first LLM router: acomplete() coroutine + sync complete() wrapper via asyncio.run()"
    - "Lazy import guard: try/except ImportError inside method, not at module top level"
    - "Backwards-compatible shim: re-export from promoted module location"
    - "Env-var configuration: all hardcoded values overridable without code change"

key-files:
  created:
    - forge_bridge/llm/__init__.py
    - forge_bridge/llm/router.py
  modified:
    - forge_bridge/llm_router.py

key-decisions:
  - "async def acomplete() is the primary API; sync complete() is explicitly for non-async callers only (documented in docstring)"
  - "Lazy imports inside _get_local_client() and _get_cloud_client() so base install succeeds without openai/anthropic"
  - "FORGE_SYSTEM_PROMPT env var added (new) so the VFX system prompt can be overridden without code change"
  - "ahealth_check() added alongside sync health_check() to match the async-first design"

patterns-established:
  - "Pattern: Lazy optional-dep import with pip install forge-bridge[llm] error message"
  - "Pattern: Async-first with sync wrapper — MCP tool handlers call acomplete() directly"

requirements-completed: [LLM-01, LLM-02, LLM-03, LLM-04]

# Metrics
duration: 2min
completed: 2026-04-15
---

# Phase 1 Plan 02: LLM Router Promotion Summary

**Async LLM router in forge_bridge/llm/ with acomplete() coroutine, lazy optional-dep guards, full env-var configuration, and backwards-compatible shim at original path**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-15T01:55:22Z
- **Completed:** 2026-04-15T01:56:42Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Promoted flat llm_router.py to forge_bridge/llm/ subpackage with router.py and __init__.py
- Added async acomplete() coroutine using AsyncOpenAI and AsyncAnthropic (non-blocking for MCP event loop)
- Added FORGE_SYSTEM_PROMPT env var so the VFX pipeline system prompt is configurable without code changes
- Lazy import guards ensure `from forge_bridge.llm.router import LLMRouter` works without openai/anthropic installed
- Original forge_bridge/llm_router.py reduced to an 11-line backwards-compatible shim

## Task Commits

Each task was committed atomically:

1. **Task 1: Create forge_bridge/llm/ package with async router** - `1c237f7` (feat)
2. **Task 2: Replace llm_router.py with backwards-compatible shim** - `d5ee6a3` (feat)

## Files Created/Modified
- `forge_bridge/llm/router.py` - Async LLMRouter with acomplete(), complete(), _get_local_client(), _get_cloud_client(), ahealth_check(), and get_router() singleton
- `forge_bridge/llm/__init__.py` - Package re-exports LLMRouter and get_router
- `forge_bridge/llm_router.py` - Reduced to 11-line backwards-compatible shim

## Decisions Made
- `asyncio.run()` used in sync wrapper (not `loop.run_until_complete()`) — creates its own event loop, safe when no loop running
- `acomplete()` is the primary async API; `complete()` docstring explicitly warns not to call from async contexts (MCP tool handlers)
- `ahealth_check()` added alongside `health_check()` sync wrapper to match async-first design and enable non-blocking health probes
- `FORGE_SYSTEM_PROMPT` env var added (new capability vs. original) — satisfies LLM-04 requirement to make system prompt configurable

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- forge_bridge.llm.router.LLMRouter is ready for use by Phase 3 synthesizer
- MCP tool handlers in Phase 2 should call `await router.acomplete()` directly, never `router.complete()`
- openai and anthropic packages are already installed in the venv; pyproject.toml [llm] extras fix is a separate plan item (LLM-05/LLM-08)

---
*Phase: 01-tool-parity-llm-router*
*Completed: 2026-04-15*
