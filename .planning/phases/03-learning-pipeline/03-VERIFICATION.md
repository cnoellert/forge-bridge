---
phase: 03-learning-pipeline
verified: 2026-04-15T05:00:00Z
status: passed
score: 4/4 must-haves verified
---

# Phase 3: Learning Pipeline Verification Report

**Phase Goal:** The bridge observes repeated Flame operations, synthesizes them into reusable MCP tools, hot-registers them in the live server, and tracks their reliability via a probation system
**Verified:** 2026-04-15T05:00:00Z
**Status:** passed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Every Flame execution (when opt-in callback is active) is appended to ~/.forge-bridge/executions.jsonl; the log survives process kill and is fully replayed on restart without re-triggering synthesis for already-promoted hashes | VERIFIED | `ExecutionLog.record()` appends JSONL with flush; `_replay()` rebuilds counters and `_promoted` set from JSONL; test `test_replay_promoted_does_not_reemit` confirms no re-trigger; `bridge.py` callback guarded by `_on_execution_callback is not None` (off by default) |
| 2 | After a code pattern crosses the promotion threshold (default 3), the synthesizer generates a Python async MCP tool, validates it (ast.parse + signature check + dry-run), and writes it to mcp/synthesized/ | VERIFIED | `ExecutionLog.record()` returns True at threshold (test `test_record_returns_true_at_threshold`); `synthesize()` calls LLM with `sensitive=True`, runs 3-stage validation (`ast.parse`, `_check_signature`, `_dry_run`), writes to `SYNTHESIZED_DIR`; 17 synthesizer tests pass |
| 3 | A newly synthesized tool appears in the MCP tool list under synth_* prefix without a server restart | VERIFIED | `watcher.py` `_scan_once()` polls `SYNTHESIZED_DIR`, loads new `.py` files via `importlib`, registers via `register_tool(mcp, fn, name=stem, source="synthesized")`; test `test_new_file_registers_tool` confirms; `SYNTHESIZED_DIR` shared between synthesizer and watcher (contract test `test_synthesized_dir_is_same_object_as_watcher`) |
| 4 | A synthesized tool that fails probation (breach of failure threshold) is quarantined and removed from the tool list without being deleted from disk | VERIFIED | `ProbationTracker.quarantine()` moves file to `~/.forge-bridge/quarantined/` via `Path.rename()` and calls `mcp.remove_tool()`; watcher threads `tracker.wrap()` before registration; test `test_triggers_quarantine_at_threshold` confirms full flow; quarantined file preserved (not deleted) |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `forge_bridge/learning/execution_log.py` | ExecutionLog class with JSONL persistence, AST normalization, promotion counters | VERIFIED | 162 lines, exports `ExecutionLog`, `normalize_and_hash`, `_LiteralStripper`; all methods substantive |
| `forge_bridge/bridge.py` | `set_execution_callback()` hook and callback invocation in `execute()` | VERIFIED | `_on_execution_callback` at line 26, `set_execution_callback()` at line 29, callback invocation at lines 133-137 with try/except guard |
| `tests/test_execution_log.py` | Unit tests for execution log, normalization, replay, promotion, callback | VERIFIED | 16 tests (13 execution log + 3 callback), all pass |
| `forge_bridge/learning/synthesizer.py` | synthesize() async function, validation pipeline, LLM prompt templates | VERIFIED | 233 lines, exports `synthesize`, `_extract_function`, `_check_signature`, `_dry_run`; uses `sensitive=True`; imports `SYNTHESIZED_DIR` from watcher |
| `tests/test_synthesizer.py` | Unit tests for synthesis, validation stages, error handling, path contract | VERIFIED | 17 tests across 5 test classes, all pass; includes contract test |
| `forge_bridge/learning/probation.py` | ProbationTracker with wrap(), quarantine(), success/failure tracking | VERIFIED | 91 lines, exports `ProbationTracker` with all required methods |
| `tests/test_probation.py` | Unit tests for probation tracking, quarantine, threshold behavior | VERIFIED | 14 tests across 7 test classes, all pass |
| `forge_bridge/learning/watcher.py` | Updated with optional tracker parameter | VERIFIED | `tracker` parameter on both `watch_synthesized_tools` and `_scan_once`; `tracker.wrap(fn, stem, mcp)` at line 80 |
| `tests/test_watcher.py` | Updated tests covering tracker integration | VERIFIED | 2 new tests in `TestWatcherTrackerIntegration`, all pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `bridge.py` | `execution_log.py` | `_on_execution_callback(code, response)` | WIRED | Callback variable at line 26, invocation at line 134, guarded by try/except |
| `execution_log.py` | `~/.forge-bridge/executions.jsonl` | `open(path, 'a') append` | WIRED | Line 130: `open(self._path, "a")` with `json.dumps(rec) + "\n"` and `fp.flush()` |
| `synthesizer.py` | `llm/router.py` | `get_router().acomplete(prompt, sensitive=True)` | WIRED | Line 185: `await get_router().acomplete(prompt, sensitive=True, system=SYNTH_SYSTEM, temperature=0.1)` |
| `synthesizer.py` | `watcher.py` | `from forge_bridge.learning.watcher import SYNTHESIZED_DIR` | WIRED | Line 21; contract test proves identity (`synth_dir is watch_dir`) |
| `synthesizer.py` | `~/.forge-bridge/synthesized/` | `SYNTHESIZED_DIR / f"{fn_name}.py"` write | WIRED | Line 230: `output_path.write_text(fn_code)` |
| `probation.py` | `watcher.py` | `tracker.wrap(fn, stem, mcp)` | WIRED | watcher.py line 80: `fn = tracker.wrap(fn, stem, mcp)` |
| `probation.py` | `~/.forge-bridge/quarantined/` | `src.rename(dest)` | WIRED | Line 76: `src.rename(self._quarantine_dir / f"{tool_name}.py")` |
| `probation.py` | `mcp` | `mcp.remove_tool(tool_name)` | WIRED | Line 81: `mcp.remove_tool(tool_name)` with try/except guard |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| LEARN-01 | 03-01 | Create forge_bridge/learning/ package with execution_log.py | SATISFIED | `forge_bridge/learning/execution_log.py` exists, 162 lines, fully implemented |
| LEARN-02 | 03-01 | JSONL execution log at ~/.forge-bridge/executions.jsonl with append-only writes | SATISFIED | `LOG_PATH` constant, `open(self._path, "a")` with flush |
| LEARN-03 | 03-01 | Replay JSONL on startup to rebuild in-memory promotion counters | SATISFIED | `_replay()` in `__init__`, rebuilds `_counters`, `_promoted`, `_code_by_hash` |
| LEARN-04 | 03-01 | AST-based code normalization and SHA-256 hash fingerprinting | SATISFIED | `_LiteralStripper(ast.NodeTransformer)`, `normalize_and_hash()` with SHA-256 |
| LEARN-05 | 03-01 | Promotion threshold counter (configurable, default 3) returning promoted=True signal | SATISFIED | `FORGE_PROMOTION_THRESHOLD` env var, threshold check in `record()` |
| LEARN-06 | 03-01 | Intent tracking -- optional intent string logged alongside code | SATISFIED | `intent` parameter on `record()`, stored in JSONL and `_intent_by_hash` |
| LEARN-07 | 03-02 | Create forge_bridge/learning/synthesizer.py targeting Python MCP tools | SATISFIED | `synthesizer.py` exists with `synthesize()`, produces `synth_*.py` files |
| LEARN-08 | 03-02 | Synthesizer uses LLM router with sensitive=True (always local) | SATISFIED | `get_router().acomplete(prompt, sensitive=True, ...)` at line 185 |
| LEARN-09 | 03-02 | Synthesized tool validation: ast.parse, signature check, dry-run | SATISFIED | 3-stage pipeline: `ast.parse` -> `_check_signature` -> `_dry_run` |
| LEARN-10 | 03-03 | Probation system: success/failure counters, quarantine on threshold breach | SATISFIED | `ProbationTracker` with `wrap()`, `quarantine()`, file move to quarantined/ |
| LEARN-11 | 03-01 | Wire execution logging into bridge.py as optional on_execution callback | SATISFIED | `_on_execution_callback`, `set_execution_callback()`, invocation in `execute()` |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| -- | -- | None found | -- | -- |

No TODOs, FIXMEs, placeholders, stub returns, or console.log-only implementations found in any phase 3 files.

### Human Verification Required

### 1. End-to-End Pipeline Flow

**Test:** With Flame running, set execution callback, execute the same code pattern 3+ times, verify synthesized tool appears in MCP tool list.
**Expected:** A `synth_*.py` file is created in `~/.forge-bridge/synthesized/` and the watcher auto-registers it.
**Why human:** Requires live Flame instance with bridge hook and running MCP server.

### 2. LLM Quality of Synthesized Code

**Test:** Trigger synthesis with real local LLM (Ollama), inspect generated `synth_*.py` for correctness.
**Expected:** Generated function is syntactically valid, has correct bridge calls, and meaningful parameter extraction.
**Why human:** Tests mock the LLM; real LLM output quality cannot be verified programmatically.

### 3. Quarantine Under Real Load

**Test:** Register a synthesized tool that calls a nonexistent Flame API, invoke it 3+ times, verify quarantine.
**Expected:** Tool file moved to `~/.forge-bridge/quarantined/`, tool removed from MCP list.
**Why human:** Requires running MCP server with real FastMCP instance to verify remove_tool behavior.

### Gaps Summary

No gaps found. All 11 requirements (LEARN-01 through LEARN-11) are satisfied. All 4 success criteria from the roadmap are verified through code inspection and 157 passing tests (56 directly related to phase 3). The learning pipeline components are fully implemented, substantive, and properly wired together.

---

_Verified: 2026-04-15T05:00:00Z_
_Verifier: Claude (gsd-verifier)_
