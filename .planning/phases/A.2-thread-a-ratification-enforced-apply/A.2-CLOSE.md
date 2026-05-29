---
milestone: v1.7
thread: A
phase: A.2
phase_name: Ratification + enforced apply
status: closed
opened: 2026-05-28
closed: 2026-05-28
type: phase-close
derives_from: .planning/phases/A.2-thread-a-ratification-enforced-apply/A.2-PLAN.md
implementation_arc: 03f8b25..aefeba2 (10 commits, D1..D9 substrate + CLI + end-to-end test)
---

# A.2 — Phase close cursor

> **Chat preview now has an assent-backed apply path.**
> A mutating graph-intent is stored as an `AssentRecord`, ratified by an
> operator, and applied by replaying the exact persisted chain. The commit
> primitive now checks both drift and assent state at the authority boundary.

## What shipped

```
03f8b25  feat(A.2): add AssentRecord core substrate primitive
1d7ee9a  feat(A.2): add AssentRecordRepo content-addressed substrate
dbbec46  feat(A.2): add assent_record entity-type migration
eb25445  feat(A.2): extend commit verification with assent state
89574de  feat(A.2): propagate assent through chain execution
5b2592e  feat(A.2): persist graph-intent preview assent records
70ad9c1  feat(A.2): wire chat apply and ratify endpoint
ce3d417  feat(A.2): add fbridge ratify CLI surface
aefeba2  test(A.2): cover ratify apply happy path end-to-end
```

Concrete deliverables:

- `AssentRecord` core entity, not exported from `forge_bridge.__all__`.
- `AssentRecordRepo` with content-addressed propose, ratify, applied, and
  failed transitions.
- Alembic migration `0009_assent_record.py`, extending `ck_entities_type` from
  20 to 21 values.
- `CommitNode.verify(..., assent=...)` with `ASSENT_INVALID` error support.
- Chain execution propagation so only commit steps receive assent state.
- Preview persistence: mutating chat previews now carry `graph_intent_id`.
- Store-and-replay apply path shared by chat `apply <graph_intent_id>` and
  `POST /api/v1/ratify`.
- Top-level `fbridge ratify <graph_intent_id>` CLI.
- End-to-end test for preview -> ratify -> apply against the real test DB.

## Verification

- A.2 D9 bundle: 42 passed.
- CLI neighbor sweep: 35 passed.
- Focused D1-D8 tests passed at each commit.
- `forge_bridge.__all__` remained 19.
- `git diff --check` clean before D9 and D10 work.

Live Flame-facing smokes from the plan remain operator-UAT items because they
require a real running daemon and host mutation target.

## Defects Caught

- D5 initially failed to pass `assent_record` into the commit-step call site.
  The new step-level assent tests caught the missing adoption point before
  commit.
- D7's first endpoint tests used sync `TestClient` with asyncpg-backed
  sessions, producing cross-event-loop failures. The tests moved to
  `httpx.AsyncClient` + `ASGITransport`, matching the async runtime shape.

## Carried Forward

- Authentication is still deferred; `actor` is a free string pending the auth
  seed.
- Chat conversational ratification remains out of scope. A.2 ships CLI
  ratify and narrow chat apply.
- Drift-invalidation live smoke remains a UAT item.
- A.3 hardening opens after this close cursor.
