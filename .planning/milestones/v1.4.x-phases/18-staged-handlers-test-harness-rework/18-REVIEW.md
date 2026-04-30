---
phase: 18-staged-handlers-test-harness-rework
reviewed: 2026-04-29T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - tests/conftest.py
  - tests/console/conftest.py
  - tests/console/test_staged_handlers_list.py
  - tests/console/test_staged_handlers_writes.py
  - tests/console/test_staged_zero_divergence.py
  - tests/test_staged_operations.py
findings:
  critical: 0
  warning: 3
  info: 6
  total: 9
status: issues_found
---

# Phase 18: Code Review Report

**Reviewed:** 2026-04-29
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Phase 18 reworks the staged-handler test harness across three plans:

1. **HARNESS-01** — Migrates `staged_client` from Starlette's sync `TestClient`
   (private event loop) to `httpx.AsyncClient(transport=ASGITransport(app=app))`
   so the test loop matches asyncpg's session loop. Cleanly executed in both
   `tests/console/conftest.py` and `tests/console/test_staged_zero_divergence.py`.
2. **HARNESS-02** — Adds the `seeded_project` async fixture in
   `tests/conftest.py` (inserts one parent `DBProject`) and wires it into the
   three FK-violating tests.
3. **HARNESS-03** — Removes the `FORGE_TEST_DB=1` opt-in gate in
   `_phase13_postgres_available()` and wraps the `pg_terminate_backend`
   teardown SQL in try/except for the non-SUPERUSER `forge` role.

The migration is correct: every site that previously relied on the sync
`TestClient` now `await`s `staged_client.get/post(...)`, and `seeded_project`
properly seeds via async session + commit before yielding the UUID. The
teardown error-handling hardening matches the goal stated in the docstring.

The findings below are mostly defensive-coding / clarity issues. Two warnings
flag genuine correctness/cleanup risks (a vestigial dead block in
`test_transition_atomicity`, and an SQL-quoting concern in the teardown path);
the rest are info-level lint and minor cleanup.

No source files were modified — the review is read-only.

## Warnings

### WR-01: Dead pre-rollback assertion block in `test_transition_atomicity`

**File:** `tests/test_staged_operations.py:341-360`
**Issue:** The first half of the test opens a session, calls `repo.approve` +
`session.flush` + `session.rollback`, then immediately enters another session
and ends with `assert True  # placeholder; the meaningful check is below`.
The second half (`# Reconstruct the test...`) is the actual atomicity check.
The whole leading block is dead code: it exits the session without any
assertion (the in-line `assert True` is a no-op and the comment confirms it).
This means a future reader will easily mistake the no-op block for a real
test, and the rollback path in the FIRST session is never observed.

This is not a regression introduced by Phase 18 — it predates the phase — but
because Phase 18 explicitly touches `test_staged_operations.py` (the file is
in scope) and the dead block sits next to the FK-fix imports, it should be
cleaned up while you're here. Otherwise leave a TODO so it isn't perceived
as intentional.

**Fix:** Either delete lines 339-360 entirely (the second half does the work),
or convert the placeholder to a real assertion that the rollback in the first
session leaves no events:

```python
# Replace the placeholder block with a real check, OR remove it entirely.
# Delete lines 341-360 — the test below does the meaningful work.
async def test_transition_atomicity(session_factory):
    """..."""
    async with session_factory() as session:
        repo = StagedOpRepo(session)
        op2 = await repo.propose(operation="op-atom", proposer="p", parameters={})
        await session.commit()

        events_before = await EventRepo(session).get_recent(entity_id=op2.id, limit=10)
        assert len(events_before) == 1
        ...  # rest of the meaningful assertions
```

---

### WR-02: Teardown DB name is f-string-interpolated into SQL

**File:** `tests/conftest.py:184, 219-228`
**Issue:** `test_db_name` is generated from `uuid.uuid4().hex[:8]` and
interpolated directly into `CREATE DATABASE`, `pg_terminate_backend`, and
`DROP DATABASE` statements. While the source is a UUID hex prefix (so
injection isn't realistic in practice), the pattern is an anti-pattern that
will rot the moment someone parameterizes the name from an env var or test
arg in the future. It's also the kind of finding a security scanner will
flag noisily.

PostgreSQL's `CREATE DATABASE` and `DROP DATABASE` cannot use bind parameters
for the database name (this is a real Postgres constraint), so the only
correct mitigation is to validate the identifier shape and quote with
`sqlalchemy.engine.identifier_preparer` or a regex check. The
`pg_terminate_backend` SELECT, however, *can* use a bind parameter for
`datname` and should.

**Fix:** Use a bind parameter for the literal in the `pg_terminate_backend`
WHERE clause (the only one that supports it), and add a `re.fullmatch` guard
at provisioning time so a future caller can't pass a malicious name:

```python
import re

# At provisioning:
test_db_name = f"forge_bridge_test_{_phase13_uuid.uuid4().hex[:8]}"
assert re.fullmatch(r"[a-zA-Z0-9_]+", test_db_name), f"unsafe db name: {test_db_name!r}"

# In teardown — use a bound param for datname:
try:
    await conn.execute(
        _phase13_text(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = :dbname AND pid <> pg_backend_pid()"
        ),
        {"dbname": test_db_name},
    )
except Exception:
    pass
```

---

### WR-03: Bare `except Exception` swallows non-privilege errors silently

**File:** `tests/conftest.py:223-227`
**Issue:** The teardown wraps `pg_terminate_backend` in `try: ... except
Exception: pass`. The docstring explains the motivation (forge role lacks
SUPERUSER → wrapped `InsufficientPrivilegeError`), but the catch is broad
enough to also swallow:
  - Connection drops mid-statement (which would also affect the next
    `DROP DATABASE` line and cascade into a misleading error).
  - asyncpg protocol errors that indicate real bugs.
  - Cancelled-task / loop-shutdown exceptions.

When the DROP fails next, the test reports the DROP error in isolation,
hiding the actual root cause from the bare `except` above.

**Fix:** Narrow the catch to the specific privilege-error class, or at minimum
log the swallowed exception so it surfaces in test output when something
unexpected occurs:

```python
from sqlalchemy.exc import ProgrammingError

try:
    await conn.execute(_phase13_text(
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
        "WHERE datname = :dbname AND pid <> pg_backend_pid()"
    ), {"dbname": test_db_name})
except ProgrammingError as e:
    # forge role lacks SUPERUSER privilege — expected, continue to DROP
    if "insufficient_privilege" not in str(e).lower():
        raise
```

If `ProgrammingError` is too narrow in practice, at least add a comment-line
import + `import warnings; warnings.warn(f"pg_terminate_backend failed: {e!r}")`
inside the `except` so the log surfaces it.

## Info

### IN-01: Two near-identical `staged_client` fixtures across files

**File:** `tests/console/conftest.py:25-45` and
`tests/console/test_staged_zero_divergence.py:43-48`
**Issue:** `test_staged_zero_divergence.py` redefines its own `staged_client`
fixture (depending on a local `staged_api` fixture) that mirrors the one in
`tests/console/conftest.py`. The redefinition is intentional (it depends on
`staged_api` to share an API instance with `staged_spy` for byte-identity
testing), but the two fixtures will drift. If the conftest fixture later adds
middleware or modifies the app config, byte-identity tests won't see it and
will silently pass on a divergent surface.

**Fix:** Either (a) parameterize the conftest fixture to accept an injected
`api`, or (b) add a comment in the divergence test that explicitly notes the
duplication and *why* it can't reuse the conftest fixture. Option (b) is
lower-risk:

```python
# NOTE: This fixture intentionally duplicates tests/console/conftest.py's
# staged_client because byte-identity tests need the SAME ConsoleReadAPI
# instance shared with staged_spy. If the conftest fixture changes, mirror
# the change here.
@pytest_asyncio.fixture
async def staged_client(staged_api, session_factory):
    ...
```

---

### IN-02: Unused imports

**File:** Multiple
**Issue:** Several unused imports remain after the migration:
  - `tests/console/test_staged_handlers_list.py:10` — `import uuid` (no usage in file)
  - `tests/console/test_staged_handlers_list.py:12` — `import time` (no usage)
  - `tests/console/test_staged_handlers_list.py:14-15` — `pytest`, `pytest_asyncio` (auto mode; not referenced)
  - `tests/console/test_staged_handlers_writes.py:13-14` — `pytest`, `pytest_asyncio` (auto mode; not referenced)
  - `tests/console/conftest.py:13` — `import pytest` (only `pytest_asyncio` is used)
  - `tests/console/test_staged_zero_divergence.py:14-15` — `pytest`, `pytest_asyncio` likely unused (auto mode)
  - `tests/test_staged_operations.py:24` — `pytest` IS used (parametrize, raises) — keep

**Fix:** Delete the unused imports. With `asyncio_mode=auto`, `pytest_asyncio`
is *not* required at the test-function level — only inside fixtures via
`@pytest_asyncio.fixture`. So:
- `tests/console/conftest.py` keeps `pytest_asyncio` (used as decorator).
- The three test modules that don't decorate fixtures or use parametrize can drop both.

---

### IN-03: `seeded_project` docstring describes second-project pattern but only the first project is in the fixture

**File:** `tests/conftest.py:252-266`
**Issue:** The docstring tells the test author "use this fixture for the
first id and inline-seed a second DBProject in the test body" — and the
three call sites do exactly that with copy-pasted blocks
(`test_staged_list_filter_by_project_id`,
`test_staged_op_list_filter_by_project_id`,
`test_staged_op_list_combined_filter`). This is by design per CONTEXT D-03
(quoted in the conftest preamble), so it's not wrong — just three nearly
identical 6-line blocks waiting to drift.

**Fix:** Optional: extract a small `_seed_extra_project(session_factory, code)`
helper in a `tests/_helpers.py` or co-locate it in `tests/console/conftest.py`
so the duplication is one point of maintenance:

```python
async def _seed_extra_project(session_factory, *, code: str, name: str = None) -> uuid.UUID:
    """Seed an additional DBProject (beyond seeded_project) and return its UUID."""
    async with session_factory() as session:
        proj = DBProject(name=name or f"harness-test-{code.lower()}", code=code)
        session.add(proj)
        await session.commit()
        await session.refresh(proj)
        return proj.id
```

If you want to keep CONTEXT D-03's "discrimination logic visible at the call
site" intent, leave as-is and ignore this finding. Either choice is defensible.

---

### IN-04: `test_staged_list_orders_by_created_at_desc` builds a `timestamps` list it never uses

**File:** `tests/console/test_staged_handlers_list.py:153-156`
**Issue:** The `timestamps` list comprehension at line 155 is computed but
never asserted on — the actual ordering check uses `all_records` two lines
later. Dead computation that confused me on first read.

**Fix:** Delete the unused list:

```python
records = r.json()["data"]
all_records = r.json()["data"]   # same thing — collapse to one variable
if len(all_records) >= 2:
    for i in range(len(all_records) - 1):
        assert all_records[i]["created_at"] >= all_records[i + 1]["created_at"], ...
```

---

### IN-05: `op_ids` accumulated then discarded

**File:** `tests/console/test_staged_handlers_list.py:141-149`
**Issue:** The same test builds `op_ids = []` and appends each op's id, then
never references it (the inner-list-comp at line 155 that mentioned
`op_ids` is itself dead per IN-04). This is the same dead-code area but a
distinct symptom.

**Fix:** Drop `op_ids` collection if the test only verifies global ordering;
keep it only if you re-introduce a per-id assertion.

---

### IN-06: `test_staged_list_filter_by_project_id` makes a weak final assertion

**File:** `tests/console/test_staged_handlers_list.py:111-115`
**Issue:** The test sets up two projects with one op each, queries
`?project_id={project_a}`, asserts `total == 1`, then asserts
`body["data"][0]["status"] is not None  # record exists`. The "record exists"
check is implied by `total == 1`, and the test never asserts that the
returned record's `project_id` equals `project_a` (the actual filter under
test). It's possible — though unlikely — for a bug to return the wrong
project's record while still satisfying the assertions.

**Fix:** Tighten the assertion to verify the filter actually selected the
right project:

```python
r = await staged_client.get(f"/api/v1/staged?project_id={project_a}")
assert r.status_code == 200
body = r.json()
assert body["meta"]["total"] == 1
assert body["data"][0]["project_id"] == str(project_a), (
    f"Filter returned wrong project: expected {project_a}, got {body['data'][0]['project_id']}"
)
```

---

_Reviewed: 2026-04-29_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
