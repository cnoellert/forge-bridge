---
milestone: v1.11
phase: SR.1
type: phase-close
status: closed-source-routing-shipped-live-verified
closed: 2026-06-01
honest_scope: "SR.1's source-of-truth routing SHIPPED + live-verified: sequence-scoped timeline reads (R8 path, R10 duration) route to flame_get_sequence_segments and return real segment payloads instead of aborting at forge_get_shot's shot_id. Reads-only deterministic post-compile pass; DI.1 untouched; __all__=19; suite 2688. R9 timewarp = capability gap (no read tool — carry-forward, not SR). Ordinal/layer segment-selection out of scope (surfaced not resolved). 2/3 reachable win realized."
verification: "pytest 2688 passed / 41 skipped; ruff clean; __all__=19; live R8/R10 routed to flame_get_sequence_segments 30sec_edit 21 (daemon @9f24fde), returned sequence/frame_rate/segments/count. Evidence: UAT/SR.1-T1-substrate-confirm.md + UAT/SR.1-acceptance.md."
commits: "6f3fe90, f4ad78f, 4912e3b, 9f24fde (4)"
---

# SR.1 — Close (source-of-truth routing shipped, live-verified)

> SR.1 made a timeline-attribute read reach the substrate that holds its answer. The
> dogfood mis-selected `forge_get_shot` (forge entity) for a Flame timeline question; SR.1
> routes it — when a sequence reference is present — to `flame_get_sequence_segments`,
> which actually carries path + duration. 2/3 of the once-"reachable" set now answers
> live; R9 timewarp is honestly a capability gap, not a routing miss.

## What shipped (4 commits)

A deterministic, reads-only **post-compile source-routing pass**
(`console/_source_route.py::apply_source_routing`), hooked at `_chat_compile.py:205` after
the commit-node branch. Sequence-ref signal via 24.11; rewrite forge shot/segment reads →
`flame_get_sequence_segments <sequence_ref>`; fail-safe + reachability-guarded. `f4ad78f` /
`4912e3b` / `9f24fde` closed the predicted trap (rewritten step must carry a faithful,
mixed-separator sequence ref AND target a reachable tool).

## Conscious divergence (recorded — DT + Creative, not a defect)

SR.1 shipped as a **targeted step-rewrite** — a fixed `_SOURCE_ROUTABLE` set (`forge_get_shot`
family + `forge_list_shots`) → `flame_get_sequence_segments` when a sequence ref is present —
**not** the general namespace/substrate bias the discuss converged on. For SR.1's
deliberately-small scope this is the better call: smallest blast radius, clearest
verification surface, predictable rollback. **The trade, recorded so it's a known shape not
a later surprise** ([[feedback-transitional-structure-naming]]): SR.1 is an *explicit
mapping*, not a general substrate router — **the next substrate-routing case extends the
list, it does not inherit generality.** The larger pattern held open: a general
source-of-truth router keyed on the `flame_*`/`forge_*` namespace axis. Maturation
condition for generalizing: a 2nd/3rd routing case where extending the table becomes the
friction (then promote the mapping to a namespace-bias rule).

## The honest claim (DT + Creative — do not over-state)

Claim **"R8/R10 reach the answer-pass with real source data,"** NOT "R8/R10 answered." The
tool returns **25 segments**; the needed fields are in there (`file_path` for R8, `duration`
for R10), but turning that into "the path of *shot 10*" needs the two next-layer things SR.1
correctly doesn't own: **ordinal grounding** ("shot 10" → which of 25; `tst_010`/`tst_100`/
`tst_110` all loosely match, several span L01/L02/L03 — Q1 ambiguity now *grounded in real
payloads*, not hypothetical) and **answer-pass synthesis** (extract one field from a
25-row payload, don't dump it). The crossing peeled forward exactly as designed: substrate-
routing fixed → next exposed seam = ordinal-grounding + answer-pass synthesis.

## Recommended next probe (the SR.1-close → next-milestone signal; cheap, daemon up)

One dogfood read — **"what's the duration of shot 10 on 30sec_edit 21"** — cleanly
identifies the next hill:
- returns all 25 segments → **answer-pass synthesis** gap;
- selects the wrong segment → **ordinal-grounding** gap;
- right segment, wrong field → **payload-interpretation** gap;
- correct duration → both layers already partial.

## Verification

`pytest` 2688 passed / 41 skipped; ruff clean; `__all__`=19. **Live:** R8 + R10 both routed
to `flame_get_sequence_segments 30sec_edit 21` and returned real segment payloads instead
of the `shot_id` abort (daemon `9f24fde`).

## What this close does NOT claim

- **R9 timewarp** — capability gap (no read tool surfaces it). SR routed it to the right
  substrate; honest "right substrate, no capability" failure. Carry-forward: a timewarp
  inspection tool (future capability-coverage work), NOT SR.
- **Segment selection** — ordinal "shot 10" → which segment, layer multiplicity
  (`tst_010` on L01+L02 …). `flame_get_sequence_segments` returns all segments; the
  answer-pass has the data. Surfaced, not resolved (deliberate boundary).

## The arc's place (4-problem progression)

DI.1 authority correctness · DI.2 eligibility correctness · **SR.1 source-of-truth
correctness (read-side)** · future capability coverage (R9 timewarp tool). Each layer
refused to become the one above it; SR.1 routes substrate, never reinterprets, never
repairs compile, never resolves which segment.

## Carry-forwards

- **R9 / timewarp capability tool** — future capability-coverage (add a segment-effects
  read tool); then it routes for free (SR already sends timeline questions to the
  timeline substrate).
- **R7 / session-project scope** — "which project universe"; adjacent, separate.
- **Segment-selection** (ordinal + layer) — when an artist's "shot 10" must pick one of N
  segments; separate concern.
- **Bridge constraint-2** (Phase 26 / ADR-003) — `compile_intent()` emits a commit-bearing
  executor chain for the mutation-side; gated on the pipeline executor.
- **v1.11 milestone close** — SR.1 is v1.11's buildable phase; the milestone close
  (MILESTONES.md entry + methodology authoring) is the small remaining ceremony.

## Methodology candidates (for v1.11 milestone close)

- **Routing/implementation/reachability triad** (PROMOTED, [[feedback-routing-vs-implementation-vs-reachability]])
  — SR.1 is the clean class-2 (routing) milestone end-to-end.
- **The interface the milestone feared it had to build already shipped** (2nd instance:
  DI.1 `readOnlyHint`; ADR-003 commit-node generic contract) — substrate is more capable
  than the milestone assumes; work is consumer/adoption, not bridge-building.
- **Observation beats theory, before code** (Creative) — 7+ pre-code premise-flips this
  arc; each made the milestone honester. SR.1's reachable win went 3/3 → ≤3/9 → 1.5/3 →
  2/3 as probes hit real rows/substrate — all before a line of SR code.
- **Presence-vs-absence probe asymmetry** (DT) — assert presence from a source read; hand
  absence to the daemon (R9 timewarp).

## Status

**SR.1 CLOSED** — source-of-truth routing shipped, live-verified, boundary held. v1.11's
buildable phase is complete; milestone close + carry-forwards remain. The read-side
source-of-truth seam is correct: timeline questions reach the timeline substrate.
