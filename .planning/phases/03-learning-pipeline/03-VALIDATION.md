---
phase: 3
slug: learning-pipeline
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-14
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | LEARN-01, LEARN-02, LEARN-03, LEARN-04, LEARN-05, LEARN-06 | — | N/A | unit | `python -m pytest tests/test_execution_log.py -x -q` | TDD inline | ⬜ pending |
| 03-01-02 | 01 | 1 | LEARN-11 | — | N/A | unit | `python -m pytest tests/test_execution_log.py tests/test_core.py -x -q` | TDD inline | ⬜ pending |
| 03-02-01 | 02 | 2 | LEARN-07, LEARN-08, LEARN-09 | — | N/A | unit | `python -m pytest tests/test_synthesizer.py -x -q` | TDD inline | ⬜ pending |
| 03-03-01 | 03 | 2 | LEARN-10 | — | N/A | unit | `python -m pytest tests/test_probation.py -x -q` | TDD inline | ⬜ pending |
| 03-03-02 | 03 | 2 | LEARN-10 | — | N/A | unit | `python -m pytest tests/test_watcher.py tests/test_probation.py -x -q` | tests/test_watcher.py exists | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

All plans in this phase use TDD (`tdd="true"` on tasks). Tests are written first as part of each task's RED-GREEN-REFACTOR cycle. No separate Wave 0 plan is needed.

- [x] `tests/test_execution_log.py` — created inline by 03-01 Task 1 (TDD)
- [x] `tests/test_synthesizer.py` — created inline by 03-02 Task 1 (TDD)
- [x] `tests/test_probation.py` — created inline by 03-03 Task 1 (TDD)
- [x] `tests/test_core.py` — exists from Phase 1/2

*Existing infrastructure covers framework and fixtures.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Hot-reload appears in MCP tool list | LEARN-08 | Requires running MCP server | Start server, drop .py in synthesized/, verify `tools/list` |
| Quarantined tool removed from list | LEARN-09 | Requires live server + failure injection | Trigger failures past threshold, verify tool disappears |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved — TDD tasks create tests inline before implementation
