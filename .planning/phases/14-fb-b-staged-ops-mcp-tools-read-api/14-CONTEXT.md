# Phase 14 (FB-B): Staged Ops MCP Tools + Read API — Context

**Gathered:** 2026-04-25
**Status:** Ready for planning
**Aliases:** FB-B (canonical cross-repo identifier per projekt-forge v1.5 dependency contract); `14` is the gsd-tooling numeric ID.

<domain>
## Phase Boundary

External read/write surface for the `staged_operation` entity shipped in Phase 13 (FB-A).
Three coordinated surfaces — MCP tools, HTTP routes, and one MCP resource — all
reading/writing through the existing single-facade pattern from Phase 9 (Read API
foundation). Approval is bookkeeping only: forge-bridge persists the lifecycle
transition and emits a `staged.approved` `DBEvent`; the proposer (projekt-forge v1.5,
future Maya/editorial endpoints) subscribes to that event via the existing event bus
and executes against its own domain.

**Surfaces shipped:**
- MCP tools: `forge_list_staged`, `forge_get_staged`, `forge_approve_staged`, `forge_reject_staged`
- HTTP routes: `GET /api/v1/staged?status=...&limit=...&offset=...&project_id=...`,
  `POST /api/v1/staged/{id}/approve`, `POST /api/v1/staged/{id}/reject`
- MCP resource: `forge://staged/pending` (proposed-only snapshot)
- Tool fallback shim: `forge_staged_pending_read` (P-03 prevention for Cursor/Gemini CLI)

**Out of scope for this phase:**
- LLM tool-call loop that proposes operations (Phase 15 / FB-C)
- Chat endpoint (Phase 16 / FB-D)
- Caller-identity bucketing / structured auth (SEED-AUTH-V1.5)
- Reason capture on approve/reject (deferred — see SEED-STAGED-REASON-V1.5 below)
- Multi-status filter (`?status=proposed,approved`) — single-status v1.4
- `forge://staged/{status}` and `forge://staged/{id}` resource templates — not requested
- Bulk approve/reject — single-op only per FB-A deferred-ideas section

</domain>

<decisions>
## Implementation Decisions

### List Query Surface (STAGED-06)

- **D-01:** `forge_list_staged` and `GET /api/v1/staged` adopt Phase 9 pattern **verbatim**:
  - `?status=<single value>` — optional; valid values are `proposed | approved | rejected | executed | failed`. Default `None` = all statuses.
  - `?limit=N&offset=M` — default `limit=50`, max `500`, silently clamped per Phase 9 D-05.
  - `?project_id=<uuid>` — optional UUID filter.
  - Default ordering: `created_at DESC` (matches Phase 9 execs ordering).
  - Single-status only. Multi-status (`?status=proposed,approved`) is deferred — projekt-forge polls "pending now" or "my recent executed"; single-value covers both consumer needs.
  - **Why:** zero divergence from Phase 9; smallest surface for projekt-forge to learn; matches `_parse_pagination()` and `_parse_filters()` helpers in `forge_bridge/console/handlers.py` so the new staged handlers can reuse them.

- **D-02:** A new `StagedOpRepo.list(status, limit, offset, project_id)` method ships in this phase to back D-01. It performs the SQL filter + ordering + pagination directly (single SELECT against `entities` filtered by `entity_type='staged_operation'`). Returns `tuple[list[StagedOperation], int]` matching the `(records, total)` shape the existing `ExecutionLog.snapshot()` returns. Reason: the staged-ops repo stays the single read+write authority for the entity rather than reaching into `EntityRepo` from `ConsoleReadAPI`.

### Read/Write Facade Shape (Phase 9 D-25 invariant)

- **D-03:** `ConsoleReadAPI` is **extended** for reads — `session_factory` parameter added to `__init__`, plus two new methods:
  - `get_staged_ops(status, limit, offset, project_id) -> tuple[list[StagedOperation], int]` — opens a session per call, instantiates `StagedOpRepo`, returns the result of `repo.list(...)`.
  - `get_staged_op(op_id: uuid.UUID) -> StagedOperation | None` — same pattern; calls `repo.get(...)`.
  - **Why:** preserves the Phase 9 D-25 "single read facade for all surfaces" invariant. HTTP routes, MCP tools, and the `forge://staged/pending` resource all read through this facade. `_envelope_json` byte-identity (D-26) holds for free.

- **D-04:** **Writes do NOT go through `ConsoleReadAPI`.** HTTP write handlers (`/approve`, `/reject`) and MCP write tools (`forge_approve_staged`, `forge_reject_staged`) call `StagedOpRepo` directly via the same `session_factory`:
  ```python
  async with session_factory() as session:
      repo = StagedOpRepo(session)
      op = await repo.approve(op_id, approver=actor)
      await session.commit()  # handler owns the txn boundary per FB-A repo contract
      return op.to_dict()
  ```
  - No `ConsoleWriteAPI` sibling class — ceremony with one consumer. `StagedOpRepo` IS the sanctioned write contract per FB-A D-08; the handler's job is just to translate from HTTP/MCP request envelopes into repo calls and back.
  - **Why:** keeps `ConsoleReadAPI` honest to its name; respects FB-A's "all writers through `StagedOpRepo`" rule; avoids inventing a write-facade abstraction for a single consumer.

- **D-05:** `session_factory` injection plumbing: the canonical `_lifespan` startup path that already constructs `ConsoleReadAPI` (Phase 9 P9-2) gains a `session_factory` parameter. The factory is built from the existing `forge_bridge/store/session.py` module (whatever the existing v1.3 wiring uses for read access — planning verifies and reuses, no new module). The factory is also passed into `register_console_resources()` so the resource and tool-shim closures can call into write paths if needed (they don't in v1.4 — STAGED-07 is read-only).

### Actor Identity Sourcing (FB-A D-11/D-12 placeholder)

- **D-06:** HTTP `POST /staged/{id}/approve` and `POST /staged/{id}/reject` resolve actor in this priority order:
  1. `X-Forge-Actor` request header (preferred)
  2. JSON body field `{"actor": "..."}`
  3. Default fallback: `"http:anonymous"`
  - Empty string in either source is rejected with HTTP 400 `bad_actor`.
  - Any non-empty string accepted (no format validation) per FB-A D-12.

- **D-07:** MCP tools `forge_approve_staged` and `forge_reject_staged` require `actor` as a **non-defaulted Pydantic field** — no fallback, no implicit identity. Empty string raises a Pydantic validation error (which FastMCP surfaces as a tool error). MCP clients always have an identity context (Claude Code, Cursor, Web UI); forcing the caller to be explicit prevents silent attribution drift.

- **D-08:** Sample actor strings the v1.4 ecosystem will use (no enum, free-string per FB-A D-11):
  - `"web-ui:anonymous"` — Web UI chat panel approval (FB-D consumer)
  - `"projekt-forge:flame-a"` — projekt-forge v1.5 Flame hooks
  - `"mcp:claude-code"` — Claude Code MCP session
  - `"http:anonymous"` — direct curl / unattributed HTTP caller (D-06 default)
  - v1.5 SEED-AUTH replaces this freeform space with a structured form.

### Idempotency on Approve/Reject

- **D-09:** **Strict 409 on illegal transitions — no idempotent 200.** Re-approving an already-approved op returns:
  ```json
  {
    "error": {
      "code": "illegal_transition",
      "message": "Illegal transition from 'approved' to 'approved' for staged_operation {id}",
      "current_status": "approved"
    }
  }
  ```
  HTTP status 409 Conflict. MCP tool error body uses the same JSON envelope.
  - **Why:** FB-A's `StagedOpRepo._transition()` raises `StagedOpLifecycleError` BEFORE any DB write — the audit log NEVER records the duplicate attempt. Silently swallowing retries via 200 would hide programmer errors from the only place that could surface them. Returning the current status in the error payload lets retry logic self-correct without an extra GET.
  - The error envelope's `current_status` field is an FB-B addition on top of the standard `{code, message}` shape — same envelope shape, one extra field on the lifecycle case.

### HTTP / MCP Error Code Mapping

- **D-10:** Lock the error mapping table:

  | Cause | HTTP Status | `error.code` | Notes |
  |---|---|---|---|
  | `StagedOpLifecycleError` (op exists, illegal transition) | 409 | `illegal_transition` | Includes `current_status` field |
  | Op not found (UUID resolves to nothing or to a non-staged entity_type) | 404 | `staged_op_not_found` | Message: `"no staged_operation with id {id}"` |
  | Malformed UUID in path or query | 400 | `bad_request` | Message: `"invalid staged_operation id"` |
  | Unknown `?status=` value | 400 | `invalid_filter` | Message lists allowed values |
  | Empty actor (HTTP only — header empty AND body missing AND fallback rejected by D-06) | 400 | `bad_actor` | This is structurally impossible given D-06's fallback; only fires if the operator explicitly passes an empty string in header or body. |
  | DB / unexpected exception | 500 | `internal_error` | Generic message; log internally with `type(exc).__name__` per Phase 8 LRN — never leak `str(exc)` (credentials hygiene). |

- **D-11:** MCP tool / resource error bodies use `_envelope_json` with the same `{"error": {"code", "message", ...}}` shape — byte-identical to HTTP. Reuse `forge_bridge/console/handlers.py::_error()` and `_envelope_json()` helpers. No new envelope module.

### Resource Template Scope (STAGED-07)

- **D-12:** Ship **only** the minimum required by STAGED-07: `forge://staged/pending` (proposed-only snapshot) plus the tool fallback shim `forge_staged_pending_read` (P-03 prevention for Cursor/Gemini CLI per STATE.md key constraints).
- **D-13:** Resource body equals `forge_list_staged(status='proposed', limit=500, offset=0)` output verbatim — guarantees the success criterion #3 byte-identity property between the tool result and the resource snapshot. Hardcoded `limit=500` (the max) gives the largest reasonable snapshot in one read; if the pending queue ever exceeds 500 staged ops, that's a v1.5 problem (and a SEED-AUTH-V1.5 caller-identity-bucketing problem first).
- **D-14:** **NOT shipping in v1.4:**
  - `forge://staged/{status}` resource template — the MCP tool already filters by status; per-status resource is duplicative.
  - `forge://staged/{id}` resource template — `forge_get_staged(id)` covers single-op lookup.
  - These can be added in a future phase if a consumer asks; deferring keeps the public resource surface tight.

### Tool Naming & Input Shapes

- **D-15:** Tool names and Pydantic input model names are locked:
  ```python
  class ListStagedInput(BaseModel):
      status: Optional[str] = None
      limit: int = 50
      offset: int = 0
      project_id: Optional[str] = None

  class GetStagedInput(BaseModel):
      id: str  # UUID string; validated by repo, NOT pre-validated in Pydantic v1.4

  class ApproveStagedInput(BaseModel):
      id: str
      actor: str  # required, non-empty (D-07)

  class RejectStagedInput(BaseModel):
      id: str
      actor: str  # required, non-empty (D-07)
  ```
  Tool names: `forge_list_staged`, `forge_get_staged`, `forge_approve_staged`, `forge_reject_staged`.

- **D-16:** MCP tool annotations (FastMCP `annotations={...}`):
  - `forge_list_staged`, `forge_get_staged`, `forge_staged_pending_read`: `{"readOnlyHint": True, "idempotentHint": True}`
  - `forge_approve_staged`, `forge_reject_staged`: `{"readOnlyHint": False, "idempotentHint": False, "destructiveHint": False}` — they mutate state but do not delete; matches Phase 7 tool-provenance annotation conventions.

- **D-17:** Tool registration site is `forge_bridge/mcp/registry.py::register_builtins()` for the four `forge_*_staged` tools (alongside the existing `forge_list_*` / `forge_get_*` family). The `forge_staged_pending_read` shim and `forge://staged/pending` resource register from `forge_bridge/console/resources.py::register_console_resources()` (alongside the existing manifest/tools/health resources) so the closure can capture `console_read_api` directly. Two registration sites match the existing v1.3 split between "read-API tools" and "console-resource shims."

### Test Strategy

- **D-18:** STAGED-05 (MCP tools callable from a real session) — integration test under `tests/mcp/` that boots the FastMCP server, calls each of the four tools via `mcp.client`, and asserts the JSON payload matches `StagedOperation.to_dict()` + `status` field. Pattern follows the existing `tests/mcp/` conventions (verify in planning).
- **D-19:** STAGED-06 (HTTP routes + zero-divergence test) — under `tests/console/`:
  - `test_staged_handlers_list.py` — `?status=...`, pagination, ordering, `?project_id=...`, error cases.
  - `test_staged_handlers_writes.py` — approve/reject lifecycle, 409 on re-approve, 404 on unknown id, 400 on bad UUID/actor.
  - `test_staged_zero_divergence.py` — calls the MCP tool and the HTTP route with the same input, asserts `json.loads(tool_result) == http_response.json()` byte-identity. Exercises D-04, D-11, D-26.
- **D-20:** STAGED-07 (resource snapshot) — `tests/test_console_mcp_resources.py` extension: read `forge://staged/pending` and assert payload equals `forge_list_staged(status='proposed', limit=500)` result.
- **D-21:** Approval-does-NOT-execute test (success criterion #4) — unit test in `tests/store/test_staged_operations.py` (or under `tests/console/`): mock or assert no execution-side code path is reached during approval; `DBEvent` for `staged.approved` is emitted with the correct payload. The `StagedOpRepo` already enforces this (it never imports execution code); the test is a regression guard.

### Claude's Discretion

- Whether the staged-ops handlers live in a new `forge_bridge/console/staged_handlers.py` module or are appended to existing `handlers.py` (planning decides based on file size — `handlers.py` is at 171 lines; appending may be fine).
- Exact filename for the `StagedOpRepo.list()` extension — same module (`forge_bridge/store/staged_operations.py`) per FB-A's single-source-of-truth pattern, no new file.
- Whether the `tests/console/test_staged_*` tests share a fixture file (`conftest.py`) for the in-memory async session + StagedOpRepo setup, or each test bootstraps its own. FB-A's plan 13-04 already shipped a `session_factory` async-DB fixture — planning to reuse.
- Helper function placement for `_resolve_actor(request) -> str` (D-06) — likely a small helper in `forge_bridge/console/handlers.py` since it's HTTP-only and small.
- MCP tool function bodies' implementation pattern (e.g., whether they call into a shared `_handle_staged_action()` internal helper to dedupe HTTP and MCP write paths). Worth considering once the test suite shape is clearer.
- Whether the HTTP write routes use a request body parser (`await request.json()`) or query-string only for `actor` (D-06 covers both; planning picks the one that fits Phase 9 patterns best).

### Folded Todos

None — todo list was empty at phase open.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` §`Phase 14 (FB-B)` (lines 124–137) — phase goal, depends-on, success criteria, requirements mapping
- `.planning/REQUIREMENTS.md` §STAGED — STAGED-05/06/07 are this phase; STAGED-01..04 (FB-A) define the entity shape this phase serializes
- `.planning/STATE.md` — Key constraints section: ConsoleReadAPI single-facade rule, MFST-02/03 P-03 prevention pattern (apply to STAGED-05/07), uvicorn task pattern, instance-identity gate

### FB-A surfaces FB-B consumes (load-bearing)
- `forge_bridge/store/staged_operations.py` — `StagedOpRepo` (propose / get / approve / reject / execute / fail) and `StagedOpLifecycleError`. **D-02 adds `list()` here.**
- `forge_bridge/core/staged.py` — `StagedOperation.to_dict()` is the single source of truth for response shape (FB-A D-17)
- `forge_bridge/store/models.py` — `DBEntity`, `DBEvent`, `ENTITY_TYPES`, `EVENT_TYPES` (lines 207, 441), `staged_operation` (line 209), `staged.proposed/approved/rejected/executed/failed` (lines 462+)
- `forge_bridge/store/repo.py` — `EntityRepo` and `EventRepo` patterns; `StagedOpRepo.list()` (D-02) follows the existing repo idiom

### v1.3 Read API foundation FB-B extends
- `forge_bridge/console/read_api.py` — `ConsoleReadAPI` class (D-03 extends with `session_factory`, `get_staged_ops`, `get_staged_op`)
- `forge_bridge/console/handlers.py` — `_envelope`, `_envelope_json`, `_error`, `_parse_pagination`, `_parse_filters` helpers — D-01, D-09, D-10, D-11 reuse all of these
- `forge_bridge/console/app.py` — `build_console_app()` route registration (lines 63–87); D-04 adds three new routes here
- `forge_bridge/console/resources.py` — `register_console_resources()` pattern (lines 29–114); D-12, D-17 follow it for `forge://staged/pending` + `forge_staged_pending_read`
- `forge_bridge/mcp/registry.py` — `register_builtins()` (line 172); D-17 registers four new `forge_*_staged` tools alongside existing `forge_list_*` family
- `forge_bridge/mcp/tools.py` — existing tool function shape (Pydantic input model + async function returning `_ok(data)`); D-15 follows this convention

### Phase 13 prior context (decisions inherited)
- `.planning/phases/13-fb-a-staged-operation-entity-lifecycle/13-CONTEXT.md` — FB-A decisions D-01..D-22; especially D-08 (StagedOpRepo is the single sanctioned writer), D-09 (StagedOpLifecycleError translation contract), D-11/D-12 (free-string actor format), D-17 (`StagedOperation.to_dict()` shape)
- `.planning/phases/13-fb-a-staged-operation-entity-lifecycle/13-VERIFICATION.md` — verifies the shipped FB-A surface matches the contract this phase consumes
- `.planning/phases/13-fb-a-staged-operation-entity-lifecycle/13-PATTERNS.md` — Finding #5/#7 (subclass `Exception` directly), #8 (compose EventRepo, never bypass with `session.add(DBEvent)`)

### Phase 9 prior context (Read API foundation patterns)
- `.planning/phases/09-*/09-CONTEXT.md` (or equivalent — find via `ls .planning/phases | grep 09`) — D-01 envelope, D-05 pagination clamp, D-25 single-read-facade invariant, D-26 byte-identity contract
- `tests/test_console_mcp_resources.py` — D-26 byte-identity test pattern; D-19 (zero-divergence test) follows it

### Project vocabulary and architecture
- `docs/VOCABULARY.md` — staged_operation entity is part of the canonical vocabulary FB-A added; FB-B is the surface that exposes it
- `docs/ARCHITECTURE.md` — event-driven, append-only events; the `staged.approved` subscription contract for projekt-forge consumers
- `docs/API.md` — HTTP surface conventions for forge-bridge

### Codebase intel
- `.planning/codebase/STRUCTURE.md` — directory layout
- `.planning/codebase/CONVENTIONS.md` — naming patterns, import order, error envelope conventions
- `.planning/codebase/TESTING.md` — test conventions for D-18..D-21

### Forward-looking
- `.planning/seeds/SEED-AUTH-V1.5.md` — actor identity migration (D-06/D-07 are v1.4 placeholders)
- `.planning/seeds/SEED-STAGED-REASON-V1.5.md` — **NEW seed to plant** for approval/reject reason capture deferred from this phase

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`ConsoleReadAPI`** (`forge_bridge/console/read_api.py:73`) — extend with `session_factory` + two new methods (D-03). The constructor's `flame_bridge_url` / `ws_bridge_url` plumbing is the model for `session_factory` injection.
- **`_envelope`, `_envelope_json`, `_error`** (`forge_bridge/console/handlers.py:43-60`) — D-09, D-10, D-11 reuse all three. Byte-identity (D-26) is preserved automatically.
- **`_parse_pagination`, `_parse_filters`** (`forge_bridge/console/handlers.py:65-100`) — D-01 reuses verbatim. The `since` and `promoted_only` filters don't apply to staged ops; the new staged handlers use a thinner version that only parses status/project_id/pagination.
- **`StagedOpRepo`** (`forge_bridge/store/staged_operations.py:90`) — add `list()` method per D-02. All four lifecycle transitions (`approve`, `reject`, `execute`, `fail`) already raise `StagedOpLifecycleError` on illegal/idempotent transitions per FB-A D-10.
- **`StagedOperation.to_dict()`** (`forge_bridge/core/staged.py:86`) — the only serialization path FB-B uses. FB-A guarantees this is the single source of truth.
- **`register_console_resources`** (`forge_bridge/console/resources.py:29`) — pattern for D-12 (`forge://staged/pending` + `forge_staged_pending_read`).
- **`register_builtins`** (`forge_bridge/mcp/registry.py:172`) — pattern for D-17 (four new MCP tools).
- **Phase 9 tests** (`tests/console/test_*.py`, `tests/test_console_mcp_resources.py`) — D-18, D-19, D-20 fixtures and assertions.
- **Phase 13 session_factory fixture** (`tests/store/conftest.py` or equivalent — Plan 13-04 deliverable) — D-19 reuses for handler integration tests.

### Established Patterns
- **Single read facade rule** (Phase 9 D-25) — every read surface goes through `ConsoleReadAPI`.
- **Byte-identity contract** (Phase 9 D-26) — every surface returns the same bytes via `_envelope_json`.
- **Pagination clamp** (Phase 9 D-05) — limit default 50, max 500, silently clamped at the parse boundary.
- **Tool fallback shim alongside resource** (Phase 9 MFST-02/03, P-03 prevention) — every MCP resource ships with a tool alias for clients without resources support.
- **Repo as single write authority** (FB-A D-08) — handlers/tools call `StagedOpRepo`, never `session.add(DBEntity(entity_type='staged_operation'))`.
- **EventRepo composition** (FB-A PATTERNS.md Finding #8) — `StagedOpRepo` already composes `EventRepo`; FB-B handlers do NOT touch events directly.
- **Error mapping** — Phase 9 uses code strings like `tool_not_found`, `internal_error`, `bad_request`, `not_implemented`. D-10 extends with `illegal_transition`, `staged_op_not_found`, `invalid_filter`, `bad_actor`.
- **Free-string actor identity** (FB-A D-11/D-12) — D-06/D-07 source the string from headers/body/Pydantic; v1.4 accepts any non-empty string.

### Integration Points
- **`forge_bridge/console/read_api.py::ConsoleReadAPI.__init__`** — add `session_factory` parameter (D-03, D-05).
- **`forge_bridge/console/read_api.py`** — add `get_staged_ops()` and `get_staged_op()` methods (D-03).
- **`forge_bridge/console/handlers.py`** — add `staged_list_handler`, `staged_approve_handler`, `staged_reject_handler` (D-04). Reuse all envelope/parser helpers.
- **`forge_bridge/console/app.py::build_console_app`** — add three routes (D-04):
  - `Route("/api/v1/staged", staged_list_handler, methods=["GET"])`
  - `Route("/api/v1/staged/{id}/approve", staged_approve_handler, methods=["POST"])`
  - `Route("/api/v1/staged/{id}/reject", staged_reject_handler, methods=["POST"])`
- **`forge_bridge/console/resources.py::register_console_resources`** — add `forge://staged/pending` resource and `forge_staged_pending_read` tool shim (D-12, D-17).
- **`forge_bridge/mcp/registry.py::register_builtins`** — register four new MCP tools (D-17).
- **`forge_bridge/mcp/tools.py`** — add four new tool functions: `list_staged`, `get_staged`, `approve_staged`, `reject_staged` plus their Pydantic input models (D-15).
- **`forge_bridge/store/staged_operations.py::StagedOpRepo`** — add `list()` method (D-02).
- **`forge_bridge/_lifespan` (or wherever Phase 9 wires `ConsoleReadAPI`)** — pass `session_factory` to the constructor (D-05).
- **Tests:**
  - `tests/store/test_staged_operations_list.py` (or extend FB-A's test file) — D-02 unit tests
  - `tests/mcp/test_staged_tools.py` — D-18 MCP tool integration
  - `tests/console/test_staged_handlers.py` — D-19 HTTP handler tests
  - `tests/console/test_staged_zero_divergence.py` — D-19 byte-identity
  - `tests/test_console_mcp_resources.py` (extension) — D-20 resource snapshot

### What FB-C and FB-D Will Consume From This Phase
- `forge_list_staged` / `forge_get_staged` MCP tools — registered in the manifest, become available to FB-C's tool-call loop and FB-D's chat endpoint context assembly.
- `GET /api/v1/staged?status=proposed` HTTP route — projekt-forge v1.5 polls this when its event-bus subscription misses a `staged.approved` event (resync path).
- `forge://staged/pending` MCP resource — Cursor / Web UI chat panel surfaces "ops awaiting your approval" without a tool call.
- The actor-identity sourcing decision (D-06/D-07) is the v1.4 placeholder; SEED-AUTH-V1.5 will replace the resolution helper without changing the API surface.

</code_context>

<specifics>
## Specific Ideas

- **API-first, not API-then-CLI:** FB-B intentionally ships zero CLI surface. Phase 11's CLI Companion shipped exec/manifest/tool browsing; staged-ops CLI is deferred to v1.4.x or later (the Web UI chat panel + projekt-forge's own surface cover the immediate v1.4 need). Adding `staged` CLI subcommands later is mechanical once the HTTP route is locked.
- **No new auth, no new envelope module, no new test harness.** FB-B is a "wire it up using v1.3's primitives" phase — every new piece of code is a thin layer on top of existing Phase 9 / Phase 13 infrastructure. The discussion deliberately did not generate any "let's invent a new abstraction" decisions.
- **Subscription contract for projekt-forge v1.5 (carried from FB-A):** the `staged.approved` event is the trigger. projekt-forge subscribes via the existing event bus, reads `entity_id` + `payload.operation` + `attributes.parameters` (via `forge_get_staged` from FB-B), executes against Flame, then writes back via `forge_register_publish` (existing) or by calling FB-B's `POST /api/v1/staged/{id}/approve` follow-up to mark `executed`/`failed`.

   Wait — the lifecycle is `proposed → approved → executed`. After projekt-forge executes, it needs to mark the op `executed`. FB-B does NOT ship a `POST /staged/{id}/execute` route or a `forge_execute_staged` tool. **Re-reading STAGED-05..07: only approve/reject are required.** The `execute` and `fail` transitions are FB-A repo methods, not v1.4 surface.

   This means projekt-forge writes the executed/failed transition by calling `StagedOpRepo` directly (it has its own `forge-bridge` Python install — pip dep). Or it doesn't, and v1.4 stops at `approved` (the operation runs, the result lives in projekt-forge's domain, and the staged_operation row stays at `approved` forever). The latter is fine for v1.4 — the audit log captures who approved what; closure to `executed` is a v1.5 nicety.

   **Lock this:** v1.4 surfaces approve/reject only. `executed`/`failed` are FB-A repo methods that may be called by projekt-forge directly via the Python API, OR may stay un-called in v1.4 (ops sit at `approved` indefinitely and projekt-forge's own DB tracks completion). NOT FB-B scope.

</specifics>

<deferred>
## Deferred Ideas

- **`POST /api/v1/staged/{id}/execute` and `POST /api/v1/staged/{id}/fail` routes** — v1.5 closure for the lifecycle. FB-A's `StagedOpRepo.execute` and `StagedOpRepo.fail` ship; the HTTP/MCP surface for them is deferred. Tracking: `SEED-STAGED-CLOSURE-V1.5.md` (plant during planning).
- **Approval / reject reason capture** — `attributes.approve_reason` / `attributes.reject_reason` free-text field. Tracking: `SEED-STAGED-REASON-V1.5.md` (plant during planning).
- **Multi-status filter (`?status=proposed,approved`)** — single-status is enough for v1.4 consumers; multi-status is a v1.5 "give me my queue + my recent decisions" UX nicety.
- **Resource templates `forge://staged/{status}` and `forge://staged/{id}`** — MCP tools cover the equivalent query shapes; templates are deferred until a consumer asks (see D-14).
- **Bulk approve/reject endpoints** — out of scope; v1.4 ships per-op only. Carried forward from FB-A's deferred-ideas list.
- **Caller-identity bucketing for actors** — SEED-AUTH-V1.5; v1.4 uses free strings (D-06/D-07 are the placeholder).
- **`staged` CLI subcommands** — Phase 11 CLI Companion shipped exec/manifest/tools browsing; staged-ops CLI is deferred to v1.4.x patch milestone or later.
- **Pagination cursor / `?after=<id>` keyset pagination** — limit/offset is enough for v1.4 staged-ops volumes (expected dozens/day, not millions); cursor pagination is a v1.5+ scaling concern.

### Reviewed Todos (not folded)
None — todo list was empty at phase open.

</deferred>

---

*Phase: 14-fb-b-staged-ops-mcp-tools-read-api*
*Context gathered: 2026-04-25*
