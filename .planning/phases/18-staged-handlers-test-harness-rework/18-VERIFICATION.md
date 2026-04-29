---
phase: 18-staged-handlers-test-harness-rework
verified: 2026-04-29T21:00:00Z
status: passed
score: 9/9
overrides_applied: 0
---

# Phase 18: Staged-Handlers Test Harness Rework — Verification Report

**Phase Goal:** Migrate 3 test files (23 tests) from `starlette.TestClient` (sync) to `httpx.AsyncClient(transport=ASGITransport(app=...))` so the test event loop matches the asyncpg session loop. Seed parent `DBProject` rows via a new `seeded_project` fixture. Remove the `FORGE_TEST_DB=1` opt-in gate AND wrap the `pg_terminate_backend` teardown SQL.
**Verified:** 2026-04-29T21:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|---------|
| 1  | `staged_client` fixture in `tests/console/conftest.py` uses `httpx.AsyncClient` + `ASGITransport`, not `starlette.testclient.TestClient` | VERIFIED | `import httpx` + `from httpx import ASGITransport` present; `from starlette.testclient import TestClient` absent; `async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client: yield client` in fixture body |
| 2  | Local `staged_client` override in `test_staged_zero_divergence.py` mirrors the same async migration | VERIFIED | `transport = ASGITransport(app=app)` + `async with httpx.AsyncClient(...)` + `yield client` present; `TestClient(` absent |
| 3  | All `staged_client.{post,get,...}` call sites across the 3 console test files are awaited | VERIFIED | `grep -cE "(await staged_client\.)"`: writes=16, list=9, zero_divergence=6; zero un-awaited `r = staged_client.` patterns remain |
| 4  | 0 `RuntimeError: got Future ... attached to a different loop` — loop conflict eliminated | VERIFIED | Live UAT: `pytest tests/console/test_staged_handlers_writes.py tests/console/test_staged_handlers_list.py tests/console/test_staged_zero_divergence.py -v` → **33 passed, 0 failed, 0 errors** (no loop RuntimeErrors) |
| 5  | `seeded_project` fixture in `tests/conftest.py` inserts a `DBProject(name='harness-test-project', code='HARNESS')` row and yields its UUID | VERIFIED | `async def seeded_project(session_factory)` present at end of `tests/conftest.py`; `DBProject(name="harness-test-project", code="HARNESS")` + `yield proj.id` confirmed in file |
| 6  | 3 FK-violating tests consume `seeded_project` for project_a and inline-seed second `DBProject(code="HARNESS-B")` for project_b | VERIFIED | `test_staged_op_list_filter_by_project_id(session_factory, seeded_project)` + `test_staged_op_list_combined_filter(session_factory, seeded_project)` in `tests/test_staged_operations.py`; `test_staged_list_filter_by_project_id(session_factory, staged_client, seeded_project)` in `tests/console/test_staged_handlers_list.py`; all 3 inline-seed `DBProject(name="harness-test-project-b", code="HARNESS-B")` |
| 7  | 0 `entities_project_id_fkey` IntegrityErrors; store-layer suite: 42 passed + 4 by-design skipped + 1 expected fail (`test_transition_atomicity`, deferred to POLISH-03) | VERIFIED | Live UAT: `pytest tests/test_staged_operations.py -v` → **1 failed, 42 passed, 4 skipped** — only failure is `test_transition_atomicity` with `AssertionError` at line 388 (pre-existing logic bug, no FK errors) |
| 8  | `_phase13_postgres_available()` no longer references `FORGE_TEST_DB`; honors `FORGE_DB_URL` unconditionally | VERIFIED | No `if _phase13_os.environ.get("FORGE_TEST_DB") == "1":` gate code in file; docstring contains traceability anchor "Phase 18 HARNESS-03 removed the FORGE_TEST_DB=1 opt-in gate"; probe uses `urlparse(FORGE_DB_URL)` unconditionally |
| 9  | `pg_terminate_backend` teardown SQL is wrapped in `try/except Exception: pass`; suite runs without `FORGE_TEST_DB=1`; 0 teardown ERRORs | VERIFIED | `try:` block wraps `pg_terminate_backend` execute call; `except Exception:` + "forge role lacks SUPERUSER" comment present; Live UAT with `FORGE_DB_URL` only (no `FORGE_TEST_DB`) → same 42p/4s/1f result; 0 teardown ERRORs in output |

**Score:** 9/9 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/console/conftest.py` | Async `staged_client` fixture using httpx.AsyncClient + ASGITransport | VERIFIED | `import httpx`, `from httpx import ASGITransport`, `async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client: yield client`; factory fixtures `proposed_op_id`, `approved_op_id`, `rejected_op_id` untouched |
| `tests/console/test_staged_handlers_writes.py` | 16 awaited `staged_client` call sites | VERIFIED | 16 `await staged_client.post(...)` patterns; no `from starlette.testclient import TestClient` |
| `tests/console/test_staged_handlers_list.py` | 9 awaited `staged_client` call sites + seeded_project FK fix | VERIFIED | 9 `await staged_client.{get,post}(...)` patterns; `test_staged_list_filter_by_project_id` uses `seeded_project` |
| `tests/console/test_staged_zero_divergence.py` | Local async staged_client fixture override + 6 awaited call sites | VERIFIED | Local override uses `ASGITransport` + `async with ... yield client`; 6 `(await staged_client.{get,post}(...)).content.decode()` patterns |
| `tests/conftest.py` | `seeded_project` fixture + gate-free `_phase13_postgres_available()` + wrapped teardown | VERIFIED | All three present; `seeded_project` uses `@_phase13_pytest_asyncio.fixture`; `_phase13_postgres_available()` has no `FORGE_TEST_DB` gate code; `pg_terminate_backend` in `try/except Exception` |
| `tests/test_staged_operations.py` | 2 FK tests updated to use `seeded_project` + `DBProject` imported | VERIFIED | `from forge_bridge.store.models import DBEntity, DBEvent, DBProject`; both FK tests use `seeded_project` fixture parameter; `test_transition_atomicity` untouched |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `tests/console/conftest.py::staged_client` | `forge_bridge.console.app.build_console_app(...)` ASGI app | `httpx.AsyncClient(transport=ASGITransport(app=app), base_url='http://testserver')` | WIRED | `ASGITransport(app=app)` confirmed in file |
| test bodies in 3 console test files | `staged_client` async methods | `await staged_client.{post,get,...}(...)` | WIRED | 31 total awaited call sites: 16+9+6 |
| `tests/conftest.py::seeded_project` | `forge_bridge.store.models.DBProject` | `session.add(DBProject(name='harness-test-project', code='HARNESS'))` | WIRED | `DBProject(name="harness-test-project", code="HARNESS")` confirmed in fixture body |
| 3 FK tests | `seeded_project` fixture | test signatures contain `seeded_project` parameter | WIRED | All 3 test signatures confirmed |
| `tests/conftest.py::session_factory` | `_phase13_postgres_available()` | `if not _phase13_postgres_available(): pytest.skip(...)` | WIRED | Gate-call present in `session_factory` body |
| `tests/conftest.py` teardown block | asyncpg connection cleanup | `try: pg_terminate_backend; except Exception: pass` | WIRED | `try:` wraps the execute call; `except Exception:` confirmed |

---

### Data-Flow Trace (Level 4)

Not applicable — this phase delivers test infrastructure only (fixtures, test file migrations). No components that render dynamic user-visible data.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Console staged tests: 33 passed, 0 failed, 0 loop errors | `pytest tests/console/test_staged_handlers_writes.py tests/console/test_staged_handlers_list.py tests/console/test_staged_zero_divergence.py -v -p no:pytest-blender` | `33 passed, 1 warning in 3.94s` | PASS |
| Store-layer suite: 42p / 4s / 1f (atomicity) | `pytest tests/test_staged_operations.py -v -p no:pytest-blender` | `1 failed, 42 passed, 4 skipped, 1 warning in 5.60s`; single fail = `test_transition_atomicity` line-388 AssertionError | PASS |
| No FORGE_TEST_DB gate code | `grep -E "if.*FORGE_TEST_DB" tests/conftest.py` | no output | PASS |
| 3 commits, tests/ only | `git show --stat 75f8c2a 28437ed d19c0ba` | 75f8c2a: 4 console test files; 28437ed: conftest.py + 2 test files; d19c0ba: conftest.py only; no `forge_bridge/` diff | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| HARNESS-01 | 18-01-PLAN.md | Migrate `staged_client` from `starlette.TestClient` to `httpx.AsyncClient + ASGITransport`; 0 loop-conflict RuntimeErrors; 22/23 console tests pass (1 FK-fail expected) | SATISFIED | Commit 75f8c2a; live UAT 33p/0f (post-HARNESS-02, all 33 pass; HARNESS-01 itself contributed the 22+1 improvement) |
| HARNESS-02 | 18-02-PLAN.md | `seeded_project` fixture seeds parent DBProject row; 3 FK-violating tests wired; store-layer: 42p + 4s + 1f (atomicity); console FK test passes | SATISFIED | Commit 28437ed; live UAT: `1 failed, 42 passed, 4 skipped`; only fail = `test_transition_atomicity`; console FK test passes (included in 33 passed) |
| HARNESS-03 | 18-03-PLAN.md | `_phase13_postgres_available()` gate-free; `pg_terminate_backend` wrapped; suite runs without `FORGE_TEST_DB=1`; 0 teardown ERRORs | SATISFIED | Commit d19c0ba; no `FORGE_TEST_DB` gate code; `try/except Exception` present; live UAT without `FORGE_TEST_DB=1` produces same counts, 0 teardown ERRORs |

**Orphaned requirements:** None. All 3 phase requirements (HARNESS-01, HARNESS-02, HARNESS-03) are claimed and closed.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `tests/conftest.py` | 131 | `FORGE_TEST_DB` in docstring | Info | Intentional traceability anchor documenting the removed gate; not functional code |
| `tests/test_staged_operations.py` | 388 | `assert row is None` — contradicts SQLAlchemy/Postgres commit semantics | Info | Pre-existing known issue; deferred to POLISH-03 (Phase 19) per CONTEXT D-07; not introduced by Phase 18 |

No blockers. No warnings. The `FORGE_TEST_DB` in the docstring is intentional documentation. The `test_transition_atomicity` assertion bug predates Phase 18.

---

### Human Verification Required

None. All acceptance criteria are verifiable programmatically and have been verified with live test runs against Postgres at `127.0.0.1:7533`.

---

### Gaps Summary

No gaps. All 9 must-haves are verified against the actual codebase and confirmed by live test runs.

**Note on `test_transition_atomicity`:** This test fails with `AssertionError: post-rollback: even the original proposed entity is rolled back` at line 388. This is a pre-existing test logic bug (the assertion contradicts SQLAlchemy/Postgres semantics — `commit()` durably persists before `rollback()` runs). Phase 18 explicitly does not touch this test; it is deferred to POLISH-03 (Phase 19) per CONTEXT D-07. The HARNESS-02 acceptance criterion was amended to treat this as 1 expected fail ("42 passed + 4 skipped + 1 failed" = 47 collected). This is not a Phase 18 gap.

---

_Verified: 2026-04-29T21:00:00Z_
_Verifier: Claude (gsd-verifier)_
