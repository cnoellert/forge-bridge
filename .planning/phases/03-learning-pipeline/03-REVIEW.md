---
status: findings
phase: 03-learning-pipeline
depth: standard
files_reviewed: 9
findings:
  critical: 2
  warning: 5
  info: 3
  total: 10
---

# Code Review: Phase 03 — Learning Pipeline

## Summary

The learning pipeline is well-structured with clean separation of concerns across execution logging, synthesis, probation, and watching. Two critical issues involve arbitrary code execution via `importlib` without sandboxing and a path traversal vector in the watcher. Several warnings around race conditions, resource handling, and missing validation round out the findings.

## Findings

### CR-001: Arbitrary code execution through synthesized tool loading
**Severity:** critical
**File:** `forge_bridge/learning/watcher.py`:100-115
**Description:** `_load_fn` calls `spec.loader.exec_module(module)` on any `.py` file found in the synthesized directory. If an attacker can write a file to `~/.forge-bridge/synthesized/` (or the directory is world-writable), they get arbitrary code execution in the bridge process. The synthesizer validates LLM output before writing, but nothing prevents external file placement.
**Recommendation:** Add file-origin validation before loading. Options: (1) maintain a manifest of files the synthesizer wrote (hash + path) and refuse to load anything not in the manifest, (2) check file ownership/permissions match the current user, or (3) sign synthesized files with an HMAC using a local secret and verify before loading.

### CR-002: Synthesizer dry-run executes LLM-generated code without sandboxing
**Severity:** critical
**File:** `forge_bridge/learning/synthesizer.py`:105-150
**Description:** `_dry_run` loads and executes LLM-generated Python code via `importlib` and actually calls the function. While bridge calls are mocked, the code can contain arbitrary side effects at import time (module-level code) or inside the function body (file I/O, network calls, os.system, etc.). The AST signature check only validates structure, not content safety.
**Recommendation:** Add an AST-level import/call blocklist before dry-run (reject `os.system`, `subprocess`, `eval`, `exec`, `__import__`, `open` outside bridge calls). Consider running dry-run in a subprocess with restricted permissions or a `seccomp` sandbox. At minimum, document the trust boundary clearly.

### WR-001: Race condition in ExecutionLog file writes
**Severity:** warning
**File:** `forge_bridge/learning/execution_log.py`:128-132
**Description:** `record()` opens the JSONL file in append mode without any file locking. If two async tasks or processes call `record()` concurrently, JSONL lines could interleave and corrupt the log. The `_counters` dict is also not protected against concurrent modification in an async context (though CPython's GIL mitigates this for single-process use).
**Recommendation:** Use `fcntl.flock` (Unix) or `msvcrt.locking` (Windows) around file writes, or use an asyncio lock to serialize access to both the file and in-memory state.

### WR-002: Quarantine overwrites existing file without backup
**Severity:** warning
**File:** `forge_bridge/learning/probation.py`:73-77
**Description:** `quarantine()` uses `src.rename(dest)` which will silently overwrite `dest` on Unix if a file with the same name already exists in the quarantine directory (e.g., from a previous quarantine of a regenerated tool). The prior quarantined version is lost.
**Recommendation:** Check if dest exists and, if so, rename with a timestamp suffix (e.g., `tool_name.2026-04-14T12:00:00.py`) to preserve forensic history.

### WR-003: `_extract_function` fragile markdown fence parsing
**Severity:** warning
**File:** `forge_bridge/learning/synthesizer.py`:57-69
**Description:** The fence-stripping logic splits on ` ``` ` and takes `parts[1]`. If the LLM output contains triple backticks inside the code (e.g., in a docstring), this will truncate the function. The language-tag check (`lines[0].strip().isalpha()`) also fails for tags like `python3` or `py` with digits, though `isalpha()` happens to work for common cases.
**Recommendation:** Use a regex like `` ^```\w*\n(.*?)^``` `` with `re.DOTALL | re.MULTILINE` for more robust extraction. Or find the first and last fence lines by index rather than splitting.

### WR-004: Watcher `_scan_once` imports inside loop body
**Severity:** warning
**File:** `forge_bridge/learning/watcher.py`:81
**Description:** `from forge_bridge.mcp.registry import register_tool` is imported inside the `for` loop body of `_scan_once`. While Python caches imports after the first load, performing the import lookup on every file scan iteration is unnecessary overhead and obscures the dependency.
**Recommendation:** Move the import to the top of the function or to the module level (using `TYPE_CHECKING` guard if needed to avoid circular imports at module load time).

### WR-005: `configure()` in bridge.py mutates module-level globals without thread safety
**Severity:** warning
**File:** `forge_bridge/bridge.py`:35-44
**Description:** `configure()` mutates `BRIDGE_HOST`, `BRIDGE_PORT`, `BRIDGE_TIMEOUT`, and `BRIDGE_URL` as module globals. If `configure()` is called while an `execute()` call is in-flight (reading `BRIDGE_URL`), the URL could be inconsistent (e.g., old host with new port). This is unlikely in practice but is a latent bug.
**Recommendation:** Bundle connection settings into an immutable dataclass or namedtuple and swap the reference atomically, or use a lock.

### IR-001: `normalize_and_hash` does not handle `ast.fix_missing_locations`
**Severity:** info
**File:** `forge_bridge/learning/execution_log.py`:43-48
**Description:** After `_LiteralStripper().visit(tree)`, `ast.fix_missing_locations(tree)` is not called before `ast.unparse(tree)`. This works in practice because `unparse` does not require location info, but it is technically incorrect per the `ast.NodeTransformer` documentation which recommends calling `fix_missing_locations` after transformation.
**Recommendation:** Add `ast.fix_missing_locations(tree)` after the visitor for correctness.

### IR-002: Tests use `asyncio.run()` instead of pytest-asyncio
**Severity:** info
**File:** `tests/test_probation.py`:69, 82, 94
**Description:** The probation tests use `asyncio.run(wrapped())` to test async wrappers, while the synthesizer tests use `@pytest.mark.asyncio`. This inconsistency works but means probation tests create a new event loop per call rather than reusing the test event loop. This can mask bugs that depend on event loop state.
**Recommendation:** Use `@pytest.mark.asyncio` and `await` consistently across all async test cases.

### IR-003: Test files import inside test functions
**Severity:** info
**File:** `tests/test_execution_log.py` (multiple locations), `tests/test_synthesizer.py` (multiple locations)
**Description:** Many test functions import from `forge_bridge.learning.*` inside the function body rather than at the module top. While this works and can avoid import-time side effects, it is inconsistent (e.g., `test_watcher.py` and `test_probation.py` use top-level imports). The pattern also makes it harder to see what a test file depends on at a glance.
**Recommendation:** Standardize on top-level imports for test files unless there is a specific reason to defer (e.g., monkeypatching environment variables before import).

## Files Reviewed

| File | Notes |
|------|-------|
| `forge_bridge/bridge.py` | Clean HTTP client. Global mutable state (WR-005). Callback error swallowing is intentional and documented. |
| `forge_bridge/learning/execution_log.py` | Solid JSONL append-only log with AST normalization. Race condition on concurrent writes (WR-001). Minor AST hygiene (IR-001). |
| `forge_bridge/learning/probation.py` | Clean tracker with quarantine. Overwrite risk on quarantine (WR-002). |
| `forge_bridge/learning/synthesizer.py` | 3-stage validation pipeline. LLM code execution without sandboxing (CR-002). Fragile fence parsing (WR-003). |
| `forge_bridge/learning/watcher.py` | Polling-based hot-loader. Unsandboxed file loading (CR-001). Import inside loop (WR-004). |
| `tests/test_execution_log.py` | Good coverage of recording, replay, promotion, env var override, and callback hooks. |
| `tests/test_probation.py` | Thorough coverage of tracking, wrapping, quarantine, and edge cases. |
| `tests/test_synthesizer.py` | Covers all 3 validation stages, collision handling, and path contract. |
| `tests/test_watcher.py` | Covers new/changed/deleted files, dunder skipping, tracker integration. |
