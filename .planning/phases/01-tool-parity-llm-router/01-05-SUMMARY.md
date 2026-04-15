---
phase: 01-tool-parity-llm-router
plan: 05
subsystem: tools
tags: [porting, batch, reconform, switch_grade, stub, flame]
dependency_graph:
  requires: []
  provides: [inspect_batch_xml, prune_batch_xml, reconform_sequence, replace_segment_media, switch_grade, query_alternatives]
  affects: [forge_bridge/tools/batch.py, forge_bridge/tools/reconform.py, forge_bridge/tools/switch_grade.py]
tech_stack:
  added: []
  patterns: [RuntimeError stub for unavailable external deps, catalog WebSocket stub as JSON error response]
key_files:
  created:
    - forge_bridge/tools/reconform.py
    - forge_bridge/tools/switch_grade.py
  modified:
    - forge_bridge/tools/batch.py
    - forge_bridge/tools/timeline.py
    - forge_bridge/tools/utility.py
    - forge_bridge/tools/project.py
    - forge_bridge/tools/publish.py
    - forge_bridge/mcp/tools.py
decisions:
  - "inspect_batch_xml and prune_batch_xml stubbed with RuntimeError: forge_batch_xml/forge_batch_prune scripts not present in standalone repo"
  - "query_alternatives stubbed with JSON error response: catalog WebSocket is projekt-forge infrastructure"
  - "switch_grade ported with direct media_path parameter (no openclip vstack builder): callers who know the target path can use it without catalog"
  - "Auto-fixed broken 'from forge_mcp import bridge' imports across all tool files — forge_mcp package does not exist in standalone repo; correct import is from forge_bridge import bridge"
metrics:
  duration: 275s
  completed: 2026-04-15
  tasks_completed: 2
  files_changed: 8
---

# Phase 1 Plan 05: Batch XML Tools, Reconform, and Switch Grade Summary

**One-liner:** Batch XML tool stubs plus full reconform_sequence and stubbed switch_grade/query_alternatives ported from projekt-forge, with auto-fix of broken forge_mcp import across all tool files.

## What Was Built

### Task 1: batch.py additions + reconform.py

**batch.py additions:**
- `InspectBatchXmlInput` Pydantic model and `inspect_batch_xml` function — raises `RuntimeError` with a clear message explaining that `forge_batch_xml` from `flame_hooks` is required but not present in standalone.
- `PruneBatchXmlInput` Pydantic model and `prune_batch_xml` function — same stub pattern for `forge_batch_prune`.

**forge_bridge/tools/reconform.py (new file):**
- `ReconformSequenceInput`, `ReplaceSegmentMediaInput` Pydantic models.
- `reconform_sequence` — tag-driven reconform for Flame timelines. Reads `forge:` tags from segments, discovers plate or shot openclips from the pipeline directory structure, creates a new sequence version, and applies `smart_replace_media`. Fully ported from projekt-forge with no external dependencies.
- `replace_segment_media` — targeted per-segment media swap for known paths.
- `_build_reconform_code` — code generator producing self-contained Flame Python.

### Task 2: switch_grade.py

**forge_bridge/tools/switch_grade.py (new file):**
- `QueryAlternativesInput` Pydantic model and `query_alternatives` — stubbed with JSON error response explaining catalog WebSocket dependency.
- `SwitchGradeInput` Pydantic model and `switch_grade` — fully functional Flame-side media swap. Locates target segment, locks all version tracks, imports alternative media into a scratch reel, calls `smart_replace_media`, unlocks tracks, and cleans up. Accepts a direct `media_path` parameter; no openclip vstack builder or catalog lookup required.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed broken `from forge_mcp import bridge` across all tool files**
- **Found during:** Task 1 verification
- **Issue:** All existing `forge_bridge/tools/*.py` files use `from forge_mcp import bridge`. The `forge_mcp` package does not exist in the standalone `forge-bridge` repo — this causes `ModuleNotFoundError` for every tool import. The research notes identified this as the "correct standalone pattern" but that was based on misreading a broken import that already existed in the repo.
- **Fix:** Changed all occurrences of `from forge_mcp import bridge` to `from forge_bridge import bridge` (the actual package name). Affected: `batch.py`, `timeline.py`, `utility.py`, `project.py`, `publish.py`, `mcp/tools.py`. New files `reconform.py` and `switch_grade.py` use the corrected import from creation.
- **Files modified:** forge_bridge/tools/batch.py, forge_bridge/tools/timeline.py, forge_bridge/tools/utility.py, forge_bridge/tools/project.py, forge_bridge/tools/publish.py, forge_bridge/mcp/tools.py
- **Commit:** b03db70 (included in Task 1 commit)

**2. [Rule 2 - Deviation] switch_grade SwitchGradeInput uses media_path instead of entity_id + alternative_path**
- **Found during:** Task 2 implementation
- **Issue:** The original `SwitchGradeInput` in projekt-forge includes `alternative_path`, `alternative_start_frame`, `alternative_duration`, and `entity_id` — all needed to build an openclip vstack via `_write_openclip_server_side`. Since the openclip builder is not available in standalone, those fields serve no purpose.
- **Fix:** Simplified `SwitchGradeInput` to accept `media_path` directly. Callers who know their target media path (from disk or another source) can use `switch_grade` without the catalog. This is consistent with the plan's intent: "port the core switch_grade function for direct media path swaps without openclip."

## Verification Results

All plan verification commands pass:
- `python -c "from forge_bridge.tools.batch import inspect_batch_xml, prune_batch_xml; print('OK')"` — PASS
- `python -c "from forge_bridge.tools.reconform import reconform_sequence; print('OK')"` — PASS
- `python -c "from forge_bridge.tools.switch_grade import switch_grade; print('OK')"` — PASS
- No tool files contain `from forge_mcp import bridge` as a real import (only in a comment in publish.py)

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | b03db70 | feat(01-05): port batch XML tools and create reconform.py |
| Task 2 | 45d6be6 | feat(01-05): create switch_grade.py with catalog stub |

## Self-Check: PASSED
