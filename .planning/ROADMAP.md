# Roadmap: forge-bridge

## Milestones

- ✅ **v1.0 Canonical Package & Learning Pipeline** — Phases 1-3 (shipped 2026-04-15)
- ✅ **v1.1 projekt-forge Integration** — Phases 4-6 (shipped 2026-04-19 — v1.1.0 API release, v1.1.1 PATCH-01)
- 🟢 **v1.2 Observability & Provenance** — Phases 7-8 (active — planning)

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

### 🟢 v1.2 Observability & Provenance (Phases 7-8)

**Milestone Goal:** Surface what forge-bridge has synthesized (tool provenance in MCP annotations) and where it has persisted executions (SQL backend for the learning-pipeline storage callback) — so downstream consumers can reason about synthesis history without scraping JSONL files.

- [ ] **Phase 7: Tool Provenance in MCP Annotations (EXT-02 → v1.2.0)** — lift `.tags.json` sidecars into MCP `Tool._meta` via sidecar-schema evolution + watcher/registry wiring; bundle WR-01/WR-02 hygiene + README conda-env guidance
- [ ] **Phase 8: SQL Persistence Protocol (EXT-03 → v1.2.1 or v1.3.0)** — define `StoragePersistence` Protocol on the bridge side + cross-repo SQLAlchemy adapter in projekt-forge; Protocol-only on bridge, all DDL in consumer

**Ordering:** Strictly sequential. Phase 7 ships v1.2.0, projekt-forge pins and UATs, *then* Phase 8 starts. Matches the v1.1 Phase 5 → Phase 6 gate pattern; shared `__all__` barrel edits + potential `ExecutionRecord` evolution forbid parallelism.

**Stretch / deferred:** EXT-01 (shared synthesis manifest between repos) — revisit after Phase 7 clarifies what `_meta` payload is actually consumed. DF-02.1..DF-02.3, DF-03.1..DF-03.4 — candidates for v1.3 once observability data is in production.

## Phase Details

### Phase 7: Tool Provenance in MCP Annotations

**Goal:** Consumers calling `tools/list` over MCP see canonical provenance fields on every synthesized tool (origin, code_hash, synthesized_at, version, observation_count) under the `forge-bridge/*` namespace in `Tool._meta`, with consumer-supplied tags passing through a sanitization boundary that strips injection markers and enforces size budgets.
**Depends on:** Phase 6 (v1.1.0 shipped — `.tags.json` sidecar write-path, `ExecutionRecord` frozen, barrel at 15 symbols)
**Requirements:** PROV-01, PROV-02, PROV-03, PROV-04, PROV-05, PROV-06
**Success Criteria** (what must be TRUE):
  1. An MCP client calling `tools/list` against a forge-bridge server with synthesized tools present receives `Tool._meta` payloads keyed under `forge-bridge/origin`, `forge-bridge/code_hash`, `forge-bridge/synthesized_at`, `forge-bridge/version`, `forge-bridge/observation_count` — verifiable via `mcp==1.26.0` roundtrip on `qwen2.5-coder:32b` against assist-01
  2. A synthesized tool registered with a `.sidecar.json` envelope (`{"tags": [...], "meta": {...}, "schema_version": 1}`) surfaces its tags on the MCP wire; a legacy `.tags.json` sidecar still loads via the backward-compat grace path; a missing sidecar registers the tool with default `_meta` and no crash
  3. A consumer-supplied tag containing control chars (`\n`, `\x00`..`\x1f`), injection markers (`ignore previous`, `<|`, `[INST]`, triple-backtick, `---`), or exceeding 64 chars is rejected at the `_sanitize_tag()` boundary with a WARNING log; every synthesized tool's `_meta` payload stays ≤ 4 KB and ≤ 16 tags per tool
  4. Every synthesized tool registered has `annotations.readOnlyHint=False` set explicitly — verifiable by inspecting the `Tool` payload returned from `tools/list` (MCP clients MUST NOT auto-approve forge-synthesized tools)
  5. projekt-forge pinned to `forge-bridge @ git+...@v1.2.0`, re-run live-UAT against assist-01 Ollama, `tools/list` diff shows only additive `_meta` changes on `synth_*` tools — no regressions on builtin `flame_*`/`forge_*` tools
**Plans:** 4 plans

Plans:
- [x] 07-01-PLAN.md — Sidecar schema evolution: synthesizer writes `.sidecar.json` envelope `{"tags": [...], "meta": {...}, "schema_version": 1}` with five canonical `forge-bridge/*` meta keys; round-trip test (PROV-01)
- [x] 07-02-PLAN.md — Watcher read-path + `_sanitize_tag()` + size budgets + redaction allowlist; `.sidecar.json` preferred, `.tags.json` fallback; feature-detect `provenance=` in `_scan_once` (PROV-01, PROV-03)
- [x] 07-03-PLAN.md — `register_tool(..., provenance=)` kwarg + `_meta` merge + `readOnlyHint=False` synthesized baseline + WR-01 async callback test + WR-02 `ExecutionRecord` docstring fix + README conda-env section (PROV-02, PROV-04, PROV-05, PROV-06)
- [ ] 07-04-PLAN.md — Release ceremony: `mcp[cli]>=1.19,<2` pin, `v1.2.0` annotated tag on main, GitHub release (wheel + sdist), projekt-forge pin bump + cross-repo UAT `tools/list` diff

**Release artifact:** annotated `v1.2.0` tag on `main`, GitHub release with wheel + sdist. Hard gate: projekt-forge must pin `@v1.2.0` and UAT clean before Phase 8 starts.

**UI hint:** no

### Phase 07.1: startup_bridge graceful degradation hotfix + deployment UAT (INSERTED)

**Goal:** Ship forge-bridge v1.2.1 whose MCP server boots cleanly when the standalone forge-bridge WebSocket server on :9998 is unreachable (honoring the existing docstring/warning-log contract of graceful degradation), then re-UAT PROV-02 via a real MCP client session instead of the monkey-patched harness used in Phase 7-04.
**Requirements**: Defect fix — no REQ-ID (exposed during Phase 7 UAT; no matching entry in REQUIREMENTS.md)
**Depends on:** Phase 7 (v1.2.0 released 2026-04-20)
**Success Criteria** (what must be TRUE):
  1. `python -m projekt_forge --no-db` (and `python -m forge_bridge`) in the `forge` conda env on Portofino boots cleanly with no process on :9998 — no exceptions escape the MCP server's lifespan, `tools/list` succeeds over stdio, `flame_ping` returns Flame's live state. NO monkey-patches or shims involved.
  2. A regression test exists in `tests/` that FAILS against forge-bridge v1.2.0 and PASSES against the v1.2.1 fix (nyquist gate: spins up the MCP server with `FORGE_BRIDGE_URL` pointed at a dead port, asserts the server still serves a `tools/list` request).
  3. forge-bridge v1.2.1 tagged, pushed, and released on GitHub with wheel + sdist; release notes clearly call out "hotfix" and "no PROV-02 changes".
  4. projekt-forge re-pinned to `@v1.2.1` (line 25 of its pyproject.toml), reinstalled in the `forge` env, and its `pytest tests/` remains green at the 422 baseline.
  5. A real MCP client (the user's Claude Code session on Portofino, with projekt-forge registered as an MCP server) observes PROV-02 `_meta` fields (`forge-bridge/origin: synthesizer`, `code_hash`, `synthesized_at`, `version`, `observation_count`) on a freshly Ollama-synthesized `synth_*` tool — verified end-to-end with evidence captured in `07.1-UAT-EVIDENCE.md` including verbatim tool-call result objects.
  6. Phase 7 close-out unblocked: `07-04-SUMMARY.md` backfilled with pointer to 07.1 as the true UAT vehicle; `07-04` plan marked complete; Phase 7 verification pipeline can proceed.
**Plans:** 3/5 plans executed

Plans:
- [x] 07.1-01-PLAN.md — RED/GREEN fix + regression test: failing test for startup_bridge graceful degradation (TDD RED), then try/except expansion to wrap both `_client.start()` and `wait_until_connected()` with `_client = None` nulling on failure (TDD GREEN). Covers SC1, SC2.
- [x] 07.1-02-PLAN.md — Release ceremony: bump pyproject.toml 1.2.0→1.2.1, update test_public_api.py version-guard, annotated `v1.2.1` tag on main, GitHub release with wheel + sdist and hotfix-framed release notes. Covers SC3.
- [x] 07.1-03-PLAN.md — Cross-repo re-pin: sed projekt-forge/pyproject.toml `@v1.2.0`→`@v1.2.1`, reinstall in `forge` conda env, verify site-packages resolution, regression-gate `pytest tests/` at 422-baseline. Covers SC4.
- [ ] 07.1-04-PLAN.md — Deployment UAT via real MCP client: register projekt-forge in Claude Code via `claude mcp add` + write HANDOFF.md + STOP for user-restart; fresh session runs 6-step UAT checklist + writes verbatim 07.1-UAT-EVIDENCE.md + cleanup. Covers SC5.
- [ ] 07.1-05-PLAN.md — Phase 7 close-out: backfill 07-04-SUMMARY.md with pointer to 07.1-UAT-EVIDENCE.md as the canonical UAT artifact; mark 07-04 complete in ROADMAP via `gsd-tools.cjs roadmap update-plan-progress`. Covers SC6.

### Phase 8: SQL Persistence Protocol

**Goal:** Consumers have a typed, documented contract (`StoragePersistence` Protocol) for mirroring `ExecutionRecord` writes into durable storage, with projekt-forge's `_persist_execution` stub replaced by a real sync-SQLAlchemy adapter that inserts rows idempotently and survives DB outages without retrying in the callback.
**Depends on:** Phase 7 (v1.2.0 shipped, projekt-forge pin bumped + UAT clean)
**Requirements:** STORE-01, STORE-02, STORE-03, STORE-04, STORE-05, STORE-06
**Success Criteria** (what must be TRUE):
  1. `from forge_bridge import StoragePersistence` succeeds in a clean virtualenv; `isinstance(fn, StoragePersistence)` returns `True` for an `async def persist(record): ...` function, `False` for a non-callable — verifiable via a contract test in `tests/learning/test_storage_protocol.py`; `__all__` grows 15 → 16
  2. `ExecutionLog.set_storage_callback()` signature is unchanged from v1.1.0; consumers pass `backend.persist` (bound method) as the existing callable and the existing sync/async detection via `inspect.iscoroutinefunction` still works
  3. After projekt-forge upgrades to the v1.2.1 (or v1.3.0) pin, every `ExecutionLog.record()` call results in a row in projekt-forge's `execution_log` SQL table (modulo DB outages, which are logged-and-swallowed); two forge-bridge processes writing to distinct JSONL paths produce no duplicate rows in the shared DB thanks to `on_conflict_do_nothing(index_elements=["code_hash","timestamp"])`
  4. A simulated DB outage during a synthesis burst produces exactly one WARNING log line per failed callback (no retry stacking, no `QueuePool exhausted`); JSONL writes proceed unaffected; no async tasks stack beyond the normal steady-state count
  5. CONTEXT.md documents the consistency model (log-authoritative, eventual, best-effort), the no-retry invariant (P-03.5), and the sync-callback recommendation (P-03.8); forge-bridge ships NO DDL, NO Alembic migrations, NO SQLAlchemy models — only the Protocol + docstring
**Plans:** TBD (research suggests 3 plans — see below)

Suggested plan structure (to be ratified by `/gsd-plan-phase 8`):
- **08-01** — `StoragePersistence` Protocol + barrel re-export + consistency-model CONTEXT.md: new `forge_bridge/learning/storage.py` with `@runtime_checkable` Protocol (`persist`, `persist_batch`, `shutdown`); `forge_bridge/__init__.py` re-export; `__all__` grows 15 → 16; Protocol docstring carries the canonical minimal schema (columns + unique constraint + indexes); CONTEXT.md locks (a) "Protocol-only on bridge side — no DDL, no migrations" (P-03.3), (b) "eventual, best-effort, log-authoritative" consistency (P-03.2), (c) "no retry in callback, ever" (P-03.5), (d) sync-callback recommendation (P-03.8); no ExecutionRecord field additions
- **08-02** — projekt-forge sync SQLAlchemy adapter + Alembic migration + isinstance check *(CROSS-REPO: `/Users/cnoellert/Documents/GitHub/projekt-forge/`)*: `_persist_execution` stub body swapped from logger → sync SQLAlchemy session-per-call using `sessionmaker.begin()` context manager (not `AsyncSession`); `insert(...).on_conflict_do_nothing(index_elements=["code_hash","timestamp"])` for idempotency (TS-03.3); new Alembic revision on projekt-forge's existing chain creating `execution_log` table (code_hash TEXT, timestamp TIMESTAMPTZ, raw_code TEXT, intent TEXT NULL, promoted BOOLEAN + unique (code_hash, timestamp) + indexes on code_hash and timestamp DESC); `assert isinstance(_persist_execution, StoragePersistence)` at registration; cutover-over-backfill decision ratified (P-03.4); mirrors the Phase 6 Plan 04 cross-repo pattern
- **08-03** — Release ceremony: annotated `v1.2.1` (or `v1.3.0` if `__all__` delta is perceived as a minor-bump trigger) tag on forge-bridge `main`; projekt-forge pin bump + UAT verifying SQL rows appear after real Flame executions + `QueuePool` stays bounded under simulated DB outage; final milestone close via `/gsd-complete-milestone`

**Release artifact:** annotated `v1.2.1` or `v1.3.0` tag on `main` (planning-phase decision — `__all__` delta is additive, so SemVer-minor is defensible; patch is also defensible since the Protocol is documentation). Milestone-close ceremony follows.

**UI hint:** no

## Cross-Repo Coordination

| Phase | Plan | Repo | Notes |
|-------|------|------|-------|
| 7 | 07-04 | projekt-forge | pin bump `@v1.2.0` + UAT `tools/list` diff (live MCP verification against assist-01) |
| 07.1 | 3/5 | In Progress|  |
| 07.1 | 07.1-04 | projekt-forge | Claude Code MCP registration + live deployment UAT of PROV-02 `_meta` via real MCP client (no monkey-patches) |
| 8 | 08-02 | projekt-forge | SQLAlchemy adapter + Alembic revision + isinstance check — **primary cross-repo deliverable** (mirrors Phase 6-04 pattern); path: `/Users/cnoellert/Documents/GitHub/projekt-forge/` |
| 8 | 08-03 | projekt-forge | pin bump + UAT DB-write verification |

Both cross-repo moments should be flagged as waves in their respective plans so phase-planning doesn't re-discover the coordination cost.

## Locked Non-Goals (carried from v1.1 + added in v1.2)

From v1.1:
- **No `LLMRouter` hot-reload** — built once at consumer startup, restart to pick up config changes
- **No shared-path JSONL writers across processes** — `fcntl.LOCK_EX` serializes writes, `_counters` is per-process state; two processes on the same file duplicate-promote
- **No LLM config reload without restart** — ditto

New in v1.2 (from REQUIREMENTS.md §"Out of Scope"):
- **No full-text search / tsvector on `raw_code`** — JSONL `grep` is good enough for v1.2
- **No time-series rollups / materialized views** — v1.3 dashboard concern
- **No realtime callback streaming (WebSocket/SSE)** — local-first, consumers subscribe to their own DB's NOTIFY/LISTEN if needed
- **No built-in Alembic migrations in forge-bridge** — Protocol-only, all DDL in projekt-forge
- **No pluggable-backends registry** — one consumer today, YAGNI
- **No cross-process promotion-counter sync** — v1.1 non-goal carried forward
- **No code-signing / cryptographic provenance** — `code_hash` is integrity, not signature
- **No placeholder sidecars for non-synthesized tools** — `_source` tag already distinguishes builtins; keep the "sidecar == synthesis artifact" contract
- **No `_meta` provenance via `annotations`** — MCP spec reserves `annotations` for safety hints (PITFALL P-02.1)
- **No consumer-facing `redact_fn` customization hook** — ship sane default in v1.2, reconsider in v1.3
- **`ExecutionRecord` stays frozen at v1.1.0 shape** — any field addition requires minor bump + coordinated projekt-forge migration review (P-03.7, P-03.9)

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Tool Parity & LLM Router | v1.0 | 7/7 | Complete | 2026-04-15 |
| 2. MCP Server Rebuild | v1.0 | 3/3 | Complete | 2026-04-15 |
| 3. Learning Pipeline | v1.0 | 3/3 | Complete | 2026-04-15 |
| 4. API Surface Hardening | v1.1 | 4/4 | Complete | 2026-04-15 |
| 5. Import Rewiring | v1.1 | 5/5 | Complete | 2026-04-18 |
| 6. Learning Pipeline Integration | v1.1 | 4/4 | Complete | 2026-04-18 |
| 7. Tool Provenance in MCP Annotations | v1.2 | 3/4 | In progress | - |
| 07.1. startup_bridge hotfix + deployment UAT | v1.2 | 0/5 | Planned | - |
| 8. SQL Persistence Protocol | v1.2 | 0/~3 | Not started | - |
