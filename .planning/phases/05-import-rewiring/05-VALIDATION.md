---
phase: 5
slug: import-rewiring
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-16
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Phase 5 implementation commits land in the **projekt-forge** repo; validation therefore runs projekt-forge's test suite with the new pip-installed `forge_bridge`.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (projekt-forge) |
| **Config file** | `/Users/cnoellert/Documents/GitHub/projekt-forge/pyproject.toml` (pytest config) + `/Users/cnoellert/Documents/GitHub/projekt-forge/tests/conftest.py` |
| **Quick run command** | `cd /Users/cnoellert/Documents/GitHub/projekt-forge && pytest tests/ -x --timeout=30` |
| **Full suite command** | `cd /Users/cnoellert/Documents/GitHub/projekt-forge && pytest` |
| **Estimated runtime** | ~30–90 seconds (existing suite) |

---

## Sampling Rate

- **After every task commit:** Run quick command above (fails fast on first broken test)
- **After every plan wave:** Run full suite — each wave (A/B/C/D) must be green before starting the next
- **Before `/gsd-verify-work`:** Full suite green + RWR-04 conftest assertion green
- **Max feedback latency:** ~90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 5-00-01 | 00 | 0 | RWR-01 (prereq) | — | forge-bridge v1.0.1 tagged after patches | cmd | `git -C /Users/cnoellert/Documents/GitHub/forge-bridge tag --list 'v1.0.*'` emits `v1.0.1` | ✅ (this repo) | ⬜ pending |
| 5-01-01 | 01 | A | RWR-01 | — | projekt-forge renames to `projekt_forge/` | cmd | `test -d /Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge && ! test -d /Users/cnoellert/Documents/GitHub/projekt-forge/forge_bridge` | ⬜ W0 (projekt-forge) | ⬜ pending |
| 5-01-02 | 01 | A | RWR-01 | — | all internal imports rewritten | cmd | `grep -r "from forge_bridge" /Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/ /Users/cnoellert/Documents/GitHub/projekt-forge/tests/ \| wc -l` emits `0` (canonical imports come back in Wave B from pip) | ⬜ W0 | ⬜ pending |
| 5-01-03 | 01 | A | RWR-01 | — | pyproject.toml reflects rename | cmd | `grep -c '"projekt_forge"' /Users/cnoellert/Documents/GitHub/projekt-forge/pyproject.toml` ≥ 1; `grep -c '"forge_bridge"' pyproject.toml` = 0 | ⬜ W0 | ⬜ pending |
| 5-01-04 | 01 | A | RWR-01 | — | full test suite green post-rename | unit | `cd /Users/cnoellert/Documents/GitHub/projekt-forge && pytest` exits 0 | ✅ | ⬜ pending |
| 5-02-01 | 02 | B | RWR-01, RWR-02 | — | pip dep added | cmd | `grep 'forge-bridge @ git+' /Users/cnoellert/Documents/GitHub/projekt-forge/pyproject.toml` matches `@v1.0.1` | ⬜ W0 | ⬜ pending |
| 5-02-02 | 02 | B | RWR-02 | — | duplicates deleted | cmd | `! test -f /Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/bridge.py` AND `! test -f /Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/tools/publish.py` AND `! test -f /Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/tools/switch_grade.py` (etc. per research D-08 list) | ⬜ W0 | ⬜ pending |
| 5-02-03 | 02 | B | RWR-02 | — | canonical imports restored via pip | cmd | `grep -r "from forge_bridge import\|from forge_bridge\." /Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/ \| wc -l` ≥ 1 | ⬜ W0 | ⬜ pending |
| 5-02-04 | 02 | B | RWR-02 | — | suite green post-delete | unit | `cd /Users/cnoellert/Documents/GitHub/projekt-forge && pytest` exits 0 | ✅ | ⬜ pending |
| 5-03-01 | 03 | C | RWR-03 | — | `server/mcp.py` collapses to `get_mcp()` + `register_tools()` | cmd | `grep -c 'mcp.tool(' /Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/server/mcp.py` = 0; `grep -c 'register_tools(' .../server/mcp.py` ≥ 1 | ⬜ W0 | ⬜ pending |
| 5-03-02 | 03 | C | RWR-03, API-04, API-05 | — | `__main__.py` uses `startup_bridge` / `shutdown_bridge` | cmd | `grep -E 'startup_bridge\|shutdown_bridge' /Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/__main__.py` emits ≥1 match; `grep -E '_startup\\(\|_shutdown\\(' __main__.py` emits 0 | ⬜ W0 | ⬜ pending |
| 5-03-03 | 03 | C | RWR-03 | — | MCP server starts; tools visible under `forge_` prefix | integration | `python -m projekt_forge --help` exits 0 OR a pytest MCP smoke test confirms `forge_trace_lineage` in tool list | ⬜ W0 | ⬜ pending |
| 5-04-01 | 04 | D | RWR-04 | — | conftest site-packages assertion present + passing | unit | `pytest /Users/cnoellert/Documents/GitHub/projekt-forge/tests/conftest.py::test_forge_bridge_resolves_to_site_packages` exits 0 | ⬜ W0 | ⬜ pending |
| 5-04-02 | 04 | D | RWR-04 | — | defensive check: no top-level `forge_bridge/` directory at repo root | cmd | `! test -d /Users/cnoellert/Documents/GitHub/projekt-forge/forge_bridge` | ⬜ W0 | ⬜ pending |
| 5-04-03 | 04 | D | RWR-04 | — | full suite green (phase-wide gate) | unit | `cd /Users/cnoellert/Documents/GitHub/projekt-forge && pytest` exits 0 | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] **forge-bridge v1.0.1 patch release** — land `query_lineage` / `query_shot_deps` builders in `forge_bridge/server/protocol.py`, `entity_list` narrowing kwargs, and `ref_msg_id` correlation fix in `async_client.py`. Tag `v1.0.1` and push. **This is Wave 0 / Plan 00 and blocks every other wave.**
- [ ] **pytest fixture for MCP smoke check** (optional, if not already present in projekt-forge) — covers 5-03-03.
- [ ] **conftest assertion file** (`projekt-forge/tests/conftest.py`) — lands in Wave D; verifies forge_bridge resolves to site-packages.

*No new test framework install required — pytest is already configured in projekt-forge.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| MCP client connects and sees `forge_*` tools end-to-end | RWR-03 | Requires a live MCP client (Claude Desktop or similar); not a pytest target | Start projekt-forge via `python -m projekt_forge`, connect Claude Desktop, confirm `forge_trace_lineage` / `forge_publish_pipeline` / `forge_media_scan` / `forge_seed_catalog` are listed and callable |
| Flame hook (`flame_hooks/forge_tools/`) subprocess continues to import `forge_bridge` successfully | (Claude's Discretion, CONTEXT.md) | Requires running Flame (non-CI environment) | Trigger a publish inside Flame; observe the conda subprocess log for successful `from forge_bridge.client.sync_client import SyncClient` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (v1.0.1 patch; conftest file)
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
