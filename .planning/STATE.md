---
gsd_state_version: 1.0
milestone: v1.3
milestone_name: Artist Console
status: defining_requirements
stopped_at: Milestone scope confirmed
last_updated: "2026-04-22T00:00:00.000Z"
last_activity: 2026-04-22
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-22)

**Core value (v1.3):** Make forge-bridge legible to its operator — artist-first Web UI + CLI console surfacing the synthesis manifest, execution history, provenance, and live tool state, backed by a canonical MCP resource.
**Current focus:** Defining v1.3 requirements

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-04-22 — Milestone v1.3 Artist Console started

Progress: [··········] 0% (v1.3 milestone — scope confirmed, requirements + roadmap pending)

## Session Handoff — Resume Instructions

**What's committed and ready:**

- `.planning/PROJECT.md` — v1.3 "Artist Console" Current Milestone section written
- `.planning/STATE.md` — reset for new milestone
- Git: clean working tree (pre-commit)

**Still to produce this session:**

- `.planning/REQUIREMENTS.md` — scoped v1.3 requirements with REQ-IDs (categories likely: CONSOLE, MFST, API, CLI, CHAT)
- `.planning/ROADMAP.md` — phase structure starting at Phase 9
- `.planning/research/` (optional) — 4 parallel agents if research step is approved

**Next action:**

Continue the `/gsd-new-milestone` workflow — research decision → requirements → roadmap → approval.

**Key constraints for v1.3 planning:**

- Read-only UI this milestone — no admin/mutation actions, no auth
- Serving on new port inside MCP server process (NOT mounted on `:9999` Flame exec endpoint, NOT on `:9998` WS)
- JSONL is canonical data source (STORE-06); SQL read-adapter is opt-in
- One manifest, two surfaces — bridge-owned canonical synthesis manifest served via MCP resource + console read API
- Design language inherits LOGIK-PROJEKT `#242424` + `#cc9c00` amber, web-adapted; Web UI phase runs `/gsd-ui-phase` for its formal design contract
- Locked v1.1/v1.2 non-goals carry forward (no LLMRouter hot-reload, no shared-path JSONL writers)

**Open (roadmapper to decide scope):** real-time streaming (SSE/WebSocket push) vs poll-only; multi-project view.

## Performance Metrics

**Velocity (v1.0 baseline):**

- Total plans completed: 37
- v1.0 phases: 3 phases, 13 plans

**By Phase (v1.0):**

| Phase | Plans | Status |
|-------|-------|--------|
| 1. Tool Parity & LLM Router | 7 | Complete |
| 2. MCP Server Rebuild | 3 | Complete |
| 3. Learning Pipeline | 3 | Complete |

**v1.1 Phase 5 Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 05 P03 | ~15min | 2 tasks | 3 files |
| Phase 05 P04 | ~12min | 1 task  | 1 file  |
| Phase 07.1 P02 | 9min | 2 tasks | 2 files |
| Phase 07.1-startup-bridge-graceful-degradation-hotfix-deployment-uat P03 | 8min | 1 tasks | 1 files |

## Accumulated Context

### Roadmap Evolution

- Phase 07.1 inserted after Phase 7: startup_bridge graceful degradation hotfix + deployment UAT (URGENT) — Phase 7 UAT surfaced a deployment-blocking bug in forge-bridge.mcp.server.startup_bridge; exception from _client.start() escapes the try/except intended to guard wait_until_connected. Latent in v1.2.0. Fix + v1.2.1 hotfix + re-UAT via real MCP client before closing v1.2 milestone.

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
- [Phase 05]: [Plan 05-03]: Expanded Task 2 scope to cover projekt_forge/server/__init__.py as a Rule 3 blocking auto-fix -- the package __init__ re-exported 'main' from server.mcp which Task 1 explicitly removed, so without the three-file atomic commit the package becomes unimportable mid-wave. The alternative (split the __init__ fix into a separate commit) would have broken RWR-03's atomic-commit requirement.
- [Phase 05]: [Plan 05-03]: Introduced _run_mcp_only(args) helper in __main__.py instead of leaving the two 'from projekt_forge.server.mcp import main as mcp_main' callers dangling -- the helper configures the bridge via forge_bridge.bridge.configure and calls mcp.run() directly, so the canonical FastMCP lifespan owns startup_bridge/shutdown_bridge per Phase 4 API-04/API-05 and projekt-forge never duplicates the lifecycle.
- [Phase 05]: [Plan 05-03]: Swept the Wave A cosmetic leftovers in __main__.py (argparse prog label, module docstring, logger channel name) from 'forge_bridge' to 'projekt_forge' in the same atomic commit as the architectural rewire -- Plan 05-01 SUMMARY flagged these as Wave C's responsibility.
- [Phase 05]: [Plan 05-04]: D-06 editable-shadow reconciliation handled per plan STEP 4 — uninstalled the editable forge-bridge shadow (0.1.0 from /Users/cnoellert/Documents/GitHub/forge-bridge) and installed forge-bridge 1.0.1 from the git tag into site-packages before committing the fixture. The fixture's site-packages assertion is by design incompatible with the editable dev loop; if the user reinstates the editable shadow for forge-bridge development, pytest will fail with a clear remediation message. This is the guard working as intended, not a regression.
- [Phase 05]: [Plan 05-04]: Duplicate `import pytest` omitted from the appended conftest block — plan STEP 3 explicitly permits this reconciliation when pytest is already imported at file top (it is, at line 17). `pathlib` and `forge_bridge` are new and stay inline for section cohesion per the plan's guidance. This is plan-approved, not a deviation.
- [Phase 05]: [Plan 05-04]: projekt-forge pyproject.toml missing `tool.hatch.metadata.allow-direct-references = true` prevents `pip install -e /path/to/projekt-forge` from resolving the forge-bridge git-URL dep. Worked around in this plan by installing forge-bridge directly from its git tag. Adding the hatchling flag to projekt-forge's pyproject.toml is a projekt-forge packaging concern flagged as follow-up — out of scope for RWR-04.
- [Phase 06 scope]: 2026-04-18 — SQL persistence backend for ExecutionLog (EXT-03) stays deferred to v1.1.x. Phase 6 focuses on LRN-01..04 wiring only: JSONL log path injection, LLMRouter construction from forge_config.yaml, storage callback hook, pre_synthesis_hook. Rationale: (1) v1.1 milestone goal is "wire it, don't redesign it" — integration, not persistence redesign; (2) projekt-forge already has its own DB layer that can consume the storage callback directly, so SQL-in-bridge isn't blocking; (3) Phase 5 scope already stretched three days — keeping Phase 6 focused minimizes schedule risk; (4) EXT-03 gets a dedicated v1.1.x patch when a consumer actually needs it.
- [Phase 07.1]: v1.2.1 release ceremony mirrors Phase 7-04 v1.2.0 precedent (0987525); annotated tag v1.2.1 locks downstream identity for projekt-forge @ git+... re-pin
- [Phase 07.1]: Historical changelog comment in tests/test_public_api.py preserved across releases (1.0.0 → 1.0.1 → 1.1.0 → 1.2.0 → 1.2.1) — minor departure from Plan 02's strict grep-zero acceptance criterion, intentional convention-preservation
- [Phase 07.1-startup-bridge-graceful-degradation-hotfix-deployment-uat]: Approved Option A editable-shadow remediation before cross-repo pin bump: pip uninstall -y forge-bridge in forge conda env, then pip install -e .[dev,test] from projekt-forge to resolve fresh from @v1.2.1 tag. Shadow source was byte-identical to tag source (HEAD f069407 is one docs-only commit ahead of v1.2.1 at abd047c), so remediation is a clean no-behavior-change operation that restores direct_url.json identity lock.

### Pending Todos

None yet.

### Blockers/Concerns

None currently — v1.2 blockers all resolved (see archived milestones).

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| EXT | Tool provenance in MCP annotations (EXT-02) | Shipped v1.2.0 (Phase 7) | — |
| EXT | SQL persistence backend for ExecutionLog (EXT-03) | Shipped v1.3.0 (Phase 8) | — |
| EXT | Shared synthesis manifest between repos (EXT-01) | Pulled into v1.3 Artist Console (one manifest, two surfaces) | — |

## Session Continuity

Last session: 2026-04-22 — v1.3 Artist Console milestone opened
Stopped at: Milestone scope confirmed, PROJECT.md + STATE.md updated
Resume file: continue `/gsd-new-milestone` workflow (research decision → REQUIREMENTS.md → ROADMAP.md)
