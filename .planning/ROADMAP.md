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

- [ ] **Phase 13 (FB-A): Staged Operation Entity & Lifecycle** — `entity_type='staged_operation'` with proposed→approved→executed/rejected/failed state machine + `DBEvent` audit trail per transition
- [ ] **Phase 14 (FB-B): Staged Ops MCP Tools + Read API** — `forge_list/get/approve/reject_staged` MCP tools + `/api/v1/staged/*` HTTP routes + `forge://staged/pending` resource via single `ConsoleReadAPI` facade
- [ ] **Phase 15 (FB-C): LLMRouter Tool-Call Loop** — `complete_with_tools()` agentic coordinator + thin Anthropic + Ollama adapters; iteration cap (default 8) + wall-clock cap (default 120s); repeat-call detection, 8 KB result cap, sanitization boundary, recursive-synthesis guard
- [ ] **Phase 16 (FB-D): Chat Endpoint** — `/api/v1/chat` over `complete_with_tools()` with rate limiting, sanitization end-to-end, single chat surface for Web UI + projekt-forge Flame hooks (absorbs superseded Phase 12)

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
**Plans**: TBD — `/gsd-discuss-phase 14` next (alias `FB-B`)

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
**Plans**: TBD — `/gsd-discuss-phase 15` next (alias `FB-C`)

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
**Plans**: TBD — `/gsd-discuss-phase 16` next (alias `FB-D`)
**UI hint**: yes

**Phase 12 reconciliation**: With FB-D landing, the standalone Phase 12 "LLM Chat" is
redundant. Phase 12 already marked Superseded in the progress table at v1.3 close
(2026-04-24).

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
| 13 (FB-A). Staged Operation Entity & Lifecycle | v1.4 | 3/4 | In Progress|  |
| 14 (FB-B). Staged Ops MCP Tools + Read API | v1.4 | 0/? | Open | - |
| 15 (FB-C). LLMRouter Tool-Call Loop | v1.4 | 0/? | Open | - |
| 16 (FB-D). Chat Endpoint | v1.4 | 0/? | Open | - |
