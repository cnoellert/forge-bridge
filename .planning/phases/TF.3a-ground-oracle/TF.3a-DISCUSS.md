# TF.3a (Ground the Oracle) — DISCUSS: build + validate the measurement instrument

**Milestone:** v1.13 Translation Fidelity, Phase 3a of 4 (3a = ground / 3b = run). **THE KEYSTONE.**
**Predecessors:** TF.1 (contract + inventory), TF.2 (taxonomy + 2-tier detection spec). **Deliverable (after room):** `TF.3a-PLAN.md`.
**Objective:** build the **labeled reference corpus** + the **example-fill detector with a measured false-positive
rate**, and **validate the oracle against held-out labels** — so 3b's verdicts are trustworthy enough to gate
Phase 4. `[[feedback-audit-before-overfit]]`: you cannot measure-first with an unvalidated instrument.

---

## Grounded realities (read live; these shape every question below)

1. **The comprehension corpus is real seed material but 100% unlabeled.** `~/.forge-bridge/comprehension/`
   holds **36 traces** (`question` + `chain[{step,result}]` + `answer`) — but **all 36 verdicts are null**
   (dogfood pending, per the cursor), 21 are `chain_aborted`, 11 `answered`, **4 malformed** (null question).
   And its `verdict` vocabulary (loved/hated/overstated/omitted_context/missed_intent) is the
   **legibility** axis, **orthogonal** to translation-correctness. → Seed exists; *every* translation label is
   **net-new authored work**.
2. **Distinct-instrument constraint, now with TWO siblings.** TF.3a's labeled corpus must never couple schemas
   with `comprehension/` (CR.1) **or** `corpus/` (v1.6 divergence). It is a **third** measurement instrument —
   mirror the atomic-append-JSONL + versioned-schema pattern; keep all three named distinctly forever.
3. **The chain-step graph is a step-text string list** (`parse_chain` → `[{step, result}]`,
   `handlers.py:1058/1677`); compile emits step text, dispatch resolves params. **No separate IR** — the label's
   "correct graph" is expressed in this same shape (TF.1-CONTRACT §1).
4. **The D3 example inventory already exists** (`NLT-…/D3-EXAMPLE-SALIENCE-INVENTORY.md`) — the grounding
   detector's oracle is documented; the open question is whether it's *machine-consumable* (Q4).
5. **Inherited de-scope:** the framing room put "resolve the reads two-part contract" on 3a's plate. **TF.1
   already resolved it** (reframed reads-vs-mutations → the compile-vs-context axis, commit `041d8a1`). So 3a
   **inherits a resolved axis** and does NOT re-open it — one fewer keystone obligation than the framing room
   assumed.

## The 3a / 3b boundary (restated)

- **3a (this phase):** build the labeled corpus, build + validate the example-fill detector (with its FP rate),
  validate the oracle against held-out labels. Ships the **instrument**, not a measurement.
- **3b (next):** run the validated oracle over the corpus → translation-pass/substrate-pass verdict pairs +
  the example-fill-vs-grounded frequency that **ranks Phase 4** (by deduped defect, TF.2 §4).

---

## Design questions (leads-with-views; → DT room)

### Q1 — What is a labeled "correct graph"? **Lean: an `(input → expected graph + expected params + expected verdict-pair)` tuple.**

A label is **not** "the right answer string." Grounded in the contract, a label = the NL input plus:
1. the **expected chain-step graph** (the step-text list a correct compile would emit),
2. the **expected resolved params per step** (compile-resolved values; context-resolved refs labeled *as*
   unresolved-pending-dispatch, per TF.1-CONTRACT §2 — the corpus must not demand a concrete value where the
   contract says the ref resolves at dispatch), and
3. the **expected verdict-pair** (translation {pass,fail} × substrate {pass,gap}, TF.2 §2).

**The verdict-pair target is load-bearing:** without it the oracle has no way to score an **honest decline as a
*success*** (cell (c)/R9) or to mark a **substrate-gap** (cell (d)) — it would only know "right vs wrong." A
label that can't express "correctly declined" can't validate the behavior TF.2 most wants to reward.

### Q2 — How do we build the corpus? **Lean: seed from the 36 traces + the D-series/E2E documented defects, then hand-label; aborts are first-class.**

- **Seed sources:** the 32 well-formed comprehension traces (drop the 4 malformed) **+** the D-series/E2E-01
  defects, which already carry *known-correct* expectations (defects #1/#2/#3 are pre-diagnosed — they are the
  cheapest high-value labels). Do **not** reuse the comprehension `verdict` (wrong axis); label fresh.
- **Aborts are first-class, not noise (21/36).** An abort can be a **correct** honest-decline (cell (c) —
  label it a *success*) or a **wrong** abort (translation-FAIL). Excluding aborts would discard exactly the
  cell-(c) evidence Q1's verdict-pair exists to capture. **Lean: label aborts by the decline-vs-misroute
  discriminator** (TF.2 §2.1).
- **Honest open sub-question for the room:** 32 traces is a *small* corpus. Is hand-labeling 32 + the D-series
  enough to (a) rank Phase 4 and (b) hold out a meaningful validation slice (Q3)? Or does 3a need an
  authored-input pass (write N new NL inputs spanning all five classes) to reach a floor? **Lean: author a
  small targeted set to guarantee ≥1 labeled instance per class × per verdict-cell**, rather than hoping the
  organic 32 happen to cover the matrix.

### Q3 — How do we validate the oracle itself? **Lean: held-out labeled slice; oracle must reproduce human labels within a stated agreement threshold before 3b gates anything.**

The oracle is "validated" when, on a **held-out** slice it never saw during detector tuning, its emitted
verdict-pairs reproduce the human labels within a **pre-declared agreement threshold**. This operationalizes
`[[feedback-audit-before-overfit]]` (v1.10 carried a 3× measurement-debt pattern — don't repeat it).
**Open for the room:** (a) what threshold (and is it per-class, since Tier-2 classes are harder)? (b) with a
small corpus, a held-out slice is tiny — does that force the authored-input pass from Q2? (c) the **Tier-1
detectors are substrate-observable and near-deterministic** (TF.2 §5) — do they even *need* held-out
validation, or only the **Tier-2** detectors (grounding, entity-resolution, routing/wrong-selection)? **Lean:
validation effort concentrates on Tier-2; Tier-1 gets a cheap sanity check, not a held-out slice.**

### Q4 — What is a false positive for example-fill detection? **Lean: a value that matches an example but was NOT lifted (the legitimately-equal real `30sec_21`); measure the rate as a labeled sub-task.**

FP = the grounding detector flags `filled-from-example`, but the value was **genuinely grounded** and merely
*happens* to equal a docstring example (a real sequence named `30sec_21`). This is the milestone's **riskiest
instrument** (TF.2 §5). **Lean:** over the corpus values that match a D3-inventory example, hand-label each
**lifted** vs **legitimately-equal**, and report the FP rate. **3a may not ship the grounding detector — or let
3b score the grounding class — without this number.** Two grounded sub-questions: (a) is
`D3-EXAMPLE-SALIENCE-INVENTORY.md` **machine-consumable**, or does 3a operationalize it into a value-set first?
(b) the detector reads the *live tool-description corpus* (the strip target spans `tools/{batch,timeline,
utility,publish,project,reconform}.py`) — does the inventory still match the live docstrings, or has it drifted
since the NLT phase? (`[[feedback-baseline-drift-invalidates-controls]]` — re-verify before trusting.)

### Q5 — Where does the third corpus instrument live + what is it named? **Lean: a new `forge_bridge/<distinct>/` package, named for *translation labels*, never `corpus`/`comprehension`.**

Given the §2 constraint, the labeled reference corpus needs its **own** package with its **own** versioned
schema — not a module inside `corpus/` or `comprehension/`. **Lean:** `forge_bridge/translation_oracle/` (or
similar), `__all__`-scoped, atomic-append JSONL, `SCHEMA_VERSION` from day one, **zero shared symbols** with the
other two. This is also the **one-artifact** home (framing-room reconciliation): the labeled corpus, the
per-param **provenance signal** (`grounded-from-intent`/`from-context`/`filled-from-example`/`unresolved`), and
the operator-facing validation surface are the **same artifact** built once here. **Open:** confirm the exact
name + that the per-param provenance signal lives in this schema (so 3b reads it and Phase-4's gate surfaces it).

---

## What TF.3a produces (after the room settles Q1–Q5)

`TF.3a-PLAN.md`: the labeled-corpus schema + package (Q1/Q5), the seeding + hand-labeling method incl. aborts
and any authored-input floor (Q2), the oracle-validation protocol + agreement threshold (Q3), the example-fill
detector + its measured FP rate + the D3-inventory operationalization/drift check (Q4). **No 3b run, no ranking,
no Phase-4 fix.** 3a ships a *validated instrument*; 3b is the first time it's allowed to measure.
