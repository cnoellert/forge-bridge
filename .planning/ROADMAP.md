# Roadmap: forge-bridge

## Milestones

- ✅ **v1.0 Canonical Package & Learning Pipeline** — Phases 1-3 (shipped 2026-04-15)
- ✅ **v1.1 projekt-forge Integration** — Phases 4-6 (shipped 2026-04-19 — v1.1.0 API release, v1.1.1 PATCH-01)
- ✅ **v1.2 Observability & Provenance** — Phases 7, 07.1, 8 (shipped 2026-04-22 — v1.2.0, v1.2.1 hotfix, v1.3.0)
- ✅ **v1.3 Artist Console** — Phases 9, 10, 10.1, 11 (shipped 2026-04-25 — v1.3.1; Phase 12 superseded by v1.4 FB-D)
- ✅ **v1.4 Staged Ops Platform** — Phases 13, 14, 15, 16, 16.1, 16.2 (FB-A..FB-D + two inserted gap-closure phases) (shipped 2026-04-28 — consumed by projekt-forge v1.5)
- 🚧 **v1.4.x Carry-Forward Debt** — Phases 17-19 (opened 2026-04-28 — patch milestone targeting `v1.4.1` tag)

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

### 🚧 v1.4.x Carry-Forward Debt (opened 2026-04-28)

- [x] **Phase 17: Default model bumps** — `LLMRouter._cloud_model` and `_local_model` default flips. Closes SEED-CLOUD-MODEL-BUMP-V1.4.x and SEED-DEFAULT-MODEL-BUMP-V1.4.x. Single-commit isolated `_DEFAULT_*` constant changes per the SEED decoupled-commit mandate. **Requirements**: MODEL-01, MODEL-02 (completed 2026-04-29)
  **Plans:** 3 plans
  Plans:
  - [x] 17-01-PLAN.md — Extract `_DEFAULT_LOCAL_MODEL` + `_DEFAULT_CLOUD_MODEL` module constants (pure refactor, values preserved)
  - [x] 17-02-PLAN.md — MODEL-01: bump `_DEFAULT_CLOUD_MODEL` to `claude-sonnet-4-6` + plant SEED-OPUS-4-7-TEMPERATURE-V1.5 + live LLMTOOL-02 gate
  - [x] 17-03-PLAN.md — MODEL-02: defer (per 2026-04-28 assist-01 pre-run UAT) — retarget SEED-DEFAULT-MODEL-BUMP-V1.4.x to v1.5 with empirical evidence
- [ ] **Phase 18: Staged-handlers test harness rework** — Migrate 3 test files (23 tests) from `starlette.TestClient` (sync) to `httpx.AsyncClient(transport=ASGITransport(app=...))` so the test event loop matches the asyncpg session loop. Seed parent `DBProject` rows via a new `seeded_project` fixture. Remove the `FORGE_TEST_DB=1` opt-in gate AND wrap the `pg_terminate_backend` teardown SQL. **Requirements**: HARNESS-01, HARNESS-02, HARNESS-03
  **Plans:** 3 plans
  Plans:
  - [x] 18-01-PLAN.md — HARNESS-01: migrate `staged_client` fixture from `starlette.testclient.TestClient` to `httpx.AsyncClient(transport=ASGITransport)` + add `await` at 31 call sites across 3 console test files
  - [x] 18-02-PLAN.md — HARNESS-02: add `seeded_project` fixture in `tests/conftest.py` + wire into 3 FK-violating tests (2 store + 1 console); inline-seed second `DBProject` for filter discrimination; atomicity test logic bug deferred to POLISH-03 per CONTEXT D-07
  - [ ] 18-03-PLAN.md — HARNESS-03: remove `FORGE_TEST_DB=1` gate from `_phase13_postgres_available()` + wrap `pg_terminate_backend` teardown SQL in `try/except Exception` (sequenced LAST per CONTEXT D-01)
- [ ] **Phase 19: Code-quality polish** — WR-02 ref-collision guard in salvage helper; Phase 13 type-contract + atomicity sub-test fixes; qwen2.5-coder `<|im_start|>` tail-token strip in chat handler. **Requirements**: POLISH-01, POLISH-02, POLISH-03, POLISH-04

**Milestone Goal**: Pay down v1.4 carry-forward debt as a clean patch release. Ship a polished `v1.4.1` that projekt-forge v1.5 can pin against without test-harness or model-default surprises. Each requirement maps to a specific debt item surfaced during v1.4 close-out (`.planning/milestones/v1.4-MILESTONE-AUDIT.md`).

**Out of scope (carry to v1.5)**: SEED-CHAT-STREAMING-V1.4.x (its trigger condition was not reported in Phase 16.2 UAT); all V1.5+ planted seeds; sensitive-routing changes (waits on auth).

**Target tag**: `v1.4.1` after Phase 19 ships and a single post-milestone audit confirms 9/9 requirements closed.

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
| 18. Staged-handlers test harness rework | v1.4.x | 2/3 | In Progress|  |
| 19. Code-quality polish | v1.4.x | 0/? | Open | - |
