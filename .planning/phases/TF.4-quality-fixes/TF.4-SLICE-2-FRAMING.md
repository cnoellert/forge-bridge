# TF.4 Quality Fixes — Slice #2 Framing: space-mangle / entity-resolution value fidelity

**Status:** framing settled (writer's-room: Orch draft → DT → Creative → Orch grounding → DT/Creative redline). Code-ready. Three grounded flips folded; Flip 3 (param-location-blind detector) was required-before-commit.
**Date:** 2026-06-03. **Base:** `main @ f1ab8f5` (Slice #1 + post-gate pass shipped).
**Scope of this slice:** the **space-bearing sequence-name value mangle** only — the model emits a wrong `sequence_name` *value* in the compiled graph. Tool-misrouting on the same cases is the parked **routing** sibling. Live world-state validation + honest-decline are parked to the **desktop-wiring / contextual** slice.

This is the second TF.4 quality fix. It is ranked **#2 by live measurement** — space-mangle was the *measured dominant content failure* (stable 4/4 across post-gate runs, `TF.4-POSTGATE-FINDINGS.md`), ahead of `non_tool_step` (the prose slice). It is opened only after the post-gate re-measure, not on momentum.

---

## The defect (grounded)

Qualified space-bearing sequence names are mangled by **the model** (qwen2.5-coder:14b) at compile time. The compiled chain-step carries the wrong `sequence_name` *value*; the parser and the param extractor are faithful and uninvolved.

**Grounding chain (live evidence, post-gate `cases.jsonl`):**

1. The mangled value lives in `observed_graph` (the compiled chain-step), while `observed_resolved_params` is empty `{}` for every case. The value is the model's, not the extractor's.
2. `extract_explicit_params` (`_param_extract.py`) is UUID-/`project_*`-keyed only and **explicitly puts embedded-space names out of scope** (PR29: "names with embedded spaces must use the UUID form"). It returns `{}` for natural-language inputs — matching the empty resolved-params. **Not the mangler.**
3. The chain-step parser is **value-faithful**. The structured path (`_structured_compile_step_text`, `router.py:499`) renders the model's `arguments` dict verbatim via `" ".join(f"{key}={value}")` — no space/underscore transform. The text path (`parse_chain`, `_chain_parse.py`) only splits on `->` at depth-0 and `.strip()`s segments — never touches spaces inside a value, never drops tokens. **Not the mangler.**
4. **The decisive case — IDX 13.** Input `"rename this sequence with prefix tv"` contains **no `30sec` token at all**; `world_state.open_sequence = "30sec_edit 21"`. The model resolved the anaphor against world-state and emitted `sequence_name=30sec_21`. There is *no input text* for a parser or extractor to mangle — the value was synthesized and mangled by the model in the same breath. This forecloses every non-model hypothesis.

**Verdict (dual-lens, [[feedback-substrate-pass-translation-open]]):** the compiled chain-step graph carries the wrong value → **translation fails; substrate passes**. Within translation, it is the **model**, not the text→graph plumbing. This matches the room's existing `{substrate: pass, translation: fail}` labels on the whole set.

### The defect has two manifestations

The same value-mangle surfaces two ways from the same input `30sec_edit 21`:

- **Conflation / truncation** → `30sec_21` (IDX 5, 7). The `edit` token is *dropped*. No whitespace rule produces this — only the model, almost certainly conflating with the **real, distinct** sequence `30sec_21` that exists in the world (IDX 6 uses it as a legitimate input/expected value). **This silently dispatches the wrong sequence.**
- **Space→underscore** → `30sec_edit_21` (IDX 10, 11). All tokens preserved; classic model identifier-normalization. Neither parser converts spaces to underscores.

The model never quotes the name; the expected graph always does (`sequence_name="30sec_edit 21"`). The underlying model failure: **it does not treat a space-bearing entity name as a single quoted literal** — it either collapses the space or substitutes a near-looking known entity.

---

## Two grounded facts that reshaped the spine (DT + Creative, then Orch grounding)

The opening proposal (Orch) was *prevention + a deterministic live world-state validity detector (Prong B)*. Two grounded facts killed Prong B for this slice:

**Fact 1 — `30sec_21` is a real sequence (membership detection is conflation-blind).** IDX 6 proves it: input literally says `30sec_21`, expected `sequence_name="30sec_21"`; that row is `translation: fail` only because of a spurious trailing `commit`, *not* the name. So a label-free membership check waves `30sec_21` through as valid and dispatches the wrong sequence silently. The conflation half is catchable **only** by comparing to the labeled canonical — label-gated, not label-free.

**Fact 2 — `world_state` is a label field, unwired at the live compile path.** It is authored corpus data (`None` in production/post-gate); desktop is unwired at compile per TF.1-CONTRACT §4 (the chat handler imports no Flame client — reachable only at dispatch). A live world-state detector cannot run in this slice without wiring desktop-at-dispatch — which **is** the contextual slice. Building it here = two invariants + scope explosion.

So the spine reshapes from *prevention + deterministic-live-validation* to **prevention now + deterministic measurement from the labeled corpus + live guarantee deferred to the desktop-wiring slice.**

---

## Three post-grounding flips (Orch, grounded against live code + room redline)

Both DT and Creative built the deterministic surface on "lean on the **existing** 3a Tier-2 entity-resolution detector." Grounding `_detect.py` and the observed param-locations flipped three assumptions:

**Flip 1 — the Tier-2 entity-resolution detector does not exist.** `_detect.py` contains exactly one function, `compute_well_formed` (Tier-1 well-formedness); its docstring says "*Starts with* the WELL-FORMEDNESS detector." There is no entity-resolution detector — it was a taxonomy spec, never built. DT's plan-stage flag ("confirm it reads `expected_params`") resolves to: it isn't built. **Consequence — and this *raises* the slice's value, not its overhead:** the detector is the **entity-resolution Tier-2 instrument TF.3b needs regardless** to score the entity-resolution class at all. It is reusable milestone substrate (substrate-before-consumer), small and deterministic (~`compute_well_formed`-sized). Given the live fix is prompt-only with no deterministic backstop, **the detector is the only deterministic thing this slice ships — the banked headline deliverable.** The prompt is the speculative add-on.

**Flip 2 — the corpus labels for this class are inconsistent; the detector must be tag-blind, and the relabel is measurement integrity (not legibility).** Only IDX 10/11 carry `defect_ref: space-mangle` + `expected_classes: [routing, entity-resolution]`. The conflation cases 5/7 are tagged `serialization` with empty `expected_classes` — stale from the 3a serialization-focused labeling pass.

| IDX | input | exp `sequence_name` | observed param carrying the value | `defect_ref` | `expected_classes` |
|----|----|----|----|----|----|
| 5  | `30sec_edit 21` | `30sec_edit 21` | `sequence_name=30sec_21` (conflate)        | serialization | `[]` |
| 7  | `30sec_edit 21` | `30sec_edit 21` | `sequence_name=30sec_21` (conflate)        | serialization | `[]` |
| 10 | `30sec_edit 21` | `30sec_edit 21` | `project_id=30sec_edit_21` (under, routed) | space-mangle | `[routing, entity-resolution]` |
| 11 | `30sec_edit 21` | `30sec_edit 21` | `project_id=30sec_edit_21` (under, routed) | space-mangle | `[routing, entity-resolution]` |

A detector keyed on the **class tags** catches only 10/11 — reintroducing exactly the conflation blindness Fact 1 warned against. The relabel is therefore **measurement integrity, not cosmetics**: 5/7 tagged `serialization` while being entity-value failures means TF.3b's class-frequency count would *undercount entity-resolution and overcount serialization* — corrupting the very re-rank that justified this slice. Fold it, per-case and accurate, via `_authored.py` (the sanctioned locus — "correct the labels here, not in a hand-edited JSONL"; precedent: the 2026-06-02 6-case flip): **IDX 5 → `[routing, entity-resolution]`** (it mis-routed to `preview_start_frames`); **IDX 7 → `[entity-resolution]`** (the rename tool was right). It touches only `expected_classes` — never `expected_params`, never the frozen `ObservedTrace`. **Non-blocking for the bar** (the detector reads `expected_params`, already correct), but **folded for TF.3b integrity.**

**Flip 3 — the detector must be param-location-blind, not `sequence_name`-keyed (DT/Creative, required before commit).** The routing confound *relocates the mangled value into a different param*: IDX 10/11 emit `forge_list_shots project_id=30sec_edit_21` — there is **no `sequence_name` param** on those graphs. A comparator keyed on `observed.sequence_name` finds nothing to compare on 10/11 and reaches only 5/7 (**count 2**), contradicting the slice's claim of **4 value-fidelity cases** ([[feedback-counts-are-archaeology-grade]] — the 4 is a claim the detector has to actually *reach*). **Correct detector invariant:** *does the expected canonical entity string (`30sec_edit 21`) appear verbatim as **any** param value in the emitted graph?* — tag-blind, param-location-blind, exact (verbatim equality to the label, no similarity scoring → inside the no-fuzzy constraint, label-gated). That catches all 4 — 5/7 (`sequence_name=30sec_21` ≠ canonical), 10/11 (`project_id=30sec_edit_21` ≠ canonical) — and passes a correct `sequence_name="30sec_edit 21"`. **This is what makes the count of 4 coherent.**

---

## The reshaped spine (room-blessed: measurement built · prevention attempted · guarantee deferred)

Ordered by deliverable solidity, so the durable thing is not rhetorically overshadowed by the unprovable one.

**1. Built deterministic measurement — the headline (Metric A).** A new param-location-blind, verbatim-canonical comparator in `_detect.py` (Flip 3 invariant), + pos/neg unit pairs, replayed over the **4** frozen labeled value-fidelity cases (IDX 5, 7, 10, 11). Catches both manifestations (conflation + underscore) across the routing confound. Model-free (no Ollama/daemon/Flame). **This is deterministic measurement infrastructure TF.3b needs regardless — built and reusable, not slice overhead.** It is a measurement surface, *not* a runtime guarantee.

**2. Attempted prevention — Prong A prompt clause (cheap, unproven).** A compile-prompt clause: treat a space-bearing entity name as a single quoted literal — never collapse the space, never normalize to underscores, never substitute a near-looking known entity. Smoke assertion (presence) only; no deterministic live gate.

> **Honest ceiling — ship it now, do not gate on N≥3 + control.** Prong A has **no deterministic backstop** (unlike Slice #1's `normalize_chain_shape` corrector — there is *no faithful value* to reattach; it is wrong at emission), and its efficacy is *unprovable from re-capture* — Slice #1 already proved this (0/60 with salvage never firing → variance vs clause indistinguishable; we left it "likely helped, not proven"). Gating Prong A's ship on evidence our own prior slice showed re-capture cannot produce would be incoherent. **Ship it as cheap unproven prevention, retain it (no downside); N≥3 + control is an optional attribution follow-on, never a ship-gate.**

**3. Deferred guarantee — live guard (parked on the desktop-wiring / contextual slice).** Dispatch-time membership validity → honest-decline on an unknown sequence (deterministic, exact-membership, inside the no-fuzzy constraint — *decline, never correct*); + contextual "this sequence" resolution from the live desktop. Folds the parked **(c) honest-decline restoration** for this class, and absorbs **IDX 8** (expected-decline) and **IDX 13** (anaphora/sentinel). **Maturation condition: desktop wired at dispatch** ([[feedback-transitional-structure-naming]]).

The honest tri-part shape: **measurement (built, deterministic) + prevention (prompt, unproven) + guarantee (parked, needs desktop wiring).**

---

## Scope boundaries (held / parked, named)

- **Confound scope-out (endorsed).** IDX 10/11 carry `expected_classes: [routing, entity-resolution]` — the multi-tag lets the measurement isolate value-fidelity from tool-misroute. Slice #2 owns the **entity-resolution / value-fidelity** tag; the **routing** tag on the same case is the parked sibling (its own slice). The Metric does not conflate them.
- **IDX 8** (`set the start frames on 30sec_edit 21`, expected-decline, `expected_params: {}`) — not a value-fidelity case (no canonical to compare); parked to the honest-decline rider.
- **IDX 13** (anaphora `"rename this sequence"`, sentinel canonical `unresolved-pending-dispatch`) — contextual resolution, not clean value-fidelity; parked to the desktop-wiring slice.
- **Slice #1 carries** (still binding): the Prong-B salvage tripwire; the parked control trigger (flips mandatory if any motion proposes relying on Prong A's emission-rate win).

## Roadmap dependency flag (frequency vs enablement)

Space-mangle is **#2 by frequency** (measured dominant content failure), but its **deterministic live guarantee depends on #3's desktop-wiring**. Do **not** reorder on this. Ship the slice now on its tri-part honest shape — **measurement built (deterministic), prevention attempted (prompt, unproven), guarantee deferred (parked on desktop-wiring)** — and name the dependency so the framing does not promise in #2 what only #3's enabler can deliver. Frequency justifies the slice; the detector's reusability (TF.3b instrument) raises its value above the prompt alone.

## Constraints (binding)

Public `forge_bridge.__all__` = **19** (held); `translation_oracle.__all__` = **18** (the new detector is internal — confirm at plan stage whether it needs export; default: no); `pyproject` = `1.5.1`; SCHEMA_VERSION = "1" (no schema change — `expected_params`/`expected_classes` already exist); no new external libs; the frozen `ObservedTrace` corpus is **never** mutated (label corrections land in `_authored.py` only).

## Forward-pointers

- **Plan stage (`TF.4-SLICE-2-PLAN.md`):** the param-location-blind comparator fn signature (verbatim-canonical-appears-as-any-param-value) + unit-pair design (positives: all 4 mangle cases; negatives: correct `sequence_name="30sec_edit 21"`, canonical-as-substring-of-longer-correct-value guard); the per-case relabel of 5/7 (rides this slice, via `_authored.py`); whether a label-only corpus rebuild (re-pair authored labels onto frozen observations, **no live capture**) is needed for the JSONL to reflect the relabel; Prong-A clause wording; whether the detector needs `translation_oracle.__all__` export (default: no, internal).
- **Next slice (desktop-wiring / contextual):** absorbs the parked live guard, IDX 8, IDX 13, and the routing sibling's enabler.
