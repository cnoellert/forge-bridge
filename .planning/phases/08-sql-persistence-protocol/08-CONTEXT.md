# Phase 8: SQL Persistence Protocol - Context

**Gathered:** 2026-04-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Define a typed `StoragePersistence` Protocol in `forge_bridge/learning/storage.py` that consumers implement to mirror `ExecutionLog.record()` writes into durable storage. Replace projekt-forge's `_persist_execution` stub with a sync SQLAlchemy adapter that inserts rows idempotently into projekt-forge's **existing** Postgres (via a new Alembic revision on projekt-forge's **existing** chain), and logs-and-swallows DB outages without retrying in the callback.

forge-bridge ships Protocol + docstring only: no models, no migrations, no Alembic, no SQL dialect assumptions in code. projekt-forge owns schema, table name, migration chain, and connection management.

</domain>

<decisions>
## Implementation Decisions

### Protocol Shape

- **D-01 (signature — duck-typed return):** `persist(self, record: ExecutionRecord) -> None | Awaitable[None]`. Matches the existing `StorageCallback = Callable[[ExecutionRecord], Union[None, Awaitable[None]]]` already shipped in `forge_bridge/learning/execution_log.py:53`. The Protocol is a typed restatement of what `set_storage_callback()` already accepts — not a new contract. `inspect.iscoroutinefunction` at registration resolves sync vs async dispatch.
- **D-02 (method set — `persist` ONLY):** Ship one method for v1.3.0. No `persist_batch`, no `shutdown`. **Deviation from ROADMAP.md's "Suggested plan structure"** which listed three methods — that line was provisional and is superseded by this decision. Rationale: one consumer today (projekt-forge), session-per-call has nothing to clean up, batching parked in DF-03.1 until backfill demand emerges. Additive evolution preserved via a future `BatchingStoragePersistence(StoragePersistence)` sub-Protocol.
- **D-03 (`@runtime_checkable`):** Decorated so consumers can `isinstance(fn, StoragePersistence)` at registration as a sanity check. Method-presence only; signature is not enforced at runtime.
- **D-04 (canonical schema in docstring):** The Protocol class docstring carries the minimal SQL schema that implementations MUST preserve for cross-consumer compatibility:

  ```
  CREATE TABLE <name> (
      code_hash   TEXT        NOT NULL,
      timestamp   TIMESTAMPTZ NOT NULL,
      raw_code    TEXT        NOT NULL,
      intent      TEXT        NULL,
      UNIQUE (code_hash, timestamp)
  );
  CREATE INDEX ix_<name>_code_hash ON <name>(code_hash);
  CREATE INDEX ix_<name>_timestamp ON <name>(timestamp DESC);
  ```

  **Four columns.** `promoted` deliberately OMITTED (see D-08). No DDL ships in forge-bridge; the docstring documents what projekt-forge's Alembic revision must create.

### Consistency & Error Model

- **D-05 (consistency — log-authoritative, eventual, best-effort):** JSONL is source of truth; DB is a best-effort mirror. A row in DB implies a row in JSONL; reverse is not guaranteed. Queries for promotion-invariants MUST use `ExecutionLog.get_count()` or JSONL scan, NOT the DB. Documented explicitly in the Protocol's module docstring AND in projekt-forge's adapter docstring.
- **D-06 (no retry — EVER):** `_persist_execution` body is `try / except: logger.warning(...); return` — no `tenacity`, no `backoff`, no inner retry loop. Rationale (P-03.5): retry stacks async tasks / DB connections; JSONL durability + optional backfill handle recovery. Invariant holds regardless of sync/async dispatch — retry creates QueuePool exhaustion under sustained outage.
- **D-07 (sync callback — projekt-forge's adapter):** `def persist(self, record)` — synchronous, uses `sessionmaker.begin()` context manager (NOT `async_sessionmaker.begin()`). Rationale (P-03.8): `ExecutionLog.record()` can fire from Flame threads where no event loop is running; async callback silently drops via `asyncio.ensure_future` RuntimeError path (`execution_log.py:220`). Sync dispatch has no such failure mode.

### Schema Shape

- **D-08 (NO `promoted` column in v1.3.0):** The canonical schema has no `promoted` column. Rationale: `ExecutionLog.mark_promoted()` writes to JSONL but does NOT fire the storage callback (`execution_log.py:237-252`); a `promoted` column would always be False at insert and never updated, producing a false-negative query landmine. Promotion state stays JSONL-only for v1.2 / v1.3.0. A proper mirror hook (e.g. `set_promotion_callback`) is deferred to v1.3.x with its own requirement.
- **D-09 (idempotency):** projekt-forge's adapter uses `insert(...).on_conflict_do_nothing(index_elements=["code_hash", "timestamp"])` (PostgreSQL dialect; native to projekt-forge's existing PG deployment). Two forge-bridge processes writing to distinct JSONL paths but sharing the projekt-forge DB produce no duplicate rows. Same `code_hash` with distinct `timestamp` is expected (different execution instances) and both rows persist.

### Callback Wiring & isinstance

- **D-10 (`set_storage_callback()` signature unchanged):** Identical to v1.1.0. Consumers pass `backend.persist` (bound method) as the existing callable. The Protocol is documentation / type-check only; the runtime dispatch path is unchanged. STORE-03 satisfied.
- **D-11 (isinstance at registration — projekt-forge side):** In projekt-forge's wiring code (the path currently calling `ExecutionLog.set_storage_callback(self._persist_execution)`), add `assert isinstance(self.persist, StoragePersistence)` as a startup-time sanity check. If the Protocol ever grows a required method (v1.3+), stale projekt-forge pins fail at startup with a clear error instead of silently writing nothing. **Bridge code does NOT assert isinstance** — the callable is accepted as-is (duck-typed pass-through, preserving STORE-03).

### Cross-Repo Coordination

- **D-12 (Plan 08-02 is cross-repo):** The SQLAlchemy adapter, Alembic revision, `isinstance` sanity check, adapter unit tests, and simulated-outage test all land in `/Users/cnoellert/Documents/GitHub/projekt-forge/`. Mirrors the Phase 6-04 cross-repo wave pattern.
- **D-13 (Alembic — projekt-forge's existing chain):** projekt-forge's existing migration chain is extended with ONE new revision creating the `execution_log` table (projekt-forge owns the table name — planner confirms at time-of-plan whether `execution_log` collides with anything existing; if so, `forge_execution_log` is the fallback). forge-bridge ships NO Alembic of its own. projekt-forge's existing `alembic_version` table tracks the migration.

### Release & Versioning

- **D-14 (version — v1.3.0 MINOR):** forge-bridge bumps to v1.3.0, NOT v1.2.2 (patch). Rationale: `__all__` grows 15 → 16 (adds `StoragePersistence`); Phase 6 precedent locks barrel growth → minor bump. v1.3.0 also cleanly signals v1.2 "Observability & Provenance" milestone closure. SemVer cares about surface, not observable behavior of existing callers.
- **D-15 (release ceremony):** Reuses Phase 6 / Phase 7 / Phase 07.1 pattern — bump `pyproject.toml` (`1.2.1` → `1.3.0`), update `tests/test_public_api.py` version guard AND `__all__` membership list, annotated `v1.3.0` tag on `main`, GitHub release with wheel + sdist from `python -m build`. projekt-forge pin bump `@v1.2.1` → `@v1.3.0` + `pip install -e` in the `forge` conda env + regression-gate `pytest tests/` at its baseline.

### Claude's Discretion

- Test file names (planner — `tests/learning/` convention; `test_storage_protocol.py` is a reasonable default).
- Alembic revision ID and slug in projekt-forge (planner — convention-match existing chain).
- Exact Protocol docstring wording (writer — must cover schema, consistency, no-retry invariant, sync-callback recommendation).
- Commit message phrasing (writer — match Phase 6/7 precedent: `feat(learning): add StoragePersistence Protocol (STORE-01..04)`, separate `chore(release): bump ... 1.2.1 → 1.3.0`, separate cross-repo commit in projekt-forge).
- Contract test fixture shape (planner — `types.SimpleNamespace` with a `persist` attr, OR a minimal class with a `persist` method).
- CHANGELOG.md introduction at 08-03 (planner judges — v1.3.0 is a reasonable anchor for milestone close; still not a stated requirement).
- Whether to squash the Protocol module + barrel re-export + contract test into ONE atomic commit vs split (planner picks; Phase 6 precedent leaned toward atomic).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### forge-bridge source (integration targets)

- `forge_bridge/learning/execution_log.py` — `ExecutionRecord` frozen dataclass (lines 33-51), `StorageCallback` type alias (line 53), `ExecutionLog.set_storage_callback()` (lines 121-145), `record()` dispatch path (lines 215-231), `mark_promoted()` (lines 237-252 — note it does NOT fire the callback, which is the root of D-08)
- `forge_bridge/__init__.py` — `__all__` barrel at 15 symbols today (lines 54-75); Phase 8 grows to 16 by adding `StoragePersistence`
- `forge_bridge/learning/__init__.py` — existing re-exports; `StoragePersistence` lives here and re-exports to package root
- `pyproject.toml` — version field (`1.2.1` → `1.3.0`)
- `tests/test_public_api.py` — version-guard string AND `__all__` membership list (Phase 7 / 07.1 precedent for how to update both)

### Research & prior-phase artifacts (read these first — they lock most of the design)

- `.planning/research/PITFALLS.md` §"EXT-03 pitfalls — SQL persistence backend for `ExecutionLog`" — P-03.1 through P-03.9; every pitfall has phase ownership and concrete deliverable mapping (lines 62-136)
- `.planning/research/PITFALLS.md` §"Integration pitfalls — EXT-02 ↔ EXT-03" — I-1 through I-4; particularly I-1 (don't couple MCP `_meta` shape to DB schema) and I-4 (separate tags per feature) (lines 138-184)
- `.planning/ROADMAP.md` §"Phase 8: SQL Persistence Protocol" — success criteria, locked non-goals, suggested plan structure (provisional — superseded by D-02 above), cross-repo coordination table (lines 90-110)
- `.planning/REQUIREMENTS.md` §"Storage Backend (Phase 8 — EXT-03)" — STORE-01 through STORE-06 requirement text (lines 19-27)
- `.planning/phases/07.1-startup-bridge-graceful-degradation-hotfix-deployment-uat/07.1-CONTEXT.md` — release ceremony shape for v1.2.x (reusable pattern for v1.3.0)

### Phase precedent (release ceremony + cross-repo pattern)

- `.planning/phases/06-*/` — Phase 6 CONTEXT/PLAN/SUMMARY artifacts; Plan 06-04 is the cross-repo wave pattern Phase 8-02 mirrors
- `.planning/phases/07-tool-provenance-in-mcp-annotations/` — Phase 7 release ceremony (v1.2.0) precedent
- Commit `0987525` — v1.2.0 release commit shape
- Commits on Phase 07.1 tagging `v1.2.1` — most recent release ceremony reference

### projekt-forge cross-repo

- `/Users/cnoellert/Documents/GitHub/projekt-forge/pyproject.toml` — line 25 has current `@v1.2.1` pin (bump to `@v1.3.0` after forge-bridge tag lands)
- `/Users/cnoellert/Documents/GitHub/projekt-forge/` — the `_persist_execution` stub target (grep for `_persist_execution`; currently a logger stub per Phase 6 LRN-02 decision)
- projekt-forge's existing Alembic chain — location verifiable at plan time (`projekt_forge/db/alembic/versions/` or equivalent); Plan 08-02 adds ONE revision to this chain

### External docs (SQLAlchemy / Alembic — look these up at plan time with Context7 for current syntax)

- SQLAlchemy 2.0 docs — §"Managing Transactions" for `sessionmaker.begin()` context-manager pattern; §"PostgreSQL Dialect" for `insert(...).on_conflict_do_nothing(index_elements=[...])` usage
- Alembic docs — §"Working with Branches" (reference only; projekt-forge's chain stays linear and single-head per D-13)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `StorageCallback` type alias (`forge_bridge/learning/execution_log.py:53`) — the Protocol is a typed restatement; the callable contract is unchanged
- `ExecutionRecord` frozen dataclass — payload is stable, no new fields in Phase 8 (P-03.7)
- `ExecutionLog.set_storage_callback()` + `inspect.iscoroutinefunction` dispatch (lines 121-145) — unchanged; Phase 8 adds NO new wiring on forge-bridge side
- Existing Phase 6/7 release ceremony tooling — `python -m build`, `gh release create`, annotated-tag pattern

### Established Patterns

- **Barrel re-export:** new public symbols land in `forge_bridge/learning/<module>.py` → re-exported by `forge_bridge/learning/__init__.py` → re-exported by `forge_bridge/__init__.py` → listed in `__all__` → asserted in `tests/test_public_api.py`
- **Release ceremony:** `pyproject.toml` bump → `test_public_api.py` version-guard update → `git commit -m "chore(release): bump ..."` → `git tag -a v1.3.0` → `git push origin main --tags` → GitHub release with wheel + sdist
- **Cross-repo handoff:** plan lands in forge-bridge first (tag released), THEN projekt-forge bumps pin + reinstalls in `forge` conda env + regression-gates `pytest tests/` at its baseline (422 as of 07.1)

### Integration Points

- `forge_bridge/__init__.py:35-39` — learning pipeline re-export block; `StoragePersistence` goes alongside `StorageCallback`
- `forge_bridge/__init__.py:54-75` — `__all__` list grows by one entry
- `tests/` (forge-bridge) — contract test file for `StoragePersistence` isinstance behavior (positive and negative cases); pattern like the existing `tests/learning/test_execution_log.py`

</code_context>

<specifics>
## Specific Ideas

- **`execution_log` table lives in projekt-forge's EXISTING Postgres** (the one backing shots / entities / events). Same DB, new table. Single Alembic head via projekt-forge's existing chain — no version-table collision, no shared-chain complexity. User confirmed this during discussion.
- **Protocol docstring schema is normative.** The minimal schema in the Protocol's class docstring is the contract; projekt-forge's Alembic migration MUST match (columns + unique constraint + indexes). If a future consumer deviates, it's their responsibility to provide equivalent query performance.
- **Test scaffolding shape:**
  - forge-bridge: `tests/learning/test_storage_protocol.py` — `isinstance` positive (class with `persist`), `isinstance` negative (object missing `persist`, or callable that isn't an instance)
  - projekt-forge: adapter unit test + simulated-outage test. In-memory SQLite fallback for CI is reasonable; a marker-gated integration test against projekt-forge's real PG validates the full path
  - Simulated-outage test: mock session to raise `OperationalError`, verify single WARNING logged, no exceptions propagate to `ExecutionLog.record()`, JSONL write unaffected, no retry-task stacking
- **Cutover, not backfill.** projekt-forge's adapter starts writing from the moment the v1.3.0 pin takes effect. Pre-cutover JSONL rows do NOT get backfilled into DB. If reconciliation is ever needed, it's a projekt-forge script OUT of the storage callback's hot path (P-03.5).
- **Suggested plan structure (3 plans — supersedes ROADMAP.md's provisional list which assumed three-method Protocol):**
  - **08-01** — `StoragePersistence` Protocol module (`forge_bridge/learning/storage.py`) with `persist` only; barrel re-export through `forge_bridge/learning/__init__.py` → `forge_bridge/__init__.py`; `__all__` grows 15 → 16; contract test in `tests/learning/test_storage_protocol.py`; Protocol docstring carries minimal schema + consistency model + no-retry invariant + sync-callback recommendation. Covers STORE-01..04, STORE-06.
  - **08-02** *(CROSS-REPO — lands in `/Users/cnoellert/Documents/GitHub/projekt-forge/`)* — sync SQLAlchemy adapter replaces `_persist_execution` stub; new Alembic revision on projekt-forge's existing chain creates the `execution_log` table; `isinstance(self.persist, StoragePersistence)` sanity check at wiring time; adapter unit test + simulated-outage test; mirrors Phase 6-04 cross-repo wave pattern. Covers STORE-05.
  - **08-03** — Release ceremony: annotated `v1.3.0` tag on forge-bridge `main`; GitHub release (wheel + sdist); projekt-forge pin bump `@v1.2.1` → `@v1.3.0`; reinstall in `forge` conda env; regression-gate `pytest tests/` at baseline; milestone-close via `/gsd-complete-milestone`.

</specifics>

<deferred>
## Deferred Ideas

- **`set_promotion_callback` mirror hook (DF-03.4)** — addresses the `mark_promoted` → DB gap left open by D-08. New ExecutionLog API surface + sub-Protocol or new callback. v1.3.x requirement when a concrete consumer asks for promotion-state DB queries.
- **`persist_batch` + `shutdown` methods** — sub-Protocol `BatchingStoragePersistence(StoragePersistence)` when backfill / buffered-write demand emerges (DF-03.1). Additive; not v1.3.0.
- **Backfill script** — one-time JSONL → DB reconciliation tool. If projekt-forge needs it, they own it; OUT of forge-bridge's pip surface per P-03.4.
- **CHANGELOG.md introduction** — v1.3.0 is a reasonable anchor (milestone close). Still not a stated requirement; planner's call at 08-03.
- **Retention / cleanup policy for `raw_code`** — `raw_code TEXT NOT NULL` is stored per D-04. Retention SQL (e.g., `DELETE WHERE timestamp < now() - interval '90 days'`) lives in projekt-forge's operational tooling, not forge-bridge.
- **DF-02.x items** (per-consumer `_meta` prefixes, etc.) — v1.3+ roadmap once EXT-02 usage patterns clarify.
- **Circuit-breaker around the callback (P-03.6)** — shape documented in `.planning/research/PITFALLS.md` §P-03.6 for future reference. v1.3.0 explicitly does not retry in-callback; circuit-breaker deferred until/unless P-03.5 is ever overturned.
- **Additional `ExecutionRecord` fields** — P-03.7 / P-03.9 gate any future additions behind a migration-review requirement and a minor bump.

</deferred>

---

*Phase: 08-sql-persistence-protocol*
*Context gathered: 2026-04-21*
