# Phase 13 (FB-A): Staged Operation Entity & Lifecycle — Context

**Gathered:** 2026-04-25
**Status:** Ready for planning
**Aliases:** FB-A (canonical cross-repo identifier per projekt-forge v1.5 dependency contract); `13` is the gsd-tooling numeric ID.

<domain>
## Phase Boundary

A new `entity_type='staged_operation'` joins the existing single-table polymorphic
entity model. It carries a `proposed → approved → executed/rejected/failed` state
machine enforced in the repo/application layer. Every transition writes a `DBEvent`
for full audit replay. forge-bridge is the **bookkeeper** — it persists the proposed
operation, its approval state, and the realized result; it does NOT execute the
operation. The proposer (projekt-forge v1.5, future Maya/editorial endpoints) subscribes
to approval events via the existing event bus and executes against its own domain.

**Out of scope for this phase:** the MCP/HTTP surface (Phase 14, FB-B), the LLM tool-call
loop that proposes operations (Phase 15, FB-C), the chat endpoint (Phase 16, FB-D), and
any caller-identity bucketing (SEED-AUTH-V1.5).

</domain>

<decisions>
## Implementation Decisions

### Storage Shape
- **D-01:** `parameters` and `result` JSONB live as sub-keys inside the existing `DBEntity.attributes` JSONB column. **Why:** Consistent with `version`/`media`/`shot`/`asset` attribute conventions. Single GIN index (`ix_entities_attributes`) already covers JSONB containment queries. Lowest schema disruption — no new columns, no new table. STAGED-04's "diff via SQL alone" satisfied by `SELECT attributes->'parameters', attributes->'result' FROM entities WHERE entity_type='staged_operation' AND id=?`.
- **D-02:** `attributes` shape for staged_operation:
  ```jsonc
  {
    "proposer":   "<free-string actor>",   // who proposed (D-04)
    "operation":  "<operation name>",      // e.g. "flame.publish_sequence"
    "parameters": { ... },                 // proposed args (immutable after creation)
    "result":     { ... } | null,          // populated on executed/failed only (D-05)
    "approver":   "<free-string actor>" | null,  // populated on approved
    "executor":   "<free-string actor>" | null,  // populated on executed/failed
    "approved_at": "<ISO timestamp>" | null,
    "executed_at": "<ISO timestamp>" | null
  }
  ```
- **D-03:** `name` column on `DBEntity` carries the `operation` string (denormalized) so existing `ix_entities_type_name` index supports `WHERE entity_type='staged_operation' AND name='flame.publish_sequence'` queries without JSONB scan. `status` column carries the lifecycle state. `project_id` is nullable (operations can target a project but proposed-but-rejected ones may never bind to one).

### Event Vocabulary
- **D-06:** Five new specific event types added to `EVENT_TYPES` (in `forge_bridge/store/models.py`): `staged.proposed`, `staged.approved`, `staged.rejected`, `staged.executed`, `staged.failed`. **Why:** Matches the existing granular vocabulary (`version.published`, `media.ingested`, `entity.status_changed` is the only generic one and is poorly suited to subscriber-side filtering). FB-B's projekt-forge consumer subscribes to `staged.approved` specifically and executes — clean subscription contract; `ix_events_type_time` is the indexed query path.
- **D-07:** `DBEvent.payload` shape per transition:
  ```jsonc
  {
    "old_status": "<status before>",     // null for proposed
    "new_status": "<status after>",
    "actor":      "<free-string actor>",
    "operation":  "<operation name>",    // denormalized for search without join
    "transition_at": "<ISO timestamp>"
  }
  ```
  `entity_id` column on `DBEvent` (already indexed via `ix_events_entity_time`) carries the staged_operation's UUID. `client_name` carries the actor as well (existing convention) — same value as `payload.actor`, intentional duplication so existing event tooling that reads `client_name` works without payload inspection.

### Lifecycle Enforcement
- **D-08:** State machine lives in the **repo/application layer**, not the DB. A new `StagedOpRepo` (or methods on existing repo — to be decided in planning based on existing repo composition) owns the `(from_status, to_status)` transition map and raises `StagedOpLifecycleError` on illegal transitions. **Why:** Matches the established no-DB-level-rules pattern (no enum on `status`, no FKs in JSONB, no CHECK constraints on application data shape). Adding a CHECK constraint just for `staged_operation.status` would create an exception to the polymorphic invariant. All writers (FB-B MCP tools, FB-B HTTP routes, future projekt-forge integration) go through the repo — no bypass risk.
- **D-09:** `StagedOpLifecycleError` is a new exception class in `forge_bridge/store/` (or wherever the existing repo-layer errors live — planning decides). Message format: `"Illegal transition from '{from_status}' to '{to_status}' for staged_operation {id}"`. Not exported from `forge_bridge.__all__` (internal error; FB-B's MCP/HTTP layer translates to user-facing error envelopes).
- **D-10:** Allowed transitions:
  ```
  (None)     → proposed
  proposed   → approved  | rejected
  approved   → executed  | failed
  ```
  Terminal states: `rejected`, `executed`, `failed`. Idempotent re-application of any transition (e.g., `approved → approved`) raises `StagedOpLifecycleError` — consistent with state-machine semantics.

### Actor Identity
- **D-11:** Actor representation is a **free string** matching the existing `DBEvent.client_name` convention. Examples: `"projekt-forge:flame-a"`, `"web-ui:artist"`, `"mcp:claude-code"`. Stored on `DBEntity.attributes.{proposer,approver,executor}` and on `DBEvent.client_name` + `DBEvent.payload.actor`. **Why:** Auth lands in v1.5 (SEED-AUTH-V1.5); v1.4 is the staged-ops MVP, not the identity model. Free string is forward-compatible — auth migration writes a structured form; the column type does not need to change.
- **D-12:** No validation on actor string format in v1.4 (any non-empty string accepted). Validation hardens with auth in v1.5.

### Failure Result Payload
- **D-13:** On `approved → failed` transition, `attributes.result` is populated with shape:
  ```jsonc
  {
    "error":      "<human message>",
    "error_type": "<exception class name>",
    "details":    { ... } | null
  }
  ```
  **Why:** `error_type` lets projekt-forge consumers branch on error class without string-matching `error`. `details` is open for caller-supplied context (e.g., partial Flame output, retry-after hints). Matches the FB-D chat-endpoint error envelope shape FB-D will return on rate-limit / timeout (consistency).
- **D-14:** On `approved → executed` transition, `attributes.result` is populated with the operation-specific success payload — shape is opaque to forge-bridge (whatever the proposer chooses to record). Most consumers will record `{success: true, output: {...}}` or similar; this is NOT enforced.

### Schema Migration
- **D-15:** A new Alembic migration (`forge_bridge/store/migrations/versions/0003_staged_operation.py` — exact filename per existing convention) adds `staged_operation` to the `ENTITY_TYPES` frozenset AND updates the `ck_entities_type` CHECK constraint to include the new value. Adds `EVENT_TYPES` updates by Python-side change only (the constraint on `event_type` column is a check on a frozenset literal — needs a similar migration if there's a CHECK constraint; planning to verify).
- **D-16:** No backfill step needed — staged_operation is a new entity type with no existing rows.

### Application Class
- **D-17:** A new `StagedOperation(BridgeEntity)` class in `forge_bridge/core/entities.py` (or a new module if the existing file gets too dense — planning decides). Carries the application-side shape with type-checked attributes (proposer, operation, parameters, result, approver, executor, timestamps) and a `status` property (string, set by repo layer on transition). `to_dict()` produces the JSON shape that FB-B's MCP tools and HTTP routes return verbatim — single source of truth.
- **D-18:** `StagedOperation` does NOT carry the `Versionable` trait (operations are not versioned in the FB-A sense — proposed parameters are immutable, status advances, result is populated once). Carries `Locatable` and `Relational` (via `BridgeEntity` inheritance) although neither is exercised in v1.4 — kept for future "this op affects these shots" relationship hops once v1.5 needs them.

### Test Strategy
- **D-19:** STAGED-01 round-trip test goes in `tests/store/test_staged_operations.py` — direct SQLAlchemy session creation, fetch by id, assert all attributes intact. Pattern matches existing `tests/store/test_entities.py` if present.
- **D-20:** STAGED-02 illegal-transition test parameterizes over the full (from, to) cross-product and asserts exactly the legal transitions succeed. Captures the state machine as test data, not just code.
- **D-21:** STAGED-03 audit-replay test exercises the full happy path (`proposed → approved → executed`) and the two non-happy paths (`proposed → rejected`, `approved → failed`), then queries `DBEvent` rows by `entity_id` and asserts ordering, payloads, and event types.
- **D-22:** STAGED-04 SQL-only-diff test uses a raw SQLAlchemy `select()` to confirm `attributes->'parameters'` and `attributes->'result'` are independently retrievable and that `parameters` is bit-identical across all status advancements.

### Claude's Discretion
- Exact filename for the new migration version (existing convention is `NNNN_description.py` — 4-digit zero-padded; pick the next number).
- Whether to add a new `staged_operations.py` module under `forge_bridge/store/` for the repo class or to extend the existing repo file.
- Whether to add a `forge_bridge/core/staged.py` module for the application class or to extend `entities.py`.
- Test file granularity — single `test_staged_operations.py` covering all four success criteria, or split per criterion.
- Whether `EVENT_TYPES` enforcement is a CHECK constraint at the DB layer (verify existence; if absent, this is a Python-side frozenset only and no migration needed for the new event types).

### Folded Todos
None — todo list was empty at phase open.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` §`Phase 13 (FB-A)` (lines 97-110) — phase goal, depends-on, success criteria, requirements mapping
- `.planning/REQUIREMENTS.md` §STAGED — STAGED-01..04 are this phase; STAGED-05..07 are FB-B and consume this phase's shape (FB-A must not break that contract)
- `.planning/STATE.md` — Key constraints section enumerates v1.4 invariants (dual-naming amendment, locked uvicorn task pattern, single ConsoleReadAPI facade, etc.)

### Existing entity & event model (the load-bearing code)
- `forge_bridge/store/models.py` — DBEntity, DBEvent, ENTITY_TYPES, EVENT_TYPES, schema design principles (lines 1-50 set the architectural rules; D-01, D-06, D-08 all flow from these)
- `forge_bridge/core/entities.py` — BridgeEntity base class, Versionable/Locatable/Relational trait composition pattern; D-17/D-18 build on this
- `forge_bridge/core/traits.py` — trait classes referenced in entity composition
- `forge_bridge/store/repo.py` — existing repo pattern; D-08's StagedOpRepo composes here
- `forge_bridge/store/migrations/versions/0001_initial_schema.py`, `0002_role_class_media_roles_process_graph.py` — Alembic migration conventions for D-15

### Project vocabulary and architecture
- `docs/VOCABULARY.md` — the canonical-vocabulary spec (the shared language all endpoints map to). staged_operation extends this vocabulary; the doc is the project's anchor for what an entity is.
- `docs/ARCHITECTURE.md` — design rationale (event-driven, append-only events, application-layer relationships)
- `docs/DATA_MODEL.md` — entity-relationship reference

### Codebase intel (analyzer outputs)
- `.planning/codebase/STRUCTURE.md` — directory layout, where things go
- `.planning/codebase/CONVENTIONS.md` — naming patterns, code style, import order
- `.planning/codebase/ARCHITECTURE.md` — system design summary
- `.planning/codebase/TESTING.md` — test conventions for D-19..D-22

### Forward-looking
- `.planning/seeds/SEED-AUTH-V1.5.md` — actor identity migration plan (D-11 is the v1.4 placeholder; v1.5 owns the structured form)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`DBEntity` polymorphic table** (`store/models.py:212`) — the new entity_type rides on existing infrastructure: `name`/`status`/`project_id` columns, JSONB `attributes`, GIN index, all migrations.
- **`DBEvent` append-only log** (`store/models.py:463`) — `entity_id`/`event_type`/`payload`/`client_name` columns + three indexes (`ix_events_type_time`, `ix_events_project_time`, `ix_events_entity_time`) cover every query the staged-ops audit needs.
- **`ENTITY_TYPES` and `EVENT_TYPES` frozensets** (`store/models.py:207, 441`) — single source of truth for allowed values. D-15's migration extends both.
- **`BridgeEntity` base class** (`core/entities.py:42`) — id/created_at/metadata + Locatable + Relational traits. `StagedOperation` inherits everything for free.
- **Alembic migration framework** (`store/migrations/versions/`) — D-15's new revision uses the existing `0001`/`0002` pattern.

### Established Patterns
- **Single-table polymorphism** — type-specific shape in JSONB `attributes`, common shape in promoted columns (D-01, D-02, D-03).
- **Application-layer enforcement** — DB stores shape; repo enforces business rules (D-08).
- **Granular event vocabulary** — per-action event types, not generic placeholders (D-06).
- **Free-string actors via `DBEvent.client_name`** — matches existing `flame_a`/`mcp_claude` examples in models.py docstrings (D-11).
- **`__future__ import annotations` + dataclass + traits** — entity application classes follow this shape (D-17).

### Integration Points
- **`forge_bridge/store/models.py`** — extend `ENTITY_TYPES` and `EVENT_TYPES`; CHECK constraint update via migration.
- **`forge_bridge/store/repo.py` (or new module)** — new `StagedOpRepo` or methods (D-08).
- **`forge_bridge/core/entities.py` (or new module)** — new `StagedOperation` class (D-17).
- **`forge_bridge/store/migrations/versions/0003_staged_operation.py`** — new migration (D-15).
- **`tests/store/test_staged_operations.py` (or per-criterion files)** — test suite (D-19..D-22).

### What FB-B Will Consume From This Phase
- `StagedOperation.to_dict()` shape — the single source of truth for FB-B's MCP tool returns and HTTP route response bodies (STAGED-06 zero-divergence test).
- `staged.approved` event type — the subscription contract for projekt-forge v1.5 to know "execute this op now."
- `StagedOpLifecycleError` — FB-B's API layer catches and translates to error envelopes (HTTP 409 Conflict, MCP error result).

</code_context>

<specifics>
## Specific Ideas

- **Subscription contract for projekt-forge v1.5:** The `staged.approved` event is the trigger. projekt-forge subscribes via the existing event bus, reads `entity_id` + `payload.operation` + `attributes.parameters` (via a `forge_get_staged` call from FB-B), executes against Flame, then writes back via `forge_register_publish` (existing) or by transitioning the staged_operation to `executed`/`failed` (FB-B endpoint). FB-A must not constrain this beyond providing the data and the event.
- **Data-first, not API-first:** This phase deliberately ships ONLY the entity, the state machine, and the event vocabulary. FB-B is where the surface (MCP tools, HTTP routes, MCP resource) gets wired. Keeping these separate means FB-A can ship and unit-test against the store layer without any API plumbing — and FB-B can be built (and tested) against a real, persisting backend rather than mocks.

</specifics>

<deferred>
## Deferred Ideas

- **Caller-identity bucketing for actors** — SEED-AUTH-V1.5; v1.4 uses free strings.
- **Operation-specific parameter validation** — staged_operation accepts any JSONB `parameters` shape in v1.4; per-operation validation (e.g., "flame.publish_sequence requires shot_id") is a v1.5 concern when the operation registry exists.
- **Cancel/cancel-on-timeout transitions** — neither the requirements nor the success criteria mention canceling a `proposed` or `approved` operation that times out. Future work; the state machine (D-10) is the locked v1.4 surface.
- **Relationship edges on staged_operation** — D-18 keeps the Relational trait but does not exercise it. Future work: link a staged op to the shots it affects via the existing `relationships` table.
- **Bulk approval / batch operations** — out of scope; FB-B exposes per-op approve/reject only.

### Reviewed Todos (not folded)
None — todo list was empty at phase open.

</deferred>

---

*Phase: 13-fb-a-staged-operation-entity-lifecycle*
*Context gathered: 2026-04-25*
