# TF.3b Corpus-Instrument — Orch Framing (→ DT / Creative redline)

**Base:** `main @ 2d404c2` (TF.4 CLOSED, clean, pushed). **Phase kind:** measurement-instrument, not runtime. TF.4 fixed the runtime defects the corpus *measured*; TF.3b fixes the **corpus that does the measuring** — the instrument drifted out of true the moment Slice #1 repaired a defect, because the labels couldn't follow.

This is an Orch framing pass. I lead with a position on each open question per the room's cadence; DT grounds, Creative pressures experience, then we converge before any PLAN. One structural seam (the schema coupling) gets explicit caution below — it is the place a wrong move is expensive.

---

## The trigger, grounded (not archaeology — live corpus reads)

The S4 deposit (`6bb2af3`) said: *the shared authored label is right-for-frozen / wrong-for-postgate across `expected_well_formed` + `defect_ref` + `expected_classes`; no single-field edit is correct for both corpora.* That was a prediction off a consumer read. It is now **measured**:

- Labels are **15/15 byte-identical** between the frozen corpus and `postgate` (`expected_well_formed` + `defect_ref`). The label was authored once against the frozen capture and **mechanically stamped onto every re-capture**.
- After Slice #1 repaired detached-args, **7 of 15 `postgate` cases have a label↔observed well-formedness mismatch**:
  - idx 5–9 (`list the projects`-family serialization): label `expected_well_formed=False`, observed `well_formed=True` — *the fix worked, the label didn't notice.*
  - idx 11–12 (`shot 10 duration`, `gen_0460 iteration`): label `expected_well_formed=True`, observed `well_formed=False` — *a different, intermittent malformation appeared.*

The mismatch is **bidirectional**, which kills the tempting read that "the labels are just stale and need bumping forward." They are not stale — **they are mis-typed.** They are authored as a per-INPUT constant but describe a per-`(input, observation)` event.

## The diagnosis (my lean — the load-bearing claim for redline)

The schema's own docstring says *"the Label is an authored statement of what it **should** have done."* The frozen labels do not do that. `expected_well_formed=False` on `list the projects` does not mean "this input **should** produce a malformed graph" (absurd — no input should). It means "this capture **was** malformed." **The label conflates intent ("should", per-input, stable) with verdict ("was", per-observation, volatile).**

The verdict already has a correct home: `ObservedTrace.well_formed`, computed by `compute_well_formed` from the actual trace. The label's `expected_well_formed` is a **redundant copy of the verdict wearing intent's clothes** — and a copy is exactly the thing that cannot stay true across two corpora whose observeds diverge.

So the three carried items are one root with three faces:

| carried item | face of the root |
|---|---|
| shared-label / per-manifestation representation | the label conflates intent vs verdict |
| class-frequency counting hygiene | `coverage_report` sources frequency/tier-count from the **authored label**, not the **observed manifestation** |
| `detect_entity_value_fidelity` export | the verdict-from-observed path (detectors) is what *should* feed counting — its consumption decides the export |

## My lean on the fix — re-source, don't re-label

**Do not flip labels. Re-source the readers to the ObservedTrace, and additively narrow the Label to intent.**

Two reasons re-labeling is the wrong instinct, one of them a hard wall:

1. **The hard wall (the structural seam — caution here):** `validate_translation_case` *couples* `expected_well_formed` + `translation` + `expected_classes` (`_schema.py:185–214`). Flipping idx 5 `expected_well_formed=False→True` while `translation` stays `fail` forces `expected_classes` non-empty (`:205`) — but the serialization cases have empty content classes by construction (malformed short-circuits content). **A single-field flip is schema-invalid.** Proven, not asserted.
2. **The immutability wall:** frozen + all `reference/postgate*` corpora are NEVER mutated (binding). Even if a flip were legal, the corpora that carry the mismatch can't be edited. Re-labeling is not merely hard — it is **out of bounds**.

What re-sourcing means concretely (proposal, for redline — not yet a plan):

- **Tier count + class frequency read the ObservedTrace, not the Label.** `coverage_report`'s `well_formedness_fails` currently counts `label.expected_well_formed is False` (`_corpus.py:177`). The well-formedness *tier* is a property of the **trace**, so it should count `observed.well_formed is False`. Same re-sourcing logic for class frequency feeding the re-rank. This *is* the "counting hygiene" item — it was never a tallying nit, it's a **source-of-truth correction**.
- **The Label keeps a stable, additive intent field** (name TBD — e.g. `intended_well_formed`, defaulting to the legacy field so SCHEMA_VERSION stays `"1"` additive-only). Intent for every one of these inputs is "well-formed, correctly routed." The legacy `expected_well_formed` is retained, re-documented as *the original frozen verdict snapshot*, and explicitly NOT the tier-count source going forward.
- **Per-manifestation falls out for free.** Once the verdict is sourced from `observed`, each corpus carries its own correct verdict automatically (it always did — `observed.well_formed` was right in all 7 mismatch cases). There is no per-corpus label to author; the manifestation *is* the observed trace.

If this lean holds, the "shared-label problem" dissolves into "we were reading the wrong field," which is a much smaller and fully in-bounds change than re-authoring labels or versioning the schema.

**The alternative I want DT/Creative to pressure:** carry a genuinely per-manifestation *label* (a label that varies per corpus). I currently reject it — it re-authors the volatile verdict into the place (`label`) that the immutability constraint freezes, and it leaves `observed.well_formed` as a redundant second source. But if there's a verdict the observed trace *cannot* derive (a "should" that needs human authorship and varies by manifestation), re-sourcing won't cover it and we'd need per-manifestation labels after all. I haven't found such a field; name one if it exists.

## The finding the cursor didn't carry — the oracle emit() is unbuilt

`_oracle.py` **does not exist.** TF.3a Step 6 ("Oracle assembly — `emit(observed) → verdict_pair`") was never built; `__init__.__all__` (18) exports detectors (`compute_well_formed`) and the corpus layer, but no emit function. The corpus is validated today by `coverage_report` occupancy, not by an emit-and-compare oracle.

This matters to TF.3b because **re-sourcing IS the emit path.** "Derive the well-formedness verdict from the ObservedTrace and compare to intent" is precisely what `emit()` would formalize. So the scope question is sharp: does TF.3b (a) build the minimal `emit(observed)→verdict_pair` as the principled home for re-sourcing, or (b) re-source `coverage_report` directly and leave full oracle-assembly deferred? I lean (a)-minimal — give the re-sourced verdict one named function instead of inlining it into the coverage reader — but it's a real fork for the room.

## Scope boundary (proposed)

**In:** the representation root and its three faces — verdict re-sourcing (counting hygiene), the additive intent field, `detect_entity_value_fidelity` export *iff* TF.3b consumes it, and the minimal emit-verdict path if the room takes fork (a).

**Out (deferred bucket — explicit, nothing measured vanishes):**
- `non_tool_step` deterministic repair (non-recoverable well-formedness; detector-only — TF.4 disposition stands).
- `space-mangle` deterministic guarantee (needs external entity ground-truth → desktop-wiring, gated).
- desktop-wiring / contextual Shape-A (investigation-gated; postgate-15 didn't promote it).
- honest-decline-on-gap (model/routing change, not model-free).
- full `_oracle.py` assembly beyond the minimal emit path (if room takes fork (b)).

## Success criteria — per native layer, never conflated

1. **Instrument-truth (the phase's reason to exist):** `coverage_report` over any corpus reports the well-formedness tier count and class frequencies that match that corpus's **observed** manifestations — verified against the 7 known `postgate` mismatch cases (the count must move when re-sourced, and match observed, not label).
2. **In-bounds invariant:** zero mutations to frozen or `reference/postgate*`; SCHEMA_VERSION stays `"1"` (every change additive); `parse_chain` untouched; no new libs.
3. **Representation correctness:** intent and verdict are separately addressable in the schema, documented so they cannot re-conflate; the legacy field is retained and re-roled, not flipped.
4. **Counts hold:** `forge_bridge.__all__` = 19; `translation_oracle.__all__` = 18 **unless** `detect_entity_value_fidelity` / `emit` are consumed-and-exported this phase, in which case the delta is stated explicitly and propagated everywhere (counts are archaeology-grade).

## Open questions for the redline

- **Q1 (the seam):** re-source readers to `observed` + additive intent field — or genuinely per-manifestation labels? I lean re-source; name a verdict `observed` can't derive if you'd overturn it.
- **Q2 (oracle scope):** minimal `emit()` as the home for re-sourcing (my lean), or inline into `coverage_report` and defer `_oracle.py`?
- **Q3 (intent field):** add `intended_well_formed` (additive, defaults to legacy) vs re-document the existing field in place? Additive is safer for the immutable corpora (they validate unchanged); confirm it doesn't create two fields readers must reconcile forever.
- **Q4 (export trigger):** does TF.3b's counting actually consume `detect_entity_value_fidelity`? If the re-rank's class frequency needs entity-fidelity tallies, yes → export; if not, it stays internal per substrate-before-consumer.

## Forward-pointers (named, not lost)
- TF.3a Step 6 oracle-assembly gap → folded into Q2 above, not silently dropped.
- `_DSERIES_DEFECTS` (`_corpus.py:56`) and `_DISCOVERY_MULTITAG` are also label-sourced — if Q1 lands on re-sourcing, audit whether defect/multi-tag frequency has the same mis-source (likely yes; `defect_ref` is a label field). Flagged for the PLAN's grounding pass.
- Memory ties: [[feedback-wellformedness-precedes-content]] (gate-then-content; this phase says verdict-lives-on-observed, intent-lives-on-label — a layering claim about *where* well-formedness is recorded, not *when* it's evaluated), [[feedback-substrate-before-consumer-landing]] (export-on-consumption), [[feedback-counts-are-archaeology-grade]], [[feedback-ground-specs-in-actual-files]] (this framing read all 8 corpora + the schema before scoping).
