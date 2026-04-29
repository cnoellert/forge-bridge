---
phase: 18
plan: 02
subsystem: test-harness
tags: [harness, postgres, fixtures, fk-seeding, staged-ops]
requirements_closed: [HARNESS-02]

dependency_graph:
  requires: [18-01]
  provides: [seeded_project fixture, FK-free store-layer suite, FK-free console FK test]
  affects: [tests/conftest.py, tests/test_staged_operations.py, tests/console/test_staged_handlers_list.py]

tech_stack:
  added: []
  patterns: [pytest-asyncio fixture composition, inline DBProject seeding for filter discrimination]

key_files:
  created: []
  modified:
    - tests/conftest.py
    - tests/test_staged_operations.py
    - tests/console/test_staged_handlers_list.py

decisions:
  - "Single-id seeded_project fixture + inline second-insert in test body (D-03 / D-07 #5): keeps fixture API minimal, discrimination logic visible at call site"
  - "Local DBProject import inside fixture body (mirrors _phase13_* aliasing style): keeps module-top imports clean for downstream maintenance"
  - "HARNESS-02 acceptance = 42 passed + 4 by-design skipped + 1 expected fail (test_transition_atomicity deferred to POLISH-03 per D-07)"

metrics:
  duration_minutes: 12
  completed: "2026-04-29T18:32:05Z"
  tasks_completed: 4
  tasks_total: 4
  files_modified: 3
  commit: 28437ed
---

# Phase 18 Plan 02: HARNESS-02 — DBProject FK Seeding Summary

**One-liner:** `seeded_project` pytest-asyncio fixture inserts a DBProject parent row and eliminates `entities_project_id_fkey` IntegrityErrors across 3 FK-violating staged-ops tests.

---

## What Was Done

Introduced a new `seeded_project` `@pytest_asyncio.fixture` in `tests/conftest.py` that inserts a `DBProject(name="harness-test-project", code="HARNESS")` row via `session_factory` and yields its UUID. Wired it into the 3 FK-violating tests that previously minted bare `uuid.uuid4()` project IDs with no parent row in the `projects` table.

**Root cause closed:** `entities_project_id_fkey` FK constraint on `staged_operations.project_id` → `projects.id` rejects inserts when no parent project row exists. Tests used `uuid.uuid4()` for project IDs without seeding a parent `DBProject` row first.

**Three tests fixed:**
1. `tests/test_staged_operations.py::test_staged_op_list_filter_by_project_id` — now uses `seeded_project` for project_a; inline-seeds `DBProject(name="harness-test-project-b", code="HARNESS-B")` for project_b
2. `tests/test_staged_operations.py::test_staged_op_list_combined_filter` — same pattern
3. `tests/console/test_staged_handlers_list.py::test_staged_list_filter_by_project_id` — same pattern; P-01's `await staged_client.get(...)` preserved

**No production source touched.** Diff scope: `tests/conftest.py`, `tests/test_staged_operations.py`, `tests/console/test_staged_handlers_list.py` only.

---

## New `seeded_project` Fixture (verbatim for searchability)

```python
# ============================================================
# Phase 18 (HARNESS-02) — seeded_project fixture
# ------------------------------------------------------------
# Three staged-operation tests carry `project_id` parameters and run
# against live Postgres via session_factory. Without a parent DBProject
# row, the entities_project_id_fkey constraint rejects the insert.
#
# This fixture inserts ONE DBProject and yields its UUID. Tests that
# need a SECOND distinct project_id (filter-discrimination tests)
# inline-insert another DBProject in the test body — keeps the fixture
# API minimal and the discrimination logic visible at the call site.
#
# Auto-seeding inside session_factory was rejected (would couple 90% of
# unrelated tests to a default project they don't need). Lazy-creating
# inside the proposed_op factory was rejected (would hide the FK
# requirement from the test reader). See CONTEXT D-03.
# ============================================================

@_phase13_pytest_asyncio.fixture
async def seeded_project(session_factory):
    """Insert one DBProject row and yield its UUID.

    For tests that need a real parent project for staged_operation rows
    that carry project_id. Tests needing TWO distinct project ids should
    use this fixture for the first id and inline-seed a second DBProject
    in the test body using a different `code` value (the projects table
    has a UNIQUE constraint on code).
    """
    from forge_bridge.store.models import DBProject
    async with session_factory() as session:
        proj = DBProject(name="harness-test-project", code="HARNESS")
        session.add(proj)
        await session.commit()
        await session.refresh(proj)
        yield proj.id
```

---

## Acceptance Criteria Evidence

### Store-layer suite (`tests/test_staged_operations.py`)

```
pytest tests/test_staged_operations.py -v
47 collected
1 failed, 42 passed, 4 skipped
```

**Summary line:** `1 failed, 42 passed, 4 skipped, 1 warning in 6.11s`

**FK error counts:**
- `grep -c "entities_project_id_fkey" /tmp/harness-02-store.log` → **0**
- `grep -c "IntegrityError" /tmp/harness-02-store.log` → **0**

**Single FAILED test:**
```
FAILED tests/test_staged_operations.py::test_transition_atomicity - AssertionError: ...
```

This is the **deferred atomicity test** (see Deferral Note below). It is the sole failing test and matches the expected HARNESS-02 acceptance criterion exactly.

**4 by-design SKIPPED tests:** parameterized `test_transition_legality[None-approved-False]`, `[None-rejected-False]`, `[None-executed-False]`, `[None-failed-False]` — these are explicitly skipped per test code lines 116-128 because `from_status=None` only permits → `proposed` transitions.

### Console FK test

```
pytest tests/console/test_staged_handlers_list.py::test_staged_list_filter_by_project_id -v
1 collected
1 passed
```

**Result:** `1 passed, 1 warning in 0.24s` — PASSED.

---

## Deferral Notes

### `test_transition_atomicity` — Deferred to POLISH-03 (Phase 19)

From CONTEXT D-07:

> `test_transition_atomicity` in `tests/test_staged_operations.py:323-398` has a pre-existing test logic bug at line 388 surfaced by the baseline. The assertion `assert row is None` after the sequence `propose() → commit() → approve() → flush() → rollback()` contradicts SQLAlchemy/Postgres semantics: `commit()` durably persists the proposed entity to the database; the subsequent `rollback()` only reverts work done since that commit (the approve+events), NOT the proposed entity itself. The test author's assertion message ("post-rollback: even the original proposed entity is rolled back because its commit was tied to the rolled-back session") describes a behavior that does not exist in PostgreSQL. The test has been broken since written; the loop-conflict skip masked it.

**Phase 18 does NOT touch this test.** POLISH-03 (Phase 19) scopes the rewrite. The HARNESS-02 acceptance criterion was explicitly amended to treat this as 1 expected FAIL ("42 passed + 4 by-design skipped + 1 expected fail" = 47 collected).

### `pg_terminate_backend` teardown ERROR

**Not observed in this UAT run** (0 teardown errors, vs. 1/47 in the CONTEXT D-05 baseline). If it surfaces in future runs, it is HARNESS-03 / P-03 territory — the `forge` role lacks SUPERUSER and the teardown SQL fails intermittently. P-03 wraps it in `try/except`.

### `FORGE_TEST_DB=1` still required

At this point in Phase 18 execution, `FORGE_TEST_DB=1` is still required to run the DB-backed tests. P-03 (HARNESS-03) removes the `FORGE_TEST_DB == "1"` gate from `_phase13_postgres_available()` and replaces it with an always-on TCP probe against `FORGE_DB_URL` host/port.

---

## Deviations from Plan

None — plan executed exactly as written. All three tasks completed with zero FK errors in UAT. The atomicity test was not touched (correctly deferred to POLISH-03).

---

## Next Plan

**P-03 (HARNESS-03):** Remove the `FORGE_TEST_DB=1` gate from `_phase13_postgres_available()` in `tests/conftest.py` and wrap the `pg_terminate_backend` teardown SQL in `try/except`. After P-03 lands, the suite runs without the `FORGE_TEST_DB=1` env var and 0 teardown ERRORs are expected.

---

## Self-Check: PASSED

- `tests/conftest.py` — exists and contains `seeded_project` fixture: FOUND
- `tests/test_staged_operations.py` — both FK tests updated: FOUND
- `tests/console/test_staged_handlers_list.py` — console FK test updated: FOUND
- Commit `28437ed` — landed: FOUND
- Production source diff empty: CONFIRMED
- `entities_project_id_fkey` count in store log: 0 — CONFIRMED
- Store suite: 42 passed + 4 skipped + 1 failed (`test_transition_atomicity`) = 47 collected — CONFIRMED
- Console FK test: 1 passed — CONFIRMED
