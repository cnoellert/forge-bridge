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

## §A — Seed-derived labels (EXACT tools, grounded against live signatures)

**Tool signatures verified** (`tools/*.py` Input models + `mcp/tools.py`): paramless reads take `{}`;
`flame_get_sequence_segments`/`flame_inspect_sequence_versions` take `sequence_name`; `flame_rename_shots`
needs `sequence_name`+`prefix` (both REQUIRED); `flame_get_batch_iterations` is **paramless + operates on the
currently-OPEN batch**; `forge_get_shot` needs a **Shot UUID** and its docstring routes Flame sequences to
`flame_get_sequence_segments`.

### A1. Clean reads — cell (a) PASS/PASS, no classes
| # | input | EXACT expected graph | verdict | note |
|---|---|---|---|---|
| A1.1 | "What batch groups are on the desktop" | `flame_list_batch_groups {}` | (a) | exact, paramless |
| A1.2 | "What is the name of the current desktop" | `flame_list_desktop {}` | (a) | exact, paramless |
| A1.3 | "What reels are on the desktop" | `flame_list_desktop {}` *(or `flame_list_reel_groups {}`)* | (a) | **⚑D3** which tool surfaces "reels"? |
| A1.4 | "What is the name of the current reels group" | `flame_get_batch_reels {}` *(observed)* | (a)? | **⚑D3** "reels group" routing — confirm |

### A2. Routing failures — cell (b) FAIL/PASS ⚡NEEDS-LIVE-CAPTURE
*(capability exists; observed `graph=[]` or a non-existent tool = the routing failure)*
| # | input | EXACT expected graph | classes | substrate basis |
|---|---|---|---|---|
| A2.1 | "list the projects" | `forge_list_projects {}` | `[routing]` | exists, paramless — **cleanest routing-fail** (trivial intent → empty graph) |
| A2.2 | "What's the duration in frames of 30sec_edit 21" | `flame_get_sequence_segments sequence_name="30sec_edit 21"` | `[routing, entity-resolution]` | seg tool exists; **⚑** duration derived from segments (alt `flame_inspect_sequence_versions`) |
| A2.3 | "What is the path to shot 10 on 30sec_edit 21?" | `flame_get_sequence_segments sequence_name="30sec_edit 21"` | `[routing, entity-resolution]` | **NOT `forge_get_shot`** (that needs a Shot UUID; the tool's own docstring routes Flame sequences here). "shot 10" = a segment in the result |
| A2.4 | "What's the duration of shot 10 on 30sec_edit 21?" | `flame_get_sequence_segments sequence_name="30sec_edit 21"` | `[routing, entity-resolution]` | same; segment 10's frame extent |
| A2.5 | "What iteration is gen_0460 on?" | `flame_open_batch_group batch_group_name="gen_0460"` → `flame_get_batch_iterations {}` | `[routing, entity-resolution]` | **2-STEP** (get_batch_iterations reads the *open* batch). Observed `forge_get_batch_iterations` = a **non-existent tool** (only `flame_`) → tool-unknown routing failure; `gen_0460` dropped = entity half |

### A3. Correct-tool reads that aborted — reclassified ⚡NEEDS-LIVE-CAPTURE
| # | input | observed | corrected analysis |
|---|---|---|---|
| A3.1 | "What is the name of the current batch" | `flame_list_batch_groups` (aborted) | **CORRECTION (grounded):** `flame_list_batch_groups` *does* return which batch is current (batch.py:18) → the tool selection is **CORRECT** = translation PASS. So this is **not** a contextual routing failure. The abort is a runtime/substrate matter → live capture classifies cell (likely (a) had it not aborted, or a substrate fault). **⚑D2** |

### A4. Capability gap — the R9 case (THE judgment call)
| # | input | observed | grounded fact | proposed verdict |
|---|---|---|---|---|
| A4.1 | "Does shot 10 on 30sec_edit 21 have a timewarp?" | `graph=[]` + `chain_aborted` | **NO timewarp-query capability** (grep `tools/`+`mcp/` empty) | **(c) translation-PASS + substrate-GAP — REWARDED honest decline, no classes** — *IF the abort was honest.* **⚠ D1:** honest decline vs silent routing fail? Verdict hinges on it; needs the live abort mechanism (did the `:407`/decline net fire, or just empty?). |

---

## §B — Authored cases (not in the seed; needed for coverage)

| # | input (authored) | EXACT expected graph | classes | cell | defect_ref | capture |
|---|---|---|---|---|---|---|
| B1 | "rename the shots on 30sec_21 with prefix tv" | `flame_rename_shots sequence_name="30sec_21" prefix="tv"` | `[grounding]` | (b) | defect-1 | ⚡LIVE — observed shows `prefix="noise"` **lifted** from the docstring example. (`RenameInput`: both REQUIRED) |
| B2 | "rename shots on 30sec_edit 21 prefix noise" | `flame_rename_shots sequence_name="30sec_edit 21" prefix="noise"` | `[routing, extraction]` | (b) | defect-2 | ⚡LIVE — PR20 shadow (routing) + `prefix`/`sequence_name` unparsed by the partial extractor (extraction). Multi-tag pattern. |
| B3 | "rename this sequence with prefix tv" | `flame_rename_shots sequence_name="unresolved-pending-dispatch" prefix="tv"` | `[contextual]` | (b) | defect-3 | ⚡LIVE — "this sequence" needs desktop; `world_state={"open_sequence": "<name>"}` holds ground truth |

---

## §C — Coverage check (what this draft reaches)

- **Verdict cells:** (a) A1 ✓ · (b) A2/A3/B ✓ · (c) A5.1 (pending judgment) · (d) A4.1 (pending judgment). **All four reachable** if A5.1→(c) and A4.1→(d) ratify.
- **Tier-2 classes:** grounding (B1) · entity-resolution (A3) — need ≥2 each; **author one more of each** (or accept B1 + a second grounding case).
- **Tier-1 classes (routing, extraction, contextual):** labels drafted, but **all ⚡NEED-LIVE-CAPTURE** — GREEN coverage is **blocked on bringing the stack up** (Ollama compile + Flame dispatch) to produce `instrumented-translation` traces. This is the expected structural consequence of the guard, not a gap in the draft.
- **D-series:** defect-1 (B1) · defect-2 (B2) · defect-3 (B3) ✓.
- **Multi-tag {routing,extraction}:** B2 ✓.

## §D — Open judgment calls for the operator (the ones I won't decide solo)
*(D4 from the prior draft is RESOLVED: shot-path = `flame_get_sequence_segments`, capability exists → substrate PASS.)*
1. **D1 — A4.1 timewarp → (c) honest-decline or translation-FAIL?** The whole verdict-matrix (c)-cell rides on this. The capability gap is grounded-real; the only question is whether the abort was *honest* (decline-net fired) vs silent — resolvable at live capture.
2. **D2 — A3.1 "current batch":** now reclassified to **translation-PASS** (correct tool surfaces the current batch). Confirm — and the abort's cause (why did a correct read abort?) is a live-capture question, not a labeling one.
3. **D3 — A1.3/A1.4 reels routing:** are `flame_list_desktop` (for "reels on the desktop") and `flame_get_batch_reels` (for "current reels group") the right reads, or mild routing issues? (alt: `flame_list_reel_groups`/`flame_list_reel_contents`.)
4. **D5 — Tier-2 second instances:** accept authoring a 2nd grounding + 2nd entity-resolution case for the ≥2 floor (A2.2/A2.3/A2.5 already give multiple entity-resolution instances; grounding has only B1 → needs a 2nd)?

**On ratification:** confirm/correct §A–§B, decide D1–D5, and I write the ratified Tier-2 + (a)/(c) cases to the corpus immediately; the Tier-1 ⚡ cases (routing/extraction/contextual) get written when their instrumented captures run (stack up).
