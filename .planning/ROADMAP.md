# Roadmap: forge-bridge

## Milestones

- ✅ **v1.0 Canonical Package & Learning Pipeline** — Phases 1-3 (shipped 2026-04-15)
- ✅ **v1.1 projekt-forge Integration** — Phases 4-6 (shipped 2026-04-19 — v1.1.0 API release, v1.1.1 PATCH-01)
- ✅ **v1.2 Observability & Provenance** — Phases 7, 07.1, 8 (shipped 2026-04-22 — v1.2.0, v1.2.1 hotfix, v1.3.0)
- 📋 **v1.3 Artist Console** — Phases 9-12 (in progress)

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

### 📋 v1.3 Artist Console (Phases 9-12)

- [ ] **Phase 9: Read API Foundation** — ConsoleReadAPI, ManifestService singleton, instance-identity gate, uvicorn task on `:9996`, MCP resources + tool fallback shim
- [ ] **Phase 10: Web UI** — Jinja2 + htmx + Alpine.js, five views (tools, execs, manifest, health, chat nav), structured query console, health header strip
- [ ] **Phase 11: CLI Companion** — Typer subcommands (tools, execs, manifest, health, doctor), Rich output, --json flags
- [ ] **Phase 12: LLM Chat** — /api/v1/chat endpoint, Web UI chat panel, sanitized context assembly, token budget cap (velocity-gated; may defer to v1.4)

## Phase Details

### Phase 9: Read API Foundation
**Goal**: The shared read layer is live — `ConsoleReadAPI` is the sole read path for all surfaces, `ManifestService` singleton is injected into the watcher and console router, the console HTTP API runs on `:9996` as a separate uvicorn asyncio task inside `_lifespan`, and MCP resources plus tool fallback shim are registered so every client can reach manifest and tool data from Phase 9 onward.
**Depends on**: Phase 8 (v1.3.0 foundation — StoragePersistence, ExecutionLog, watcher, `_lifespan`)
**Requirements**: API-01, API-02, API-03, API-04, API-05, API-06, MFST-01, MFST-02, MFST-03, MFST-06, TOOLS-04, EXECS-04
**Success Criteria** (what must be TRUE):
  1. An MCP client completing `tools/list` while the console HTTP API is serving traffic on `:9996` sees no errors or stdout corruption — MCP stdio wire is clean.
  2. `GET /api/v1/manifest` returns the current synthesis manifest as JSON, and `forge_manifest_read` tool + `resources/read forge://manifest/synthesis` return identical data from a real (non-mocked) MCP session.
  3. `GET /api/v1/tools`, `GET /api/v1/execs`, and `GET /api/v1/health` all return JSON; a live `bridge.execute()` call produces a record visible via `GET /api/v1/execs` — confirming the ExecutionLog instance-identity gate (API-04).
  4. If `:9996` is unavailable at startup, the MCP server boots anyway and logs a WARNING — mirroring the v1.2.1 degradation pattern.
  5. Existing stdio integration tests pass with no `--http` flag — transport posture is unchanged.
**Plans**: 3 plans
  - [ ] 09-01-PLAN.md — Typer entrypoint refactor + ruff T20 lint gate (unblocks console CLI + enforces print-ban before console package lands)
  - [ ] 09-02-PLAN.md — Console package data layer: ManifestService singleton + ConsoleReadAPI facade + ExecutionLog deque snapshot + watcher injection
  - [ ] 09-03-PLAN.md — Surface layer: Starlette app on :9996 as uvicorn asyncio task, MCP resources + tool shims, _lifespan D-31 wiring, LOGGING_CONFIG stdio-safety, SC#1 stdout-cleanliness integration test

---

### Phase 10: Web UI
**Goal**: An artist can open `http://localhost:9996/ui/` in a browser and navigate five fully-functional views — tools table with provenance drilldown, execution history with per-record detail, manifest browser, health panel, and chat navigation stub — served from Jinja2 templates with htmx partial refreshes and Alpine.js state, with no npm build step required and a persistent health strip visible on every page.
**Depends on**: Phase 9 (ConsoleReadAPI and HTTP API must be stable before any template layer is built on top)
**Requirements**: CONSOLE-01, CONSOLE-02, CONSOLE-03, CONSOLE-04, CONSOLE-05, TOOLS-01, TOOLS-02, EXECS-01, EXECS-02, MFST-04, HEALTH-01, HEALTH-04

**CONTEXT NOTE — UI design contract:** Before `/gsd-plan-phase 10` generates plans, run `/gsd-ui-phase` to produce `UI-SPEC.md`. The phase plan must reference that spec; do not write CSS palette or layout rules into plans before `UI-SPEC.md` exists.

**Success Criteria** (what must be TRUE):
  1. A fresh `pip install forge-bridge` from the built wheel followed by starting the server and opening `http://localhost:9996/ui/` in Chrome or Safari loads all static assets without any npm commands and without CORS errors in the browser console.
  2. Non-developer dogfood: an operator who is not the developer opens the Web UI cold and identifies the three most recently synthesized tools and their status (active / quarantined) within 30 seconds.
  3. Artist can click into any tool and see its canonical `_meta` provenance fields (origin, code_hash, synthesized_at, version, observation_count) and raw source for synthesized tools — no jargon-only displays.
  4. Health strip is visible on every view and updates automatically (poll) — artist can see at a glance whether Flame bridge, LLM backends, and watcher are reachable without navigating away.
  5. Structured query console accepts a filter expression (e.g. `origin:synthesized`, `promoted:true`) and the view updates deterministically without an LLM call.
**Plans**: TBD
**UI hint**: yes

---

### Phase 11: CLI Companion
**Goal**: An operator on a headless server or SSH session can run `forge-bridge console <subcommand>` and get the same information surfaced by the Web UI — tool list, execution history, manifest, health status, and a `doctor` pre-flight check — with Rich-formatted output in a TTY and plain JSON when piped.
**Depends on**: Phase 10 (CLI calls the same console HTTP API; building after Phase 10 means the API contract is tested by real Web UI usage before the CLI writes against it)
**Requirements**: CLI-01, CLI-02, CLI-03, CLI-04, TOOLS-03, EXECS-03, MFST-05, HEALTH-02, HEALTH-03
**Success Criteria** (what must be TRUE):
  1. `forge-bridge console tools` output matches `/api/v1/tools` JSON for the same runtime state — zero divergence between CLI and Web UI data.
  2. `forge-bridge console doctor` exits non-zero when any health check fails and prints an actionable remediation hint per failure — suitable for CI gating.
  3. `forge-bridge console doctor` prints a clear "server is not running — start with `python -m forge_bridge`" message when `:9996` is unreachable, rather than a raw connection error.
  4. Non-developer dogfood: an operator can answer "what synthesized tools are active?" and "when did the last execution run?" from the terminal without opening a browser, within 30 seconds.
**Plans**: TBD

---

### Phase 12: LLM Chat
**Goal**: An artist can type a natural-language question about the pipeline state into the Web UI chat panel (e.g. "what synthesis tools were created this week?") and receive a useful, safely-assembled answer from the LLM router — with deterministic cost protection (token budget cap, rate limiter) and graceful degradation when no LLM backend is healthy.

**Velocity gate:** This phase is included as a v1.3 target but is explicitly deferrable to v1.4 if Phases 9-11 run long. Do not defer silently — roadmapper must make an explicit scope decision before Phase 11 closes.

**Depends on**: Phase 10 (Web UI chat panel lives in the Web UI template layer); Phase 9 (ManifestService + ExecutionLog.snapshot() provide context for the chat endpoint)
**Requirements**: CHAT-01, CHAT-02, CHAT-03, CHAT-04
**Success Criteria** (what must be TRUE):
  1. Eleven rapid requests from the same IP within one minute: the eleventh returns HTTP 429 with a clear "rate limit exceeded" message — cost cap is enforced.
  2. A mocked `LLMRouter.acomplete()` that blocks indefinitely causes the endpoint to return a timeout error within 125 seconds — no hung requests.
  3. A tool whose sidecar name contains an injection marker (e.g. `IGNORE PREVIOUS INSTRUCTIONS`) does not propagate that string into the LLM context — sanitization boundary holds.
  4. Non-developer dogfood: an artist asks "what synthesis tools were created this week?" in the chat panel and receives a useful, plain-English answer within the LLM's normal response time.
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
| 9. Read API Foundation | v1.3 | 0/3 | Not started | - |
| 10. Web UI | v1.3 | 0/? | Not started | - |
| 11. CLI Companion | v1.3 | 0/? | Not started | - |
| 12. LLM Chat | v1.3 | 0/? | Not started | - |
