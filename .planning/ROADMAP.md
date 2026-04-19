# Roadmap: forge-bridge

## Milestones

- ✅ **v1.0 Canonical Package & Learning Pipeline** — Phases 1-3 (shipped 2026-04-15)
- ✅ **v1.1 projekt-forge Integration** — Phases 4-6 (shipped 2026-04-19 — v1.1.0 API release, v1.1.1 PATCH-01)
- 🟢 **v1.2 Observability & Provenance** — Phases 7-8 (scoping; kickoff pending `/gsd-new-milestone`)

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

### 🟢 v1.2 Observability & Provenance (scoping)

**Milestone Goal (draft):** Surface what forge-bridge has synthesized (tool provenance in MCP annotations) and where it has persisted executions (SQL backend for the learning-pipeline storage callback) — so downstream consumers can reason about synthesis history without scraping JSONL files.

Phases TBD via `/gsd-new-milestone`. Candidate scope:

- **Phase 7: Tool provenance in MCP annotations (EXT-02)** — lift `.tags.json` sidecars (produced by Phase 6-02) into MCP tool annotations; bundle WR-01/WR-02 hygiene + README conda-env guidance
- **Phase 8: SQL persistence backend for ExecutionLog (EXT-03)** — define `StoragePersistence` Protocol on the bridge side; implement in projekt-forge via SQLAlchemy + Alembic

**Stretch / deferred:** EXT-01 (shared synthesis manifest between repos) — scope unclear; revisit after Phase 7 clarifies what metadata needs sharing.

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Tool Parity & LLM Router | v1.0 | 7/7 | Complete | 2026-04-15 |
| 2. MCP Server Rebuild | v1.0 | 3/3 | Complete | 2026-04-15 |
| 3. Learning Pipeline | v1.0 | 3/3 | Complete | 2026-04-15 |
| 4. API Surface Hardening | v1.1 | 4/4 | Complete | 2026-04-15 |
| 5. Import Rewiring | v1.1 | 5/5 | Complete | 2026-04-18 |
| 6. Learning Pipeline Integration | v1.1 | 4/4 | Complete | 2026-04-18 |
