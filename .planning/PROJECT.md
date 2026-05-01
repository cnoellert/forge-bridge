# forge-bridge: Canonical Package & Learning Pipeline

## What This Is

forge-bridge is protocol-agnostic middleware for post-production pipelines — a communication bus with a canonical vocabulary that any endpoint (Flame, Maya, editorial systems, LLM agents) can connect to. As of v1.0, it ships as a standalone pip-installable package with full Flame tool parity (matching projekt-forge), an LLM-powered learning pipeline that auto-promotes repeated operations into reusable MCP tools, and a pluggable MCP server that downstream consumers can extend.

## Current State

**Shipped:** v1.4.1 (2026-04-30) — `v1.4.x Carry-Forward Debt` patch milestone complete. Closed nine carry-forward debt items surfaced during v1.4 close-out (`.planning/milestones/v1.4-MILESTONE-AUDIT.md`) across three phases: default cloud model flipped to `claude-sonnet-4-6` and `qwen3:32b` deferred to v1.5 with empirical evidence (Phase 17 — MODEL-01..02); `staged_client` migrated from `starlette.TestClient` to `httpx.AsyncClient + ASGITransport` and 22+ previously silently-skipped console tests now run against live Postgres (Phase 18 — HARNESS-01..03); WR-02 ref-collision guard, Phase 13 `from_status` `Optional[str]` type-contract fix, real cross-session atomicity assertion, and qwen2.5-coder `<|im_start|>` tail-token strip in `OllamaToolAdapter` (Phase 19 — POLISH-01..04). Audit `passed` with 7/7 cross-phase integration wires verified; public `__all__` byte-identical to v1.4 close (no API surface changes; internal tech-debt only). See `.planning/milestones/v1.4.x-ROADMAP.md` and `.planning/milestones/v1.4.x-MILESTONE-AUDIT.md`.

**Previously shipped:** v1.4.0 (2026-04-28) — Staged Ops Platform (FB-A..FB-D — staged_operation entity, MCP tools + HTTP routes + chat endpoint with agentic tool-call loop). Consumed by projekt-forge v1.5. See `.planning/milestones/v1.4-ROADMAP.md`.

**In progress:** v1.5 Legibility (opened 2026-04-30) — see Current Milestone below.

**Codebase at v1.4.1 close:** ~40,594 LOC (forge_bridge + tests; +556 over v1.4.0), 865 unit tests passing in default suite (19 skipped, 0 failed), 689 commits across 17 shipped phases (1, 2, 3, 4, 5, 6, 7, 07.1, 8, 9, 10, 10.1, 11, 13, 14, 15, 16, 16.1, 16.2, 17, 18, 19). Public API surface: 19 symbols in `forge_bridge.__all__` — byte-identical to v1.4.0 close. Carry-forward seeds for v1.5: `SEED-OPUS-4-7-TEMPERATURE-V1.5` (planted Phase 17), `SEED-DEFAULT-MODEL-BUMP-V1.4.x` (retargeted v1.4.x → v1.5), `SEED-CHAT-STREAMING-V1.4.x`, `SEED-AUTH-V1.5`.

## Current Milestone: v1.5 Legibility

**Goal:** Make forge-bridge usable by its first daily user — close the gap between what's shipped (19 phases, 5 user-facing surfaces, ~40k LOC) and what a person can sit down and actually use without re-deriving the deployment topology each time.

**Target features:**
- **Reality audit + canonical install** — walk a fresh install end-to-end, fix gaps as they surface, ship `docs/INSTALL.md`, refresh README install section, refresh CLAUDE.md ground-truth, pin `install-flame-hook.sh` default to `v1.4.1`.
- **Surface map + concept docs** — document the five user-facing surfaces (Web UI on `:9996/ui/`, CLI `forge-bridge`, `/api/v1/chat` HTTP, MCP server `python -m forge_bridge`, Flame hook on `:9999`) and forge-bridge's relationship to projekt-forge. Output: `docs/GETTING-STARTED.md` + rewritten README "What This Is".
- **Daily workflow recipes** — step-by-step guides for ~5–7 daily tasks: first-time setup, Claude Desktop / Claude Code wiring, watching tool synthesis happen, driving multi-step Flame automation via chat, approving/rejecting staged ops, inspecting auto-promoted tools in the manifest, basic failure diagnosis.
- **Diagnostics + recovery** — document common failure modes (Flame crash, Postgres restart, Ollama hang, qwen3 cold-start `LLMLoopBudgetExceeded`), recovery paths, polish `forge doctor` if needed. Output: `docs/TROUBLESHOOTING.md`.

**Key context:**
- Legibility, not features. No new external libraries. Public `forge_bridge.__all__` should stay at 19 unless something genuinely shifts.
- Forcing function: if the install doc doesn't work end-to-end on a clean machine, we don't ship it. Phase 20 will likely surface deployment gaps that get fixed in-flight.
- Internal codebase audit + workflow articulation — no external research phase.
- Done state: user can sit down, follow the docs, and use forge-bridge in daily VFX workflow.

**v1.5 ship blocker (post-Phase-20 truth, 2026-05-01):** Phase 20's reality audit confirmed that `docs/INSTALL.md` as prose is NOT shippable to artists — the procedure demands knowledge (Postgres `pg_hba.conf`, `password_encryption` history, two-process launch order, conda env lifecycle, env-var persistence) that the doc itself does not give. The architecture works (cross-host LLM via assist-01 Ollama validated end-to-end on flame-01 during the Phase 20 Track A walk); the install procedure does not. **Phase 20.1 (install.sh + systemd units `forge-bridge-server.service` + `forge-bridge.service` + `/etc/forge-bridge/forge-bridge.env` + INSTALL.md reshape) is the v1.5 ship gate.** No artist non-author UAT can pass against the current INSTALL.md; 20.1 is therefore the prerequisite to claiming v1.5 ships. Capture: `.planning/phases/20-reality-audit-canonical-install/20-PHASE-20.1-CANDIDATE.md`. Headline framing repeated in `20-HUMAN-UAT.md`. Phase 20 closed PASS-with-deviations under D-02.1 amendment (author-walk, no fully-non-author available); the 13 gap-log entries are 20.1's input requirements.

**Carry-forward seeds (deferred to v1.6+, NOT v1.5 scope):**

- **`SEED-OPUS-4-7-TEMPERATURE-V1.5`** (planted Phase 17, v1.4.1) — AnthropicAdapter unconditionally sends `temperature`, but `claude-opus-4-7` rejects it. Required before any future opus-4-7 default bump can be considered.
- **`SEED-DEFAULT-MODEL-BUMP-V1.4.x`** (retargeted v1.4.x → v1.5) — `_DEFAULT_LOCAL_MODEL` bump to `qwen3:32b` deferred with empirical evidence: cold-start `LLMLoopBudgetExceeded` driven by qwen3 thinking-mode token verbosity (400-525 tokens/turn). Trigger: widened salvage helper, qwen3 thinking-mode token-budget mitigation, or a tool-coordinator wall-clock fix.
- **`SEED-AUTH-V1.5`** (planted v1.4 FB-D) — caller-identity migration for chat rate limiting; sensitive-routing changes wait on auth.
- **`SEED-CHAT-STREAMING-V1.4.x`** — surface if/when artist feedback reports the trigger condition (spinner runs too long without progress feedback); was NOT reported in Phase 16.2 UAT, so deferred.
- All v1.5+ planted seeds (CHAT-CLOUD-CALLER, CHAT-PARTIAL-OUTPUT, CHAT-PERSIST-HISTORY, CHAT-TOOL-ALLOWLIST, CMA-MEMORY, CROSS-PROVIDER-FALLBACK, MESSAGE-PRUNING, PARALLEL-TOOL-EXEC, STAGED-CLOSURE, STAGED-REASON, TOOL-EXAMPLES).

<details>
<summary>Previous milestone: v1.4 Staged Ops Platform (shipped 2026-04-28)</summary>

Goal: Extend forge-bridge with the human-in-the-loop primitives projekt-forge v1.5 needs to become a thin Flame-side consumer — `staged_operation` entity with proposed→approved→executed lifecycle, MCP + HTTP surface for list/approve/reject, agentic `complete_with_tools()` on `LLMRouter`, and a chat endpoint that binds it all together. Target features FB-A..FB-D (preserved as canonical cross-repo aliases). Two decimal gap-closure phases (16.1, 16.2) inserted mid-milestone per the Phase 10/10.1 precedent. Full archive: `.planning/milestones/v1.4-ROADMAP.md`.

</details>

<details>
<summary>Previous milestone: v1.4.x Carry-Forward Debt (shipped 2026-04-30)</summary>

Goal: Pay down v1.4 carry-forward debt as a clean patch release. Ship a polished `v1.4.1` that projekt-forge v1.5 can pin against without test-harness or model-default surprises. Each requirement maps to a specific debt item surfaced during v1.4 close-out. 9/9 requirements closed across 3 phases (17, 18, 19). Audit `passed`; 7/7 cross-phase integration wires verified; public `__all__` byte-identical to v1.4 close. Full archive: `.planning/milestones/v1.4.x-ROADMAP.md`.

</details>

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
- ✓ Read API foundation: `ConsoleReadAPI` is the sole read path for all surfaces (Web UI, CLI, MCP resources); `ManifestService` singleton with watcher injection; instance-identity gate (API-04) enforced in `_lifespan`; uvicorn asyncio task on `:9996` co-resident with MCP server (NOT FastMCP `custom_route` — would break stdio); `forge://manifest/synthesis` MCP resource + `forge_manifest_read` tool fallback shim ship in same plan; graceful degradation when `:9996` unavailable (API-01..06, MFST-01..03,06, TOOLS-04, EXECS-04) — v1.3.1 (Phase 9)
- ✓ Web UI: artist-first dashboard at `http://localhost:9996/ui/` — five views (tools, execs, manifest, health, chat-nav), Jinja2 + vendored htmx + Alpine.js with SRI, zero JS build step, structured query console as primary interaction (no LLM in hot path), persistent health header strip, LOGIK-PROJEKT amber-on-dark palette via UI-SPEC.md design contract (CONSOLE-01..05, TOOLS-01,02, EXECS-01,02, MFST-04, HEALTH-01,04) — v1.3.1 (Phase 10 + 10.1 remediation)
- ✓ Artist-UX gap closure (INSERTED Phase 10.1): D-36 fresh-operator dogfood UAT failed Phase 10 → six-plan remediation shipped explicit Status chip column, artist-facing column headers with demoted developer telemetry, `hx-boost` shell-duplication fix, chip discoverability, in-browser Playwright nav-swap regression test, gap-closure-of-gap-closure for chip-click shell-dup; D-36 re-UAT PASSED — v1.3.1 (Phase 10.1)
- ✓ CLI companion: Typer + Rich + sync `httpx` consumer of `:9996` — five subcommands (`tools`, `execs`, `manifest`, `health`, `doctor`), filter-flag grammar mirrors Web UI 1:1, `--json` short-circuits Rich (P-01 stdout purity), locked exit codes (`0` ok / `1` server error / `2` unreachable), `doctor` expanded check matrix (JSONL parseability, sidecar dirs, port reachability, disk space) with CI-gating exit codes; D-08 soft UAT PASS (CLI-01..04, TOOLS-03, EXECS-03, MFST-05, HEALTH-02,03) — v1.3.1 (Phase 11)
- ✓ Phase 12 supersession (decided 2026-04-23, confirmed at v1.3 close): mid-milestone, projekt-forge v1.5 declared FB-A..FB-D as required deps; FB-D ("Chat Endpoint") absorbs Phase 12's chat scope while adding the agentic tool-call loop. CHAT-01..04 carry forward to v1.4 FB-D — explicit decision, not a silent drop
- ✓ FB-D / Bug D closure: `OllamaToolAdapter.send_turn()` now salvages text-shaped tool calls — when qwen2.5-coder emits `{"name": ..., "arguments": ...}` as JSON in `message.content` while leaving `message.tool_calls` empty, `_try_parse_text_tool_call` parses it and re-emits as a structured tool call. Closes the Phase 16.1 close-with-known-gap. Three independent layers of evidence: captured-fixture regression guard (`TestOllamaToolAdapterBugDFallback` — RED→GREEN flip), strengthened E2E (`_BUG_D_TERMINAL_JSON_RE` regex reject in `test_chat_canonical_uat_prompt_under_60s`), and live walkthrough on assist-01 (synthesized natural-language answer to canonical CHAT-04 prompt in 21–22s, agentic loop iterated). CHAT-04 fresh-operator UAT recorded `Outcome: PASS with deviations` per the Phase 10.1 / 16.1 D-14 precedent — v1.4 (Phase 16.2, completed 2026-04-28). v1.4 milestone close is now unblocked.
- ✓ Staged Operation entity + lifecycle (FB-A): `entity_type='staged_operation'` with `proposed → approved → executed/rejected/failed` state machine enforced in the data layer; illegal transitions raise `StagedOpLifecycleError`. Every transition emits a `DBEvent` row (audit replay queryable by `entity_id`). `parameters` JSONB preserved verbatim across status advancement; `result` JSONB null until terminal. Reversible Alembic migration `0003_staged_operation.py`. STAGED-01..04 closed live 2026-04-28 on dev Postgres `127.0.0.1:7533/forge_bridge` (29 passed, 4 by-design skips, 0 failed) — v1.4 (Phase 13)
- ✓ Staged Ops MCP + HTTP surface (FB-B): four MCP tools (`forge_list/get/approve/reject_staged`) + three HTTP routes (`GET /api/v1/staged?status=...`, `POST /api/v1/staged/{id}/approve`, `POST /api/v1/staged/{id}/reject`) + `forge://staged/pending` resource — all served from a single `ConsoleReadAPI` facade with byte-identity zero-divergence (D-19 + D-20 tests). Approval is bookkeeping only — proposer subscribes to approval events and executes against its own domain. STAGED-05..07 closed v1.4 (Phase 14)
- ✓ LLMRouter agentic loop (FB-C): `LLMRouter.complete_with_tools(prompt, tools, sensitive=...)` runs the full loop with provider-neutral coordinator + thin Anthropic + Ollama adapters; sensitive routing preserved verbatim from `acomplete()`. Hard caps (8 iterations, 120s wall-clock, 30s per-tool sub-budget) raise `LLMLoopBudgetExceeded` (added to `forge_bridge.__all__`, barrel grew 16→17). Repeat-call detection (3 identical invocations → synthetic error tool result), 8 KB result-size cap (`_TOOL_RESULT_MAX_BYTES`), `_sanitize_tool_result()` consolidated with Phase 7's `_sanitize_tag()` (single-source `INJECTION_MARKERS`), recursive-synthesis guard (`_in_tool_loop` ContextVar + `RecursiveToolLoopError`; synthesizer AST blocklist updated for `forge_bridge.llm` imports). LLMTOOL-01 closed retroactively by Phase 16.2 live UAT; LLMTOOL-02 closed live 2026-04-28 against `claude-sonnet-4-6` after surfacing + fixing two latent Anthropic SDK API-drift bugs (`disable_parallel_tool_use` moved into `tool_choice`; `additionalProperties: false` injected for strict tools). LLMTOOL-01..07 closed v1.4 (Phase 15)
- ✓ Chat endpoint (FB-D): `/api/v1/chat` exposes `complete_with_tools()` over HTTP. Rate limiting (10 req/60s, 11th → 429 + `Retry-After`; IP-keyed, SEED-AUTH-V1.5 plants caller-identity migration). 125s outer wall-clock timeout (FB-C 120s inner + 5s framing buffer). Sanitization boundary held end-to-end via FB-C transitive (D-15: handler does NOT re-sanitize). External-consumer parity verified — same endpoint serves Web UI + projekt-forge Flame hooks identically. CHAT-01, CHAT-02, CHAT-03, CHAT-05 closed v1.4 (Phase 16); CHAT-04 closed via chained 16 → 16.1 → 16.2 (PASS-with-deviations recorded in 16.2-HUMAN-UAT.md)
- ✓ Phase 16.1 (FB-D gap closure, INSERTED): backend-aware tool-list filter (`_IN_PROCESS_FORGE_TOOLS` frozenset + async TCP probe + 5s asyncio.Lock cache; 7-tool subset survives on bare-deploy hosts), Starlette `TemplateResponse(request, name, ctx)` migration in 13 callers + `starlette<0.53` pin drop, `_canonical_console_read_api` lifespan smoke test (Bug B regression guard), threshold bisection on assist-01 (`_CHOSEN_SCOPING_COUNT=20` locked) — v1.4 (Phase 16.1, completed 2026-04-28; Bugs A/B/C closed, Bug D routed to 16.2)
- ✓ Staged-handlers test harness rework (HARNESS-01..03): migrated `staged_client` from `starlette.testclient.TestClient` to `httpx.AsyncClient(transport=ASGITransport(app=app))` so test event loops match asyncpg's session loop (HARNESS-01); added `seeded_project` `@pytest_asyncio.fixture` in `tests/conftest.py` and wired it into 3 FK-violating staged-ops tests (HARNESS-02); removed `FORGE_TEST_DB=1` opt-in gate from `_phase13_postgres_available()` and wrapped `pg_terminate_backend` teardown SQL in `try/except Exception: pass` for non-SUPERUSER `forge` role (HARNESS-03). 22 of 23 previously silently-skipped console tests now run; remaining `test_transition_atomicity` failure is a pre-existing logic bug closed by POLISH-03. — v1.4.1 (Phase 18)
- ✓ Default cloud model bump (MODEL-01): `_DEFAULT_CLOUD_MODEL` flipped from `claude-opus-4-6` (deprecated, returned 500 against the live Anthropic API) → `claude-sonnet-4-6` (verified passing in v1.4 LLMTOOL-02 UAT after the `tool_choice` + `additionalProperties: false` adapter fixes). Single-commit isolated value-flip per Phase 15 D-30 decoupled-commit mandate; Plan 17-01 first extracted the two inline literals to module-scope `_DEFAULT_LOCAL_MODEL` / `_DEFAULT_CLOUD_MODEL` constants (pure refactor) so the flip became a single-line literal change. Live LLMTOOL-02 PASS without env override. — v1.4.1 (Phase 17)
- ✓ Default local model deferred with empirical evidence (MODEL-02 branch (b)): pre-run UAT against `qwen3:32b` on assist-01 produced cold-start `LLMLoopBudgetExceeded` driven by qwen3 thinking-mode token verbosity (400-525 tokens/turn). Numerics + diagnosis + named candidate v1.5 fixes captured in `SEED-DEFAULT-MODEL-BUMP-V1.4.x` (retargeted v1.4.x → v1.5). `SEED-OPUS-4-7-TEMPERATURE-V1.5` planted alongside for the AnthropicAdapter `temperature`-elision work needed before any future opus-4-7 bump becomes viable. Conservative-bump-first preserved: `qwen2.5-coder:32b` stays as default. — v1.4.1 (Phase 17)
- ✓ Code-quality polish (POLISH-01..04): WR-02 ref-collision guard — `_try_parse_text_tool_call` emits a placeholder ref and the call site overrides via `dataclasses.replace(salvaged, ref=f"{len(tool_calls)}:{salvaged.tool_name}")`, sharing the same `len(tool_calls)`-indexed namespace as the structured path so collisions are impossible (POLISH-01). Phase 13 `from_status="(missing)"` sentinel replaced with proper `Optional[str]`; zero `"(missing)"` literals in `forge_bridge/` and `tests/`; FB-B 404/409 split discriminators rewired to `exc.from_status is None` (POLISH-02). `test_transition_atomicity` rewritten from a vacuous `assert True  # placeholder` + a contradictory `assert row is None` to a single-session approve+flush+rollback observation that exercises the real SQLAlchemy/Postgres atomicity contract against live Postgres (POLISH-03). `_strip_terminal_chat_template_tokens` helper in `OllamaToolAdapter` strips contiguous `<|im_start|>` / `<|im_end|>` / `<|endoftext|>` runs from the tail of `_TurnResponse.text`; `INJECTION_MARKERS` extended 8 → 10; provider-scoped (Anthropic untouched) so no double-strip path through `console/handlers.py` (POLISH-04). — v1.4.1 (Phase 19)

### Active

v1.5 Legibility — see Current Milestone above. Requirements written to `.planning/REQUIREMENTS.md` at milestone-init; categories are DOCS / INSTALL / RECIPES / DIAG.

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
| Decoupled-commit purity for default-value flips: structural refactor (constant extraction) ships separately from value flips so `git blame` on a future bump line shows "model bump", not "refactor + bump". | Phase 17's MODEL-01 split into 17-01 (extract `_DEFAULT_LOCAL_MODEL` / `_DEFAULT_CLOUD_MODEL` module constants, values byte-identical) and 17-02 (single-line literal flip to `claude-sonnet-4-6`). The Phase 15 D-30 mandate proved its value here — every future model bump now ships as a pure single-line value change visible at the top of `git blame`. | ✓ Locked pattern (Phase 17, reusable for all future tunable-default flips) |
| Conservative-bump-first beats aspirational defaults: pre-run UAT against the candidate value before flipping. | Phase 17 MODEL-02: pre-run UAT against `qwen3:32b` on assist-01 produced cold-start `LLMLoopBudgetExceeded` driven by thinking-mode token verbosity (400-525 tokens/turn). Defer with empirical evidence (Run 1/Run 2 numerics + named candidate v1.5 fixes captured in the seed) is a first-class outcome, not a punt. The default flip would have regressed the live operator surface. | ✓ Complete (Phase 17, MODEL-02 deferral branch (b)) |
| Default-on test fixture probes with `OSError` silent-skip beat opt-in env-gates (`FORGE_TEST_DB=1`). | The v1.4 opt-in gate silently disabled an entire test surface (22+ tests). Phase 18 removed the gate and the tests it had been hiding immediately surfaced — including the `test_transition_atomicity` logic bug Phase 13 had carried since FB-A. Probe-and-skip-on-OSError matches CI green-state behavior without hiding regressions in development. | ✓ Complete (Phase 18, HARNESS-03) |
| Sentinel strings for type-discriminated routing are debt — replace with `Optional[T]` so the type system can see the contract. | Phase 13's `from_status="(missing)"` sentinel survived three phases discriminating an FB-B 404/409 routing split on a string literal the type system couldn't see. Phase 19 POLISH-02 replaced with proper `Optional[str]`; FB-B handlers now discriminate on `exc.from_status is None`. Lesson: if a sentinel value carries semantic discrimination, the type system should see it. | ✓ Complete (Phase 19, POLISH-02) |
| Provider-scoped strip helpers colocated with consumer; no double-strip path through callers. | Phase 19 POLISH-04 placed `_strip_terminal_chat_template_tokens` in `OllamaToolAdapter` only — `AnthropicToolAdapter` source contains zero references; `console/handlers.py` does not strip. Greedy `\Z`-anchored regex strips contiguous tail-token runs only, leaving mid-content occurrences alone (sanitization concern, not strip concern). FB-C D-09 colocation principle applied. | ✓ Complete (Phase 19, POLISH-04) |
| Single-session approve+flush+rollback observation pins the actual SQLAlchemy/Postgres atomicity contract; cross-session assertions that contradict committed-state durability are debt. | Phase 13's `test_transition_atomicity` was a vacuous `assert True  # placeholder` + a contradictory `assert row is None` (the row WAS committed in the propose step, so the assertion contradicted Postgres rollback semantics). Phase 19 POLISH-03 rewrote to a 26-line single-session observation: propose+commit (baseline persists) → approve+flush (in-flight visible) → rollback (in-flight reverts) → re-observe. Real audit-trail tamper guard against live Postgres. | ✓ Complete (Phase 19, POLISH-03) |

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
*Last updated: 2026-05-01 — Phase 20 (Reality Audit + Canonical Install) closed PASS-with-deviations. Track A author-walked-with-deviation under D-02.1 amendment surfaced 13 gaps; architecture validated end-to-end (cross-host LLM via assist-01 Ollama); install procedure as prose proven not shippable to artists. Phase 20.1 (install.sh + systemd daemon + env file) captured as v1.5 ship blocker. v1.5 not shippable until 20.1 lands.*
