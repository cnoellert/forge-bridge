---
phase: 4
slug: api-surface-hardening
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-16
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + pytest-asyncio |
| **Config file** | pyproject.toml [tool.pytest.ini_options] |
| **Quick run command** | `pytest tests/ -x --no-header -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x --no-header -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green + grep gates (success criterion #1 and #5) must pass
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | API-01..05, PKG-01..03 | — | N/A | unit+smoke | `pytest tests/ -v` | ❌ W0 (test_public_api.py) | ⬜ pending |

*Planner fills this table after task breakdown. See RESEARCH.md §Validation Architecture for the 21 mapped assertions.*

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_public_api.py` — new file, stubs for clean-venv import smoke test + `__all__` assertions
- [ ] Test additions inside `tests/test_llm.py` for D-05/D-06/D-07 injection precedence (existing file)
- [ ] Test additions inside `tests/test_synthesizer.py` for D-17/D-18/D-19 class migration (existing file, 7 call sites on lines 147-242 must migrate atomically with D-19)
- [ ] Test additions inside `tests/test_mcp_registry.py` for D-14/D-15 post-run guard (existing file)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Clean-venv importability | API-01 | Requires isolated venv; not run in CI loop | `python -m venv /tmp/fb-verify && /tmp/fb-verify/bin/pip install -e . && /tmp/fb-verify/bin/python -c "from forge_bridge import LLMRouter, ExecutionLog, SkillSynthesizer, register_tools, get_mcp, startup_bridge, shutdown_bridge, execute, execute_json, execute_and_read, get_router"` |
| PKG-03 grep gate | PKG-03 | String scan of whole package | `grep -rn "portofino\|assist-01\|ACM_" forge_bridge/ --include="*.py"` must return zero matches |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
