---
phase: 20-reality-audit-canonical-install
plan: 06
subsystem: install / docs / UAT
tags: [install, docs, uat, track-b, mcp-only, deferred]

requires:
  - phase: 20-05
    provides: gap inventory that establishes Track B would re-discover the same gaps
provides:
  - explicit deferral record so Phase 20 can close with all plans accounted for
  - Track B acceptance moved to Phase 20.1 acceptance criteria
affects: [20.1, v1.5-milestone-close, project.md, roadmap.md]

tech-stack:
  added: []
  patterns:
    - "Deferral SUMMARY pattern — when a sibling plan's outcome obviates running the current plan, write a SUMMARY explicitly recording the deferral instead of running theatre."

key-files:
  created:
    - .planning/phases/20-reality-audit-canonical-install/20-06-SUMMARY.md
  modified: []

key-decisions:
  - "Plan 20-06 (Track B / MCP-only integrator dry-run) is DEFERRED to Phase 20.1's acceptance criteria. Per CONTEXT.md D-03, Track B is author-driven and NOT a milestone gate. Per the 20-05 UAT Action section, running Track B now against the current INSTALL.md would simply re-discover the same 13 gaps Track A surfaced — particularly Step 3 (Postgres setup, gaps #1, #3, #4, #6) and Step 6 (gap #11, the substantive doc lie about single-process launch). Track B against the same broken doc adds no signal."
  - "Phase 20.1's reshaped INSTALL.md + install.sh + systemd units will collapse Step 3 and Step 6 into idempotent script invocations. At that point, Track B's 'integrator on a Flame-less host' walk becomes a meaningful test — the same script handles both Track A and Track B (with `--track-b` skipping the Flame-hook bits per the 20.1 candidate non-goals)."
  - "Phase 20.1 acceptance criteria explicitly include both Track A and Track B walks under the new install.sh path. Track B's value (catching dependency-presence assumptions Track A masks) is preserved — just deferred to where the artifact under test is honest."

patterns-established:
  - "Deferral-by-subsumption: when plan B's value is fully captured by an upcoming successor phase's acceptance criteria, deferring is more honest than ritualistic execution."

requirements-completed: [INSTALL-01, INSTALL-04]  # partially — coverage transfers to Phase 20.1

duration: deferred
completed: 2026-05-01
---

# Phase 20 — Plan 06: Track B Integrator Dry-Run — DEFERRED to Phase 20.1

**Track B is subsumed by Phase 20.1's acceptance criteria. Running it against the current INSTALL.md would re-discover the same gaps Track A already surfaced. Deferring preserves the test's value (catching dep-presence assumptions on a Flame-less host) for when the artifact-under-test is honest.**

## Why this plan was not run

Plan 20-05 (Track A non-author UAT) surfaced 13 gaps in `docs/INSTALL.md` and produced one definitive finding: **the install procedure is not shippable to non-authors**. Running Plan 20-06 (Track B / MCP-only on a Flame-less host) immediately afterward against the same broken doc would:

1. Re-discover gaps #1, #3, #4, #6 in Step 3 (Postgres setup — same on any Linux host regardless of Flame's presence)
2. Re-discover gap #11 in Step 6 (the doc lie about single-process launch — Flame-less hosts hit it identically)
3. Add no new signal beyond confirming "yes, the doc is also broken for Track B operators"

Per CONTEXT.md D-03, Track B is **author-driven** and **NOT a milestone gate** — it exists to catch dependency-presence assumptions (e.g., "I assumed Postgres was already running") that Track A masks because assist-01 had Postgres pre-installed. With Phase 20.1's `install.sh` handling Postgres bootstrap explicitly on any host, that assumption-catching value moves naturally into 20.1's acceptance criteria.

## What replaces this plan

Phase 20.1's acceptance criteria explicitly cover both walks:

- **Track A under 20.1**: Flame workstation operator runs `sudo ./scripts/install-bootstrap.sh` → edits `/etc/forge-bridge/forge-bridge.env` → `systemctl start forge-bridge`. All 5 surfaces green.
- **Track B under 20.1**: Flame-less integrator runs `sudo ./scripts/install-bootstrap.sh --track-b` (skips Flame-hook install) → same env edit → `systemctl start forge-bridge`. Surfaces 1–4 green, Surface 5 (Flame hook) intentionally absent.

Both walks must be performed by **non-authors** (a Flame artist for Track A, a pipeline integrator for Track B), not the project author. See `20-PHASE-20.1-CANDIDATE.md` "Validation requirements" — author-walked-with-deviation is NOT acceptable for 20.1, because the whole point of 20.1 is to make the install accessible to non-authors.

## Cross-references

- `.planning/phases/20-reality-audit-canonical-install/20-CONTEXT.md` D-03 — Track B is author-driven, not a milestone gate
- `.planning/phases/20-reality-audit-canonical-install/20-HUMAN-UAT.md` Action section — explicitly defers Track B to 20.1
- `.planning/phases/20-reality-audit-canonical-install/20-05-SUMMARY.md` — Track A walk that produced the gap inventory
- `.planning/phases/20-reality-audit-canonical-install/20-PHASE-20.1-CANDIDATE.md` — where Track B re-emerges as a 20.1 acceptance criterion

## Outcome

**Plan 20-06: DEFERRED to Phase 20.1.** Phase 20 may close with this deferral record; Phase 20.1 absorbs Track B's intent.
