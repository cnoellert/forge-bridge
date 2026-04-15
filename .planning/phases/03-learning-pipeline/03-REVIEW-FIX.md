---
status: all_fixed
phase: 03-learning-pipeline
findings_in_scope: 7
fixed: 7
skipped: 0
iteration: 1
---

# Code Review Fix Report: Phase 03

## Summary
All 7 critical and warning findings from the phase 03 code review have been fixed across 5 atomic commits. Two new test cases were added for manifest validation (CR-001). Full test suite passes (159 tests, 0 failures).

## Fixes Applied

### CR-001: Arbitrary code execution through synthesized tool loading
**Status:** fixed
**Commit:** 558c9b5 (synthesizer side) + 4ba5a8f (watcher side)
**What changed:** Created `forge_bridge/learning/manifest.py` with `manifest_register()` and `manifest_verify()` functions backed by `~/.forge-bridge/synthesized/.manifest.json` (filename -> sha256). The synthesizer registers every file it writes. The watcher verifies files against the manifest before loading and rejects unregistered or tampered files. Two new test cases validate rogue file rejection and tampered content rejection.

### CR-002: Synthesizer dry-run executes LLM-generated code without sandboxing
**Status:** fixed
**Commit:** 558c9b5
**What changed:** Added `_check_safety(tree: ast.Module) -> bool` function that walks the AST and rejects code containing dangerous calls: `eval`, `exec`, `__import__`, `compile`, `open`, `os.system`, `os.popen`, `subprocess.*`, `shutil.rmtree`, and related functions. The check runs between signature validation and dry-run (Stage 2b), preventing dangerous code from ever being executed.

### WR-001: Race condition in ExecutionLog file writes
**Status:** fixed
**Commit:** 027bf28
**What changed:** Added `import fcntl` at module level. Wrapped file write operations in both `record()` and `mark_promoted()` with `fcntl.flock(fp, fcntl.LOCK_EX)` / `fcntl.flock(fp, fcntl.LOCK_UN)` in try/finally blocks for exclusive file locking during concurrent writes.

### WR-002: Quarantine overwrites existing file without backup
**Status:** fixed
**Commit:** a5abb2f
**What changed:** Before `src.rename(dest)`, added a check for `dest.exists()`. If the destination file already exists, a Unix timestamp suffix is appended to the filename (e.g., `tool_name_1713100000.py`) to preserve the previously quarantined version.

### WR-003: `_extract_function` fragile markdown fence parsing
**Status:** fixed
**Commit:** 558c9b5
**What changed:** Replaced the fragile `split("```")` approach with a `re.search(r"```(?:\w*)\n(.*?)```", raw, re.DOTALL | re.MULTILINE)` regex pattern that robustly handles language tags, multiline content, and edge cases.

### WR-004: Watcher `_scan_once` imports inside loop body
**Status:** fixed
**Commit:** 4ba5a8f
**What changed:** Moved `from forge_bridge.mcp.registry import register_tool` from inside the per-file loop to the top of `_scan_once()`, before the loop begins.

### WR-005: `configure()` in bridge.py mutates module-level globals without thread safety
**Status:** fixed
**Commit:** 0536b7e
**What changed:** Created a frozen `_BridgeConfig` dataclass with `host`, `port`, `timeout`, and a computed `url` property. `configure()` now builds a new immutable instance and swaps the module-level `_config` reference atomically. `execute()` snapshots `_config` once per call to avoid torn reads. Legacy module-level names (BRIDGE_HOST, etc.) are kept in sync for backward compatibility.

## Test Results
```
159 passed, 2 warnings in 2.37s
```
