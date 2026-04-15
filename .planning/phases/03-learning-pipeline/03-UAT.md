---
status: complete
phase: 03-learning-pipeline
source: [03-01-SUMMARY.md, 03-02-SUMMARY.md, 03-03-SUMMARY.md]
started: 2026-04-15T00:00:00Z
updated: 2026-04-15T00:15:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Import chain — all learning modules load cleanly
expected: All learning pipeline modules import without errors — ExecutionLog, normalize_and_hash, synthesize, ProbationTracker, set_execution_callback.
result: pass

### 2. AST normalization — literal-variant code produces same hash
expected: normalize_and_hash("seg.name = 'ACM_0010'") and normalize_and_hash("seg.name = 'ACM_0020'") return the same hash.
result: pass

### 3. JSONL round-trip — record, promote, replay
expected: ExecutionLog records 3 identical codes, third returns True (promotion). Replay rebuilds counter to 3 without re-triggering promotion.
result: pass

### 4. Bridge callback hook — set and clear
expected: set_execution_callback(fn) sets callback, set_execution_callback() clears it. Default is None.
result: pass

### 5. Synthesizer validation — rejects bad code
expected: _check_signature rejects non-async, missing synth_ prefix, missing docstring, missing return annotation, multiple functions. All return None.
result: pass

### 6. Synthesizer safety — AST blocklist
expected: Code containing os.system, subprocess.run, eval(), exec(), __import__ is blocked before dry-run.
result: pass

### 7. Probation quarantine — file move on threshold breach
expected: After 3 failures, tool file moved from synthesized/ to quarantined/, mcp.remove_tool called, file preserved.
result: pass

### 8. Watcher manifest — rejects unregistered files
expected: Rogue .py file placed in synthesized/ without manifest entry is refused. Warning logged.
result: pass

### 9. Path contract — synthesizer and watcher share SYNTHESIZED_DIR
expected: synthesizer.SYNTHESIZED_DIR is watcher.SYNTHESIZED_DIR (identity, not just equality).
result: pass

### 10. Full test suite — no regressions
expected: python -m pytest passes all 159 tests with zero failures.
result: pass

## Summary

total: 10
passed: 10
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none]
