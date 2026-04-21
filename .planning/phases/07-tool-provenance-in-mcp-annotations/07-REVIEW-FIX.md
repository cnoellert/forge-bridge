---
phase: 07-tool-provenance-in-mcp-annotations
fixed_at: 2026-04-21T00:00:00Z
review_path: .planning/phases/07-tool-provenance-in-mcp-annotations/07-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 7: Code Review Fix Report

**Fixed at:** 2026-04-21T00:00:00Z
**Source review:** `.planning/phases/07-tool-provenance-in-mcp-annotations/07-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (Critical + Warning; Info deferred)
- Fixed: 4
- Skipped: 0

All four Phase 7 warnings from REVIEW.md have been fixed, tested, and committed atomically. Full test suite (278 tests) green after each fix; targeted PROV test suites (71 tests across `test_mcp_registry.py` + `test_watcher.py` + `test_sanitize.py`) all pass.

## Fixed Issues

### WR-04: README installer URL pins stale version `v1.1.0`

**Files modified:** `README.md`
**Commit:** `96209cb`
**Applied fix:** Bumped both occurrences of the installer version pin from `v1.1.0` to `v1.2.1` — the `curl` one-liner URL on line 106 and the `FORGE_BRIDGE_VERSION` parenthetical default on line 109. Verified `git describe --tags --abbrev=0` returns `v1.2.1`, confirming the pin now matches the shipped version (includes startup-bridge graceful-degradation hotfix and all PROV-* work).

### WR-03: Dead feature-detection branch in `_scan_once`

**Files modified:** `forge_bridge/learning/watcher.py`
**Commit:** `c6eeedf`
**Applied fix:** Removed the `inspect.signature(register_tool).parameters` feature-detect and the Wave-2 fallback call `register_tool(mcp, fn, name=stem, source="synthesized")`. The watcher now unconditionally calls `register_tool(..., provenance=provenance)`. Also removed the now-unused `import inspect` at module top. Rationale: Wave 2 and Wave 3 have both landed in Phase 7 (`registry.py:58` shows `provenance` as a permanent kwarg); the per-scan reflection cost on every 5 s poll and the silent-regression hazard (a future refactor dropping the kwarg would fall through to the no-provenance path undetected) are both eliminated. All 19 existing watcher tests still pass.

### WR-02: `_read_sidecar` trusts `tags`/`meta` field type

**Files modified:** `forge_bridge/learning/watcher.py`, `tests/test_watcher.py`
**Commit:** `3617b90`
**Applied fix:** Added explicit `isinstance(..., list)` and `isinstance(..., dict)` type-guards before the `raw = {...}` construction in both the sidecar and legacy `.tags.json` paths. A non-list `tags` field (e.g. `"tags": "project:acme"`) or non-dict `meta` field (e.g. `"meta": 42`) now logs a targeted `.sidecar.json for <stem> has non-list tags field — skipping provenance` (or `non-dict meta field`) warning and returns `None`, rather than iterating per-character or crashing inside `_scan_once`'s try-block. Added three new regression tests: `test_non_list_tags_field_returns_none_with_warning`, `test_non_dict_meta_field_returns_none_with_warning`, and `test_legacy_tags_json_non_list_tags_returns_none`. 22 watcher tests pass (19 prior + 3 new).

### WR-01: `register_tool` does not apply `apply_size_budget` to caller-supplied `provenance`

**Files modified:** `forge_bridge/mcp/registry.py`, `forge_bridge/learning/sanitize.py`, `tests/test_mcp_registry.py`
**Commit:** `1c840fa`
**Applied fix:** Added a top-level `from forge_bridge.learning.sanitize import apply_size_budget` import to `registry.py` and threaded it into the provenance branch of `register_tool`. Caller-supplied `provenance` payloads now go through `apply_size_budget({"tags": ..., "meta": ...})` before the forge-bridge/* namespace filter and the `forge-bridge/tags` attachment. Non-watcher callers (plugins, tests, future synthesizer shortcuts) are now prevented from pushing unbounded meta bytes or tag counts onto the MCP wire.

**Deviation from REVIEW.md fix suggestion:** The review proposed re-running per-tag `_sanitize_tag` at the write boundary. I deliberately did NOT do that. Reason: the watcher prepends the literal `"synthesized"` filter tag (TS-02.1 contract) AFTER its own sanitization pass; re-running `_sanitize_tag` at the registry would redact `"synthesized"` to `redacted:<hash>` (it has no allowlisted prefix). That would silently break the `"synthesized"` client filter AND break the existing `test_register_tool_merges_provenance_into_meta` test which asserts `meta["forge-bridge/tags"] == ["synthesized", "project:acme"]`. The correct split is: watcher is the PROV-03 content boundary (sanitize + budget), registry is the PROV-03 shape boundary (budget only). Updated the `sanitize.py:15` module docstring to accurately describe this split so the next reader doesn't trip on the same rake.

Added three new write-boundary tests to `TestProvenanceMerge`: `test_register_tool_applies_size_budget_to_tags` (caps at `MAX_TAGS_PER_TOOL=16` even when caller hands 30 tags), `test_register_tool_applies_size_budget_to_meta` (non-canonical `forge-bridge/noise` key is evicted when it pushes meta over `MAX_META_BYTES=4096`; canonical `forge-bridge/origin` survives), and `test_register_tool_preserves_synthesized_literal_tag` (the TS-02.1 literal passes through unmodified — regression guard against accidentally adding `_sanitize_tag` at the write boundary in the future). 23 registry tests pass (20 prior + 3 new).

**Full test suite:** 278 passed, 2 warnings. No regressions.

---

_Fixed: 2026-04-21T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
