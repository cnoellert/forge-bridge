---
gsd_state_version: 1.0
milestone: v1.3
milestone_name: Artist Console
status: executing
stopped_at: Phase 10 context gathered
last_updated: "2026-04-23T01:46:12.559Z"
last_activity: 2026-04-23
progress:
  total_phases: 4
  completed_phases: 1
  total_plans: 3
  completed_plans: 3
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-22)

**Core value (v1.3):** Make forge-bridge legible to its operator — artist-first Web UI + CLI console surfacing the synthesis manifest, execution history, provenance, and live tool state, backed by a canonical MCP resource.
**Current focus:** Phase 09 — read-api-foundation

## Current Position

Phase: 10
Plan: Not started
Status: Executing Phase 09
Last activity: 2026-04-23

Progress: [··········] 0% (v1.3 milestone — 4 phases, 0 complete)

## Session Handoff — Resume Instructions

**What's committed and ready:**

- `.planning/PROJECT.md` — v1.3 "Artist Console" milestone scope
- `.planning/REQUIREMENTS.md` — 37 requirements across 8 categories (API, TOOLS, EXECS, MFST, HEALTH, CONSOLE, CLI, CHAT)
- `.planning/ROADMAP.md` — Phases 9-12 defined with success criteria
- `.planning/STATE.md` — this file, reset for Phase 9
- `.planning/research/SUMMARY.md` — HIGH confidence research across stack, features, architecture, pitfalls

**Next action:**

Run `/gsd-plan-phase 9` to begin Phase 9: Read API Foundation.

**Phase 10 planning note:** Before `/gsd-plan-phase 10`, run `/gsd-ui-phase` to produce `UI-SPEC.md`. The Web UI phase plan must reference that spec.

**Phase 12 velocity gate:** Explicitly decide whether to include or defer Phase 12 (LLM Chat) to v1.4 before Phase 11 closes. Do not defer silently.

**Key constraints for v1.3 implementation:**

- Uvicorn task pattern is locked — console runs as a separate uvicorn asyncio task inside `_lifespan` on `:9996`; NOT via `FastMCP.custom_route` (only works in `--http` mode, breaks stdio)
- ConsoleReadAPI is the sole read path for all surfaces — Web UI, CLI, MCP resources, and chat all call it; no per-surface JSONL parsers
- ManifestService singleton injected into watcher (write path) and console router (read path) — watcher is sole writer, console API reads via `snapshot()`
- Instance-identity gate (API-04): `_lifespan` owns the canonical ExecutionLog and ManifestService; no duplicate instances anywhere in the process
- MFST-02 and MFST-03 ship in the SAME plan (MCP resource + tool fallback shim together — P-03 prevention for Cursor/Gemini CLI)
- Only new pip dep: `jinja2>=3.1`; all other deps (Starlette, uvicorn, Typer, Rich, httpx) already ship transitively via `mcp[cli]`
- CLI commands must be sync functions calling sync `httpx.get()` — Typer 0.24.1 silently drops `async def` (verified via live test)
- Every UI-touching phase (10, 12) includes mandatory non-developer dogfood UAT: artist identifies three most recently synthesized tools within 30 seconds

## Performance Metrics

**Velocity (v1.0 baseline):**

- Total plans completed: 40
- v1.0 phases: 3 phases, 13 plans
- v1.2 phases: 3 phases (7, 07.1, 8), 12 plans, 17 tasks

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
- v1.3 roadmap written 2026-04-22: 4 phases (9-12), 37 requirements across 8 categories. Phase 12 (LLM Chat) explicitly velocity-gated — may defer to v1.4 if Phases 9-11 run long.

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
- [v1.3 Roadmap, 2026-04-22]: Console serves on a separate uvicorn task on `:9996` inside `_lifespan` — NOT via FastMCP.custom_route (only works in `--http` mode; stdio is the locked default and custom_route would break Claude Desktop/Claude Code configurations).
- [v1.3 Roadmap, 2026-04-22]: MFST-02 and MFST-03 (MCP resource + tool fallback shim) ship in the same Phase 9 plan — P-03 prevention; Cursor and Gemini CLI do not support resources and the shim costs one function.
- [v1.3 Roadmap, 2026-04-22]: Phase 12 (LLM Chat) is velocity-gated — explicitly deferrable to v1.4 if Phases 9-11 run long; must be an explicit scope decision before Phase 11 closes, not a silent drop.

### Pending Todos

None.

### Blockers/Concerns

None — v1.3 roadmap defined; ready to begin Phase 9.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| EXT | Tool provenance in MCP annotations (EXT-02) | Shipped v1.2.0 (Phase 7) | — |
| EXT | SQL persistence backend for ExecutionLog (EXT-03) | Shipped v1.3.0 (Phase 8) | — |
| EXT | Shared synthesis manifest between repos (EXT-01) | Pulled into v1.3 Artist Console (MFST-06) | — |
| v1.4 | SSE/WebSocket streaming push | Deferred — poll-first for v1.3 | v1.3 roadmap |
| v1.4 | Multi-project console view | Deferred — single-bridge/single-project in v1.3 | v1.3 roadmap |
| v1.4 | Promotion sparklines / rich historical charts | Deferred | v1.3 roadmap |
| v1.4 | Admin/mutation actions (quarantine, promote, kill) | Deferred — paired with auth milestone | v1.3 roadmap |
| v1.4 | Maya/editorial manifest producers | Deferred — Flame only in v1.3 | v1.3 roadmap |
| v1.4 (maybe) | LLM Chat (Phase 12) | Velocity-gated — explicit decision required before Phase 11 closes | v1.3 roadmap |

## Session Continuity

Last session: 2026-04-23T01:46:12.556Z
Stopped at: Phase 10 context gathered
Resume file: .planning/phases/10-web-ui/10-CONTEXT.md
