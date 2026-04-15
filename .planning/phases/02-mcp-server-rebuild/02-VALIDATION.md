---
phase: 2
slug: mcp-server-rebuild
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-14
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (already installed) |
| **Config file** | `pyproject.toml` — `[tool.pytest.ini_options]` asyncio_mode = "auto" |
| **Quick run command** | `pytest tests/test_mcp_registry.py tests/test_watcher.py -x` |
| **Full suite command** | `pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_mcp_registry.py tests/test_watcher.py -x`
- **After every plan wave:** Run `pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 0 | MCP-01 | unit | `pytest tests/test_mcp_registry.py::test_builtin_namespace -x` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 0 | MCP-01 | unit | `pytest tests/test_mcp_registry.py::test_synth_prefix_rejected_from_static -x` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 0 | MCP-02 | unit | `pytest tests/test_mcp_registry.py::test_dynamic_registration -x` | ❌ W0 | ⬜ pending |
| 02-01-04 | 01 | 0 | MCP-03 | unit | `pytest tests/test_watcher.py::test_watcher_loads_new_file -x` | ❌ W0 | ⬜ pending |
| 02-01-05 | 01 | 0 | MCP-03 | unit | `pytest tests/test_watcher.py::test_watcher_reloads_changed_file -x` | ❌ W0 | ⬜ pending |
| 02-01-06 | 01 | 0 | MCP-03 | unit | `pytest tests/test_watcher.py::test_watcher_removes_deleted_file -x` | ❌ W0 | ⬜ pending |
| 02-01-07 | 01 | 0 | MCP-04 | unit | `pytest tests/test_mcp_registry.py::test_register_tools_api -x` | ❌ W0 | ⬜ pending |
| 02-01-08 | 01 | 0 | MCP-05 | unit | `pytest tests/test_mcp_registry.py::test_source_tagging -x` | ❌ W0 | ⬜ pending |
| 02-01-09 | 01 | 0 | MCP-06 | unit | `pytest tests/test_mcp_registry.py::test_synth_name_enforcement -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_mcp_registry.py` — stubs for MCP-01, MCP-02, MCP-04, MCP-05, MCP-06
- [ ] `tests/test_watcher.py` — stubs for MCP-03
- [ ] `pyproject.toml` — pytest-asyncio config if not present

*Existing infrastructure covers pytest framework; Wave 0 creates test files with stubs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Claude Desktop sees updated tool list after watcher adds a tool | MCP-02 | Requires running Claude Desktop client | 1. Start MCP server 2. Drop .py into synthesized/ 3. Wait 5s 4. Check tool list in Claude Desktop |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
