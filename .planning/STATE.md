---
gsd_state_version: 1.0
milestone: v1.5
milestone_name: Legibility
status: planning
stopped_at: Phase 20 context gathered
last_updated: "2026-04-30T23:45:21.095Z"
last_activity: 2026-04-30 — Roadmap created (Phases 20–23)
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-30 at v1.5 milestone open)

**Project core value:** forge-bridge is the single canonical pip-installable middleware (`pip install forge-bridge`) — protocol-agnostic communication bus with a canonical vocabulary that any endpoint (Flame, Maya, editorial, LLM agents) connects to.
**Current focus:** v1.5 Legibility — Phase 20: Reality Audit + Canonical Install

## Current Position

Phase: 20 (next to execute)
Plan: —
Status: Roadmap approved — ready to plan Phase 20
Milestone: v1.5 Legibility (opened 2026-04-30)
Last activity: 2026-04-30 — Roadmap created (Phases 20–23)

**v1.4.x closed 2026-04-30** — patch milestone shipped at tag `v1.4.1`. 9/9 requirements (MODEL-01..02, HARNESS-01..03, POLISH-01..04) closed across 3 phases (17, 18, 19); audit `passed`; 7/7 cross-phase integration wires verified; public `__all__` byte-identical to v1.4 close (19 symbols).

**v1.5 scope** — Legibility milestone, no LOC target, no API surface change expected:

- **Phase 20** (next) — Reality audit + canonical install. Walk a fresh install end-to-end on a clean machine; fix gaps as they surface. Output: `docs/INSTALL.md`, refreshed `README.md` install section, refreshed `CLAUDE.md` ground-truth section, `install-flame-hook.sh` default pinned to `v1.4.1`. Maps: INSTALL-01..04 + DOCS-02.
- **Phase 21** (pending) — Surface map + concept docs. Document the five user-facing surfaces (Web UI on `:9996/ui/`, CLI `forge-bridge`, `/api/v1/chat` HTTP, MCP server `python -m forge_bridge`, Flame hook on `:9999`) plus projekt-forge relationship. Output: `docs/GETTING-STARTED.md` + rewritten README "What This Is" section. Maps: DOCS-01, DOCS-03, DOCS-04.
- **Phase 22** (pending) — Daily workflow recipes. Step-by-step recipes for ~6 daily tasks (first-time setup, Claude Desktop wiring, watching tool synthesis, chat-driven Flame automation, staged-ops approval, manifest inspection). Output: `docs/RECIPES.md` (or directory). Maps: RECIPES-01..06.
- **Phase 23** (pending) — Diagnostics + recovery. Document common failure modes (Flame crash, Postgres restart, Ollama hang, qwen3 cold-start `LLMLoopBudgetExceeded`) and recovery paths; polish `forge doctor` if it surfaces gaps during recipe writing. Output: `docs/TROUBLESHOOTING.md`. Maps: DIAG-01..05.

**Next action:** Run `/gsd-plan-phase 20` to generate the execution plan for Phase 20.

**Key constraints (binding for v1.5):**

- Legibility, not features. No new external libraries. Public `forge_bridge.__all__` stays at 19 unless something genuinely shifts during install audit.
- Forcing function: if `docs/INSTALL.md` doesn't work end-to-end on a clean machine, we don't ship it. Phase 20 will likely surface deployment gaps that get fixed in-flight (and may add code-fix plans alongside doc plans).
- Internal codebase audit + workflow articulation — no external research phase.
- RECIPES-04 (multi-step Flame chat) and RECIPES-05 (staged-ops approval) require a working Flame setup — assume assist-01 or equivalent operator workstation.
- Phase 23 DIAG-05 (`forge doctor` parity) may require in-flight polish — "polish forge doctor if gaps surface" is in Phase 23 scope, not a separate phase.
- All 16 planted seeds in `.planning/seeds/SEED-*.md` are out of v1.5 scope (feature work for v1.6+: auth, chat enhancements, model bumps, tool-call optimizations, staged-ops follow-on, CMA memory).
- Done state: user can sit down, follow the docs, and use forge-bridge in daily VFX workflow without re-deriving the deployment topology each time.

## Performance Metrics

**Velocity (v1.0–v1.3 baseline):**

- Total plans completed: 86 (across milestones v1.0–v1.3)
- v1.0 phases: 3 phases, 13 plans
- v1.1 phases: 3 phases, 13 plans
- v1.2 phases: 3 phases (7, 07.1, 8), 12 plans, 17 tasks
- v1.3 phases: 4 phases (9, 10, 10.1, 11), 20 plans

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
| Phase 16.2 P01 | 3min | 2 tasks | 4 files |
| Phase 16.2 P02 | 2min | 1 tasks | 1 files |
| Phase 16.2 P03 | 1min | 1 tasks | 1 files |

## Accumulated Context

### Roadmap Evolution

- Phase 07.1 inserted after Phase 7: startup_bridge graceful degradation hotfix + deployment UAT (URGENT) — Phase 7 UAT surfaced a deployment-blocking bug in forge-bridge.mcp.server.startup_bridge; exception from _client.start() escapes the try/except intended to guard wait_until_connected. Latent in v1.2.0. Fix + v1.2.1 hotfix + re-UAT via real MCP client before closing v1.2 milestone.
- v1.3 roadmap written 2026-04-22: 4 phases (9-12), 37 requirements across 8 categories. Phase 12 (LLM Chat) explicitly velocity-gated — may defer to v1.4 if Phases 9-11 run long.
- v1.4 pre-design dated 2026-04-23 in ROADMAP.md alongside v1.3 close — FB-A..FB-D scoped against projekt-forge v1.5 declared deps (consumer-driven naming). Phase 12 superseded by FB-D in same audit.
- v1.4 roadmap formalized 2026-04-25 by gsd-roadmapper: FB-C success criteria grew from 4→7 (absorbed LLMTOOL-04 repeat-call detection, LLMTOOL-05 8KB result truncation, LLMTOOL-06 sanitization boundary, LLMTOOL-07 recursive-synthesis guard — all surfaced by targeted FB-C research). FB-D success criteria grew from 4→5 (absorbed CHAT-05 external-consumer parity with projekt-forge Flame hooks). Total v1.4 requirements: 19 (STAGED 7 + LLMTOOL 7 + CHAT 5).
- Phase 16.2 inserted after Phase 16.1: Bug D — chat tool-call loop renders raw JSON instead of executing tools and synthesizing answer (URGENT) — surfaced in Phase 16.1 fresh-operator UAT on assist-01 2026-04-28; v1.4 milestone close blocked until Bug D fixed and CHAT-04 fresh-operator UAT records PASS. Investigation scope: LLMRouter agentic loop, chat handler tool dispatch, UI rendering, plus strengthen Strategy B chat E2E assertion to reject tool-call-only responses.
- v1.5 roadmap formalized 2026-04-30 by gsd-roadmapper: 4 phases (20-23), 19 requirements across 4 categories (DOCS/INSTALL/RECIPES/DIAG). Phase numbering continues from v1.4.x (last shipped phase 19). Phase 20 is a forcing function — INSTALL.md must pass fresh-machine UAT before the milestone ships. DOCS-02 assigned to Phase 20 (not Phase 21) because the install audit walk-through discovers the CLAUDE.md ground-truth gaps.

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
- [Phase 11, 2026-04-24]: Phase 12 velocity gate decision honored — Phase 12 superseded by FB-D in ROADMAP. v1.3 closes with Phases 9, 10, 10.1, 11 (LLM Chat work moves to v1.4 FB-D).
- [Phase 11, 2026-04-24]: D-04 W-01 stays open — `execs --tool` runs client-side with locked stderr note. Server-side `/api/v1/execs?tool=...` is a v1.4 API extension; Phase 11 deliberately consumed Phase 9/10 API as-is and added zero server endpoints.
- [Phase 11, 2026-04-24]: Soft UAT gate (D-08) is the right tool for technical CLI surfaces — developer-as-operator with the "can I decipher" criterion produced a useful PASS plus one v1.4-deferred UX note (manifest/tools render visually indistinguishable). Bundle the manifest caption + cross-link fix with Phase 10.1 humanized-timestamps follow-up in a v1.4 polish pass.
- [v1.4 Roadmap, 2026-04-25]: Phase letter scheme `FB-A..FB-D` is LOCKED — consumer-driven by projekt-forge v1.5 declared deps. NOT renumbered to phases 12..15. Pre-discussed at v1.4 open and re-confirmed at roadmap formalization.
- [v1.4 Roadmap, 2026-04-25]: FB-C success criteria expanded from pre-design's 4 to 7 to absorb LLMTOOL-04 (repeat-call detection), LLMTOOL-05 (8 KB result truncation), LLMTOOL-06 (sanitization boundary), LLMTOOL-07 (recursive-synthesis guard) — all surfaced by targeted FB-C research. FB-C is the largest phase by criterion count.
- [v1.4 Roadmap, 2026-04-25]: FB-D success criteria expanded from pre-design's 4 to 5 to add CHAT-05 (external-consumer parity with projekt-forge Flame hooks). FB-D is the v1.5 cross-consumer integration point, not just the Web UI chat panel.
- [v1.4 Roadmap, 2026-04-25]: FB-A and FB-C are parallelizable — no shared dependency. FB-B → FB-A (entity before its surface). FB-D → FB-C (loop before chat endpoint). Sequencing FB-A and FB-C concurrently is a legitimate execution-order option.
- [v1.4 Roadmap, 2026-04-25]: Sanitization patterns consolidate into a single source of truth in FB-C — Phase 7's `_sanitize_tag()` and FB-C's `_sanitize_tool_result()` share `forge_bridge/_sanitize_patterns.py` (or equivalent). This is a FB-C scope item, not a new phase.
- [v1.4 Roadmap, 2026-04-25]: `LLMLoopBudgetExceeded` exported from `forge_bridge.__all__`. Barrel grows 16→17. Required so callers (FB-D chat endpoint) can catch it and translate to HTTP 504/408.
- [v1.4 Roadmap amendment, 2026-04-25]: Dual-naming applied — `Phase 13..16` numeric IDs added alongside preserved `FB-A..FB-D` aliases. Forced by `gsd-tools` impedance: `normalizePhaseName()` only strips letter prefixes when followed by a digit, so `FB-A` cannot resolve via `find-phase` and the discuss/plan/execute pipeline silently fails. Numeric mapping skips 12 (taken by superseded "LLM Chat" — 12 still exists in v1.3 history as superseded). The original locked decision (no renumber) was about preserving the cross-repo contract with projekt-forge v1.5; the amendment satisfies that intent (alias preserved everywhere) while adding the numeric plumbing tooling needs.
- [Phase 16.2]: [Phase 16.2-01]: Bug D D-03 hypothesis CONFIRMED with reproduce-from-disk evidence — captured Ollama response from assist-01 shows tool_calls=null and content='{"name": "forge_tools_read", "arguments": {"name": "synthesis-tools"}}'. RED adapter test landed at tests/llm/test_ollama_adapter.py::TestOllamaToolAdapterBugDFallback::test_text_content_tool_call_salvaged with explicit Bug D regression message. Plan 02 GREEN fix unblocked.
- [Phase 16.2]: [Phase 16.2-01]: Captured fixture lives in BOTH operator-readable JSON in planning tree AND verbatim Python constant in test file; equality asserted at verify time per threat T-16.2.01-01 to prevent drift. Pattern reusable for future captured-fixture testing.
- [Phase 16.2]: [Phase 16.2-02]: Bug D GREEN fix landed in OllamaToolAdapter. _try_parse_text_tool_call helper at module scope salvages a _ToolCall from message.content when message.tool_calls is empty AND content matches the canonical {name, arguments} JSON shape. Helper never raises (returns None on parse failure). Salvage hook in send_turn resets text="" on success to prevent double-emit. Plan 01's RED test flipped to PASSED; full tests/llm/ suite 91/91 green; router.py + handlers.py byte-identical to main.
- [Phase 16.2]: [Phase 16.2-02]: Helper placement decision — _try_parse_text_tool_call lives at module scope between _TurnResponse (line 114) and _ToolAdapter Protocol (line 195) because it constructs _ToolCall (line 86). Plan-compliant; the plan's 'after _OLLAMA_KEEP_ALIVE' hint was a module-level placement directive, not a strict line constraint. Reusable pattern for future adapter-layer salvage helpers.
- [Phase 16.2-03]: Strategy B chat E2E (test_chat_canonical_uat_prompt_under_60s) strengthened with two additive D-06 assertions: regex-reject raw tool-call JSON (^\s*\{\s*"name"\s*:) as terminal content, AND assert agentic loop iterated (>=1 role=tool turn AND >=2 role=assistant turns). Module-top compiled regex _BUG_D_TERMINAL_JSON_RE; module-top import re. Fixture body byte-identical; no router/adapter mocks introduced. CONTEXT D-07 'natural prose detection' heuristic explicitly rejected — too brittle, false-positives on legitimate one-word answers. Default pytest skips cleanly (1 skipped, 0 failed).
- [v1.5 Roadmap, 2026-04-30]: DOCS-02 (CLAUDE.md ground-truth refresh) assigned to Phase 20, not Phase 21. Rationale: the install audit walk-through is what surfaces the CLAUDE.md divergence from reality — the discovery and fix are co-located in the same phase. Phase 21 (surface map) can then rely on already-accurate ground truth.
- [v1.5 Roadmap, 2026-04-30]: Phase 20 is the milestone forcing function. INSTALL.md must pass a fresh-machine non-author UAT walk-through before the phase closes. Deployment gaps found during authoring are fixed in-flight as Phase 20 plans — not deferred.
- [v1.5 Roadmap, 2026-04-30]: RECIPES-04 and RECIPES-05 carry a prerequisite assumption: assist-01 or equivalent operator workstation with Flame running. This is documented in Phase 22 success criteria and must be stated explicitly in the recipe text.
- [v1.5 Roadmap, 2026-04-30]: Phase 23 DIAG-05 scope includes in-flight `forge doctor` polish — gaps surfaced during recipe or troubleshooting authoring are closed in Phase 23, not as a separate decimal phase.

### Pending Todos

None. Roadmap formalized; ready to plan Phase 20.

### Blockers/Concerns

- **None.** All 19 v1.5 requirements mapped (INSTALL-01..04 + DOCS-02 → Phase 20; DOCS-01,03,04 → Phase 21; RECIPES-01..06 → Phase 22; DIAG-01..05 → Phase 23). Coverage 19/19.

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
| v1.4 | LLM Chat (Phase 12) | Superseded by FB-D — velocity gate decided 2026-04-23, confirmed at Phase 11 close 2026-04-24, formalized in FB-D 2026-04-25 | v1.3 roadmap |
| v1.4 | CLI manifest/tools differentiation | Deferred — Phase 11 D-08 UAT noted manifest + tools render visually indistinguishable; bundle with Phase 10.1 humanized-timestamps follow-up | Phase 11 UAT 2026-04-24 |
| v1.4.x | Manifest/tools CLI visual differentiation, 10.1-HUMAN-UAT items, W-01 server-side filter, real-time streaming push, multi-project view | Pre-discussed at v1.4 open — patch milestone after core v1.4 ships | v1.4 open 2026-04-25 |
| v1.5 | Auth (caller-identity rate limiting, multi-user) | SEED-AUTH-V1.5 planted at v1.4 open | v1.4 open 2026-04-25 |
| v1.5 | Parallel tool execution within single LLM turn | FB-C ships `parallel: bool = False` advertising the v1.5 path; passing True raises NotImplementedError | v1.4 FB-C scope |
| v1.5 | Cross-provider sensitive fallback | Loop state is provider-specific; mid-loop fallback would require state reconstruction | FB-C research §5.4 |
| v1.5 | Message-history pruning (summarize old turns, drop early tool results) | SEED-MESSAGE-PRUNING-V1.5 — for v1.4, ingest-time truncation at 8KB per result is sufficient | FB-C research §6.2 |
| v1.5 | Tool examples (Anthropic `input_examples` field) | SEED-TOOL-EXAMPLES-V1.5 | FB-C research §2.1 |

## Session Continuity

Last session: 2026-04-30T23:45:21.093Z
Stopped at: Phase 20 context gathered
Resume file: .planning/phases/20-reality-audit-canonical-install/20-CONTEXT.md
