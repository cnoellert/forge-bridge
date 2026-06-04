# TF.3b Corpus-Instrument — PLAN (post DT/Creative convergence)

**Base:** `main @ 2d404c2` (TF.4 CLOSED, clean, pushed). **Ratification:** DT and Creative returned identical redlines — a clean lock across all four Qs. This plan opens on that convergence; grounding below sharpened two acceptance numbers and surfaced one site the redline didn't name.

---

## The locked diagnosis (convergence, verbatim shape)

`expected_well_formed` is a **verdict mis-typed as intent** — a per-`(input,observation)` fact smuggled into the per-input Label. Proven by the **7/15 bidirectional** label↔observed mismatch in `postgate` (5 repaired by Slice #1, 2 newly-malformed), and foreclosed from re-labeling by two walls: the schema *couples* `expected_well_formed`+`translation`+`expected_classes` (single-field flip is **schema-invalid**), and the corpora are **immutable**. The verdict already lives correctly on `ObservedTrace.well_formed`. **Fix = re-source the reader through `emit()`, mark the label field vestigial. No corpus edit, no new field.**

Two framings recorded so a future reader doesn't go looking for the wrong commit:

1. **S4 is retired by being made moot, not executed.** Re-sourcing makes `expected_well_formed` unread; the mislabel stops mattering. There is no "fix the nit" commit — there is a "stop reading the nit" commit.
2. **This is the TranslationCase lock enforcing itself.** The lock set verdict↔ObservedTrace (volatile) / intent↔Label (stable). `expected_well_formed` broke its own contract; the re-source restores it. The milestone's recurring shape — a field measured to be other than it looked.

## Grounding results (read-before-scoping — two refinements to the convergence)

- **DT's single-site claim HOLDS.** The only verdict-*reader* of `expected_well_formed` outside the schema is `_corpus.py:178`. Confirmed by grep over `forge_bridge/**/*.py`.
- **Second site (writer, not reader): `_authored.py:43`** stamps `"expected_well_formed": well_formed` when authoring a case. Does not violate the single-reader claim (it writes, doesn't read for a verdict), but it is the **origin of the conflation** and a plan touch-point: it must keep emitting the field (the schema coupling still validates it on author), and it is the natural home for the "vestigial / do-not-read" re-documentation (Step 4).
- **emit()/frequency genuinely absent — CONFIRMED.** `_oracle.py` does not exist; no observed-sourced emit or frequency reader anywhere in the package. emit() is net-new, the phase deliverable, not a re-source of an existing path.
- **The anti-over-reach boundary (load-bearing for the executor).** Only `well_formedness_fails` is mis-sourced. `coverage_report`'s *other* label-sourced counts — `cell_counts` (verdict-pair), `class_status`/`multitag` (expected_classes), `defect_counts` (defect_ref) — answer **"is this represented in the validation set?"** (coverage = intent, correctly label-sourced), NOT **"how often does it manifest now?"** (frequency = verdict, emit's net-new observed-sourced output). **Do not re-source the coverage counts.** Re-source exactly one reader; add frequency as a new emit consumer.

## Acceptance numbers (concrete, grounded)

| corpus | `well_formedness_fails` label-sourced (before) | observed-sourced via emit (after) | meaning |
|---|---|---|---|
| **frozen** | 6 | **6** (Δ=0) | re-source is a **no-op on the calibration set** — the regression-safety proof |
| **postgate** | 6 | **3** (Δ=−3) | 5 repaired (idx 5–9) leave · 2 newly-malformed (idx 11–12) enter · 1 unrepaired (idx 4) stays |

The frozen no-op and the postgate flip are the two halves of the same gate: re-sourcing must change nothing where label==observed, and must track observed where they diverge.

---

## Steps

### Step 1 — Build `emit()` in `_oracle.py` (the phase deliverable)
`emit(observed, *, label=None) -> verdict_pair`. The verdict-pair is the deliverable; well-formedness is its cheap first cut, content is the detector cut.
- **Well-formedness axis (label-free core):** straight from `observed.well_formed` (already computed by `compute_well_formed` at capture). Malformed ⇒ `translation=fail`, content short-circuits.
- **Substrate axis (label-free):** from `observed.outcome` / abort markers (pass vs capability-gap).
- **Content axis (label-gated):** for well-formed graphs, score the content classes via detectors. Entity-resolution class = `detect_entity_value_fidelity(observed_graph, label.expected_params)`. **Label-gated by construction** (needs `expected_params` canonical) — emit scores content **only when a label is present**; in label-free production the content axis is unscored. This is the TranslationCase lock honored, not bypassed.
- **Design invariant (will be close-graded):** the label-free core (well-formedness + substrate) must emit *without* a label; only content scoring engages the label. Do not make the whole verdict label-dependent.
- Tests: `tests/translation_oracle/test_oracle.py` (new) — emit over a malformed observed ⇒ fail/short-circuit; over a well-formed labeled case ⇒ content-scored; over well-formed **label-free** ⇒ core-only, content unscored.

### Step 2 — Re-source `coverage_report` well-formedness count **through `emit()`**
- `_corpus.py:178` stops reading `label.expected_well_formed`; the count becomes "cases whose `emit(observed)` reports well-formed=False." **Through emit, not a direct `observed.well_formed` read** — DT's close-grade: the verdict derivation must live in one named place (emit), not be re-buried inline in the coverage reader.
- Verify the acceptance table: frozen stays 6 (no-op), postgate flips to 3.
- Tests: update `tests/translation_oracle/test_corpus.py` — assert frozen=6 / postgate=3 explicitly (the regression-safety no-op + the flip are both pinned).

### Step 3 — Export `detect_entity_value_fidelity` (oracle `__all__` 18 → 19)
- Rides Step 1: emit() is the real consumer. **Confirm at build that emit actually calls it** — if a scoring shortcut bypasses the detector, keep it internal and revisit (Creative + DT caveat). It should call it; the detector's entire purpose is emit's entity-class verdict.
- This closes the Slice-#2 E2 sibling asymmetry: `compute_well_formed` exported because capture consumes it; `detect_entity_value_fidelity` exported because emit consumes it. Both exports earn their place by consumption ([[feedback-substrate-before-consumer-landing]]).
- `detect_entity_value_fidelity` is already under test (`test_detect.py`, `test_tf4_entity_value_fidelity_bar.py`) — export is low-risk.

### Step 4 — Re-document `expected_well_formed` as vestigial (no new field)
- `_schema.py`: keep the field + its coupling validation (immutable corpora must still validate); add a docstring/comment block — **"VESTIGIAL: the original frozen-capture verdict snapshot. Do NOT read for a well-formedness verdict — the verdict lives on `observed.well_formed`, read via `emit()`. Retained because the corpora are immutable and the schema coupling still validates it on author."**
- `_authored.py:43`: comment at the stamp site pointing to the same — the writer still emits it (schema requires self-consistency), readers ignore it.
- **No `intended_well_formed` field.** Falsification (convergence): intent is degenerate — always-True for compilable inputs, and the non-compilable case is already encoded by `expected_verdict_pair.substrate=gap`. A new field would be a low-value near-constant column. Re-document in place; do not replace.

### Step 5 — Frequency-that-ranks-Phase-4 (emit's net-new observed-sourced output)
- The re-rank input: run `emit()` over a labeled corpus → per-class manifestation frequency (observed-sourced, NOT the label-sourced coverage counts). Scope **minimal-but-complete-for-3b-scoring** — the full verdict-pair frequency that ranks the next phase's work, not gold-plated analytics.
- This is where the postgate "5-repaired/2-newly-malformed" reality becomes a ranking signal rather than a stale label tally.

---

## Goal-backward verification (the two gates DT will close-grade)

1. **Re-source goes THROUGH `emit()`** — `coverage_report` does not contain a direct `observed.well_formed` read; the verdict derivation is named once, in `_oracle.emit`. (Anti-re-burying.)
2. **The count flips to the mismatch reality** — `well_formedness_fails`: frozen **6→6** (no-op), postgate **6→3** (5 leave / 2 enter / 1 stays). Pinned in `test_corpus.py`.
3. **Label-free core honored** — emit emits well-formedness + substrate without a label; content scoring engages only on labeled cases (the TranslationCase lock).
4. **Export rides real consumption** — `detect_entity_value_fidelity` exported iff emit calls it (verified at build).

## Out of scope (deferred bucket — nothing measured vanishes)
- `non_tool_step` deterministic repair (non-recoverable well-formedness; detector-only — TF.4 disposition stands).
- `space-mangle` deterministic guarantee (needs external entity ground-truth → desktop-wiring, gated).
- desktop-wiring / contextual Shape-A (investigation-gated).
- honest-decline-on-gap (model/routing change, not model-free).
- `_oracle.py` beyond the minimal-but-complete verdict-pair emit (no gold-plated analytics this phase).
- Re-sourcing the coverage counts (`cell`/`class`/`multitag`/`defect`) — they are validation-set coverage (intent), correctly label-sourced; **explicitly NOT touched**.

## Counts ledger (archaeology-grade — propagate everywhere)
- `forge_bridge.__all__` = **19** (unchanged — `translation_oracle` is internal).
- `translation_oracle.__all__` = **18 → 19** (adds `detect_entity_value_fidelity`; if emit is also exported, 18 → 20 — state it explicitly at the export step, do not let it drift silently).
- `pyproject` = `1.5.1`. `SCHEMA_VERSION` = `"1"` (every change additive; no field added, one field re-documented — schema bytes unchanged except comments).
- Frozen + all `reference/postgate*` corpora: **0 mutations**. `parse_chain`: untouched. No new libs.

## Commit cadence
S1 emit() + test · S2 re-source + pinned count test · S3 export + `__all__` bump · S4 vestigial re-doc · S5 frequency. Each atomic; each green before the next. Close doc when the two gates verify.
