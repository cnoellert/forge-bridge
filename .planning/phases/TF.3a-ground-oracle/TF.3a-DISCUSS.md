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
4. **The D3 example inventory exists BUT has drifted** (`NLT-…/D3-EXAMPLE-SALIENCE-INVENTORY.md`, scoped to
   `5f2b2a6`). Re-swept against live HEAD during this discuss (Creative redline #3): HIGH-risk literals persist,
   **but the `30sec_21` example surface grew** — new worked few-shot blocks (`timeline.py:146-148, :286-287,
   :687-688, :1100-1102`) D3 doesn't list, each higher-risk than the headlined `Field` examples. The grounding
   detector's substrate is therefore larger than D3 records → re-sweep is **3a step 0**, not a plan task (Q4).
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

### Q1 — What is a labeled "correct graph"? **LOCKED (Creative): an `(input → expected graph + expected params + expected verdict-pair)` tuple — the verdict-pair is foundational, not a detail.**

The verdict-pair is **locked**: without it the oracle literally cannot distinguish honest decline (PASS/GAP)
from translation failure (FAIL/NO-GAP) from translation-failure-plus-substrate-gap (FAIL/GAP). TF.2 made that
distinction; **TF.3a must inherit it** — it is the floor the rest of 3a stands on.

A label is **not** "the right answer string." Grounded in the contract, a label = the NL input plus:
1. the **expected chain-step graph** (the step-text list a correct compile would emit),
2. the **expected resolved params per step** (compile-resolved values; context-resolved refs labeled *as*
   unresolved-pending-dispatch, per TF.1-CONTRACT §2 — the corpus must not demand a concrete value where the
   contract says the ref resolves at dispatch), and
3. the **expected verdict-pair** (translation {pass,fail} × substrate {pass,gap}, TF.2 §2).

**The verdict-pair target is load-bearing:** without it the oracle has no way to score an **honest decline as a
*success*** (cell (c)/R9) or to mark a **substrate-gap** (cell (d)) — it would only know "right vs wrong." A
label that can't express "correctly declined" can't validate the behavior TF.2 most wants to reward.

### Q2 — How do we build the corpus? **REFRAMED (Creative): coverage-completeness, NOT corpus size. Seed from the 32 traces, augment until every taxonomy obligation is represented; aborts first-class.**

Creative's correction (folded): "is 32 enough?" is the wrong question — the oracle isn't estimating a
population parameter, it's **validating a taxonomy**. So adequacy is defined by **coverage, not count**. A
40-trace coverage-complete corpus beats a 200-trace corpus concentrated in one class.

- **Corpus adequacy [N] = every taxonomy obligation represented:** every **verdict-pair cell** (a–d),
  every **translation class** (the five), every **multi-tag pattern observed in discovery** (e.g. defect #2's
  routing+extraction), and **every D-series defect**. Raw counts matter only *after* coverage is complete.
- **Build method:** seed from the **32 well-formed comprehension traces** (drop the 4 malformed), **augment
  with the D-series/E2E-01 defects** (pre-diagnosed → cheapest high-value labels), and **author additional
  inputs until every obligation above is covered**. Do **not** reuse the comprehension `verdict` (wrong axis);
  label fresh.
- **Aborts are first-class, not noise (21/36).** An abort can be a **correct** honest-decline (cell (c) —
  label it a *success*) or a **wrong** abort (translation-FAIL). Excluding aborts would discard exactly the
  cell-(c) evidence Q1's verdict-pair exists to capture. **Lean: label aborts by the decline-vs-misroute
  discriminator** (TF.2 §2.1).

### Q3 — How do we validate the oracle itself? **Lean: held-out slice for Tier-2; Tier-1 gets LIGHTWEIGHT validation, NOT exemption (Creative).**

The oracle is "validated" when, on a **held-out** slice it never saw during detector tuning, its Tier-2
verdict-pairs reproduce the human labels within a **pre-declared agreement threshold**. This operationalizes
`[[feedback-audit-before-overfit]]` (v1.10 carried a 3× measurement-debt pattern — don't repeat it).

- **Tier-2** (grounding, entity-resolution, routing/wrong-selection): full held-out validation + agreement
  threshold. **Open:** per-class threshold (Tier-2 classes differ in difficulty)?
- **Tier-1 — lightweight validation, NOT a full exemption (Creative redline).** TF.3a is establishing *trust
  doctrine*; declaring "this class needs no validation" introduces a special case **before the validation
  framework exists** — starting the phase with an exception to its own principle. Compromise (folded): Tier-1
  gets a **sanity corpus + an explicit falsification case + documented assumptions** — enough to **prove the
  detector can fail when it should** — but **no held-out requirement and no precision/recall study.**
- **Open (still small-corpus-sensitive):** does coverage-completeness (Q2) leave a held-out slice large enough
  to mean anything for Tier-2, or does the authored-input pass need to over-provision the Tier-2 cells
  specifically?

### Q4 — What is a false positive for example-fill detection? **Lean: a value that matches an example but was NOT lifted (the legitimately-equal real `30sec_21`); measure the rate as a labeled sub-task.**

FP = the grounding detector flags `filled-from-example`, but the value was **genuinely grounded** and merely
*happens* to equal a docstring example (a real sequence named `30sec_21`). This is the milestone's **riskiest
instrument** (TF.2 §5). **Lean:** over the corpus values that match a D3-inventory example, hand-label each
**lifted** vs **legitimately-equal**, and report the FP rate. **3a may not ship the grounding detector — or let
3b score the grounding class — without this number.**

**D3 drift is a GROUNDING PREREQUISITE, not a planning task (Creative redline #3 — folded, and already
acted on).** D3 is the detector's *measurement substrate*; an unverified D3 = an uncalibrated instrument, and
the FP study depends on knowing what examples actually exist. So D3 was **re-swept against live HEAD now**, and
it **has drifted** — materially:

- HIGH-risk literals **persist** (no false-safe drift): `timeline.py:215/243` `prefix "e.g. 'noise', 'tst'"`;
  `publish.py:317/320` `'test long'`/`'test long_published'`; `publish.py:27` `'noise','spk','gen'`.
- **But the `30sec_21` surface GREW.** D3 (scoped to `5f2b2a6`) records it as `timeline.py:1094 ×2`; live HEAD
  now has worked **few-shot example blocks** — `timeline.py:146-148, :286-287, :687-688, :1100-1102` — each
  showing the **exact param fill** (`"sequence_name": "30sec_21"`, `"prefix": "noise"`). These are **higher**
  liftability risk than the `Field(description=…)` examples D3 headlined (a worked Tool-call block is directly
  pluggable), and **D3 does not list them.**

**Consequence:** building the FP study against D3-as-written would under-count its own substrate. **3a step 0 =
re-sweep D3 against HEAD** (refresh the inventory, add the few-shot blocks) **before** detector design. Remaining
sub-question: is the refreshed inventory **machine-consumable** (a value-set the detector reads), or does 3a
operationalize it? (`[[feedback-baseline-drift-invalidates-controls]]` — confirmed live, not assumed.)

### Q5 — Where does the third corpus instrument live + what is it named? **Lean: a new `forge_bridge/<distinct>/` package, named for *translation labels*, never `corpus`/`comprehension`.**

Given the §2 constraint, the labeled reference corpus needs its **own** package with its **own** versioned
schema — not a module inside `corpus/` or `comprehension/`. **Lean:** `forge_bridge/translation_oracle/` (or
similar), `__all__`-scoped, atomic-append JSONL, `SCHEMA_VERSION` from day one, **zero shared symbols** with the
other two.

**One artifact, one home — defend aggressively (Creative, strongly endorsed).** The room keeps rediscovering
that the same asset is being named from different angles — **DT** calls it a *reference corpus*; **Creative**
calls it an *operator-facing provenance surface*; **Phase 3** calls it *oracle validation*. These are **not
separate systems — they are projections of one asset.** So the labeled corpus, the per-param **provenance
signal** (`grounded-from-intent`/`from-context`/`filled-from-example`/`unresolved`), the validation outputs,
and the operator surface all live **together** in this one package. Splitting them would re-fragment exactly the
scattered translation layer v1.13 exists to consolidate. **Open:** confirm the exact name + that the per-param
provenance signal lives in this schema (so 3b reads it and Phase-4's gate surfaces it).

---

## North-star (Creative, recorded)

TF.3a is shaping up because it asks **"why should anyone trust this oracle?"** rather than **"how do we build a
detector?"** That is the distinction that keeps v1.13 from collapsing into another implementation-first
milestone. Every Q1–Q5 answer is in service of *earned trust in the instrument*, not instrument mechanics.

---

## What TF.3a produces (after the room settles Q1–Q5)

`TF.3a-PLAN.md`: the labeled-corpus schema + package incl. the per-param provenance signal (Q1/Q5,
verdict-pair LOCKED); the **coverage-complete** seeding + hand-labeling method (every taxonomy obligation
represented, aborts first-class — Q2, not a raw-count floor); the oracle-validation protocol — **Tier-2
held-out + threshold, Tier-1 lightweight (sanity + falsification case + documented assumptions, no holdout)**
(Q3); and **step 0 = re-sweep D3 against HEAD** (drift confirmed) → the refreshed example-set + the example-fill
detector + its measured FP rate (Q4). **No 3b run, no ranking, no Phase-4 fix.** 3a ships a *validated
instrument*; 3b is the first time it's allowed to measure — *because anyone can say why they trust it* (north-star).
