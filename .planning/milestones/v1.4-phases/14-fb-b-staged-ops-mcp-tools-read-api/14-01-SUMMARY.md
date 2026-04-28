---
phase: 14
plan: "01"
subsystem: store
tags: [staged-ops, repository, read-api, wr-01, tdd]
dependency_graph:
  requires:
    - "13-fb-a: StagedOpRepo.propose/approve/reject/execute/fail (FB-A lifecycle)"
    - "forge_bridge/store/models.py: DBEntity with entity_type, status, project_id, created_at"
    - "forge_bridge/store/repo.py: EntityRepo.list_by_type pattern"
  provides:
    - "StagedOpRepo.list(status, limit, offset, project_id) -> (list[StagedOperation], int)"
    - "from_status=None discriminator in StagedOpLifecycleError for not-found case (WR-01)"
  affects:
    - "14-02: ConsoleReadAPI.get_staged_ops() calls StagedOpRepo.list()"
    - "14-03: GET /api/v1/staged HTTP route calls ConsoleReadAPI.get_staged_ops()"
    - "14-04: MCP tools forge_list_staged/forge_get_staged call ConsoleReadAPI"
    - "14-05: forge://staged/pending resource calls ConsoleReadAPI.get_staged_ops()"
    - "14-03/14-04: from_status is None discriminator enables 404 vs 409 split"
tech_stack:
  added: []
  patterns:
    - "EntityRepo.list_by_type analog (repo.py:295) extended with count query + pagination"
    - "SQLAlchemy parameterized WHERE clause via tuple unpacking into .where(*base_filter)"
    - "TDD RED/GREEN cycle with Postgres-skip gate (conftest.py session_factory)"
key_files:
  created: []
  modified:
    - forge_bridge/store/staged_operations.py
    - tests/test_staged_operations.py
decisions:
  - "list() imports sqlalchemy.func and select at module level (not inline) per plan note"
  - "_to_staged_operation helper name confirmed: exactly that name, no deviation"
  - "WR-01 fix uses from_status=None discriminator (not optional not_found: bool field) per RESEARCH.md Q1 primary recommendation"
  - "test_transition_wrong_entity_type inserts DBEntity(entity_type='shot') directly via session.add — confirms both branches of the not-found guard"
metrics:
  duration: "~10 minutes"
  completed: "2026-04-26T19:43:00Z"
  tasks_completed: 2
  files_modified: 2
---

# Phase 14 Plan 01: StagedOpRepo.list() + WR-01 Fix Summary

StagedOpRepo.list(status, limit, offset, project_id) read method with DESC ordering and pre-pagination total count, plus WR-01 from_status=None not-found discriminator replacing "(missing)" sentinel.

## What Was Built

### Task 1: StagedOpRepo.list() (TDD GREEN)

Added `async def list(status, limit, offset, project_id) -> tuple[list[StagedOperation], int]` to `StagedOpRepo` in `forge_bridge/store/staged_operations.py`:

- Placed after the existing `get()` method, before `approve()`
- Added `from sqlalchemy import func, select` at module level
- Filters compose via SQL AND using tuple unpacking `where(*base_filter)` (T-14-01-01 tamper mitigation — parameterized, never f-string)
- D-01 ordering: `.order_by(DBEntity.created_at.desc())`
- Separate COUNT query for total-before-pagination (`func.count().select_from(DBEntity).where(*base_filter)`)
- Calls `self._to_staged_operation(db)` — helper exists with that exact name (no deviation)
- Does NOT call `await session.commit()` — caller owns transaction boundary per FB-A repo contract

### Task 2: WR-01 Fix (D-17a)

In `_transition()` not-found branch (line ~289):
- Before: `from_status="(missing)"` — type-contract bug, string where `str | None` was declared
- After: `from_status=None` — load-bearing discriminator for FB-B 404/409 split
- Added comment trail explaining `from_status is None` → HTTP 404 mapping in Plans 14-03 + 14-04

## Test Cases Added

**13 new tests total** (9 list + 4 WR-01):

| Test | Coverage |
|------|----------|
| test_staged_op_list_default_returns_all_statuses | No filter returns all statuses |
| test_staged_op_list_filter_by_status_proposed | status filter returns matching only |
| test_staged_op_list_filter_by_status_approved | status filter (approved variant) |
| test_staged_op_list_filter_by_project_id | project_id filter |
| test_staged_op_list_combined_filter | AND composition of both filters |
| test_staged_op_list_orders_by_created_at_desc | D-01 created_at DESC invariant |
| test_staged_op_list_pagination_clamp_in_caller | limit/offset pagination, non-overlapping pages |
| test_staged_op_list_empty_result | Empty database returns ([], 0) |
| test_staged_op_list_total_reflects_filtered_set | total == filtered count BEFORE pagination |
| test_transition_unknown_uuid_raises_with_from_status_none | WR-01: approve(bogus) → from_status is None |
| test_transition_unknown_uuid_for_reject_also_raises_from_status_none | WR-01: reject(bogus) → from_status is None |
| test_transition_wrong_entity_type_raises_from_status_none | WR-01: wrong entity_type → from_status is None |
| test_transition_illegal_status_keeps_from_status_set | WR-01: must NOT apply to legitimate illegal transitions |

**All tests skip cleanly** on machines without Postgres at localhost:5432 (fixture gate in conftest.py).

## FB-A Test Adjustments

None. All 592 existing tests continue to pass. The `test_transition_legality` parameterized cross-product was NOT modified — it asserts `exc_info.value.from_status == from_status` for illegal transitions where `from_status` is a real status string (proposed/approved/etc.), which remains correct after WR-01. The only affected path was the `from_status is None` not-found case which the cross-product test skips for `(None, X)` rows.

## Helper Name Confirmation

`_to_staged_operation` exists with exactly that name at line 393 of `staged_operations.py`. Plan 14-02's `get_staged_op` implementation can call `self._to_staged_operation(db)` without any deviation.

## WR-01 Sentinel Elimination Confirmed

```
$ grep -n '"(missing)"' forge_bridge/store/staged_operations.py | grep -v "WR-01 bug"
# → zero results
```

The only remaining occurrence of the string `"(missing)"` is inside the WR-01 comment that explains why it was removed.

## Deviations from Plan

### Auto-fixed Issues

None.

### Minor Pattern Deviation: entity_type filter grep criterion

The plan's acceptance criterion stated `grep -n 'DBEntity.entity_type == "staged_operation"'` should return "at least 2 matches (existing `_transition` plus the new `list()` filter)". In practice:

- `list()` adds a SQLAlchemy expression: `DBEntity.entity_type == "staged_operation"` (line 198) — 1 match
- `_transition` uses a Python attribute check: `db_entity.entity_type != "staged_operation"` (line 323) — does NOT match the grep pattern

**Impact:** None. The behavior is correct — both locations filter for `staged_operation` entity type. The plan's expected grep count was based on an assumption that `_transition` also used the SQLAlchemy ORM expression, but it uses a post-fetch Python attribute comparison (which is correct for a `session.get()` result). Criterion intent is satisfied; grep pattern was slightly off.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. This plan is store-layer only (no HTTP routes, no MCP tools). The `list()` method participates in the existing SELECT read path — no new trust boundaries created.

| Threat | Status |
|--------|--------|
| T-14-01-01 (SQL injection via filter params) | Mitigated — SQLAlchemy parameterized `.where(DBEntity.status == status)` |
| T-14-01-02 (error message information disclosure) | Accepted — no secrets in from_status/to_status/op_id |
| T-14-01-03 (WR-01 sentinel consumer) | Resolved — sentinel eliminated; None discriminator now canonical |
| T-14-01-04 (COUNT query DoS) | Accepted — v1.4 volumes are small; cursor pagination is v1.5 |

## Known Stubs

None. `list()` is fully implemented and returns real data from the database. The WR-01 fix is a one-line value change.

## Self-Check: PASSED

Files created/modified exist:
- `forge_bridge/store/staged_operations.py` — FOUND
- `tests/test_staged_operations.py` — FOUND

Commits exist:
- `1a17dda` — test(14-01): failing tests (RED phase)
- `b3bae6d` — feat(14-01): StagedOpRepo.list() + WR-01 fix (GREEN phase)
