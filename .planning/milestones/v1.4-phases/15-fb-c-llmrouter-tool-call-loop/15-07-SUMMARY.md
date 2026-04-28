---
phase: 15-fb-c-llmrouter-tool-call-loop
plan: 07
subsystem: llm
tags: [mcp, fastmcp, tool-call-loop, llmtool-03, llmrouter, async, registry]

# Dependency graph
requires:
  - phase: 14-fb-b-llm-decision-helpers
    provides: forge_bridge.mcp.registry register_tool/register_tools namespace + source surface; FastMCP singleton at forge_bridge.mcp.server.mcp
provides:
  - "forge_bridge.mcp.registry.invoke_tool(name, args) -> str — public async default tool executor for LLMRouter.complete_with_tools (D-20/D-21/D-22)"
  - "forge_bridge.mcp.registry._stringify_tool_result private helper — coerces 4 FastMCP return shapes (ContentBlock list, str, dict/list, fallback) into a string"
  - "forge_bridge.mcp.__all__ grown 2→3 — invoke_tool re-exported from the package barrel alongside register_tools and get_mcp"
  - "Hallucinated-tool-name self-correction surface — KeyError carries sorted available-tool list per research §4.3"
affects: [15-08-coordinator, 15-fb-c-llmrouter-tool-call-loop, fb-d-future]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "FastMCP public-API access only (list_tools/call_tool) — never poke _tool_manager._tools"
    - "Lazy import of forge_bridge.mcp.server inside function bodies — anti-cycle pattern (mirrors register_tools precedent)"
    - "Result-shape coercion via private helper with isinstance dispatch (4 cases)"
    - "KeyError with sorted-available-list message — LLM-self-correction surface"

key-files:
  created: []
  modified:
    - forge_bridge/mcp/registry.py
    - forge_bridge/mcp/__init__.py
    - tests/test_mcp_registry.py

key-decisions:
  - "D-21 deferred-question resolved YES — invoke_tool re-exported from forge_bridge.mcp barrel to mirror register_tools symmetry"
  - "Use FastMCP public API (list_tools, call_tool) — defense-in-depth for namespace enforcement (T-15-36)"
  - "Lazy-import server module to avoid registry → server → registry cycle"
  - "json.dumps with default=str — gracefully handles UUIDs/datetimes a tool may return"
  - "KeyError carries full sorted available-tool list (not truncated here) — coordinator's _sanitize_tool_result handles overflow"

patterns-established:
  - "Single-tool-invocation-authority pattern (analog of Phase 13 D-08 repo-as-single-write-authority)"
  - "Coerce-tool-result helper isolated in its own private function — testable, swappable"
  - "Async public function with explicit `name`/`args` param names matching D-20 contract"

requirements-completed: [LLMTOOL-03]

# Metrics
duration: ~12min
completed: 2026-04-27
---

# Phase 15 Plan 07: invoke_tool Default Tool Executor Summary

**Public async invoke_tool(name, args) -> str at forge_bridge.mcp.registry — the canonical default tool executor LLMRouter.complete_with_tools lazy-imports when the caller passes tool_executor=None, with hallucinated-name KeyError carrying the available-tool list per research §4.3**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-04-27T02:46:35Z (approx)
- **Completed:** 2026-04-27T02:58:47Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- New public `async invoke_tool(name: str, args: dict) -> str` at `forge_bridge/mcp/registry.py` matching the D-20/D-21/D-22 contract verbatim — looks up tools via the public FastMCP API (`list_tools`/`call_tool`), stringifies the result, and propagates tool exceptions for the coordinator to wrap.
- New private helper `_stringify_tool_result` handles 4 FastMCP return shapes: list[ContentBlock] (canonical), plain str, dict/list (json.dumps default=str), fallback str().
- Barrel growth from 2 → 3 entries in `forge_bridge/mcp/__init__.py` — `invoke_tool` re-exported alongside `register_tools` and `get_mcp` (D-21 deferred question locked YES).
- New `TestInvokeTool` class in `tests/test_mcp_registry.py` with 7 tests covering async signature, hallucinated-name KeyError + available-tool list, string passthrough, dict JSON-stringification, exception propagation, and the package re-export identity check.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add public async invoke_tool() to forge_bridge/mcp/registry.py** — `988eb3d` (feat)
2. **Task 2: Grow forge_bridge/mcp/__init__.py barrel from 2 to 3 entries** — `e78a938` (feat)
3. **Task 3: Add TestInvokeTool class to tests/test_mcp_registry.py** — `aa3b26d` (test)

## Files Created/Modified

- `forge_bridge/mcp/registry.py` — Added `invoke_tool` (FB-C LLMTOOL-03 default executor) and `_stringify_tool_result` private helper; added `import json`, `import logging`, and module-level `logger`; updated module docstring's Public API list.
- `forge_bridge/mcp/__init__.py` — Imported `invoke_tool` from registry, added it to `__all__` (single-source-of-truth re-export — `forge_bridge.mcp.invoke_tool is forge_bridge.mcp.registry.invoke_tool`).
- `tests/test_mcp_registry.py` — Appended new `TestInvokeTool` class with 7 tests; existing 23 tests untouched and still passing (30/30 total).

## Decisions Made

- **D-21 module re-export** — Locked YES (mirror `register_tools` symmetry). Future external consumers can import via either `forge_bridge.mcp` or `forge_bridge.mcp.registry` and get the same callable.
- **FastMCP public API only** — `await mcp.list_tools()` + `await mcp.call_tool(name, arguments=args)`. Never pokes `_tool_manager._tools`. This means any namespace-enforcement logic in `register_tool` (the `_validate_name` flame_/forge_/synth_ prefix check) is unconditionally honored — `invoke_tool` can only invoke tools that passed registration validation (T-15-36 mitigation).
- **Lazy import of server module** — `import forge_bridge.mcp.server as _server` inside the function body, then `mcp = _server.mcp`. Mirrors the precedent at line 165 in `register_tools`. Prevents the `server.py → registry.py → server.py` cycle and captures the *current* singleton value, not a stale snapshot.
- **`json.dumps(result, default=str)`** — Accepts non-JSON-serializable values (UUIDs, datetimes) via their `str()` representation rather than raising TypeError. The downstream coordinator (plan 15-08) re-sanitizes via `_sanitize_tool_result` before feeding to the LLM.
- **KeyError with full available-tool list** — Per research §4.3, the LLM uses the list to self-correct on the next turn. No truncation here; the coordinator's `_sanitize_tool_result` (plan 15-04) caps at 8 KB if needed.

## Deviations from Plan

None — plan executed exactly as written. All three task verification commands and acceptance criteria passed on first run.

## Issues Encountered

None. Existing 23 tests in `test_mcp_registry.py` continued to pass after each task; new 7 tests in `TestInvokeTool` passed on first run.

## User Setup Required

None — no external service configuration required. Pure Python addition to `forge_bridge.mcp` package surface.

## Architectural Confirmations

Per the plan's `<output>` requirements:

- **Lazy-import anti-cycle pattern preserved.** `invoke_tool` uses `import forge_bridge.mcp.server as _server` inside the function body — same precedent as `register_tools` at line 165 of registry.py. `grep -c "import forge_bridge.mcp.server as _server" forge_bridge/mcp/registry.py` returns `2` (one per function).
- **FastMCP public API is the only access path.** The implementation uses ONLY `mcp.list_tools()` and `mcp.call_tool(name, arguments=args)`. There is no `_tools` / `_tool_manager` poke anywhere in `invoke_tool` or `_stringify_tool_result`. Namespace-enforcement logic in `register_tool._validate_name` is therefore unconditionally honored.
- **D-21 module re-export deferred question resolved YES.** `forge_bridge.mcp.__all__` now contains exactly 3 entries: `["register_tools", "get_mcp", "invoke_tool"]`. Identity check `forge_bridge.mcp.invoke_tool is forge_bridge.mcp.registry.invoke_tool` passes (single source of truth — no copy).
- **Wave 3 plan 15-08 lazy-imports invoke_tool inside `complete_with_tools()`.** Per D-21, the coordinator imports this function only when the caller passes `tool_executor=None`. This plan is the standalone helper counterpart — Wave 3 closes the loop by wiring it into the coordinator.

## Next Phase Readiness

- Wave 3 plan 15-08 (`LLMRouter.complete_with_tools`) can now `from forge_bridge.mcp.registry import invoke_tool` (or `from forge_bridge.mcp import invoke_tool`) inside the executor-default branch.
- The KeyError shape from this function is the structured input the coordinator's hallucinated-tool-name surfacer expects per research §4.3.
- The `_stringify_tool_result` helper's output is the input to the coordinator's `_sanitize_tool_result` (plan 15-04) — defense in depth across both helpers.

## Self-Check: PASSED

**Files claimed → exist:**
- `forge_bridge/mcp/registry.py` — FOUND (modified, +110 lines)
- `forge_bridge/mcp/__init__.py` — FOUND (modified, +2/-2 lines)
- `tests/test_mcp_registry.py` — FOUND (modified, +118 lines)

**Commits claimed → exist (verified via `git log --oneline`):**
- `988eb3d` (Task 1, feat) — FOUND
- `e78a938` (Task 2, feat) — FOUND
- `aa3b26d` (Task 3, test) — FOUND

**Plan-level verification (from plan's `<verification>` block):**
- `pytest tests/test_mcp_registry.py -x -q` — 30 passed, 1 warning (unrelated websockets DeprecationWarning) — PASSED
- Cross-package surface check (`from forge_bridge.mcp import invoke_tool` + `iscoroutinefunction` + parameters `[name, args]`) — PASSED
- `git diff --stat` shows exactly 3 files modified — PASSED

---
*Phase: 15-fb-c-llmrouter-tool-call-loop*
*Plan: 07*
*Completed: 2026-04-27*
