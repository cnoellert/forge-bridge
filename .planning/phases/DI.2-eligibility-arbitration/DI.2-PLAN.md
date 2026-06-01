---
milestone: v1.10
phase: DI.2
phase_name: Eligibility Arbitration — make routing resolve instead of hard-stop
type: phase-plan
status: cycle-2-draft
drafted: 2026-06-01
derives_from: .planning/phases/DI.2-eligibility-arbitration/DI.2-DISCUSS.md (ratified) + DI.2-FRAMING.md (cycle-3, sized ≤3/9)
artifact_role: executable task breakdown for DI.2. The capture baseline (T1) sizes everything downstream; rungs are measurement-gated. Shape-locks grounded by direct read ([[feedback-substrate-shape-grounding-at-plan-stage]]).
grounding: live reads 2026-06-01 — _tool_filter.py:338-362 (exact/other buckets; substring-exact :344, token-complete-subset :349, cap-combine return :362) + :425-544 (deterministic_narrow Rules 1/2/2.5/3; closed lists _PR21_DOMAIN_PRIORITIES :395, _PR21_INTENT_MODIFIERS :405, _VERB_TOKENS :263); _step.py:255 (filter call) → :263-266 (narrow iff >1) → :314-328 (divergence emit, fires BEFORE) → :330-341 (tool_selection_ambiguous + candidates leak) → :342 tool_name → :415 dispatch_authority (DI.1 gate); handlers.py:1752 (chat-handler capture site, narrower_decision=tools, prompt=last_user_text); corpus/_capture.py:197 (FORGE_BRIDGE_DIVERGENCE_CAPTURE) + :221 (enabled, call-time read) + :505 (emit signature); corpus/_schema.py:31 (SCHEMA_VERSION="1") + :7/138-141 (optional add = non-breaking; new required key = bump) + :159-161/376 (_REQUIRED_NARROWER_KEYS, _VALID_AMBIGUITY_STATES)
---

# DI.2 — Plan

> Executable breakdown of the ratified DI.2 discuss. **Measure-first by
> construction:** T1 (capture baseline) is zero-code and *sizes* T3 and *gates*
> T4 — so the plan builds only what the data justifies. The arbitration ladder
> (rungs 2–5) all obeys the invariant *choose among known candidates; never create
> a new one.* Shape-locks below are read off the code, not assumed.

## What discuss already closed (do not re-derive)

Five Q-DI2.x resolved; the five framing deliverables collapsed to one
measurement-gated ladder; rung 4 ratified **contingent** with the invariant + 7
guardrails; deliverable 5 reclassified as the boundary that constrains the ladder.
The plan's only new work is task ordering, shape-locks, and the test matrix.

## Plan-check — call-site topology (sibling-check, cycle-1)

Grounded by grep ([[feedback-sibling-check-before-fix-scope-declared]]); each
target verified as single-site or shared, not silently scoped to the first of a
class:

- **The "matched N tools" leak has NO sibling — single site `_step.py:332`**
  (`tool_selection_ambiguous`). T5 is correctly single-site. The chat **direct
  path** does *not* leak: when narrowing leaves N>1 it hands the set to the LLM
  (`handlers.py:1792` forces only at ==1; otherwise LLM-dispatches). The leak is
  reached on the **chain path** (`_step.py`), which is where the v1.7 compile path
  executes each step — so chat-via-compile reads still hit it.
- **`filter_tools_by_message` is SHARED** — `handlers.py:1701` (direct) +
  `_step.py:255` (chain). **T2's exclusivity fix reaches both paths.**
- **`deterministic_narrow` is SHARED** — `handlers.py:1727` + `_step.py:264`.
  **T3 reaches both paths.**
- **Rung 4 reframed (accuracy):** the chain path **hard-stops** on N>1 while the
  direct path **already LLM-selects** on N>1. So T4 is not a new capability — it
  gives the **chain path** a *bounded, guardrailed* version of the selection the
  direct path already does loosely (the direct path is the existing reference;
  T4's seven guardrails are what the chain path adds on top).

## Sizing is provisional until T1 — and T1 measures a *distribution*, not a replay

The "≤3/9 reachable" number is an **upper bound, ledger-grounded, not yet
corpus-reproducible** (the dogfood never captured candidate sets). **T1 makes it
reproducible — but T1 re-runs a stochastic compiler (`qwen2.5-coder:14b`), so a
single pass is one *sample*, not a deterministic replay of the June-1 corpus**
(DT/Creative, plan cycle-2). The decision T1 informs is not "did R8 fail today?"
but "what failure *class* does R8 *tend* to produce?" — so **T1 measures a
failure-shape distribution across N runs and sizes DI.2 on class frequency +
stability, never a single outcome** ([[feedback-failure-shape-stability-as-disposition-evidence]],
[[feedback-baseline-drift-invalidates-controls]]). Three downstream consequences,
stated so they can't be quietly skipped:

- **T3's scope** (which tie-shapes to add to the closed rule-lists) is *unknown
  until T1* — do not pre-author rule additions; derive them from the **stable**
  captured ties (a tie that appears in 1 of 3 runs is weaker evidence than one in
  3 of 3).
- **T4 ships only if T1 shows a *stable* residual (a)** that rungs 2+3 can't reach.
  If rungs 2+3 eliminate the reachable class, **T4 never ships** — a smaller
  successful phase, not an underdelivery ([[feedback-operational-maturity-not-completeness]]).
- **T5's frequency** depends on how much (a) stably survives rungs 2+3; build it
  minimal.

## Tasks (ordered; dependencies noted)

### T1 — Capture baseline *(enabling; ZERO code; sizes T3, gates T4)*
**Establishes a failure-shape *distribution*, not a deterministic replay** of the
June-1 corpus (DT/Creative).

**Bring-up.** Documented stdio-held-open recipe with the capture flag prepended:
`FORGE_BRIDGE_DIVERGENCE_CAPTURE=1` + `FORGE_DB_URL=…@127.0.0.1:7533/forge_bridge`
(+ `FORGE_BRIDGE_CORPUS_DIR`), held background process in the conda `forge` env.
Project `013_13_13_2026_2_1_portofino` (id `2753ec84-775a-4928-8116-2cfef08e1ac3`)
— **confirmed still published** (27 shots / 20 versions / 48 media; consumer-refactor
risk retired by query, not assumption). 2 projects present → R7 `MULTIPLE_PROJECTS`
reproduces. *Nuance (not a blocker):* no `sequence` entity in pg, but R8/9/10 die at
the resolver and R7 at project-scoping — neither needs it; the (a)-class still
reproduces.

**Provenance gate first** ([[feedback-provenance-precedes-behavioral-interpretation]]):
confirm the daemon's model (`qwen2.5-coder:14b`) + loaded-code SHA before trusting
the harvest (the earlier "Flame dispatch failed" was a stale daemon, now
disproven).

**Capture-write sanity check (DT diligence) — BEFORE driving all reads.** There are
import-fallback `divergence_capture_enabled` stubs (`_step.py:57`,
`handlers.py:130`) that silently return False if the corpus module can't import —
which would disable capture *regardless of the env var* and silently reproduce the
dogfood's abort-blindness. So: drive **one** read first and confirm a `source:
"runtime"` divergence record actually lands in `corpus/capture-*.jsonl` before
proceeding.

**The runs (stability clause).** Run **each of the 11 reads N≥3 times → ≥33
samples.** Harvest `candidate_set_post_pr14` + `narrower_decision` from the
**divergence** corpus at **both** call sites (`_step.py:314` chain,
`handlers.py:1752` chat). Classify **per run** by dominant failure shape:
**(a) resolver-overmatch** (right operation, N tools) · **(b) bad-compile** (wrong
operation) · **(c) other-seam**. **Size DI.2 on class frequency + stability**
(a tie in 3/3 runs ≫ a tie in 1/3) — *not* a single outcome.

**Artifact:** `UAT/DI.2-baseline.md` — per-read × per-run classification table,
the resulting class-frequency distribution, the candidate set per stable (a) read,
and an explicit stability/confidence note. **Don't-couple:** read divergence only;
never merge into the comprehension schema. *No dependency; everything downstream
consumes it.*

### T2 — Exact-name-wins exclusivity *(rung 2; unconditional; unblocks DI.1 demo)*
`_tool_filter.py` — in `filter_tools_by_message`, **before** the cap-combine at
`:359-362`:
`if len(exact_matches) == 1: return exact_matches` (drop `other_matches`).
Today `:362` returns `exact_matches + other_matches[:remaining]` — exact has
*survival* precedence, not *exclusivity*, so typing `flame_set_start_frames`
yields 1 substring-exact + ~8 token-overlap = the 9. **Multi-exact (≥2) falls
through** to the current combine → `deterministic_narrow` → ranking (do not
collapse genuine ambiguity). Shared substrate: this fix also benefits the
chat-handler filter path, not just the chain. **Test matrix (4 cases, all
required):**
1. unique **substring-exact** (`"flame_set_start_frames"`) → returns `[that]` only.
2. unique **token-complete-subset** (`"set start frames"` → `flame_set_start_frames`
   via `:349`) → returns `[that]` only.
3. **≥2 exact** → falls through (returns `exact + other`, length >1).
4. **regression:** update existing PR17/PR18 filter tests that assert the combined
   `exact + other` return for a *unique-exact* input — their expectation changes
   to exclusive (Stage-1b: this is an expectation *update*, not just new cases).

*Cross-phase acceptance (in T6):* `flame_set_start_frames` now reaches
`_step.py:415` and DI.1 blocks it — the meta-finding's "DI.1 value becomes live."
*Depends on nothing.*

### T3 — Strengthen `deterministic_narrow` *(rung 3; scope sized by T1)*
`_tool_filter.py:425-544` — close the residual N>1 cases T1 surfaced for ordinary
task phrasings. **This is data-driven extension of the existing closed rule-lists,
NOT a new algorithm:** add pairs to `_PR21_DOMAIN_PRIORITIES` (`:395`) and/or
tokens to `_PR21_INTENT_MODIFIERS` (`:405`) / the verb set (`:263`) as the captured
tie-shapes dictate. Preserve the A.5.3.1 verb-only guard (`:522-530`) — never
break ties on a non-signal. **Do not author rule additions before T1.** Each added
rule gets a unit test using the exact captured tie as the reproducer. *Depends on
T1 (scope) ; touches the same function family as T2 but a different code path
(`:425+` narrow vs `:338+` filter).*

### T4 — Bounded LLM selection *(rung 4; CONTINGENT on T1; the seven guardrails)*
**Build iff T1 shows residual (a) that rungs 2+3 cannot reach.** A console-layer
helper (needs router/mcp; **not** pure `_tool_filter.py` which is I/O-free by
contract), slotted between `_step.py:266` (post-narrow) and `:330` (ambiguous
return). A **single** pick-one-from-set call — control-flow, not the orchestration
loop. The invariant: *choose among known candidates; never create a new one.* The
seven binding guardrails:
1. fires **only after** rungs 2+3 leave 2..5 survivors (runtime ordering);
2. candidate set **≤5**;
3. selects **only** over the resolver's produced set;
4. **no new tool** invented;
5. **no reinterpretation** of the request beyond choosing among candidates;
6. **timeout-bounded** — reuse the existing router per-tool cap, no new knobs;
7. **captured** to the **divergence** corpus.
**Guardrail-7 shape-lock (grounded):** the selection is a new arbitration outcome.
Add it as a new **optional** field (`llm_selection`) OR a new `ambiguity_state`
value (`_VALID_AMBIGUITY_STATES`, `_schema.py:376`). A new *optional* field is
non-breaking (no forced bump, `:7/138-141`); a new **required** key or a new valid
state value is a `SCHEMA_VERSION` bump (`:31`). Lean: optional field, no bump —
confirm at execute. *Depends on T1 (build decision) + T2/T3 (runtime ordering);
off the critical path.*

### T5 — Task-term fallback surface *(rung 5; terminal; minimal)*
`_step.py:330-341` — replace the `tool_selection_ambiguous` leak. Today it returns
`message:"Step matched N tools… use a more specific verb"` + `candidates:[tool
names]` — **both** the message and the `candidates` tool-identifier list must go.
Substitute an **outcomes-not-tools** prompt: labels derived from each candidate's
**description** (not its name); a **generic** ambiguity explanation when
descriptions are poor (*don't invent clarity that isn't present*). Never leak tool
identifiers ([[project-forge-bridge-ux-philosophy]]). **Single-site** — the leak
has no sibling (plan-check); the chat direct path doesn't leak (it LLM-dispatches
on N>1), so T5 touches only `_step.py:330-341`. *Depends on T2/T3 (it's the
residual after arbitration); frequency sized by T1.*

### T6 — Regression-lock + acceptance *(the invariant + the cross-phase proof)*
- **Rung correctness:** T2 four-case matrix; T3 per-rule reproducers; (if shipped)
  T4 guardrail tests — esp. guardrail 4 (no invented tool) + guardrail 1 (never
  fires before rungs 2+3).
- **The leak is gone:** no `tool_selection_ambiguous` response carries raw tool
  identifiers to the human surface (T5).
- **Cross-phase (the meta-finding made live):** a mutating exact-name
  (`flame_set_start_frames`) now resolves to one tool and is **blocked by DI.1** at
  `_step.py:415` — DI.2 makes the request *reach* the gate; DI.1 still decides.
- **Reads-side invariant held:** DI.2 changes do not weaken DI.1 — a resolved
  mutation still hits the gate; no mutation executes via arbitration.
*Depends on T2..T5.*

## Critical path & sequencing

`T1` (baseline — first, gates T3/T4) → `T2` (exclusivity, unconditional) →
`T3` (narrow, sized by T1) → `T5` (fallback) → `T6` (lock). `T4` rides
**contingent** after T1's build decision, off the critical path. **Shippable
core = T1 + T2 + T3 + T5 + T6.** T4 ships only if measured-necessary.

## Shape-locks (grounded, do not re-derive)

- Exclusivity insertion = `_tool_filter.py` before `:359` (`if len(exact_matches)
  == 1: return exact_matches`); the two exact kinds are substring (`:344`) +
  token-complete-subset (`:349`) — both covered by the single-member check.
- `deterministic_narrow` is closed-rule (`:425-544`); strengthening = list
  additions (`:395/:405/:263`) + the verb-only guard preserved (`:522-530`).
- Ambiguous-leak site = `_step.py:330-341` (message + `candidates` list); both fields
  replaced in T5.
- DI.1 gate (untouched) = `_step.py:415` `dispatch_authority(filtered[0])`.
- Divergence capture already fires on the multi-match reject path before `:330`
  (`:314-328`); T1 needs no new emit. T4's capture is an optional schema field
  (non-breaking) per `_schema.py:7/138-141`.

## Constraints (inherited, binding)

`__all__` stays **19**; no new external libs. Reads-side only; DI.1's gate
untouched. Control-flow, not meaning — no prose, no invented tools, no authority
decisions anywhere in the ladder. Best-effort bar (usability), not a safety
guarantee. Don't-couple: divergence corpus stays distinct from the comprehension
corpus forever.

## Status

**Cycle-2 plan draft, 2026-06-01** (DT/Creative stability amendment folded). Six
tasks (T1–T6); shippable core = T1+T2+T3+T5+T6, T4 contingent. Measure-first is
structural: T1 is zero-code, sizes T3, gates T4. Cycle-2 change:

- **T1 measures a distribution, not a replay (DT/Creative).** A single rerun of a
  stochastic compiler is one sample, not the frozen 9-failure ledger. T1 now runs
  **each read N≥3 (≥33 samples)**, classifies **per run** by dominant failure
  shape, and **sizes DI.2 on class frequency + stability** — the same discipline
  DI.2 applies to the resolver, applied to its own measurement. Infra risk closed
  by query (013_13_13 still published; Flame/bus/Ollama/pg live); the real risk
  was compile nondeterminism, now provisioned. Added DT's **capture-write sanity
  check** (one read first; confirm a `runtime` record lands, guarding the
  import-fallback stub) before driving all reads.

Cycle-1 plan-check (retained):

- **Sibling-check (grep):** the "matched N tools" leak is single-site
  (`_step.py:332`, no sibling) → T5 correctly scoped. `filter_tools_by_message`
  and `deterministic_narrow` are **shared** across the direct + chain paths → T2
  and T3 reach both.
- **Rung 4 reframed:** the chain path hard-stops on N>1; the direct path already
  LLM-selects — T4 gives the chain path a *bounded, guardrailed* version of an
  existing reference behavior, not a net-new capability.

Open for cross-voice review before execute.
