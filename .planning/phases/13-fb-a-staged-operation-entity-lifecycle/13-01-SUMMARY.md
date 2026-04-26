---
phase: 13-fb-a-staged-operation-entity-lifecycle
plan: "01"
subsystem: store
tags: [schema-constants, alembic, staged-operation, entity-types, event-types]
dependency_graph:
  requires: []
  provides:
    - forge_bridge.store.models.ENTITY_TYPES includes staged_operation
    - forge_bridge.store.models.EVENT_TYPES includes staged.proposed/approved/rejected/executed/failed
    - ck_entities_type CHECK constraint auto-generates from sorted(ENTITY_TYPES) for fresh DBs
    - Alembic revision 0003 retrofits ck_entities_type on existing databases
  affects:
    - forge_bridge.store.models.DBEntity.__table_args__ (ck_entities_type auto-regenerated)
    - All downstream plans in Phase 13 (FB-A) that INSERT staged_operation rows
tech_stack:
  added: []
  patterns:
    - ENTITY_TYPES frozenset drives ck_entities_type CHECK via f-string at class definition time
    - EVENT_TYPES frozenset is Python-only — no DB CHECK constraint on events.event_type
    - Alembic drop + recreate CHECK idiom (established in 0002, extended here)
key_files:
  created:
    - forge_bridge/store/migrations/versions/0003_staged_operation.py
  modified:
    - forge_bridge/store/models.py
decisions:
  - ENTITY_TYPES uses double-quoted string literals per existing codebase style
  - No CHECK constraint added for event_type — verified absent in 0001_initial_schema.py and DBEvent.__table_args__ (only Index entries)
  - import uuid omitted from 0003 migration (no row seeding, unlike 0002)
  - staged_operation slots alphabetically between stack and version in the CHECK literal
metrics:
  duration: ~10 minutes
  completed: "2026-04-26T03:14:00Z"
  tasks_completed: 2
  files_modified: 1
  files_created: 1
---

# Phase 13 Plan 01: Extend Schema Constants for staged_operation Summary

Additive frozenset extensions and matching Alembic migration wire `staged_operation` entity type and five `staged.*` lifecycle event types into the data layer, enabling all downstream Phase 13 (FB-A) plans to insert rows without hitting the `ck_entities_type` CHECK boundary.

## What Was Built

### Task 1 — Extend ENTITY_TYPES and EVENT_TYPES (commit b674924)

Two additive edits to `forge_bridge/store/models.py`:

**ENTITY_TYPES** — grew from 7 to 8 types:
- Added: `"staged_operation"` (alphabetic position: between `stack` and `version`)
- Final sorted order: `asset`, `layer`, `media`, `sequence`, `shot`, `stack`, `staged_operation`, `version`
- The `ck_entities_type` CHECK constraint in `DBEntity.__table_args__` auto-regenerates from `sorted(ENTITY_TYPES)` at module import — no manual edit to the constraint expression was needed or made.

**EVENT_TYPES** — grew from 27 to 32 event types:
- Added: `staged.proposed`, `staged.approved`, `staged.rejected`, `staged.executed`, `staged.failed`
- Grouped under a new `# Staged operations (FB-A — proposer/approver/executor lifecycle)` comment block at the end of the frozenset, following the established comment-grouping convention.
- No DB CHECK constraint exists on `events.event_type` — this was verified against `0001_initial_schema.py:141-156` (events table CREATE with no CheckConstraint) and `DBEvent.__table_args__` (lines 499-503, Index entries only). EVENT_TYPES remains Python-side validation only.

### Task 2 — 0003_staged_operation Alembic migration (commit aafe01b)

New file `forge_bridge/store/migrations/versions/0003_staged_operation.py`:

- `revision = "0003"`, `down_revision = "0002"` — wired into the existing chain
- **upgrade()**: drops `ck_entities_type`, recreates it with 8 types in alphabetical order including `staged_operation` between `stack` and `version`
- **downgrade()**: drops `ck_entities_type`, restores original 7-type literal verbatim from `0001_initial_schema.py:86`
- No `import uuid` (no row seeding; D-16 — `staged_operation` is greenfield)
- No events table modifications (confirmed `event_type` has no CHECK constraint)
- Follows the exact "drop + recreate CHECK" idiom from `0002`'s `ck_locations_storage_type` section (lines 96-103 / 193-199)

## Confirmed Deferrals

**Critical Pre-Planning Finding #1 — No event_type CHECK constraint:**
No `CHECK` constraint exists on `events.event_type`. Verified against:
- `0001_initial_schema.py:141-156`: events table CREATE statement has no `sa.CheckConstraint`
- `DBEvent.__table_args__`: only three `Index` entries (`ix_events_type_time`, `ix_events_project_time`, `ix_events_entity_time`)

This means EVENT_TYPES additions are Python-only — the migration touches `ck_entities_type` ONLY. Adding a DB CHECK for event_type was explicitly out of scope and was not done.

## Counts

| Frozenset | Before | After | Delta |
|-----------|--------|-------|-------|
| ENTITY_TYPES | 7 | 8 | +1 (staged_operation) |
| EVENT_TYPES | 27 | 32 | +5 (staged.proposed/approved/rejected/executed/failed) |

Note: The plan's output spec stated "was 28, now 33" — the actual counts were 27 and 32. The plan's frozenset listing in the interfaces section contained 27 event types; this is a documentation discrepancy in the plan, not a missing event type. All five `staged.*` types were added as specified.

## Migration Revision Summary

| Field | Value |
|-------|-------|
| revision | 0003 |
| down_revision | 0002 |
| upgrade | drops + recreates ck_entities_type with 8 types |
| downgrade | restores 7-type CHECK from 0001 verbatim |
| row backfill | none (D-16) |
| events table | untouched |
| reversibility | exactly reversible — downgrade literal taken from 0001_initial_schema.py:86 |

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | b674924 | feat(13-01): extend ENTITY_TYPES and EVENT_TYPES for staged_operation |
| Task 2 | aafe01b | feat(13-01): add 0003_staged_operation Alembic migration |

## Deviations from Plan

None — plan executed exactly as written. The only note is a count discrepancy (27/32 vs plan's 28/33) which is a documentation artifact in the plan's output spec, not a missing implementation item.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or trust-boundary schema changes introduced. The migration widens the `ck_entities_type` vocabulary (T-13-01 per plan's threat register — mitigated by reversible downgrade). No new threat surface beyond what was anticipated in the plan's STRIDE register.

## Self-Check: PASSED

- forge_bridge/store/models.py: FOUND (modified)
- forge_bridge/store/migrations/versions/0003_staged_operation.py: FOUND (created)
- commit b674924: FOUND
- commit aafe01b: FOUND
