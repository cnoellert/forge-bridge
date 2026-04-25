# Roadmap: forge-bridge

## Milestones

- ✅ **v1.0 Canonical Package & Learning Pipeline** — Phases 1-3 (shipped 2026-04-15)
- ✅ **v1.1 projekt-forge Integration** — Phases 4-6 (shipped 2026-04-19 — v1.1.0 API release, v1.1.1 PATCH-01)
- ✅ **v1.2 Observability & Provenance** — Phases 7, 07.1, 8 (shipped 2026-04-22 — v1.2.0, v1.2.1 hotfix, v1.3.0)
- ✅ **v1.3 Artist Console** — Phases 9, 10, 10.1, 11 (shipped 2026-04-25 — v1.3.1; Phase 12 superseded by v1.4 FB-D)
- 📐 **v1.4 Staged Ops Platform** — Phases FB-A..FB-D (proposed 2026-04-23 — consumed by projekt-forge v1.5)

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

## Phase Details


### 📐 v1.4 Staged Ops Platform (Phases FB-A..FB-D)

**Milestone Goal**: Extend forge-bridge with the human-in-the-loop primitives that
projekt-forge v1.5 needs to become a thin Flame-side consumer: a `staged_operation` entity
with a proposed→approved→executed lifecycle, MCP + HTTP surface for list/approve/reject,
an agentic `complete_with_tools()` method on LLMRouter, and a chat endpoint that binds it
all together for both the Web UI (Phase 10) and external Flame hooks.

**Proposed 2026-04-23** after projekt-forge ROADMAP restructure audit. Each FB phase maps
directly to a dependency projekt-forge v1.5 has declared. (projekt-forge v1.4 is Editorial
Operations — Flame-side work independent of forge-bridge, sequenced ahead of the consumer
milestone so Flame-side velocity is not gated on upstream platform work.)

---

### Phase FB-A: Staged Operation Entity & Lifecycle
**Goal**: A new `staged_operation` entity type participates in the existing extensible
entity model with a full proposed→approved→executed/rejected/failed lifecycle enforced
in the data layer. Every transition emits a `DBEvent` for audit. Stores proposer identity,
operation name, proposed parameters (JSONB), realized result diff (JSONB), and timing.
**Depends on**: Phase 8 (SQL persistence), Phase 9 (Read API + event surface)
**Requirements**: STAGED-01, STAGED-02, STAGED-03, STAGED-04
**Success Criteria** (what must be TRUE):
  1. `entity_type='staged_operation'` entities can be created via the store layer with `proposer`, `operation`, `parameters` (JSONB), and initial `status='proposed'` — verified via a direct SQLAlchemy round-trip test.
  2. Lifecycle transitions are enforced: `proposed → approved → executed` (happy path), `proposed → rejected` (artist veto), `approved → failed` (execution error). Illegal transitions (e.g., `executed → proposed`) raise `StagedOpLifecycleError`.
  3. Every transition writes a `DBEvent` row with the old and new status, the actor (proposer vs approver), and a timestamp — queryable by `entity_id` for full audit replay.
  4. The `parameters` JSONB at `status='proposed'` is preserved verbatim when `status` advances; the `result` JSONB is populated only on `executed` or `failed`. A diff of `parameters` vs `result` is recoverable per operation.
**Plans**: TBD

---

### Phase FB-B: Staged Ops MCP Tools + Read API
**Goal**: MCP and HTTP surface for external clients (projekt-forge, Claude Code, Web UI)
to list, fetch, approve, and reject staged operations. `forge://staged/...` MCP resources
mirror HTTP endpoints; the same `ConsoleReadAPI` facade serves both.
**Depends on**: Phase FB-A (entity + lifecycle), Phase 9 (Read API foundation), Phase 10 (Web UI — consumer reference)
**Requirements**: STAGED-05, STAGED-06, STAGED-07
**Success Criteria** (what must be TRUE):
  1. MCP tools `forge_list_staged`, `forge_get_staged`, `forge_approve_staged`, `forge_reject_staged` are registered and callable from a real MCP session; each returns a JSON payload that matches the shape defined in FB-A.
  2. `GET /api/v1/staged?status=proposed` returns all pending operations; `POST /api/v1/staged/{id}/approve` and `POST /api/v1/staged/{id}/reject` transition lifecycle and return the updated record — same data as the MCP tools (zero divergence).
  3. `resources/read forge://staged/pending` returns a snapshot of pending operations identical to the MCP tool output.
  4. Approval does NOT execute the operation itself — forge-bridge is the bookkeeper; the proposer (e.g., projekt-forge) subscribes to approval events and executes against its own domain (Flame).
**Plans**: TBD

---

### Phase FB-C: LLMRouter Tool-Call Loop
**Goal**: `LLMRouter.complete_with_tools(prompt, tools, context, sensitive=...)` runs the
full agentic loop — send prompt + tool schemas, parse `tool_call`, execute each tool against
the registered MCP tools in-process, feed result back, repeat until the LLM returns a
terminal response. Sensitive routing preserved. Anthropic + Ollama both supported via their
native tool-call formats.
**Depends on**: Phase 1 (LLMRouter), Phase 7 (tool provenance — tools expose schemas)
**Requirements**: LLMTOOL-01, LLMTOOL-02, LLMTOOL-03
**Success Criteria** (what must be TRUE):
  1. `router.complete_with_tools(prompt, tools=[...], sensitive=True)` completes a two-step loop (LLM calls tool A, receives result, returns final response) against a real Ollama backend — verified in an integration test.
  2. Cloud path (Anthropic) produces the same terminal response for the same prompt + tool schemas — verified against live API with `ANTHROPIC_API_KEY` set. Sensitive routing logic (`sensitive=True → local`) still enforced.
  3. A tool invocation failure (raised exception, timeout, schema mismatch) is caught, surfaced back to the LLM as a structured error message, and the loop continues — one bad tool doesn't abort the session.
  4. The loop has a hard iteration cap (default 8) and a total wall-clock cap (default 120s) — infinite tool-call cycles terminate with a clear `LLMLoopBudgetExceeded`.
**Plans**: TBD

---

### Phase FB-D: Chat Endpoint (merges with Phase 12)
**Goal**: `/api/v1/chat` exposes `complete_with_tools()` over HTTP with sanitized context
assembly, token-budget cap, and rate limiting. Consumed by the Web UI chat panel (Phase 10)
and by external Flame hooks (projekt-forge Phase 22/23). This phase absorbs the previously
velocity-gated Phase 12 "LLM Chat" scope — it is no longer deferrable once FB-C lands.
**Depends on**: Phase FB-C (tool-call loop), Phase 10 (Web UI consumer), Phase 9 (Read API host)
**Requirements**: CHAT-01, CHAT-02, CHAT-03, CHAT-04 (inherited from Phase 12)
**Success Criteria** (what must be TRUE):
  1. Eleven rapid requests from the same IP within one minute: the eleventh returns HTTP 429 with a clear "rate limit exceeded" message — cost cap enforced.
  2. An `acomplete_with_tools()` call that blocks indefinitely causes the endpoint to return a timeout error within 125 seconds — no hung requests.
  3. A tool whose sidecar name or parameters contain an injection marker (e.g., `IGNORE PREVIOUS INSTRUCTIONS`) does not propagate that string into the LLM context — sanitization boundary holds.
  4. Non-developer dogfood: an artist asks "what synthesis tools were created this week?" in the Web UI chat panel and receives a useful, plain-English answer within the LLM's normal response time.
  5. Same endpoint serves projekt-forge Flame hooks with zero divergence in behavior or context assembly — one chat surface, multiple clients.
**Plans**: TBD

**Phase 12 reconciliation**: With FB-D landing, the standalone Phase 12 "LLM Chat" is
redundant. On FB-D ship, mark Phase 12 as superseded in the progress table.

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
| 12. LLM Chat | v1.3 | 0/? | Superseded by FB-D (velocity gate triggered) | - |
| FB-A. Staged Operation Entity & Lifecycle | v1.4 | 0/? | Designed | - |
| FB-B. Staged Ops MCP Tools + Read API | v1.4 | 0/? | Designed | - |
| FB-C. LLMRouter Tool-Call Loop | v1.4 | 0/? | Designed | - |
| FB-D. Chat Endpoint | v1.4 | 0/? | Designed | - |
