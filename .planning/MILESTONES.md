# Milestones

## v1.3 Artist Console (Shipped: 2026-04-25)

**Phases completed:** 4 phases (9, 10, 10.1, 11), 20 plans
**Phase superseded:** Phase 12 (LLM Chat) → v1.4 FB-D (velocity gate decided 2026-04-23)
**Release tag:** v1.3.1 (milestone close on top of v1.3.0 from Phase 8)
**Requirements:** 33/37 shipped + 4/37 superseded → v1.4 FB-D = 37/37 resolved
**Stats:** 148 commits, 202 files changed, +43,765 / −1,059 lines, ~30,378 LOC at close

**Key accomplishments:**

- **Read API foundation (Phase 9 → uvicorn task on `:9996`).** `ConsoleReadAPI` is the sole read path for all surfaces — Web UI, CLI, MCP resources, future chat all consume the byte-identical `{data, meta}` envelope. `ManifestService` singleton injected into the watcher (write path) and console router (read path); instance-identity gate (API-04) ensures `_lifespan` owns the canonical `ExecutionLog` and `ManifestService`. Console runs as a separate uvicorn asyncio task inside `_lifespan` — NOT via `FastMCP.custom_route` (which only works in `--http` mode and would break stdio default). MCP resources + tool fallback shim ship in the same plan (P-03 prevention for Cursor / Gemini CLI).
- **Web UI (Phase 10 → Jinja2 + htmx + Alpine.js).** Five views (tools / execs / manifest / health / chat-nav) served from Jinja2 templates with htmx partial refreshes and Alpine.js state — zero JS build step, vendored htmx + Alpine with SRI. Persistent health header strip on every view. Structured query console as primary interaction (deterministic, no LLM in hot path). LOGIK-PROJEKT amber-on-dark palette translated to web idioms via `UI-SPEC.md` design contract.
- **Artist-UX gap closure (Phase 10.1 → INSERTED 2026-04-23).** Phase 10's D-36 fresh-operator dogfood UAT FAILED qualitatively ("nearly impossible to understand") and surfaced an `hx-boost` shell-duplication bug. Six-plan remediation: nav-swap fix, explicit Status chip column, artist-facing column headers with demoted developer telemetry, chip discoverability, in-browser Playwright nav-swap regression test, gap-closure-of-gap-closure for an independent chip-click shell-dup bug. Re-UAT PASSED 2026-04-24 with two honest-recorded deviations carried to a HUMAN-UAT follow-up file.
- **CLI companion (Phase 11 → Typer + Rich + sync httpx).** Five subcommands (`tools`, `execs`, `manifest`, `health`, `doctor`) consume the `:9996` API via sync `httpx` (Typer 0.24.1 silently drops `async def` — verified). Filter-flag grammar mirrors Phase 10 Web UI tokens 1:1 so artists who learn one dialect use both. `--json` short-circuits Rich entirely (P-01 stdout purity). Locked exit-code taxonomy: `0` success, `1` server error envelope, `2` server unreachable. `doctor` runs an expanded check matrix (JSONL parseability, sidecar dirs, port reachability, disk space) with CI-gating exit codes. D-08 soft-UAT PASS — developer-as-operator with "can I decipher" criterion is the right tool for technical surfaces (vs. fresh-operator for artist surfaces).
- **Phase 12 supersession (decided 2026-04-23).** Mid-milestone, projekt-forge v1.5 declared FB-A..FB-D as required deps. FB-D ("Chat Endpoint") naturally absorbs Phase 12's chat scope while adding the agentic tool-call loop that makes the chat surface useful in the first place. CHAT-01..04 carry forward to v1.4 FB-D — explicit decision, not a silent drop.

**Verification & regression:**
- Phase 9 VERIFICATION: PASSED 2026-04-22 (5/5 must-haves; 379 tests green)
- Phase 10 VERIFICATION: plans shipped 2026-04-23; D-36 UAT initially FAILED → resolved by 10.1
- Phase 10.1 VERIFICATION: PASSED 2026-04-24 (D-36 re-UAT PASS with two honest-recorded deviations)
- Phase 11 VERIFICATION: PASSED 2026-04-25 (13/13 must-haves; 111 CLI tests + 592 full-suite green; 91% CLI coverage; D-08 soft UAT PASS)

**Known deferred items at close** (carry forward to v1.4 polish or v1.5):
- Truly-fresh-operator re-UAT for Web UI (10.1-HUMAN-UAT)
- Default-sort affordance legibility on Web UI `Created` column — CLI side already ships `Created ▼` glyph (10.1-HUMAN-UAT)
- Non-Chromium browser parity smoke (10.1-HUMAN-UAT)
- `manifest` and `tools` CLI views render visually indistinguishable (Phase 11 D-08 UAT)
- W-01 server-side `/api/v1/execs?tool=...` filter (client-side workaround shipped in Phase 11)
- Quarantined-tool surfacing in UI/CLI → v1.5 admin/auth milestone

**Lessons:**
- Hard fresh-operator UAT gate is the right tool for artist-facing surfaces (Phase 10 retrospectively taught us this when the D-36 UAT caught a UX failure class unit tests missed). Soft developer-as-operator gate is the right tool for technical CLI/SSH surfaces (Phase 11 D-08 confirmed). Match the gate to the user population.
- ConsoleReadAPI as sole read path validated three times in one milestone (Web UI, CLI, MCP resources). Single read layer + multiple presentations is a pattern that earned its discipline.
- Apply UX lessons to the surface that ships *next* — Phase 11's CLI shipped `Created ▼` default-sort affordance closing Phase 10.1's HUMAN-UAT item #2 on the CLI surface immediately, even though the Web UI fix remains a deferred follow-up. Don't wait to retrofit; bake the lesson into the next surface.
- Bookkeeping drift compounds — the Phase 9 ROADMAP top-line checkbox stayed unchecked from 2026-04-22 → 2026-04-25 because Phases 10, 10.1, 11 all shipped on top of Phase 9 in the same week and the `[x]` flip got skipped four times in a row. Reconciled at v1.3 close. Mitigation: GSD `roadmap update-plan-progress` already handles per-plan; need an analogous "phase complete" sweep that flips the top-line bullet too.

---

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
