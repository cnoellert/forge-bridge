# A.5.3.2 — Phase close (end-of-phase archaeology synthesis)

**Status:** phase close artifact 2026-05-12. End-of-phase archaeology synthesis
per `A.5.3.2-PHASE-SCOPE-EVALUATION-FRAMING.md` §3 recommendation (firm) +
§5.2 9-item deliverable shape. Honors §5.1 binding voice constraint
throughout (operational-maturity-for-handoff language; no
architectural-completeness shapes).

**HEAD at draft:** post-`52054e8`. Sibling artifact same-commit-paired
target: `docs/learnings/2026-05-06-narrowing-vocabulary.md` Issue 2
second-entry. **4th operational instance** of same-commit-paired close
cadence (methodology promoted at Gate 4 close §1.12 after three gate-arc
instances `a6e42f0` + `ee2225b` + `bf6f3c9`); **1st application at
phase-arc scope.**

**Decision-locus claim:** this synthesis claims the "end-of-A.5.3.2
archaeology" architectural-decision-locus per Gate 4 close §7.4
("future-Gate-X (or end-of-A.5.3.2 archaeology) authors the phase-scope
evaluation at appropriate architectural-decision-locus"), per
phase-scope evaluation framing §3 recommendation adopted.

**Voice discipline binding:** every "substrate mature" claim in this
document is paired with consumer-shape + consumption-conditions per
§5.1 of the phase-scope evaluation framing. No paragraph asserts that
no-further-work-in-this-area is justified; every closure claim is
explicitly scope-bound. The architectural test from §5.1 ("could a
future contributor reading this paragraph cold conclude that no further
work in this area is justified?") was applied to every section during
drafting; victory-lap-shaped phrasings were rewritten to handoff-shape.

---

## 1. Phase-arc summary

### 1.1 Phase shape and duration

A.5.3.2 opened 2026-05-06 with `A.5.3.2-FRAMING.md` (343 lines / 5 main
sections). Phase close authored 2026-05-12 — **6-day arc**.

Original framing locked three sequential steps:

1. Observation-and-classification (build the comparison instrument; run
   it; produce a divergence corpus).
2. Heuristic-tuning (only after corpus supports defensible
   classification).
3. Spec close + learnings entry (durable-doc append to
   `docs/learnings/2026-05-06-narrowing-vocabulary.md`).

**As-delivered phase shape:** original three-step framing expanded
under operational evidence into **4 gates + 12 PRs**. Phase-shape
evolution is itself a phase-arc archaeology observation preserved at §4
as candidate methodology — *original framing trigger-conditions
correctly anticipated the close-cadence; the gate-and-PR substrate
emerged from the work, not from the framing.*

### 1.2 As-delivered substrate (recounted, archaeology-grade)

**4 gates:**

- **Gate 1** — spec-only (`A.5.3.2-GATE-1-SPEC.md`, 21018 bytes / 2026-05-07).
  No framing or close artifact at gate-arc scope. Gate-arc framing-and-close
  cadence emerged at Gate 2.
- **Gate 2** — framing 2026-05-08 (`A.5.3.2-GATE-2-FRAMING.md`); close
  paired at `a6e42f0` 2026-05-11 with PR 9 close (**first operational
  instance** of same-commit-paired close cadence). Commit subject
  verbatim: `phase-a.5.3.2: PR 9 close + Gate 2 close — two artifacts
  at one commit`.
- **Gate 3** — framing 2026-05-11 (`A.5.3.2-GATE-3-FRAMING.md`); close
  paired at `ee2225b` 2026-05-11 with PR 11 close (**second operational
  instance**). Commit subject verbatim: `phase-a.5.3.2: PR 11 close +
  Gate 3 close — two artifacts at one commit`.
- **Gate 4** — framing 2026-05-12 (`A.5.3.2-GATE-4-FRAMING.md`,
  `fbf2285`); close paired at `bf6f3c9` 2026-05-12 with PR 15 close
  (**third operational instance**).

**12 PRs delivered** (PRs 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15). PR
12 numbering **preserved as conditional archaeology** per Gate 4 close
§6 DEFERRAL PRESERVED disposition (re-evaluable at future-Gate-X under
fifth+ ABSENCE evidence; not at Gate 5 since Gate 5 substrate = same
substrate).

**PR-close-cadence emerged mid-phase:** PR 3 has FRAMING + SPEC only,
no CLOSE artifact. PR 4 was first PR to ship the full FRAMING + SPEC +
CLOSE cadence. The full PR-close-cadence convention stabilized at PR 4
and held through PR 15. This is a phase-arc methodology-evolution
observation preserved at §4.

**Phase-arc artifact count (recounted from filesystem; archaeology-grade per [[feedback-counts-are-archaeology-grade]]):**

- Phase framing: 1 (`A.5.3.2-FRAMING.md`)
- Instrument contract: 1 (`A.5.3.2-INSTRUMENT-CONTRACT.md`, 781 lines)
- Gate-arc artifacts: 7 (Gate 1 spec-only = 1; Gates 2/3/4 framing +
  close each = 2 × 3 = 6)
- PR-arc artifacts: 35 (PR 3 partial cadence: framing + spec = 2;
  PRs 4-11 + 13-15 full cadence: framing + spec + close each = 11 × 3
  = 33)
- Phase-close governance artifacts: 2 (`A.5.3.2-PHASE-SCOPE-EVALUATION-FRAMING.md`
  at `52054e8` + this synthesis pending commit)
- PASSOFF artifacts: 6 (4 general-scope dated handoffs + 2 PR-8-scoped;
  session-scoped, predating durable memory cursor pattern)

Total durable phase-arc artifacts: **52** (post-this-commit; pre-this-
commit substrate had 51). PASSOFFs are session-scoped and arguably
not phase-arc-binding for V1.6+ consumer scope; PASSOFF-excluded total
is **46**.

### 1.3 What the phase delivered against original framing scope

Original framing **Primary deliverable** (line 81): "The **divergence
corpus** is the most important artifact this phase produces — more
important than any heuristic change that follows."

**As-delivered:** the divergence corpus exists as a structured test-time
fixture corpus + comparison instrument substrate. The 17 active carriers
(see §2.2) operationally encode corpus invariants. The 220 forge env
tests collected (see §2.1) exercise the corpus + instrument substrate
under three operational divergence vectors (PR 13 cardinality + PR 14
ordering + PR 15 multi-survivor cardinality).

Original framing **Objective lock** (line 158): "**This phase optimizes
for C** (minimize harmful hijacking). A and B are recorded for
completeness but are NOT the chosen objective."

**As-delivered:** objective C operationally maintained across all 12
delivered PRs. Zero PR proposed a relaxation toward A (maximize
deterministic) or B (maximize planner freedom). Zero gate close
proposed re-litigation. Objective C is **operationally consumable as
phase-arc-binding** by V1.6+ phases that touch the same substrate.

Original framing **Phase-end conditions trigger 1** (line 291): "Step 1
corpus shows the narrower is mostly correct and divergences are
isolated → Smaller fix scope; document the corpus; close."

**As-delivered:** trigger 1 fired at Gate 4 close §1.4 six-PR cumulative
architectural sufficiency signal (six-PR cumulative 0-prod-mod escalation
demonstrating "the narrower is mostly correct and divergences are
isolated"). The original framing correctly anticipated the close
condition; the substrate operationally validated the anticipation.

### 1.4 Phase-arc state at close

- **Phase scope deliverables met under original framing scope:**
  divergence corpus + comparison instrument substrate + learnings-entry-
  ready archaeology. Original framing Step 3 (`narrowing-vocabulary.md`
  Issue 2 second-entry) lands at this commit's pairing partner.
- **Architectural questions explicitly preserved as unbound at named
  loci:** 4 §7.3 ontological questions (V1.6+ Layer-2-↔-Layer-3
  handoff); 2 deferred candidate methodologies (await third operational
  instance in V1.6+ work); PR 12 DEFERRAL PRESERVED (re-evaluable at
  future-Gate-X under fifth+ ABSENCE evidence).
- **Substrate operationally mature for V1.6+ Layer 2 consumption** per
  Placement B precondition 3 final cumulative manifestation (Gate 4
  close §7.4 verbatim).
- **Methodology stack continues to mature against future evidence** —
  5 promoted methodologies + 1 substrate primitive at Gate 4 close +
  2 deferred candidate methodologies + 2 preserved candidate
  observations + phase-arc candidates surfaced at §4. None claim
  cross-phase corroboration; all preserve as governance acts.

### 1.5 Recount catch at synthesis drafting — gate-↔-PR pairing archaeology

**Catch preserved at synthesis drafting locus per [[feedback-counts-are-archaeology-grade]]:**

Initial drafting of §1.2 + §9.2 propagated **two pairing errors**
inherited from Gate 4 close §1.12 + §8 cross-references:

- §1.12 stated "Gate 2 close `a6e42f0` + PR 6 close pair" — **WRONG**.
- §8 predecessor-artifacts list stated "(Gate 2 + PR 6 close pair)" —
  **WRONG**.

Ground-truth verification at this synthesis drafting via
`git log -1 --format="%s" a6e42f0` returned commit subject:

> `phase-a.5.3.2: PR 9 close + Gate 2 close — two artifacts at one commit`

And `git diff-tree --no-commit-id --name-only -r a6e42f0` returned:

> `A.5.3.2-GATE-2-CLOSE.md`
> `A.5.3.2-PR9-CLOSE.md`

**Correct pairings (ground-truth verified):**

| Same-commit instance | Commit | Gate | PR paired |
|----------------------|--------|------|-----------|
| 1st operational | `a6e42f0` | Gate 2 | **PR 9** close |
| 2nd operational | `ee2225b` | Gate 3 | **PR 11** close |
| 3rd operational | `bf6f3c9` | Gate 4 | PR 15 close |

Synthesis sites corrected at §1.2 (Gate 2 + Gate 3 pairing lines) +
§9.2 (Gate 2 close cross-reference). Gate 4 cross-references state
PR 15 correctly; no fix needed there.

**Inherited-artifact discipline at this catch:**

`A.5.3.2-GATE-4-CLOSE.md` is committed at `bf6f3c9`; its §1.12 + §8
state Gate 2 + PR 6 close pair, contradicted by ground-truth git log.
**Gate 4 close is NOT amended at this synthesis** (history rewrite of
a pushed paired-close commit erodes archaeology more than the catch
preserves). The catch is preserved at this synthesis as
**downstream-correction archaeology** per
[[feedback-counts-are-archaeology-grade]] — counts and pairings are
archaeology-grade facts; downstream artifacts correct upstream errors
explicitly with the correction noted, rather than silently propagating
them.

**Consumer-shape:** V1.6+ readers consuming gate-arc archaeology MUST
trust this synthesis's §1.2 + §9.2 pairings over Gate 4 close §1.12 +
§8 pairings where they conflict; ground-truth-verified.

**Methodology implication (preserved as candidate observation):**
gate-arc cross-reference archaeology in close artifacts can drift from
ground-truth between gate-arc events as later artifacts cite earlier
artifacts citing earlier artifacts; phase-arc synthesis is the natural
locus to catch and correct such drift via direct git-log verification
of each cited commit. Candidate methodology observation: **"phase-arc
synthesis verifies upstream archaeology against ground-truth git log
before propagating gate-arc pairings."** Awaits second-phase
corroboration before promotion; NOT promoted at this synthesis.

---

## 2. Substrate inventory at phase close

### 2.1 Quantitative substrate state (verbatim from Gate 4 close §2; pointer-only)

Inherited unchanged from `A.5.3.2-GATE-4-CLOSE.md` §2 (gate-arc
inventory at `bf6f3c9`); no re-derivation at this synthesis. Phase close
does not modify code surfaces — `52054e8` framing commit and this
synthesis commit (`A.5.3.2-PHASE-CLOSE.md`-only) are documentation-only.

- **220 forge env tests collected** (verified at Gate 4 close per
  `python -m pytest tests/corpus/ --collect-only -q | tail -1`).
- **19 `forge_bridge.__all__` symbols** preserved (cleanup-pressure-
  resistance class member #2; six-PR cumulative reliability arc
  preserved unchanged).
- **17 active carriers** (Gate 4 close §1.14 — preserved unchanged
  across Gate 4 substrate; Carrier #16 promoted at Gate 3 close).
- **10-member cleanup-pressure-resistance class** (Gate 3 close
  promotion preserved; no new members at Gate 4 substrate per Gate 4
  close §1.13).
- **4-walker Layer 2 partition** (Gate 3 close promotion preserved).
- **17/17 Layer 3 lint passes** (gate-arc validation; carryforward
  unchanged).
- **Layer 3 architectural-surface count** unchanged from Gate 4 close
  §2.4.

**Consumer-shape:** V1.6+ phases that touch Layer 2 arbitration
substrate (foundry / Ask / schematic surfaces; downstream of Layer 2 ↔
Layer 3 seam questions per §5).

**Consumption-conditions:** carrier-and-class membership inherited
unchanged; production source modifications must clear the architectural
sufficiency signal evaluation (§3.2 promoted methodology); deferred
candidates honored as governance acts not latent pressure to relitigate
at consumer scope.

### 2.2 17 active carriers (Gate 4 close §1.14 verbatim; pointer-only)

The 17 active carriers preserved at Gate 4 close substrate are inherited
unchanged at phase close. Their operational role at V1.6+ consumer
scope: corpus invariants + instrument substrate + comparison fixture
substrate.

**Re-derivation prohibition:** carrier list is preserved verbatim at
Gate 4 close §1.14. This synthesis does NOT re-enumerate carriers — that
inventory is the gate-arc-scope artifact's responsibility, and
re-enumeration at phase-arc scope would weaken the gate-arc-scope
inheritance contract.

**Consumer access shape:** V1.6+ phases consume carrier inventory by
reading Gate 4 close §1.14 + §2.2; they MUST NOT re-enumerate carriers
at consumer scope unless surfacing fresh evidence that a carrier shape
is operationally insufficient (§7.3 ontological questions handoff scope
under §5 below).

### 2.3 Substrate provenance (artifact reading order for V1.6+ consumers)

V1.6+ phases consuming this substrate read in operational order:

1. `A.5.3.2-FRAMING.md` — original phase shape + objective C lock +
   boundary discipline + anti-pattern list. **Load-bearing for
   architecturally-prohibited at V1.6+ consumer scope.**
2. `A.5.3.2-INSTRUMENT-CONTRACT.md` — instrument substrate + explicit
   exclusions discipline. Load-bearing for any V1.6+ work that extends
   the comparison instrument.
3. `A.5.3.2-GATE-4-CLOSE.md` (`bf6f3c9`) — final gate-arc substrate +
   methodology stack + 5 promoted methodologies + 1 substrate primitive
   + 2 deferred candidates + 2 preserved observations.
4. This synthesis (`A.5.3.2-PHASE-CLOSE.md`) — phase-arc methodology
   candidates + reseed protocol + §7.3 phase-arc-scope disposition + PR
   12 phase-arc-scope disposition + same-commit pairing + cross-refs.

Earlier gate closes (Gate 2 `a6e42f0`; Gate 3 `ee2225b`) are accessible
as gate-arc precedent archaeology but not load-bearing for V1.6+
consumer scope unless V1.6+ work surfaces evidence that earlier-gate
substrate is operationally insufficient.

PR-arc closes are reference-grade archaeology, not load-bearing for
V1.6+ consumer scope (gate closes already synthesize PR-arc material).

---

## 3. Methodology stack at phase close

### 3.1 Promoted methodologies (5 named methodologies + 1 substrate primitive at Gate 4 close)

Inherited unchanged from Gate 4 close §5.2 + §1.2/§1.4/§1.7/§1.8/§1.10/§1.12;
pointer-only. **Promotion is gate-arc-scope evidence-shape; phase-arc
synthesis does not re-promote, nor does it elevate promotion to phase-arc
scope.** Re-promotion at phase-arc scope from single-phase evidence would
be architectural-completeness-shaped (covered by §5.1 voice constraint —
banned shape: "the substrate is final").

The 5 promoted named methodologies:

1. **§5.3 framing-time pressure prediction through absence** — five-
   instance cumulative ABSENCE (PR 10 + 11 + 13 + 14 + 15). Promoted
   methodology: at framing time, predict architectural pressure that
   should manifest in implementation and observe whether it does;
   absence-of-predicted-pressure is itself evidence of substrate
   sufficiency. Gate-arc-scope corroboration consumable at V1.6+ phase-
   open framings.
2. **Architectural sufficiency signal (six-PR cumulative 0-prod-mod
   escalation)** — PR 9 + 10 + 11 + 13 + 14 + 15. Promoted methodology:
   when N consecutive PRs ship without touching production source under
   active substrate exercise, the architectural-sufficiency signal is
   met at gate-arc scope. Consumable at V1.6+ reliability work.
3. **Both-skeletons-at-Step-1 lifecycle invariant** — three-PR-
   corroborated (PR 13 + 14 + 15). Promoted methodology: both test
   skeleton and fixture skeleton land at Step 1, not staggered across
   Steps 1-2. Consumable at V1.6+ corpus-extending work.
4. **Catch-point migration discipline with recursive-self-governance** —
   five-instance descriptive + seven catch-shape continuations. Promoted
   methodology: when a discipline catches a methodology drift, the
   discipline-catch itself becomes archaeology-grade; catch-point
   migration discipline applies recursively to its own catches.
5. **Same-commit-paired close cadence** — three operational instances
   (Gate 2 `a6e42f0` + Gate 3 `ee2225b` + Gate 4 `bf6f3c9`). Promoted
   methodology: PR-close + Gate-close at same commit when gate-arc
   synthesis surface coincides with PR-arc synthesis surface. **This
   synthesis is the 4th operational instance and 1st at phase-arc scope**
   (paired with `narrowing-vocabulary.md` Issue 2 second-entry — see §8).

The 1 promoted substrate primitive:

- **`"list"`-as-canonical-calibration-prompt** — four-PR cumulative (PR
  9 + 13 + 14 + 15). Substrate primitive: `"list"` as the canonical
  calibration prompt across the comparator + recomposition arc.
  Consumable at V1.6+ extension work that calibrates against the same
  substrate.

### 3.2 Deferred candidate methodologies (2; preserved as governance acts)

Inherited from Gate 4 close §1.6 + §1.9; pointer-only. **Honored as
governance acts per [[feedback-deferral-first-class-governance]]; NOT
re-evaluated at phase-arc scope.** Re-evaluation at phase-arc scope from
unchanged evidence would be threshold-chasing shape (covered by §5.1
voice constraint and by phase-scope evaluation framing §4.2).

1. **PR-N-LOCAL parallel-not-regenerative pattern** — two-PR
   corroboration (PR 14 introduce + PR 15 second instance). Awaits
   third operational instance at V1.6+ work; promotion-shape requires
   non-A.5.3.2-scope corroboration to honor cross-phase methodology
   discipline.
2. **Direction selection rationale at framing-level direction-symmetric
   pressure** — two-PR corroboration (PR 14 Direction A + PR 15 Direction
   A INVERSE). Awaits third operational instance at V1.6+ work.

**Consumer scope:** V1.6+ phases that surface PR-N-LOCAL or
direction-symmetric pressure may corroborate (advancing toward
promotion) or falsify (preserving deferral). V1.6+ phases MUST NOT
artificially manufacture corroboration to satisfy promotion threshold —
that would invert governance into latent pressure.

### 3.3 Preserved candidate observations (2)

Inherited from Gate 4 close §1.11 + §1.15; pointer-only.

1. **Format-as-structural-claim discipline** — NOVEL single-instance at
   PR 15. Awaits second corroboration at V1.6+ work.
2. **Single-PR three-fold catch-shape continuation sub-pattern** —
   INTEGRATED into catch-point migration methodology (§3.1 item 4) as
   sub-pattern at two-PR-corroborated cumulative archaeology (PR 14
   multi-instance + PR 15 single-instance).

### 3.4 Phase-arc methodology additions (preserved as candidates; see §4)

Phase-arc scope surfaces methodology candidates whose evidence-shape
spans the phase-arc rather than gate-arc or PR-arc. These candidates
are **preserved at this synthesis, NOT promoted** — single-phase
evidence is insufficient for cross-phase methodology promotion.
Promotion requires V1.6+ corroboration at consumer scope.

See §4 for the full phase-arc candidate inventory.

---

## 4. Phase-arc methodology candidates

Phase-arc-scope candidates surface during synthesis drafting per §5.2
deliverable item 4 of the phase-scope evaluation framing. Each candidate
is preserved with evidence-shape + consumer-shape-for-corroboration +
consumption-conditions. **None claim cross-phase corroboration.**

### 4.1 Four-gate decomposition→recomposition validation arc (full single-phase instance)

**Evidence shape:** A.5.3.2 delivered the first FULL operational
instance of the decomposition→recomposition validation arc named at
[[feedback-decomposition-recomposition-validation-arc]]. The arc shape:

- **Decomposition phase** — Gate 2 (carriers + cleanup-pressure-class
  decomposed; framing artifact `A.5.3.2-GATE-2-FRAMING.md` opens
  three-authority-surface partition; close at `a6e42f0` promotes
  carrier #14).
- **Recomposition phase opening** — Gate 3 (carrier #16 promotion +
  10-member cleanup-pressure-resistance class promotion + 4-walker
  Layer 2 partition promotion; close at `ee2225b`).
- **Recomposition phase completion** — Gate 4 (three-PR cumulative
  manifestation completes Placement B precondition 3; five-PR
  cumulative ABSENCE corroboration of §5.3; close at `bf6f3c9`).

**Phase-arc observation:** the four-gate arc demonstrates that the
decomposition→recomposition pattern manifests at gate-arc scope within
a single phase, not merely as inter-phase pattern. The
[[feedback-decomposition-recomposition-validation-arc]] memory text
("Gate 2 decomposed, Gate 3 recomposes") is corroborated at this
phase's full arc.

**Consumer-shape:** V1.6+ reliability phases at gate-arc scope.
**Consumption-conditions:** at framing time, enumerate the cleanup-
pressure forms explicitly per the existing feedback memory; observe
whether four-gate-arc shape recurs (corroborates) or doesn't (preserves
single-phase as instance #1).

**Promotion threshold:** unchanged — requires second-phase full arc
corroboration. **Not promoted at this synthesis.**

### 4.2 Governance-of-the-ending-separated-from-the-ending-itself (NOVEL phase-arc principle)

**Evidence shape:** NOVEL at A.5.3.2 phase close. Operator's explicit
2026-05-12 framing during phase-scope evaluation review:

> commit the phase-scope-evaluation framing + memory additions
> standalone, then draft the synthesis under those constraints, then
> same-commit-pair the final synthesis artifact with the actual phase
> close if that cadence still feels structurally right. That preserves
> the distinction between governance of the ending, and the ending
> itself.

**Phase-arc observation:** the architectural decision to close a phase
(governance act) is structurally distinct from the closing artifact
itself (synthesis act). Conflating them collapses the decision-locus
into the synthesis-locus and erodes the maturity signature that the
phase-scope evaluation framing artifact's existence creates.

**Operational manifestation at A.5.3.2:**

- Step 1 — `A.5.3.2-PHASE-SCOPE-EVALUATION-FRAMING.md` committed
  standalone at `52054e8`. Governance of the ending.
- Step 2 — this synthesis drafted under the framing's §5.1 voice
  constraint + §5.2 9-item deliverable shape. The ending itself.
- Step 3 (pending) — synthesis same-commit-paired with
  `narrowing-vocabulary.md` Issue 2 second-entry as actual phase close
  commit. Closure.

**Sibling principle:** [[feedback-explicitly-unbound-vs-implicitly-rejected]]
applied at phase-arc scope. Framing the decision is its own
architectural act; the decision's execution is a separate act.

**Consumer-shape:** V1.6+ phases at phase-close cadence.
**Consumption-conditions:** when authoring a phase close, first author
a phase-scope evaluation framing artifact that authors the close
decision (governance act); then author the synthesis artifact under
that framing's constraints (ending-itself act); pair-commit the
synthesis with any durable-doc-closer artifacts at a separate commit.

**Promotion threshold:** requires second-phase corroboration at V1.6+
phase close. **Not promoted at this synthesis** — single-phase NOVEL
observation.

### 4.3 Recursive-self-application of binding voice constraint at authoring commit (NOVEL operational discipline)

**Evidence shape:** NOVEL at A.5.3.2 phase-scope evaluation framing
commit `52054e8`. The §5.1 voice constraint authored in the framing
artifact was applied recursively to that same commit's commit-message
body: title "governance of the ending separated from the ending
itself"; body uses "operational maturity sufficient for handoff" +
"phase-scope deliverables met" + "intentionally unbound" throughout;
zero architectural-completeness shapes.

**Phase-arc observation:** when authoring a binding-discipline artifact,
recursively-self-applying the discipline at the authoring commit's own
message body operationalizes the discipline at its first natural locus.
Failure to recursively-self-apply at authoring commit would create a
discipline-mismatch precedent — the commit body would be the first
opportunity to violate the discipline the commit body authors.

**Sibling pattern:** catch-point migration methodology (§3.1 item 4)
already exhibits recursive-self-governance shape; this observation is
the same shape applied at binding-voice-constraint scope.

**Consumer-shape:** V1.6+ work that authors binding-discipline artifacts.
**Consumption-conditions:** when committing a binding-discipline
artifact, audit the commit message body against the discipline being
authored; rewrite if mismatch.

**Promotion threshold:** requires second instance of binding-discipline
authoring with recursive-self-application. **Not promoted at this
synthesis** — NOVEL single-instance observation.

### 4.4 PR-close-cadence mid-phase emergence (phase-arc methodology-evolution observation)

**Evidence shape:** PR 3 has FRAMING + SPEC artifacts only (no CLOSE
artifact). PR 4 was first PR with full FRAMING + SPEC + CLOSE cadence.
Cadence held PR 4 through PR 15.

**Phase-arc observation:** methodology cadence can emerge mid-phase
under operational pressure. The PR-close-cadence convention was not
named in the original phase framing; it emerged because PR 4's
substrate surfaced enough architectural archaeology to warrant a
dedicated close artifact.

**Anti-observation (binding):** this is NOT corroboration that PR 3
"should have had" a close artifact. PR 3's substrate may have been
inline-closeable without a dedicated close artifact; the emergent
cadence is consumer-evidence, not historical-deficiency-evidence.

**Consumer-shape:** V1.6+ phase opens that may surface emergent cadence
needs mid-phase.
**Consumption-conditions:** preserve maneuverability for cadence
evolution; do NOT retroactively impose cadence on early PRs whose
substrate didn't warrant it.

**Promotion threshold:** requires second-phase emergent-cadence
instance at V1.6+. **Not promoted at this synthesis.**

### 4.5 9-step traversal annotation pattern (PR 13/14/15 cumulative)

**Evidence shape:** PRs 13, 14, 15 each shipped a 9-step traversal
annotation pattern in test bodies (verified at PR 15 close §1; consistent
across the three-PR cumulative substrate).

**Phase-arc observation:** the 9-step annotation pattern emerged at PR
13 + held at PR 14 + held at PR 15. Three-PR cumulative within Gate 4
substrate; same-cadence-shape across cardinality / ordering /
multi-survivor cardinality divergence vectors.

**Sibling to Gate 4 §1.7 promoted methodology** (both-skeletons-at-Step-1
lifecycle invariant) — both observations corroborate at three-PR
cumulative within Gate 4 substrate. The traversal-annotation pattern
could be elevated to substrate-primitive-candidate alongside
`"list"`-as-canonical-calibration-prompt.

**Consumer-shape:** V1.6+ work that extends the corpus + comparator
substrate.
**Consumption-conditions:** when adding test fixtures that exercise
the comparator, follow the 9-step traversal annotation pattern unless
fresh evidence justifies divergence.

**Promotion threshold:** requires extension beyond A.5.3.2 substrate.
**Not promoted at this synthesis** — substrate-primitive-candidate.

### 4.6 Phase-arc duration as operational signal (6-day arc observation)

**Evidence shape:** phase opened 2026-05-06, closes 2026-05-12 (this
commit). 6-day arc delivered 4 gates + 12 PRs + 44 durable artifacts +
220 forge env tests + 5 promoted methodologies + 1 substrate primitive
+ 2 deferred candidates + 2 preserved observations.

**Phase-arc observation:** 6-day arc duration may be representative or
may be outlier; insufficient single-phase evidence to claim either.
Preserved as phase-arc operational data point.

**Consumer-shape:** V1.6+ phase-open framing.
**Consumption-conditions:** do NOT use A.5.3.2's 6-day arc as duration
benchmark; consume only as one-instance evidence in any cross-phase
duration analysis.

**Promotion threshold:** N/A — duration is operational data, not
methodology. Preserved for phase-arc archaeology only.

---

## 5. §7.3 ontological questions — phase-arc disposition

Inherited unchanged from Gate 4 close §3.2; phase-arc-scope disposition
**restates intentional unbinding**, does NOT attempt resolution.

The 4 §7.3 ontological questions surfaced at Gate 4 close §3.2 are
**intentionally unbound at phase-arc scope** per
[[feedback-explicitly-unbound-vs-implicitly-rejected]]. Resolution at
phase-arc scope would be:

- Layer-2-internal: insufficient — these questions are Layer-2-↔-Layer-3,
  per phase-scope evaluation framing §4.4. The natural decision-locus
  is V1.6+ phases that touch Layer 3 (foundry / Ask / schematic
  surfaces).
- Phase-arc-internal: insufficient — single-phase evidence cannot
  resolve cross-phase ontological questions; resolution at phase-arc
  scope would be premature.

**Phase-arc disposition:** the 4 §7.3 ontological questions are
**handed forward to V1.6+ Layer-2-↔-Layer-3 phases as named handoff
artifacts**. Each consuming phase that touches the seam between Layer 2
and Layer 3 is the natural architectural-decision-locus for the
question(s) relevant to that seam.

**Consumer-shape:** V1.6+ phases at the Layer-2-↔-Layer-3 seam (foundry
/ Ask / schematic).

**Consumption-conditions:**

- Consuming phase MUST reference Gate 4 close §3.2 ontological question
  list at framing time.
- Consuming phase MAY resolve question(s) relevant to its scope at its
  own architectural-decision-locus.
- Consuming phase MUST NOT resolve question(s) outside its scope.
- Consuming phase MUST honor [[feedback-explicitly-unbound-vs-implicitly-rejected]]
  — resolved questions get explicit-resolution language; deferred
  questions get continued-unbinding language.

**Re-evaluation discipline:** the 4 §7.3 ontological questions are
**re-evaluable at V1.6+ consumer-phase scope**, NOT at A.5.3.2 phase-arc
scope. This synthesis claims architectural-decision-locus for phase-arc
disposition (handoff), NOT for question-resolution.

---

## 6. PR 12 final disposition at phase-arc scope

Inherited unchanged from Gate 4 close §6 final disposition; phase-arc-
scope disposition **restates DEFERRAL PRESERVED**, does NOT re-evaluate.

**Disposition:** PR 12 numbering preserved as conditional architectural
archaeology. Numerical threshold satisfied (6 cumulative call-sites ≥ 4
threshold per Gate 4 close §6). Qualitative second-clause pressure
observation registered ABSENCE across four-PR cumulative evaluation (PR
11 + 13 + 14 + 15 all ABSENCE; no "preserving decomposition becomes
harder than abstracting" pressure surfaced).

**Phase-arc disposition:** DEFERRAL PRESERVED forward to V1.6+ work.
Re-evaluable at future-Gate-X (NOT at Gate 5 — Gate 5 substrate would
be the same substrate, so re-evaluation would be rehearsal under
unchanged evidence per phase-scope evaluation framing §4.3).

**Consumer-shape:** V1.6+ work that introduces call-sites or surfaces
qualitative second-clause pressure under fifth+ ABSENCE evidence.

**Consumption-conditions:**

- Numerical threshold remains 6+ call-sites (Gate 4 close §6).
- Qualitative second-clause remains "preserving decomposition becomes
  harder than abstracting" (Gate 4 close §6).
- Helper extraction in absence of qualitative pressure remains
  premature abstraction at any future-Gate-X.
- Re-evaluation triggered ONLY by fresh qualitative pressure evidence;
  numerical-only re-evaluation invalid.

**Re-evaluation discipline:** intentionally unbound per
[[feedback-explicitly-unbound-vs-implicitly-rejected]]; preserved as
governance act per [[feedback-deferral-first-class-governance]]; NOT
implicit rejection of PR 12 work.

---

## 7. Reseed protocol — V1.6+ Layer 2 consumer entry

### 7.1 What V1.6+ phases inherit from A.5.3.2 substrate

Substrate at phase close consumable as **operational maturity
sufficient for handoff** under named conditions:

- **220 forge env tests collected** — V1.6+ work that extends or
  modifies this collection MUST preserve existing test pass state;
  additions follow the 9-step traversal annotation pattern (§4.5)
  unless fresh evidence justifies divergence.
- **19 `forge_bridge.__all__` symbols** — cleanup-pressure-resistance
  class member #2; V1.6+ work that proposes `__all__` modification MUST
  surface architectural pressure justifying it (six-PR cumulative
  reliability arc preserves at 19; pressure-of-absence is itself
  evidence).
- **17 active carriers** — corpus invariants + instrument substrate +
  comparison fixture substrate. V1.6+ work consumes carriers by
  reference (Gate 4 close §1.14); MUST NOT re-enumerate at consumer
  scope unless surfacing fresh evidence of insufficiency.
- **10-member cleanup-pressure-resistance class** — Gate 3 close
  promotion preserved; V1.6+ work that introduces new class members
  follows Gate 3 close §1 promotion-shape (cumulative evidence at
  three-instance-or-equivalent shape).
- **4-walker Layer 2 partition** — Gate 3 close promotion preserved;
  V1.6+ work that proposes walker addition MUST clear architectural
  sufficiency signal (§3.1 item 2 promoted methodology).
- **17/17 Layer 3 lint passes** — gate-arc validation; V1.6+ work MUST
  maintain at consumer scope.

### 7.2 What V1.6+ phases MUST NOT do at this substrate

Architecturally-prohibited per Gate 4 close §3.1 + §3.2 + phase-scope
evaluation framing §3 + §5.1 voice constraint:

- **MUST NOT re-litigate objective C lock.** Original framing §line 158
  locked objective C (minimize harmful hijacking); A.5.3.2 substrate
  operationally validated C across 12 delivered PRs. Re-litigation at
  V1.6+ consumer scope requires fresh asymmetric-cost-of-error evidence
  (original framing §lines 162-193); not merely a proposal that A or B
  would be faster.
- **MUST NOT relax boundary discipline.** Original framing §line 210
  boundary-discipline table is load-bearing for V1.6+ consumer scope.
  Every proposed heuristic must clear the boundary table; blurred-line
  proposals get rejected, not "compromised on."
- **MUST NOT manufacture corroboration to satisfy deferred-candidate
  promotion thresholds.** PR-N-LOCAL parallel-not-regenerative
  (§3.2 item 1) + direction selection rationale (§3.2 item 2) await
  third operational instance — corroboration must arise from genuine
  V1.6+ work pressure, not from manufactured pressure to advance
  promotion.
- **MUST NOT re-promote phase-arc methodology candidates from
  single-phase evidence.** §4 candidates require cross-phase
  corroboration; re-promotion at V1.6+ single-instance corroboration
  would be threshold-chasing.
- **MUST NOT resolve §7.3 ontological questions outside V1.6+ consuming
  phase's scope** (per §5 above).
- **MUST NOT re-evaluate PR 12 deferral under unchanged evidence
  shape** (per §6 above).
- **MUST NOT use architectural-completeness voice about A.5.3.2
  substrate.** The substrate is operationally mature for V1.6+ Layer 2
  consumption under named conditions — it is NOT "complete" or
  "finished." V1.6+ phase artifacts that reference A.5.3.2 MUST use
  handoff-shape voice per §5.1 voice constraint discipline.

### 7.3 How to consume the carrier inventory

Inheriting carriers at V1.6+ scope:

1. **Read Gate 4 close §1.14 + §2.2** for the 17 active carrier list.
2. **Read this synthesis §2.2** for consumer-shape + consumption-
   conditions discipline.
3. **At V1.6+ framing time**, enumerate which carriers the V1.6+ work
   touches; mark each carrier touched as either preserved, extended,
   or evolved.
4. **Carrier extension or evolution at V1.6+ scope** requires
   architectural sufficiency signal at V1.6+-phase-arc scope (per §3.1
   item 2 promoted methodology consumption).
5. **Carrier preservation at V1.6+ scope** requires no special
   discipline beyond the boundary-discipline + objective-C-lock
   inheritance.

### 7.4 How to consume the cleanup-pressure-resistance class

Inheriting class membership at V1.6+ scope:

1. **Read Gate 3 close** for class-promotion archaeology + 10-member
   inventory.
2. **Read Gate 4 close §1.13** for "no new members at Gate 4 substrate"
   negative-evidence anchor.
3. **At V1.6+ framing time**, predict cleanup-pressure forms that V1.6+
   work might surface (per [[feedback-decomposition-recomposition-validation-arc]]
   discipline).
4. **Class-member addition at V1.6+ scope** requires cumulative evidence
   at three-instance-or-equivalent shape per Gate 3 close promotion
   precedent.

### 7.5 Layer-2-↔-Layer-3 handoff shape for §7.3 questions

Per §5 above + Gate 4 close §3.2. V1.6+ phases at the Layer-2-↔-Layer-3
seam (foundry / Ask / schematic) are the natural decision-locus.
Consumer phase MUST reference Gate 4 close §3.2 ontological question
list at framing time.

---

## 8. Same-commit pairing

### 8.1 Phase-arc first application of promoted methodology

This synthesis pairs at commit with `docs/learnings/2026-05-06-narrowing-vocabulary.md`
Issue 2 second-entry (~150-250 line entry per phase-scope evaluation
framing §5.2 estimate; final size emerges at drafting). **4th operational
instance** of same-commit-paired close cadence (Gate 4 close §1.12
promoted methodology); **1st application at phase-arc scope**.

**Methodology promotion shape consumer-evidence:** the methodology was
promoted at Gate 4 close after three gate-arc operational instances
(Gate 2 + Gate 3 + Gate 4). The phase-arc application at this synthesis
is the first cross-scope corroboration — gate-arc methodology
manifesting at phase-arc scope without re-derivation. This is
**phase-arc consumer-evidence** that the promoted methodology has
cross-scope generality.

**NOT a promotion event:** phase-arc first-application is corroboration,
not re-promotion. The methodology stays at promoted-status; this
synthesis adds phase-arc operational instance #1 to the cumulative
evidence base.

### 8.2 What the pairing partner artifact carries

`docs/learnings/2026-05-06-narrowing-vocabulary.md` Issue 2 second-entry
shape (per pre-existing placeholder lines 121-149 of the learnings doc):

- **What real usage exposed** — multi-intent prompt collapse case
  surfaced under A.5.3.1's pre-fix behavior; comparison-instrument
  substrate is the right diagnostic shape.
- **Why the collapse was wrong** — asymmetric cost of error (state
  corruption vs latency), per original framing §lines 162-193.
- **Why architecture review didn't reveal it** — narrower's failure
  modes only visible at the seam between subsystems (per learnings
  doc methodological note line 153-160).
- **What diagnostic evidence drove the fix** — instrument contract +
  divergence corpus + 17 active carriers + comparator substrate.
- **What landed** — pointer to A.5.3.2-PHASE-CLOSE.md synthesis +
  PHASE-SCOPE-EVALUATION-FRAMING + Gate 4 close §1 + §2.

The pairing partner is **operator-readable**, not internal-
methodology-readable, per phase-scope evaluation framing §5.2
estimate. Audience: future contributor reading `docs/learnings/` cold,
not future-Claude reading phase archaeology.

### 8.3 Commit cadence at phase close

**This synthesis commit:** synthesis-only or synthesis-plus-learnings-
entry (pairing-partner). Operator decision per phase-scope evaluation
framing §8 Next concrete decision point.

**Push cadence:** batched push of `52054e8` (phase-scope evaluation
framing) + this synthesis commit + (optional) pairing partner commit.
Push happens at Step 3 close per phase-scope evaluation framing §8
operator three-step plan; not before.

---

## 9. Cross-references

### 9.1 Phase-shape artifacts

- `A.5.3.2-FRAMING.md` (343 lines) — original phase shape; objective C
  lock (§ lines 145-205); boundary discipline (§lines 210-229);
  anti-pattern list (§lines 233-247); phase-end conditions (§line 289;
  trigger 1 fired per §1.3 above + phase-scope evaluation framing
  §4.1).
- `A.5.3.2-INSTRUMENT-CONTRACT.md` (781 lines) — instrument substrate;
  explicit-exclusions discipline.
- `A.5.3.2-PHASE-SCOPE-EVALUATION-FRAMING.md` (`52054e8`, 391 lines /
  8 sections / 9 subsections) — governance-of-the-ending decision-
  locus framing; §3 recommendation (firm); §5.1 BINDING voice
  constraint authored; §5.2 9-item deliverable shape; §6 counter-case
  4 conditions preserving maneuverability.

### 9.2 Gate-arc closes (operational reading order)

- `A.5.3.2-GATE-1-SPEC.md` (2026-05-07) — Gate 1 spec only; no
  framing-and-close cadence at gate-arc scope yet.
- `A.5.3.2-GATE-2-FRAMING.md` (2026-05-08) — three-authority-surface
  partition; decomposition opens.
- `A.5.3.2-GATE-2-CLOSE.md` (`a6e42f0`, 2026-05-11) — first
  operational instance of same-commit-paired close cadence (paired
  with PR 9 close per ground-truth git verification at this synthesis
  drafting; see §1.5 recount catch); carrier #14 promoted.
- `A.5.3.2-GATE-3-FRAMING.md` (2026-05-11) — Path B locked precedent;
  cross-surface unbinding clarification.
- `A.5.3.2-GATE-3-CLOSE.md` (`ee2225b`, 2026-05-11) — second
  operational instance (paired with PR 11 close); carrier #16
  promotion + 10-member cleanup-pressure-resistance class promotion +
  4-walker Layer 2 partition promotion; conditional PR 12 DEFER
  inheritance.
- `A.5.3.2-GATE-4-FRAMING.md` (`fbf2285`, 2026-05-12) — gate-level
  inheritance contract; §2.4 architectural commitment; three-PR primary
  slot structure (PR 13 + PR 14 + PR 15); §5.10 PR 12 conditional
  disposition options; §11.8 same-commit Gate 4 close pattern.
- `A.5.3.2-GATE-4-CLOSE.md` (`bf6f3c9`, 2026-05-12) — third
  operational instance of same-commit-paired close cadence (paired
  with PR 15 close); 5 named methodologies + 1 substrate primitive
  promoted; 2 deferred candidate methodologies; 2 preserved candidate
  observations; PR-12 DEFERRAL PRESERVED final disposition; 4 §7.3
  ontological questions intentionally unbound.

### 9.3 PR-arc artifacts (12 PRs delivered; reading order)

- **PR 3** — FRAMING + SPEC (no close; cadence emerged at PR 4).
- **PR 4** — FRAMING + SPEC + CLOSE (first full cadence).
- **PR 5, 6, 7, 8, 9, 10, 11** — full cadence each.
- **PR 12** — numbering preserved as conditional archaeology; no
  artifacts; DEFERRAL PRESERVED disposition (per §6 above).
- **PR 13, 14, 15** — full cadence each; Gate 4 three-PR primary
  slot structure.

PR-arc artifacts are reference-grade archaeology for V1.6+ consumer
scope (Gate 4 close synthesizes PR-arc material; PR-arc artifacts are
accessible if V1.6+ work surfaces evidence requiring deeper
PR-arc-scope archaeology).

### 9.4 Sibling at same-commit pairing target

- `docs/learnings/2026-05-06-narrowing-vocabulary.md` Issue 2
  second-entry — same-commit pairing partner; ~150-250 line entry;
  operator-readable; original phase framing Step 3 deliverable.

### 9.5 Memory companions (out-of-tree; not in git history)

- `feedback_operational_maturity_not_completeness.md` — binding voice
  constraint memory; authored at same operational instant as phase-
  scope evaluation framing.
- `project_state_2026_05_12_phase_scope_evaluation_framing_landed.md`
  — fresh cursor at `52054e8` cut before this synthesis drafting;
  preserves framing-landed state separately from synthesis-compressed
  state per [[feedback-cursor-before-retrospective-synthesis]].

### 9.6 Predecessor session-scoped artifacts (PASSOFFs)

- `A.5.3.2-PASSOFF-2026-05-08.md`
- `A.5.3.2-PASSOFF-2026-05-09.md`
- `A.5.3.2-PASSOFF-2026-05-09-STEP7.md`
- `A.5.3.2-PASSOFF-2026-05-10.md`
- `A.5.3.2-PR8-CLOSE-PASSOFF-2026-05-11.md`
- `A.5.3.2-PR8-PASSOFF-2026-05-11.md`

Session-scoped handoff cursors predating durable memory cursor
pattern. Not load-bearing for V1.6+ consumer scope; phase-arc
archaeology grade only.

### 9.7 Predecessor phase

- A.5.3.1 closed at `d15c00e` (per original framing line 4): "narrower
  fail-open guard shipped for the verb-only-overlap case." A.5.3.2
  extended A.5.3.1's posture per original framing §lines 196-204
  ("continuity with A.5.3.1" — objective C is the same posture
  A.5.3.1 already operationalized at smaller scope).

---

## 10. Closing posture

A.5.3.2 phase scope deliverables met under original framing scope.
Substrate operationally mature for V1.6+ Layer 2 consumption under
named conditions enumerated in §7. Methodology stack continues to
mature against future evidence per §3 promoted-and-deferred discipline.
Deferred candidates preserved as governance acts, not as latent
pressure to manufacture closure at V1.6+ consumer scope.

The phase-scope evaluation framing artifact's existence (and this
synthesis under its binding §5.1 voice constraint) signals project
maturity at the architectural-decision-locus discipline scope — mature
projects explicitly evaluate whether continuation is justified, neither
continuing forever under latent pressure nor stopping arbitrarily
without justification. This synthesis is the explicit-evaluation
artifact for the A.5.3.2 phase-arc decision-locus.

Architectural questions explicitly preserved as unbound at named loci
(§5 § 7.3 ontological questions handoff; §6 PR 12 DEFERRAL PRESERVED;
§3.2 + §3.3 deferred candidate methodologies and preserved
observations). V1.6+ consumer phases are the natural architectural-
decision-locus for those questions whose scope reaches their substrate
intersections.

This is **not** "the architecture is now complete." This is **phase-
scope deliverables met; architectural questions explicitly preserved
as unbound at appropriate loci; substrate ready for V1.6+ Layer 2
consumer integration; methodology stack continues to mature against
future evidence.**

The distinction is load-bearing. This synthesis honors it by §5.1
binding voice constraint discipline throughout.

---

**Authored:** 2026-05-12.
**Sibling commit pairing target:** `docs/learnings/2026-05-06-narrowing-vocabulary.md` Issue 2 second-entry.
**Push cadence:** batched at Step 3 close commit per phase-scope evaluation framing §8 operator three-step plan.
**Voice discipline:** §5.1 binding voice constraint honored throughout (architectural test applied per paragraph).
