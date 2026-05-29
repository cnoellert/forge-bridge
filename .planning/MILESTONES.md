# Milestones

## v1.7 Artist Readiness (Shipped: 2026-05-29)

**Threads completed:** 3 threads (B → C → A), 3 phase closures within Thread A (A.1 + A.2 + A.3), 1 thread-level close cursor (Thread A formal closure — first thread-level close in the project)
**Release tag:** none — patch-equivalent against 1.4.1 baseline (`__all__` at 19; `pyproject.toml` version 1.4.1; no public API expansion across the full milestone arc)
**Stats:** 75 commits, 126 files changed, +31,642 / −1,519 lines
**Timeline:** 2026-05-25 → 2026-05-29, ~5 days
**Audit:** verification gates green per phase; 38 tests passing at A.3 close; ruff clean on changed Python; `git diff --check` clean; A.2-shipped substrate byte-equivalent across A.3

**Key accomplishments per thread:**

- **Thread B — exec discoverability (closed 2026-05-25).** `fbridge discover` sub-app enumerating the chain grammar, six graph primitives, and registered tools as a substrate-derived introspection surface — never a curated layer. Two commits (B-1 sub-app + B-2 dogfooding pass for substrate self-description fixes). Architectural law named + exercised: introspection-pure, derived from docstrings and registries.
- **Thread C — asset operability (closed 2026-05-27).** Six dedicated MCP tools (`forge_create_asset` / `forge_list_assets` / `forge_get_asset` / `forge_attach_asset_location` / `forge_update_asset` / `forge_relate_asset`) bringing Asset to operator-legibility parity with Shot. Single-day arc seed→close (17 commits); behavioral test coverage + operator-readable docs. Asset is no longer quiet at the operator surface.
- **Thread A — chat input intent-layer (formally closed 2026-05-29 per THREAD-A-CLOSE.md).** Authority chain end-to-end: NL → compile → graph-intent → preview → ratify → apply. A.1 shipped `LLMRouter.compile_intent()` + `preview_emitted` SSE taxon + graph-intent persistence pre-ratify (authority-model retired across 3 surfaces / 2 transports / 4 contract shapes — 37 tests dispositioned). A.2 shipped `AssentRecord` + `AssentRecordRepo` substrate + 4 `assent.*` event types + `CommitNode.verify` assent extension + `fbridge ratify` CLI + `POST /api/v1/ratify` endpoint + store-and-replay substrate. A.3 shipped operational hardening — `_check_ratification` doctor row, `forge_bridge.console.helpers` operator helpers, drift-invalidation smoke, UAT runbook, `docs/RATIFICATION.md` auth-seed deferral section.
- **Phase 4b parallel track (orthogonal, 14 commits).** Sibling registration protocol (`ToolRegistry` + discovery + hard-degraded mode) and `GenerationPoller` worker + driver protocol + registry. Architecturally independent of Thread A — same window, separate substrate.

**Verification & regression:**

- A.1 / A.2 / A.3 phase verification gates green per phase close
- A.3 test gate: 38 passed
- Public API surface: `forge_bridge.__init__.py::__all__` length 19 — byte-identical to v1.4 close (no API changes; observability + operator surfaces only)
- `pyproject.toml` version: 1.4.1 across the full arc

**Known deferred items at close** (advisory, non-blocking — carry forward to v1.8 or beyond):

- **SEED-AUTH-V1.5** — auth identity binding for `AssentRecord.decided_by`. Documented as deferral in `docs/RATIFICATION.md` § Authentication (A.3 L5). A.3 ships NO auth code path; deferral is operationally surfaced.
- **Console ratification** — UI surface for assent. NOT Q5-safe via chat (LLM never owns assent — constitutional Thread A constraint). Separate operator-surface phase or thread.
- **Multi-turn graph-intent persistence** — graph-intent lifetime extension beyond single-session scope. Thread A scoped to sync-apply common case.
- **MILESTONES.md gap** — v1.5 and v1.6 shipped (per `CLAUDE.md` archaeology) but never received MILESTONES.md entries. The gap is explicitly noted at v1.7 close; backfill is optional future archaeology.
- **A.3-PLAN.md L4 drift envelope** — left as handoff archaeology recording the substrate-shape grounding miss (response envelope shape vs assent-record column); test asserts production shape, UAT-A3.md reconciled at 90bfbc2, A.3-CLOSE §Carried Forward documents the divergence.

**Lessons learned:**

- **Cadence convention shift mid-arc.** The writing-room cadence drifted toward methodology-surface inflation through Thread A; the operator named the devolution 2026-05-29 (*"the discipline framework is generating its own overhead"*). The lighter convention memorialized at `[[feedback-cadence-artifacts-shrink-to-load-bearing]]` landed mid-A.3 — concrete proof: A.3-DISCUSS-QUESTIONS at 193 lines vs A.2's 901; A.3-PLAN at 337 lines vs A.2's 2456. Same convergence work; ~1/5 the artifact volume. Shape trimming, not discipline abandonment.
- **Substrate-shape grounding matured to 5 instances / 4 manifestations.** The memory `[[feedback-substrate-shape-grounding-at-plan-stage]]` accumulated 4 within-project instances during Thread A's A.1+A.2 arc (shape / convention / flow manifestations). A.3 added a 5th instance + 4th manifestation (envelope/response shape). Catch-surface refinement: discoverable-surface Stage 1b reaches manifestations 1-3; runtime-path tracing from entry to error-wrapping site reaches manifestation 4.
- **Thread-level close cursor as new convention.** A.3-CLOSE R-A3.7 named "Thread A framing or v1.7 milestone framing RULES on formal Thread A closure." Thread B + C closed via milestone-level passoff archaeology without thread-level close cursors; Thread A got the first dedicated THREAD-A-CLOSE.md per the explicit R-A3.7 signal. Whether future threads adopt the precedent or stay with milestone-level archaeology is an open convention question.
- **Role-boundary discipline at scale.** Writing-room + active-testing surface preserved across A.1+A.2+A.3 arcs, Thread B+C arcs, and phase-4b parallel track. Implementation execution ran in separate sessions for A.2 + A.3 (and Thread B/C). 30+ within-day phase progressions across Thread A alone; zero role violations.

## v1.4.x Carry-Forward Debt (Shipped: 2026-04-30)

**Phases completed:** 3 phases (17, 18, 19), 10 plans, 14 tasks
**Release tag:** v1.4.1 (patch on top of v1.4.0)
**Requirements:** 9/9 Closed (MODEL-01..02, HARNESS-01..03, POLISH-01..04)
**Stats:** 60 commits, 13 source files changed (forge_bridge/+tests), +556 / −166 lines
**Timeline:** 2026-04-28 → 2026-04-30, ~3 days
**Audit:** `passed` (9/9 requirements satisfied, 7/7 cross-phase integration wires verified, public `__all__` byte-identical to v1.4 close)

**Key accomplishments:**

- **Default cloud model bump (Phase 17, MODEL-01).** `_DEFAULT_CLOUD_MODEL` flipped `claude-opus-4-6` (deprecated, returned 500 against the live Anthropic API) → `claude-sonnet-4-6` (verified passing in v1.4 LLMTOOL-02 UAT after the `tool_choice` + `additionalProperties: false` adapter fixes). Single-commit isolated value-flip (`edbfef6`) per the Phase 15 D-30 decoupled-commit mandate. Plan 17-01 first extracted the two inline literals at `LLMRouter.__init__` env-fallback sites into module-level `_DEFAULT_LOCAL_MODEL` / `_DEFAULT_CLOUD_MODEL` constants (pure refactor, values preserved) so 17-02's flip became a single-line literal change. Live LLMTOOL-02 PASS without env override.
- **Default local model deferred with empirical evidence (Phase 17, MODEL-02 branch (b)).** MODEL-02 took the deferral acceptance branch — pre-run UAT against `qwen3:32b` on assist-01 produced cold-start `LLMLoopBudgetExceeded` driven by qwen3 thinking-mode token verbosity (400-525 tokens/turn). Numerics + diagnosis + named candidate fixes were captured in `SEED-DEFAULT-MODEL-BUMP-V1.4.x` (retargeted v1.4.x → v1.5). `SEED-OPUS-4-7-TEMPERATURE-V1.5` planted alongside to capture the AnthropicAdapter `temperature`-elision work needed before any future opus-4-7 bump becomes viable. Conservative-bump-first preserved (qwen2.5-coder:32b stays as default until empirical evidence justifies the flip).
- **Test harness rework (Phase 18, HARNESS-01..03).** Migrated `staged_client` fixture from `starlette.testclient.TestClient` (sync, private event loop) to `httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")` and awaited all 31 call sites across 3 console test files — eliminates the asyncpg event-loop conflict (HARNESS-01). Added `seeded_project` `@pytest_asyncio.fixture` in `tests/conftest.py` and wired it into 3 FK-violating tests (2 store + 1 console), eliminating `entities_project_id_fkey` IntegrityErrors (HARNESS-02). Removed `FORGE_TEST_DB=1` opt-in gate from `_phase13_postgres_available()` and wrapped `pg_terminate_backend` teardown SQL in `try/except Exception` for the non-SUPERUSER `forge` role (HARNESS-03). Result: 22+ previously silently-skipped console tests now run against live Postgres; default `pytest tests/` 763p/117s/0err.
- **Code-quality polish (Phase 19, POLISH-01..04).** WR-02 ref-collision guard — `_try_parse_text_tool_call` now emits a placeholder ref and the call site overrides via `dataclasses.replace(salvaged, ref=f"{len(tool_calls)}:{salvaged.tool_name}")`, sharing the same `len(tool_calls)`-indexed namespace as the structured path so collisions are impossible (POLISH-01). Phase 13 `from_status="(missing)"` sentinel replaced with proper `Optional[str]`; zero `"(missing)"` literals in `forge_bridge/` and `tests/`; FB-B 404/409 split discriminators rewired to `exc.from_status is None` (POLISH-02). `test_transition_atomicity` rewritten from a vacuous `assert True  # placeholder` + a contradictory `assert row is None` to a single-session approve+flush+rollback observation that exercises the real SQLAlchemy/Postgres atomicity contract against live Postgres (POLISH-03). `_strip_terminal_chat_template_tokens` helper in `OllamaToolAdapter` strips contiguous `<|im_start|>` / `<|im_end|>` / `<|endoftext|>` runs from the tail of `_TurnResponse.text`; `INJECTION_MARKERS` extended 8 → 10; provider-scoped (Anthropic untouched) so no double-strip path through `console/handlers.py` (POLISH-04).

**Verification & regression:**

- Phase 17 VERIFICATION: `passed` (11/11 must-haves)
- Phase 18 VERIFICATION: `passed` (9/9; 4 SUMMARY files because 18-02 also produced a `PHASE-SUMMARY.md`)
- Phase 19 VERIFICATION: `passed` (14/14 must-haves; 6 new POLISH-targeted regression tests)
- Cross-phase integration audit: 7/7 wires verified
- Default unit-test suite: 865 passed, 19 skipped, 0 failed (~35s) at close
- Combined integration slice with `FORGE_DB_URL` set: 148 passed, 4 skipped, 0 failed
- Public API surface: `forge_bridge.__init__.py::__all__` length 19 — byte-identical to v1.4 close (no API changes; internal tech-debt only)

**Known deferred items at close** (advisory only, non-blocking — carry forward to v1.5):

- Nyquist VALIDATION.md coverage — Phase 17 missing, Phase 18 missing, Phase 19 partial (draft generated by planner, not finalized). Run `/gsd-validate-phase 17/18/19` to backfill if desired.
- SUMMARY frontmatter `requirements_completed` field missing in 17-02, 17-03, 18-02, 18-03, 19-01, 19-02 (VERIFICATION.md remained authoritative for the audit cross-reference).
- `SEED-DEFAULT-MODEL-BUMP-V1.4.x` retargeted to v1.5 (qwen3:32b deferral with empirical evidence).
- `SEED-OPUS-4-7-TEMPERATURE-V1.5` planted by Phase 17 (carry forward).

**Lessons learned:**

- Decoupled-commit purity is real and worth the cost — Phase 17 split a structural refactor (constant extraction) from two value flips so `git blame` on the bumped line shows "model bump", not "refactor + bump". The Phase 15 D-30 mandate proved its value here.
- Conservative-bump-first beats aspirational defaults — pre-run UAT against `qwen3:32b` produced concrete failure-mode diagnosis (thinking-mode token verbosity) and a named v1.5 candidate fix path, instead of a default flip that would have regressed the live operator surface. Deferral with empirical evidence is a first-class outcome, not a punt.
- A test fixture probe gated behind a non-default opt-in env (`FORGE_TEST_DB=1`) silently disabled an entire test surface for the v1.4 milestone. Phase 18 removed the gate and the 22+ tests it had been hiding immediately surfaced — including the `test_transition_atomicity` logic bug Phase 13 had carried since FB-A. Default-on probes with `OSError` silent-skip beat opt-in gates.
- Sentinel strings ("(missing)") create type-contract drift that compounds — an FB-B 404/409 routing split survived three phases discriminating on a string literal that the type system couldn't see. Replacing it with `Optional[str]` made the contract honest and gave the type checker a real signal at the exception-surface boundary.

---

## v1.4 Staged Ops Platform (Shipped: 2026-04-28)

**Phases completed:** 6 phases (13, 14, 15, 16, 16.1, 16.2 — FB-A..FB-D + two inserted gap-closure phases), 28 plans
**Release tag:** v1.4.0 (proposed; not yet pushed)
**Requirements:** 19/19 Closed (100%) — STAGED-01..07, LLMTOOL-01..07, CHAT-01..05
**Stats:** 218 commits, 66 files changed (forge_bridge/+tests), +10,073 / −154 lines, ~40,038 LOC at close
**Timeline:** 2026-04-25 → 2026-04-28, ~3 days

**Key accomplishments:**

- **Staged Operation entity + lifecycle (Phase 13 → FB-A).** New `entity_type='staged_operation'` participates in the existing extensible entity model. State machine `proposed → approved → executed/rejected/failed` enforced in the data layer; illegal transitions raise `StagedOpLifecycleError`. Every transition emits a `DBEvent` row with `actor`, `old_status`, `new_status`, timestamp — full audit replay queryable by `entity_id`. `parameters` JSONB preserved verbatim across status advancement; `result` JSONB null until terminal. Reversible Alembic migration `0003_staged_operation.py`. STAGED-01..04 closed live on dev Postgres `127.0.0.1:7533/forge_bridge` 2026-04-28 (29 passed, 4 by-design skips, 0 failed).
- **Staged Ops MCP + HTTP surface (Phase 14 → FB-B).** Four MCP tools (`forge_list/get/approve/reject_staged`) + three HTTP routes (`GET /api/v1/staged?status=...`, `POST /api/v1/staged/{id}/approve`, `POST /api/v1/staged/{id}/reject`) + `forge://staged/pending` MCP resource — all served from a single `ConsoleReadAPI` facade. D-19 byte-identity tests assert MCP/HTTP zero divergence; D-20 byte-identity test asserts resource ↔ shim ↔ list-tool consistency. Approval is bookkeeping only — proposer (e.g., projekt-forge) subscribes to approval events via the existing event bus and executes against its own domain.
- **LLMRouter agentic loop (Phase 15 → FB-C).** `LLMRouter.complete_with_tools(prompt, tools, sensitive=...)` runs the full loop: send prompt + tool schemas → parse `tool_call` → execute against MCP tools in-process → feed result back → repeat until terminal. Provider-neutral coordinator + thin Anthropic + Ollama adapters. Sensitive routing preserved verbatim from `acomplete()`. Hard caps: 8 iterations, 120s wall-clock, 30s per-tool sub-budget — exceeding any raises `LLMLoopBudgetExceeded` (exported in `forge_bridge.__all__`, barrel grew 16→17). Repeat-call detection (3 identical `(tool_name, json.dumps(args, sort_keys=True))` invocations → synthetic `is_error=True` tool result, original tool not invoked). 8 KB result-size cap (`_TOOL_RESULT_MAX_BYTES=8192`, overridable). `_sanitize_tool_result()` consolidated with Phase 7's `_sanitize_tag()` — single-source `INJECTION_MARKERS` at `_sanitize_patterns.py`. Recursive-synthesis guard (`_in_tool_loop` ContextVar + `RecursiveToolLoopError`); synthesizer AST blocklist updated for `forge_bridge.llm` imports. LLMTOOL-01 closed retroactively by Phase 16.2 live UAT (PASS in 21.38s on assist-01). LLMTOOL-02 closed live 2026-04-28 against `claude-sonnet-4-6` after surfacing + fixing two latent Anthropic SDK API-drift bugs.
- **Chat endpoint (Phase 16 → FB-D, absorbed superseded Phase 12).** `/api/v1/chat` exposes `complete_with_tools()` over HTTP. Rate limiting (10 req/60s, 11th → 429 + `Retry-After`; IP-keyed for v1.4 — SEED-AUTH-V1.5 plants caller-identity migration). 125s outer wall-clock timeout (LLMTOOL-03 inner 120s + 5s framing buffer). Sanitization boundary held end-to-end via FB-C transitive (chat handler does NOT re-sanitize per D-15). External-consumer parity verified — same endpoint serves Web UI + projekt-forge Flame hooks with structurally identical responses. CHAT-04 satisfied via the chained 16 → 16.1 → 16.2 closure.
- **Phase 16.1 (FB-D gap closure, INSERTED 2026-04-27).** Phase 16's deploy on assist-01 surfaced three structural bugs: (A) `TemplateResponse(name, ctx)` deprecated signature in 13 callers, (B) silent `_llm_router=None` short-circuit when `_lifespan` boot order changed, (C) chat-handler tool-list hang on 49-tool registry against live Ollama. Six-plan remediation: backend-aware tool-list filter (`_IN_PROCESS_FORGE_TOOLS` frozenset + async TCP probe + 5s asyncio.Lock cache; 7 tools survive on bare-deploy hosts), Starlette ≥0.30 migration + pin drop, `_canonical_console_read_api` lifespan smoke test (Bug B regression guard), threshold bisection on assist-01 (`_CHOSEN_SCOPING_COUNT=20` locked with margin). Bugs A/B/C closed; Bug D — chat surface returning raw tool-call JSON as assistant text — surfaced in Phase 16.1's UAT and routed to Phase 16.2.
- **Phase 16.2 (Bug D closure, INSERTED 2026-04-28).** RED → GREEN TDD pair against real captured Ollama 0.21.0 / qwen2.5-coder:32b traffic from assist-01. RED test (`tests/llm/test_ollama_adapter.py::TestOllamaToolAdapterBugDFallback`) fails on `main` with explicit Bug D regression assertion. GREEN fix (`_try_parse_text_tool_call` salvage helper + hook in `OllamaToolAdapter.send_turn()`) flips RED → GREEN; router/handlers byte-identical to pre-phase. Strengthened E2E adds `_BUG_D_TERMINAL_JSON_RE` regex assertion to `test_chat_canonical_uat_prompt_under_60s`. Fresh-operator UAT records `Outcome: PASS with deviations` per Phase 10.1 / 16.1 D-14 precedent — D-08 #1 PASS in 21.38s, D-08 #2a/b PASS 16/16 each, D-08 #3 PASS via live walkthrough on assist-01 (synthesized natural-language answer, NOT raw JSON). Live correction during the UAT loop: dropped Plan 03's D-06 #2 assertion (asserted on router-internal turns instead of API response) — load-bearing D-06 #1 regex guard untouched. Branch divergence (dev main ↔ origin v1.4 ↔ assist-01 v1.4) reconciled before milestone close — all three at `2afb921` on `gsd/v1.4-staged-ops-platform`.

**Verification & regression:**

- Phase 13 VERIFICATION: `human_needed` 2026-04-26 (4/4 structurally); STAGED-01..04 closed live 2026-04-28 (29/29)
- Phase 14 VERIFICATION: `passed` 2026-04-26 (4/4)
- Phase 15 VERIFICATION: `human_needed` 2026-04-26 (7/7 programmatic); LLMTOOL-01 closed retroactively by 16.2; LLMTOOL-02 closed live 2026-04-28
- Phase 16 VERIFICATION: `gaps_found` 2026-04-27 (5/6 — CHAT-04 routed); CHAT-04 closed via chained 16 → 16.1 → 16.2
- Phase 16.1 VERIFICATION: `gaps_found` 2026-04-28T01:46Z (4/5 — Bug D routed); HUMAN-UAT status flipped to `resolved` after 16.2 close
- Phase 16.2 VERIFICATION: `passed` 2026-04-28T22:00Z (5/5 ROADMAP + 23/23 plan-level; 1 override accepted for live D-06 #2 correction)
- Cross-phase integration audit: 12/12 wires verified, 5/5 E2E flows complete, 0 orphans, 0 broken flows, 0 missing connections
- Default unit-test suite: 754 passed, 102 skipped, 0 failed at close
- Branch reconciliation: dev main ↔ origin v1.4 ↔ assist-01 v1.4 all at `2afb921`

**Known deferred items at close** (carry forward to v1.4.x):

- Staged-handlers test harness rework — 26 tests fail under live Postgres with `starlette.TestClient`/`asyncpg` event-loop conflict; switch to `httpx.AsyncClient(transport=ASGITransport(app=...))`. Conftest probe gated behind `FORGE_TEST_DB=1` opt-in to preserve historical CI green state.
- `tests/test_staged_operations.py` Project-row seeding gap — 3 tests fail because `repo.propose(project_id=<fresh UUID>)` violates `entities_project_id_fkey`; fixture needs to seed parent `Project` rows.
- `LLMRouter._cloud_model` default bump from `claude-opus-4-6` (deprecated; returns 500) → `claude-sonnet-4-6` (or `claude-opus-4-7` paired with conditional-temperature handling — opus-4-7 rejects `temperature`).
- Phase 16.2 REVIEW.md WR-02 (hard-coded `ref="0:{name}"` fragile if guard ever loosens). WR-01 (regex `^{` prefilter limitation) was closed during v1.4 milestone close after the LLMTOOL-01 sentinel UAT surfaced a trailing-prose Bug D variant against qwen2.5-coder:32b — `_try_parse_text_tool_call` now uses `json.JSONDecoder().raw_decode()` to handle markdown-fenced + leading-prose + trailing-prose variants. Local LLM tool-call parity with Claude is now real, not aspirational.
- Phase 13 REVIEW.md WR-01 (`from_status="(missing)"` type-contract issue at `staged_operations.py:290`) and WR-02 (placeholder cross-session atomicity sub-test at `tests/test_staged_operations.py:356`).
- qwen2.5-coder model-quality artifact: occasionally appends `<|im_start|>` chat-template tokens + speculative second tool-call JSON at tail of synthesized prose; strip in chat handler.
- Phase 16.2 D-10 ratification annotation hook: post-close fresh-artist re-run remains open as strengthening (does NOT re-open Phase 16.2).

**Lessons learned (carried as memory notes):**

- `git fetch` of a stale remote-tracking ref can make divergence look bigger than it is — always verify `git log REMOTE..HEAD` before assuming a complex rebase. Patch-id deduplication during `git rebase` correctly drops cherry-picked commits without warning.
- Live operator UAT catches what mocked unit tests don't — the Anthropic adapter had two latent SDK API-drift bugs that 14 wire-format unit tests using mocks could not surface.
- A test fixture probe hardcoded to a port that doesn't match the project's actual DB silently disables an entire test surface. Fixed (gated behind `FORGE_TEST_DB=1` for now); harness rework deferred to v1.4.x.

---

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
