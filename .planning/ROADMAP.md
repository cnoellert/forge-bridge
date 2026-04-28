# Roadmap: forge-bridge

## Milestones

- ✅ **v1.0 Canonical Package & Learning Pipeline** — Phases 1-3 (shipped 2026-04-15)
- ✅ **v1.1 projekt-forge Integration** — Phases 4-6 (shipped 2026-04-19 — v1.1.0 API release, v1.1.1 PATCH-01)
- ✅ **v1.2 Observability & Provenance** — Phases 7, 07.1, 8 (shipped 2026-04-22 — v1.2.0, v1.2.1 hotfix, v1.3.0)
- ✅ **v1.3 Artist Console** — Phases 9, 10, 10.1, 11 (shipped 2026-04-25 — v1.3.1; Phase 12 superseded by v1.4 FB-D)
- ✅ **v1.4 Staged Ops Platform** — Phases 13, 14, 15, 16, 16.1, 16.2 (FB-A..FB-D + two inserted gap-closure phases) (shipped 2026-04-28 — consumed by projekt-forge v1.5)

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
