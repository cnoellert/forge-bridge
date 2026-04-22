# Phase 8: SQL Persistence Protocol - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `08-CONTEXT.md` — this log preserves the alternatives considered.

**Date:** 2026-04-21
**Phase:** 08-sql-persistence-protocol
**Areas discussed:** Protocol signature shape, Method set, `promoted` column treatment, Release version

---

## Clarifying question (pre-discussion)

**User raised:** "We are deploying Postgres for the rest of projekt-forge — does it make sense to implement alongside that rather than moving to SQL?"

**Resolution:** Confirmation of a pre-locked decision, not a new gray area. Plan 08-02 already targets projekt-forge's existing Postgres via its existing Alembic chain (ROADMAP.md line 105). The `execution_log` table lives in the SAME DB as projekt-forge's shots / entities / events. Single Alembic head; no new infrastructure. Recorded as D-12 / D-13 in CONTEXT.md.

---

## Protocol signature shape

| Option | Description | Selected |
|--------|-------------|----------|
| Async-only | `async def persist(record) -> None` | |
| Sync-only | `def persist(record) -> None` | |
| Duck-typed union (Recommended) | `def persist(record) -> None \| Awaitable[None]` — matches existing `StorageCallback` | ✓ |

**User's choice:** Approve Claude's recommendation (duck-typed union).

**Notes:** The Protocol is a typed restatement of the existing `StorageCallback` type alias in `forge_bridge/learning/execution_log.py:53`. Async-only would break projekt-forge's sync adapter's `isinstance` check. Sync-only would reject any future async consumer. `inspect.iscoroutinefunction` in `set_storage_callback` already dispatches correctly for both shapes. User was beyond their granular expertise on this and asked for a strong reco — approved.

---

## Method set (persist-only vs three)

| Option | Description | Selected |
|--------|-------------|----------|
| persist + persist_batch + shutdown | All three required (matches ROADMAP.md's suggested structure) | |
| persist only (Recommended) | Ship one method; defer batch / shutdown to sub-Protocol in v1.3+ | ✓ |
| Core + optional sub-Protocol | `BatchingStoragePersistence(StoragePersistence)` alongside base | |

**User's choice:** Approve Claude's recommendation (persist only).

**Notes:** Deviation from the roadmap's provisional three-method list. Rationale: one consumer today (projekt-forge), session-per-call has nothing to shutdown, `persist_batch` parked in DF-03.1 until backfill demand emerges. Additive evolution path preserved via a future `BatchingStoragePersistence` sub-Protocol. CONTEXT.md D-02 explicitly flags the roadmap deviation.

---

## `promoted` column treatment (DF-03.4)

| Option | Description | Selected |
|--------|-------------|----------|
| Ship the column | `promoted BOOLEAN` column, always False at insert, never updated | |
| Drop from schema (Recommended) | Four-column schema; promotion state stays JSONL-only for v1.3.0 | ✓ |
| Add promotion callback hook | New `set_promotion_callback` API surface on `ExecutionLog` | |

**User's choice:** Approve Claude's recommendation (drop the column).

**Notes:** `mark_promoted()` (`execution_log.py:237-252`) does not fire the storage callback; shipping the column would produce a false-negative query landmine (downstream `WHERE promoted=true` always returns zero). Mirror hook is the "real" fix but deserves its own requirement + bump; deferred to v1.3.x.

---

## Release version

| Option | Description | Selected |
|--------|-------------|----------|
| v1.2.2 patch | Protocol is documentation; no functional change for existing consumers | |
| v1.3.0 minor (Recommended) | `__all__` grows 15 → 16; matches Phase 6 barrel-growth ceremony; closes v1.2 milestone cleanly | ✓ |

**User's choice:** Approve Claude's recommendation (v1.3.0).

**Notes:** New public symbol = SemVer-minor by convention. Phase 6 precedent locks the ceremony shape (barrel grow → pyproject bump → annotated tag → push → GitHub release). Milestone-close narrative — v1.3.0 cleanly signals "v1.2 Observability & Provenance shipped."

---

## Claude's Discretion (planner / writer picks)

- Test file names (`tests/learning/` convention; `test_storage_protocol.py` is a reasonable default).
- Alembic revision ID and slug in projekt-forge (convention-match existing chain).
- Exact Protocol docstring wording (must cover schema, consistency model, no-retry invariant, sync-callback recommendation).
- Commit message phrasing (match Phase 6/7/07.1 precedent).
- Contract test fixture shape (`types.SimpleNamespace` vs minimal class).
- CHANGELOG.md introduction at 08-03 (v1.3.0 is a reasonable anchor; still not a stated requirement).
- Whether to squash 08-01 into ONE atomic commit vs split (Phase 6 precedent leaned atomic).

---

## Deferred Ideas

- `set_promotion_callback` mirror hook (DF-03.4 — v1.3.x)
- `persist_batch` + `shutdown` via `BatchingStoragePersistence` sub-Protocol (DF-03.1 — v1.3+)
- Backfill script (projekt-forge-owned if needed; not forge-bridge pip surface)
- CHANGELOG.md introduction (deferred from 07.1; revisit at 08-03 release ceremony)
- Retention / cleanup policy for `raw_code` (projekt-forge operational tooling)
- Additional DF-02.x items (per-consumer `_meta` prefixes, etc.) — v1.3+ roadmap
- Circuit-breaker around callback (P-03.6 — documented but not built for v1.3.0)
- Future `ExecutionRecord` field additions (P-03.7 / P-03.9 gate behind migration review)

---

## Collaboration note

User explicitly asked Claude for recommendations rather than neutral option menus: *"This is beyond my understanding on a granular level and I'd prefer to make sure it's right."* All four recommendations were approved in a single turn. For future sessions in this domain (Python middleware, SQL schema, Protocol typing, SemVer mechanics), expect the user to trust-and-approve strong recos with rationale rather than pick between equally-weighted options.
