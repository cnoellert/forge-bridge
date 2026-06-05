# Context Pressure Instrument — Q3: Reject-Threshold Cost-Anchoring (blind precommit)

**Status:** DRAFT for room/operator ratification (Orch), 2026-06-04.
**Discipline:** This artifact MUST be ratified and committed **BEFORE** the typed-selection `resolvable_delta` is computed or looked at. Authored blind: at drafting, no delta (recall-plausibility or measured) has been seen. If the threshold is set after the number is known, it reverse-engineers to fit — which would void the measure-first gate. Ruling (ii) ratified 2026-06-04.

## 0. The decision this gates

After the capture-expansion (typed selection) lands and the corpus is re-captured, do we **build the typed-selection desktop resolver** (inject the selected typed object as the referent into the compile path), or **not**?

Symmetric by construction (the instrument must be able to say *don't build*): this artifact defines a **build trigger**, a **reject trigger**, and an explicit **more-data zone** between them.

## 1. The metric (precise)

Over the re-captured corpus, after authoring (`author_analysis`):

- **Confirmed contextual failure** = a record whose authored `analysis.failure_class` is non-null (`wrong_referent` or `unresolved_reference`), AND whose `flag_contextual_failure_candidates` fired (deictic prompt, dimension matched).
- **Typed-selection-resolvable** = a confirmed failure where authored `world_state_resolvable is True` AND `analysis.resolving_signal` names a **selection** signal (i.e. the captured `flame.selected` typed object of the op's required type would have supplied the correct referent). Loaded/playhead-only resolutions do NOT count toward the typed-selection metric (they are the fallback axis, separately reported).

```
typed_selection_resolvable_rate
  = (# confirmed failures resolvable via the SELECTED typed object)
  / (# confirmed contextual failures)
```

Read from `resolvable_delta(...)`'s `resolving_signal_ranking`, filtered to selection signals. Report N alongside the rate — a small N delta is **directional**, not the final gate (the first re-capture will be small; treat accordingly and re-measure as N grows).

## 2. Cost-anchoring (the reasoning, blind to the number)

Two asymmetries set the bar:

- **The resolver is THIN** (Creative's hooks-as-ontology read; capture is already done): the remaining build is "match the selected object's type to the op's required type, inject its `.name` as the referent into the compile path." The op→(context,type) ontology is mechanically derivable from the hooks (Capture-Model Spec §2). So **build cost is low** — which lowers the bar to justify it.
- **Failures are ratify-CAUGHT, not dangerous**: a `wrong_resolution` that reaches preview is caught by the operator at ratify (they see the wrong value and reject). So the cost of a contextual failure is **operator friction** (re-prompt / manual correction), not data corruption. This **raises** the bar somewhat (the pain is annoyance × frequency, not catastrophe) — but high-frequency friction on the dominant op class (sequence rename) is real drag worth removing if the signal explains enough of it.

Net: a thin build against ratify-caught friction means the bar is **a meaningful majority, not near-certainty** — we don't need typed selection to explain *almost all* failures, but it must explain *enough* that the thin resolver removes real, recurring friction rather than chasing a long tail of other causes (translation mangles, genuine ambiguity, no-selection cases).

## 3. The threshold (RECOMMENDED — room/operator ratifies the numbers)

Let `R = typed_selection_resolvable_rate` (§1).

| Zone | Condition | Ruling |
|---|---|---|
| **BUILD** | `R ≥ 0.50` | Typed selection is the referent for a majority of contextual failures → the thin resolver removes real recurring friction. Build it (dominant op class — sequence — first). |
| **MORE DATA** | `0.25 ≤ R < 0.50` | Signal is real but not dominant. Do NOT commit the general resolver. Optionally build the **thinnest** sequence-only inject and re-measure; grow N before re-deciding. |
| **REJECT** | `R < 0.25` | Typed selection explains too little — failures are dominated by other causes. Do NOT build the resolver; the captured signal does not justify even the thin cost. Phase X concludes "don't build (this signal)" and the instrument keeps measuring the other desktop signals (ruling iii — mission stays broad). |

Guardrails on reading R:
- **N gate:** with `N < ~10` confirmed failures, R is directional only — report it, do not trip BUILD/REJECT on it; re-measure as N grows. (The first re-capture will be small.)
- **Well-formedness precedes content:** a failure that never compiled (e.g. the `rename shots on X` translation errors, R5–R8) is NOT a contextual-resolution failure — exclude from the denominator (it's a translation failure, out of scope).
- R is the **typed-selection** rate specifically; the loaded/playhead-resolvable rate is reported separately and does NOT substitute (that axis is the demoted fallback).

## 4. What this threshold is NOT

- Not a quality bar for the resolver's *implementation* (that's a later eval).
- Not a re-scope of Phase X (ruling iii): REJECT means "this signal doesn't justify a build," not "desktop context doesn't matter" — the broader mission and other signals persist.
- Not authored against any seen delta (§0).

## 5. Ratification record (filled BEFORE computing the delta)

- [x] Threshold numbers ratified **as drafted** (BUILD ≥ 0.50 / MORE-DATA 0.25–0.50 / REJECT < 0.25) by: **operator (cnoellert)** on **2026-06-04**.
- [x] Committed to git: **this commit** establishes the blind-precommit timestamp (SHA in `git log`).
- [x] Confirmed: no `resolvable_delta` (recall-plausibility or measured) was viewed before this ratification — authored and ratified **blind**.

*Record complete. The typed-selection `resolvable_delta` may be computed and read against §3 — but only after the live re-capture produces it (the remaining gated step).*
