---
phase: 07-tool-provenance-in-mcp-annotations
plan: "03"
subsystem: mcp-registry
tags: [provenance, registry, prov-02, prov-04, prov-05, prov-06, wr-01, wr-02, readOnlyHint, conda]

requires:
  - phase: 07-tool-provenance-in-mcp-annotations
    plan: "02"
    provides: "watcher._read_sidecar() passing provenance= via inspect feature-detect to register_tool"

provides:
  - "register_tool grows provenance: dict[str, Any] | None = None kwarg (PROV-02)"
  - "Only forge-bridge/* namespaced meta keys forwarded to mcp.add_tool meta dict (T-07-12 defense)"
  - "source='synthesized' registrations get readOnlyHint=False baseline via setdefault (PROV-04)"
  - "register_tools (public plural API) signature frozen: [mcp, fns, prefix, source]"
  - "10 new TestProvenanceMerge tests covering all PROV-02 + PROV-04 cases"
  - "2 new WR-01 async callback failure isolation tests (closes coverage gap on _log_callback_exception)"
  - "ExecutionRecord docstring corrected — scoped to record() writes, cross-references mark_promoted() partial row (WR-02)"
  - "README.md ## Conda environment section matching projekt-forge convention (PROV-06)"

affects:
  - 07-04-release-ceremony

tech-stack:
  added: []
  patterns:
    - "provenance merge: _source set first, then forge-bridge/* keys added — never overwrites _source (T-07-14)"
    - "PROV-04 baseline: effective_annotations.setdefault('readOnlyHint', False) only when source='synthesized'"
    - "defense-in-depth: k.startswith('forge-bridge/') filter at registry boundary drops non-canonical keys"
    - "Plan 07-02 inspect feature-detect auto-activates now that provenance kwarg exists"

key-files:
  created: []
  modified:
    - forge_bridge/mcp/registry.py
    - forge_bridge/learning/execution_log.py
    - tests/test_mcp_registry.py
    - tests/test_execution_log.py
    - README.md

key-decisions:
  - "Tags echoed as forge-bridge/tags in merged_meta (not via FastMCP tags= param) — FastMCP tags= is a filter/enable mechanism, not data. _meta is the PROV-02 data channel."
  - "effective_annotations.setdefault (not assignment) for readOnlyHint=False baseline — caller's explicit readOnlyHint on a synthesized tool always wins (e.g., test fixture needs True)."
  - "WR-01 tests pass GREEN immediately — the _log_callback_exception done_callback was already correctly implemented; the gap was test coverage, not implementation."
  - "Conda env section inserted before ## Quick Start (not between ## Current Status and dev docs) — Quick Start is the natural setup entry point, conda activation logically precedes pip install."

requirements-completed:
  - PROV-02
  - PROV-04
  - PROV-05
  - PROV-06

duration: 22min
completed: 2026-04-19
---

# Phase 7 Plan 03: Registry Provenance Wiring + v1.2 Hygiene Bundle

**register_tool grows provenance= kwarg merging forge-bridge/* meta into mcp.add_tool, readOnlyHint=False baseline for synthesized tools, async callback failure test coverage, ExecutionRecord docstring correction, and README conda env section.**

## Performance

- **Duration:** ~22 min
- **Started:** 2026-04-19T23:27:00Z
- **Completed:** 2026-04-19T23:49:00Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

### Task 1: register_tool provenance kwarg + readOnlyHint baseline (PROV-02 + PROV-04)

- Extended `register_tool` signature with `provenance: dict[str, Any] | None = None`
- Builds `merged_meta` starting with `{"_source": source}`, then adds only `forge-bridge/*` keys from `provenance["meta"]` (defense-in-depth T-07-12 — non-canonical keys dropped)
- Echoes `provenance["tags"]` as `forge-bridge/tags` in meta (only when non-empty — no noise)
- PROV-04: `effective_annotations.setdefault("readOnlyHint", False)` for `source="synthesized"` — caller's explicit annotation wins via setdefault
- `register_tools` (public plural API) signature completely unchanged: `[mcp, fns, prefix, source]`
- All 22 existing `register_builtins` call sites work unchanged (no `provenance=` needed)
- Plan 07-02's `inspect.signature` feature-detect now activates — end-to-end provenance pipeline live
- TDD: RED `1498075` → GREEN `456c5df`, 10 new tests pass

### Task 2: WR-01 async callback failure tests + WR-02 docstring fix (PROV-05)

- Added `test_async_storage_callback_exception_isolated`: verifies JSONL written, WARNING with "storage_callback" logged, no exception propagation
- Added `test_async_storage_callback_exception_does_not_propagate`: verifies `record()` returns `bool` normally when async callback raises
- WR-01 note: `_log_callback_exception` done_callback was already correctly implemented; the gap was test coverage only — tests pass GREEN immediately without implementation changes
- Fixed `ExecutionRecord` docstring (WR-02): replaced "Mirrors the JSONL on-disk schema exactly" with "Mirrors the JSONL row written by ExecutionLog.record()" + cross-reference to `mark_promoted()` partial row shape

### Task 3: README conda env section (PROV-06)

- Inserted `## Conda environment` section before `## Quick Start`
- Covers: `conda create -n forge python=3.11`, activation, `pip install -e ".[dev]"`, `pip install -e ".[dev,llm]"`, projekt-forge git-URL pin note, Python 3.10 minimum
- README grows from 185 to 213 lines

## Task Commits

1. **Task 1 RED — failing TestProvenanceMerge tests** - `1498075` (test)
2. **Task 1 GREEN — register_tool provenance kwarg + readOnlyHint baseline** - `456c5df` (feat)
3. **Task 2 — WR-01 async callback failure tests** - `5d542e7` (test)
4. **Task 2 — WR-02 ExecutionRecord docstring fix** - `c61a449` (fix)
5. **Task 3 — README conda env section** - `daeb34c` (docs)

## Files Created/Modified

- `forge_bridge/mcp/registry.py` — Extended `register_tool` with `provenance` kwarg; merged_meta build logic; PROV-04 readOnlyHint=False baseline for synthesized
- `forge_bridge/learning/execution_log.py` — ExecutionRecord docstring corrected (WR-02 only; no field/type/decorator changes)
- `tests/test_mcp_registry.py` — Appended `TestProvenanceMerge` class: 10 tests covering PROV-02 + PROV-04
- `tests/test_execution_log.py` — Appended 2 WR-01 async callback failure isolation tests
- `README.md` — Added `## Conda environment` section (29 lines)

## Decisions Made

- Tags echoed as `forge-bridge/tags` in `merged_meta` rather than via FastMCP `tags=` param — FastMCP `tags=` is a filter/enable mechanism, not a data channel. `_meta` is the PROV-02 data channel for MCP clients that read `_meta` directly.
- `setdefault` (not assignment) for PROV-04 readOnlyHint=False — so an explicit `annotations={"readOnlyHint": True}` on a synthesized tool wins (e.g., test fixtures).
- WR-01: no implementation change needed — `_log_callback_exception` was already correct; only test coverage was missing.
- Conda env section placed before `## Quick Start` rather than between `## Current Status` and dev docs — Quick Start is the natural environment setup entry point.

## Deviations from Plan

### Note: WR-01 RED phase behavior

The plan's TDD instruction for Task 2 implied tests would fail RED (the gap was "uncovered" code). In practice, the `_log_callback_exception` done_callback was already correctly implemented — the tests passed GREEN immediately. This is not a deviation from correctness: the plan's intent was to add test coverage for an already-working path. The coverage gap (WR-01) is now closed.

## TDD Gate Compliance

- Task 1: RED `1498075` (test) → GREEN `456c5df` (feat) — gate sequence verified
- Task 2: Tests committed as test commit `5d542e7`; implementation was pre-existing (no GREEN needed — the gap was coverage, not missing code). Docstring fix committed as fix `c61a449`.

## Known Stubs

None. All implemented functionality is fully wired:
- `register_tool` now accepts `provenance=` and merges it into `mcp.add_tool` meta
- Plan 07-02's feature-detect guard activates automatically (no code changes needed in watcher.py)
- End-to-end provenance pipeline: sidecar (07-01) → sanitize+read (07-02) → registry merge (07-03)

## Threat Flags

No new threat surface beyond what was declared in the plan's threat model. All T-07-12..T-07-16 mitigations implemented and tested:

- T-07-12 (key injection): `k.startswith("forge-bridge/")` filter enforced, tested by `test_register_tool_drops_non_forge_bridge_meta_keys`
- T-07-13 (auto-approval elevation): `readOnlyHint=False` baseline enforced, tested by `test_register_tool_synthesized_defaults_readonly_false`
- T-07-14 (`_source` repudiation): `_source` set first and never overwritten, tested by `test_register_tool_preserves_source_tag_with_provenance`
- T-07-15 (async callback DoS): `_log_callback_exception` isolation path now covered by 2 new tests (WR-01)
- T-07-16 (public API drift): signature stability test `test_register_tools_signature_unchanged` enforces `[mcp, fns, prefix, source]`

## Self-Check: PASSED

- FOUND: forge_bridge/mcp/registry.py
- FOUND: forge_bridge/learning/execution_log.py
- FOUND: tests/test_mcp_registry.py
- FOUND: tests/test_execution_log.py
- FOUND: README.md
- FOUND commit: 1498075 (test: RED TestProvenanceMerge)
- FOUND commit: 456c5df (feat: register_tool provenance kwarg)
- FOUND commit: 5d542e7 (test: WR-01 async callback)
- FOUND commit: c61a449 (fix: WR-02 docstring)
- FOUND commit: daeb34c (docs: README conda env)
- pytest tests/test_mcp_registry.py: 20 passed (10 new + 10 existing)
- pytest tests/test_execution_log.py: 23 passed (2 new + 21 existing)
- pytest tests/: 270 passed (no regressions)

---
*Phase: 07-tool-provenance-in-mcp-annotations*
*Completed: 2026-04-19*
