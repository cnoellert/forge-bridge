---
phase: 01-tool-parity-llm-router
plan: "04"
subsystem: tools/timeline
tags: [tool-parity, flame-api, porting, timeline, publish]
dependency_graph:
  requires: []
  provides: [TOOL-01, TOOL-03]
  affects: [forge_bridge/tools/timeline.py, forge_bridge/tools/publish.py]
tech_stack:
  added: []
  patterns:
    - Pydantic BaseModel input classes for each ported function
    - bridge.execute_json() for read-only Flame queries
    - bridge.execute_json(..., main_thread=True) for Flame write operations
    - threading.Event pattern inside Flame's schedule_idle_event() callbacks
key_files:
  created: []
  modified:
    - forge_bridge/tools/timeline.py
    - forge_bridge/tools/publish.py
decisions:
  - "All 8 ported functions use 'from forge_mcp import bridge' — the correct import path for standalone tools"
  - "publish.py rename_segments is functionally identical to projekt-forge; verification comment added, no logic changes"
metrics:
  duration: "~3 minutes"
  completed: "2026-04-14"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
---

# Phase 1 Plan 4: Timeline and Publish Tool Parity Summary

8 Flame timeline functions ported from projekt-forge with Pydantic input models and correct import paths; publish.py rename_segments verified identical to projekt-forge.

## Tasks Completed

| Task | Description | Commit | Status |
|------|-------------|--------|--------|
| 1 | Port 8 timeline functions from projekt-forge | e4d0d0f | Done |
| 2 | Verify publish.py rename_segments | 9bc6279 | Done |

## What Was Done

### Task 1: 8 New Timeline Functions

All 8 functions ported from `/Users/cnoellert/Documents/GitHub/projekt-forge/forge_bridge/tools/timeline.py` into `forge_bridge/tools/timeline.py`.

Each function includes:
- A Pydantic `BaseModel` subclass for input validation
- Full docstring from the source
- Correct bridge import (`from forge_mcp import bridge`)
- Async function signature

Functions ported:

| Function | Description | Method |
|----------|-------------|--------|
| `inspect_sequence_versions` | Inspect all versions/tracks/segments with full PyTime metadata | bridge.execute_json() |
| `create_version` | Create a blank version on a sequence | bridge.execute_json(main_thread=True) |
| `reconstruct_track` | Copy segments between versions via copy_to_media_panel + overwrite() | bridge.execute_json(main_thread=True) |
| `clone_version` | Fork a version by reconstructing all tracks | bridge.execute_json(main_thread=True) |
| `disconnect_segments` | Call remove_connection() on all segments in a reel | bridge.execute_json(main_thread=True) |
| `replace_segment_media` | Relink segment source via smart_replace_media() | bridge.execute_json(main_thread=True) |
| `scan_roles` | Audit tagged/detected/effective roles on segments | bridge.execute_json() |
| `assign_roles` | Write forge:{role} tags to named segments | bridge.execute_json(main_thread=True) |

### Task 2: publish.py rename_segments Verification

Compared standalone and projekt-forge implementations of `rename_segments`. Result: **Scenario A — functionally identical**.

Both implementations use:
- Same track collection pattern (iterating all versions)
- Same role detection via `footage/([^/]+)/` regex
- Same fallback role ('graded' when undetectable)
- Same `threading.Event` + `flame.schedule_idle_event()` pattern
- Same `bridge.execute_and_read()` call

Added verification comment to source documenting parity status. No logic changes required.

## Deviations from Plan

### Auto-fixed Issues

None.

### Observations

**[Observation] Linter auto-corrected bridge import in publish.py**
- Found during: Task 2 commit
- Issue: After committing the verification comment, a linter/formatter changed `from forge_mcp import bridge` to `from forge_bridge import bridge` in publish.py. This is a pre-existing codebase inconsistency — the forge_bridge and forge_mcp module aliases both resolve to the same bridge.py HTTP client.
- Action: Updated verification comment to accurately describe the import resolution. Did not attempt to fix the underlying module alias inconsistency (out of scope for this plan).
- Files modified: forge_bridge/tools/publish.py (comment only)

## Self-Check: PASSED

Files exist:
- forge_bridge/tools/timeline.py — FOUND (all 8 functions added)
- forge_bridge/tools/publish.py — FOUND (verification comment present)

Commits exist:
- e4d0d0f: feat(01-04): port 8 new timeline functions from projekt-forge — FOUND
- 9bc6279: chore(01-04): verify publish.py rename_segments against projekt-forge — FOUND
- 2f82287: chore(01-04): fix verification comment in publish.py rename_segments — FOUND
