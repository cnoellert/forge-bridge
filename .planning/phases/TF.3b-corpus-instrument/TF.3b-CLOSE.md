# TF.3b Corpus-Instrument — CLOSE

**Status:** CLOSED 2026-06-03. **Base:** `main @ 2d404c2`. **Branch:** `codex/tf3b-corpus-instrument` (5 atomic commits `f35996e`→`88f0232`). **Ruling:** DT + Creative converged to close; orchestrator independently re-verified all five close-grade gates. Clean.

TF.3b completed the measurement instrument the milestone was built to trust: it restored the Label/ObservedTrace separation the schema's own lock declared, by **re-sourcing the well-formedness verdict from the observed trace through a real `emit()`** — not by editing the immutable corpora.

---

## Delivered (5 commits)

| # | step | mechanism | commit |
|---|---|---|---|
| 1 | observed-sourced `emit()` | new `_oracle.py`: `emit(observed, *, label=None) -> verdict_pair`; well-formedness + substrate are the label-free core, content (entity-fidelity) is the only label-gated axis | `f35996e` |
| 2 | re-source the count **through emit** | `_corpus.py:179` now counts `emit(c["observed"])["translation"] == "fail"` — no `expected_well_formed` read, no direct `observed["well_formed"]` read | `a014f31` |
| 3 | export the consumed detector | `detect_entity_value_fidelity` (emit's entity-class verdict) → `translation_oracle.__all__` 18→**19**; `emit` kept internal | `04ca50c` |
| 4 | mark `expected_well_formed` vestigial | re-doc at `_schema.py` + `_authored.py:43`; schema coupling validation kept intact (immutable corpora still validate) | `120a9c4` |
| 5 | observed verdict-frequency reader | `verdict_frequency()` tallies the four verdict-pair cells over labeled cases — the net-new observed-sourced ranking signal | `88f0232` |

## Verification (independently reproduced by orchestrator)

| gate | result |
|---|---|
| re-source through `emit()` | ✅ no `expected_well_formed` read, no direct `observed["well_formed"]` read in `_corpus.py` |
| count flips (decisive) | ✅ **frozen 6→6** (no-op = regression proof) · **postgate 6→3** (5 repaired leave / 2 newly-malformed enter / 1 unrepaired stays) |
| label-free core honored | ✅ `label=None` path returns before ever calling the detector |
| export rides consumption | ✅ `emit` calls `detect_entity_value_fidelity`; detector exported, `emit` internal |
| green + 0 mutations | ✅ 76 (oracle) / 788 (llm+console+oracle) green, reproduced; `reference/` untouched across all 5 commits |

Counts: `forge_bridge.__all__`=19 · `translation_oracle.__all__`=18→**19** · `pyproject`=1.5.1 · `SCHEMA_VERSION`="1" (no field added — comments only).

## The durable finding — an invariant tripwire to bank

`well_formedness_fails` is now computed as **label-free** `emit(...).translation == "fail"`. This equals well-formedness-fails **only because the label-free core never content-scores** — `translation=fail` in that path can arise *solely* from the well-formedness axis. **If a future change makes `emit` content-score without a label, this count silently begins miscounting content failures as well-formedness failures.** The re-sourced count's correctness is **load-bearing on the label-free-core invariant**. Recorded as a tripwire, not a defect — but any change to emit's label-free branch must re-verify the frozen-6 / postgate-3 numbers.

## The phase finding (Creative, elevated) — getting better by deleting a dependency

> **TF.3b does not repair `expected_well_formed`; it retires it as a verdict source.**

The `expected_well_formed` nit survived multiple slices because everyone assumed *bad label → fix label*. TF.3b shows the opposite: *bad label → stop reading the label*. That is a **different class of correction** — the system got better by **deleting a dependency, not repairing data**. The bidirectional 7/15 mismatch (5 repaired, 2 newly-malformed) is what forced it: a unidirectional mismatch is explainable as stale labels; a field that moves *both above and below* reality depending on manifestation is not stale data, it is the **wrong abstraction**. The measurement killed the "just update the labels" hypothesis. Recorded as a reusable pattern, not a one-off.

## Two framings retired (so a future reader doesn't go looking)

1. **S4 (the shared-label / per-manifestation problem) is retired by being made moot, not executed.** Re-sourcing makes `expected_well_formed` unread; the mislabel stops mattering. There is no "fix the nit" commit — there is a "stop reading the nit" commit (`a014f31`).
2. **The TranslationCase lock enforced itself.** verdict↔ObservedTrace (volatile) / intent↔Label (stable). `expected_well_formed` was a verdict smuggled into the label; the re-source restored the separation. The mismatch is **the lock detecting its own breach** — the milestone's recurring shape, a field measured to be other than it looked.

## Deferred (rolled up to the milestone bucket)
Two TF.3b-native deferrals, both **clean substrate-before-consumer** (the consumer that would need them isn't built — building now would be speculative), each with a named re-entry trigger in `v1.13-TRANSLATION-FIDELITY-MILESTONE-CLOSE.md`:
- **multi-salvage `+`-split counting** — re-enter when any report ranks salvage *reasons* by frequency (TF.3b ranks verdict-pairs, not salvage reasons; the `+`-joined reason is preserved losslessly in the record).
- **`defect_ref` manifestation split** — re-enter when any report needs manifestation-granular (conflation-vs-underscore) ranking; coverage only needs family-presence today.

These differ in kind from `non_tool_step` (a *measured failure class* that was a real close-blocker until dispositioned at TF.4) — these are accounting refinements with no consumer. Different severity; both get an explicit line.
