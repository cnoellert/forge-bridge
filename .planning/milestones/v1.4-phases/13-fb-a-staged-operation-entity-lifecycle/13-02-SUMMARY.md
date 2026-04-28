---
phase: 13-fb-a-staged-operation-entity-lifecycle
plan: "02"
subsystem: core-entities
tags: [staged-operation, entity, vocabulary, fb-a, zero-divergence]
dependency_graph:
  requires:
    - forge_bridge/core/entities.py (BridgeEntity base class)
    - forge_bridge/core/traits.py (Locatable, Relational trait mix-in)
  provides:
    - forge_bridge/core/staged.py (StagedOperation class — FB-B contract anchor)
    - forge_bridge/core/__init__.py (barrel re-export, entity count 9→10)
  affects:
    - forge_bridge/store/staged_operations.py (Plan 03 — imports StagedOperation)
    - tests/test_staged_operations.py (Plan 04 — asserts on StagedOperation shape)
    - Any FB-B (Phase 14) MCP/HTTP consumer that calls to_dict()
tech_stack:
  added: []
  patterns:
    - BridgeEntity single-inheritance (Locatable + Relational via base)
    - entity_type property override (literal string, not __name__.lower())
    - to_dict() extends super().to_dict() via d.update({...})
    - Raw string status (not Status enum — Pre-Planning Finding #6)
key_files:
  created:
    - forge_bridge/core/staged.py
  modified:
    - forge_bridge/core/__init__.py
decisions:
  - "StagedOperation lives in its own forge_bridge/core/staged.py module (not entities.py) — entities.py is 22 KB and focused on original-vocabulary entities; separate module gives FB-B a clean import line"
  - "entity_type overridden to literal 'staged_operation' — BridgeEntity.__name__.lower() would yield 'stagedoperation', silently breaking EntityRepo.save discriminator write at repo.py:254"
  - "status is raw str (default 'proposed'), NOT the Status enum — enum values (PENDING/IN_PROGRESS/REVIEW/APPROVED/PUBLISHED/REJECTED) do not match the staged_op lifecycle per Pre-Planning Finding #6"
  - "Versionable trait excluded per D-18 — operations are not versioned; Locatable + Relational kept via BridgeEntity inheritance for forward-compatibility"
metrics:
  duration: "92s"
  completed: "2026-04-26"
  tasks_completed: 2
  files_created: 1
  files_modified: 1
---

# Phase 13 Plan 02: StagedOperation Application Class Summary

**One-liner:** New `StagedOperation(BridgeEntity)` class with `entity_type='staged_operation'` override, nine typed fields per D-02, and 16-key `to_dict()` as the FB-B zero-divergence anchor; re-exported from `forge_bridge.core` barrel (entity count 9→10).

## What Was Built

### Task 1: forge_bridge/core/staged.py

New module defining the `StagedOperation` application class — the single source of truth for the JSON shape that FB-B's MCP tools and HTTP routes return verbatim (STAGED-06 zero-divergence anchor).

**Class structure:**
- Inherits from `BridgeEntity` only (no `Versionable` per D-18)
- Transitively inherits `Locatable` and `Relational` through `BridgeEntity`
- 114 lines including load-bearing comments

**Entity class count in `forge_bridge.core.__all__`:** was 9, now 10 (`BridgeEntity, Project, Sequence, Shot, Asset, Version, Media, Stack, Layer, StagedOperation`).

### Task 2: forge_bridge/core/__init__.py

Three additive edits:
1. New import line: `from forge_bridge.core.staged import StagedOperation`
2. Docstring example block updated to mention `StagedOperation`
3. `__all__` entities cluster: `"Layer", "StagedOperation"` (appended)

## Critical: entity_type Override

The `entity_type` property is overridden with a load-bearing comment block:

```python
# ── CRITICAL: override entity_type ─────────────────────────────────────
# BridgeEntity returns cls.__name__.lower() == "stagedoperation",
# which does NOT match the discriminator string "staged_operation"
# used everywhere else (ENTITY_TYPES frozenset, ck_entities_type CHECK,
# EntityRepo.save at repo.py:254). Without this override the save
# path silently writes the wrong discriminator.
# See PATTERNS.md Critical Pre-Planning Finding #3.
@property
def entity_type(self) -> str:
    return "staged_operation"
```

This is verifiable by Python introspection: `op.entity_type == 'staged_operation'` for any constructed instance.

## Versionable Exclusion (D-18)

`StagedOperation` does NOT inherit `Versionable`. Verified:
- `grep -q "Versionable" forge_bridge/core/staged.py` → exits 1 (not present)
- `isinstance(op, Versionable)` → `False`

The `Locatable` and `Relational` traits are present via `BridgeEntity` but unexercised in v1.4 (forward-compatibility only, per D-18).

## to_dict() Shape — The FB-B Contract (16 keys)

This is the exact shape `to_dict()` returns — FB-B (Phase 14) planners can lift it verbatim into STAGED-06 zero-divergence test assertions:

```python
{
    # From super().to_dict() (BridgeEntity base — 6 keys):
    "id":            str(self.id),                     # UUID string
    "entity_type":   "staged_operation",               # literal — overridden
    "created_at":    self.created_at.isoformat(),      # ISO 8601 string
    "metadata":      {},                               # open key/value bag
    "locations":     [],                               # Locatable.get_location_dicts()
    "relationships": [],                               # Relational.get_relationship_dicts()

    # Added by StagedOperation.to_dict() (9 keys):
    "operation":     self.operation,                   # str — e.g. "flame.publish_sequence"
    "proposer":      self.proposer,                    # str — free-string actor (D-11)
    "parameters":    self.parameters,                  # dict — immutable after creation (D-22)
    "result":        self.result,                      # None until executed/failed
    "status":        self.status,                      # raw str — NOT enum.value
    "approver":      self.approver,                    # None until approved
    "executor":      self.executor,                    # None until executed/failed
    "approved_at":   ...,                              # ISO string or None
    "executed_at":   ...,                              # ISO string or None
}
```

**Key invariants:**
- `status` is a raw string, NOT `status_enum.value` — the `Status` enum is not used
- `approved_at` / `executed_at` use `.isoformat()` if set, else `None` (not `""`)
- `result` is `None` at construction; populated by `StagedOpRepo` on `executed` or `failed` transition
- `parameters` is stored as-is (dict reference); immutability is enforced at the repo layer (Plan 03), not here

## Deviations from Plan

None — plan executed exactly as written. All three `forge_bridge/core/__init__.py` edits were made in the prescribed order and form. The `staged.py` module structure matches the plan's mandatory structural elements verbatim.

## Known Stubs

None. `StagedOperation` has no stub values — all fields are typed, all serialization is complete. The class intentionally accepts any `parameters` dict (no validation — deferred to FB-B per D-12).

## Threat Flags

None. The two threats in scope for this plan (T-13-05 and T-13-06) were reviewed:
- T-13-05 (`status="executed"` direct construction) — accepted per plan; docstring `IMPORTANT` paragraph warns against direct construction
- T-13-06 (`to_dict()` field exposure) — accepted; all 16 fields are intentionally public per D-02

## Self-Check: PASSED

- `forge_bridge/core/staged.py` exists: CONFIRMED
- `grep -q "class StagedOperation" forge_bridge/core/staged.py`: CONFIRMED
- `grep -q 'return "staged_operation"' forge_bridge/core/staged.py`: CONFIRMED
- `from forge_bridge.core.staged import StagedOperation` imports cleanly: CONFIRMED
- `from forge_bridge.core import StagedOperation` imports cleanly: CONFIRMED
- `'StagedOperation' in forge_bridge.core.__all__`: CONFIRMED
- `isinstance(op, Versionable)` is False: CONFIRMED
- `set(op.to_dict().keys()) == expected_16_keys`: CONFIRMED
- Task 1 commit `fbb1172` exists: CONFIRMED
- Task 2 commit `171c4a2` exists: CONFIRMED
