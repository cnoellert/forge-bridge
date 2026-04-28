# Roadmap: forge-bridge

## Milestones

- ✅ **v1.0 Canonical Package & Learning Pipeline** — Phases 1-3 (shipped 2026-04-15)
- ✅ **v1.1 projekt-forge Integration** — Phases 4-6 (shipped 2026-04-19 — v1.1.0 API release, v1.1.1 PATCH-01)
- ✅ **v1.2 Observability & Provenance** — Phases 7, 07.1, 8 (shipped 2026-04-22 — v1.2.0, v1.2.1 hotfix, v1.3.0)
- ✅ **v1.3 Artist Console** — Phases 9, 10, 10.1, 11 (shipped 2026-04-25 — v1.3.1; Phase 12 superseded by v1.4 FB-D)
- 🚧 **v1.4 Staged Ops Platform** — Phases 13-16 (FB-A..FB-D) (opened 2026-04-25 — consumed by projekt-forge v1.5)

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

### 🚧 v1.4 Staged Ops Platform (opened 2026-04-25)

- [x] **Phase 13 (FB-A): Staged Operation Entity & Lifecycle** — `entity_type='staged_operation'` with proposed→approved→executed/rejected/failed state machine + `DBEvent` audit trail per transition (completed 2026-04-26)
- [x] **Phase 14 (FB-B): Staged Ops MCP Tools + Read API** — `forge_list/get/approve/reject_staged` MCP tools + `/api/v1/staged/*` HTTP routes + `forge://staged/pending` resource via single `ConsoleReadAPI` facade (completed 2026-04-26)
- [x] **Phase 15 (FB-C): LLMRouter Tool-Call Loop** — `complete_with_tools()` agentic coordinator + thin Anthropic + Ollama adapters; iteration cap (default 8) + wall-clock cap (default 120s); repeat-call detection, 8 KB result cap, sanitization boundary, recursive-synthesis guard ✅ 2026-04-27 (operator UAT pending for LLMTOOL-01/02)
- [x] **Phase 16 (FB-D): Chat Endpoint** — `/api/v1/chat` over `complete_with_tools()` with rate limiting, sanitization end-to-end, single chat surface for Web UI + projekt-forge Flame hooks (absorbs superseded Phase 12) (complete 2026-04-27; CHAT-04 deploy gap routed to Phase 16.1)
- [x] **Phase 16.1 (FB-D gap closure): Chat Tool-List Hang + Wiring Regression Guards** — Close the CHAT-04 artist UAT gap surfaced in the 2026-04-27 assist-01 deploy: bisect + fix the 49-tool `complete_with_tools()` hang, add boot-time regression guard for LLMRouter wiring, migrate `TemplateResponse` callers, re-run the artist UAT (inserted 2026-04-27 per Phase 10/10.1 precedent) (completed 2026-04-28)

## Phase Details


### 🚧 v1.4 Staged Ops Platform (Phases 13-16, alias FB-A..FB-D)

**Milestone Goal**: Extend forge-bridge with the human-in-the-loop primitives that
projekt-forge v1.5 needs to become a thin Flame-side consumer: a `staged_operation` entity
with a proposed→approved→executed lifecycle, MCP + HTTP surface for list/approve/reject,
an agentic `complete_with_tools()` method on LLMRouter, and a chat endpoint that binds it
all together for both the Web UI (Phase 10) and external Flame hooks.

**Pre-designed 2026-04-23** after projekt-forge ROADMAP restructure audit. Each FB phase maps
directly to a dependency projekt-forge v1.5 has declared. (projekt-forge v1.4 is Editorial
Operations — Flame-side work independent of forge-bridge, sequenced ahead of the consumer
milestone so Flame-side velocity is not gated on upstream platform work.) **Opened 2026-04-25**
via `/gsd-new-milestone v1.4`; REQUIREMENTS.md authored same day; targeted FB-C research at
`.planning/research/FB-C-TOOL-CALL-LOOP.md` expanded LLMTOOL coverage from 3 → 7 requirements
and added CHAT-05 (external-consumer parity) to FB-D.

**Dual-naming locked 2026-04-25** (gsd-discuss-phase tooling impedance): phases carry both
a numeric ID for gsd tooling (`13..16`, skipping superseded Phase 12 "LLM Chat") AND the
preserved `FB-A..FB-D` alias. The letter scheme is the canonical cross-repo identifier —
projekt-forge v1.5 declared FB-A..FB-D as required deps so the alias stays stable. The
numeric IDs are internal plumbing for `find-phase`, state tracking, and directory naming.
References below use `Phase 13 (FB-A)` style; either side of the parens resolves.

**Parallel-execution note**: Phase 13 (FB-A) and Phase 15 (FB-C) have NO dependency on each
other and CAN ship in parallel. The dependency chains are 13→14 (FB-A → FB-B; entity before
its surface) and 15→16 (FB-C → FB-D; loop before the chat endpoint that consumes it).
Sequencing 13 and 15 concurrently is a legitimate execution-order choice for the user;
14 and 16 both depend on the v1.3 Read API + Web UI surface that already shipped.

---

### Phase 13 (FB-A): Staged Operation Entity & Lifecycle
**Goal**: A new `staged_operation` entity type participates in the existing extensible
entity model with a full proposed→approved→executed/rejected/failed lifecycle enforced
in the data layer. Every transition emits a `DBEvent` for audit. Stores proposer identity,
operation name, proposed parameters (JSONB), realized result diff (JSONB), and timing.
**Depends on**: Phase 8 (SQL persistence — both shipped in v1.3), Phase 9 (Read API + event surface — shipped in v1.3)
**Parallelizable with**: Phase 15 (FB-C) (no shared dependency)
**Requirements**: STAGED-01, STAGED-02, STAGED-03, STAGED-04
**Success Criteria** (what must be TRUE):
  1. `entity_type='staged_operation'` entities can be created via the store layer with `proposer`, `operation`, `parameters` (JSONB), and initial `status='proposed'` — verified via a direct SQLAlchemy round-trip test (insert, fetch, compare).
  2. Lifecycle transitions are enforced: `proposed → approved → executed` (happy path), `proposed → rejected` (artist veto), `approved → failed` (execution error). Illegal transitions (e.g., `executed → proposed`, `rejected → executed`) raise `StagedOpLifecycleError` with the attempted transition in the message.
  3. Every transition writes a `DBEvent` row with `old_status`, `new_status`, the actor (proposer for proposed→rejected; approver for proposed→approved; executor for approved→executed/failed), and timestamp — queryable by `entity_id` for full audit replay.
  4. The `parameters` JSONB at `status='proposed'` is preserved verbatim across status advancement (the column is never mutated after creation); the `result` JSONB column is populated only on `executed` or `failed` and is null otherwise. A diff of `parameters` vs `result` is recoverable per operation via SQL alone.
**Plans**: 4 plans across 3 waves (planned 2026-04-25 — execute in dependency order)
  - Wave 1 (parallel):
    - [ ] `13-01-PLAN.md` — Extend ENTITY_TYPES + EVENT_TYPES in models.py and ship the 0003_staged_operation Alembic migration (CHECK-constraint update only; events table needs no migration per PATTERNS.md Finding #1)
    - [ ] `13-02-PLAN.md` — Create the StagedOperation application class (overrides entity_type to return literal "staged_operation" — fixes the #1 silent-bug risk per PATTERNS.md Finding #3) and re-export from forge_bridge.core
  - Wave 2 (depends on 13-01 + 13-02):
    - [ ] `13-03-PLAN.md` — StagedOpRepo state machine + StagedOpLifecycleError + EntityRepo extensions; composes EventRepo for audit append per PATTERNS.md Finding #8; atomicity on shared AsyncSession
  - Wave 3 (depends on 13-03):
    - [ ] `13-04-PLAN.md` — session_factory async-DB fixture (greenfield per PATTERNS.md Finding #4) + STAGED-01..04 tests + atomicity test

---

### Phase 14 (FB-B): Staged Ops MCP Tools + Read API
**Goal**: MCP and HTTP surface for external clients (projekt-forge, Claude Code, Web UI)
to list, fetch, approve, and reject staged operations. `forge://staged/...` MCP resources
mirror HTTP endpoints; the same `ConsoleReadAPI` facade serves both. Approval is bookkeeping
only — forge-bridge does not execute the operation; the proposer (e.g., projekt-forge)
subscribes to approval events via the existing event bus and executes against its own domain.
**Depends on**: Phase 13 (FB-A) (entity + lifecycle), Phase 9 (Read API foundation — shipped in v1.3), Phase 10 (Web UI — consumer reference, shipped in v1.3)
**Requirements**: STAGED-05, STAGED-06, STAGED-07
**Success Criteria** (what must be TRUE):
  1. MCP tools `forge_list_staged`, `forge_get_staged`, `forge_approve_staged`, `forge_reject_staged` are registered and callable from a real MCP client session; each returns a JSON payload that matches the entity shape from Phase 13 (FB-A) plus the `status` field.
  2. `GET /api/v1/staged?status=proposed` returns all pending operations; `POST /api/v1/staged/{id}/approve` and `POST /api/v1/staged/{id}/reject` transition lifecycle and return the updated record — same data shape as the MCP tools (zero divergence; verified by side-by-side response comparison test).
  3. `resources/read forge://staged/pending` returns a snapshot of pending operations identical to `forge_list_staged(status='proposed')` output.
  4. Approval does NOT execute the operation itself — forge-bridge is the bookkeeper; the proposer subscribes to approval events via the existing event bus and executes against its own domain (Flame). Verified by unit test: approval transitions the entity and emits a DBEvent without calling any execution code path.
**Plans**: 5 plans across 3 waves (planned 2026-04-26 — execute in dependency order)
  - Wave 1 (parallel — foundation):
    - [ ] `14-01-PLAN.md` — StagedOpRepo.list() + WR-01 sentinel fix at staged_operations.py:289
    - [ ] `14-02-PLAN.md` — ConsoleReadAPI session_factory + get_staged_ops/get_staged_op + _lifespan wiring
  - Wave 2 (parallel — surfaces; depend on Wave 1):
    - [ ] `14-03-PLAN.md` — HTTP routes + handlers (staged_list/approve/reject) + _resolve_actor + app.state.session_factory + CORS extension
    - [ ] `14-04-PLAN.md` — 4 forge_*_staged MCP tools + Pydantic input models + register from register_console_resources per D-17 Solution C
  - Wave 3 (integration; depends on Wave 2):
    - [ ] `14-05-PLAN.md` — forge://staged/pending resource + forge_staged_pending_read shim + zero-divergence tests + does_not_execute regression guard + v1.5 SEED files

---

### Phase 15 (FB-C): LLMRouter Tool-Call Loop
**Goal**: `LLMRouter.complete_with_tools(prompt, tools, sensitive=...)` runs the full
agentic loop — send prompt + tool schemas, parse `tool_call`, execute each tool against
the registered MCP tools in-process, feed result back, repeat until the LLM returns a
terminal response. Provider-neutral coordinator + thin Anthropic + Ollama adapters.
Sensitive routing preserved verbatim from `acomplete()`. Hard iteration cap, wall-clock cap,
repeat-call detection, ingest-time result truncation, sanitization boundary on tool results,
and a recursive-synthesis guard ship in the same phase.
**Depends on**: Phase 1 (LLMRouter), Phase 7 (tool provenance — tools expose schemas + `_sanitize_tag()` pattern set to consolidate)
**Parallelizable with**: Phase 13 (FB-A) (no shared dependency)
**Requirements**: LLMTOOL-01, LLMTOOL-02, LLMTOOL-03, LLMTOOL-04, LLMTOOL-05, LLMTOOL-06, LLMTOOL-07
**Success Criteria** (what must be TRUE):
  1. `router.complete_with_tools(prompt, tools=[...], sensitive=True)` completes a two-step loop (LLM calls tool A, receives result, returns final response) against a real Ollama backend running `qwen2.5-coder:32b` — verified in an integration test on assist-01.
  2. Cloud path (`sensitive=False` → Anthropic) produces a terminal response for the same prompt + tool schemas as criterion 1 — verified against live API with `ANTHROPIC_API_KEY` set. Sensitive routing logic (`sensitive=True → local`) is preserved verbatim from existing `acomplete()` behavior.
  3. A tool invocation failure (raised exception, timeout, schema mismatch) is caught at the coordinator boundary, surfaced back to the LLM as a structured `tool_result` with `is_error=True` (Anthropic) or `"ERROR: "` content prefix (Ollama), and the loop continues — one bad tool does not abort the session. Iteration cap (default 8) and wall-clock cap (default 120s) terminate runaway loops with `LLMLoopBudgetExceeded` (exported from `forge_bridge.__all__`, barrel grows 16→17). Per-tool sub-budget is `min(30s, remaining_global_budget)`.
  4. Repeat-call detection: after three identical `(tool_name, json.dumps(args, sort_keys=True))` invocations within one session, the coordinator injects a synthetic `tool_result` with `is_error=True` and text `"You have called {tool} with the same arguments {n} times..."`. The original tool is NOT invoked the third time — verified via integration test with a stub LLM that emits the same tool_call three times.
  5. Tool result size cap: every tool result string is truncated to 8192 bytes before feeding back to the LLM, suffixed with `\n[...truncated, full result was {n} bytes]`. Constant `_TOOL_RESULT_MAX_BYTES = 8192` is overridable via `complete_with_tools(..., tool_result_max_bytes=N)` — verified via integration test with a stub tool returning 100 KB of payload.
  6. Sanitization boundary: `_sanitize_tool_result()` exists in `forge_bridge/llm/_sanitize.py` and runs on every tool_result content string before leaving the coordinator. Pattern set is consolidated with Phase 7's `_sanitize_tag()` (single source of truth in `forge_bridge/_sanitize_patterns.py` or equivalent). Injection markers (case-insensitive) are replaced with `[BLOCKED:INJECTION_MARKER]`; ASCII control chars (other than `\n`, `\t`) are stripped — verified via integration test with a tool returning a known injection string. **Acceptance overlaps with CHAT-03 in Phase 16 (FB-D)**: Phase 15 ships the helper, Phase 16 wires the chat endpoint into it.
  7. Recursive-synthesis guard: a contextvar `_in_tool_loop` is set inside `complete_with_tools()` (try/finally for cleanup); both `acomplete()` and `complete_with_tools()` check the var on entry and raise `RecursiveToolLoopError` if set. The synthesizer's safety blocklist (Phase 3) is updated to flag imports from `forge_bridge.llm` in synthesized code — verified via unit test that a tool function calling `acomplete()` raises `RecursiveToolLoopError` when invoked from within `complete_with_tools()`.
**Plans**: 10 plans across 5 waves (planned 2026-04-26 — execute in dependency order)
  - Wave 1 (parallel — foundation):
    - [ ] `15-01-PLAN.md` — Hoist sanitization patterns to `forge_bridge/_sanitize_patterns.py` + shim `learning/sanitize.py` (D-09/D-10)
    - [ ] `15-02-PLAN.md` — Add `ollama>=0.6.1,<1` to pyproject `[llm]` extra + `LLMRouter._get_local_native_client()` lazy slot (D-02)
    - [ ] `15-03-PLAN.md` — Three exception classes (`LLMLoopBudgetExceeded`, `RecursiveToolLoopError`, `LLMToolError`) + `forge_bridge.__all__` barrel growth 16→19 (D-15..D-19)
  - Wave 2 (parallel — core surfaces; depend on Wave 1):
    - [ ] `15-04-PLAN.md` — `_sanitize_tool_result()` in `forge_bridge/llm/_sanitize.py` + 21 unit tests (LLMTOOL-05/06, D-08/D-11)
    - [ ] `15-05-PLAN.md` — `_adapters.py` (`_ToolAdapter` Protocol + `AnthropicToolAdapter` + `OllamaToolAdapter` + dataclasses + `_OLLAMA_TOOL_MODELS`) + `_StubAdapter` fixture + adapter wire-format tests (D-01..D-06, D-29, D-31, D-33, D-35, D-37)
    - [ ] `15-06-PLAN.md` — Recursive-synthesis guard: `_in_tool_loop` ContextVar + `acomplete()` entry check + synthesizer `_check_safety()` AST extension + tests (LLMTOOL-07, D-12..D-14)
    - [ ] `15-07-PLAN.md` — Public `invoke_tool(name, args)` in `mcp/registry.py` + `mcp` package re-export + tests (D-21)
  - Wave 3 (coordinator; depends on all of Wave 2):
    - [ ] `15-08-PLAN.md` — `LLMRouter.complete_with_tools()` coordinator wiring all LLMTOOL-03..07 helpers + 18+ deterministic unit tests against `_StubAdapter` (D-03..D-08, D-17, D-18, D-20..D-27, D-34, D-36)
  - Wave 4 (live integration; depends on Wave 3):
    - [ ] `15-09-PLAN.md` — `tests/integration/` subpackage + env-gated live tests against Ollama (`qwen2.5-coder:32b` on assist-01) and Anthropic API (LLMTOOL-01/02, D-32)
  - Wave 5 (forward-looking seeds; parallel — last):
    - [ ] `15-10-PLAN.md` — Plant 7 SEED files (DEFAULT-MODEL-BUMP-V1.4.x, CLOUD-MODEL-BUMP-V1.4.x, PARALLEL-TOOL-EXEC-V1.5, MESSAGE-PRUNING-V1.5, TOOL-EXAMPLES-V1.5, CMA-MEMORY-V1.5+, CROSS-PROVIDER-FALLBACK-V1.5)

---

### Phase 16 (FB-D): Chat Endpoint (absorbs superseded Phase 12)
**Goal**: `/api/v1/chat` exposes `complete_with_tools()` over HTTP with sanitized context
assembly, wall-clock timeout, and rate limiting. Consumed by the Web UI chat panel
(wired through the chat-nav stub shipped in CONSOLE-04 v1.3) and by external Flame hooks
(projekt-forge v1.5 Phase 22/23). One chat surface, multiple consumers, byte-identical
behavior. This phase absorbs the previously velocity-gated Phase 12 "LLM Chat" scope.
**Depends on**: Phase 15 (FB-C) (tool-call loop), Phase 10 (Web UI consumer — shipped in v1.3), Phase 9 (Read API host — shipped in v1.3)
**Requirements**: CHAT-01, CHAT-02, CHAT-03, CHAT-04, CHAT-05
**Success Criteria** (what must be TRUE):
  1. Eleven rapid requests from the same IP within one minute: the eleventh returns HTTP 429 with `{"error": "rate limit exceeded", ...}` envelope — cost cap enforced. Bucket is keyed by remote IP for v1.4; SEED-AUTH-V1.5 plants the migration to caller-identity bucketing once auth lands.
  2. Wall-clock timeout: an `acomplete_with_tools()` call that blocks indefinitely causes the endpoint to return a timeout error within 125 seconds (Phase 15 (FB-C) cap of 120s + 5s buffer for response framing) — no hung requests, verified via integration test with a stub tool that sleeps forever.
  3. Sanitization boundary holds end-to-end: a tool whose sidecar name or parameters contain an injection marker (e.g., `IGNORE PREVIOUS INSTRUCTIONS`) does not propagate that string into the LLM context. Wired through Phase 15 (FB-C)'s `_sanitize_tool_result()` plus Phase 7's tool-definition sanitization — verified via integration test that the LLM-bound prompt does NOT contain the marker substring after a deliberately-poisoned tool runs.
  4. Non-developer dogfood UAT: an artist asks "what synthesis tools were created this week?" in the Web UI chat panel and receives a useful, plain-English answer within the LLM's normal response time (<60s on assist-01 hardware). UAT pattern matches Phase 10's D-36 hard fresh-operator gate; failure here triggers a remediation phase (analogous to Phase 10.1).
  5. External-consumer parity: the same `/api/v1/chat` endpoint serves projekt-forge Flame hooks (projekt-forge v1.5 Phase 22/23 consumers) with zero divergence in behavior or context assembly compared to the Web UI — verified by replaying the same prompt + tool schemas through both clients and comparing terminal responses (modulo non-deterministic LLM output — assert structural shape match).
**Plans**: 7 plans across 4 waves (planned 2026-04-27 — execute in dependency order)
  - Wave 1 (parallel — foundation):
    - [ ] `16-01-PLAN.md` — Extend FB-C `complete_with_tools()` with optional `messages: list[dict] | None = None` kwarg (D-02a Pattern B prerequisite)
    - [ ] `16-02-PLAN.md` — Greenfield `forge_bridge/console/_rate_limit.py` token-bucket module + 8 deterministic tests (D-13 / CHAT-01)
    - [ ] `16-03-PLAN.md` — Append chat-panel CSS rules to `forge-console.css` (LOGIK-PROJEKT amber spinner + transcript layout, all using existing tokens)
  - Wave 2 (surfaces; depend on Wave 1):
    - [ ] `16-04-PLAN.md` — `chat_handler` + `Route("/api/v1/chat", ...)` + 11 deterministic tests (CHAT-01/CHAT-02 + D-09/D-13/D-14/D-14a/D-15/D-16/D-17/D-21)
    - [ ] `16-05-PLAN.md` — Web UI panel: delete `stub.html`, ship `panel.html` + `forge-chat.js` + rename `ui_chat_stub_handler` → `ui_chat_handler` (D-06/D-07/D-08/D-10/D-11/D-20) — has human-verify checkpoint
  - Wave 3 (integration; depends on Wave 2):
    - [ ] `16-06-PLAN.md` — `tests/integration/test_chat_endpoint.py` (CHAT-03 sanitization E2E) + `test_chat_parity.py` (CHAT-05 external-consumer parity)
  - Wave 4 (forward-looking artifacts; depends on Wave 3):
    - [ ] `16-07-PLAN.md` — Plant 5 SEED files (STREAMING, TOOL-ALLOWLIST, CLOUD-CALLER, PERSIST-HISTORY, PARTIAL-OUTPUT) + retire orphan stub-regression tests + verify shell.html nav-link
**UI hint**: yes

**Phase 12 reconciliation**: With FB-D landing, the standalone Phase 12 "LLM Chat" is
redundant. Phase 12 already marked Superseded in the progress table at v1.3 close
(2026-04-24).

---

### Phase 16.1 (FB-D gap closure): Chat Tool-List Hang + Wiring Regression Guards (INSERTED)

**Goal**: The CHAT-04 fresh-operator artist UAT actually completes on assist-01 — an artist asks "what synthesis tools were created this week?" in the Web UI chat panel against live `qwen2.5-coder:32b` and receives a useful, plain-English answer within <60s. The 49-tool `complete_with_tools()` hang is bisected and fixed via a tool-list scoping policy for chat; boot-time regression guard prevents LLMRouter wiring drift; deprecated `TemplateResponse(name, ctx)` callers are migrated so the `starlette<0.53` pin can be dropped; an integration-style test exercises the full chat → MCP tool registry → live Ollama path so this class of gap can't reach a deploy again.

**Depends on**: Phase 16 (FB-D) (the shipped chat endpoint surface; 16.1 patches it, doesn't replace it)
**Inserted**: 2026-04-27 after Phase 16's CHAT-04 deploy UAT FAIL on assist-01 (three Phase-16 wiring/integration bugs surfaced; Bugs A and B patched inline this session, Bug C is structural and routes here per Phase 10/10.1 precedent)
**Plans**: 5 plans across 3 waves (planned 2026-04-27 — execute in dependency order)
  - Wave 1 (parallel — three independent fixes, zero file overlap):
    - [ ] `16.1-01-PLAN.md` — Backend-aware tool-list filter (D-01/D-02): `_tool_filter.py` + chat_handler integration + log fields + filter unit test (covers ROADMAP §16.1 SC-2 partial)
    - [ ] `16.1-02-PLAN.md` — TemplateResponse migration (D-09/D-10): UI-render guard FIRST + 13 mechanical migrations + drop `starlette<0.53` pin (covers SC-5)
    - [ ] `16.1-03-PLAN.md` — Boot-wiring guard (D-07 #1): `_canonical_console_read_api` global + `_lifespan` smoke test (covers SC-3)
  - Wave 2 (depends on 16.1-01):
    - [ ] `16.1-04-PLAN.md` — Bisection sweep + Strategy B chat E2E (D-04/D-06/D-07 #3): `test_chat_tool_list_threshold.py` + `test_chat_endpoint_live.py` + `16.1-BISECTION.jsonl` (covers SC-1, SC-4, SC-2 final)
  - Wave 3 (depends on 16.1-01..04):
    - [ ] `16.1-05-PLAN.md` — Fresh-operator re-UAT (D-11..D-15): deploy + assist-01 pre-flight + canonical CHAT-04 prompt + `16.1-HUMAN-UAT.md` outcome (covers SC-6)

**Requirements**: CHAT-04 (re-verifies the v1.4 must-have that failed in deploy)

**Success Criteria** (what must be TRUE):
  1. Tool-list bisection produces a deterministic data point: at what tool count (or which specific tool) does `complete_with_tools()` against live `qwen2.5-coder:32b` on assist-01 tip from "fast" (1–10s) to "hangs the full 120s budget with `prompt_tokens_total=0`"? The bisection is captured in a synthetic-test artifact that future regressions can rerun.
  2. Chat tool-list scoping policy is implemented per the G-1 decision driven through `/gsd-discuss-phase 16.1` (backend-aware filtering vs. static "core" set vs. LLM-assisted routing vs. hard cap — the discuss-phase agent picks one). After the policy ships, `chat_handler` against the full real `mcp.list_tools()` registry returns a useful response on assist-01 within `<60s`, not the 120s `loop_budget_exceeded` hang.
  3. Boot-time regression guard exists: a TestClient + `_lifespan` smoke test asserts `app.state.console_read_api._llm_router is not None` after boot. Single test, ~10 LOC. This catches the Bug B class of "ConsoleReadAPI constructed without `llm_router=`" silently breaking chat.
  4. Strategy B integration test (`FB_INTEGRATION_TESTS=1` gated) exercises `chat_handler` end-to-end with the real `mcp.list_tools()` registry plus live Ollama, asserts a useful response within budget, and is wired into the documented integration-test invocation. Mocked-router-only coverage missed all three Bug A/B/C deploy bugs — this gate plugs that hole for the chat surface.
  5. `TemplateResponse` migration: all `forge_bridge/console/ui_handlers.py` callers move from the deprecated `TemplateResponse(name, ctx)` signature to `TemplateResponse(request, name, ctx)`. The `starlette<0.53` pin in `pyproject.toml` is dropped once the migration verifies green. (~8 mechanical sites; could be one plan within 16.1 or split out — discuss-phase decides.)
  6. CHAT-04 re-UAT runs on assist-01 with a fresh operator (not `CN/dev`) and records a `PASS` outcome in `.planning/phases/16.1-fb-d-chat-gap-closure/16.1-HUMAN-UAT.md`. Exit criteria: same as Phase 16's CHAT-04 success criterion 4 — useful plain-English answer within <60s for the canonical "what synthesis tools were created this week?" prompt, no error banner, no timeout, no rate-limit fallback.

**Canonical refs**: `.planning/phases/16-fb-d-chat-endpoint/16.1-CONTEXT-PREVIEW.md` (orchestrator handoff with full diagnostic chain, hypotheses, suggested phase shape — this is the discuss-phase entry point), `.planning/phases/16-fb-d-chat-endpoint/16-HUMAN-UAT.md` (the FAIL record), `.planning/phases/16-fb-d-chat-endpoint/16-VERIFICATION.md` Post-Verification Discovery section (full bug A/B/C disposition)

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
