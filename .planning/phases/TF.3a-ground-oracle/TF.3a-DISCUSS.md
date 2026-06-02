# TF.3a (Ground the Oracle) — DISCUSS: build + validate the measurement instrument

**Milestone:** v1.13 Translation Fidelity, Phase 3a of 4 (3a = ground / 3b = run). **THE KEYSTONE.**
**Status:** **room-settled** (DT + Creative; 4 endorsements-with-sharpenings + 1 blocking precondition).
**Predecessors:** TF.1 (contract + inventory), TF.2 (taxonomy + 2-tier detection spec). **Deliverable:** `TF.3a-PLAN.md`.
**Objective:** build the **labeled reference corpus** + the **example-fill detector with a measured false-positive
rate**, and **validate the oracle against held-out labels** — so 3b's verdicts are trustworthy enough to gate
Phase 4. `[[feedback-audit-before-overfit]]`: you cannot measure-first with an unvalidated instrument.

> **North-star (both voices):** the hard problem of v1.13 is **not building detectors — it's proving the
> detectors observe the right thing.** TF.3a was itself about to inherit the very flaw the milestone exists to
> detect (measuring against an incomplete representation of reality — see the Q4 finding). Every Q1–Q5 answer
> serves *earned trust in the instrument*, not instrument mechanics. The right question is "**why should anyone
> trust this oracle?**", not "how do we build a detector?"

---

## Grounded realities (read live; these shape every question)

1. **The comprehension corpus is real seed material but 100% unlabeled — and skewed.** `~/.forge-bridge/
   comprehension/` holds **36 traces** (`question` + `chain` + `answer`); all 36 verdicts null, 21 aborts, 4
   malformed. Its `verdict` axis (loved/hated/…) is **legibility**, orthogonal to translation-correctness. DT's
   sharpening: 32 well-formed traces are **one reads-dogfood session on the legibility axis** → they clump in a
   few cells (grounding/routing on reads), and the **contextual class (§3.5) was almost certainly never
   exercised** (it needs world-state the dogfood didn't set up). Seed exists; every translation label is
   net-new; and the *geometry* is lopsided.
2. **Distinct-instrument constraint, now a three-vocabulary rule.** TF.3a's corpus must stay schema-distinct
   from `comprehension/` (CR.1) and `corpus/` (v1.6). It is a **third** instrument — mirror atomic-append-JSONL
   + versioned-schema; and (DT/Q5) the distinctness bites at the **label-vocabulary field level**, not just the
   package name.
3. **The chain-step graph is a step-text string list** (`parse_chain` → `[{step, result}]`,
   `handlers.py:1058/1677`). **No separate IR** — the label's "correct graph" uses this same shape.
4. **The D3 inventory does NOT match the live salience surface — and it is method-undercount, NOT drift**
   (DT's git probe, re-verified here). `git log 5f2b2a6..HEAD` is **empty** for timeline/publish/reconform/
   batch; the `30sec_21` count is **12 at the pin == 12 at HEAD**; the compound exemplar at `timeline.py:286-287`
   existed **at the pin**. So nothing drifted — **D3's sweep method missed an entire source kind from day one**:
   it swept `Field(description=…)` + `e.g.`/`Example call:` docstrings but **not** the `Operator query:` /
   `Tool call:` **few-shot exemplar blocks** (`timeline.py:146-148, 286-287, 687-688, 1100-1102`). *(This
   corrects my earlier "the surface GREW / drift confirmed" framing in commit `3fd5835` — it was wrong; the
   worry RELOCATES from docstring-drift to method-undercount, which is a stronger reason to re-derive.)*

## The 3a / 3b boundary

- **3a (this phase):** re-derive D3 (step 0, see Q4), build the labeled corpus, build + validate the detectors,
  validate the oracle. Ships the **instrument**, not a measurement.
- **3b (next):** run the validated oracle → translation-pass/substrate-pass verdict pairs + the
  example-fill-vs-grounded frequency that **ranks Phase 4** (by deduped defect, TF.2 §4).

---

## Q1 — What is a labeled "correct graph"? **LOCKED + world-state is a fifth field (DT).**

The verdict-pair is **locked** (Creative): without it the oracle cannot distinguish honest decline (PASS/GAP)
from translation failure (FAIL/NO-GAP) from FAIL/GAP. TF.2 made the distinction; TF.3a inherits it as its floor.

A label = the NL input plus **five** fields:
1. the **expected chain-step graph** (the step-text list a correct compile emits);
2. the **expected resolved params per step** — context-resolved refs labeled *as* unresolved-pending-dispatch
   (TF.1-CONTRACT §2; the corpus must not demand a concrete value where the contract resolves at dispatch);
3. the **expected verdict-pair** (translation {pass,fail} × substrate {pass,gap}, TF.2 §2);
4. the **per-param provenance** (`grounded-from-intent`/`from-context`/`filled-from-example`/`unresolved`);
5. **[DT add] the captured world-state the input was issued against.** The contextual class (§3.5) is
   **unscorable from text alone** — "rename *this sequence*" + open=`30sec_edit 21_publish` and the same text +
   open=`Hyundai_013_final` have **different correct graphs** (Creative's example). Without recorded world-state
   there is no ground truth for a contextual label. This ties to Q2: contextual cases need **fresh authored
   capture with world-state**, not replay of CR.1 traces (which never captured it).

## Q2 — How do we build the corpus? **Coverage-geometry, not size; ≥2-per-cell for Tier-2 (DT).**

"Is 32 enough?" is the wrong question (Creative) — the oracle **validates a taxonomy**, it doesn't estimate a
population parameter. DT converts size → **geometry**: the real question is *can every taxonomy cell be both
trained-against AND independently validated?*

- **Corpus adequacy [N] = coverage:** every **verdict-pair cell** (a–d), every **translation class** (five),
  every **multi-tag pattern observed in discovery** (defect #2 routing+extraction), every **D-series defect**.
- **The authoring target [N] is class-dependent (DT — this replaces the vague "≥1 per class×cell"):**
  - **Tier-2 classes** (grounding, entity-resolution, routing/wrong-selection) need **≥2 labeled instances per
    validated verdict-cell** — one to label/tune against, one to **hold out** (Q3). You cannot hold out from a
    cell with ≤1 instance; "≥1" understates exactly the cells that carry validation weight.
  - **Tier-1 classes** need **≥1** (the sanity instance — Q3).
- **Build method:** seed from the **32 well-formed traces**, augment with the **D-series/E2E-01 defects**
  (pre-diagnosed → cheapest high-value labels), and **author additional inputs (with world-state for contextual
  cases) until the adequacy + authoring targets above are met.** Do not reuse the comprehension `verdict`.

## Q3 — How do we validate the oracle? **Tier-1 = positive+negative unit pair; Tier-2 = held-out slice (DT reframe).**

The two tiers fail in different ways, so they need different checks — mirroring the §5 detection split:

- **Tier-1 (deterministic, substrate-observable):** the risk is a **logic bug** (wrong field, wrong marker,
  off-by-one). A statistical holdout **wouldn't catch that anyway**. The correct, cheap tool is a
  **known-positive + known-negative unit assertion per detector** — fires on the grounded defect instance,
  stays silent on a clean negative. This is **not a downgrade from holdout** for deterministic detectors; it's
  the right instrument for the logic-error surface. *(Don't open the trust-doctrine phase with an "exempt"
  class — give it the check that fits.)*
- **Tier-2 (ground-truth-dependent):** the risk is a **ground-truth error**. Full **held-out statistical
  slice** + a **pre-declared agreement threshold** (open: per-class, since Tier-2 classes differ in difficulty).
  This is why Q2's ≥2-per-cell authoring target exists — the held-out instance has to come from somewhere.

## Q4 — Example-fill FP rate — **BLOCKING PRECONDITION: re-derive D3 first (DT, the load-bearing redline).**

FP = the detector flags `filled-from-example` but the value was **genuinely grounded** and merely *happens* to
equal an example (a real `30sec_21`). But that FP number is **meaningless against an incomplete lift surface** —
and §grounded-reality-4 shows D3 **is** incomplete (method-undercount).

- **The compound exemplar is the killer evidence.** `timeline.py:286-287`:
  `Operator query: "rename the shots on 30sec_21 with prefix 'noise'"` /
  `Tool call: {"params": {"sequence_name": "30sec_21", "prefix": "noise"}}` — **both grounded defects (#1
  prefix→noise AND #3 sequence_name→30sec_21) in one liftable exemplar.** This is a **stronger causal candidate**
  for E2E-01's *compound* failure than "lift `30sec_21` from one tool + `noise` from another": the model can lift
  the **entire semantic pattern** from a single few-shot block. The richest part of the lift surface is the part
  D3 never enumerated.
- **Why it gates the keystone:** if 3a operationalizes D3-as-written, the detector misses lifts from the
  few-shot blocks → **false negatives** (the inverse of the FP worry), and the FP rate is measured against an
  **incomplete universe** → not the real number. The detector would inherit the exact milestone-flaw v1.13
  exists to prevent.
- **[N] Precondition (Orch-rewritten, both voices):** *TF.3a may NOT operationalize D3 directly. **Step 0** is
  re-deriving the salience surface with a sweep that includes ALL NL→tool demonstration kinds visible to
  compilation:* (i) `Field(description=…)`; (ii) docstrings (`e.g.`, `Example call:`); (iii) `Operator query:`
  exemplars; (iv) `Tool call:` exemplars; (v) any other NL→tool demonstration block. **Only after that refreshed
  inventory exists is it legitimate detector input / FP-study substrate.** Remaining sub-question: is the
  refreshed inventory machine-consumable, or does 3a operationalize it into a value-set? (`[[feedback-baseline-drift-invalidates-controls]]`
  + `[[feedback-ground-specs-in-actual-files]]`.)

## Q5 — Home + naming. **`translation_oracle/`; three-vocabulary rule at the field level (DT).**

One package, its own versioned schema, `__all__`-scoped, atomic-append JSONL, zero shared symbols with the
other two. **One artifact, one home (Creative, strongly endorsed):** DT's *reference corpus* = Creative's
*operator-facing provenance surface* = Phase-3's *oracle validation* are **projections of one asset** — the
labeled corpus, the per-param provenance signal, the validation outputs, the operator surface all live together;
splitting them re-fragments exactly the scattered translation layer v1.13 consolidates. Two sharpenings:

- **Three-vocabulary rule [N] (DT):** the provenance vocabulary (`grounded-from-intent`/`from-context`/
  `filled-from-example`/`unresolved`) must **not** reuse comprehension's verdict vocab (loved/hated/…) **or**
  corpus's divergence vocab. Three instruments, three distinct label vocabularies — "named distinctly forever"
  operationalized at the **schema field**, not just the package name.
- **Internal module split (DT):** keep the **corpus (data+schema)** and the **detector (logic)** as separate
  modules inside the package, so 3b can import them independently — even though they ship together per the
  one-artifact call.

---

## What TF.3a produces (after this settled discuss)

`TF.3a-PLAN.md`: **Step 0 = re-derive D3** across all five salience-surface source kinds (Q4 gating
precondition) → the refreshed, possibly machine-consumable example value-set. Then: the `translation_oracle/`
package with its corpus (data+schema, 5-field label incl. world-state — Q1/Q5) and detector (logic) modules; the
**coverage-complete** seeding + authoring method (≥2/Tier-2-cell, ≥1/Tier-1-class, world-state for contextual —
Q2); the oracle-validation protocol (**Tier-1 positive+negative unit pairs; Tier-2 held-out slice + threshold** —
Q3); the example-fill detector + its FP rate measured **against the refreshed surface** (Q4). **No 3b run, no
ranking, no Phase-4 fix.** 3a ships a *validated instrument*; 3b is the first time it's allowed to measure —
because by then anyone can say why they trust it.
