# Roadmap: forge-bridge

## Milestones

- ✅ **v1.0 Canonical Package & Learning Pipeline** — Phases 1-3 (shipped 2026-04-15)
- ✅ **v1.1 projekt-forge Integration** — Phases 4-6 (shipped 2026-04-19 — v1.1.0 API release, v1.1.1 PATCH-01)
- ✅ **v1.2 Observability & Provenance** — Phases 7, 07.1, 8 (shipped 2026-04-22 — v1.2.0, v1.2.1 hotfix, v1.3.0)
- ✅ **v1.3 Artist Console** — Phases 9, 10, 10.1, 11 (shipped 2026-04-25 — v1.3.1; Phase 12 superseded by v1.4 FB-D)
- ✅ **v1.4 Staged Ops Platform** — Phases 13, 14, 15, 16, 16.1, 16.2 (FB-A..FB-D + two inserted gap-closure phases) (shipped 2026-04-28 — consumed by projekt-forge v1.5)
- ✅ **v1.4.x Carry-Forward Debt** — Phases 17, 18, 19 (shipped 2026-04-30 — `v1.4.1` patch tag)
- 🔄 **v1.5 Legibility** — Phases 20-23 (in progress — opened 2026-04-30)

## Phases

<details>
<summary>✅ v1.0 Canonical Package & Learning Pipeline (Phases 1-3) — SHIPPED 2026-04-15</summary>

- [x] **Phase 1: Tool Parity & LLM Router** (7/7 plans) — completed 2026-04-15
- [x] **Phase 2: MCP Server Rebuild** (3/3 plans) — completed 2026-04-15
- [x] **Phase 3: Learning Pipeline** (3/3 plans) — completed 2026-04-15

Full details: `.planning/milestones/v1.0-ROADMAP.md`

</details>

<details>
<summary>✅ v1.1 projekt-forge Integration (Phases 4-6) — SHIPPED 2026-04-19</summary>

- [x] **Phase 4: API Surface Hardening** (4/4 plans) — completed 2026-04-15
- [x] **Phase 5: Import Rewiring** (5/5 plans) — completed 2026-04-18
- [x] **Phase 6: Learning Pipeline Integration** (4/4 plans) — completed 2026-04-18

Full details: `.planning/milestones/v1.1-ROADMAP.md`

</details>

<details>
<summary>✅ v1.2 Observability & Provenance (Phases 7, 07.1, 8) — SHIPPED 2026-04-22</summary>

- [x] **Phase 7: Tool Provenance in MCP Annotations** (4/4 plans) — completed 2026-04-21 (v1.2.0)
- [x] **Phase 07.1: startup_bridge hotfix + deployment UAT** (5/5 plans) — completed 2026-04-21 (v1.2.1 hotfix)
- [x] **Phase 8: SQL Persistence Protocol** (3/3 plans) — completed 2026-04-22 (v1.3.0)

Full details: `.planning/milestones/v1.2-ROADMAP.md`

</details>

<details>
<summary>✅ v1.3 Artist Console (Phases 9, 10, 10.1, 11) — SHIPPED 2026-04-25</summary>

- [x] **Phase 9: Read API Foundation** (3/3 plans) — completed 2026-04-22
- [x] **Phase 10: Web UI** (8/8 plans) — completed 2026-04-23 (D-36 gate closed by Phase 10.1)
- [x] **Phase 10.1: Artist-UX Gap Closure** (6/6 plans, INSERTED) — completed 2026-04-24
- [x] **Phase 11: CLI Companion** (3/3 plans) — completed 2026-04-25
- ~~Phase 12: LLM Chat~~ — superseded by v1.4 FB-D 2026-04-23 (velocity gate)

Full details: `.planning/milestones/v1.3-ROADMAP.md`

</details>

<details>
<summary>✅ v1.4 Staged Ops Platform (Phases 13, 14, 15, 16, 16.1, 16.2) — SHIPPED 2026-04-28</summary>

- [x] **Phase 13 (FB-A): Staged Operation Entity & Lifecycle** (4/4 plans) — completed 2026-04-26
- [x] **Phase 14 (FB-B): Staged Ops MCP Tools + Read API** (5/5 plans) — completed 2026-04-26
- [x] **Phase 15 (FB-C): LLMRouter Tool-Call Loop** (10/10 plans) — completed 2026-04-27
- [x] **Phase 16 (FB-D): Chat Endpoint** (7/7 plans) — completed 2026-04-27 (CHAT-04 deploy gap routed to 16.1)
- [x] **Phase 16.1 (FB-D gap closure): Chat Tool-List Hang + Wiring Regression Guards** (4/4 plans, INSERTED) — completed 2026-04-28 (Bug D routed to 16.2)
- [x] **Phase 16.2 (FB-D Bug D closure): Chat Tool-Call Loop + Fresh-Operator UAT** (4/4 plans, INSERTED) — completed 2026-04-28 (CHAT-04 closed via PASS-with-deviations)

Full details: `.planning/milestones/v1.4-ROADMAP.md`
Audit: `.planning/milestones/v1.4-MILESTONE-AUDIT.md`

</details>

<details>
<summary>✅ v1.4.x Carry-Forward Debt (Phases 17, 18, 19) — SHIPPED 2026-04-30</summary>

- [x] **Phase 17: Default model bumps** (3/3 plans) — completed 2026-04-29 (MODEL-01 closed; MODEL-02 deferred to v1.5 with empirical evidence)
- [x] **Phase 18: Staged-handlers test harness rework** (3/3 plans) — completed 2026-04-29 (HARNESS-01..03 closed; 22+ tests un-skipped against live Postgres)
- [x] **Phase 19: Code-quality polish** (4/4 plans) — completed 2026-04-30 (POLISH-01..04 closed; WR-02 ref-collision guard, Phase 13 type-contract + atomicity sub-test fixes, qwen2.5-coder tail-token strip)

Full details: `.planning/milestones/v1.4.x-ROADMAP.md`
Audit: `.planning/milestones/v1.4.x-MILESTONE-AUDIT.md`

</details>

### v1.5 Legibility (Phases 20-23)

- [x] **Phase 20: Reality Audit + Canonical Install** - Walk a fresh install end-to-end, fix gaps, ship `docs/INSTALL.md`, refresh README install section + CLAUDE.md ground-truth, pin `install-flame-hook.sh` to v1.4.1 (completed 2026-05-01)
- [ ] **Phase 21: Surface Map + Concept Docs** - Document the five user-facing surfaces and the projekt-forge relationship; ship `docs/GETTING-STARTED.md` and rewrite README "What This Is"
- [ ] **Phase 22: Daily Workflow Recipes** - Step-by-step guides for first-time setup, Claude Desktop wiring, tool synthesis, Flame chat automation, staged-ops approval, and manifest inspection
- [ ] **Phase 23: Diagnostics + Recovery** - Document Flame crash, Postgres restart, Ollama hang, qwen3 cold-start failure modes; ship `docs/TROUBLESHOOTING.md`; polish `forge doctor` if gaps surface

---

## Phase Details

### Phase 20: Reality Audit + Canonical Install
**Goal**: A new user can follow `docs/INSTALL.md` on a fresh machine and reach a working forge-bridge install — every gap found during the audit walk-through is fixed in-flight before the doc ships.
**Depends on**: Nothing (first phase of v1.5)
**Requirements**: INSTALL-01, INSTALL-02, INSTALL-03, INSTALL-04, DOCS-02
**Success Criteria** (what must be TRUE):
  1. A non-author can follow `docs/INSTALL.md` verbatim on a clean machine and reach all five surfaces reachable (Web UI on `:9996/ui/`, CLI `forge-bridge`, `/api/v1/chat`, MCP server, Flame hook on `:9999`) without hitting undocumented errors.
  2. Running `install-flame-hook.sh` with default settings installs the `v1.4.1` Flame hook (not a stale tag).
  3. The README install section and `docs/INSTALL.md` agree on every version number and step — a reader following either reaches the same state.
  4. A user can identify all required external dependencies (Postgres version, Ollama, conda env, Python version, Anthropic API key) from the install doc before starting, without hitting them mid-install.
  5. `CLAUDE.md` reflects v1.4.1 ground truth — the "what exists and works" and "what is designed but not yet implemented" sections match shipped reality, not the v1.0 "extracted from projekt-forge" snapshot.
**Plans**: 6 plans
- [x] 20-01-PLAN.md — Establish v1.4.1 as canonical pinned version (pyproject + script + README curl URL + D-17 consistency guard)
- [x] 20-02-PLAN.md — Refresh CLAUDE.md to v1.4.1 ground truth (5 surfaces + subsystems + active dev context)
- [x] 20-03-PLAN.md — Refresh README install commands + Current Status table to v1.4.1
- [x] 20-04-PLAN.md — Create canonical docs/INSTALL.md (8-step operator-workstation path + Track B carveout)
- [x] 20-05-PLAN.md — Track A non-author UAT on assist-01 (milestone gate per D-02)
- [x] 20-06-PLAN.md — Track B integrator dry-run on Flame-less host (assumption-gap surfacing per D-03)
**UI hint**: yes

### Phase 20.1: Install Bootstrap Script + Systemd Daemon (v1.5 ship blocker) (INSERTED)

**Goal**: A fresh-VM Linux walk on flame-01 (Rocky/RHEL 9) AND a fresh-state macOS walk on portofino can complete the install end-to-end via `sudo ./scripts/install-bootstrap.sh`, edit `/etc/forge-bridge/forge-bridge.env`, and reach all reachable surfaces with `forge doctor` PASS or PARTIAL — closing Phase 20's 13-gap log via the daemon model (systemd units / launchd plists / wrapper scripts / env-file template / reshaped INSTALL.md / new doctor `daemon_state` sub-check).
**Requirements**: INSTALL-01, INSTALL-02, INSTALL-03, INSTALL-04
**Depends on:** Phase 20
**Plans:** 1/7 plans executed

Plans:
- [x] 20.1-01-PLAN.md — Create packaging/forge-bridge.env.example template (env-var defaults + locked seed values; tests/test_packaging.py with 7 lock tests)
- [ ] 20.1-02-PLAN.md — Create packaging/systemd/forge-bridge*.service units (Type=simple, EnvironmentFile=, Requires= cascade, StandardInput=null; 7 systemd regression tests)
- [ ] 20.1-03-PLAN.md — Create packaging/launchd/com.cnoellert.forge-bridge*.plist + wrapper scripts (RunAtLoad, KeepAlive=SuccessfulExit:false, set-a env-source, nc -z readiness gate; 10 launchd regression tests)
- [ ] 20.1-04-PLAN.md — Create scripts/install-bootstrap.sh (Postgres bootstrap + auth alignment + role+db + alembic + env-file + units/plists install + daemon start + doctor verification; 7 script regression tests)
- [ ] 20.1-05-PLAN.md — Add forge_bridge.cli.doctor `_check_daemon_state` sub-check (D-13 single-row OS-branched probe; 3 pytest cases)
- [ ] 20.1-06-PLAN.md — Reshape docs/INSTALL.md Steps 3, 5, 6 (script + env-file + daemon model; delete Phase 20 gap #11 doc lie)
- [ ] 20.1-07-PLAN.md — Walk fresh-VM Linux on flame-01 + fresh-state macOS on portofino (HUMAN-UAT × 2; both walks gate per D-18); plant SEED-PHASE-20.1-ARTIST-UAT-V1.6+.md per D-19

### Phase 21: Surface Map + Concept Docs
**Goal**: A new user can read `docs/GETTING-STARTED.md` and understand what forge-bridge's five surfaces are, what each is for, how they fit together, and how forge-bridge relates to projekt-forge — without reading source code.
**Depends on**: Phase 20 (needs accurate ground truth from the install audit before documenting surfaces)
**Requirements**: DOCS-01, DOCS-03, DOCS-04
**Success Criteria** (what must be TRUE):
  1. A non-author can read `README.md` and understand what forge-bridge is, what it ships at v1.4.1, and which surfaces are available — without reading source code.
  2. A non-author can read `docs/GETTING-STARTED.md` and identify the five user-facing surfaces (Web UI on `:9996/ui/`, CLI `forge-bridge`, `/api/v1/chat` HTTP, MCP server `python -m forge_bridge`, Flame hook on `:9999`), what each is for, and how they fit together.
  3. A user can find an explicit statement of forge-bridge's relationship to projekt-forge (consumer pattern, version pin discipline) in `README.md` or `docs/GETTING-STARTED.md`.
**Plans**: TBD
**UI hint**: yes

### Phase 22: Daily Workflow Recipes
**Goal**: A user who has completed the install can follow step-by-step recipes for every daily workflow — from first-time setup through Flame chat automation and manifest inspection — and reach the stated outcome each time.
**Depends on**: Phase 20, Phase 21 (recipes assume install completed and surfaces understood)
**Requirements**: RECIPES-01, RECIPES-02, RECIPES-03, RECIPES-04, RECIPES-05, RECIPES-06
**Success Criteria** (what must be TRUE):
  1. A non-author can follow the "first-time setup on a personal workstation" recipe (after completing INSTALL-01) and reach a state where they can run a sample query against `:9996/ui/`.
  2. A non-author can follow the "connect Claude Desktop / Claude Code to forge-bridge" recipe and successfully invoke an MCP tool from their LLM client.
  3. A non-author can follow the "watch tool synthesis happen" recipe and observe the learning pipeline promoting a repeated operation into a new MCP tool with provenance metadata visible.
  4. A non-author can follow the "drive multi-step Flame automation via `/api/v1/chat`" recipe (on an operator workstation with a working Flame setup) and see the agentic tool-call loop execute Flame operations end-to-end with a natural-language answer at the end. (Prerequisite: assist-01 or equivalent workstation with Flame running.)
  5. A non-author can follow the "approve / reject staged operations from the Web UI" recipe and complete a full staged-operation lifecycle from `proposed` to `approved` to `executed`.
  6. A non-author can follow the "inspect the manifest to see auto-promoted tools" recipe across all three paths (Web UI, CLI, MCP resource) and verify provenance fields (`origin`, `code_hash`, `synthesized_at`, `version`, `observation_count`).
**Plans**: TBD
**UI hint**: yes

### Phase 23: Diagnostics + Recovery
**Goal**: A user who hits a common failure mode (Flame crash, Postgres restart, Ollama hang, qwen3 cold-start budget exceeded) can consult `docs/TROUBLESHOOTING.md` and recover without re-deriving the topology from scratch — and `forge doctor` output covers every failure mode named in that doc.
**Depends on**: Phase 22 (recipe authoring surfaces failure modes that inform troubleshooting coverage; sequential is preferred)
**Requirements**: DIAG-01, DIAG-02, DIAG-03, DIAG-04, DIAG-05
**Success Criteria** (what must be TRUE):
  1. A non-author can follow `docs/TROUBLESHOOTING.md` to diagnose a Flame crash and recover the bridge — including the MCP server's graceful-degradation behavior with Flame offline.
  2. A non-author can follow `docs/TROUBLESHOOTING.md` to diagnose a Postgres restart or unavailability and recover — understanding the JSONL-authoritative + SQL-mirror semantics and the correct restart sequence.
  3. A non-author can follow `docs/TROUBLESHOOTING.md` to diagnose an Ollama hang or cold start and apply a recovery path (model preload, timeout signals).
  4. A non-author can follow `docs/TROUBLESHOOTING.md` to diagnose a qwen3 cold-start `LLMLoopBudgetExceeded` and apply a recovery path — including model selection guidance and the context from `SEED-DEFAULT-MODEL-BUMP-V1.4.x`.
  5. Every failure mode named in `docs/TROUBLESHOOTING.md` is covered by `forge doctor` output — or `forge doctor` has been polished in-flight during this phase to close the gaps.
**Plans**: TBD

---

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Tool Parity & LLM Router | v1.0 | 7/7 | Complete | 2026-04-15 |
| 2. MCP Server Rebuild | v1.0 | 3/3 | Complete | 2026-04-15 |
| 3. Learning Pipeline | v1.0 | 3/3 | Complete | 2026-04-15 |
| 4. API Surface Hardening | v1.1 | 4/4 | Complete | 2026-04-15 |
| 5. Import Rewiring | v1.1 | 5/5 | Complete | 2026-04-18 |
| 6. Learning Pipeline Integration | v1.1 | 4/4 | Complete | 2026-04-18 |
| 7. Tool Provenance in MCP Annotations | v1.2 | 4/4 | Complete | 2026-04-21 |
| 07.1. startup_bridge hotfix + deployment UAT | v1.2 | 5/5 | Complete | 2026-04-21 |
| 8. SQL Persistence Protocol | v1.2 | 3/3 | Complete | 2026-04-22 |
| 9. Read API Foundation | v1.3 | 3/3 | Complete | 2026-04-22 |
| 10. Web UI | v1.3 | 8/8 | Complete (D-36 gate closed by Phase 10.1) | 2026-04-23 |
| 10.1. Artist-UX Gap Closure | v1.3 | 6/6 | Complete    | 2026-04-24 |
| 11. CLI Companion | v1.3 | 3/3 | Complete   | 2026-04-25 |
| 12. LLM Chat | v1.3 | 0/? | Superseded by Phase 16 (FB-D) (velocity gate triggered) | - |
| 13 (FB-A). Staged Operation Entity & Lifecycle | v1.4 | 4/4 | Complete    | 2026-04-26 |
| 14 (FB-B). Staged Ops MCP Tools + Read API | v1.4 | 5/5 | Complete    | 2026-04-26 |
| 15 (FB-C). LLMRouter Tool-Call Loop | v1.4 | 10/10 | Complete    | 2026-04-27 |
| 16 (FB-D). Chat Endpoint | v1.4 | 7/7 | Complete (CHAT-04 deploy gap routed to 16.1) | 2026-04-27 |
| 16.1 (FB-D gap closure). Chat Tool-List Hang + Wiring Regression Guards | v1.4 | 4/5 | Complete    | 2026-04-28 |
| 16.2 (FB-D Bug D closure). Chat Tool-Call Loop + Fresh-Operator UAT | v1.4 | 4/4 | Complete    | 2026-04-28 |
| 17. Default model bumps | v1.4.x | 3/3 | Complete    | 2026-04-29 |
| 18. Staged-handlers test harness rework | v1.4.x | 3/3 | Complete    | 2026-04-29 |
| 19. Code-quality polish | v1.4.x | 4/4 | Complete    | 2026-04-30 |
| 20. Reality Audit + Canonical Install | v1.5 | 7/7 | Complete    | 2026-05-01 |
| 21. Surface Map + Concept Docs | v1.5 | 0/? | Not started | - |
| 22. Daily Workflow Recipes | v1.5 | 0/? | Not started | - |
| 23. Diagnostics + Recovery | v1.5 | 0/? | Not started | - |
