# A.5.3.2 — Phase-scope evaluation framing

**Status:** framing draft 2026-05-12 (post-Gate-4 close).
**Predecessor:** `A.5.3.2-GATE-4-CLOSE.md` (HEAD `bf6f3c9`, 1265 lines) — §7.4
explicitly left the phase-scope evaluation **intentionally unbound** between
two options: phase-closes-at-Gate-4 (with end-of-A.5.3.2 archaeology
synthesis) vs phase-extends-through-Gate-5+.
**Sibling at same commit:** `A.5.3.2-PR15-CLOSE.md` (1531 lines).
**Successor (if recommendation adopted):** `A.5.3.2-PHASE-CLOSE.md` — the
end-of-phase archaeology synthesis artifact, plus the second entry of
`docs/learnings/2026-05-06-narrowing-vocabulary.md` per original framing Step 3.

This document is a **decision-framing artifact**. It does not author the
end-of-phase synthesis itself; it authors the architectural decision of
whether to author that synthesis vs. open Gate 5. The Gate 4 close §7.4
unbinding clarification names "future-Gate-X (or end-of-A.5.3.2 archaeology)"
as the architectural-decision-locus — this framing claims that locus.

---

## 1. What this artifact decides

**Single decision:** does A.5.3.2 terminate at Gate 4 (with an end-of-phase
archaeology synthesis as Successor 1, and the deferred `narrowing-vocabulary`
learnings entry as Successor 2), or does it open Gate 5+ as continuation?

**What this artifact does NOT decide:**

- The substrate inventory itself — Gate 4 close §1 + §2 already captures it.
- The disposition of the 2 deferred candidate methodologies, 2 preserved
  candidate observations, PR 12 deferral, or 4 §7.3 ontological questions —
  Gate 4 close §3.2 + §6 already disposed of these as intentionally unbound
  at appropriate scope.
- The Layer 2 / Layer 3 boundary itself — out of scope at phase level.

---

## 2. Inputs — recount of Gate 4 close §7.4 unbound options

Recounted verbatim from `A.5.3.2-GATE-4-CLOSE.md` lines 1051–1080:

> The phase scope evaluation question — whether A.5.3.2 closes at Gate 4 or
> extends through Gate 5+ work — is **intentionally unbound** at this close.

Two arguments preserved at §7.4:

**Argument A (phase-closes-at-Gate-4):**

- Six-PR cumulative architectural sufficiency signal met (§1.4 promoted).
- Three-PR Gate 4 substrate operationally validates the comparator +
  recomposition arc under three divergence vectors without falsification.
- 5 named methodologies + 1 substrate primitive promoted at Gate 4 close
  establish the architectural-substrate evidence at phase scope.

**Argument B (phase-extends-through-Gate-5+):**

- 2 deferred candidate methodologies (PR-N-LOCAL parallel-not-regenerative;
  direction selection rationale) — both at 2-PR corroboration, would hit
  3-PR threshold under Gate 5.
- 2 preserved candidate observations (format-as-structural-claim discipline;
  single-PR three-fold catch-shape continuation sub-pattern).
- PR 12 DEFERRAL PRESERVED — numerical threshold met, qualitative
  second-clause failed under four-PR cumulative ABSENCE.
- 4 §7.3 ontological questions awaiting architectural-decision-locus.

Both arguments are load-bearing on their own terms. The decision is which
**architectural-decision-locus** is appropriate for the cumulative
archaeology — gate-arc-synthesis scope (Gate 5) or phase-arc-synthesis
scope (end-of-A.5.3.2 archaeology).

---

## 3. Recommendation

**A.5.3.2 terminates at Gate 4** with end-of-phase archaeology synthesis as
the closing artifact and the deferred `narrowing-vocabulary` learnings entry
as the durable-doc closer. **Gate 5 does NOT open.**

This is a position, not a hedge. Reasoning follows.

---

## 4. Reasoning

### 4.1 The original phase framing's "smaller fix scope; close" trigger fired

`A.5.3.2-FRAMING.md` line 291, Phase-end conditions table:

> Step 1 corpus shows the narrower is mostly correct and divergences are
> isolated → Smaller fix scope; document the corpus; close.

Six-PR cumulative ABSENCE of narrower-divergence under three operational
divergence vectors (PR 13 + PR 14 + PR 15) is the operationalization of
"the narrower is mostly correct and divergences are isolated." The Gate 4
close §1.4 six-PR cumulative architectural sufficiency signal **is** that
trigger firing at gate-arc scope. The framing already authored the
disposition; Gate 4 close operationalized the evidence.

This is the dominant load-bearing reason. Gate 5 would re-litigate a
trigger that has already fired against its own framing-time disposition.

### 4.2 Two-PR corroboration → three-PR corroboration is not architectural sufficiency, it is threshold-chasing

The two candidate methodologies at 2-PR corroboration (PR-N-LOCAL
parallel-not-regenerative; direction selection rationale) would hit the
3-PR threshold under Gate 5. But:

- Both candidates emerged from PR-shaped work, not from gate-arc synthesis.
  Their natural promotion vehicle is **next operational instance**, not
  **next gate**. Forcing a gate solely to satisfy 3-PR corroboration is
  the architectural cousin of `feedback_arbitration_boundary_discipline`'s
  "just one more heuristic" anti-pattern.
- The deferral language preserved at Gate 4 close is itself a governance
  act per `feedback_deferral_first_class_governance`. Treating the
  deferred candidates as Gate-5-shaped pressure inverts the governance —
  it converts deferral into latent pressure to manufacture corroboration.
- V1.6+ phases will produce real call-sites that either corroborate or
  falsify these candidates against actual code. That evidence is
  load-bearing in a way Gate-5-internal evidence is not — Gate 5 would
  reuse the A.5.3.2 substrate, so corroboration at Gate 5 is in-substrate.
  Promotion at substrate-scope from in-substrate corroboration is the
  weaker promotion shape.

### 4.3 PR 12 deferral is explicitly re-evaluable at "future-Gate-X," not at "next-Gate"

Gate 4 close §6 final disposition language: "DEFERRAL PRESERVED;
re-evaluable at future-Gate-X." The "future-Gate-X" framing is deliberate
— it preserves the option without binding to Gate 5 specifically. Opening
Gate 5 would force a premature re-evaluation against the same evidence
shape (four-PR cumulative ABSENCE qualitative second-clause failure) that
hasn't changed since Gate 4 close. Re-evaluation under unchanged evidence
is not governance, it is rehearsal.

### 4.4 The 4 §7.3 ontological questions are V1.6-shaped, not Gate-5-shaped

Gate 4 close §3.2 preserved 4 ontological questions as intentionally
unbound "at future-Gate-X (or end-of-A.5.3.2 archaeology) as named
methodology dispositions." These questions live at the seam between
substrate architecture and user-surface architecture — they are Layer 2 ↔
Layer 3 questions, not Layer 2-internal questions. The natural
architectural-decision-locus for Layer-2-↔-Layer-3 questions is the
next phase that touches Layer 3 (foundry / Ask / schematic surfaces),
not a continuation gate within A.5.3.2.

### 4.5 The original framing's Step 3 deliverable is unwritten and pending

`A.5.3.2-FRAMING.md` lines 68–71 names Step 3:

> 3. **Spec close + learnings entry.** Document what changed, why, and
>    against what evidence. Append the second entry of
>    `docs/learnings/2026-05-06-narrowing-vocabulary.md`.

`docs/learnings/2026-05-06-narrowing-vocabulary.md` line 123 still
carries the placeholder: "Status: DEFERRED until LLM reachability returns
... This entry will be written when A.5.3.2 lands."

This is a load-bearing structural artifact. The phase framing committed
to it as the durable-doc successor. Gate 5 cannot satisfy this commitment
— only phase close can. As long as A.5.3.2 remains open, the placeholder
remains, and the framing's Step 3 commitment carries a stale-deferral
posture (the original "deferred until LLM reachability returns" reason
has been fully satisfied since PR 7).

Closing A.5.3.2 lets this entry land. Opening Gate 5 defers it further
with no architectural justification.

### 4.6 Same-commit-paired close cadence has reached three operational instances at phase-arc scope, not gate-arc scope

Gate 4 close §1.12 promoted the same-commit-paired close cadence as
methodology after three operational instances (Gate 2 + Gate 3 + Gate 4
closes). The next natural application of the promoted methodology is the
**phase-arc close** — pair end-of-phase archaeology synthesis with the
final operational artifact (the learnings entry). Opening Gate 5 would
defer first phase-arc application of the methodology, weakening the
promotion shape.

### 4.7 Substrate is operationally mature

Gate 4 close §7.4 statement: "A.5.3.2 phase substrate operationally
mature for V1.6+ consumption per Placement B precondition 3 final
cumulative manifestation." This is an affirmative phase-arc state, not
a transitional state. Affirmative phase-arc state is the architectural
signature of phase close, not phase continuation.

---

## 5. End-of-phase archaeology synthesis — concrete deliverable shape

### 5.1 Binding voice constraint — operational-maturity-for-handoff, NOT architectural-completeness

The synthesis artifact MUST use **"operational maturity sufficient for
handoff"** language. It MUST NOT use **"architecture is now complete"**
language. These are different claims:

| Claim shape | What it asserts | Methodology compatibility |
|-------------|-----------------|---------------------------|
| Operational maturity for handoff | substrate is consumable by next consumers under known shape; methodology stack continues to mature | Compatible with the whole methodology stack — deferral-as-governance, arbitration-boundary discipline, decomposition→recomposition arc, explicit-continuation-evaluation |
| Architectural completeness | no further work is needed here; the architecture is closed | **INCOMPATIBLE** — this is victory-lap shape; it erodes the methodology stack by claiming closure on a substrate whose explicit purpose was deferral preservation + handoff readiness |

Concretely banned voice shapes for the synthesis:

- "the architecture is now complete"
- "A.5.3.2 is finished" (without qualifier — "finished as phase" is OK if
  paired with "handoff-ready for V1.6+ consumption")
- "all reliability questions are resolved"
- "the substrate is final"
- "no further work needed" (without scope-bound — "no further work
  needed within phase scope" is OK; bare claim is victory-lap)

Concretely required voice shapes for the synthesis:

- "operational maturity sufficient for handoff"
- "consumable forward by V1.6+ phases under [named conditions]"
- "phase-scope deliverables met; architectural questions explicitly
  preserved as unbound at [appropriate locus]"
- "substrate ready for next-consumer integration; methodology stack
  continues to mature against future evidence"
- "deferred candidates preserved as governance acts, not as latent
  pressure" — i.e., honor `feedback_deferral_first_class_governance` in
  the synthesis voice itself

**Why this is binding:** the existence of this phase-scope evaluation
framing artifact is itself a maturity signal — mature projects
**explicitly evaluate** whether continuation is justified, rather than
continuing forever (latent-pressure-driven) or stopping arbitrarily
(no-justification stop). A victory-lap synthesis would invert that
maturity signature: it would claim closure on a substrate whose explicit
methodology stack respects the distinction between consumable-handoff and
architecturally-finished. The synthesis voice must be coherent with the
artifact-existence's own signal.

The architectural test for any synthesis paragraph: **could a future
contributor reading this paragraph cold conclude that no further work in
this area is justified?** If yes, the paragraph is victory-lap-shaped and
must be rewritten with handoff-shape voice. If a paragraph asserts
substrate maturity, it must also name the **consumer-shape and
consumption-conditions** under which that maturity is operational.

### 5.2 Deliverable items

If recommendation adopted, the synthesis artifact (`A.5.3.2-PHASE-CLOSE.md`)
carries:

1. **Phase-arc summary** — original framing → 4 gates → 13 PRs (PRs 3–15,
   PR 12 numbering preserved as conditional archaeology). Brief, archaeology-
   grade counts.
2. **Substrate inventory at phase close** — carrier inventory, cleanup-
   pressure-resistance class membership, walker partition, env test count,
   `__all__` surface count, Layer 3 lint state. Verbatim from Gate 4 close
   §2; not re-derived.
3. **Methodology stack at phase close** — promoted (5 named + 1 substrate
   primitive at Gate 4 close, plus any phase-arc additions from synthesis),
   deferred (2 candidate methodologies), preserved (2 candidate
   observations).
4. **Phase-arc methodology candidates** — methodology candidates whose
   evidence-shape is phase-arc rather than PR-arc or gate-arc. Specifically:
   the four-gate decomposition→recomposition validation arc as named
   methodology candidate at phase-arc scope; whatever else surfaces during
   synthesis drafting.
5. **§7.3 ontological questions disposition** — restate as intentionally
   unbound at phase-arc scope, named-handoff to V1.6+ Layer 3 phases. Do
   NOT attempt to resolve. The unbinding is the disposition.
6. **PR 12 final disposition at phase-arc scope** — DEFERRAL PRESERVED
   forward to V1.6+. Restate the four-PR cumulative ABSENCE evidence
   without re-evaluating.
7. **Reseed protocol** — what V1.6+ phases that touch this substrate
   inherit, what they must NOT do (architecturally-prohibited per Gate 4
   close §3.1 + §3.2), how the carrier inventory is to be consumed.
8. **Same-commit pairing** — synthesis pairs with the `narrowing-
   vocabulary` learnings entry second-entry commit per §4.6.
9. **Cross-references** — phase framing, all gate framings + closes, all
   PR framings + specs + closes, instrument contract, learnings doc.

**Estimated synthesis size:** comparable to Gate 4 close (~1200–1500
lines). Phase-arc synthesis should not exceed gate-arc synthesis by
material proportions — the gate closes already carry the bulk of the
substrate archaeology. Phase synthesis is **cumulative pointer + phase-arc
methodology candidates**, not re-derivation.

**Estimated `narrowing-vocabulary.md` second-entry size:** ~150–250
lines. Shape matches the A.5.3.1 first-entry shape per the placeholder's
own anticipation (lines 133–136). Operator-readable; not internal-
methodology-readable. The audience is "future contributor reading
`docs/learnings/` cold," not "future-Claude reading phase archaeology."

---

## 6. Counter-case audit — what would change my view

Per `feedback_explicitly_unbound_vs_implicitly_rejected`, deferral
language preserves maneuverability. The recommendation above is firm but
not architecturally-prohibited from reversal. Conditions that would
warrant Gate 5 opening instead:

- **A V1.6+ phase surfaces evidence that the 2 deferred candidate
  methodologies are load-bearing for active substrate consumption, and
  the next operational instance is not naturally PR-shaped.** Currently
  no such pressure exists.
- **A §7.3 ontological question turns out to be Layer-2-internal rather
  than Layer 2-↔-Layer 3.** This would require fresh evidence that
  cannot exist at Gate 4 close — would emerge only from V1.6+ work.
- **PR 12 trigger surface evaluation inputs change shape.** Specifically,
  if the four-PR cumulative ABSENCE qualitative second-clause failure
  re-shapes under fifth+ ABSENCE evidence. Cannot happen at Gate 5 (Gate
  5 substrate is the same substrate); would require V1.6+ call-sites.
- **The narrower itself becomes Layer 3 rather than Layer 2.** This
  would be a profound re-scoping; it would also be its own phase, not a
  continuation gate.

None of these conditions presently obtain. Re-evaluation is appropriate
if any do.

---

## 7. Cross-references

**Predecessor decision-locus artifact:**

- `A.5.3.2-GATE-4-CLOSE.md` (`bf6f3c9`, 1265 lines) — §7.4 explicit
  unbinding clarification; this framing claims §7.4's "end-of-A.5.3.2
  archaeology" architectural-decision-locus.

**Sibling at same commit:**

- `A.5.3.2-PR15-CLOSE.md` (`bf6f3c9`, 1531 lines) — PR-15-scoped
  archaeology; third operational instance of same-commit-paired close
  cadence per Gate 4 §1.12.

**Phase-shape artifacts:**

- `A.5.3.2-FRAMING.md` (343 lines) — original phase shape; line 291
  Phase-end conditions trigger 1 ("smaller fix scope; close") fired
  per §4.1 above.
- `A.5.3.2-INSTRUMENT-CONTRACT.md` (781 lines) — instrument substrate.

**Gate-arc closes (in operational reading order):**

- `A.5.3.2-GATE-2-CLOSE.md` (`a6e42f0`) — first same-commit-paired close
  instance (Gate 2 + PR 6).
- `A.5.3.2-GATE-3-CLOSE.md` (`ee2225b`) — second same-commit-paired close
  instance (Gate 3 + PR 11); 17 active carriers + 10-member class +
  four-walker partition promotion.
- `A.5.3.2-GATE-4-CLOSE.md` (`bf6f3c9`) — third same-commit-paired close
  instance (Gate 4 + PR 15); 5 methodologies + 1 substrate primitive
  promoted.

**Durable-doc successor (commitment from original framing):**

- `docs/learnings/2026-05-06-narrowing-vocabulary.md` lines 121–149 —
  Issue 2 (A.5.3.2) placeholder section, unwritten since 2026-05-06. Per
  §4.5 above, this is load-bearing structural artifact for phase close.

**Memory cursor reference:**

- `project_state_2026_05_12_pr_15_gate_4_closed.md` — cursor recording
  the PR 15 + Gate 4 paired close at `bf6f3c9` and the "no practical
  near-term work pending; phase-scope evaluation handoff intentionally
  unbound" architectural state from which this framing departs.

---

## 8. Next concrete decision point

**Decision required from operator:**

1. Adopt the recommendation (phase-closes-at-Gate-4 + end-of-phase
   archaeology synthesis + learnings entry). Next action: draft
   `A.5.3.2-PHASE-CLOSE.md` per §5 shape; pair-commit with
   `narrowing-vocabulary.md` second-entry.
2. Reject the recommendation and open Gate 5. Next action: draft
   `A.5.3.2-GATE-5-FRAMING.md` against unchanged-evidence
   re-evaluation of the deferred candidates + PR 12. Counter-reasoning
   required per §4 above.
3. Defer the decision itself — keep A.5.3.2 in an open-but-quiescent
   state. This is the **architecturally-weakest option** per §4.5
   (Step 3 deliverable stays stale) + §4.6 (same-commit pairing
   methodology stays gate-arc-only); flagged here for completeness but
   not recommended.

Until this decision lands, the project state is "Gate 4 closed; phase
substrate operationally mature; next architectural action intentionally
unbound." That state is currently truthful, but a deferred decision is
not free — it costs `narrowing-vocabulary.md` accuracy and the
same-commit-paired close methodology's first phase-arc application
opportunity.

---

**Authored:** 2026-05-12.
**HEAD at draft:** `bf6f3c9` (clean working tree; `AGENTS.md` long-untracked, unrelated).
**Origin/main parity:** 0/0 at draft.
