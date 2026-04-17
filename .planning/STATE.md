---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: projekt-forge Integration
status: executing
stopped_at: Completed 05-02-PLAN.md (projekt-forge Wave B pip adoption + atomic RWR-02 delete landed)
last_updated: "2026-04-16T12:00:00.000Z"
last_activity: 2026-04-16 -- Phase 05 Plan 02 complete (projekt-forge Wave B, RWR-02 atomic commit 9856376, D-12 hook fix commit 4d2b579)
progress:
  total_phases: 3
  completed_phases: 1
  total_plans: 9
  completed_plans: 7
  percent: 78
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-15)

**Core value:** Make forge-bridge the single canonical pip package so projekt-forge can consume it rather than duplicate it
**Current focus:** Phase 05 — import-rewiring

## Current Position

Phase: 05 (import-rewiring) — EXECUTING
Plan: 4 of 5 (next: 05-03)
Status: Executing Phase 05
Last activity: 2026-04-16 -- Plan 05-02 complete: projekt-forge Wave B atomic RWR-02 landed as commit 9856376 (4 duplicate modules deleted, forge-bridge pip dep added, canonical imports flipped); precondition D-12 hook sys.path fix landed as commit 4d2b579; pytest tests/ green at 414 passed + 3 xfailed (baseline 421 - 7 projekt-forge-specific switch_grade tests removed per user Option 1)

Progress: [█████░░░░░] 50% (v1.1 milestone — 3 of 5 Phase 5 plans done)

## Performance Metrics

**Velocity (v1.0 baseline):**

- Total plans completed: 17
- v1.0 phases: 3 phases, 13 plans

**By Phase (v1.0):**

| Phase | Plans | Status |
|-------|-------|--------|
| 1. Tool Parity & LLM Router | 7 | Complete |
| 2. MCP Server Rebuild | 3 | Complete |
| 3. Learning Pipeline | 3 | Complete |

*v1.1 metrics will populate as plans complete*

## Accumulated Context

### Decisions

Recent decisions affecting current work:

- [v1.0 Phase 3]: Synthesized tools must use bridge.execute(), never import flame — tools run in MCP server process, not inside Flame
- [v1.0 Phase 3]: Manifest-based file validation in watcher prevents arbitrary code execution from rogue synthesized files
- [v1.1 Roadmap]: Phase ordering is strict — Phase 5 cannot start until Phase 4 is complete; Phase 6 cannot start until both are done
- [Plan 05-00]: Four projekt-forge fixes ported upstream (query_lineage/query_shot_deps/media_scan builders, entity_list narrowing, ref_msg_id correlation fallback, timeline T0 gap-fill) — released as forge-bridge v1.0.1 so projekt-forge can delete local duplicates in Wave B
- [Plan 05-00]: `project_name` kwarg on AsyncClient.__init__ stays in projekt-forge fork (NOT upstreamed) — forge-specific multi-project routing, per RESEARCH §D-09b
- [Plan 05-01]: Single atomic commit over rename-aware 1597-line diff chosen over the 2-commit split heuristic — the work is mechanical/programmatic and reviewers benefit more from `git diff --find-renames` on the combined rewrite than from an artificial rename-first/sed-second separation
- [Plan 05-01]: sed rewrite scope expanded beyond plan's `from forge_bridge\.` pattern to cover (1) bare `from forge_bridge import bridge` imports in projekt_forge/tools/, (2) quoted string-literal `unittest.mock.patch("forge_bridge...")` targets across 9 test files, (3) `import forge_bridge.X as Y` statements, and (4) filesystem-path string literals in 2 static-analysis tests — all variants of the same local-package-reference rewrite the plan intended
- [Plan 05-01]: Cosmetic `forge_bridge` mentions (log channel name, FastMCP display name, argparse prog, usage-text `python -m forge_bridge`) intentionally left for Wave C's server/mcp.py + __main__.py rewrite — no runtime/test impact in Wave A
- [Plan 05-02]: D-09b resolved to branch-b (preserve local clients) — projekt-forge's db_server relies on extended HELLO project_name for per-project DB routing; swapping to canonical pip AsyncClient would silently break DB routing. All 3 client files retained: client/__init__.py, client/async_client.py, client/sync_client.py.
- [Plan 05-02]: Two-commit execution instead of single — a precondition fix(hooks) commit (4d2b579) for the sys.path.insert→append collision at 17 sites, then the atomic refactor(projekt_forge) RWR-02 commit (9856376). The plan wrote "single atomic commit" but the hook issue was discovered during Wave B execution and its fix is mechanically separate from RWR-02 (pip-dep + deletes + import flips remain atomic in commit 9856376).
- [Plan 05-02]: tests/test_switch_grade_mcp.py pared from 22 to 15 tests per user-approved Option 1 — deleted 7 projekt-forge-specific tests asserting on fork-only SwitchGradeInput fields (alternative_path/alternative_start_frame/alternative_duration/entity_id), server-side openclip writer (_write_openclip_server_side / forge_openclip_writer / _switch.clip naming), and UUID path construction. Rewrote 4 tests to use pip's media_path field. Coverage of pip surface maintained and expanded.
- [Plan 05-02]: D-12 discovered during execution — Flame hook scripts' sys.path.insert(0, scripts_dir) shadows pip forge_bridge/ because scripts dir contains sibling forge_bridge.py hook module. Resolution: insert→append at 17 sites; 05-04's autouse conftest fixture is the long-term guard.
- [Plan 05-02]: Pytest invocation standardized to `pytest tests/` (explicit path) — default `pytest` collection in projekt-forge pollutes from flame_hooks/forge_tools/forge_bridge/scripts/forge_llm_test.py (matches *_test.py AND sys.exit(1) on Ollama offline). Pre-existing issue noted in SUMMARY but not fixed in 05-02.

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 4]: mcp/server.py lifespan refactor — promoting _startup/_shutdown to public requires confirming forge-bridge's own test suite does not depend on the private names before Phase 4 planning
- ~~[Phase 5]: Import blast radius in projekt-forge not yet measured~~ — RESOLVED: 179 `from forge_bridge.*` imports + 8 bare-module + 30+ patch-target variants all measured and rewritten in Plan 05-01
- [Phase 6]: DB persistence scope in v1.1 not decided — is SQL backend for ExecutionLog in v1.1 or deferred to v1.1.x? Needs explicit decision before Phase 6 planning

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| EXT | Shared synthesis manifest between repos (EXT-01) | Future requirement | v1.1 definition |
| EXT | Tool provenance in MCP annotations (EXT-02) | Future requirement | v1.1 definition |
| EXT | SQL persistence backend for ExecutionLog (EXT-03) | Future requirement | v1.1 definition |

## Session Continuity

Last session: 2026-04-16T12:00:00.000Z
Stopped at: Completed 05-02-PLAN.md — projekt-forge Wave B atomic RWR-02 landed (commits 4d2b579 hook fix + 9856376 RWR-02 in projekt-forge); pytest tests/ green at 414 passed + 3 xfailed
Resume file: .planning/phases/05-import-rewiring/05-03-PLAN.md
