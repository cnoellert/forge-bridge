# TF.4 Post-Gate Re-Capture — PLAN (rev 3 — Creative + DT ratified)

**Milestone:** v1.13 Translation Fidelity. A **measurement interlude** between TF.4 Slice #1 (shipped) and the Slice-#2 decision. Discharges the deferred **TF.3b** instrument-run, now with a concrete purpose: measure the Slice-#1 fix in the wild.
**Settles:** the cursor's parked-queue item #1 + the DT/Orch *re-measure-before-Slice-#2* ruling.
**Goal:** re-measure the live compile distribution through the **repaired** substrate, preserving the frozen pre-fix baseline, so the provisional #2–#5 content ranking becomes **measured** and the Slice-#2 scope is **evidence-driven**.
**North-star:** *Slice #1 moved the measurement apparatus — use the instrument before trusting another prediction.*

This pass **measures; it does not fix.** No runtime repair, no taxonomy change. Settled fact going in (do not re-litigate): *serialization/well-formedness was the dominant measured defect, deterministically repaired at the substrate (Metric A green).* Everything downstream is the open measurement.

---

## Pre-flight (confirmed this session — all green)
Anchor → this checkout `d355a88` (repaired `normalize_chain_shape` runs in-process); Ollama + `qwen2.5-coder:14b`; postgres `:7533` (asyncpg `select 1`); Flame (daemon dispatches `:9999`). The daemon serving stale `73b035b9` is **irrelevant** — `run_captures` builds its own `LLMRouter()` + imports `mcp` in-process at `d355a88`, so compile+normalize run repaired regardless.

## Finding (rev 3, DT-corrected): evidence-discard is NARROWED, not gone — which reshapes the pass
The rev-2 claim "Slice #1's loosening already solved evidence-discard" was **too strong (DT grounded the correction).** Read `run_compile_branch` (`_chat_compile.py:172-186`):
```
try:
    steps = await router.compile_intent(...)
    steps, salvage = normalize_chain_shape(steps)   # ← re-raises on unrepairable residual
except CompileError as exc:
    return CompileBranchOutcome(regime="compile_error", steps=[], ...)   # ← steps DISCARDED
```
The loosening preserves evidence **only for the repairable detached-args** (they reach the success path with `steps` populated). For the **unrepairable residual** — the seam-#1 negatives (orphan / ambiguous / already-has-args) — `normalize_chain_shape` *re-raises* `CompileInvalidChainShape`, the `except` returns `steps=[]`, and the bound loosened step-list is **thrown away: `observed_graph` empty, `well_formed_reason` lost — the same L1 blindness.**

So the evidence-discard problem is **narrowed to the re-raise / compile-error path**, not gone. Two consequences, kept separate:

⇒ **`compile_raw` is REMOVED from the critical path — for the precise reason (not "it's solved").** What it still backstops ([[feedback-transitional-structure-naming]] — name it, don't collapse): the **`compile_intent`-raise classes** (unknown-tool `:496`, unresolvable, non-string/empty-step `:478/:481`) — where `steps` was *never bound*, so only raw survives. Those are **out of scope** for a detached-args measurement pass. **Maturation condition:** a future pass that investigates those failure classes. So `compile_raw` = heavyweight forensic hygiene for out-of-scope classes → optional FUTURE observability enhancement, off this pass. (Not deleted: the project's four prior malformed-shape surprises argue for keeping raw as a future debugging surface.)

⇒ **The in-scope move is capture-on-re-raise (NEW S2), not `compile_raw`.** On the normalize re-raise, `steps` is *still bound* to the loosened `compile_intent` output (the tuple-unpack never completed). Capturing that bound value instead of `[]` makes an unrepairable-residual detached-args case land as a **classifiable** compile_error (`observed_graph` populated → `compute_well_formed` → `(False, "detached_args")`) instead of blind. **Why this pass needs it:** the post-gate measurement validates the detached-args fix, and the residual of that exact class (the cases normalize *refused* to repair) is the single most important "how complete is the fix" signal. The recursive TF.3a lesson: *don't run a measurement instrument blind to the dominant residual of the very class it measures* — we got burned once this milestone by exactly that. It's instrument hygiene (touches the capture path, not compile logic), so it's legitimate measure-don't-fix scope.

## Constraints (binding)
- **`reference/cases.jsonl` is NEVER mutated — it is now effectively a benchmark dataset (Creative).** It is the frozen pre-fix baseline AND the input the deterministic bar replays (`assert len(detached_rows) == 4`). Once you overwrite it, every future "did the gate actually improve things?" question becomes archaeology instead of measurement. The post-gate capture writes to a **distinct** corpus; mutating the baseline destroys the "before" half of Metric B and breaks the bar.
- Public `forge_bridge.__all__` = **19**; `translation_oracle.__all__` = **18** (no new public symbol — `compile_raw` is not added this pass); `SCHEMA_VERSION` stays `"1"`. No new external libs.

## Grounded mechanism
`_corpus.py` is already `corpus_dir`-parameterized (`append_case(case, *, corpus_dir=None)`, `read_cases(*, corpus_dir=None)`, `_resolve_corpus_dir`). `run_captures.build()` hardcodes `REFERENCE_DIR` in three spots (`path = REFERENCE_DIR/"cases.jsonl"`, the `read_cases(...)`, the `append_case(...)`). Output-targeting = thread a target dir through `build()` + a CLI flag. `coverage_report(cases)` is corpus-agnostic (takes a list). No deep change.

---

## Steps

### Step 1 — Output-targeting in `run_captures` (preserve the frozen baseline)
- Thread a `corpus_dir` through `build()` (default `REFERENCE_DIR` — unchanged behavior) + a `--postgate` / `--output DIR` CLI flag selecting a distinct target, e.g. `reference/postgate/`.
- A `--postgate` run reads/unlinks/appends ONLY under the target dir; `reference/cases.jsonl` is untouched.
- **Verify (`tests/translation_oracle/`):** a `--postgate` build leaves `reference/cases.jsonl` byte-identical (hash/mtime asserted); the **Slice-#1** deterministic well-formedness bar still passes against the frozen file; a postgate build round-trips through `read_cases(corpus_dir=…)`.
- Commit: `feat(TF.4): post-gate output-targeting — preserve frozen baseline`

### Step 2 — Capture-on-re-raise (instrument hygiene — see the residual of the measured class)
- In `run_compile_branch` (`_chat_compile.py:172-186`): pre-initialize `steps: list = []` before the `try`, and on the `except CompileError` return the **bound** `steps` instead of `[]`. On a `compile_intent`-raise (out-of-scope classes) `steps` stays `[]` (unchanged); on a `normalize_chain_shape` re-raise `steps` holds the loosened output → the unrepairable-residual detached-args case is captured with a populated `observed_graph`.
- Net effect: `_capture` maps it → `compute_well_formed` returns `(False, "detached_args")` → the residual is **classifiable**, not blind. This is the only thing that lets S3 distinguish *"the fix is complete (no residual)"* from *"the fix has residual the model still hits."*
- **Verify (`tests/console/` + `tests/translation_oracle/`):** an unrepairable-residual detached-args input → `regime="compile_error"` with `observed_graph` populated and `well_formed_reason="detached_args"`; the `compile_intent`-raise classes (unknown-tool / unresolvable) still yield `steps=[]`. **Production-safety check (do at execute): confirm no consumer branches on `outcome.steps` for a `compile_error` outcome** — this must be a pure observability gain, behavior-equivalent on the live chat path. Existing compile_error tests stay green.
- Commit: `feat(TF.4): capture-on-re-raise — classifiable residual on compile_error`

### Step 3 — The live post-gate capture
- Stack up (it is). Run the post-gate build: `python -m forge_bridge.translation_oracle.run_captures --postgate` (in-process `d355a88` compile + normalize; Flame `:9999`; pg `:7533`).
- Produces `reference/postgate/cases.jsonl` — live `ObservedTrace`s carrying `salvage_applied`.
- **Verify:** capture completes for all cases (log skips, no silent drops); on the previously-`detached_args` cases `well_formed == True` — the **first live (non-replay) confirmation of Metric A**; `salvage_applied` present where the model still detached.
- Commit the data artifact: `data(TF.4): post-gate live capture (qwen2.5-coder:14b @ d355a88)`

### Step 4 — The comparison / re-rank findings (`TF.4-POSTGATE-FINDINGS.md`)
Mirrors `TF.3a-CAPTURE-FINDINGS.md`. Interpretation (room/operator judgment), not mechanism:
- **Metric B (ecological):** `detached_args` rate — frozen baseline vs post-gate. Did incidence drop in the wild (Prong A's win)? Did `salvage_applied` carry the rest (Prong B)? Report both — they are separate (the 2×2).
- **Gate-clear confirmation:** previously-malformed → now well-formed, live.
- **Fix-completeness (the S2 payoff):** how much **unrepairable-residual detached-args** survived (now classifiable, not blind)? This is the honest "how complete is the fix" number — the residual of the very class this milestone repaired.
- **Content re-rank (#2–#5):** the distribution that was "what survived malformation" re-measured **ungated**. Space-mangling / contextual / entity-resolution — what actually dominates now.
- **L8 re-judge:** grounding-on-contextual-seam, now that the gate is clear.
- **Is `non_tool_step` still representative?** Did the grammar clause (Prong A) or the loosening change the prose-step incidence?
- Commit: `docs(TF.4): post-gate findings — measured #2–#5 re-rank`

### Step 5 — Re-rank ratification + Slice-#2 decision
- Room ratifies the measured ranking; update the cursor with **measured** (not provisional) #2–#5.
- **Decide whether Slice #2 is still `non_tool_step`** — or whether the measurement re-ranked it (as TF.3a re-ranked example-salience). Honor the measure-first ruling: the decision is evidence-driven.
- Commit: `docs(TF.4): ratify measured ranking + Slice-#2 scope`

### Carry-forward (NOT a step) — `compile_raw` future observability
Demoted per the rev-3 finding: optional raw-model-output capture (an optional non-breaking `_raw_out` param on `compile_intent` if ever built). **What it still backstops:** forensic replay of the `compile_intent`-raise classes (unknown-tool / unresolvable / non-string), where `steps` is never bound so only raw survives — *out of scope* here. **Maturation condition:** a future pass investigating those failure classes. Named so it is not lost — a candidate, not a debt; do not collapse "Slice #1 + S2 handled the detached-args slice" into "compile_raw is unnecessary."

---

## Goal-backward verification
1. Frozen `reference/cases.jsonl` byte-identical after the pass → before/after comparison valid, Slice-#1 bar intact. ✓ S1
2. The pass is **not blind to its own class's residual** — unrepairable-detached-args lands as a classifiable `compile_error` (`observed_graph` populated, `well_formed_reason="detached_args"`), not `steps=[]`. ✓ S2
3. Live capture confirms Metric A in the wild (not just deterministic replay). ✓ S3
4. Metric B computed as a baseline-vs-postgate delta, Prong A vs Prong B kept separate. ✓ S4
5. #2–#5 content distribution re-measured ungated → ranking is **measured**, not provisional. ✓ S4
6. Slice-#2 scope is an evidence-driven decision, not a carried-forward prediction. ✓ S5
7. `compile_raw` re-decided on merit (not inertia) → demoted to future candidate, off the path; what it still backstops named. ✓ rev-3 finding

## Out of scope
The actual Slice #2 fix (prose/non-tool-step); space-mangling fix (defect #2); (c) honest-decline restoration. All are downstream of this measurement — this pass tells us which is next, it does not build any of them.

## Commit cadence
S1 + S2 are code commits with tests; S3 commits the post-gate data artifact; S4 the findings doc; S5 the ratification. `pytest tests/console tests/translation_oracle` green before close. **The frozen baseline corpus is never rebuilt** — only `reference/postgate/` is written.
