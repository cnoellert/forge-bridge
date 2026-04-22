---
phase: 08-sql-persistence-protocol
plan: "02"
subsystem: learning
tags:
  - cross-repo
  - projekt-forge
  - sqlalchemy
  - alembic
  - storage
  - adapter
dependency_graph:
  requires:
    - forge_bridge.StoragePersistence (from 08-01)
    - projekt_forge/db/migrations/versions/004_media_content_hash.py (chain anchor)
    - projekt_forge/learning/wiring.py (Phase 6 LRN-02 stub replaced)
  provides:
    - projekt_forge/db/migrations/versions/005_execution_log.py (Alembic revision)
    - projekt_forge/learning/wiring._persist_execution (sync SQLAlchemy adapter)
    - tests/test_persist_execution_adapter.py (9 adapter unit tests)
    - tests/test_learning_wiring.py (updated — sync-callback semantics)
  affects:
    - 08-03 (release ceremony: alembic upgrade head + forge-bridge v1.3.0 tag)
tech_stack:
  added:
    - "sqlalchemy.dialects.postgresql.insert (pg_insert) — ON CONFLICT DO NOTHING support"
    - "sqlalchemy.create_engine (sync psycopg2 URL) — D-07 sync over async"
    - "sqlalchemy.Table / MetaData Core descriptor — no ORM model needed for single INSERT"
  patterns:
    - "Sync SQLAlchemy adapter: _get_sync_engine() lazy cache + engine.begin() auto-commit"
    - "Protocol satisfaction via function attribute: _persist_execution.persist = _persist_execution"
    - "Log-and-swallow exception handler: type(exc).__name__ only — no str(exc) credential leak"
    - "Alembic hand-written migration: composite UNIQUE + DESC index not auto-detected"
key_files:
  created:
    - /Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/db/migrations/versions/005_execution_log.py
    - /Users/cnoellert/Documents/GitHub/projekt-forge/tests/test_persist_execution_adapter.py
  modified:
    - /Users/cnoellert/Documents/GitHub/projekt-forge/projekt_forge/learning/wiring.py
    - /Users/cnoellert/Documents/GitHub/projekt-forge/tests/test_learning_wiring.py
decisions:
  - "D-07 enforcement: adapter is def (sync), not async def — Flame threads have no event loop"
  - "isinstance gate: _persist_execution.persist = _persist_execution self-ref turns function into Protocol-satisfying object while keeping ^def _persist_execution at module level"
  - "Credential safety: warning logs type(exc).__name__ only, not str(exc) — SQLAlchemy OperationalError.__str__() includes full exception chain which carries DB URL"
  - "Non-editable forge-bridge install required: conftest RWR-04 fixture blocks editable installs (site-packages path check); pip install /path/to/forge-bridge --force-reinstall used for tests"
metrics:
  duration_minutes: 45
  completed_date: "2026-04-21"
  tasks_completed: 4
  files_changed: 4
---

# Phase 08 Plan 02: SQL Persistence Adapter (Cross-Repo) Summary

**One-liner:** Sync SQLAlchemy adapter replacing projekt-forge's Phase 6 logger stub — idempotent `ON CONFLICT DO NOTHING` inserts into a new Alembic revision 005 `execution_log` table, with D-11 `isinstance` gate and 9 adapter unit tests covering all security invariants.

## What Was Built

### Alembic Revision 005 (commit `6a098be`)

`projekt_forge/db/migrations/versions/005_execution_log.py` — hand-written migration extending projekt-forge's existing 001→002→003→004 chain:

```python
revision: str = "005"
down_revision: str = "004"

def upgrade() -> None:
    op.create_table(
        "execution_log",
        sa.Column("code_hash", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_code", sa.Text(), nullable=False),
        sa.Column("intent", sa.Text(), nullable=True),
        sa.UniqueConstraint("code_hash", "timestamp",
                            name="uq_execution_log_code_hash_timestamp"),
    )
    op.create_index("ix_execution_log_code_hash", "execution_log", ["code_hash"], unique=False)
    op.create_index("ix_execution_log_timestamp", "execution_log",
                    [sa.text("timestamp DESC")], unique=False)

def downgrade() -> None:
    op.drop_index("ix_execution_log_timestamp", table_name="execution_log")
    op.drop_index("ix_execution_log_code_hash", table_name="execution_log")
    op.drop_table("execution_log")
```

Schema matches 08-01 Protocol docstring verbatim (D-04). No `promoted` column (D-08). Hand-written because Alembic autogenerate does not reliably detect composite UNIQUE constraints or DESC index direction.

**Migration NOT yet applied to live DB** — `alembic upgrade head` is an 08-03 release ceremony step after the v1.3.0 pin lands in projekt-forge.

### `_persist_execution` Sync Adapter (commit `42b767b`, amended in `c76e321`)

`projekt_forge/learning/wiring.py` — four surgical edits:

**1. Module docstring** — LRN-02 updated to document SQL persistence (STORE-05) replacing the logger stub.

**2. Imports** — Added `sqlalchemy as sa`, `create_engine`, `pg_insert` (from `sqlalchemy.dialects.postgresql`), and `StoragePersistence` to the `from forge_bridge import (...)` block.

**3. Module-level additions:**
- `_execution_log_table` — Core `sa.Table` descriptor (no ORM model needed for single INSERT)
- `_sync_engine: Optional[sa.Engine] = None` — lazy-initialized cache
- `_get_sync_engine()` — lazy factory using `get_db_config()` + psycopg2 URL
- `_reset_engine_for_testing()` — disposes and clears engine for test isolation

**4. `_persist_execution` (sync, not async):**

```python
def _persist_execution(record: ExecutionRecord) -> None:
    try:
        engine = _get_sync_engine()
        stmt = (
            pg_insert(_execution_log_table)
            .values(
                code_hash=record.code_hash,
                timestamp=record.timestamp,
                raw_code=record.raw_code,
                intent=record.intent,
            )
            .on_conflict_do_nothing(index_elements=["code_hash", "timestamp"])
        )
        with engine.begin() as conn:
            conn.execute(stmt)
    except Exception as exc:
        logger.warning(
            "execution_log DB write failed — JSONL unaffected "
            "(code_hash=%s, error=%s)",
            record.code_hash[:12],
            type(exc).__name__,
        )

# StoragePersistence @runtime_checkable checks for `persist` attribute.
# Self-ref satisfies isinstance without changing the function's callable interface.
_persist_execution.persist = _persist_execution
```

**5. D-11 isinstance gate in `init_learning_pipeline` (line 266):**

```python
assert isinstance(_persist_execution, StoragePersistence), (
    "_persist_execution must satisfy forge_bridge.StoragePersistence. ..."
)
execution_log.set_storage_callback(_persist_execution)
```

### Adapter Unit Tests (commit `c76e321`)

`tests/test_persist_execution_adapter.py` — 9 tests, all passing, no live DB required:

| Test | Covers |
|------|--------|
| `test_persist_execution_is_sync` | D-07: not a coroutine |
| `test_persist_execution_satisfies_protocol` | D-11 / STORE-05: isinstance check |
| `test_persist_execution_logs_once_on_db_outage` | D-06: exactly 1 WARNING, code_hash prefix present |
| `test_persist_execution_no_retry_on_sustained_outage` | P-03.5: 10 calls → 10 WARNINGs, engine.begin() count == N |
| `test_persist_execution_no_credential_leak_in_warning` | T-08-02-01: SUPERSECRETPW not in log text |
| `test_persist_execution_statement_has_on_conflict_do_nothing` | D-09: compiled SQL contains ON CONFLICT DO NOTHING |
| `test_persist_execution_uses_bound_parameters_for_raw_code` | T-08-02-02: DROP TABLE not in compiled SQL |
| `test_persist_execution_does_not_write_promoted_column` | D-08: promoted not in compiled SQL |
| `test_persist_execution_happy_path_issues_single_insert` | Happy path: 1 begin, 1 execute, 0 WARNINGs |

```
pytest tests/test_persist_execution_adapter.py -v
9 passed, 1 warning in 0.02s
```

### Updated Wiring Tests (commit `60682bc`)

`tests/test_learning_wiring.py` — replaced 1 async test with 2 sync tests:

- **Deleted:** `async def test_init_registers_storage_callback` (Phase 6 logger-stub assertion, `await asyncio.sleep(0)`)
- **Added:** `def test_init_registers_storage_callback_sync` — mocks engine, asserts `engine.begin()` and `conn.execute()` called from synchronous `record()` dispatch
- **Added:** `def test_init_asserts_persist_satisfies_protocol` — confirms isinstance at module import + init runs clean

Also: `import asyncio` removed (only usage was `asyncio.sleep(0)` in deleted test).

```
pytest tests/test_learning_wiring.py -v
9 passed, 1 warning in 0.05s   (5 original + 2 new + 2 pre-existing async SC tests)
```

## Test Results

```
pytest tests/test_persist_execution_adapter.py -q
9 passed, 1 warning in 0.02s

pytest tests/test_learning_wiring.py -q
9 passed, 1 warning in 0.03s

pytest tests/ -q
432 passed, 3 xfailed, 1 warning in 2.10s
```

Baseline was 422 passed. Net change: +9 adapter tests + 2 new wiring tests - 1 deleted async wiring test = **+10 net tests** → 432 total.

## Decision Confirmations

| Decision | Status |
|----------|--------|
| D-06: no retry | Confirmed — `test_persist_execution_no_retry_on_sustained_outage` green |
| D-07: sync adapter | Confirmed — `test_persist_execution_is_sync` green; `asyncio` removed from wiring tests |
| D-08: no promoted column | Confirmed — `test_persist_execution_does_not_write_promoted_column` green; migration has no promoted column |
| D-09: on_conflict_do_nothing | Confirmed — `test_persist_execution_statement_has_on_conflict_do_nothing` green |
| D-11: isinstance gate | Confirmed — `test_persist_execution_satisfies_protocol` + `test_init_asserts_persist_satisfies_protocol` green; gate fires before `set_storage_callback` at line 266 |
| D-13: single-head Alembic chain | Confirmed — revision 005 → down_revision 004 extends the existing chain |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `StoragePersistence` isinstance fails for plain function**
- **Found during:** Task 2 verification
- **Issue:** `@runtime_checkable` Protocol checks for `persist` attribute presence. A plain `def _persist_execution(record)` has no `persist` attribute → `isinstance(_persist_execution, StoragePersistence)` returns `False`.
- **Fix:** Added `_persist_execution.persist = _persist_execution` after the function definition — turns the function into a Protocol-satisfying callable. Both `grep "^def _persist_execution"` and `isinstance` check pass simultaneously.
- **Files modified:** `projekt_forge/learning/wiring.py`
- **Commits:** `42b767b`, `c76e321`

**2. [Rule 1 - Bug] `conda run -n forge` from worktree directory shadows site-packages forge_bridge**
- **Found during:** Task 3 test run
- **Issue:** Running `conda run -n forge pytest` from the forge-bridge worktree directory adds `''` (cwd) to `sys.path`, making Python find `forge_bridge/` in the worktree first (before site-packages). This breaks the conftest RWR-04 fixture which asserts "site-packages" in forge_bridge's resolved path.
- **Fix:** Used `conda run -n forge --cwd /Users/cnoellert/Documents/GitHub/projekt-forge pytest` to run tests from the projekt-forge directory. Also installed forge-bridge as a non-editable build from the main repo (`pip install /path/to/forge-bridge --force-reinstall`) to ensure site-packages has the v1.2.1+StoragePersistence build.
- **Files modified:** None (operational fix only)

**3. [Rule 1 - Bug] Warning log `str(exc)` leaks SQLAlchemy exception chain with DB credentials**
- **Found during:** Task 3 — `test_persist_execution_no_credential_leak_in_warning` FAILED
- **Issue:** Original adapter logged `"(code_hash=%s, error=%s: %s)", ..., type(exc).__name__, exc`. SQLAlchemy's `OperationalError.__str__()` formats the full exception chain including the inner exception message — which in the credential-leak test contained `SUPERSECRETPW`. The test correctly caught this.
- **Fix:** Changed warning format to `"(code_hash=%s, error=%s)", ..., type(exc).__name__` — dropping `str(exc)` entirely. Logs only the exception class name. This is safer (no exception chain content in logs) at the cost of less context for operators, but aligned with T-08-02-01 security requirement.
- **Files modified:** `projekt_forge/learning/wiring.py`
- **Commit:** `c76e321`

## Alembic Migration Status

Migration file `005_execution_log.py` **EXISTS** and is valid Python/Alembic syntax. It has NOT been applied to the live DB — `alembic upgrade head` is part of the 08-03 release ceremony after forge-bridge v1.3.0 is tagged and projekt-forge's pin is bumped.

## `asyncio` Import Status

`import asyncio` was removed from `tests/test_learning_wiring.py` — confirmed no remaining `asyncio.` usage in that file after removing `await asyncio.sleep(0)`. The `@pytest.mark.asyncio` decorators on the SC tests do not require `import asyncio` in the test file.

## Commits (projekt-forge repo)

| Hash | Message |
|------|---------|
| `6a098be` | feat(db): add execution_log migration (revision 005, STORE-05) |
| `42b767b` | feat(learning): replace _persist_execution stub with sync SQLAlchemy adapter (STORE-05) |
| `c76e321` | test(08-02): add _persist_execution adapter unit tests (STORE-05) |
| `60682bc` | test(08-02): update wiring tests for sync-callback semantics (D-07, STORE-05) |

## Known Stubs

None — the adapter makes real SQLAlchemy calls (mocked in tests only). Migration file is complete DDL. No placeholder data flows to any UI rendering path.

## Threat Flags

All threats from the plan's threat model were addressed:

| Threat | Mitigation | Verified by |
|--------|-----------|-------------|
| T-08-02-01 credential leak | Warning logs only `type(exc).__name__` — no `str(exc)`, no `engine.url` | `test_persist_execution_no_credential_leak_in_warning` |
| T-08-02-02 SQL injection via raw_code | SQLAlchemy Core `insert(...).values(raw_code=...)` bound params | `test_persist_execution_uses_bound_parameters_for_raw_code` |
| T-08-02-03 DoS via retry loop | Zero retry code; grep acceptance criterion blocks regressions | `test_persist_execution_no_retry_on_sustained_outage` |
| T-08-02-07 stale Protocol pin | `assert isinstance(_persist_execution, StoragePersistence)` at startup | `test_init_asserts_persist_satisfies_protocol` |

## Self-Check

- `005_execution_log.py` exists: FOUND (`ls` confirmed)
- `wiring.py` has sync `_persist_execution`: CONFIRMED (`grep "^def _persist_execution"` exits 0)
- `test_persist_execution_adapter.py` exists: FOUND
- `test_learning_wiring.py` updated: CONFIRMED (async test removed, 2 sync tests added)
- projekt-forge commit `6a098be` exists: CONFIRMED
- projekt-forge commit `42b767b` exists: CONFIRMED
- projekt-forge commit `c76e321` exists: CONFIRMED
- projekt-forge commit `60682bc` exists: CONFIRMED
- `pytest tests/` green: CONFIRMED (432 passed, 3 xfailed)

## Self-Check: PASSED
