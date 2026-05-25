# forge-bridge — Continuity-Authority Topology

This file maps which `.planning/` surfaces carry what kind of authority.
It exists because the project's continuity model evolved — during the
25.x -> N -> N+ arc the methodology migrated from a single state cursor
to a distributed set of artifacts, and that migration happened before
it was named. This file names it.

This file is **descriptive, not operational**. It explains the topology;
it is not itself "the cursor." There is no single cursor — that is the
finding (see Q1 below).

## Diagnostic axis (permanent doctrine)

Any future audit of `.planning/` artifacts measures one thing:

**alignment between a document's claimed authority role and its actual operational behavior**

— not recency. Consequences:

- A frozen document that claims archival identity is healthy.
  Intentional temporality is governance maturity, not decay.
- A document that claims a living/cadenced role but behaviorally froze
  is a governance discrepancy — that is the defect to surface.
- Do not incentivize churn on documents whose purpose is to remain
  historically fixed. Freshness is not the metric; role/behavior
  alignment is.

## The continuity model (Q1 finding)

forge-bridge does not have a single live cold-resume cursor. Continuity
is a **distributed substrate**: it emerges collectively from milestone
framing/close docs, §11 deferral registers, evidence artifacts, seeds,
the cycle journal, and git history. A contributor resuming cold reads
the most recent milestone close doc plus this map — not one state file.

## Top-level `.planning/` document roles

| Document | Role | Notes |
|---|---|---|
| `CONTINUITY-MAP.md` | living-cadenced doc | this file; updated when the topology changes (docs added, roles shift) — not on a calendar |
| `JOURNAL.md` | cycle log | per-cycle close-out record; self-declares non-cursor |
| `STATE.md` | frozen-with-topology-pointer | froze at Phase 24.4; carried the single-cursor model; header points here |
| `RETROSPECTIVE.md` | archival archaeology | claimed living per-milestone cadence; froze at v1.4.x close; function migrated to milestone close docs |
| `PROJECT.md` | archival archaeology | "What This Is" broadly current; dated sections froze at v1.5-open |
| `MILESTONES.md` | milestone-local authority | ledger frozen at v1.4.x close; correct for its era |
| `ROADMAP.md` | milestone-local authority | roadmap snapshot frozen at v1.5-open; correct for its era |
| `REQUIREMENTS.md` | milestone-local authority | self-scoped to milestone v1.5; correct for its era |
| `COLD-START-INVESTIGATION.md` | archival archaeology | dated investigation; archaeology by construction |
| `PROTOCOL-VS-SUBSTRATE-INVESTIGATION.md` | archival archaeology | dated investigation; archaeology by construction |
| `THREE-DOMAIN-DECOMPOSITION.md` | archival archaeology | dated decomposition; archaeology by construction |

Role vocabulary: *live operational cursor* (none currently) /
*distributed continuity substrate* (the model itself) /
*live reference surface* / *milestone-local authority* /
*living-cadenced doc* / *archival archaeology* /
*frozen-with-topology-pointer* / *cycle log*.

"Milestone-local authority" and "archival archaeology" are both
correctly-frozen states — they are not defects. Only `STATE.md`,
`RETROSPECTIVE.md`, and `PROJECT.md` carried a claimed-living role their
behavior outgrew; each now carries a freeze header naming that.

## Subdirectory collective roles

- `milestones/` —
  distributed constitutional continuity + evidence substrate;
  phase-localized historical authority.
  The primary cold-resume surface is the most recent `*-CLOSE.md` here.
- `seeds/` — forward-pressure / deferred-intent substrate.
- `phases/` — active-phase working / coordination substrate.

These are not classified per-file; each functions coherently as a
collective.

## Cadence of this file

Updated when the continuity topology changes — a planning doc added or
removed, or a role reclassified. Not updated on a calendar. This is a
living-cadenced doc with an honest, event-driven trigger.

## Provenance

Produced by the continuity-authority topology motion, 2026-05-25, under
the writer's-room three-step cadence. The motion was itself an instance
of substrate-coherence-revealed-in-retrospect at governance grain: the
distributed model already existed; this cycle named it.

