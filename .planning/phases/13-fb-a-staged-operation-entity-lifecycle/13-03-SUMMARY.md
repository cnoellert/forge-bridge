---
phase: 13-fb-a-staged-operation-entity-lifecycle
plan: "03"
subsystem: store
tags:
  - staged-operation
  - state-machine
  - audit-trail
  - entity-repo
  - lifecycle
dependency_graph:
  requires:
    - 13-01  # DBEntity + DBEvent schema with ENTITY_TYPES + EVENT_TYPES
    - 13-02  # StagedOperation core entity class
  provides:
    - StagedOpRepo (forge_bridge.store.staged_operations)
    - StagedOpLifecycleError (forge_bridge.store.staged_operations)
    - EntityRepo staged_operation branch (_attrs_to_dict, _to_core, save)
    - forge_bridge.store barrel re-exports
  affects:
    - 13-04  # Plan 04 test suite exercises StagedOpRepo end-to-end
tech_stack:
  added:
    - forge_bridge/store/staged_operations.py (new module, 422 lines)
  patterns:
    - Composed EventRepo for audit writes (PATTERNS.md Finding #8)
    - BridgeEntity.__init__ deserialization idiom (Version pattern, repo.py:424-431)
    - frozenset O(1) legality check for state-machine transitions
key_files:
  created:
    - forge_bridge/store/staged_operations.py
  modified:
    - forge_bridge/store/repo.py
    - forge_bridge/store/__init__.py
decisions:
  - StagedOpRepo and StagedOpLifecycleError co-locate in staged_operations.py (state-machine constants are unique to this entity; avoids growing repo.py to 30KB+)
  - StagedOpLifecycleError subclasses Exception directly per PATTERNS.md Findings #5/#7 (not RegistryError -- unrelated domain)
  - _transition read-modify-write preserves parameters key verbatim (STAGED-04 SQL-only-diff invariant, D-22)
  - No internal session.commit() calls -- caller owns transaction boundaries (matching EntityRepo/EventRepo conventions)
  - D-09 honored: StagedOpRepo/StagedOpLifecycleError in store.__all__ but NOT in forge_bridge.__all__
metrics:
  duration: "~7 minutes"
  completed_date: "2026-04-26"
  tasks_completed: 3
  files_created: 1
  files_modified: 2
requirements_addressed:
  - STAGED-01  # round-trip via EntityRepo._attrs_to_dict + _to_core
  - STAGED-02  # lifecycle enforcement via StagedOpRepo._transition + _ALLOWED_TRANSITIONS
  - STAGED-03  # audit-trail via composed EventRepo on every transition
  - STAGED-04  # parameters-immutable property (SQL-only-diff) -- _transition never touches parameters
---

# Phase 13 Plan 03: StagedOpRepo State Machine + EntityRepo Extension Summary

Ship the state-machine repository (`StagedOpRepo`) and JSONB serializer extensions
that enforce the `proposed→approved→executed/rejected/failed` lifecycle, write a
`DBEvent` audit row on every transition, and extend `EntityRepo` with the
`staged_operation` branch for full round-trip persistence.

## What Was Built

### New module: `forge_bridge/store/staged_operations.py` (422 lines)

**`StagedOpLifecycleError`** — direct `Exception` subclass carrying structured
`from_status` / `to_status` / `op_id` fields for caller introspection (PATTERNS.md
Findings #5/#7). Produces the D-09 message format:
`"Illegal transition from 'proposed' to 'executed' for staged_operation <uuid>"`.

**`StagedOpRepo`** — the only sanctioned write path for staged operations:

| Method | Transition | `attribute_updates` |
|--------|-----------|----------------------|
| `propose` | (None) → proposed | n/a (direct insert) |
| `approve` | proposed → approved | approver, approved_at |
| `reject`  | proposed → rejected | None |
| `execute` | approved → executed | executor, executed_at, result |
| `fail`    | approved → failed   | executor, executed_at, result |
| `get`     | read-only query | — |

### State machine — D-10 (5 transitions, single source of truth)

`_ALLOWED_TRANSITIONS` frozenset:
- `(None, "proposed")`
- `("proposed", "approved")`
- `("proposed", "rejected")`
- `("approved", "executed")`
- `("approved", "failed")`

Terminals: `rejected`, `executed`, `failed`. Idempotent re-application (e.g., `approved → approved`) raises `StagedOpLifecycleError` immediately per D-10.

### Event-type mapping — D-06 (5 mappings)

`_TRANSITION_EVENTS` dict:
- `(None, "proposed")` → `"staged.proposed"`
- `("proposed", "approved")` → `"staged.approved"`
- `("proposed", "rejected")` → `"staged.rejected"`
- `("approved", "executed")` → `"staged.executed"`
- `("approved", "failed")` → `"staged.failed"`

### Atomicity invariant (security_threat_model T-13-09)

`_transition` mutates `db_entity.status` and calls `await self._events.append(...)` on the SAME `AsyncSession` passed at construction time. Both operations commit or rollback together — there is no window where the status advances without an audit record. The repo never calls `await self.session.commit()`.

### `parameters`-immutability property (STAGED-04, D-22)

None of the four transition methods (`approve`, `reject`, `execute`, `fail`) include `parameters` in their `attribute_updates` dict. The `_transition` read-modify-write starts from `dict(db_entity.attributes or {})` and only writes the keys supplied — `parameters` is never touched after `propose`. This preserves the SQL-only-diff invariant that Plan 04's STAGED-04 test will verify end-to-end.

### PATTERNS.md Finding #8 — composition, not bypass

`StagedOpRepo.__init__` composes `EventRepo(session)` as `self._events`. All audit writes go through `self._events.append(...)`. Grep proof:

```
grep -c "session.add(DBEvent" forge_bridge/store/staged_operations.py
# returns 0 for functional code (comments/docstrings mention it as the prohibited pattern)
```

### `forge_bridge/store/repo.py` — surgical extension (3 additive edits)

1. **Import**: `from forge_bridge.core.staged import StagedOperation` added below the entities import block.
2. **`EntityRepo.save`**: D-03 name-column denormalization — `name = getattr(entity, "operation", None)` when `entity_type == "staged_operation"`, enabling `ix_entities_type_name` index use without JSONB scan.
3. **`EntityRepo._attrs_to_dict`**: new `elif t == "staged_operation":` branch writing the 8-key D-02 JSONB shape (operation/proposer/parameters/result/approver/executor/approved_at/executed_at).
4. **`EntityRepo._to_core`**: new `elif t == "staged_operation":` branch reconstructing `StagedOperation` via the Version-pattern idiom (`StagedOperation.__new__(StagedOperation)` + `BridgeEntity.__init__(e, id=db.id, metadata={})`).

All 7 pre-existing entity-type branches (sequence/shot/asset/version/media/layer/stack) are byte-identical.

### `forge_bridge/store/__init__.py` — barrel re-export

`StagedOpRepo` and `StagedOpLifecycleError` added to the import block and `__all__`.
Final repo-class count in `forge_bridge.store.__all__`: **8 repo classes** (was 7) + 1 exception class entry.

D-09 holds: neither symbol appears in `forge_bridge.__all__` (package-root barrel unchanged).

## Verification Results

All plan verification assertions passed:

- `from forge_bridge.store import StagedOpRepo, StagedOpLifecycleError` — imports cleanly
- `StagedOpRepo._ALLOWED_TRANSITIONS == frozenset(expected_legal)` — 5 transitions, D-10 match
- `set(StagedOpRepo._TRANSITION_EVENTS.keys()) == expected_legal` — event map covers all 5
- `StagedOpLifecycleError.__bases__ == (Exception,)` — direct subclass
- `'StagedOpRepo' not in forge_bridge.__all__` — D-09 holds
- `src.count('elif t == "staged_operation":') == 2` — both branches present
- `EntityRepo._attrs_to_dict` round-trips a `StagedOperation` to correct 8-key dict

## Deviations from Plan

None — plan executed exactly as written.

The plan's verification script had a minor namespace issue (used `StagedOpRepo` before binding it from the aliased import) — corrected during execution without behavioral change. The file content matches the plan specification exactly.

## Known Stubs

None. All typed fields are wired and round-trip correctly. No placeholder values.

## Threat Flags

None. No new network endpoints, auth paths, file access patterns, or schema changes beyond those described in the plan's `<threat_model>`.
