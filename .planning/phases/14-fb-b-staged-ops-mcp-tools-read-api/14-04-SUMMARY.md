---
phase: 14
plan: "04"
subsystem: mcp-tools
tags: [mcp, staged-ops, pydantic, fb-b, wave-2]
dependency_graph:
  requires: [14-01, 14-02]
  provides: [forge_list_staged, forge_get_staged, forge_approve_staged, forge_reject_staged, ListStagedInput, GetStagedInput, ApproveStagedInput, RejectStagedInput]
  affects: [14-05]
tech_stack:
  added: []
  patterns:
    - "Deferred import inside register_console_resources to break circular import: mcp/tools.py -> console/handlers.py -> console/__init__.py -> console/resources.py -> mcp/tools.py"
    - "Pydantic min_length=1 as D-07 enforcement gate before tool body runs"
    - "_envelope_json from console/handlers for byte-identity with HTTP routes (D-19)"
    - "session_factory closure capture in tool bodies for write-path (D-04)"
key_files:
  created:
    - tests/mcp/__init__.py
    - tests/mcp/test_staged_tools.py
  modified:
    - forge_bridge/mcp/tools.py
    - forge_bridge/console/resources.py
    - tests/test_console_mcp_resources.py
decisions:
  - "Impl functions kept in forge_bridge/mcp/tools.py (co-location with existing tool pattern, not a new staged_tools.py)"
  - "Deferred import (inside function body) chosen over module-level import to break the mcp.tools->console.handlers->console.__init__->console.resources->mcp.tools circular import chain"
  - "tests/test_console_mcp_resources.py updated to reflect 6 total tools (2 Phase 9 shims + 4 Phase 14 FB-B tools) — broken by the new registrations, fixed as Rule 1 deviation"
metrics:
  duration: "~25 minutes"
  completed: "2026-04-26"
  tasks_completed: 3
  files_changed: 5
---

# Phase 14 Plan 04: Staged-Ops MCP Tools Summary

**One-liner:** Four `forge_*_staged` MCP tools registered from `register_console_resources` closures with Pydantic D-07 validation, `_envelope_json` byte-identity, and session_factory write-path per D-17 Solution C.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create tests/mcp/ package marker | 1fdd226 | tests/mcp/__init__.py |
| 2 | Add Pydantic input models + 4 impl functions | 80d6b0f | forge_bridge/mcp/tools.py, tests/mcp/test_staged_tools.py |
| 3 | Register 4 forge_*_staged tools from register_console_resources | 0692e03 | forge_bridge/console/resources.py, tests/test_console_mcp_resources.py |

## Plan Output Verification

**Registered tools (from register_console_resources introspection):**
```
forge_approve_staged, forge_get_staged, forge_list_staged, forge_manifest_read, forge_reject_staged, forge_tools_read
```
(6 total: 2 Phase 9 shims + 4 Phase 14 FB-B staged-ops tools)

**Implementation functions location:** `forge_bridge/mcp/tools.py` (not a separate `staged_tools.py` — co-location per Claude's Discretion in CONTEXT.md)

**Tests added in test_staged_tools.py:** 17 total
- 3 Pydantic validation tests (no DB required, always pass)
- 14 tool integration tests (skip cleanly without Postgres)

**Legacy `_ok` usage in staged tools:** ZERO — confirmed by `grep -n "_ok(" forge_bridge/mcp/tools.py | grep -i staged` returning empty

**Staged tools in register_builtins:** ZERO — confirmed by `grep -n "forge_list_staged..." forge_bridge/mcp/registry.py` returning empty

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Circular import: mcp/tools.py -> console/handlers.py -> console/__init__.py -> console/resources.py -> mcp/tools.py**
- **Found during:** Task 3, first import attempt
- **Issue:** The plan instructed adding a module-level import of impl functions in `resources.py`. This created a circular import because `mcp/tools.py` imports `console/handlers._envelope_json`, and `console/__init__.py` re-exports `register_console_resources` from `console/resources.py`, which would then import `mcp/tools.py` — circular.
- **Fix:** Moved the `from forge_bridge.mcp.tools import (...)` import inside the `register_console_resources` function body. Since `register_console_resources` is called from `_lifespan` (not at module load), both modules are fully initialized before the deferred import runs. Added `# noqa: PLC0415` comment to suppress the "import not at top of file" linter warning.
- **Files modified:** `forge_bridge/console/resources.py`
- **Commit:** 0692e03

**2. [Rule 1 - Bug] test_console_mcp_resources.py: two tests broken by new tool registrations**
- **Found during:** Task 3 verification
- **Issue:** `test_register_console_resources_registers_two_tool_shims` asserted `len(names) == 2` (pre-FB-B assumption). `test_tool_shims_have_read_only_hint` asserted ALL tools have `readOnlyHint=True` (write tools intentionally have `readOnlyHint=False` per D-16).
- **Fix:** Updated count assertion to 6 (2 + 4 new); updated hint test to split read-only vs write tools by name using `_READ_ONLY_TOOLS` and `_WRITE_TOOLS` sets.
- **Files modified:** `tests/test_console_mcp_resources.py`
- **Commit:** 0692e03

**3. [Rule 1 - Bug] reject() method parameter name mismatch**
- **Found during:** Task 2 implementation review
- **Issue:** `StagedOpRepo.reject(op_id, actor=str)` but implementation was written with `rejecter=params.actor`
- **Fix:** Changed to `actor=params.actor` to match the repo signature.
- **Files modified:** `forge_bridge/mcp/tools.py`
- **Commit:** 80d6b0f

## Known Stubs

None. All four tools are fully wired to `console_read_api` (reads) or `session_factory` (writes).

## Threat Flags

None. All STRIDE threats from the plan's threat model are addressed:
- T-14-04-01: Pydantic min_length=1 enforced on actor fields
- T-14-04-03: `_envelope_json` used for all success paths; Plan 14-05 byte-identity test will be the regression guard

## Test Results

```
tests/mcp/test_staged_tools.py: 3 passed, 14 skipped (Postgres unavailable)
tests/test_console_mcp_resources.py: 35 passed
tests/test_mcp_registry.py: passed (no regression)
Total: 38 passed, 14 skipped, 0 failed
```

## Self-Check: PASSED

Files created/modified all exist and committed:
- forge_bridge/mcp/tools.py: FOUND (commit 80d6b0f)
- forge_bridge/console/resources.py: FOUND (commit 0692e03)
- tests/mcp/__init__.py: FOUND (commit 1fdd226)
- tests/mcp/test_staged_tools.py: FOUND (commit fb6f5a5, 80d6b0f)
- tests/test_console_mcp_resources.py: FOUND (commit 0692e03)

Commits verified: 1fdd226, fb6f5a5, 80d6b0f, 0692e03 — all present in git log.
