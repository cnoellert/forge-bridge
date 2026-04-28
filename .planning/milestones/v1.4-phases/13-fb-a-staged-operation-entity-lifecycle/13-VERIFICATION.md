---
phase: 13-fb-a-staged-operation-entity-lifecycle
verified: 2026-04-26T00:00:00Z
status: human_needed
score: 4/4
overrides_applied: 0
human_verification:
  - test: "Run pytest tests/test_staged_operations.py -v on a Postgres-equipped machine"
    expected: "34 passed (0 skipped) — all five tests including the cross-session rollback atomicity sub-test pass against a real Postgres backend"
    why_human: "No Postgres at localhost:5432 in this environment — all 34 tests skip cleanly. Static analysis confirms the test bodies are structurally correct and wired to the right code paths, but end-to-end DB execution cannot be mechanically verified without a live backend."
---

# Phase 13 (FB-A): Staged Operation Entity & Lifecycle Verification Report

**Phase Goal:** A new `staged_operation` entity type participates in the existing extensible entity model with a full proposed→approved→executed/rejected/failed lifecycle enforced in the data layer. Every transition emits a `DBEvent` for audit. Stores proposer identity, operation name, proposed parameters (JSONB), realized result diff (JSONB), and timing.
**Verified:** 2026-04-26T00:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `entity_type='staged_operation'` entities can be created via the store layer with `proposer`, `operation`, `parameters` (JSONB), and initial `status='proposed'` — verified via direct SQLAlchemy round-trip test | VERIFIED | `ENTITY_TYPES` contains `'staged_operation'`; `StagedOperation` class with `entity_type` override confirmed; `EntityRepo._attrs_to_dict` + `_to_core` branches verified via in-memory smoke; `test_staged_op_round_trip` exercises full two-session DB round-trip (skipped without Postgres — see human verification) |
| 2 | Lifecycle transitions enforced: proposed→approved→executed (happy), proposed→rejected (veto), approved→failed (error). Illegal transitions raise `StagedOpLifecycleError` with attempted transition in message | VERIFIED | `StagedOpRepo._ALLOWED_TRANSITIONS` is a frozenset of exactly 5 D-10 tuples; `_transition` raises `StagedOpLifecycleError` for any non-member (from, to) pair; `StagedOpLifecycleError` carries `from_status`/`to_status`/`op_id` fields and message includes all three; `test_transition_legality` exercises the full (from × to) cross-product with 30 parametrized cases |
| 3 | Every transition writes a `DBEvent` row with `old_status`, `new_status`, actor, and timestamp — queryable by `entity_id` | VERIFIED | `StagedOpRepo._append_event` composes `EventRepo` (never `session.add(DBEvent(...))` directly); `_TRANSITION_EVENTS` map covers all 5 transitions with correct D-06 event-type strings; `DBEvent.entity_id` wired via `entity_id=op_id` in `_append_event`; `test_audit_replay` asserts 3-event happy path + 2-event veto/failure paths with full D-07 payload shape |
| 4 | `parameters` JSONB preserved verbatim across status advancement (never mutated); `result` JSONB populated only on `executed` or `failed`. A `parameters` vs `result` diff recoverable via SQL alone | VERIFIED | None of the four transition methods (`approve`, `reject`, `execute`, `fail`) include `parameters` in their `attribute_updates` dicts; `_transition`'s read-modify-write starts from `dict(db_entity.attributes or {})` and only writes supplied keys; `test_sql_only_parameter_diff` uses raw `attributes->'parameters'` JSONB-arrow SELECT to assert bit-identity across proposed/approved/executed states |

**Score:** 4/4 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `forge_bridge/store/models.py` | ENTITY_TYPES + EVENT_TYPES extensions; ck_entities_type auto-regenerates from `sorted(ENTITY_TYPES)` | VERIFIED | `'staged_operation'` in `ENTITY_TYPES` (8 types total); five `staged.*` events in `EVENT_TYPES` (32 types total); `sorted(ENTITY_TYPES)` in `DBEntity.__table_args__` unchanged |
| `forge_bridge/store/migrations/versions/0003_staged_operation.py` | Alembic migration for ck_entities_type with staged_operation | VERIFIED | `revision="0003"`, `down_revision="0002"`; upgrade adds 8-type CHECK; downgrade restores 7-type CHECK verbatim from 0001; both `upgrade` and `downgrade` callable; no `op.add_column`, `op.bulk_insert`, or `op.create_table` |
| `forge_bridge/core/staged.py` | StagedOperation class with entity_type override and 16-key to_dict() | VERIFIED | 114 lines; inherits `BridgeEntity` only (no Versionable); `entity_type` property returns literal `"staged_operation"`; `to_dict()` produces exactly 16 keys (6 from super + 9 typed fields + status); `isinstance(op, Versionable)` is False |
| `forge_bridge/core/__init__.py` | Re-export of StagedOperation alongside the nine existing entity classes | VERIFIED | `from forge_bridge.core.staged import StagedOperation` present; `"StagedOperation"` in `__all__`; `from forge_bridge.core import StagedOperation` succeeds; all 9 pre-existing entity exports intact |
| `forge_bridge/store/staged_operations.py` | StagedOpRepo with propose/approve/reject/execute/fail/get methods + StagedOpLifecycleError | VERIFIED | 422 lines (> 200 required); `StagedOpRepo` and `StagedOpLifecycleError` both present; `_ALLOWED_TRANSITIONS` frozenset with 5 tuples; `_TRANSITION_EVENTS` dict covering all 5; `self._events = EventRepo(session)` composition; no `session.add(DBEvent(...))` in functional code; no `await self.session.commit()` calls |
| `forge_bridge/store/repo.py` | Extended EntityRepo with staged_operation branch in _attrs_to_dict and _to_core | VERIFIED | 2× `elif t == "staged_operation":` branches present (one in each method); `name = getattr(entity, "operation", None)` denormalization in `save()`; `StagedOperation.__new__(StagedOperation)` deserialization idiom in `_to_core`; all pre-existing 7 entity-type branches unchanged |
| `forge_bridge/store/__init__.py` | Re-export StagedOpRepo and StagedOpLifecycleError | VERIFIED | Both in `__all__`; importable via `from forge_bridge.store import StagedOpRepo, StagedOpLifecycleError`; NOT in `forge_bridge.__all__` (D-09 holds); all 12 pre-existing exports intact |
| `tests/conftest.py` | session_factory async-DB fixture for store-layer integration tests | VERIFIED | `session_factory` fixture exists and is callable; `_phase13_postgres_available` probe present; `Base.metadata.create_all` schema setup; `DROP DATABASE` + `pg_terminate_backend` teardown; `import pytest_asyncio` present; all 4 pre-existing fixtures intact |
| `tests/test_staged_operations.py` | Five test functions covering STAGED-01..04 + atomicity | VERIFIED | 394 lines (> 250 required); all 5 test functions present; `@pytest.mark.parametrize` cross-product (30 cases); `attributes->'parameters'` JSONB-arrow syntax; `entity_id=` query; `session.flush` + `session.rollback` atomicity assertions; 34 tests collected; 34 skipped cleanly without Postgres |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `forge_bridge/store/models.py:DBEntity.__table_args__` | `ENTITY_TYPES` frozenset | `f-string at class definition time — sorted(ENTITY_TYPES)` | VERIFIED | `sorted(ENTITY_TYPES)` drives the ck_entities_type CHECK literal at module import |
| `forge_bridge/store/migrations/versions/0003_staged_operation.py` | ck_entities_type CHECK constraint | `op.drop_constraint + op.create_check_constraint` idiom | VERIFIED | `ck_entities_type` appears in both upgrade and downgrade; 8-type upgrade literal correct |
| `forge_bridge/core/staged.py:StagedOperation.entity_type` | `forge_bridge/store/repo.py:EntityRepo.save` | `@property` returning literal `"staged_operation"` | VERIFIED | `return "staged_operation"` confirmed in staged.py; EntityRepo.save reads `entity.entity_type` at discriminator write |
| `forge_bridge/core/__init__.py` | `forge_bridge/core/staged.py` | `from forge_bridge.core.staged import StagedOperation` | VERIFIED | Import line confirmed in __init__.py |
| `forge_bridge/store/staged_operations.py:StagedOpRepo._transition` | `forge_bridge/store/repo.py:EventRepo.append` | Composed EventRepo — `self._events = EventRepo(session)` | VERIFIED | `self._events = EventRepo(session)` at line 131 of staged_operations.py; `self._events.append(...)` used in `_append_event` |
| `forge_bridge/store/staged_operations.py:StagedOpRepo._ALLOWED_TRANSITIONS` | D-10 lifecycle enforcement | frozenset of (from_status, to_status) tuples — O(1) legality check | VERIFIED | frozenset confirmed with exactly 5 D-10 tuples; `_transition` checks `(old_status, new_status) not in self._ALLOWED_TRANSITIONS` |
| `forge_bridge/store/repo.py:EntityRepo._attrs_to_dict` | D-02 staged_operation JSONB shape | `elif t == "staged_operation"` branch writing 8 typed fields | VERIFIED | Branch confirmed; in-memory smoke test returns correct 8-key dict |
| `tests/conftest.py:session_factory` | `forge_bridge/store/session.py` Base + create_async_engine | `Base.metadata.create_all` schema setup | VERIFIED | `Base.metadata.create_all` confirmed in conftest; direct `create_async_engine` (not singleton) |
| `tests/test_staged_operations.py` | `forge_bridge/store/staged_operations.py` + `forge_bridge/store/repo.py` | `from forge_bridge.store import StagedOpRepo, StagedOpLifecycleError, EventRepo` | VERIFIED | Barrel import confirmed; 34 test cases collected without import errors |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `StagedOpRepo.propose` | `op.parameters` | Caller-supplied dict passed to `StagedOperation.__init__` then serialized into `DBEntity.attributes` via `_serialize()` | Yes — persisted to `entities.attributes` JSONB column | FLOWING |
| `StagedOpRepo._transition` | `db_entity.attributes` | `await self.session.get(DBEntity, op_id)` → read-modify-write on existing DB row | Yes — reads from DB, writes back mutated dict with transition fields appended | FLOWING |
| `EntityRepo._attrs_to_dict` | `attrs` dict | `entity.operation`, `entity.proposer`, `entity.parameters` etc. from `StagedOperation` instance fields | Yes — reads typed instance attributes, not placeholder values | FLOWING |
| `EntityRepo._to_core` (staged_op branch) | `e.parameters`, `e.status` etc. | `a = db.attributes or {}` where `db` is a fetched `DBEntity` row | Yes — deserializes from actual DB-fetched JSONB; no hardcoded stubs | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command / Check | Result | Status |
|----------|----------------|--------|--------|
| `ENTITY_TYPES` contains `staged_operation` | `python -c "from forge_bridge.store.models import ENTITY_TYPES; assert 'staged_operation' in ENTITY_TYPES"` | Pass | PASS |
| `EVENT_TYPES` contains all five staged.* events | `python -c "from forge_bridge.store.models import EVENT_TYPES; assert {'staged.proposed','staged.approved','staged.rejected','staged.executed','staged.failed'} <= EVENT_TYPES"` | Pass | PASS |
| `StagedOperation.entity_type` returns `"staged_operation"` | `python -c "from forge_bridge.core import StagedOperation; op = StagedOperation(operation='x', proposer='y', parameters={}); assert op.entity_type == 'staged_operation'"` | Pass | PASS |
| `StagedOperation.to_dict()` returns 16-key shape | In-process check — set(d.keys()) matches expected_16_keys | Pass | PASS |
| `StagedOpRepo._ALLOWED_TRANSITIONS` has exactly 5 D-10 tuples | `python -c "from forge_bridge.store import StagedOpRepo; assert len(StagedOpRepo._ALLOWED_TRANSITIONS) == 5"` | Pass | PASS |
| `StagedOpLifecycleError` subclasses `Exception` directly | `python -c "from forge_bridge.store import StagedOpLifecycleError; assert StagedOpLifecycleError.__bases__ == (Exception,)"` | Pass | PASS |
| `StagedOpLifecycleError` message format | `err = StagedOpLifecycleError(from_status='proposed', to_status='executed', op_id=uuid4())` — message contains `'proposed'`, `'executed'`, `'staged_operation'` | Pass | PASS |
| `EntityRepo._attrs_to_dict` returns correct 8-key JSONB shape | In-memory smoke via `_MockSess` — no missing keys | Pass | PASS |
| D-09 invariant holds | `'StagedOpRepo' not in forge_bridge.__all__` + `'StagedOpLifecycleError' not in forge_bridge.__all__` | Both True | PASS |
| No regression in existing 592 tests | `pytest --ignore=tests/test_staged_operations.py` | 592 passed, 0 failed | PASS |
| Postgres tests skip cleanly (not fail) without Postgres | `pytest tests/test_staged_operations.py -v` | 34 skipped, exit 0 | PASS |
| Migration module loads and revision chain correct | `spec.loader.exec_module(m)` — `m.revision == "0003"`, `m.down_revision == "0002"` | Pass | PASS |
| Banned pattern: no `session.add(DBEvent(...))` in functional code | `grep -n "session\.add(DBEvent" staged_operations.py` | 0 matches in functional code (4 in comments/docstrings only) | PASS |
| Banned pattern: no `await self.session.commit()` in staged_operations.py | `grep -n "await self.session.commit" staged_operations.py` | 0 matches in functional code (3 in docstrings only) | PASS |

---

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|------------|---------------|-------------|--------|----------|
| STAGED-01 | 13-01, 13-02, 13-03, 13-04 | Round-trip test: entity_type='staged_operation' with proposer/operation/parameters/status='proposed' | VERIFIED | ENTITY_TYPES extension (01), StagedOperation class + entity_type override (02), EntityRepo _attrs_to_dict/_to_core branches (03), test_staged_op_round_trip (04) |
| STAGED-02 | 13-03, 13-04 | Lifecycle transitions enforced; illegal transitions raise StagedOpLifecycleError with message | VERIFIED | StagedOpRepo._ALLOWED_TRANSITIONS frozenset + _transition raises error; test_transition_legality cross-product |
| STAGED-03 | 13-03, 13-04 | Every transition writes a DBEvent with old_status/new_status/actor/timestamp queryable by entity_id | VERIFIED | EventRepo composition in _append_event; _TRANSITION_EVENTS map; test_audit_replay 3-path coverage |
| STAGED-04 | 13-03, 13-04 | parameters JSONB preserved verbatim; result populated only on executed/failed; diff via SQL alone | VERIFIED | _transition never touches parameters key; test_sql_only_parameter_diff raw JSONB-arrow SELECT |

No orphaned requirements — STAGED-01..04 are declared in all four plans and traceable to REQUIREMENTS.md. STAGED-05..07 are explicitly Phase 14 (FB-B) scope per REQUIREMENTS.md traceability table.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `forge_bridge/store/staged_operations.py` | 290 | `from_status="(missing)"` string literal passed where `str \| None` type annotation expects `None` for "no prior status" semantics | Warning (WR-01 from REVIEW) | FB-B API handlers that check `exc.from_status is None` to distinguish "entity not found" from "illegal transition on existing entity" will silently misclassify the "not found" case. Does not affect the correctness of the state machine itself — only the exception-handling surface for FB-B. Documented in `13-REVIEW.md`. |
| `tests/test_staged_operations.py` | 356 | `assert True  # placeholder` in `test_transition_atomicity` — first cross-session rollback sub-test (session A proposes+commits, session B approves+rollbacks, session C verifies) contains no real assertions | Warning (WR-02 from REVIEW) | The cross-session atomicity scenario is the most realistic production case and remains unverified. The single-session sub-test (lines 358-394) correctly exercises rollback semantics. Documented in `13-REVIEW.md`. |
| `tests/conftest.py` | 101 | `_phase13_get_async_session_factory` imported but never referenced | Info (IN-01 from REVIEW) | Dead import — no functional impact |
| `tests/test_staged_operations.py` | 83-124 | `_CROSS_PRODUCT` includes 4 untestable `(None, X)` rows where X != "proposed" — these produce `pytest.skip()` noise in CI output | Info (IN-03 from REVIEW) | CI output noise only; test coverage is not reduced |

The two warnings (WR-01, WR-02) are pre-existing findings documented in the phase code review (`13-REVIEW.md`, 0 critical findings). Neither blocks the phase goal as stated. WR-01 is a type-contract issue for FB-B's exception handling surface. WR-02 leaves a cross-session atomicity scenario untested but does not contradict the goal's requirement for event emission.

---

### Human Verification Required

#### 1. End-to-end DB integration — all four STAGED success criteria

**Test:** On a machine with Postgres at localhost:5432 (or with `FORGE_DB_URL` pointing at a reachable Postgres instance), run:
```bash
cd forge-bridge
pytest tests/test_staged_operations.py -v
```
**Expected:** 34 passed (0 skipped, 0 failed). All five test functions execute against a live Postgres backend:
- `test_staged_op_round_trip` — STAGED-01 round-trip persistence verified
- `test_transition_legality[*]` — STAGED-02 state machine verified (30 parametrized cases: 5 legal pass, 25 illegal raise StagedOpLifecycleError)
- `test_audit_replay` — STAGED-03 audit trail verified (3 lifecycle paths, D-07 payload shapes, client_name duplication)
- `test_sql_only_parameter_diff` — STAGED-04 JSONB-arrow SQL diff verified (parameters bit-identical across proposed/approved/executed; result null until terminal)
- `test_transition_atomicity` — atomicity invariant verified

**Why human:** No Postgres at localhost:5432 in this verification environment. All 34 tests skip cleanly (exit 0) without a live backend. Static analysis confirms all assertions map correctly to the implementation, but mechanical verification requires actual DB I/O.

**Secondary check (WR-02):** After the `pytest -v` run passes, confirm `test_transition_atomicity` is PASSED (not just skipped) and review whether the cross-session rollback sub-test (`assert True` at line 356) should be replaced with real assertions per the `13-REVIEW.md` WR-02 recommendation before FB-B begins.

---

### Gaps Summary

No blocking gaps. All four STAGED success criteria are implemented and structurally verified. The two review warnings (WR-01, WR-02) are pre-existing findings from `13-REVIEW.md` and do not prevent the phase goal from being achieved in principle. They are recommended fixes before FB-B (Phase 14) ships its API layer.

The single gating item is human/Postgres verification of the 34 integration tests.

---

_Verified: 2026-04-26T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
