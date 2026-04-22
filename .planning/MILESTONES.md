# Milestones

## v1.2 Observability & Provenance (Shipped: 2026-04-22)

**Phases completed:** 3 phases (7, 07.1, 8), 12 plans, 17 tasks
**Release tags:** v1.2.0 (Phase 7) · v1.2.1 (Phase 07.1 hotfix) · v1.3.0 (Phase 8)
**Requirements:** 12/12 Done (PROV-01..06, STORE-01..06)

**Key accomplishments:**

- **Provenance in MCP annotations (Phase 7 → v1.2.0).** Synthesized tools now emit `.sidecar.json` with `{tags, meta, schema_version: 1}` envelope; watcher reads sidecar preferentially with legacy `.tags.json` fallback during grace window; MCP clients see canonical `Tool._meta` fields under `forge-bridge/*` namespace (`origin`, `code_hash`, `synthesized_at`, `version`, `observation_count`); `_sanitize_tag()` boundary strips control chars, rejects injection markers, enforces 64-char / 16-tag / 4KB budgets; every synth tool gets explicit `annotations.readOnlyHint=False` preventing MCP auto-approve of synth tools that call `bridge.execute()`.
- **startup_bridge graceful degradation (Phase 07.1 → v1.2.1 hotfix).** MCP server boots cleanly when standalone forge-bridge WebSocket on `:9998` is unreachable (honors existing docstring contract); re-UAT of PROV-02 via real MCP client session replaces the monkey-patched Phase 7-04 harness; `pip install @v1.2.1` resolves cleanly for consumers; projekt-forge re-pinned `@v1.2.0 → @v1.2.1` with editable-shadow remediation (Option A).
- **StoragePersistence Protocol (Phase 8 → v1.3.0).** `@runtime_checkable` Protocol with a single `persist` method (D-02 narrowed from original 3-method Spec); canonical 4-column schema in module docstring (`code_hash`, `timestamp`, `raw_code`, `intent`) — no `promoted` column per D-08; barrel re-export grows `__all__` 15 → 16; `ExecutionLog.set_storage_callback()` signature unchanged so consumers pass `backend.persist` as the existing callable; ships NO DDL on the bridge side — schema ownership stays with consumers.
- **Cross-repo SQLAlchemy adapter (Phase 8 → projekt-forge).** `_persist_execution` stub replaced with real sync SQLAlchemy backend using `pg_insert(...).on_conflict_do_nothing(index_elements=["code_hash","timestamp"])` for idempotent writes; new Alembic revision `005_execution_log.py` chaining 004 → 005; `isinstance(_persist_execution, StoragePersistence)` startup-time sanity gate (D-11); bound-parameter SQL-injection safety; credential-leak prevention (logs only `type(exc).__name__`, never `str(exc)` which would include URL via SQLAlchemy exception chain).
- **LRN-05 gap closure (Phase 8 UAT deviation).** `forge_bridge.bridge.set_execution_callback()` was defined in Phase 6 as the hook for learning-pipeline observation but never installed by any production caller — meaning `bridge.execute()` skipped the observation path unconditionally. Discovered during Phase 8 live UAT when a real MCP call produced zero rows. Fixed in projekt-forge `cf221fe` by installing `_forward_bridge_exec_to_log` in `init_learning_pipeline`; 4 new tests cover install/forward/drop/reset. End-to-end chain now live: `bridge.execute() → callback → ExecutionLog.record() → _persist_execution → ON CONFLICT DO NOTHING INSERT → PG row`.

**Verification & regression:**
- Phase 7 VERIFICATION: passed
- Phase 07.1 VERIFICATION: passed
- Phase 8 VERIFICATION: passed 20/20 (one documented override on REQUIREMENTS.md STORE-01 wording — shipped 1-method Protocol satisfies the requirement's intent per D-02)
- Live UAT: real `bridge.execute()` produced new row in `execution_log` (code_hash `174d89e4…`, delta +1, zero DB-write WARNING lines)
- Test suites: forge-bridge 289 passed; projekt-forge 436 passed, 3 xfailed (baseline 422 + 14 net new, zero regressions)

**Lessons:**
- Unit tests that call `log.record()` directly mask missing upstream wiring — ensure UAT flexes the full production call path end-to-end. The Phase 6 → Phase 7 → Phase 8 chain had the observation hook defined but uninstalled for three phases before Phase 8's live UAT surfaced it.
- Cross-repo releases need explicit order-of-operations: forge-bridge tag + push → wheel + sdist build → GitHub Release → consumer pin bump → `pip uninstall before pip install -e .` (Option A shadow remediation) → migration apply → UAT. Each step has a specific gate; skipping one produces silent false positives.
- `@runtime_checkable` Protocols checking for a method attribute require plain functions to attach a self-referencing `.persist` attribute to satisfy `isinstance()` — surprise discovered during 08-02 execution.

---

## v1.0 Canonical Package & Learning Pipeline (Shipped: 2026-04-15)

**Phases completed:** 3 phases, 13 plans, 25 tasks

**Key accomplishments:**

- One-liner:
- Async LLM router in forge_bridge/llm/ with acomplete() coroutine, lazy optional-dep guards, full env-var configuration, and backwards-compatible shim at original path
- forge://llm/health MCP resource exposing local (Ollama) and cloud (Anthropic) backend availability via ahealth_check() on LLMRouter
- [Observation] Linter auto-corrected bridge import in publish.py
- One-liner:
- 13 new Flame MCP tools registered in active server (reconform, switch_grade, timeline disconnect/inspect/version/reconstruct/clone/replace/scan/assign, batch XML) plus LLM health resource wired
- One-liner:
- Namespace-enforcing MCP tool registry with source tagging via meta={'_source'} and frozenset prefix allowlist, with TDD-verified synth_ reservation for synthesis pipeline only
- All ~42 MCP tool registrations centralised in register_builtins() in registry.py; server.py reduced to lifecycle-only with zero direct mcp.tool() calls; forge_bridge.mcp exports register_tools and get_mcp as public API
- ExecutionLog with AST normalization stripping literals, JSONL append-only persistence, SHA-256 fingerprinting, configurable promotion threshold, and bridge.py callback hook
- 1. [Rule 1 - Bug] Fixed test for identical file skip -- content hash mismatch
- ProbationTracker wrapping synthesized tools with per-tool success/failure counters, threshold-based quarantine (file move + MCP removal), and watcher integration

---
