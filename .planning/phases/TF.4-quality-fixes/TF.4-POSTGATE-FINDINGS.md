# TF.4 Post-Gate — Findings (the measure-first payoff, again)

**Run:** 2026-06-02, `qwen2.5-coder:14b` @ d355a88 (in-process compile+normalize; Flame `:9999`; pg `:7533`). 15 live cases → `reference/postgate/cases.jsonl`. Baseline = frozen `reference/cases.jsonl` (15 cases, 4 `detached_args`), byte-preserved.

**Headline: the count says "4 detached_args → 0." The substrate says the win is model-side (NOT the salvage), it is not monotonic (2 regressions appeared), and the content failures relocated.** Do not read "0 detached_args" as "the fix worked in the wild." That's the exact trap measure-first exists to catch.

---

## Finding 1 — Prong B never fired. The live recovery is model-side, NOT the deterministic salvage.

`salvage_applied` tally across the 15 postgate cases: **`True` (Prong B fired): 0** · `False` (normalize ran, model didn't detach): 11 · `None` (no normalize attempt): 4.

All four previously-`detached_args` cases are now `well_formed=True` **with `salvage_applied=False`** — i.e. the model emitted clean inline args this run, so the salvage had nothing to repair. **The load-bearing Prong B has ZERO live firings.** This is the 2×2 quadrant we explicitly named a success — *"prompt succeeds + salvage never fires = success"* — but it carries a sharp caveat: the in-the-wild well-formedness is currently carried entirely by **model behavior (Prong A and/or sampling variance)**, and the deterministic guarantee (Prong B) has no live evidence here. Its correctness still holds — the frozen-corpus replay bar proves it deterministically — but the wild did not exercise it.

**We cannot attribute Prong A vs. variance from a single run** ([[feedback-baseline-drift-invalidates-controls]]). At temp 0.1 qwen is near- but not fully-deterministic; one capture is one sample.

## Finding 2 — Well-formedness is NOT monotonically improved. Two cases REGRESSED.

| case | baseline | postgate | likely cause |
|---|---|---|---|
| duration of shot 10 on 30sec_edit 21 | `well_formed=True` (forge_list_shots → forge_get_shot) | **`compile_error` / `non_tool_step`** — graph = `[forge_list_shots…, "filter status=…", "find shot_id=shot_10", forge_get_shot…, "extract cut_info duration"]` (prose pseudo-steps) | plausibly Prong-A grammar nudging toward pseudo-code — **unconfirmed** |
| gen_0460 iteration | `well_formed=True` (forge_get_batch_iterations → format_result) | **`compile_error` / `invalid_chain_shape`** — `CompileBudgetExceeded`, empty graph | likely variance / infra timeout |

So the prompt-grammar change (Prong A) may have *helped* detached-args while *hurting* other cases — a classic intervention-with-side-effects. One regression looks grammar-shaped (prose steps); one looks like a timeout. **Neither is attributable from one run.**

**S2 (capture-on-re-raise) already paid off:** the prose-step regression lands as a **classifiable** `compile_error` (`observed_graph` populated, `well_formed_reason="non_tool_step"`) instead of a blind `steps=[]`. DT's insight caught a real regression on its first live run — the pass is not blind to its own residual.

## Finding 3 — Content re-rank: with the gate cleared, entity-resolution is the pervasive live defect.

The previously-`detached_args` cases are now well-formed — which **exposes the content failures the malformation was masking**:
- **Entity-resolution (space-mangle) — pervasive & live:** `30sec_edit 21` → `30sec_21` (duration-in-frames, rename-noise) or `30sec_edit_21` (set-start-frames). The space-bearing qualified-name defect (TF.1 defect #2) is the **most consistent live failure** now.
- **Grounding (example-lift):** set-start-frames now emits `default_frame=1001` — the docstring example value (baseline was `1`).
- **Routing:** "duration in frames" → `flame_preview_start_frames` (start-frames ≠ duration — wrong tool).
- **Prose / non_tool_step RELOCATED:** it left "current batch" (now well-formed) and appeared on "duration of shot 10" (Finding 2). The *class* persists; its *locus moved*.

**This re-answers the S5 ranking question — by corroboration, not overturn (DT + Creative correction).** ~5 graphs carry the `30sec_edit 21` → `30sec_21`/`30sec_edit_21` mangle (plus a sequence-name-as-`project_id` crossing and routing coupled to the corruption); vs **1** `non_tool_step` and 2 `invalid_chain_shape`. So:
- **Entity-resolution / space-mangling is the now-measured dominant content failure** — the roadmap's provisional defect #2 is *corroborated* (provisional → measured), exactly the conversion this pass existed for.
- **`non_tool_step` stays Slice #2 as planned — it was NOT outranked** (1 case vs ~5 mangle). The prose-step's *locus* moved (off "current batch," onto "duration of shot 10"), but the class neither vanished nor displaced entity-resolution. Both stay on the board; entity-resolution is simply the bigger content fish. (Earlier draft over-claimed displacement — corrected.)
- **(c) honest-decline still absent** — no live decline observed; cell (c) remains an *objective*, not an observed behavior.

## Finding 4 — `list projects` unchanged: `invalid_chain_shape`, empty graph.

Still a `compile_intent`-raise (parser-side `CompileInvalidChainShape`), so `steps` was never bound → empty graph, even with S2. This is the **out-of-scope** class `compile_raw` was named to backstop (the rev-3 carry-forward). Consistent with the design — not a gap.

---

## The dominant methodological caveat (gates every S5 decision)

**A single live run cannot separate intervention-effect from sampling-variance.** Every delta here — the 4 recoveries, the 2 regressions, the content shifts — is a one-sample observation. Attribution needs **replication and/or a control** ([[feedback-failure-shape-stability-as-disposition-evidence]]): re-run N times for failure-shape stability, and/or run **with vs. without the Prong-A grammar clause** to isolate its effect. Until then, this capture is *suggestive, not attributive*.

## Recommendation to the room (S5)
1. **N≥3 postgate re-captures (the next action — cheap, stack is up).** This is the only way to separate Prong-A-effect from sampling variance. Record the distribution, e.g. `4/11 before → 0/15, ?/15, ?/15 after`. Either outcome is useful: `0/45` across three ⇒ Prong A likely helped; a `1/15` appearing ⇒ detached-args is still stochastic and **Prong B remains the truly load-bearing protection** (and the run that detaches will finally exercise `salvage_applied=True` live). Same N≥3 discipline as DI.2-T1 ([[feedback-failure-shape-stability-as-disposition-evidence]]) — distribution, not single replay.
2. **Prong A's effect is unconfirmed in BOTH directions — do not bank "Prong A succeeded."** The 0-detached recovery *and* the "duration of shot 10" prose-step regression are each one-sample; either could be Prong A or variance. The regression is real data to watch across the N≥3 — not yet an indictment, not yet cleared. (Prong B's deterministic guarantee is unaffected — frozen bar green; this run simply never exercised it, `salvage_applied=0`.)
3. **Bank the re-rank as corroboration:** entity-resolution / space-mangling = measured dominant content failure (roadmap defect #2 firms from provisional → measured). `non_tool_step` stays Slice #2 as planned (not outranked). The N≥3 is for the *detached-args attribution*, not the content ranking — the ranking is already clear enough to bank.
4. `compile_raw` stays a carry-forward (Finding 4 reaffirms its only domain is the out-of-scope raise classes).

**Net:** the gate cleared on paper, but the post-gate measurement refused to let "0 detached_args" mean "done." The instrument did its job twice over — it measured the fix's ecological effect, and its own `salvage_applied` observability **stopped the room from misreading a model-variance 0 as a salvage win**. Without that field this would have entered the roadmap as "Prong B works in the wild," which the data does not support. Measure-first, fourth time this milestone.

---

## ADDENDUM — N≥3 attribution (4 postgate samples: S3 + run1/2/3, qwen2.5-coder:14b @ d355a88)

The distribution (baseline: **4** detached_args, **0** salvage):

| sample | detached_args | salvage_fired | wf=False (reasons) |
|---|---|---|---|
| S3 | 0 | 0 | 3 (`invalid_chain_shape`×2, `non_tool_step`×1) |
| run1 | 0 | 0 | 1 (`invalid_chain_shape`×1) |
| run2 | 0 | 0 | 1 (`invalid_chain_shape`×1) |
| run3 | 0 | 0 | 2 (`invalid_chain_shape`×1, `non_tool_step`×1) |

**Disposition 1 — detached_args stably suppressed; Prong B still never exercised.** `0/0/0/0` across four post-clause runs (vs **4** pre-clause), and `salvage_fired = 0/0/0/0`. The stable-0 is no longer a fluke — it's `0/60` post-clause. This is real evidence the detached-args shape is suppressed in the wild (Creative's "0/45 ⇒ Prong A likely helped" outcome). **But Prong B's live efficacy remains unmeasured** — the model never detached, so the salvage never had work; its correctness rests solely on the deterministic Slice-#1 bar. A clean *Prong-A-specifically* attribution would still want the clause-reverted control — but that's now **optional**, because no decision hinges on it (see Disposition 2).

**Disposition 2 — the two S3 "regressions" were VARIANCE, not stable regressions ([[feedback-failure-shape-stability-as-disposition-evidence]]).** N≥3 dissolved both:
- *duration of shot 10* → `True | True | False` across run1/2/3 (+ `False` in S3) = **2/4 prose-flicker, intermittent** — the `non_tool_step` class flickering stochastically, not a deterministic Prong-A side-effect.
- *gen_0460* → `True | True | True` across run1/2/3 = the S3 `CompileBudgetExceeded` was a **one-off timeout (1/4)**.

⇒ **Prong A is NOT indicted by a regression** — there is no stable regression. My earlier "Prong A is suspect" is refuted by the distribution. With no downside evidence *and* a stable-0 upside, **Prong A is retained**; the clause-reverted control is downgraded to optional curiosity (it would refine attribution of the 0 but change no action).

**Disposition 3 — space-mangle is STABLE across all 4 runs** (`flame_preview_start_frames sequence_name=30sec_21`, `flame_set_start_frames sequence_name=30sec_edit_21`, `flame_rename_shots sequence_name=30sec_21` in *every* run). Entity-resolution / space-mangling is firmly the **measured dominant content failure** — deterministic, not variance. Re-rank banked with confidence.

**Net well-formedness improved and held:** baseline wf-False = 6 (4 detached + 1 `non_tool_step` + 1 `invalid_chain_shape`) → postgate stable core = **1** (`list projects` `invalid_chain_shape`, the out-of-scope raise class) + intermittent flicker. The cleared cases stayed cleared across all four runs.

**S5 is now ratifiable:** Prong A retained (no regression, stable-0); Prong B = deterministic guarantee (unexercised live, by design); space-mangling = next content target; `non_tool_step` stays Slice #2 (real but intermittent, not outranked); (c) absent; `list projects` raise = out-of-scope (`compile_raw` carry-forward).
