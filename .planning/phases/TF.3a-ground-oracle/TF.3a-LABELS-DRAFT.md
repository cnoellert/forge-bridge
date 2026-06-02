# TF.3a Step 4b — Labeled corpus DRAFT (for operator ratification)

**Status: DRAFT for review — NOT written to the live corpus.** These are *proposed* ground-truth labels; the
operator is the ground-truth authority (the oracle's trustworthiness rests on label correctness — I won't assert
them solo). Ratify / correct, then I write the ratified set via `append_case`.
**Grounded against:** the 32 well-formed seed traces (`comprehension-2026-06-01.jsonl`) + the live tool surface
(substrate pass/gap calls verified, not guessed) + the D-series.

**Label shape:** `(input → expected_graph · expected_params · verdict_pair{translation,substrate} ·
expected_classes · world_state · defect_ref)`. Verdict cells: (a) pass/pass · (b) fail/pass · (c) pass/gap
[honest-decline, REWARDED] · (d) fail/gap.

**Two structural facts about this draft (honest):**
1. **Seed traces are `seed-legibility`** → they can carry labels for **Tier-2** (grounding, entity-resolution)
   + the **verdict cells**, but per the `_corpus` guard they **cannot fill Tier-1 cells** (routing, extraction,
   contextual). Every Tier-1 row below is marked **⚡NEEDS-LIVE-CAPTURE** — its label is authorable now, but
   GREEN coverage waits on an instrumented capture (stack up).
2. The seed is **skewed** (one reads-dogfood session): no grounding/example-fill case exists in it — defect #1
   must be **authored** (§B).

---

## §A — Seed-derived labels (distinct inputs from the 32 traces)

### A1. Clean reads — cell (a), translation PASS / substrate PASS, no classes
| # | input | expected_graph | verdict | confidence |
|---|---|---|---|---|
| A1.1 | "What batch groups are on the desktop" | `flame_list_batch_groups {}` | (a) | HIGH — matches observed answered trace |
| A1.2 | "What is the name of the current desktop" | `flame_list_desktop {}` | (a) | HIGH |
| A1.3 | "What reels are on the desktop" | `flame_list_desktop` | (a) | MED — "reels" vs "desktop" tool; flag if reels want `flame_list_reel_*` |

### A2. Routing failures — cell (b), translation FAIL / substrate PASS, class `routing` ⚡NEEDS-LIVE-CAPTURE
*(capability exists; observed `graph=[]` = nothing selected = a routing failure)*
| # | input | expected_graph (intended) | classes | substrate basis | confidence |
|---|---|---|---|---|---|
| A2.1 | "list the projects" | `forge_list_projects {}` | `[routing]` | `forge_list_projects` exists | HIGH — cleanest routing-fail (trivial intent, empty graph) |
| A2.2 | "What's the duration in frames of 30sec_edit 21" | `flame_inspect_sequence_versions sequence_name=…` | `[routing, entity-resolution]` | seq-inspect exists | MED — multi-tag; the `30sec_edit 21` space-name is the entity half |

### A3. Entity-resolution — cell (b), class `entity-resolution` ⚡NEEDS-LIVE-CAPTURE (Tier-2 half label-gated)
| # | input | observed | expected | classes | confidence |
|---|---|---|---|---|---|
| A3.1 | "What iteration is gen_0460 on?" | `forge_get_batch_iterations` (aborted) | resolve `gen_0460` → iterations | `[entity-resolution]` | MED — `gen_0460` named entity unresolved; could carry `extraction` too |
| A3.2 | "What is the path to shot 10 on 30sec_edit 21?" | `graph=[]` | resolve shot 10 + seq → path | `[routing, entity-resolution]` | MED — **flag:** confirm a shot-path read capability exists (substrate) |

### A4. Contextual / stateful — class `contextual` ⚡NEEDS-LIVE-CAPTURE
| # | input | observed | analysis | confidence |
|---|---|---|---|---|
| A4.1 | "What is the name of the current batch" | `flame_list_batch_groups` (aborted) | "current batch" = state-ref; selected *list-all* instead of resolving *current* → `[contextual]`. **Verdict judgment:** translation FAIL/(b) if you call list-all a mis-translation; OR substrate-GAP/(d) since resolving "current" needs the unwired desktop (TF.1 §4). **Lean (d)** — the desktop gap is the real blocker. | LOW — operator call |

### A5. Capability gap — the R9 case (THE judgment call)
| # | input | observed | grounded fact | proposed verdict |
|---|---|---|---|---|
| A5.1 | "Does shot 10 on 30sec_edit 21 have a timewarp?" | `graph=[]` + `chain_aborted` | **NO timewarp-query capability exists** (grep `tools/`+`mcp/` = empty) | **(c) translation-PASS + substrate-GAP — REWARDED honest decline, no classes** — *IF the abort was an honest decline.* **⚠ THE judgment call:** did it decline honestly, or silently fail to route? Verdict hinges on it. Lean (c) given the gap is real; needs the abort mechanism checked at live capture (did `:407`/an honest-decline fire, or just empty?). |

---

## §B — Authored cases (not in the seed; needed for coverage)

| # | input (authored) | expected | classes | cell | defect_ref | capture |
|---|---|---|---|---|---|---|
| B1 | "rename the shots on 30sec_21 with prefix tv" *(operator-intended prefix)* | `flame_rename_shots sequence_name=30sec_21 prefix=tv` | `[grounding]` | (b) | defect-1 | ⚡LIVE — observed shows `prefix=noise` **lifted** from the example (the grounding defect). Tier-2 so seed-legibility *could* work, but no seed exists → author+capture |
| B2 | "rename shots on 30sec_edit 21 prefix noise" | correct rename graph w/ both params | `[routing, extraction]` | (b) | defect-2 | ⚡LIVE — the PR20 shadow (routing) + `prefix`/`sequence_name` unparsed (extraction). The multi-tag pattern. |
| B3 | "rename this sequence with prefix tv" | graph carrying unresolved `sequence_name=unresolved-pending-dispatch` | `[contextual]` | (b) | defect-3 | ⚡LIVE — "this sequence" needs desktop; `world_state={open_sequence: …}` holds ground truth |

---

## §C — Coverage check (what this draft reaches)

- **Verdict cells:** (a) A1 ✓ · (b) A2/A3/B ✓ · (c) A5.1 (pending judgment) · (d) A4.1 (pending judgment). **All four reachable** if A5.1→(c) and A4.1→(d) ratify.
- **Tier-2 classes:** grounding (B1) · entity-resolution (A3) — need ≥2 each; **author one more of each** (or accept B1 + a second grounding case).
- **Tier-1 classes (routing, extraction, contextual):** labels drafted, but **all ⚡NEED-LIVE-CAPTURE** — GREEN coverage is **blocked on bringing the stack up** (Ollama compile + Flame dispatch) to produce `instrumented-translation` traces. This is the expected structural consequence of the guard, not a gap in the draft.
- **D-series:** defect-1 (B1) · defect-2 (B2) · defect-3 (B3) ✓.
- **Multi-tag {routing,extraction}:** B2 ✓.

## §D — Open judgment calls for the operator (the ones I won't decide solo)
1. **A5.1 timewarp → (c) honest-decline or translation-FAIL?** The whole verdict-matrix (c)-cell rides on this. Capability gap is grounded-real; the question is whether the abort was *honest*.
2. **A4.1 "current batch" → (b) mis-translation or (d) desktop-gap?** Lean (d).
3. **A1.3 / "reels group" routing** — are `flame_list_desktop` for "reels" and `flame_get_batch_reels` for "reels group" correct, or mild routing issues?
4. **A3.2 shot-path** — confirm a shot-path read capability exists (sets substrate pass vs gap).
5. **Tier-2 second instances** — accept authoring a 2nd grounding + 2nd entity-resolution case for the ≥2 floor?

**On ratification:** correct/confirm the above, decide D1–D5, and I write the ratified Tier-2 + (a)/(c)/(d) cases to the corpus immediately; the Tier-1 ⚡ cases get written when their instrumented captures run (stack up).
