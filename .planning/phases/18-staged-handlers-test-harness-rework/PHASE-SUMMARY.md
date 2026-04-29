# Phase 18: Staged-Handlers Test Harness Rework — Phase Summary

**Phase:** 18-staged-handlers-test-harness-rework
**Milestone:** v1.4.x Carry-Forward Debt (targeting v1.4.1)
**Requirements closed:** HARNESS-01, HARNESS-02, HARNESS-03
**Plans:** 3 of 3 complete
**Commits landed:** 3 (one per requirement, D-30 isolated-commit mandate)
**Files modified:** `tests/` only — no production source touched

---

## Gates Table

| Gate | Requirement | Commit | Status | Acceptance Evidence |
|------|-------------|--------|--------|---------------------|
| HARNESS-01 | AsyncClient migration — eliminate asyncpg event-loop conflict | `75f8c2a` | CLOSED | Replaced `starlette.testclient.TestClient` with `httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")` in `tests/console/conftest.py`; awaited all 31 call sites across 3 console test files. Console static analysis: 0 `TestClient(` references, 31 awaited call sites. Live UAT post-P03: 33 passed / 0 failed. |
| HARNESS-02 | DBProject FK seeding — eliminate `entities_project_id_fkey` IntegrityErrors | `28437ed` | CLOSED | Introduced `seeded_project` fixture in `tests/conftest.py`; wired into 3 FK-violating tests (2 store-layer + 1 console). Live UAT: store-layer 42 passed / 4 by-design skipped / 1 expected fail (`test_transition_atomicity`, deferred to POLISH-03). Console FK test 1/1 passed. `grep -c "entities_project_id_fkey" /tmp/harness-02-store.log` → 0. |
| HARNESS-03 | Gate removal + teardown fix — remove `FORGE_TEST_DB=1` gate; wrap `pg_terminate_backend` in `try/except` | `d19c0ba` | CLOSED | `_phase13_postgres_available()` body replaced — no `FORGE_TEST_DB` gate code remaining. Teardown wrapped. Live UAT without `FORGE_TEST_DB=1`: store-layer 42p/4s/1f, 0 teardown ERRORs; console 33p/0f; default `pytest tests/` 763p/117s/0err. |

---

## Final Status — Empirical Baseline vs Post-Fix

### Baseline (CONTEXT D-05, 2026-04-29, with `FORGE_TEST_DB=1`)

| Suite | Passed | Failed | Skipped | ERRORs |
|-------|--------|--------|---------|--------|
| `tests/test_staged_operations.py` (47 collected) | 40 | 3 | 4 | 1 (teardown) |
| `tests/console/test_staged_*.py` (33 collected) | 10 | 23 | 0 | 0 |

Failure breakdown at baseline:
- 22 console failures: `RuntimeError: got Future attached to a different loop` (HARNESS-01 target)
- 1 console failure: `entities_project_id_fkey` IntegrityError on `test_staged_list_filter_by_project_id` (HARNESS-02 target, reclassified from HARNESS-01 during baseline)
- 2 store-layer failures: `entities_project_id_fkey` on `test_staged_op_list_filter_by_project_id` + `test_staged_op_list_combined_filter` (HARNESS-02 target)
- 1 store-layer failure: `AssertionError` at line 388 of `test_transition_atomicity` (pre-existing test logic bug, deferred to POLISH-03)
- 1 teardown ERROR: `pg_terminate_backend` SUPERUSER required (HARNESS-03 target)

### Post-Phase-18 (no `FORGE_TEST_DB=1` — gate removed by HARNESS-03)

| Suite | Passed | Failed | Skipped | ERRORs |
|-------|--------|--------|---------|--------|
| `tests/test_staged_operations.py` (47 collected) | 42 | 1 | 4 | 0 |
| `tests/console/test_staged_*.py` (33 collected) | 33 | 0 | 0 | 0 |
| `tests/` (no env vars, 880 collected) | 763 | 0 | 117 | 0 |

---

## Atomicity Test Deferral — POLISH-03

**`test_transition_atomicity`** in `tests/test_staged_operations.py:323-398` is the **1 expected fail** remaining after Phase 18.

From CONTEXT D-07:

> The assertion `assert row is None` at line 388 after the sequence `propose() → commit() → approve() → flush() → rollback()` contradicts SQLAlchemy/Postgres semantics: `commit()` durably persists the proposed entity to the database; the subsequent `rollback()` only reverts work done since that commit (the approve+events), NOT the proposed entity itself. The test author's assertion message ("post-rollback: even the original proposed entity is rolled back because its commit was tied to the rolled-back session") describes a behavior that does not exist in PostgreSQL. The test has been broken since written; the loop-conflict skip masked it.

**Phase 18 does NOT touch this test.**

**Deferred to POLISH-03 (Phase 19).** POLISH-03's mandate — "make the atomicity test actually work" — covers the line-388 fix. The fix is one of:
- (a) Invert the assertion to `assert row is not None` and rewrite the message to reflect the actual atomicity claim ("approve+events rolled back; prior propose remains durable"), or
- (b) Drop the second-half single-session block and put a real cross-session atomicity test in the placeholder slot at line 356.

Either approach is POLISH-03's call.

**HARNESS-02 acceptance was explicitly amended** to treat `test_transition_atomicity` as 1 expected FAIL rather than the original "47 passed" — the amendment is recorded in CONTEXT D-07 and the HARNESS-02 SUMMARY.

---

## Out-of-Scope Confirmation

Per CONTEXT `<deferred>` block — all confirmed as not touched in Phase 18:

| Item | Status |
|------|--------|
| CI matrix job with Postgres service container | Deferred to v1.5+ |
| Cross-host (assist-01) staged-ops UAT replication | Deferred — dev-host UAT sufficient |
| `AsyncTestClient` shim class (option 3b) | Rejected — abstraction debt |
| `session_factory` auto-seeded default project (option 2a) | Rejected — couples unrelated tests |
| `_OLLAMA_TOOL_MODELS` allow-list audit | Phase 19 territory |
| SEED-CHAT-STREAMING-V1.4.x | Explicitly out-of-scope per v1.4.x REQUIREMENTS |

---

## Carry-Forward

**POLISH-03 (Phase 19)** is the consumer of the sole deferral from Phase 18:

- `tests/test_staged_operations.py::test_transition_atomicity` — pre-existing test logic bug at line 388 (assert row is None contradicts SQLAlchemy/Postgres commit semantics). Fix or rewrite within POLISH-03's "make the atomicity test actually work" mandate.

No other Phase 18 items carry forward. HARNESS-01, HARNESS-02, HARNESS-03 are all closed with live UAT evidence.

---

## Phase Commit Log

| Commit | Plan | Message |
|--------|------|---------|
| `75f8c2a` | 18-01 (HARNESS-01) | `test(harness-01): migrate staged_client fixture to httpx.AsyncClient + ASGITransport` |
| `28437ed` | 18-02 (HARNESS-02) | `test(harness-02): seed DBProject parent rows for FK-violating staged-ops tests` |
| `d19c0ba` | 18-03 (HARNESS-03) | `test(harness-03): remove FORGE_TEST_DB=1 gate; wrap pg_terminate_backend teardown` |

Three commits. One per requirement. Entire diff scope is `tests/`. No production source modified in Phase 18.

---

*Phase: 18-staged-handlers-test-harness-rework*
*Completed: 2026-04-29*
*v1.4.x Carry-Forward Debt — HARNESS-01/02/03 paid.*
