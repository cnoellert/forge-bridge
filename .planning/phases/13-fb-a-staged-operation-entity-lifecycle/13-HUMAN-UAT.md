---
status: partial
phase: 13-fb-a-staged-operation-entity-lifecycle
source: [13-VERIFICATION.md]
started: 2026-04-25T00:00:00Z
updated: 2026-04-25T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. End-to-end DB integration — all four STAGED success criteria

expected: On a machine with Postgres at `localhost:5432` (or with `FORGE_DB_URL` pointing at a reachable Postgres instance), run `pytest tests/test_staged_operations.py -v` from the project root and confirm: **34 passed, 0 skipped, 0 failed**. All five test functions execute against a live Postgres backend:
- `test_staged_op_round_trip` — STAGED-01 round-trip persistence
- `test_transition_legality[*]` — STAGED-02 state machine (30 parametrized cases: 5 legal pass, 25 illegal raise `StagedOpLifecycleError`)
- `test_audit_replay` — STAGED-03 audit trail (3 lifecycle paths, D-07 payload shapes, `client_name` duplication)
- `test_sql_only_parameter_diff` — STAGED-04 JSONB-arrow SQL diff (`parameters` bit-identical across proposed/approved/executed; `result` null until terminal)
- `test_transition_atomicity` — atomicity invariant

result: [pending]

## Summary

total: 1
passed: 0
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps
