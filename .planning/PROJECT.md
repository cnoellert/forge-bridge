# forge-bridge: Canonical Package & Learning Pipeline

## What This Is

forge-bridge is protocol-agnostic middleware for post-production pipelines — a communication bus with a canonical vocabulary that any endpoint (Flame, Maya, editorial systems, LLM agents) can connect to. As of v1.0, it ships as a standalone pip-installable package with full Flame tool parity (matching projekt-forge), an LLM-powered learning pipeline that auto-promotes repeated operations into reusable MCP tools, and a pluggable MCP server that downstream consumers can extend.

## Current State

**Shipped:** v1.3.0 (2026-04-22) — `v1.2 Observability & Provenance` milestone complete. Synthesized MCP tools now carry canonical provenance in `Tool._meta` (`origin`, `code_hash`, `synthesized_at`, `version`, `observation_count`) via `.sidecar.json` envelopes with consumer-tag sanitization + size budgets. The `StoragePersistence` `@runtime_checkable` Protocol ships on the bridge (1 method, documentation-only — no DDL on bridge side); projekt-forge consumes it via a sync SQLAlchemy adapter with idempotent `ON CONFLICT DO NOTHING` inserts + Alembic revision 005 + `isinstance` gate at registration. Three annotated tags this milestone (`v1.2.0` = Phase 7, `v1.2.1` = Phase 07.1 hotfix, `v1.3.0` = Phase 8) on origin with wheel + sdist assets. End-to-end UAT verified: real `bridge.execute()` writes land in projekt-forge's `execution_log` PG table. See `.planning/milestones/v1.2-ROADMAP.md` for the full archive.

**In progress (v1.3 "Artist Console"):** Phase 9 "Read API Foundation" complete (2026-04-23); Phase 10 "Web UI" shipped then remediated — initial Phase 10 execution closed automated gates but FAILED the D-36 non-developer dogfood UAT ("nearly impossible to understand") and surfaced a shell-duplication render bug on nav click. **Phase 10.1 "Artist-UX Gap Closure" (2026-04-24)** remediated all six scoped items: `shell.html` nav-swap fix, explicit Status chip column (`active`/`loaded` — quarantined deferred to Phase 11/v1.4), artist-facing column headers with demoted telemetry, chip caption for discoverability, Playwright nav-swap + chip-click regression tests, and the re-run D-36 dogfood UAT (PASS with two honest-recorded deviations around fresh-operator identity + partial-understanding read). Gap-closure-of-gap-closure Plan 10.1-06 added when the pre-UAT smoke caught an independent chip-click shell-dup bug (same D-39 invariant class, different code path). Three follow-ups persisted to `10.1-HUMAN-UAT.md` for Phase 11 or a dedicated micro-pass: truly-fresh-operator re-UAT, default-sort affordance legibility on the `Created` column, and Firefox/Safari parity smoke. Full suite: 481/481.

**Codebase:** 21,826 LOC (forge_bridge + tests), 289 tests passing, 263 commits across 7 phases. Public API surface: 16 symbols in `forge_bridge.__all__`.

## Current Milestone: v1.3 Artist Console

**Goal:** Make forge-bridge legible to its operator — ship an artist-first Web UI + CLI console that surfaces the synthesis manifest, execution history, provenance, and live tool state, backed by a canonical MCP resource that any consumer can read.

**Target features:**
- Console Web UI — artist-first dashboard (LOGIK-PROJEKT dark + amber, web-adapted) served on a new port by the MCP server process; views for tools, execs, manifest, health, per-tool drilldown
- Console CLI companion — `forge-bridge console <subcommand>` mirrors the Web UI surface for scripting / SSH workflows
- Structured query console — primary interaction mode inside the Web UI; fast, deterministic, no LLM in the hot path
- LLM chat layered on the console — second surface over the same read API using the existing `LLMRouter`
- Synthesis manifest as MCP resource — one canonical manifest owned by the bridge, exposed at `forge://manifest/synthesis` (for LLM agents) and via the console read API (for the Web UI and CLI); satisfies both DF-02 and EXT-01 through the same artifact
- Shared read-side API powering Web UI + CLI + chat, reading JSONL (canonical, per STORE-06) + live bridge state; optional SQL read-adapter mirrors the StoragePersistence shape

**Key context:**
- Read-only milestone; no quarantine/promote/kill in UI (admin is a follow-on once auth is in scope)
- Serving model: new port (e.g., `:9996`) inside the MCP server process; `:9999` stays Flame's exec endpoint, `:9998` stays WS
- Design contract for the Web UI is owned by `/gsd-ui-phase` for its phase — expected palette inherits `#242424` base + `#cc9c00` amber from LOGIK-PROJEKT
- Minor version bump (grows `__all__` for new console entrypoints + manifest API) → next tag expected **v1.4.0**
- Phase numbering continues from v1.2 — v1.3 starts at **Phase 9**

**Locked non-goals:**
- No Maya/editorial adapters for the manifest (Flame remains the only producer this milestone)
- No auth in the console (localhost-bound, same posture as `:9999`)
- No admin/mutation actions in the UI
- Carried forward: no `LLMRouter` hot-reload, no shared-path JSONL writers

**Open (roadmapper to decide scope):** real-time streaming (SSE/WebSocket push) vs poll-only; multi-project view in the console.

## Core Value

Make forge-bridge the single canonical package (`pip install forge-bridge`) that ships independently with full Flame tool parity, an LLM-powered learning pipeline, and a pluggable MCP server — so projekt-forge can consume it rather than duplicate it.

## Requirements

### Validated

- ✓ HTTP bridge running inside Flame on port 9999, accepting Python code via POST /exec — existing
- ✓ MCP server exposing Flame tools (project, timeline, batch, publish, utility) to LLM agents — existing
- ✓ Canonical vocabulary layer with entities and traits — existing
- ✓ WebSocket server with wire protocol, connection management, and event-driven pub/sub — existing
- ✓ PostgreSQL persistence for entities, relationships, events, and registry — existing
- ✓ Async/sync client pair for connecting to forge-bridge server — existing
- ✓ Flame endpoint that syncs Flame segments to forge-bridge shots bidirectionally — existing
- ✓ Registry system for roles and relationship types with orphan protection — existing
- ✓ Flame tools updated to parity with projekt-forge (reconform, switch_grade, expanded timeline/batch/publish) — v1.0
- ✓ Pydantic models for tool input validation — v1.0
- ✓ LLM router promoted to forge_bridge/llm/ with async API, configurable system prompt, optional deps — v1.0
- ✓ LLM router health check exposed as MCP resource (forge://llm/health) — v1.0
- ✓ MCP server rebuilt with flame_*/forge_* namespace, synthesized tool registration, pluggable tool API — v1.0
- ✓ Pluggable tool registration API (register_tools()) for downstream consumers — v1.0
- ✓ Learning pipeline: execution log with JSONL persistence, replay on startup, intent tracking — v1.0
- ✓ Learning pipeline: skill synthesizer targeting Python MCP tools, using LLM router as backend — v1.0
- ✓ Learning pipeline: registry watcher for dynamic tool registration — v1.0
- ✓ Learning pipeline: probation system for synthesized tools (success/failure tracking, quarantine) — v1.0
- ✓ Learning pipeline wired into bridge.py as optional hook — v1.0
- ✓ Public API surface hardened: 11-name `__all__` barrel, injectable `LLMRouter`, public `startup_bridge`/`shutdown_bridge`, `register_tools()` post-run guard, `pyproject.toml` 1.0.0, PKG-03 grep gate clean — v1.1 (Phase 4)
- ✓ projekt-forge rewired to consume forge-bridge as a pip dependency with site-packages resolution enforced (RWR-01..04) — v1.1 (Phase 5)
- ✓ Learning pipeline integration in projekt-forge: storage callback + `pre_synthesis_hook` wired through `init_learning_pipeline`; `LLMRouter` built from `forge_config.yaml`; per-project `ExecutionLog` path; `forge_bridge` public surface grew to 15 symbols; annotated `v1.1.0` tag on origin (LRN-01..04) — v1.1.0 (Phase 6)
- ✓ Tool provenance in MCP annotations: `.sidecar.json` envelope write-path with watcher preferring sidecar over legacy `.tags.json`; canonical `_meta` fields (`origin`, `code_hash`, `synthesized_at`, `version`, `observation_count`) under `forge-bridge/*` namespace; `_sanitize_tag()` boundary strips control chars + rejects injection markers + 64-char/16-tag/4KB budgets; explicit `annotations.readOnlyHint=False` on every synth tool (PROV-01..06) — v1.2.0 (Phase 7)
- ✓ `startup_bridge` graceful degradation hotfix: MCP server boots cleanly when the standalone WS server on `:9998` is unreachable (honors existing docstring contract); re-UAT of PROV-02 via real MCP client session instead of the Phase 7-04 monkey-patched harness — v1.2.1 (Phase 07.1)
- ✓ `StoragePersistence` Protocol: `@runtime_checkable typing.Protocol` with single `persist(record)` method; canonical 4-column schema (`code_hash`, `timestamp`, `raw_code`, `intent`) documented in module docstring; barrel re-export grows `__all__` 15→16; ships NO DDL on bridge — schema ownership stays with consumers (STORE-01..04) — v1.3.0 (Phase 8)
- ✓ Cross-repo SQLAlchemy adapter: projekt-forge's `_persist_execution` stub replaced with real sync adapter using `pg_insert(...).on_conflict_do_nothing(index_elements=["code_hash","timestamp"])` for idempotency; Alembic revision `005_execution_log.py`; `isinstance(_persist_execution, StoragePersistence)` startup-time sanity gate; credential-leak prevention (logs only `type(exc).__name__`, never `str(exc)`) (STORE-05) — v1.3.0 (Phase 8)
- ✓ No-retry invariant documented end-to-end: callback failures log WARNING once and return, durability comes from JSONL + optional backfill (STORE-06) — v1.3.0 (Phase 8)
- ✓ LRN-05 gap closure: `forge_bridge.bridge.set_execution_callback()` hook was defined in Phase 6 but never installed; projekt-forge now installs `_forward_bridge_exec_to_log` in `init_learning_pipeline` — completing the `bridge.execute() → ExecutionLog.record() → _persist_execution → PG INSERT` chain. Discovered during Phase 8 live UAT — v1.3.0 (Phase 8 deviation)

### Active

- _v1.3 Artist Console requirements pending in `.planning/REQUIREMENTS.md` (roadmap assigns to Phase 9+)._

### Out of Scope

- Forge-specific tools (catalog, orchestrate, scan, seed) — belong in projekt-forge
- Forge-specific CLI, config, database (users/roles/invites), scanner, seeder — belong in projekt-forge
- Authentication — deferred, local-only for now
- Maya endpoint — future work
- Cloud/network scaling — local-first design, swappable later

## Context

- **v1.3.0 shipped (2026-04-22):** 21,826 LOC Python, 289 tests passing, 263 commits across 7 phases. Public API: 16 symbols in `forge_bridge.__all__`.
- **Observability is live.** Every synthesized MCP tool carries provenance in `Tool._meta` under `forge-bridge/*`; every `bridge.execute()` call threads through to `ExecutionLog.record()` (LRN-05) then to projekt-forge's `execution_log` PG table via the StoragePersistence Protocol path. JSONL remains source of truth; SQL is the log-authoritative mirror.
- **Cross-repo pin discipline proven.** Three release ceremonies this milestone followed the same pattern: forge-bridge tag + push → wheel + sdist → GitHub Release → projekt-forge pin bump → editable-shadow remediation (`pip uninstall -y forge-bridge && pip install -e .`) → UAT. The Option A pattern from Phase 07.1 is now the locked precedent for all future releases.
- **FlameSavant learning pipeline** successfully ported from JavaScript to Python (Phase 3) with AST normalization, manifest-based file validation, safety blocklist.
- **Live-tested end-to-end** throughout the milestone: Flame 2026.2.1 + Ollama `qwen2.5-coder:32b` on assist-01 → JSONL log → threshold promotion → synthesis → validated MCP tool with provenance metadata → SQL mirror row in `execution_log`.
- **Runtime topology verified during Phase 8 UAT:** the projekt-forge admin DB lives at `forge_bridge` (not `forge_admin` as the original CONTEXT.md assumed); `FORGE_DB_URL` carries async `+asyncpg` driver prefix, so sync SQLAlchemy queries must strip the driver suffix before `create_engine()`.

## Constraints

- **Backward compatibility**: Existing Flame hook and MCP server are deployed and working — don't break them during restructuring
- **Standalone independence**: forge-bridge must work without projekt-forge. No imports from forge-specific modules.
- **Optional dependencies**: LLM packages (openai, anthropic) must be optional extras, not hard requirements
- **Flame runtime**: flame_hooks/ code must use only Python stdlib (runs inside Flame's interpreter)
- **Python 3.10+**: Minimum version, as specified in pyproject.toml

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Phases 1-3 only in this project | Phases 4-5 require changes in projekt-forge repo | ✓ Shipped v1.0 |
| Port FlameSavant learning pipeline from JS to Python | Same concepts, different language — Python matches forge-bridge's ecosystem | ✓ Complete (Phase 3) |
| LLM router in forge_bridge/llm/ | Shared infrastructure for synthesizer and any tool needing generation | ✓ Complete (Phase 1) |
| Optional deps via pyproject.toml extras | Users who don't need LLM features shouldn't install openai/anthropic | ✓ Complete (Phase 1) |
| Synthesizer uses LLM router (not direct API calls) | Single point of control for model selection, sensitivity routing, cost management | ✓ Complete (Phase 3) |
| Namespace-enforcing registry with source tagging | Prevents tool name collisions, enables provenance tracking | ✓ Complete (Phase 2) |
| Manifest-based file validation in watcher | Prevents arbitrary code execution from rogue files in synthesized dir | ✓ Complete (Phase 3, code review fix) |
| Synthesized tools must use bridge.execute(), never import flame | Tools run in MCP server process, not inside Flame — discovered during live testing | ✓ Complete (Phase 3, live test fix) |
| Inject `LLMRouter` config via constructor kwargs with arg→env→default precedence | Downstream consumers (projekt-forge) need deterministic config without env-var side effects | ✓ Complete (Phase 4) |
| `register_tools()` post-run guard + public `startup_bridge`/`shutdown_bridge` | Clear lifecycle contract for pluggable MCP consumers; prevents silent no-op registrations | ✓ Complete (Phase 4) |
| Clean break on API renames (no aliases, no `_module_level_synthesize`) | Pre-1.0 — no external consumers yet, aliases are dead weight | ✓ Complete (Phase 4) |
| `ExecutionLog.set_storage_callback()` is per-instance with sync/async detected at registration; failure isolated, JSONL stays source-of-truth | Consumers can mirror execution records into their own storage without risking the canonical JSONL append | ✓ Complete (Phase 6, LRN-02) |
| `SkillSynthesizer.pre_synthesis_hook` is additive-only; base `SYNTH_SYSTEM`/`SYNTH_PROMPT` never replaced; hook failure falls back to empty context | Consumer-supplied prompt-injection surface cannot override forge-bridge's safety rules; failure mode keeps synthesis running | ✓ Complete (Phase 6, LRN-04) |
| SC #3 scope-reduced to "log-stream mirror" for v1.1 (SQL persistence deferred to EXT-03 in v1.1.x) | `_persist_execution` is a logger-only stub; the `ExecutionRecord` contract is stable so EXT-03 swaps the callback body only | Documented (Phase 6, deferred EXT-03) |
| Minor-version bump ceremony: barrel re-export → pyproject.toml → regression test → annotated tag on main → push | Consumer (projekt-forge) pins via `git+...@vX.Y.Z`; tag identity locked at release time to prevent tag-drift attacks | ✓ Pattern established (Phase 6, reusable v1.2+) |
| `LLMRouter` is built once at consumer startup from config and injected into `SkillSynthesizer`; no hot-reload — restart to pick up config changes | Keeps the wiring simple and avoids stale-client / dangling-session edge cases from swapping routers under live synthesizers. If runtime config reload ever becomes a requirement, design it explicitly. | ✓ Locked non-goal (Phase 6 scope boundary) |
| Multiple `ExecutionLog` instances pointed at the **same** JSONL path across processes is NOT supported | `fcntl.LOCK_EX` serializes the writes, but `_counters` / `_promoted` are in-process state — each process would independently cross the promotion threshold, producing duplicate promotions. Consumer owns log-path strategy (SC #1 verified path isolation, not shared-path concurrency). If shared-path multi-writer is ever needed, design it explicitly (shared counter store, not per-process dict). | ✓ Locked non-goal (Phase 6 scope boundary) |
| Provenance lives in `Tool._meta` under `forge-bridge/*` namespace, NOT `annotations` | MCP spec reserves `annotations` for safety hints (readOnlyHint, destructiveHint); mixing provenance there pollutes a safety-critical surface. Pitfall P-02.1 from Phase 7 research. | ✓ Complete (Phase 7, PROV-02) |
| Consumer-supplied tags pass through `_sanitize_tag()` boundary at the read path (not the write path) | Consumer may produce unvalidated tags (legacy files, external tools); sanitizing at read-time means forge-bridge controls the trust boundary regardless of who wrote the sidecar. Size budgets: 64 chars/tag, 16 tags/tool, 4 KB/`_meta`. | ✓ Complete (Phase 7, PROV-03) |
| Every synthesized tool gets `annotations.readOnlyHint=False` at registration | Synthesized tools call `bridge.execute()` to run arbitrary Python in Flame's process — that is categorically NOT read-only. Without explicit override, MCP clients may auto-approve synth tools under their read-only policy. | ✓ Complete (Phase 7, PROV-04) |
| `startup_bridge` degrades gracefully when the standalone WS server on :9998 is unreachable — don't crash MCP server boot | Existing docstring + warning-log contract was written before Phase 7 made WS connectivity a hot path; v1.2.0 crashed here. Honoring the documented contract is the fix — MCP server still boots and flame_* tools still work if Flame is up. | ✓ Complete (Phase 07.1 hotfix, SC1) |
| Cross-repo re-pin uses Option A shadow remediation: `pip uninstall -y forge-bridge && pip install -e .` | Editable install can shadow the pinned tag (`direct_url.json` keeps the source-tree path cached); uninstall-first forces pip to re-resolve from the pinned git reference. Locked pattern from Phase 07.1-03. | ✓ Locked pattern (Phase 07.1, reusable for all cross-repo re-pins) |
| `StoragePersistence` Protocol exposes exactly one method (`persist`), not the originally-scoped 3-method API (`persist`, `persist_batch`, `shutdown`) | YAGNI — the single consumer (projekt-forge) has no use case for batch or shutdown today; adding them would freeze contracts with no grounding. Narrow Protocols are easier to implement correctly; wider Protocols are harder to satisfy. D-02 in Phase 8 CONTEXT. Future `BatchingStoragePersistence` sub-Protocol possible if backfill demand emerges. | ✓ Complete (Phase 8, D-02, STORE-01) |
| `@runtime_checkable` is REQUIRED for `StoragePersistence` — not optional | Consumers need `isinstance()` at registration-time to fail loudly if the adapter drifts from the Protocol (e.g., forge-bridge adds a required method in a future minor bump). D-03 in Phase 8. | ✓ Complete (Phase 8, D-03, D-11) |
| Canonical schema lives in the Protocol's module docstring, not in shipped DDL | Bridge is protocol-only — schema ownership stays with the consumer (projekt-forge has the Alembic migration). Docstring becomes the normative spec; deviating implementations are still Protocol-compliant but document their delta. D-04 in Phase 8. | ✓ Complete (Phase 8, D-04, STORE-04) |
| Consistency model is log-authoritative + eventual + best-effort — JSONL is source of truth, SQL is a mirror | DB outages log WARNING once and return (no retry in callback, D-06). If the SQL row is missing, the JSONL record is canonical; a future backfill job can reconcile. D-05/D-06 in Phase 8. | ✓ Complete (Phase 8, D-05, D-06, STORE-06) |
| Sync SQLAlchemy callback (not async), using `sessionmaker.begin()` context manager per call | ExecutionLog.record() can fire from Flame's Qt main thread where no asyncio event loop exists. Async would require `asyncio.run()` in the callback path, which is fragile across thread boundaries. Sync session-per-call is slower but correct. D-07 in Phase 8. | ✓ Complete (Phase 8, D-07, STORE-05) |
| Idempotency via `on_conflict_do_nothing(index_elements=["code_hash","timestamp"])`, not app-level dedup | Multi-process safety (SC #1 path isolation is a sanity guard, not a concurrency contract — production is single-writer). PG-level constraint is atomic and matches the JSONL dedup shape. D-09 in Phase 8. | ✓ Complete (Phase 8, D-09) |
| Credential leak prevention: log only `type(exc).__name__`, NEVER `str(exc)` for DB errors | SQLAlchemy `OperationalError.__str__()` walks the exception chain and includes the inner `asyncpg.InvalidPasswordError`-style message, which carries the DB URL with embedded credentials. Security-critical — a lazy log line leaks secrets to `.forge-bridge/*.log` and anywhere log aggregation ships. | ✓ Complete (Phase 8, 08-02 deviation, cf221fe review fix) |
| Runtime adapter binding: attach `_persist_execution.persist = _persist_execution` to make a plain function satisfy `@runtime_checkable` Protocol | Python's `@runtime_checkable` checks for a named method attribute on the candidate object. Plain functions don't have a `.persist` attribute until we synthesize one — this pattern is how a callable satisfies a method-based Protocol without wrapping it in a class. Discovered during 08-02 execution. | ✓ Surprise (Phase 8, 08-02) |
| Install `forge_bridge.bridge.set_execution_callback()` hook in projekt-forge's `init_learning_pipeline` — the Phase 6 hook was never wired | Phase 6 defined `set_execution_callback` as a public API but no production code called it. `bridge.execute() → ExecutionLog.record()` was a dead write path for three phases. Unit tests masked it by calling `log.record()` directly. Discovered during Phase 8 live UAT when real MCP calls produced zero rows. LRN-05. | ✓ Complete (Phase 8 deviation, projekt-forge cf221fe) |
| UAT must exercise the full production call path end-to-end, not just unit-level pieces | Unit tests that hit individual seams mask missing wiring between them. Phase 8 UAT criterion ("real synthesis → row") surfaced LRN-05 only because we refused to fake the bridge path. Lesson: for observability chains that span multiple phases, the UAT query must come from a live production code path — not a harness. | ✓ Lesson (Phase 8 UAT) |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-23 — Phase 9 "Read API Foundation" complete; Phase 10 "Web UI" next*
