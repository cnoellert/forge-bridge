---
phase: 13-fb-a-staged-operation-entity-lifecycle
reviewed: 2026-04-25T00:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - forge_bridge/store/migrations/versions/0003_staged_operation.py
  - forge_bridge/store/models.py
  - forge_bridge/core/staged.py
  - forge_bridge/core/__init__.py
  - forge_bridge/store/staged_operations.py
  - forge_bridge/store/repo.py
  - forge_bridge/store/__init__.py
  - tests/test_staged_operations.py
  - tests/conftest.py
findings:
  critical: 0
  warning: 2
  info: 4
  total: 6
status: issues_found
---

# Phase 13 (FB-A): Code Review Report

**Reviewed:** 2026-04-25
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

This review covers the staged-operation entity and lifecycle implementation for Phase 13 (FB-A). The core design — state machine in `StagedOpRepo`, audit event emission via composed `EventRepo`, single `to_dict()` contract anchor on `StagedOperation`, and JSONB read-modify-write that preserves `parameters` immutability — is sound and well-executed.

Two warnings require attention before FB-B begins: a type contract mismatch in `StagedOpLifecycleError` that will cause silent mis-handling in the API layer, and a test gap in the atomicity test that leaves the first rollback sub-test unverified. Four info-level items are noted for awareness.

No critical security issues found.

---

## Warnings

### WR-01: `StagedOpLifecycleError.from_status` type contract violated for missing-entity case

**File:** `forge_bridge/store/staged_operations.py:289-290`

**Issue:** `StagedOpLifecycleError.__init__` declares `from_status: str | None` — the `None` value is the intended sentinel meaning "no existing status" (i.e., the initial `propose()` transition). However, the missing-entity branch in `_transition` passes the string `"(missing)"` instead of `None`:

```python
raise StagedOpLifecycleError(
    from_status="(missing)", to_status=new_status, op_id=op_id,
)
```

FB-B API handlers catching this exception will likely check `exc.from_status is None` to distinguish "entity not found" from "illegal transition on an existing entity." That check silently fails with `"(missing)"`, making both cases indistinguishable at the API boundary. The correct sentinel is `None`, matching the type annotation and the `(None, "proposed")` entry in `_ALLOWED_TRANSITIONS`.

**Fix:**
```python
# staged_operations.py line 289
raise StagedOpLifecycleError(
    from_status=None, to_status=new_status, op_id=op_id,
)
```

If callers need to distinguish "not found" from "illegal proposed→proposed re-entry" (both have `from_status=None`), add a separate `not_found: bool = False` parameter to `StagedOpLifecycleError`, or raise a different exception type (e.g., `EntityNotFoundError`) for the missing-entity case.

---

### WR-02: `test_transition_atomicity` abandons the first rollback sub-test without assertions

**File:** `tests/test_staged_operations.py:325-356`

**Issue:** The test proposes an operation and commits it (lines 325-333), then calls `approve` + `flush` + `rollback` in a second session (lines 338-343), then opens a third session and calls `repo.get(op_id)` (lines 347-349) — but instead of asserting `fetched.status == "proposed"` and `fetched is not None`, it substitutes `assert True` with a comment explaining the "meaningful check is below." The first rollback sub-test contributes no actual assertions to the test suite.

The second sub-test (lines 358-394) does exercise atomicity correctly within a single session. But the cross-session rollback scenario (session A proposes+commits, session B approves+rollbacks, session C verifies) is exactly the most realistic production scenario and remains unverified.

**Fix:**
```python
# Replace lines 347-356 with:
async with session_factory() as session:
    repo = StagedOpRepo(session)
    fetched = await repo.get(op_id)

assert fetched is not None, "entity should still exist after rollback in another session"
assert fetched.status == "proposed", (
    "ATOMICITY VIOLATED: status advanced to 'approved' despite rollback"
)

async with session_factory() as session:
    events = await EventRepo(session).get_recent(entity_id=op_id, limit=10)
assert len(events) == 1, "only staged.proposed should exist; staged.approved was rolled back"
assert events[0].event_type == "staged.proposed"
```

---

## Info

### IN-01: Unused import in `conftest.py`

**File:** `tests/conftest.py:100-101`

**Issue:** `get_async_session_factory` is imported as `_phase13_get_async_session_factory` but never referenced anywhere in the file. The fixture builds its own engine and session factory directly without using this import.

**Fix:** Remove the unused import:
```python
# Remove lines 100-101:
from forge_bridge.store.session import (
    get_async_session_factory as _phase13_get_async_session_factory,
)
```

---

### IN-02: Deserialization logic duplicated across `StagedOpRepo._to_staged_operation` and `EntityRepo._to_core`

**File:** `forge_bridge/store/staged_operations.py:393-422` and `forge_bridge/store/repo.py:484-499`

**Issue:** Both methods contain identical logic to reconstruct a `StagedOperation` from a `DBEntity`. The docstring in `staged_operations.py` acknowledges the duplication ("both must produce identical StagedOperation instances") but does not extract the shared logic. Any future field added to `StagedOperation` (e.g., `rejected_at` in a later phase) must be updated in two places. Given the explicit note in the docstring, this appears to be an intentional deferral — documenting it here for the FB-B planning brief.

**Fix:** Extract a module-level function in `staged_operations.py`:
```python
def _db_to_staged_operation(db: DBEntity) -> StagedOperation:
    ...  # current body of _to_staged_operation
```

Then call it from both `StagedOpRepo._to_staged_operation` and `EntityRepo._to_core`'s `staged_operation` branch.

---

### IN-03: `test_transition_legality` generates untestable `(None, X)` rows in the parameterized cross-product

**File:** `tests/test_staged_operations.py:83-124`

**Issue:** `_CROSS_PRODUCT` includes five rows where `from_status is None` and `to_status != "proposed"`. These are immediately `pytest.skip()`ed at runtime, producing skipped-test noise in CI output. The rows are architecturally untestable because there is no public API to create a `staged_operation` entity without going through `propose()`, which enforces `(None, "proposed")`.

**Fix:** Filter untestable rows from the parametrize list rather than skipping them at runtime:
```python
_CROSS_PRODUCT = [
    (f, t, ((f, t) in _LEGAL))
    for f in _STATUSES_FROM
    for t in _STATUSES_TO
    # (None, X) rows other than (None, "proposed") are untestable via public API
    if not (f is None and t != "proposed")
]
```

Handle `(None, "proposed")` as an inline check in the test body (it is already handled specially via the `propose()` call above).

---

### IN-04: `BridgeEntity.__init__` uses `datetime.utcnow()` (deprecated in Python 3.12)

**File:** `forge_bridge/core/entities.py:67`

**Issue:** `datetime.utcnow()` is deprecated since Python 3.12 and returns a naive datetime (no timezone info). `StagedOperation` inherits this via `BridgeEntity.__init__`, so `op.created_at` is a naive UTC datetime while `op.approved_at` and `op.executed_at` are timezone-aware (produced by `datetime.now(timezone.utc).isoformat()` in `staged_operations.py`). This inconsistency means `to_dict()` serializes `created_at` without a `+00:00` suffix but `approved_at`/`executed_at` with one — a FB-B contract inconsistency.

**Fix (in `forge_bridge/core/entities.py` line 67):**
```python
from datetime import datetime, timezone
# ...
self.created_at: datetime = created_at or datetime.now(timezone.utc)
```

Note: `entities.py` is outside this phase's review scope but the inconsistency surfaces through `StagedOperation.to_dict()` and is worth a follow-up before FB-B ships the public API contract.

---

_Reviewed: 2026-04-25_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
