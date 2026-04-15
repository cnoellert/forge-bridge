---
phase: 1
slug: tool-parity-llm-router
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-14
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + pytest-asyncio |
| **Config file** | `pyproject.toml` (asyncio_mode = "auto") |
| **Quick run command** | `python -m pytest tests/ -x -q --timeout=10` |
| **Full suite command** | `python -m pytest tests/ -v --timeout=30` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q --timeout=10`
- **After every plan wave:** Run `python -m pytest tests/ -v --timeout=30`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | TOOL-01–09 | unit | `pytest tests/test_tools.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | LLM-01–04 | unit | `pytest tests/test_llm_router.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | LLM-05,08 | unit | `pytest tests/test_packaging.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | LLM-06,07 | unit | `pytest tests/test_llm_health.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_tools.py` — stubs for TOOL-01 through TOOL-09
- [ ] `tests/test_llm_router.py` — stubs for LLM-01 through LLM-04
- [ ] `tests/test_packaging.py` — stubs for LLM-05, LLM-08
- [ ] `tests/test_llm_health.py` — stubs for LLM-06, LLM-07
- [ ] `tests/conftest.py` — shared fixtures (mock bridge, mock LLM backends)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| MCP tools callable from Claude Desktop | TOOL-01–09 | Requires live Flame + Claude Desktop | Start MCP server, verify tools appear in Claude Desktop tool list |
| forge://llm/health MCP resource | LLM-07 | Requires MCP client connection | Connect MCP client, read forge://llm/health resource |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
