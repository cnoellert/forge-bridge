# Roadmap: forge-bridge

## Milestones

- ✅ **v1.0 Canonical Package & Learning Pipeline** — Phases 1-3 (shipped 2026-04-15)
- 🚧 **v1.1 projekt-forge Integration** — Phases 4-6 (in progress)

## Phases

<details>
<summary>✅ v1.0 Canonical Package & Learning Pipeline (Phases 1-3) — SHIPPED 2026-04-15</summary>

- [x] **Phase 1: Tool Parity & LLM Router** (7/7 plans) — completed 2026-04-15
- [x] **Phase 2: MCP Server Rebuild** (3/3 plans) — completed 2026-04-15
- [x] **Phase 3: Learning Pipeline** (3/3 plans) — completed 2026-04-15

Full details: `.planning/milestones/v1.0-ROADMAP.md`

</details>

### 🚧 v1.1 projekt-forge Integration (In Progress)

**Milestone Goal:** Make projekt-forge consume forge-bridge as a pip dependency — replacing duplicated code with imports and wiring the learning pipeline into forge's infrastructure — without breaking either system's existing functionality.

- [x] **Phase 4: API Surface Hardening** (4/4 plans) — completed 2026-04-15
- [x] **Phase 5: Import Rewiring** (5/5 plans) — completed 2026-04-18
- [ ] **Phase 6: Learning Pipeline Integration** — Wire forge-bridge's learning pipeline into projekt-forge's LLM, config, and storage infrastructure

## Phase Details

### Phase 4: API Surface Hardening
**Goal**: forge-bridge is a well-defined, externally consumable pip package with a declared public surface, injectable LLM configuration, and no forge-specific content baked in
**Depends on**: Phase 3 (v1.0 complete)
**Requirements**: API-01, API-02, API-03, API-04, API-05, PKG-01, PKG-02, PKG-03
**Success Criteria** (what must be TRUE):
  1. `from forge_bridge import LLMRouter, ExecutionLog, register_tools, get_mcp` succeeds in a clean virtualenv with only forge-bridge installed
  2. `LLMRouter(local_url="http://custom:11434", local_model="llama3", system_prompt="...")` constructs without reading env vars
  3. `register_tools(source="builtin")` accepts the call without raising; downstream consumers can register tools with the builtin source tag
  4. Calling `register_tools()` after `mcp.run()` raises `RuntimeError` with a clear message
  5. `grep -r "portofino\|assist-01\|ACM_" forge_bridge/` returns no matches
**Plans**: 4 plans
  - [x] 04-01-PLAN.md — LLMRouter injection + publish.py scrub (API-02, PKG-03)
  - [x] 04-02-PLAN.md — MCP lifecycle rename + post-run guard (API-04, API-05, PKG-01)
  - [x] 04-03-PLAN.md — SkillSynthesizer class + test migration (API-03)
  - [x] 04-04-PLAN.md — Public API surface + version bump + cross-cutting tests (API-01, API-04, API-05, PKG-02, PKG-03)

### Phase 5: Import Rewiring
**Goal**: projekt-forge contains no duplicated forge-bridge code and imports all bridge functionality from the pip package
**Depends on**: Phase 4
**Requirements**: RWR-01, RWR-02, RWR-03, RWR-04
**Success Criteria** (what must be TRUE):
  1. `pip show forge-bridge` inside projekt-forge's virtualenv shows the installed package (not a local directory)
  2. `python -c "import forge_bridge; print(forge_bridge.__file__)"` resolves to a site-packages path, not the projekt-forge source tree
  3. projekt-forge's forge-specific tools (catalog, orchestrate, scan, seed) are registered and visible to MCP clients via `register_tools()`
  4. All existing projekt-forge tests pass after the rewire with no changes to test logic
**Plans**: 5 plans (strictly sequential waves 0→1→2→3→4; Wave 0 lands in forge-bridge repo, Waves 1-4 land in projekt-forge repo)
  - [x] 05-00-PLAN.md — Wave 0 (forge-bridge repo): v1.0.1 patch release (protocol builders, ref_msg_id fix, timeline gap-fill, tag+push) (RWR-01 prereq)
  - [x] 05-01-PLAN.md — Wave A (projekt-forge repo): rename forge_bridge/→projekt_forge/ + internal import sweep + pyproject.toml + dev-loop doc (RWR-01)
  - [x] 05-02-PLAN.md — Wave B (projekt-forge repo): add pip dep; delete D-08 duplicates; flip canonical imports; atomic RWR-02 commit (RWR-01, RWR-02)
  - [x] 05-03-PLAN.md — Wave C (projekt-forge repo): rebuild server/mcp.py around get_mcp()+register_tools; wire __main__.py to canonical lifespan (RWR-03)
  - [x] 05-04-PLAN.md — Wave D (projekt-forge repo): conftest autouse guard asserting forge_bridge resolves to site-packages (RWR-04)

### Phase 6: Learning Pipeline Integration
**Goal**: projekt-forge's startup wires forge-bridge's learning pipeline with forge's own LLM config, log path, and storage callback — so synthesis uses forge's Ollama instance and logs persist separately from the standalone bridge process
**Depends on**: Phase 4, Phase 5
**Requirements**: LRN-01, LRN-02, LRN-03, LRN-04
**Success Criteria** (what must be TRUE):
  1. Two forge-bridge processes running simultaneously write to distinct execution log files with no cross-contamination of promotion counts
  2. projekt-forge startup constructs `LLMRouter` with values from `forge_config.yaml` (not env vars) and synthesis requests route to forge's configured Ollama instance
  3. An execution routed through projekt-forge fires the registered storage callback and the event appears in projekt-forge's storage, not only in the JSONL file
  4. A synthesis triggered via projekt-forge passes through the `pre_synthesis_hook` and the enriched prompt is visible in synthesis logs
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Tool Parity & LLM Router | v1.0 | 7/7 | Complete | 2026-04-15 |
| 2. MCP Server Rebuild | v1.0 | 3/3 | Complete | 2026-04-15 |
| 3. Learning Pipeline | v1.0 | 3/3 | Complete | 2026-04-15 |
| 4. API Surface Hardening | v1.1 | 4/4 | Complete | 2026-04-15 |
| 5. Import Rewiring | v1.1 | 5/5 | Complete | 2026-04-18 |
| 6. Learning Pipeline Integration | v1.1 | 0/TBD | Not started | - |
