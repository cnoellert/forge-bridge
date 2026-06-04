# TF.3b Corpus-Instrument — CODE HANDOFF

**For:** an executor picking this up cold. Self-contained — you do not need the FRAMING. Read this, then `TF.3b-PLAN.md` if you want the rationale.

**Base:** `main @ 2d404c2` (clean). **Branch first** (do not commit to `main`).
**Package:** `forge_bridge/translation_oracle/`. **Tests:** `tests/translation_oracle/`.

---

## The one-sentence job
`expected_well_formed` on a Label is a per-capture **verdict** mistakenly authored as per-input **intent**; the real verdict already lives on `observed.well_formed`. Build the oracle's `emit()`, re-source the one reader through it, export the detector emit consumes, and mark the label field vestigial. **No corpus edits. No new schema field.**

## Hard constraints (CI-grade — violating any fails the phase)
- Frozen `reference/cases.jsonl` + all `reference/postgate*/cases.jsonl`: **0 byte mutations.**
- `SCHEMA_VERSION` stays `"1"`; any change is **additive** (this phase adds no field — comments only).
- `forge_bridge.__all__` stays **19** (translation_oracle is internal).
- `parse_chain` untouched. No new external libraries.
- Don't re-source the *other* coverage counts (see Anti-over-reach below).

---

## Step 1 — Build `emit()` → new file `forge_bridge/translation_oracle/_oracle.py`

Signature: `emit(observed: dict, *, label: dict | None = None) -> dict` returning a verdict-pair `{"translation": "pass"|"fail", "substrate": "pass"|"gap"}`.

**Three axes:**

| axis | source | label-gated? |
|---|---|---|
| well-formedness | **read** `observed["well_formed"]` (already computed at capture — do NOT recompute) | no (label-free core) |
| substrate (pass/gap) | `observed["outcome"]` / `observed["abort_reason"]` | no (label-free core) |
| content (translation pass/fail for *well-formed* graphs) | detectors over `observed["observed_graph"]` vs `label["expected_params"]` | **yes** — only when `label` present |

**Rules:**
- `observed["well_formed"] is False` ⇒ `translation = "fail"`, content **short-circuits** (do not score content on a malformed graph).
- `observed["well_formed"] is True` + **no label** ⇒ label-free core only: emit well-formedness + substrate; translation content axis **unscored** (this is the TranslationCase lock — never score content in label-free production).
- `observed["well_formed"] is True` + **label present** ⇒ score content. The entity-resolution class verdict **is** `detect_entity_value_fidelity(observed["observed_graph"], label["expected_params"])`.
- **Design invariant (close-graded):** the label-free core must run without a label. Do not make the whole verdict label-dependent.

**Resolve at build (one genuinely underspecified spot):** the substrate pass/gap mapping from `observed["outcome"]`/`abort_reason`. Ground it against the *actual* values present in the committed corpora before mapping — do not invent. Conservative default: clean execution ⇒ `pass`; capability-gap / abort ⇒ `gap`. For malformed graphs `translation=fail` regardless; substrate still derives from `outcome`.

**Test:** new `tests/translation_oracle/test_oracle.py` — (a) malformed observed ⇒ fail + content short-circuited; (b) well-formed + label ⇒ content scored; (c) well-formed + **no label** ⇒ core-only, content unscored.

## Step 2 — Re-source the one reader THROUGH `emit()`

File `forge_bridge/translation_oracle/_corpus.py`, current site **lines 177–179**:
```python
    well_formedness_fails = sum(
        1 for c in labeled if c["label"].get("expected_well_formed", True) is False
    )
```
Replace the predicate so the count is **"cases whose `emit(observed)` reports well-formed=False"** — i.e. derive via `emit`, not by reading the label, **and not by a direct inline `observed["well_formed"]` read.** The verdict derivation must live in `emit` (one named place). Close-grade gate #1 fails if `_corpus.py` reads `observed["well_formed"]` directly or keeps reading `expected_well_formed`.

**Test (pin both halves):** in `tests/translation_oracle/test_corpus.py`, assert `coverage_report(...)["well_formedness_fails"]` equals:
- **frozen corpus → 6** (no-op: label==observed on the calibration set — this is the regression-safety proof)
- **postgate corpus → 3** (was 6; 5 repaired leave, 2 newly-malformed enter, 1 unrepaired stays)

Load corpora via `read_cases(corpus_dir=REFERENCE_DIR / "...")`. (`REFERENCE_DIR` is exported.)

## Step 3 — Export `detect_entity_value_fidelity`

`forge_bridge/translation_oracle/__init__.py`: add to the `_detect` import and to `__all__`.
- Current `_detect` import line: `from forge_bridge.translation_oracle._detect import compute_well_formed`
- → `from forge_bridge.translation_oracle._detect import compute_well_formed, detect_entity_value_fidelity`
- Add `"detect_entity_value_fidelity",` to `__all__` (keep the existing alpha-ish ordering).

**`translation_oracle.__all__`: 18 → 19.** Update any test that asserts the export count.

**Build-time check:** confirm `emit()` actually calls `detect_entity_value_fidelity`. If a scoring shortcut bypasses it, keep the detector internal and flag it — export must ride real consumption.

**Open decision (settle here, state explicitly):** whether to also export `emit` itself. Nothing *outside* `translation_oracle` consumes it yet → strict substrate-before-consumer says keep internal (`18→19`). Exporting emit makes it `18→20`. Pick one, put the resulting number in the commit message and the close doc. Do not let it drift silently.

## Step 4 — Re-document `expected_well_formed` vestigial (NO new field)

- `_schema.py` (around the well-formedness-tier comment at ~line 186–214): add a block — *"VESTIGIAL: original frozen-capture verdict snapshot. Do NOT read for a well-formedness verdict — that lives on `observed.well_formed`, read via `emit()`. Retained because corpora are immutable and the schema coupling still validates it on author."* **Keep the coupling validation intact** (immutable corpora must still pass `validate_translation_case`).
- `_authored.py:43` (the `"expected_well_formed": well_formed,` stamp): one-line comment pointing to the same. The writer still emits the field (schema self-consistency); readers ignore it.
- **No `intended_well_formed` field.** Intent is degenerate (always-True for compilable inputs; the non-compilable case is already encoded by `expected_verdict_pair.substrate=gap`). Re-document in place.

## Step 5 — Frequency-that-ranks-the-next-phase (emit's net-new output)

Run `emit()` over a labeled corpus to produce per-class **observed-sourced** manifestation frequency (the input that ranks the next phase's work). Scope **minimal-but-complete-for-scoring** — the verdict-pair frequency, not gold-plated analytics. This is distinct from `coverage_report`'s coverage counts (those stay label-sourced; see below).

---

## Anti-over-reach guard (the failure mode to avoid)
Only `well_formedness_fails` is mis-sourced. The other `coverage_report` counts — `cell_counts` (verdict-pair), `class_status`/`multitag` (`expected_classes`), `defect_counts` (`defect_ref`) — answer *"is this represented in the validation set?"* = **coverage = intent, correctly label-sourced.** **Do NOT re-source them.** Re-source exactly one reader (Step 2); add frequency as new emit output (Step 5).

## Close-grade gates (verification before close)
1. Re-source goes **through `emit()`** — grep `_corpus.py`: no direct `observed["well_formed"]` read, no `expected_well_formed` read.
2. Count flips: frozen **6→6**, postgate **6→3**, pinned in `test_corpus.py`.
3. Label-free core honored — emit emits well-formedness + substrate with `label=None`; content scored only with a label.
4. `detect_entity_value_fidelity` exported iff emit calls it; `__all__` number stated.
5. Full suite green (it was 754 green at TF.4 close). 0 corpus mutations (`git diff --stat` shows no `reference/**` changes).

## Counts ledger to carry into the close doc
`forge_bridge.__all__`=19 · `translation_oracle.__all__`=**18→19** (or 20 if emit exported — state which) · `pyproject`=1.5.1 · `SCHEMA_VERSION`="1" · 0 corpus mutations.

## Commit cadence
S1 emit + test · S2 re-source + pinned count test · S3 export + `__all__` bump · S4 vestigial re-doc · S5 frequency. Atomic; green before each next. Commit-message trailer:
`Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`

## Bring-up note
No live capture needed — this phase operates entirely on the **committed** corpora under `reference/`. (`run_captures.py` is standalone Ollama + in-process mcp if you ever need a fresh capture, but TF.3b does not.) Editable-install anchor check before any worktree/checkout housekeeping per CLAUDE.md.
