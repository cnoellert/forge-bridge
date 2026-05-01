---
phase: 20-reality-audit-canonical-install
plan: 05
subsystem: install / docs / UAT
tags: [install, docs, uat, postgres, systemd, daemon, reality-audit]

requires:
  - phase: 20-04
    provides: docs/INSTALL.md as the artifact being walked
  - phase: 20-07
    provides: multi-host topology framing the walker validated against
provides:
  - 20-HUMAN-UAT.md populated with PASS-with-deviations outcome and 13 gap-log entries
  - 20-PHASE-20.1-CANDIDATE.md as the requirements-input doc for the v1.5 ship-blocker follow-up phase
  - SEED-PHASE-20-NON-AUTHOR-UAT-V1.6+.md to track the deferred fresh non-author UAT
affects: [20-06, 20.1, v1.5-milestone-close, project.md, roadmap.md]

tech-stack:
  added: []
  patterns:
    - "Author-walked UAT-with-deviation pattern (D-02.1 amendment) — used when non-author unavailable"
    - "Discipline contract for author walks — verbatim copy-paste, verbatim observation transcription, no silent route-around, explicit logging of author-context dependence"
    - "In-flight D-04 doc-only patch landing mid-walk (e.g., db56f87 Step 3 superuser path expansion)"

key-files:
  created:
    - .planning/phases/20-reality-audit-canonical-install/20-HUMAN-UAT.md
    - .planning/phases/20-reality-audit-canonical-install/20-PHASE-20.1-CANDIDATE.md
    - .planning/seeds/SEED-PHASE-20-NON-AUTHOR-UAT-V1.6+.md
    - .planning/phases/20-reality-audit-canonical-install/20-05-SUMMARY.md
  modified:
    - .planning/phases/20-reality-audit-canonical-install/20-CONTEXT.md (D-02.1 amendment for author-walk-with-deviation)
    - docs/INSTALL.md (Step 3 inline patch — db56f87)

key-decisions:
  - "Walker = cnoellert (project orchestrator + author of planning artifacts; non-author of the install procedure itself, per D-02.1 amendment). Outcome capped at PASS-with-deviations; clean PASS not available."
  - "Track A walked from flame-01 (Rocky 9.5 operator workstation) → assist-01 (LLM service host @ 192.168.86.15). Cross-host LLM topology validated via curl chat round-trip."
  - "13 gaps surfaced; 12 are install/doc gaps (Phase 20.1 input); 1 (#13 — UI chat hang) is pre-existing v1.4.x debt and not a Phase 20 obligation."
  - "Most consequential finding: gap #11 — INSTALL.md Step 6 line 234 lies about 'all four surfaces in one shot.' Reality is two processes (forge_bridge.server on :9998, then forge_bridge on :9996/MCP) with required start order. The doc misrepresents the architecture."
  - "Phase 20.1 is a v1.5 ship blocker, not optional polish. forge-bridge is not shippable to its target user (Flame artist) until 20.1 lands. The architecture works; the install procedure does not."
  - "Plan 20-06 (Track B) is subsumed by Phase 20.1's acceptance criteria — running it against the current INSTALL.md would re-discover the same 13 gaps. Deferred to 20.1."

patterns-established:
  - "Reality-audit UAT outcome: when the audit catches structural truth (procedure-as-prose can't survive contact with reality), spin a successor phase rather than patching prose forever."
  - "Headline framing in artifacts: when a finding is consequential (e.g., 'no artist could complete this install'), elevate it to a redundant headline at the top of every relevant document — UAT, candidate plan, future ROADMAP — so it cannot be lost on skim."

requirements-completed: [INSTALL-01, INSTALL-02, INSTALL-03, INSTALL-04, DOCS-02]

duration: ~90min (UAT walk + triage)
completed: 2026-05-01
---

# Phase 20 — Plan 05: Track A Non-Author UAT Summary

**The reality audit caught structural truth: docs/INSTALL.md is not shippable to artists. Architecture works; install procedure does not. Phase 20.1 (install.sh + systemd daemon) is the v1.5 ship blocker.**

## Performance

- **Duration:** ~90 minutes (UAT walk on flame-01 + SSH triage of 9998 / lifecycle / topology gaps)
- **Started:** 2026-05-01T13:00:00-07:00
- **Completed:** 2026-05-01T14:30:00-07:00
- **Tasks:** 2/2 (Task 1 — scaffold author-prepared; Task 2 — walker completed UAT, signed off PASS-with-deviations)
- **Files modified:** 4 (UAT, CONTEXT amendment, seed, candidate plan)

## Accomplishments

- Track A walk completed end-to-end on flame-01 (Rocky 9.5 operator workstation) with assist-01 (192.168.86.15) as the remote LLM service host. All 5 surfaces validated reachable: Flame hook on :9999 (`flame_available: true`), MCP CLI (`forge-bridge --help`), Web UI on :9996/ui/ (HTTP 302 → 200), HTTP /api/v1/chat (cross-host curl returned `"ok"` end-to-end), browser visual (5 SPA tabs render).
- 13 gaps surfaced and disposition-tagged in the UAT gap log. 11 are doc-only or scriptable (Phase 20.1 deliverables). 1 is pre-existing v1.4.x debt (UI chat hang). 1 was patched inline mid-walk per D-04 (`db56f87` Step 3 superuser path expansion).
- D-02.1 amendment landed in CONTEXT.md to document the author-walked-with-deviation acceptance pattern (used when non-author unavailable; explicitly capped at PASS-with-deviations).
- Phase 20.1 candidate plan written and committed at `0993f01`. Spine: two systemd units + bootstrap script + `/etc/forge-bridge/forge-bridge.env`. Primary acceptance criterion: a Flame artist with no Linux/Postgres knowledge can complete the install. Validation gate: 20.1's UAT MUST be walked by an actual non-author (a Flame artist), not the project author.
- Future fresh non-author UAT seeded as `.planning/seeds/SEED-PHASE-20-NON-AUTHOR-UAT-V1.6+.md`.

## Task Commits

1. **Task 1: 20-HUMAN-UAT.md scaffold (133 lines, status `pending`, track A)** — `f7e979f` (docs)
2. **Pre-walk fixture prep on flame-01** — author-driven, no commit (conda env removed, repo cloned at HEAD, assist-01 reachability confirmed)
3. **Task 2: walker completed UAT walk** — `fac197c` (test) — populated all sections (reference versions, fixture state, Step 1–8 walk-through, surface table, doctor output, 13-row gap log, 4 deviations, outcome, sign-off)
4. **D-04 inline doc patch — Step 3 superuser path** — `db56f87` (docs)
5. **Headline elevation — "no artist could stomach this" framing** — `0993f01` (docs)
6. **D-02.1 CONTEXT amendment + seed for future non-author UAT** — `2b8bd15` (docs)
7. **Phase 20.1 candidate captured + updated** — `43c98e8`, `0993f01` (docs)

## Files Created/Modified

- `.planning/phases/20-reality-audit-canonical-install/20-HUMAN-UAT.md` — populated UAT record (PASS-with-deviations, 13 gaps, all 5 surfaces validated)
- `.planning/phases/20-reality-audit-canonical-install/20-PHASE-20.1-CANDIDATE.md` — input requirements doc for the v1.5 ship-blocker follow-up phase
- `.planning/phases/20-reality-audit-canonical-install/20-CONTEXT.md` — D-02.1 amendment recording the author-walked-with-deviation acceptance
- `.planning/seeds/SEED-PHASE-20-NON-AUTHOR-UAT-V1.6+.md` — future fresh non-author UAT
- `docs/INSTALL.md` — Step 3 inline patch (3a confirm/install, 3b create user/db with concrete superuser path, 3c alembic) for gap #1

## Outcome

**Track A: PASS-with-deviations.** The UAT achieved its purpose — surfacing comprehension and procedural gaps that Phase 20.1 must close. The install procedure is broken for non-authors. The architecture is not.

## What this unblocks

- Plan 20-06 (Track B) deferral: per the UAT Action section, Track B is subsumed by Phase 20.1's acceptance criteria — see `20-06-SUMMARY.md` (deferral record).
- Phase 20 close: with 20-05 + 20-06 SUMMARYs landing, Phase 20 can mark complete with the partial-gate annotation. Then Phase 20.1 opens immediately.

## What this blocks

- v1.5 milestone ship — until Phase 20.1 lands, forge-bridge is not shippable to its target user.

## Cross-references

- `.planning/phases/20-reality-audit-canonical-install/20-HUMAN-UAT.md` — full walk record + 13-gap inventory
- `.planning/phases/20-reality-audit-canonical-install/20-PHASE-20.1-CANDIDATE.md` — what 20.1 will deliver
- `.planning/phases/20-reality-audit-canonical-install/20-CONTEXT.md` D-02.1 — author-walk amendment
- `.planning/seeds/SEED-PHASE-20-NON-AUTHOR-UAT-V1.6+.md` — future non-author UAT trigger
