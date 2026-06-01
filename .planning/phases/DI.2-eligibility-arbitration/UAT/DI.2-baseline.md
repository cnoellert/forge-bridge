# DI.2 — T1 baseline (failure-shape distribution, not a replay)

Status: **complete.** 11 dogfood reads × 3 runs = **33 samples** driven against a live
post-DI.1 bridge daemon with divergence capture on. Sizes T3 and gates T4 per
DI.2-PLAN. This is a *distribution* measurement (stochastic compiler) — class
frequency + stability, not a single outcome.

---

## 1. Provenance (grounded, not assumed)

- **Daemon source:** `/Users/cnoellert/GitHub/forge-bridge/forge_bridge`, `main @
  82b9062` — **post-DI.1, pre-DI.2** (the correct DI.2 control; DI.1's gate is live).
- **Model:** `qwen2.5-coder:14b` (local Ollama; `_DEFAULT_LOCAL_MODEL`, non-degraded;
  32b also present but not default).
- **Port:** brought up on **`:9990`** via `FORGE_CONSOLE_PORT` (stdio-held-open recipe)
  — **`:9996` was occupied by an unrelated `forge_core --no-db` process, left
  untouched** (non-destructive deviation from the plan's `:9996`).
- **Data:** project `013_13_13_2026_2_1_portofino` (id `2753ec84-…`) on pg `:7533`;
  bus `:9998` connected; Flame reachable. 2 projects present → R7 ambiguity reproduces.
- **Capture:** `FORGE_BRIDGE_DIVERGENCE_CAPTURE=1` (+ comprehension), separate corpora
  (don't-couple honored). **Capture-write sanity check PASSED** before the full run: a
  `source:"runtime"` divergence record with a real candidate set landed on read 1 —
  the import-fallback stub (`_step.py:57`/`handlers.py:130`) is **not** active.

## 2. Method + the two instrument findings

- 11 reads × 3 runs, **round-robin** (passes separated in time → no consecutive-identical
  caching artifact).
- **Rate-limit confound (recorded):** the chat endpoint's 10-req/60s IP limit returned
  `429` for **run3 R4–R11** (8 cells). Re-run those 8 **paced** (65s cooldown + 8s
  spacing) for the 3rd clean sample. All cells now have 3 valid samples.
- **Instrument note:** `candidate_set_post_pr14` serialized as **`null`** in every
  record; the actual candidate list lives in `narrower_decision` +
  `candidate_set_post_reachability`. Classification used those. (If T4 ever ships and
  wants `post_pr14`, that field needs populating — a measurement follow-up, not a
  blocker.)

## 3. Per-read × per-run ledger (3 valid samples each)

| # | Read | Runs (stop_reason) | Stable? | Discriminator | Class |
|---|------|--------------------|---------|---------------|-------|
| R1 | batch groups on desktop | tool_forced ×3 | ✓ | `flame_list_batch_groups`, correct | **success** |
| R2 | reels on desktop | invalid_chain ×2, chain_complete ×1 | stochastic | `compile_invalid_chain_shape` ("flame_list_desktop ->", empty step) | **(b) bad-compile** |
| R3 | current desktop name | tool_forced ×3 | ✓ | fabricated "Untitled Batch" (no desktop-name field) | **(c) answer-pass** |
| R4 | current reels group name | chain_complete ×3 | ✓ | "Schematic Reel 1", correct (improved vs dogfood mutation-miscompile) | **success** |
| R5 | current batch name | chain_aborted ×3 | ✓ | step1 `unauthorized_mutation` (`flame_open_batch_group`) — **DI.1 gate** | **(b) bad-compile** |
| R6 | what iteration is gen_0460 on | chain_aborted ×3 | ✓ | injected `format_result` missing `params.format` | **(b) bad-compile** |
| R7 | list shots on 30sec_edit 21 | MULTIPLE_PROJECTS ×3 | ✓ | no session scope → raw error | **(c) other-seam** |
| R8 | path to shot 10 | chain_aborted ×3 | ✓ | `tool_selection_ambiguous`, 4 tools, step=`forge_get_shot` | **(a) resolver** |
| R9 | does shot 10 have a timewarp | chain_aborted ×3 | ✓ | same 4-tool overmatch, step=`forge_get_shot` | **(a) resolver** |
| R10 | duration of shot 10 | chain_aborted ×3 | ✓ | same 4-tool overmatch, step=`forge_get_shot` | **(a) resolver** |
| R11 | duration in frames of 30sec_edit 21 | blocked_unratified_mutation ×3 | ✓ | `flame_set_start_frames` blocked — **DI.1 gate** | **(b) bad-compile** |

The (a)-class candidate set (all of R8/R9/R10, 3/3, identical):
`[forge_get_shot, forge_get_shot_stack, forge_get_shot_versions, forge_get_shot_lineage]`.

## 4. Class distribution — the framing's split, reproduced

**2 reads succeed (R1, R4, 3/3); 9 fail.** Of the 9:

| Class | Reads | Count | % of 9 |
|---|---|---|---|
| **(a) resolver-overmatch** | R8, R9, R10 | **3** | **33%** |
| **(b) bad-compile** | R2, R5, R6, R11 | **4** | **44%** |
| **(c) other-seam** | R3 (fabrication), R7 (session scope) | **2** | **22%** |

This **reproduces the DI.2-FRAMING prediction (~33% / ~44% / ~22%) almost exactly** —
"≤3/9" is now corpus-confirmed, not ledger-grounded.

## 5. The load-bearing result — T2 alone resolves the entire reachable class

**All 3 (a)-class reads are resolved by T2 (exact-name-wins) by itself.** Each compiled
to the **bare step `forge_get_shot`**, which is a unique *substring-exact* match;
exact-name-wins returns `[forge_get_shot]` and drops the 3 token-overlap siblings →
`len==1` → executes (and `forge_get_shot` is a read, so DI.1's gate passes). The
framing's "contingent on the right tool being in the tied set" is **confirmed
satisfied**: the right tool is present *and is the exact match*.

**Consequences for the ladder (the measure-first gates fire):**

- **T2 (exact-name-wins): unconditional, and it is the whole reachable win.** Ships.
- **T3 (strengthen `deterministic_narrow`): no reproducer in this corpus.** Every (a)
  case is an exact-name case T2 handles; no (a) read needs token-rule additions. Ship
  **minimal/empty** (no rule changes justified by data) — or fold to a no-op pending a
  future corpus that shows a non-exact (a) tie.
- **T4 (bounded LLM selection): DOES NOT SHIP.** The gate condition — "a *stable*
  residual (a) that rungs 2+3 can't reach" — is **empty**. T2 reaches 3/3 of the (a)
  class. This is the plan's anticipated "smaller successful phase," realized by data,
  not underdelivery.
- **T5 (task-term fallback): ships, but with no live reproducer post-T2 here.** T2
  removes every "matched N tools" instance in *this* corpus; T5 remains worth shipping
  to replace the leak surface for future non-exact (a) cases (multi-exact, or a
  compiled step that isn't a bare tool name). Flagged: defensive, not corpus-exercised.

## 6. Cross-phase + methodology findings (load-bearing)

- **DI.1's live mutation-block is now DEMONSTRATED — a measurement-debt item retired.**
  DI.1-CLOSE could only suite-prove the block (Symptom 2 masked it live). Here **R11**
  (forced `flame_set_start_frames` → `blocked_unratified_mutation`) and **R5** (chain
  step `flame_open_batch_group` → `unauthorized_mutation`) both **reach DI.1's gate and
  are blocked, live, 3/3.** Mutation-compiles that resolve to a single tool reach the
  edge; multi-match reads die at the resolver. This is the first live confirmation of
  DI.1's value and validates the DI.1→DI.2 ordering empirically.
- **The stability clause earned its keep immediately.** R2 is stochastic (2/3
  malformed-compile, 1/3 correct). A single run would have mis-sized R2 as either a
  hard (b) failure or a success. N=3 caught it — exactly the compile-nondeterminism
  risk DT/Creative flagged.
- **R4 improved vs the dogfood** (mutation-miscompile → correct `chain_complete` ×3):
  substrate/compile drift since `dab749b`, reinforcing baseline-drift discipline (the
  dogfood is *not* a safe implicit control; this contemporaneous baseline is).

## 7. Verdict

DI.2's shippable core narrows, by evidence, to **T2 (exact-name-wins) + T5 (leak
replacement) + T6 (regression-lock)**. **T3 minimal/empty, T4 does not ship.** The
reachable win is a **confirmed 3/9 (33%)**, fully delivered by exact-name-wins. The
compile-quality class (b, 44%) and other-seam (c, 22%) remain out of scope
(`SEED-COMPILE-QUALITY-V1.10+`), as framed.
