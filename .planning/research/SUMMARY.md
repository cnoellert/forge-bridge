# Project Research Summary

**Project:** forge-bridge v1.2 — Observability & Provenance
**Domain:** Stable-contract feature additions to a v1.1-shipped pip-consumed middleware package
**Researched:** 2026-04-19
**Confidence:** HIGH

## Executive Summary

v1.2 adds two observability features on top of the v1.1.1 foundation: **EXT-02** surfaces what the learning pipeline has synthesized (by lifting `.tags.json` sidecars into MCP tool metadata), and **EXT-03** defines a `StoragePersistence` `typing.Protocol` that projekt-forge implements with SQLAlchemy to mirror `ExecutionRecord` into SQL. Both features are small in code footprint (3 production files touched in forge-bridge; `__all__` grows by exactly 1) and both ride contracts already locked at v1.1.0 (`ExecutionRecord` frozen dataclass, `set_storage_callback` dispatch semantics, Phase 6-02 sidecar write-path). All four research tracks converge on the same shape: ship EXT-02 first as v1.2.0, let projekt-forge UAT it, then ship EXT-03 as v1.2.1 or v1.3.0 once we've seen what metadata is actually worth persisting.

The recommended approach is **strictly additive, no signature changes on public APIs**. EXT-02 attaches provenance to MCP `Tool._meta` (the documented freeform slot) — never to `annotations` (a closed safety-hint schema that spec-compliant clients treat as untrusted). EXT-03 defines the Protocol in `forge_bridge/learning/storage.py` but ships no SQLAlchemy models, no Alembic migrations, and no DDL — projekt-forge owns the schema, the migration chain, and the backfill story. Both features reuse the v1.1.0 minor-bump ceremony (barrel re-export → pyproject.toml → regression test → annotated tag → push). The only dependency change is bumping `mcp[cli]>=1.0` to `mcp[cli]>=1.19,<2` to pick up the `meta=` parameter on `FastMCP.tool()` (landed in SDK 1.19.0) while capping below the in-progress v2 rename (`FastMCP → MCPServer`).

The primary new risk is a **second prompt-injection surface**: consumer-supplied `ctx.tags` already reach the synthesis LLM (Phase 6-02 additive-only hook), and v1.2 renders those same strings back to *every* LLM that calls `tools/list`. A `_sanitize_tag()` helper (strip control chars, reject injection markers, truncate to 64 chars, ≤16 tags per tool, ≤4KB `_meta` per tool) is a required Phase 7 deliverable, not a nice-to-have. The secondary risk is connection-pool exhaustion on the SQL side if EXT-03 is implemented with a long-lived session, retry-in-callback, or cross-loop session usage — mitigated by mandating one-session-per-callback (context-managed), no in-callback retry (durability comes from JSONL + backfill), and a recommended **sync SQLAlchemy callback** (matches Flame-thread `record()` call sites without an "event loop is closed" footgun).

## Key Findings

### Recommended Stack

One pin change. No new dependencies. See `STACK.md` for full rationale.

**Pin bump:**
- `mcp[cli]>=1.0` → `mcp[cli]>=1.19,<2` in `pyproject.toml` — floor is first SDK release with `meta=` param on `FastMCP.tool()` (PR #1463, v1.19.0, Oct 2025); cap avoids accidental breakage from the `FastMCP → MCPServer` rename underway on `main` (post-v1.27).

**No changes (researched-and-confirmed-negative):**
- `typing.Protocol` + `@runtime_checkable` → stdlib since 3.8; forge-bridge is 3.10+; no `typing_extensions` needed.
- `sqlalchemy[asyncio]>=2.0`, `alembic>=1.13`, `asyncpg`, `psycopg2-binary` → already carried from v1.0; EXT-03 doesn't add to them because all DDL lives in projekt-forge.

**Out-of-repo (projekt-forge owns):** `alembic.ini`, `migrations/versions/YYYYMMDD_add_execution_log.py`, `ExecutionLogRow` ORM class. See STACK.md "Alembic chain strategy" — single chain in projekt-forge, not layered chains.

### Expected Features

See `FEATURES.md` for full breakdown. REQ-ID labels preserved from research.

#### EXT-02 (Phase 7) — Tool provenance in MCP annotations

**Table stakes (MUST-HAVE):**
- **TS-02.1** — Lift `.tags.json` sidecar into tool registration. Watcher reads `path.with_suffix(".sidecar.json")` (fallback `.tags.json` for grace period), passes through to `register_tool(..., provenance=...)`. Minimum payload: `tags=["synthesized", *sidecar_tags]` so clients can filter.
- **TS-02.2** — Canonical provenance fields in `_meta` under the `forge-bridge/` namespace: `forge-bridge/origin` (`"synthesizer"`/`"builtin"`), `forge-bridge/code_hash`, `forge-bridge/synthesized_at`, `forge-bridge/version`, `forge-bridge/observation_count`. Reverse-DNS namespacing per MCP spec to avoid collision with future reserved keys.
- **TS-02.3** — Safety default: set `annotations.readOnlyHint=False` on every synthesized tool (they call `bridge.execute()` which runs arbitrary Python). Explicit, not inferred — MCP clients auto-approve read-only tools.

**Differentiators (DEFER to v1.3):**
- **DF-02.1** — Per-consumer `_meta` prefixes (e.g. `forge.projekt.*`) — waits on projekt-forge schema.
- **DF-02.2** — `title=` from `ExecutionRecord.intent` — small UX win, deferrable.
- **DF-02.3** — MCP resource `forge://synthesized/manifest` — this is the EXT-01 idea re-framed; defer until EXT-02 has clarified the schema in practice.

#### EXT-03 (Phase 8) — SQL persistence backend

**Table stakes (MUST-HAVE):**
- **TS-03.1** — `StoragePersistence` `typing.Protocol` in new module `forge_bridge/learning/storage.py`. Shape: `async def persist(self, record: ExecutionRecord) -> None; async def persist_batch(...); async def shutdown() -> None`. Modeled on OpenTelemetry's SpanExporter (single, batch, shutdown). `@runtime_checkable` for advisory isinstance checks.
- **TS-03.2** — Canonical minimal schema documented **in the Protocol docstring only** (no DDL shipped): columns `code_hash` (TEXT, 64), `timestamp` (TIMESTAMPTZ), `raw_code` (TEXT), `intent` (TEXT NULL), `promoted` (BOOLEAN). Unique constraint on `(code_hash, timestamp)`; index on `code_hash`; index on `timestamp DESC`.
- **TS-03.3** — Idempotent write via `insert(...).on_conflict_do_nothing(index_elements=["code_hash", "timestamp"])` — documented as an implementation requirement for consumers. Handles crash-replay + defensive double-fire atomically.
- **TS-03.4** — Backfill decision: projekt-forge-owned one-shot CLI (`forge-ctl db backfill-executions`) reads JSONL → calls `persist()` with `on_conflict_do_nothing`. PITFALLS P-03.4 recommends **cutover instead of backfill** for simplicity; planning-phase call.

**Differentiators (DEFER):**
- **DF-03.1** — `persist_batch()` with 100-row chunks (only needed when backfill gets slow).
- **DF-03.2** — Retention/cleanup (`DELETE WHERE timestamp < now() - interval '90 days'`).
- **DF-03.3** — `shutdown()` present from day 1 in the Protocol even if no-op.
- **DF-03.4** — Promotion-event mirror (`mark_promoted` does not fire the callback today — flag for Phase 8 planning whether this is a schema gap).

### Architecture Approach

See `ARCHITECTURE.md` for file:symbol detail.

**EXT-02 integration points (forge-bridge only):**

| File | Change | Symbol |
|------|--------|--------|
| `forge_bridge/learning/watcher.py` | Modified | `_scan_once` + new `_read_sidecar` helper |
| `forge_bridge/mcp/registry.py` | Modified | `register_tool` (internal) gains `provenance: dict \| None = None` kwarg; merged into existing `meta={"_source": source}` under `forge-bridge/*` keys |
| `forge_bridge/learning/synthesizer.py` | Modified | Sidecar schema bump `.tags.json` → `.sidecar.json` with `schema_version: 1`; WR-02 docstring fix on `ExecutionRecord`/`mark_promoted` drift |
| `tests/learning/test_watcher_sidecar.py` | New | sidecar present/missing/malformed cases |
| `tests/mcp/test_registry_provenance.py` | New | annotations merge + source-tag preserve |
| `README.md` | Modified | conda-env polish item bundled into Phase 7 |
| `forge_bridge/__init__.py` | **Not modified** | No new public symbols for EXT-02; provenance is transport-level, not API |

**EXT-03 integration points (forge-bridge only; consumer impl in projekt-forge):**

| File | Change | Symbol |
|------|--------|--------|
| `forge_bridge/learning/storage.py` | New | `StoragePersistence` Protocol, `@runtime_checkable` |
| `forge_bridge/__init__.py` | Modified | Re-export `StoragePersistence`; `__all__` grows 15 → **16** |
| `tests/learning/test_storage_protocol.py` | New | isinstance-check contract test |

**`__all__` changes:** Exactly +1 for the whole milestone (`StoragePersistence`). EXT-02 adds nothing to the public surface — annotations ride the MCP wire, not a Python import.

**`set_storage_callback` / `register_tools` signatures:** **Unchanged.** Protocol is documentation; `register_tool` (internal, not `register_tools`) grows one kwarg.

### Critical Pitfalls

Top 5 load-bearing pitfalls that constitute **phase-planning gates** — roadmapper must surface these as plan tasks, not discover them in execution. See `PITFALLS.md` for the full list.

1. **P-02.5 + Privacy — new prompt-injection surface via `_meta` → `tools/list`** (EXT-02, Phase 7). Consumer-supplied tags reach a second LLM-facing surface at MCP rendering time — different threat model than Phase 6's synthesis-time injection. **Required Phase 7 deliverable:** `_sanitize_tag()` helper that strips control chars, rejects injection markers (`ignore previous`, `<|`, `[INST]`, triple-backtick, `---`), truncates to 64 chars, logs WARNING on reject. Non-negotiable — 2026 CVE context (Anthropic's own Git MCP server had three such CVEs in Jan 2026) makes this table-stakes security hygiene.

2. **P-02.1 — `_meta` vs `annotations` is NOT interchangeable** (EXT-02, Phase 7 gate). MCP `Tool.annotations` is a closed schema of five behavior hints (`title`, `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`); spec-compliant clients MUST ignore unknown annotation keys from untrusted servers. Provenance data goes in `Tool._meta` (documented freeform extension bag), never in `annotations`. **Required Phase 7-01 CONTEXT.md decision lock.**

3. **P-03.1 + P-03.8 — SQL session scoping and sync-over-async** (EXT-03, Phase 8). One session per callback, `async with async_sessionmaker.begin()`, no long-lived sessions bound to `ExecutionLog`. **Recommended implementation pattern:** projekt-forge registers a **sync** storage callback using sync `sessionmaker` — not `AsyncSession`. Rationale: `record()` can fire from a sync Flame thread with no running event loop; async callback silently drops with `RuntimeError: no running loop`. Sync sidesteps the footgun entirely; SQLAlchemy sync and async sessions coexist fine in the same process. Gate this in Phase 8-01 CONTEXT.md.

4. **P-03.5 — No retry in the storage callback, ever** (EXT-03, Phase 8). Durability comes from JSONL + backfill, not retry-in-callback. Retries stack async tasks (bounded only by asyncio's task queue) — a 30-second DB outage at 10/sec synthesis = 300 stacked tasks each holding a connection attempt = QueuePool exhaustion, which is exactly the failure mode we're preventing. One try/except, one WARNING log, return. Circuit-breaker shape documented in CONTEXT.md as a deferred pattern, not built.

5. **I-3 + I-4 — Ship order matters; don't bundle in one tag** (Integration, both phases). Phase 7 (EXT-02) ships first as `v1.2.0`; projekt-forge UATs it; then Phase 8 (EXT-03) ships as `v1.2.1` or `v1.3.0`. Separate tags let projekt-forge pin forward/back independently. `ExecutionRecord` field additions require a minor bump + coordinated projekt-forge pin update.

## Implications for Roadmap

### Phase count: **2 phases** (Phase 7, Phase 8) — strictly sequential, not parallelizable

Two structural coupling risks forbid parallelism: (a) both phases touch `forge_bridge/__init__.py` `__all__` (race on the barrel + tag ceremony conflict); (b) Phase 8 may want to consume `ExecutionRecord` field additions that Phase 7 inspires, but `ExecutionRecord` is a D-03-locked frozen dataclass — parallel work risks committing a schema that misses a field the other phase wants. The low-friction sequential path is faster in total wall-clock time.

### Phase 7: EXT-02 Tool Provenance in MCP Annotations (→ v1.2.0)

**Rationale:** Smaller change, no consumer-side implementation dependency (unlike EXT-03 which needs projekt-forge's SQLAlchemy backend to verify end-to-end). The sidecar-to-annotation path lives entirely in forge-bridge (watcher + registry). Ships first because: (a) annotation changes are transparent to consumers not reading `_meta`; (b) EXT-02's sidecar pipeline produces the concrete `_meta` shape that EXT-03 can inspect when deciding "should the DB mirror any `_meta` fields as indexed columns?"; (c) it's the harder lift (sanitization, size budget, redaction allowlist, PII policy) and benefits from shipping before attention shifts to SQL.

**Delivers:**
- `.tags.json` → `.sidecar.json` rename with `schema_version: 1` envelope (write path in synthesizer; read path in watcher with `.tags.json` backward-compat grace window)
- `register_tool(..., provenance={"tags": [...], "meta": {...}})` internal kwarg; merges into existing `meta={"_source": ...}` under `forge-bridge/*` keys
- `_sanitize_tag()` helper + 4 KB per-tool, 16-tags-per-tool, 64-char-per-tag ceilings
- Redaction allowlist: `project:`, `phase:`, `shot:`, `type:` prefixes pass through; everything else → `redacted:<sha256[:8]>`; optional consumer-supplied `redact_fn` hook
- `annotations.readOnlyHint=False` safety baseline on all synthesized tools
- WR-02 docstring drift fix on `ExecutionRecord` vs `mark_promoted`
- README conda-env guidance (v1.1 polish carry-over)

**Addresses:** TS-02.1, TS-02.2, TS-02.3.
**Avoids:** P-02.1, P-02.2, P-02.3, P-02.5, P-02.6, P-02.7 (live-UAT diff gate).
**Plans (suggested): 4**
  - 07-01 — Provenance contract + sidecar schema evolution (`.sidecar.json` + `schema_version`)
  - 07-02 — Synthesizer + watcher wiring + `_sanitize_tag` + size budget
  - 07-03 — `register_tool` provenance kwarg + registry meta merge + tests
  - 07-04 — Release ceremony: `mcp[cli]>=1.19,<2` pin bump, regression test, `v1.2.0` tag, projekt-forge pin bump + UAT diff

### Phase 8: EXT-03 SQL Persistence Protocol (→ v1.2.1 or v1.3.0)

**Rationale:** Gated on Phase 7 shipping and projekt-forge UAT clean. Protocol-only on the bridge side; real validation happens in projekt-forge's SQLAlchemy backend. Phase 5's lesson: two-repo phases are expensive — keep forge-bridge's delivery tight (one file + one barrel entry) so cross-repo coordination is minimized.

**Delivers:**
- `forge_bridge/learning/storage.py` with `StoragePersistence` Protocol (persist, persist_batch, shutdown) + documented consistency model
- Canonical schema documented in Protocol docstring (NOT as DDL)
- `forge_bridge/__init__.py` re-export; `__all__` grows 15 → 16
- Phase 8-01 CONTEXT.md decision lock: forge-bridge ships Protocol only; projekt-forge owns schema, Alembic chain, migrations, backfill
- Recommended sync-callback pattern documented (P-03.8)
- No-retry invariant documented (P-03.5)
- `set_storage_callback` signature unchanged (Protocol is documentation)
- projekt-forge: `_persist_execution` body swapped logger → SQL; isinstance-check at registration; cutover OR backfill script (planning decision per P-03.4)

**Addresses:** TS-03.1, TS-03.2, TS-03.3, TS-03.4.
**Avoids:** P-03.1, P-03.2, P-03.3, P-03.5, P-03.7, P-03.8, P-03.9.
**Plans (suggested): 3**
  - 08-01 — `StoragePersistence` Protocol + barrel re-export + consistency-model CONTEXT.md
  - 08-02 — projekt-forge sync SQLAlchemy adapter + Alembic revision + `on_conflict_do_nothing` + cutover-vs-backfill decision
  - 08-03 — Release ceremony: `v1.2.1` (or `v1.3.0`) tag + projekt-forge pin bump + UAT DB writes

### Phase Ordering Rationale

- Phase 7 before Phase 8, non-negotiable — shared `__all__` barrel edits + potential `ExecutionRecord` evolution make concurrent landing risky.
- Phase 7 ships a full release (`v1.2.0`) before Phase 8 starts. projekt-forge pins `@v1.2.0`, UATs live `tools/list` with provenance visible, THEN Phase 8 begins. Matches v1.1 strict phase-ordering pattern (Phase 5 → Phase 6 gated; Phase 6 → v1.1.0 tag gated on UAT).
- Neither phase touches locked v1.1 non-goals: no `LLMRouter` hot-reload, no shared-path JSONL writers, no `set_storage_callback` signature change, no `ExecutionRecord` field additions without minor bump + migration review.

### Research Flags

Phases with standard patterns (no mid-planning research spike expected):
- **Phase 7** — MCP `_meta` pattern is spec-stable; FastMCP SDK `meta=` param verified; sanitization patterns are off-the-shelf.
- **Phase 8** — `typing.Protocol` + `@runtime_checkable` are PEP 544 stable stdlib since 3.8. SQLAlchemy `async_sessionmaker.begin()` context-manager pattern is documented canonical.

Phases that may benefit from targeted spike during planning:
- **Phase 8-02 (projekt-forge SQLAlchemy adapter)** — one planning-phase decision: ship `ExecutionLogMixin` SQLAlchemy declarative mixin from forge-bridge (couples package to ORM API, prevents schema drift) vs. projekt-forge defines its own ORM class (cleaner package boundary, accepts drift risk). Research confidence on recommendation: MEDIUM.
- **Phase 8-02 backfill-vs-cutover** — planning decision per P-03.4. Research recommends cutover for simplicity but flags both as valid.
- **Phase 7-02 — whether `ExecutionRecord.intent` → MCP `title`** — small UX decision, not a research gap.

## Sidecar Schema Evolution Decision

**YES — rename `.tags.json` → `.sidecar.json` with `{"tags": [...], "meta": {...}, "schema_version": 1}` envelope. Phase 7 owns the write-path change.**

Rationale:
- **One file, one load, one atomic write** — both `tags` (for `FastMCP.tool(tags=...)` filter/enable) and canonical provenance `meta` (for `_meta["forge-bridge/*"]`) ship together. Today's `.tags.json` is `{"tags": [...]}` only — EXT-02 needs a meta payload alongside; adding a second sidecar would double the atomic-write surface.
- **`schema_version: 1` costs nothing now** — lets future sidecar evolutions be detected without silently breaking old consumers.
- **Grace window for backward compat** — watcher reads **both** for a migration window: prefer `.sidecar.json`, fall back to `.tags.json`. Synthesizer writes only `.sidecar.json` from v1.2.0 onwards.
- **Lock in Phase 7-01, not 7-03** — update `synthesizer.py` write path + add round-trip read test **before** building the watcher/loader/register_tools side that consumes it.

**Plan ownership:** Phase 7-01 owns the synthesizer write-path rename + `schema_version: 1` envelope + round-trip test. Phase 7-02 owns the watcher read-path (with `.tags.json` fallback) and the `register_tool(..., provenance=...)` wiring. Phase 7-03 owns tests + size budget + sanitization. Phase 7-04 owns release ceremony.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | MCP spec (2025-06-18) + SDK changelog + live-verified `meta=` roundtrip on installed `mcp==1.26.0`. PEP 544 behavior verified locally on Python 3.11. |
| Features | HIGH | MCP `_meta` namespacing convention confirmed via 2026-03 "Tool Annotations as Risk Vocabulary" spec blog; OpenTelemetry SpanExporter provides a canonical template for the three-method Protocol shape. |
| Architecture | HIGH | Integration points derived from direct source reads. `__all__` delta (+1) is mechanically derivable. Phase-ordering rationale has concrete conflict examples. |
| Pitfalls | HIGH | Direct source analysis + 2026-era prompt-injection research (CyberArk Poison Everywhere, Unit 42 MCP Sampling, Anthropic Git MCP CVEs January 2026). SQLAlchemy 2.0 async patterns verified against current docs. |

**Overall confidence:** HIGH

### Gaps to Address During Planning

- **ExecutionLogMixin ship-or-defer** (Phase 8 planning) — MEDIUM confidence recommendation; planning-phase judgment call.
- **Backfill vs cutover** (Phase 8 planning) — P-03.4 recommends cutover; if projekt-forge needs historic reconstruction, ship backfill.
- **EXT-02 attach point** — watcher reads `.sidecar.json` at registration (recommended) vs synthesizer stashes `__forge_meta__` on function object. Recommend watcher-reads-sidecar; lock in 07-01.
- **`title=` / `description=` from sidecar** (Phase 7 planning) — small UX decision.
- **`mark_promoted` callback mirror** (Phase 8 planning) — DF-03.4 flag.
- **`ExecutionRecord` evolution pressure** — explicit carve: EXT-02 reads from `.sidecar.json` only, never from `ExecutionRecord`. Lock in Phase 7-01 CONTEXT.md.

## Sources

### Primary (HIGH confidence)
- Direct source analysis — `forge_bridge/learning/{execution_log,synthesizer,watcher,manifest,probation}.py`, `forge_bridge/mcp/registry.py`, `forge_bridge/__init__.py` (v1.1.1)
- MCP Specification 2025-06-18 — https://modelcontextprotocol.io/specification/2025-06-18/server/tools
- MCP Tool Annotations as Risk Vocabulary (2026-03-16) — https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/blog/content/posts/2026-03-16-tool-annotations.md
- MCP Python SDK release notes + PR #1463 (v1.19.0 `meta=` on `FastMCP.tool()`)
- Live verification: `mcp==1.26.0` on Python 3.11.x
- PEP 544 — Protocols
- SQLAlchemy 2.0 `async_sessionmaker.begin()` docs
- OpenTelemetry Python `SpanExporter` Protocol
- `.planning/milestones/v1.1-ROADMAP.md`, `.planning/PROJECT.md`

### Secondary (MEDIUM confidence)
- CyberArk "Poison Everywhere: No output from your MCP server is safe"
- Unit 42 "New Prompt Injection Attack Vectors Through MCP Sampling"
- Practical DevSecOps MCP Security Vulnerabilities 2026
- SQLAlchemy async issue #8145, discussion #5994
- Celery result backend — `BaseBackend` subclass contract precedent

---
*Research completed: 2026-04-19*
*Ready for roadmap: yes — 2 phases, strictly sequential, separate release tags*
