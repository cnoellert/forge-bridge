# Pitfalls — forge-bridge v1.2 (EXT-02 + EXT-03)

**Domain:** Adding observability features (MCP annotation provenance + SQL persistence) to production-adjacent Python middleware already shipped to a downstream consumer
**Researched:** 2026-04-19
**Confidence:** HIGH (direct source analysis of `forge_bridge/learning/execution_log.py`, `forge_bridge/learning/synthesizer.py`, `forge_bridge/mcp/registry.py`, v1.1 roadmap; MCP/SQLAlchemy/Alembic spec via Context7; 2026-era prompt-injection research)

> This document supersedes the v1.1 pitfalls file (which was scoped to cross-repo pip adoption). v1.2 pitfalls center on **adding features to a stable contract** — not re-wiring the consumer.

---

## EXT-02 pitfalls — Tool provenance in MCP annotations

Raw material: `.tags.json` sidecars produced by Phase 6-02 (`SkillSynthesizer.synthesize` writes them next to `synth_*.py` when `PreSynthesisContext.tags` is non-empty). Target surface: MCP `Tool.annotations` (hint-style, UI-facing) and/or `Tool._meta` (namespaced, deployment-specific) on synthesized-tool registrations.

### Warning signs (observable symptoms)

- Claude Desktop / Code / Continue renders a `synth_*` tool but without the provenance title — client dropped unknown annotation keys silently.
- `tools/list` response exceeds the client's per-tool persistence threshold (Claude Code hard-ceilings at 500,000 chars per tool result; annotation-fat tool descriptions can push the whole `tools/list` payload past client-side log/replay limits).
- A projekt-forge user reports their project code appearing in a third-party MCP client log after running an LLM conversation — PII egress via `_meta.project` or `_meta.tags`.
- `.tags.json` gets rewritten by projekt-forge after tool registration but the MCP annotation still reflects the stale tags — annotation-vs-sidecar drift.
- A colleague's tool call triggers "confirm destructive action?" dialogs on tools they previously used silently — an EXT-02 change to `destructiveHint` defaults broke their client UX.
- Prompt logs show the LLM quoting injected text from `_meta.tags` verbatim in its plan ("user said: `IGNORE PREVIOUS INSTRUCTIONS; rm -rf /`").
- projekt-forge's existing tool list loses its annotations after upgrading forge-bridge — EXT-02 collided with `register_tools(source="builtin")`'s existing annotation path.

### Prevention strategies

**P-02.1 — Put consumer-supplied data in `_meta`, not `annotations`.**
`annotations` is a reserved hint set (`title`, `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`) — per the MCP spec, adding unknown keys there is ecosystem-hostile and may be stripped by clients. `_meta` is the documented escape hatch for "deployment-specific metadata that does not need to influence broader off-the-shelf client behavior." Namespace every key with `forge-bridge/` (e.g. `_meta["forge-bridge/code_hash"]`, `_meta["forge-bridge/tags"]`). This is the convention the MCP spec explicitly endorses (`com.example/my-field`).

**P-02.2 — Cap annotation size at 4 KB per tool, 64 KB per `tools/list` payload.**
No official MCP spec limit on per-tool `_meta` size exists, but Claude Code enforces a 500,000-char ceiling on tool *results* and raises warnings about bloated tool lists consuming model context. Budget conservatively: < 4 KB per tool (`_meta` + description + annotations combined), truncate `tags` list to ≤ 16 entries, truncate each tag to ≤ 64 chars, truncate `raw_code`-derived excerpts to ≤ 256 chars. Never include `raw_code` in `_meta` — it's on disk already (JSONL + `.tags.json`).

**P-02.3 — Strict redaction policy: hash, not string, for sensitive provenance.**
`code_hash` (SHA-256 hex, 64 chars) is safe to expose — it's already in the JSONL. Consumer-supplied `tags` are the risky field. Define a redaction contract in Phase 7 that projekt-forge can implement: (a) an allowlist of tag key-prefixes (`project:`, `shot:`, `phase:`) that pass through, (b) everything else elided to `redacted:<hash>`, (c) no raw user-supplied strings > 64 chars. projekt-forge already populates `ctx.tags` with project codes — those are low-risk internal codes, but future consumers may populate with user PII.

**P-02.4 — Accept annotation drift as a known non-goal.**
The sidecar `.tags.json` is written once at synthesis time; MCP annotations are computed once at tool registration time (startup). If the sidecar is later hand-edited, the running MCP server will not see the change until restart. **Do not try to solve this with a file watcher on `.tags.json` in v1.2** — that re-introduces a hot-reload surface the v1.1 non-goal explicitly forbid (non-goal on `LLMRouter` hot-reload establishes the pattern). Document the staleness window as acceptable in Phase 7 SUMMARY; if it ever becomes a real problem, design it explicitly.

**P-02.5 — Treat consumer-supplied tags as an extended prompt-injection surface.**
2026 research ("Full-Schema Poisoning," CyberArk "Poison Everywhere," Unit 42 on MCP sampling) has confirmed that **every** field in a tool schema — not just `description` — is injected into the LLM's reasoning loop. Today, `ctx.tags` already reaches the synthesis prompt via `PreSynthesisContext.tags` (Phase 6-02 D-11) and the hook is additive-only to prevent override of `SYNTH_SYSTEM`. EXT-02 gives those same strings a second injection path: *rendered back to the LLM* when it calls `tools/list`. Mitigation: (a) strip newlines and control characters from any tag before writing to `_meta`, (b) reject tags containing common prompt-injection markers (`"ignore previous"`, `"<|"`, triple-backtick), (c) log a WARNING and skip the tag when rejected. This is a **new** injection surface vs. v1.1 — synthesis-time injection influences one LLM (synthesizer); MCP-time injection influences every LLM that ever calls `tools/list`.

**P-02.6 — Register EXT-02 metadata through the existing `register_tool(..., annotations=...)` path; do NOT add a new registration function.**
`forge_bridge/mcp/registry.py::register_tool` already accepts `annotations` and calls `mcp.add_tool(fn, name=..., annotations=..., meta={"_source": source})`. EXT-02 should **extend the existing `meta` dict** (already in use for `_source`) rather than create a parallel `register_tool_with_provenance` API — that would fork the registration path and risk projekt-forge's `register_tools(source="builtin")` call falling into the wrong branch. Add a `provenance: dict | None = None` kwarg to `register_tool` that merges into `meta` under the `forge-bridge/` namespace prefix.

**P-02.7 — Breaking-change check against projekt-forge's live tool list.**
Before v1.2.0 ships, dump projekt-forge's live `tools/list` response (via the pip-installed forge-bridge integration with projekt-forge's `register_tools(source="builtin")` call for `catalog`/`orchestrate`/`scan`/`seed`) and diff the pre-EXT-02 vs post-EXT-02 JSON. Any `annotations` or `description` field on an existing tool that changes is a breaking change. The only deltas should be **additions** to `_meta` on `synth_*` tools.

### Phase ownership

| Pitfall | Phase 7 plan that owns mitigation | Concrete deliverable |
|---------|-----------------------------------|----------------------|
| P-02.1 (use `_meta`, not `annotations`) | Phase 7-01 — provenance contract | CONTEXT.md decision: "EXT-02 attaches provenance to `Tool._meta['forge-bridge/*']`, never to `annotations`" |
| P-02.2 (size cap) | Phase 7-02 — synthesis-side emission | Unit test: `test_annotation_payload_within_4kb` asserting upper bound; `_truncate_for_annotation()` helper |
| P-02.3 (redaction) | Phase 7-01 or 7-02 | Documented allowlist + optional `redact_fn` hook on the provenance builder for consumer override |
| P-02.4 (staleness accepted) | Phase 7 SUMMARY + CONTEXT.md | Locked non-goal: "MCP annotations are snapshot at registration; no hot-reload from `.tags.json`" |
| P-02.5 (tag injection surface) | Phase 7-02 | `_sanitize_tag()` strips control chars + rejects injection markers; regression tests |
| P-02.6 (extend existing registration) | Phase 7-02 | `register_tool(provenance=...)` kwarg, not a parallel function; annotations-only path unchanged |
| P-02.7 (projekt-forge diff) | Phase 7 VERIFICATION | Live-UAT item: diff `tools/list` pre/post upgrade, confirm only additive changes |

---

## EXT-03 pitfalls — SQL persistence backend for `ExecutionLog`

Starting point: `_persist_execution` in projekt-forge is a logger-only stub. v1.1 locked `ExecutionRecord` as a frozen dataclass (code_hash, raw_code, intent, timestamp, promoted). EXT-03's job is to swap the stub body for a real SQLAlchemy write, with forge-bridge optionally shipping a `StoragePersistence` Protocol that projekt-forge implements.

### Warning signs (observable symptoms)

- `OperationalError: QueuePool limit of size 5 overflow 10 reached` after a long synthesis burst — connections leaked from the async callback path.
- Database down for an hour; JSONL has 3,000 new lines; DB has 0 rows from that window — no backfill path, schema drift vs reality.
- `RuntimeError: Task <...> got Future attached to a different loop` on projekt-forge startup after forge-bridge upgrade — `ExecutionLog()` was constructed on one loop and the callback dispatches on another.
- Projekt-forge's Alembic `alembic upgrade head` fails: "Multiple head revisions are present; please specify the head revision." — forge-bridge's Alembic chain collides with projekt-forge's.
- `_persist_execution` stops firing after an hour of uptime; logs show a single stale `storage_callback scheduled outside event loop — skipped` line — the consumer called `ExecutionLog.record()` from a sync Flame thread and there was no running loop.
- DB migration silently succeeds in dev, crashes in prod: `column "recorded_at" does not exist` — the dataclass added a field, the migration didn't ship.
- A retry loop inside `_persist_execution` stacks up async tasks faster than the DB drains; `asyncio.all_tasks()` count grows to 10,000 before OOM.
- JSONL has a record, DB has nothing — consumer asks "is the log corrupt?" — answer: "no, DB is eventually consistent; source of truth is JSONL; here's the reconcile script."

### Prevention strategies

**P-03.1 — One session per callback invocation, context-managed, begin()-wrapped.**
Every `_persist_execution` invocation must open a fresh `AsyncSession` via `async with async_session_maker.begin() as session: ...`. **Never** bind a long-lived session to the `ExecutionLog` instance. SQLAlchemy 2.0 documents this as the canonical pattern — `async_sessionmaker.begin()` produces a context manager that both opens the transaction and closes the session on exit (commit OR rollback). Never call `session.close()` manually — the `async with` handles it on normal AND exception paths. The v1.1 decision "JSONL is source of truth; callback failure is isolated" holds; this pattern enforces it at the connection-pool level.

**P-03.2 — Document the consistency model in writing: "eventual, best-effort, log-authoritative."**
JSONL write precedes callback dispatch. DB writes after. If DB write fails:
- JSONL has the row. ✓ (source of truth)
- DB does not. ✗ (missed mirror)
- Consumer gets a `WARNING` log line and continues.

This is **explicitly** eventual consistency, **not** transactional. Write this in Phase 8-01 CONTEXT.md:

> The SQL backend is a best-effort mirror of the JSONL log. The JSONL file is the source of truth. A row in the DB implies a row in the JSONL; the reverse is not guaranteed. To rebuild DB state from JSONL, run the backfill script (see P-03.4). Do not query the DB for promotion-count invariants — query the JSONL or use `ExecutionLog.get_count()`.

**P-03.3 — Use a dedicated `alembic_version` table for forge-bridge-owned migrations (if we ship migrations).**
Per Alembic docs, two applications sharing a database can coexist by configuring distinct `version_table` names. If forge-bridge v1.2 ships any Alembic migrations for a shared `execution_log` table, the migration environment must set `version_table="forge_bridge_alembic_version"` (not the default `alembic_version` which projekt-forge owns). Alternatively — and this is the decision I'd push for in Phase 8-01 — **forge-bridge ships NO migrations and NO models**; it ships only the `StoragePersistence` Protocol. projekt-forge owns the schema, the table name, the migration chain, and the `timestamp → recorded_at` rename if they want it. This keeps forge-bridge's pip surface clean of DB-server concerns (consistent with the v1.0 decision "forge-specific DB belongs in projekt-forge").

**P-03.4 — Backfill must be idempotent or explicitly not attempted.**
Two valid answers; pick one in Phase 8:
- **(a) Do backfill**: ship a script `forge-bridge-backfill-executions --log /path/to/executions.jsonl --db <url>` that reads JSONL line-by-line and upserts keyed on `(code_hash, timestamp)`. Composite PK or unique index on those columns prevents duplicates across re-runs. Must chunk (1,000 rows per transaction) for 100k-line logs.
- **(b) No backfill, documented cutover**: the DB starts empty at install; record the cutover timestamp; queries older than that timestamp hit JSONL. Faster to ship, honest about the eventual-consistency contract.

My recommendation for Phase 8: option (b). Backfill is a one-time operation that shouldn't live in the forge-bridge pip surface. If projekt-forge needs it, they write the script against the Protocol interface.

**P-03.5 — No retry inside the callback; let the JSONL handle durability.**
The Phase 6-01 decision "log WARNING, continue" explicitly chose no-retry semantics. EXT-03 must preserve this. If the DB is down, `_persist_execution` catches the exception, logs once at WARNING, and returns. **No `tenacity`, no `backoff`, no inner retry loop.** Rationale: retries stack async tasks (bounded only by asyncio's task queue); a 30-second DB outage with 10/sec synthesis produces 300 stacked retry tasks, each holding an open connection attempt, which triggers QueuePool exhaustion — the exact failure mode we're trying to prevent. Durability comes from JSONL + backfill, not from retry-in-callback. If a retry layer is ever needed, build it as a **separate** reconciliation process that reads JSONL and writes missing rows, OUT of the hot path.

**P-03.6 — Circuit-breaker shape (if retry is ever added): open on 3 consecutive failures, 60s cool-down, log at INFO on transition.**
Deferred for v1.2 — document the shape in CONTEXT.md so if P-03.5 gets overturned later, there's a designed pattern to reach for. Don't build it now.

**P-03.7 — Schema-coupling gate: `ExecutionRecord` changes require migration review.**
Add to Phase 8 VERIFICATION and carry into the v1.2+ release ceremony: any PR that touches `forge_bridge/learning/execution_log.py::ExecutionRecord` must either (a) declare no DB impact in the PR description, or (b) include an Alembic migration snippet for the reference implementation. Enforce via a CODEOWNERS-style comment or a CI check that greps the diff. **A frozen dataclass is not protection against schema drift** — a new field with a default works in Python but silently breaks production SQL schemas unless a migration ships alongside.

**P-03.8 — Threading-model decision: "async callback requires running loop at `record()` time" is ALREADY documented; make EXT-03's implementation deal with it.**
`ExecutionLog.set_storage_callback` detects sync-vs-async via `inspect.iscoroutinefunction` and caches it. The async dispatch uses `asyncio.ensure_future` which raises `RuntimeError` if no loop is running — that's caught and logged. EXT-03's implementation has three paths:
- Register a **sync** callback (`def persist(rec): ...`) that uses a sync SQLAlchemy session — works when `record()` is called from a sync Flame thread. No event loop required. Simplest, most robust.
- Register an **async** callback (`async def persist(rec): ...`) that uses `AsyncSession` — only works if `record()` fires inside an active loop. The MCP server lifespan is async; Flame-exec paths might NOT be async.
- Hybrid: async callback that schedules onto a dedicated background loop via `run_coroutine_threadsafe(coro, loop)` — requires a long-lived loop reference. Complex.

My recommendation: **sync callback with sync SQLAlchemy session** for projekt-forge's `_persist_execution`. Matches the failure isolation pattern already in place; dodges the "no running loop" silent-drop failure; SQLAlchemy sync and async sessions coexist fine in the same process. Document this pick in Phase 8-01 CONTEXT.md.

**P-03.9 — `ExecutionRecord` field additions are additive-with-default, version-coupled.**
If Phase 8 discovers it needs a new field (e.g. `consumer_id`, `project`), add it with a default value (`field(default="")`) to preserve backward compat for any projekt-forge code that `ExecutionRecord(code_hash=..., raw_code=..., intent=..., timestamp=..., promoted=...)`-constructs explicitly (unlikely but possible in tests). This requires a **minor-version bump** on forge-bridge and a corresponding update to projekt-forge's `forge-bridge @ git+...@v1.2.0` pin. Use the Phase 6-established minor-bump ceremony: barrel re-export → pyproject.toml → regression test → annotated tag → push. Do NOT add non-default fields to `ExecutionRecord` without a major bump.

### Phase ownership

| Pitfall | Phase 8 plan that owns mitigation | Concrete deliverable |
|---------|-----------------------------------|----------------------|
| P-03.1 (one session per call) | Phase 8-01 (Protocol) + Phase 8-02 (projekt-forge impl) | Protocol docstring states "implementations MUST open a fresh session per record"; projekt-forge impl uses `async with async_sessionmaker.begin()` |
| P-03.2 (consistency model) | Phase 8-01 CONTEXT.md | Explicit "best-effort, log-authoritative" section |
| P-03.3 (migration ownership) | Phase 8-01 | Decision: forge-bridge ships Protocol only, no models, no migrations — projekt-forge owns schema |
| P-03.4 (backfill) | Phase 8-02 SUMMARY | Documented cutover; backfill script optional and owned by projekt-forge |
| P-03.5 (no retry) | Phase 8-02 | `_persist_execution` body: single try/except, one WARNING log, no retry imports |
| P-03.6 (circuit breaker deferred) | Phase 8 CONTEXT.md | Locked non-goal for v1.2; shape documented for future |
| P-03.7 (schema coupling gate) | Phase 8 VERIFICATION + v1.2 release ceremony | CI grep or PR template item: "ExecutionRecord changed? include migration." |
| P-03.8 (sync-over-async) | Phase 8-02 | projekt-forge registers a **sync** storage callback using `sessionmaker` (not `async_sessionmaker`); test covers Flame-thread `record()` path |
| P-03.9 (additive fields) | Phase 8 + v1.2.x ceremony | No non-default fields on `ExecutionRecord`; minor bump for any addition |

---

## Integration pitfalls — EXT-02 ↔ EXT-03

### Cross-feature coupling risks

**I-1 — Tempting trap: make EXT-03's DB row schema mirror EXT-02's `_meta` shape.**
Because both surfaces carry provenance, it's tempting to define one `ExecutionProvenance` struct that both emit. Don't. EXT-02's consumer is an LLM (via MCP client rendering) — prompt-injection surface, 4KB budget, hint-vs-contract semantics. EXT-03's consumer is a BI analyst running SQL (or projekt-forge's future dashboards) — need indexable columns, typed fields, no truncation. **The two features have different audiences and different budget constraints; coupling them is future work locked in now.** Keep the provenance builders separate; let them share only the raw source (`.tags.json` + `ExecutionRecord`).

**I-2 — `ExecutionRecord` dataclass modification hits both features.**
If Phase 8 adds `project: str` to `ExecutionRecord` (so the SQL row can be indexed by project), that same field now flows through the callback path and is visible to any consumer — including EXT-02, which may decide to surface it in `_meta["forge-bridge/project"]`. Fine, but the cross-feature implication must be explicit: a Phase 8 field addition enables a Phase 7 feature update. Document this as "EXT-03 dataclass additions are also surfaced via EXT-02" in the v1.2 decision log, OR explicitly carve EXT-02 to only read from `.tags.json` (not `ExecutionRecord`) — I recommend the latter for clean separation (see I-1).

**I-3 — Partial-ship order matters: ship EXT-02 first, EXT-03 second.**
If EXT-03 ships first (v1.2.0) and EXT-02 ships second (v1.2.1):
- Consumer pins `@v1.2.0`, gets DB persistence. OK.
- Consumer bumps to `@v1.2.1`, gets MCP annotations. OK.

If EXT-02 ships first (v1.2.0) and EXT-03 ships second (v1.2.1):
- Consumer pins `@v1.2.0`, gets MCP annotations but their `_persist_execution` stub is still a logger. OK.
- Consumer bumps to `@v1.2.1`, the Protocol type ships; projekt-forge can now implement. OK.

Either order works, but **EXT-02-first is lower risk**: (a) annotation changes are transparent to consumers not reading annotations; (b) the DB Protocol is an API contract that benefits from being defined after observing what projekt-forge actually needs; (c) EXT-02 produces the `.tags.json` → `_meta` pipeline we can inspect to validate EXT-03's "should the DB have a `tags` column?" question. Ship Phase 7 (EXT-02) first.

**I-4 — Don't ship the features on the same git tag.**
Two features bundled into v1.2.0 means one rollback pulls both. Separate minor/patch tags (`v1.2.0` = EXT-02; `v1.2.1` = EXT-03 or v1.3.0 = EXT-03) let projekt-forge pin forward/back independently. Follows the v1.1 pattern (v1.1.0 = Phase 6, v1.1.1 = patch). Matches the Phase 6 decision "minor-version bump ceremony" and its reusability claim.

### Prevention

- **I-1 mitigation**: Phase 7-01 and Phase 8-01 separately define their provenance structures. Phase 8 CONTEXT.md explicitly states "DB row schema is NOT coupled to MCP `_meta` shape."
- **I-2 mitigation**: Phase 7-02 reads tags from `.tags.json`, not from `ExecutionRecord`. Any `ExecutionRecord` addition in Phase 8 is invisible to EXT-02.
- **I-3 mitigation**: Roadmap orders Phase 7 before Phase 8, matching the EXT-02-first recommendation.
- **I-4 mitigation**: Release ceremony in Phase 7 ships `v1.2.0`; Phase 8 ships `v1.2.1` or `v1.3.0` depending on whether EXT-03 adds a new public symbol (Protocol export = new symbol = minor bump).

### Build-order implications for roadmap

```
Phase 7 (EXT-02) → ship v1.2.0 → projekt-forge bumps pin → UAT annotations → Phase 8 (EXT-03) → ship v1.2.1 or v1.3.0 → projekt-forge implements Protocol → UAT DB writes
```

Gate: Phase 8 cannot start until Phase 7's v1.2.0 is pinned in projekt-forge and UAT'd. This matches the v1.1 strict phase-ordering pattern (Phase 5 gated on Phase 4; Phase 6 gated on Phase 5).

### `ExecutionRecord` and the git-URL pin

projekt-forge's pin form is `forge-bridge @ git+https://...@v1.1.1` (per RWR-01 final outcome). The pin is **tag-identity-locked** (annotated tag on main). This means:

- **Phase 7 ships v1.2.0**: projekt-forge updates `pyproject.toml` pin to `@v1.2.0`, re-runs `pip install -e .[test]`, conftest site-packages guard asserts resolution.
- **Phase 8 adds field to `ExecutionRecord`**: if the field has a default, projekt-forge's existing `_persist_execution(rec: ExecutionRecord)` signature is unchanged → minor bump OK. If the field is required, projekt-forge code breaks at import time → major bump required.
- **Phase 7's annotation change to `register_tool`** (new `provenance=` kwarg with default None): additive → minor bump OK.

The v1.1-established ceremony (barrel re-export → pyproject.toml → regression test → annotated tag → push) is reusable for v1.2.0. The decision "Clean break on API renames (no aliases)" still applies — if any Phase 7 or Phase 8 work renames an existing public symbol, it's a breaking change and needs v2.0.

---

## Security & privacy

### PII egress via MCP annotations

**Threat model:** An MCP client (Claude Desktop, Continue, a custom agent) receives `tools/list` containing `synth_*` tools with `_meta["forge-bridge/tags"] = ["project:ACM_1234", "shot:ST01_0420"]`. That client logs tool metadata, ships its logs to a SaaS error tracker, and now internal project/shot codes are in a third-party system.

**Local-first context means low stakes today** — forge-bridge is deployed locally, the MCP client is on the same machine. But the architecture is swappable-to-cloud per the v1.0 constraints, and projekt-forge is already a consumer populating these tags. The time to decide redaction policy is before it ships, not after.

**Policy (to be ratified in Phase 7-01):**

- **Allowlist**: Phase 7-02 ships a small allowlist of tag key-prefixes that pass through unmodified: `project:`, `phase:`, `shot:`, `type:`. These are low-stakes pipeline vocabulary.
- **Everything else**: elided to `redacted:<sha256[:8]>` — the consumer can correlate back via their own log if needed, but the raw string is never in `_meta`.
- **Override hook**: a consumer-supplied `redact_fn(tag) -> str | None` (returns None → drop the tag entirely). projekt-forge can opt into looser policy if it understands the consequences.
- **Size ceiling**: ≤ 16 tags per tool, ≤ 64 chars per tag — prevents payload-inflation attacks via huge tag lists.

### `raw_code` in DB rows — retention, redaction

**Current state:** `raw_code` is already in the JSONL (since v1.0). EXT-03 proposes to mirror it into a DB column. This is **documented existing exposure, not new** — but the DB surface is queryable in ways the JSONL isn't.

**Prevention strategies:**

- **Schema decision (Phase 8-01)**: the SQL table stores `code_hash` (PK), `intent`, `timestamp`, `promoted`. The `raw_code` column is **optional** and off by default. Consumers who need it set a flag at Protocol-construction time. Rationale: 99% of queries are "count by hash" or "sessions since timestamp" — raw code is rarely needed in SQL; leave it in JSONL.
- **If raw_code IS stored**: add a retention policy column (e.g. `expire_at` = `timestamp + 90d`) and a documented cleanup SQL. Forge-bridge doesn't ship cleanup infrastructure (no scheduled jobs in scope); projekt-forge can wire up `pg_cron` or equivalent.
- **No `raw_code` in MCP `_meta`**: reinforced in P-02.2. Synthesized tool source is on disk in `~/.forge-bridge/synthesized/synth_*.py` — that's the canonical location for "what code did the synthesizer write." Don't duplicate into annotations.

### Consumer-supplied-string pitfalls — new surface via MCP rendering

Phase 6-02 already discussed prompt-injection via `ctx.tags` and `ctx.extra_context` reaching `SYNTH_SYSTEM`. The hook is additive-only, can't replace the system prompt, and hook failure falls back to empty context. That's a solved problem for synthesis.

**What's NEW in EXT-02:** consumer-supplied tags now reach MCP client rendering AND the LLM's `tools/list` view. This is a **second injection site with a different threat model**:

| Surface | Attacker goal | Mitigation today (v1.1) | Mitigation needed (v1.2) |
|---------|---------------|-------------------------|--------------------------|
| `PreSynthesisContext` → SYNTH_SYSTEM | Manipulate synthesized tool code | Additive-only prompt composition | — |
| `_meta` → MCP client UI | Manipulate what user sees about a tool | (none — new surface) | P-02.5 strip + reject; client renders title only |
| `_meta` → LLM tools/list rendering | Manipulate LLM's reasoning when choosing a tool | (none — new surface) | P-02.5 strip + reject; keep `_meta` sizes small; don't echo tags into `description` |

**2026 CVE context:** Anthropic's own Git MCP server had three prompt-injection vulnerabilities in January 2026 where malicious README / issue content reached the LLM via tool results. The attack pattern applies to `_meta` too: anywhere consumer-controlled strings are rendered in the agent context is an injection site. Treat `_meta["forge-bridge/tags"]` as equivalent-risk to tool descriptions — sanitize at the boundary.

**Concrete Phase 7 requirement**: `_sanitize_tag()` helper that:
1. Rejects tags containing `\n`, `\r`, `\x00`..`\x1f` (control chars).
2. Rejects tags containing common injection markers (`ignore previous`, `<|`, `|>`, `[INST]`, `[/INST]`, `<|im_start|>`, triple-backtick, `---`).
3. Truncates to 64 chars after sanitization.
4. Logs WARNING on reject; doesn't crash synthesis or tool registration.

This is strictly additive to Phase 6-02's `pre_synthesis_hook` failure isolation — another layer at another boundary.

---

## Summary — "what must each phase own?"

**Phase 7 (EXT-02) must:**
1. Decide `_meta` vs `annotations` — pick `_meta` (P-02.1).
2. Ship a size budget and enforce it in code (P-02.2).
3. Ship a redaction allowlist + override hook (P-02.3, PII section).
4. Accept sidecar-vs-annotation staleness as a non-goal (P-02.4).
5. Ship `_sanitize_tag()` with injection-marker rejection (P-02.5, privacy section).
6. Extend existing `register_tool` signature; don't fork it (P-02.6).
7. Live-UAT diff against projekt-forge's tools/list (P-02.7).

**Phase 8 (EXT-03) must:**
1. Ship the Protocol only; no models, no migrations, no Alembic (P-03.3).
2. Document eventual-consistency, log-authoritative model in writing (P-03.2).
3. Require one-session-per-callback, context-managed (P-03.1).
4. Forbid in-callback retry; document the shape if ever added (P-03.5, P-03.6).
5. Pick cutover-over-backfill (P-03.4) unless projekt-forge requests otherwise.
6. Recommend sync callback + sync SQLAlchemy session for projekt-forge (P-03.8).
7. Gate `ExecutionRecord` changes on migration review (P-03.7, P-03.9).

**Integration level:**
1. Ship Phase 7 before Phase 8 (I-3).
2. Separate tags per feature (I-4); reuse v1.1 minor-bump ceremony.
3. Don't couple MCP `_meta` shape to DB schema (I-1, I-2).

---

## Sources

- [MCP Specification — Tool Annotations (2026-03)](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/blog/content/posts/2026-03-16-tool-annotations.md) — `_meta` namespace convention; `annotations` as hint-only; questions for evaluating new annotations
- [MCP Specification — Tool schema (2025-11-25)](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2025-11-25/schema.mdx) — `Tool._meta` field type; `ResourceLink` metadata pattern
- [MCP Apps — UI metadata via `_meta`](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/blog/content/posts/2026-01-26-mcp-apps.md) — `_meta.ui.resourceUri` pattern; namespaced custom fields
- [Claude Code MCP integration — `maxResultSizeChars`](https://docs.anthropic.com/en/docs/claude-code/mcp) — 500,000 char ceiling; annotation pattern for size override
- [CyberArk — Poison Everywhere: No output from your MCP server is safe](https://www.cyberark.com/resources/threat-research-blog/poison-everywhere-no-output-from-your-mcp-server-is-safe) — every schema field is an injection point
- [Unit 42 — New Prompt Injection Attack Vectors Through MCP Sampling](https://unit42.paloaltonetworks.com/model-context-protocol-attack-vectors/) — full-schema poisoning research
- [Practical DevSecOps — MCP Security Vulnerabilities 2026](https://www.practical-devsecops.com/mcp-security-vulnerabilities/) — client-side validation gaps; tool poisoning mechanics
- [SQLAlchemy 2.0 — async_sessionmaker.begin()](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) — canonical context-manager pattern for async sessions
- [SQLAlchemy — Connection Pool Exhaustion errors](https://docs.sqlalchemy.org/en/20/errors.html) — unreturned connections, garbage-collection reliance anti-pattern
- [SQLAlchemy async issue #8145](https://github.com/sqlalchemy/sqlalchemy/issues/8145) — connections not returned on task cancel
- [SQLAlchemy discussion #5994](https://github.com/sqlalchemy/sqlalchemy/discussions/5994) — "Event loop is closed" on cross-loop use
- [Alembic discussion #1522 — Separate Alembic migrations for two services sharing a DB](https://github.com/sqlalchemy/alembic/discussions/1522) — `version_table` name separation pattern
- [Alembic Runtime Objects — version_table / version_table_schema](https://alembic.sqlalchemy.org/en/latest/api/runtime.html) — configuration for third-party library migrations
- [DEV.to — Building Resilient Database Operations with Async SQLAlchemy + CircuitBreaker](https://dev.to/akarshan/building-resilient-database-operations-with-aiobreaker-async-sqlalchemy-fastapi-23dl) — circuit-breaker shape pattern
- Direct source analysis: `forge_bridge/learning/execution_log.py` (v1.1.1), `forge_bridge/learning/synthesizer.py` (v1.1.1), `forge_bridge/mcp/registry.py` (v1.1.1), `.planning/milestones/v1.1-*`
