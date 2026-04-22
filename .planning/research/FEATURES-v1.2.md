# Features Research — v1.2 Observability & Provenance

**Research mode:** Feature-landscape (subsequent milestone, v1.2 scope)
**Overall confidence:** HIGH — MCP spec, FastMCP docs, OpenTelemetry, Celery, and SQLAlchemy patterns all converge on clear conventions.

## EXT-02: Tool provenance in MCP annotations

### How the MCP ecosystem actually handles tool metadata (2026-04 state)

The MCP 2025-11-25 spec and FastMCP (the lib forge-bridge's server is built on) define **four places** tool metadata can live. Each has a different consumer contract:

| Slot | Purpose | Who renders it | Suited for provenance? |
|---|---|---|---|
| `name` | unique id (`[A-Za-z0-9_.-]`, 1–128 chars) | every client, always | no — forge-bridge already uses `synth_<descriptive_name>` |
| `title` | human-readable display name | Claude Desktop tool picker, FastMCP UI | yes, minimally (e.g. "Reconform: repointed timeline" vs raw `synth_reconform_repointed_tl`) |
| `description` | free prose, sent to the model | every client, goes into the LLM's context window | yes, but costs tokens every turn — keep short |
| `annotations` | **behavior hints** (readOnlyHint, destructiveHint, idempotentHint, openWorldHint, title) | clients use to decide confirmation UX (auto-approve read-only, require confirm on destructive) | no — this is a risk vocabulary, not provenance. Spec explicitly warns "clients MUST consider tool annotations untrusted" |
| `_meta` | **free-form key/value extension surface** reserved by the protocol | not rendered by default; clients read it programmatically (e.g. MCP Apps uses `_meta.ui.resourceUri`; Codex uses it for turn metadata) | **yes — this is exactly what `_meta` is for** |

**Key insight from MCP blog "Tool Annotations as Risk Vocabulary" (2026-03-16):** annotations are for safety/trust hints only, not arbitrary metadata. Custom provenance fields belong in `_meta`.

**FastMCP already ships the two surfaces we need:**

```python
@mcp.tool(
  name="synth_reconform_timeline",
  tags={"synthesized", "flame:timeline", "forge:project:acme"},
  meta={"version": "1.1.0", "author": "forge-bridge.synthesizer"},
)
```

`tags` is a `set[str]` used for server-side filter/enable/disable (FastMCP has `mcp.disable(tags={...})`). `meta` is free-form JSON echoed to the client as the `_meta` field on the Tool object.

FastMCP's `tags` format is a flat set of strings — **this matches forge-bridge's existing `.tags.json` sidecar format** (`{"tags": ["key:value", ...]}` per `synthesizer.py` lines 367–371), which uses K8s-style `key:value` labels.

### Table stakes (MUST-HAVE for v1.2 to ship honestly)

**TS-02.1 — Lift `.tags.json` sidecar into tool registration**
When `SynthesizedToolWatcher` (or projekt-forge's equivalent) picks up `synth_foo.py`, if a sibling `synth_foo.tags.json` exists, its `tags` array MUST be attached to the `register_tools()` call so FastMCP exposes them on the Tool object.
- **Minimum:** `tags={"synthesized", *sidecar_tags}` — the literal string `"synthesized"` is added unconditionally so clients can filter "show only synthesized tools".
- **Depends on:** Phase 6-02's sidecar schema (`{"tags": [...]}`). **If schema ever changes, EXT-02 breaks** — lock the sidecar shape before shipping.
- **Test:** register a synth tool with a sidecar containing `["flame:timeline", "forge:project:acme"]`, list tools over MCP, assert the tags appear.

**TS-02.2 — Emit canonical provenance fields into `_meta`**
Every synthesized tool gets a `_meta` payload at registration time containing:
| Field | Source | Why |
|---|---|---|
| `forge.bridge.origin` | literal `"synthesizer"` | distinguishes from builtin / consumer-registered tools |
| `forge.bridge.code_hash` | `ExecutionRecord.code_hash` (sha256 of AST-normalized code) | unique, deterministic, joins back to execution log |
| `forge.bridge.synthesized_at` | ISO-8601 timestamp | audit trail |
| `forge.bridge.version` | `forge_bridge.__version__` at synthesis time | know which bridge generated it |
| `forge.bridge.observation_count` | `count` passed into `synthesize()` | why it was promoted |

Key prefix uses `forge.bridge.*` to comply with the MCP `_meta` naming rules (reserved prefixes are the `modelcontextprotocol`/`mcp` labels; anything else must be qualified — we use a reverse-DNS-style `forge.bridge.` namespace so we don't collide with future MCP reserved keys).

- **Depends on:** `SkillSynthesizer.synthesize()` needs to write a sibling `.meta.json` (or enrich the existing `.tags.json` → `.sidecar.json`) so the loader has the data. **Recommend: rename `.tags.json` → `.sidecar.json` with schema `{"tags": [...], "meta": {...}, "schema_version": 1}`** — one file, one load, one atomic write. This is a **Phase 6-02 sidecar schema evolution**, so it's the right moment to lock it. Adding `schema_version: 1` costs nothing now and lets future sidecar evolutions be detected without silently breaking old consumers.
- **Test:** `tools/list` response over real MCP stdio, assert `tool._meta["forge.bridge.code_hash"]` matches the execution log's `code_hash` for that promotion.

**TS-02.3 — Read-only hint on every synthesized tool (default)**
Set `annotations.readOnlyHint = False` by default for synthesized tools because they call `bridge.execute()` which runs arbitrary Python inside Flame — **never read-only**. Explicit, not inferred, because MCP clients auto-approve read-only tools.
- This is safety hardening, not pure provenance — but it's cheap and belongs here.
- **Test:** assert every synth tool's annotation payload includes `readOnlyHint: False` (or is absent, which is the safer default per spec).

### Differentiators (nice-to-have, defer to v1.3 if scope tight)

**DF-02.1 — Per-consumer prefix in `_meta`** — projekt-forge could add its own `forge.projekt.*` keys (project_id, shot_id, user intent) via the `pre_synthesis_hook` returning richer context that gets stashed in the sidecar. Enables "show me all tools synthesized from shots in project ACME." Defer because it requires projekt-forge schema work and nothing consumes it yet.

**DF-02.2 — `title` field derived from `intent`** — use the `ExecutionRecord.intent` string (cleaned up) as the MCP `title` so Claude Desktop's tool picker shows "Reconform repointed timeline" instead of `synth_reconform_repointed_tl`. Small but material UX win. Deferrable because description already carries this.

**DF-02.3 — MCP resource for synthesis manifest** — expose `forge://synthesized/manifest` as an MCP resource listing all synthesized tools with their full provenance. Lets LLM agents introspect "what has forge-bridge learned?" without hitting `tools/list`. This is essentially the EXT-01 "shared synthesis manifest" idea re-framed as an MCP resource. **Note: this is exactly why the PROJECT.md says EXT-01 should be revisited AFTER EXT-02** — EXT-02 clarifies the schema, then EXT-01 exposes it.

**DF-02.4 — Tag-based filter in `register_tools()`** — accept `register_tools(source="synthesized", filter_tags={"flame:timeline"})` so consumers can selectively surface subsets. Defer — FastMCP already supports `mcp.disable/enable(tags={...})` which is good enough for now.

### Anti-features (explicit OUT OF SCOPE for v1.2)

**AF-02.1 — Don't write to `annotations` for provenance.** MCP spec is explicit: annotations are behavior hints, and clients must treat them as untrusted. Stuffing provenance there violates the contract and won't render as intended.

**AF-02.2 — Don't invent a parallel "provenance protocol".** No new MCP-level methods (`provenance/list`, `provenance/get`), no new JSON-RPC verbs. Ride `_meta` + `tags` + existing `tools/list`. If EXT-01 later needs a richer surface, MCP Resources are the extension point, not new verbs.

**AF-02.3 — Don't promise provenance for non-synthesized tools.** Builtin flame/forge tools don't need `forge.bridge.origin` = "synthesizer" — just leave `_meta` empty or set `forge.bridge.origin = "builtin"`. Don't backfill history for tools that weren't born from observation.

**AF-02.4 — No UI for browsing provenance in v1.2.** projekt-forge doesn't ship an MCP client; Claude Desktop/Code render tool lists but don't (as of 2026-04) surface `_meta` in UI. The data is present and queryable — consumers build UIs later.

**AF-02.5 — No code-signing / cryptographic provenance.** `code_hash` is sha256 of AST-normalized source — that's integrity, not signature. Don't let this creep into "signed tool manifests" territory; that's a separate security project.

## EXT-03: SQL-backed execution log

### How the ecosystem solves "append-only log → structured query store"

Three reference patterns from the research:

1. **OpenTelemetry SpanExporter** (canonical Python Protocol in observability)
   - Interface: `export(spans: Sequence[ReadableSpan]) -> ExportResult`, `shutdown() -> None`, `force_flush(timeout_millis) -> bool`
   - Key idea: the exporter is a *separate concern* from the instrumentation; swappable backends (OTLP, Jaeger, Azure Monitor, console) all implement the same Protocol.
   - Failure policy: export can return `ExportResult.FAILURE`; caller decides retry vs drop.

2. **Celery result backend** — pluggable, `BaseBackend` subclass contract, SQLAlchemy is one concrete backend among many (Redis, Memcached, RPC). **Idempotency is an explicit task-design requirement** (tasks may run >1×).

3. **SQLAlchemy `on_conflict_do_nothing(index_elements=[...])`** — the standard idempotent-insert primitive on Postgres + SQLite. This is exactly the right tool for "if we see the same `code_hash` + `timestamp` twice, silently drop."

**The JSONL-vs-DB question:** Sentry, Temporal audit logs, and Databricks all ship the **JSONL-as-source-of-truth + DB-as-queryable-mirror** pattern. The DB can always be rebuilt from the log; the log is never derived from the DB. Our v1.1 architecture already locks this: the callback fires AFTER `fcntl.LOCK_UN`, and failure is logged-and-swallowed. **v1.2 should not change this contract** — EXT-03 is a callback implementation, not a log-path rethink.

### Table stakes

**TS-03.1 — `StoragePersistence` Protocol on the bridge side**
Define in `forge_bridge/learning/storage.py`:

```python
from typing import Protocol, Sequence, runtime_checkable

@runtime_checkable
class StoragePersistence(Protocol):
    async def persist(self, record: ExecutionRecord) -> None: ...
    async def persist_batch(self, records: Sequence[ExecutionRecord]) -> None: ...
    async def shutdown(self) -> None: ...
```

- Modeled on OpenTelemetry's SpanExporter (same 3-method shape: single, batch, shutdown).
- `persist` is async because projekt-forge's DB is async (aiosqlite / asyncpg).
- The existing `set_storage_callback()` API stays: the Protocol is **what projekt-forge implements**, and its adapter presents `persist` as the callback via `log.set_storage_callback(my_backend.persist)`.
- **No new bridge-side wiring**: `set_storage_callback` already accepts async callables (Phase 6-01 shipped this).
- **Version contract:** `ExecutionRecord` is frozen; Protocol is additive-only. v1.2 ships with `persist` + `shutdown`; `persist_batch` can be `Protocol` default that loops over `persist` — that's how OTel does it too.
- **Depends on:** nothing new bridge-side. This is a **pure documentation + type-export deliverable** for forge-bridge. All SQL happens in projekt-forge.
- **Test:** `@runtime_checkable` Protocol means we get a cheap `isinstance()` check in tests asserting projekt-forge's adapter satisfies the contract.

**TS-03.2 — Canonical minimal schema for projekt-forge's implementation**
Document (in forge-bridge's Protocol docstring, not as SQL DDL) the **fields projekt-forge's table MUST preserve**:

| Column | Type | Why |
|---|---|---|
| `code_hash` | TEXT (sha256 hex, 64 chars) | join key back to JSONL, sidecar, synthesized tool |
| `timestamp` | TIMESTAMPTZ (ISO-8601) | ordering, retention |
| `raw_code` | TEXT | full code (JSONL has it too — mirror) |
| `intent` | TEXT NULL | synthesis context |
| `promoted` | BOOLEAN | mirrors JSONL flag |

**Unique constraint:** `UNIQUE (code_hash, timestamp)` — because one code pattern can execute many times, but the same (hash, timestamp) pair is a duplicate write.
**Required index:** `(code_hash)` — query "how many times did we see this pattern?" is the canonical aggregation.
**Recommended index:** `(timestamp DESC)` — time-range queries.

- **Schema DDL lives in projekt-forge**, NOT forge-bridge. forge-bridge only mandates the contract via Protocol + docstring.
- **Test (projekt-forge-side):** insert the same `ExecutionRecord` twice, assert only one row persists (covers idempotency).

**TS-03.3 — Idempotent write via `on_conflict_do_nothing`**
Projekt-forge's adapter MUST use `insert(...).on_conflict_do_nothing(index_elements=["code_hash", "timestamp"])`. This handles crash-recovery replay + defensive double-fire. **Anti-pattern to avoid:** `SELECT … WHERE code_hash=? AND timestamp=?` then `INSERT` — the race between check and insert is exactly what `ON CONFLICT` solves atomically.

**TS-03.4 — Backfill script (projekt-forge-side)**
Projekt-forge ships a one-shot CLI (`forge-ctl db backfill-executions`) that reads the JSONL, deserializes into `ExecutionRecord`, and calls `persist()` with `on_conflict_do_nothing` handling re-runs. Runs once per deployment; from that point the storage callback handles everything.

### Differentiators (nice-to-have)

**DF-03.1 — `persist_batch()` with 100-row chunks** — Major throughput win for backfill; negligible for live callback. Implement on the adapter side only when backfill gets slow (>1s for a few thousand rows). OpenTelemetry's BatchSpanProcessor is the template.

**DF-03.2 — `retention_days` config on the adapter** — periodic `DELETE FROM executions WHERE timestamp < now() - interval '90 days'`. Deferrable because JSONL is the source-of-truth; DB rows are reproducible.

**DF-03.3 — `shutdown()` → flush-and-close semantics** — If v1.2 ships with only `persist()`, `shutdown()` is a no-op. Prefer it in the Protocol from day 1 (callers call it at shutdown regardless) so we don't need a v1.3 contract break.

**DF-03.4 — Promotion-event mirror** — `mark_promoted()` writes a JSONL entry; currently the storage callback only fires on `record()`, not on `mark_promoted()`. If projekt-forge wants "which executions were promoted, at what time?" queries directly in SQL, the callback surface needs a second hook or the `ExecutionRecord` needs a separate `event_type` field. **Flag this as a potential schema gap in Phase 7 planning.**

### Anti-features (explicit OUT OF SCOPE for v1.2)

**AF-03.1 — DB is NOT source of truth.** Do not delete the JSONL after the DB is populated. The non-goal "no shared-path JSONL writers" (v1.1 decision) locks this: JSONL is per-process canonical state; the DB is a cross-process aggregator.

**AF-03.2 — No full-text search on `raw_code`.** Tempting ("show me all executions mentioning `reconform`"), but FTS wants Postgres `tsvector` + trigram indexes. JSONL `grep` is good enough for v1.2.

**AF-03.3 — No time-series rollups / materialized views.** "Count of executions per hour per project" is a v1.3 dashboard question. For v1.2, aggregate via SQL on demand.

**AF-03.4 — No realtime streaming (WebSocket/SSE) of the callback.** Keeping this out locks forge-bridge as local-first infra.

**AF-03.5 — No built-in Alembic migrations in forge-bridge.** forge-bridge ships the Protocol and nothing else.

**AF-03.6 — No pluggable-backends registry.** One consumer today; YAGNI.

**AF-03.7 — No cross-process promotion-counter sync in v1.2.** Phase 6 locked this as a non-goal; EXT-03 does NOT fix it.

## Cross-cutting findings

### EXT-02 ↔ EXT-03 dependencies

**EXT-03 does not need EXT-02's provenance data in its DB schema.** The minimal schema (TS-03.2) carries what's already in `ExecutionRecord`. Tags are a synthesis-time concept; execution-log persistence is an execution-time concern.

**BUT** there's a useful join: `SELECT … FROM synthesized_tools JOIN executions USING (code_hash)` — if projekt-forge later builds a "tools synthesized from executions matching X" query. This is a v1.3 concern; the join key (`code_hash`) is already in place.

**One concrete recommendation:** ship EXT-02 first (Phase 7), then EXT-03 (Phase 8). Reasons: EXT-02's sidecar-schema decision is the riskiest schema change in v1.2; EXT-03's Protocol deliverable is mostly documentation + one type-export, it's fast; EXT-02 is the harder lift.

### Interaction with locked v1.1 non-goals

| v1.1 non-goal | Intersection with v1.2 | Status |
|---|---|---|
| No LLMRouter hot-reload | None — neither EXT-02 nor EXT-03 touches router wiring | Safe |
| No shared-path JSONL writers | EXT-03 tempts "multiple processes write to one DB" — but that's DB concurrency (which is fine), not JSONL concurrency. Each process still owns its own JSONL; the DB aggregates. | Safe — but test explicitly: two processes, two JSONLs, one DB, no duplicate rows thanks to `on_conflict_do_nothing`. |
| Log-stream-mirror stub (SC #3 scope reduction) | EXT-03 IS the swap-in. `ExecutionRecord` contract stability was the precondition — still holds. | EXT-03 = "unstub the stub." One-function change in projekt-forge. |

### Dependencies on Phase 6 precedent

**EXT-02 consumes `.tags.json` sidecars produced by Phase 6-02 (`synthesizer.py` lines 367–371).** Any schema change to the sidecar blocks EXT-02.

**Strong recommendation: lock the sidecar schema change in Phase 7 Plan 1, not Plan 3.** Rename `synth_foo.tags.json` → `synth_foo.sidecar.json`. Shape: `{"tags": [...], "meta": {...}, "schema_version": 1}`. Update `synthesizer.py` write path + add a test asserting round-trip read. Only THEN build the watcher/loader/register_tools side that consumes it.
