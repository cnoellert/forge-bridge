---
seed: SEED-PHASE-21-NON-AUTHOR-UAT
status: pending
created: 2026-05-13
trigger: "When a fresh non-author reader becomes available — anyone who has NOT previously read forge-bridge documentation and did not participate in Phase 21 docs authoring."
target_milestone: v1.6+ (or sooner if a non-author becomes available)
---

# Re-read README.md + docs/GETTING-STARTED.md as a true non-author UAT

## Context

Phase 21 (v1.5 Legibility milestone) shipped two reader-facing docs that establish forge-bridge's identity for a non-author audience:

- `README.md` lede rewrite (DOCS-01) — the "What is forge-bridge?" framing + "Relationship to projekt-forge" subsection. Establishes the project as middleware (not a Flame utility) and names the consumer-pattern relationship with projekt-forge.
- `docs/GETTING-STARTED.md` (DOCS-03) — the surface-map concept doc covering the five user-facing surfaces (Artist Console, CLI, MCP server, chat endpoint, Flame hook) plus the canonical-vocabulary substrate they share.

The Phase 21 success criteria called for non-author validation: a reader who did not author the docs should be able to read them and (1) understand what forge-bridge is, (2) identify the five surfaces and how they fit together, (3) locate the projekt-forge relationship — all without reading source code.

At Phase 21 close, no non-author was available. The author (cnoellert) performed a cold-read UAT under writer's-room discipline: linear top-to-bottom read of both docs, friction-point capture, "explain to a Flame artist" sanity check at the end. One concrete friction point surfaced and was fixed surgically. The remainder of the cold read passed.

This seed exists so the formal non-author UAT eventually happens, and so the v1.5-milestone-shipped-without-real-non-author-reader-validation gap is archaeologically recorded rather than implicitly buried.

## Concrete evidence from the author cold-read

One reader-comprehension finding surfaced during the author cold-read:

**Verb/noun conflation of `forge-bridge`** (fixed in `cd51ac1`):

- The new README lede and existing prose used `forge-bridge` as the project-noun (correct).
- But Quick Start smoke-test invocations, the GETTING-STARTED.md CLI example block, and several table rows used `forge-bridge` as the CLI command — the same literal string the user types at the terminal — without distinguishing it from the project name.
- A fresh reader who lacks the author's mental model could not tell from context whether `forge-bridge --help` was a typed command or a reference to the project doing something help-related.
- Fix: canonicalized `fbridge` as the CLI verb (matches the actual binary name registered in `pyproject.toml [project.scripts]`), preserved `forge-bridge` for project-noun usages, added one footnote noting back-compat.

The methodology archaeology — **one finding is concrete evidence but weaker than ideal**. A real non-author reader would likely surface additional friction points; the author's mental model masks comprehension gaps the author cannot see. Two adjacent staleness issues surfaced during the same pass (README row 34 MCP server entry + row 41 CLI status row, both fixed in `f4272f7`), but those were author-archaeology-grade (technical drift the author already knew about) rather than reader-comprehension-grade. A real non-author UAT would specifically test for reader-comprehension friction the author cannot see by definition.

The cold read also surfaced three forthcoming-pointing dead links (`docs/RECIPES.md` referenced before the file exists) — unlinked in `b7297bc` to remove the click-cost while preserving the named-future-surface signal. That was an author-known intentional state rather than a reader-comprehension finding; preserved in the archaeology for completeness.

## Trigger conditions

Surface this seed when ANY of the following becomes true:

- A second operator joins the project who has NOT previously read forge-bridge documentation
- A consulting / contract operator is brought in for any work that requires understanding what forge-bridge is from the docs
- A future phase requires onboarding new team members through the README + GETTING-STARTED.md
- v1.6 milestone planning starts (regardless of whether a non-author is available yet — surface the seed for visibility)
- Phase 22 (Daily Workflow Recipes) opens — RECIPES.md is meant to be consumed AFTER GETTING-STARTED.md, so the recipes phase is a natural moment to validate the docs they build on

## What to do when triggered

1. Hand `README.md` and `docs/GETTING-STARTED.md` to the non-author. Do NOT give them the `.planning/` artifacts — they must have only the docs.
2. Have them perform the same cold-read pattern as the author UAT:
   - Linear read top-to-bottom of README, then GETTING-STARTED.md.
   - Capture three things specifically: (a) places where the doc seems to assume background knowledge the reader lacks, (b) places where the reading cadence broke, (c) places where a next-step pointer was confusing or unhelpful.
   - End with the "Flame artist pitch" test — can they summarize forge-bridge to an imagined Flame artist friend using only what the docs gave them? Where the pitch breaks is where the docs need more.
3. Compare their friction-point log against the one finding in this seed. Any new friction points are comprehension gaps the author walk failed to surface — those are the things to patch.
4. Patch the docs per discovered gaps (likely cosmetic / wording / pointer changes; if any structural rewrites are needed, that's a bigger signal that the milestone gate was meaningfully un-validated).
5. Update PROJECT.md / ROADMAP.md if any v1.5 success-criterion claims need to be revised in light of the formal non-author result.
6. Mark this seed `status: resolved` with a one-line summary of findings.

## Why this isn't urgent

The author cold-read produced one concrete finding and that finding was surgically corrected at the commit-arc level (verb/noun rule applied consistently across both docs). The docs walk cleanly for the author, and the verb/noun fix is a real comprehension improvement that survives the eventual non-author walk.

But the gate isn't fully closed. A real non-author reader is the only valid test of whether docs read cleanly for the audience they were written for — by definition, the author cannot perform that test. This seed keeps the integrity of the Phase 21 success criteria alive without blocking v1.5 ship.

## Cross-references

- `cd51ac1` — verb-usage canonicalization commit (the one finding, fixed)
- `5d155a2` — README lede rewrite + new GETTING-STARTED.md (the artifacts being read)
- `fb01681` — CLAUDE.md DOCS-02 refresh (companion archaeology; same staleness pattern surfaced post-Phase-20-close)
- `f4272f7` — README status table refresh (adjacent staleness fixed during the cold-read pass)
- `b7297bc` — three RECIPES.md unlinks (post-link-check, intentional dead-link removal)
- `.planning/STATE.md` — Phase 21 close cursor + DOCS-02 phase-mapping note
- `.planning/seeds/SEED-PHASE-20-NON-AUTHOR-UAT-V1.6+.md` — companion seed (same forcing-function gap, install procedure not surface-map docs)
- `.planning/phases/20-reality-audit-canonical-install/20-HUMAN-UAT.md` — the pattern that defines what a non-author UAT walk-log looks like in this project (Phase 20 install procedure equivalent)
