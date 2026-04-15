---
phase: 3
slug: learning-pipeline
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| 03-01-01 | 01 | 1 | LEARN-01 | — | N/A | unit | `python -m pytest tests/test_learning.py -x -q` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | LEARN-02 | — | N/A | unit | `python -m pytest tests/test_learning.py -x -q` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 2 | LEARN-03, LEARN-04 | — | N/A | unit | `python -m pytest tests/test_synthesizer.py -x -q` | ❌ W0 | ⬜ pending |
| 03-02-02 | 02 | 2 | LEARN-05 | — | N/A | unit | `python -m pytest tests/test_synthesizer.py -x -q` | ❌ W0 | ⬜ pending |
| 03-03-01 | 03 | 2 | LEARN-06, LEARN-07 | — | N/A | unit | `python -m pytest tests/test_probation.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_learning.py` — stubs for LEARN-01, LEARN-02
- [ ] `tests/test_synthesizer.py` — stubs for LEARN-03, LEARN-04, LEARN-05
- [ ] `tests/test_probation.py` — stubs for LEARN-06, LEARN-07

*Existing infrastructure covers framework and fixtures.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Hot-reload appears in MCP tool list | LEARN-08 | Requires running MCP server | Start server, drop .py in synthesized/, verify `tools/list` |
| Quarantined tool removed from list | LEARN-09 | Requires live server + failure injection | Trigger failures past threshold, verify tool disappears |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
