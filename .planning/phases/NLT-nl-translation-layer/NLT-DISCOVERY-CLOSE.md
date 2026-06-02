# NLT — Discovery Close (verdict + Q0/Q2 resolutions + go-forward)

**Status:** discovery objective MET → closeable. DT + Creative concur Phase-1-can-lock.
**Spine:** confirmed (graph-as-boundary holds for mutations; reads straddle, documented).
**Inputs:** grounded (D1/D2/D3 closed). No grounding owed.

---

## Discovery objective + verdict

The objective was **not** "fix rename." It was: *does a coherent translation-layer boundary exist, and can
failures be cleanly classified across it?* **Answer: yes, on both counts.** The D-series didn't find bugs —
it **partitioned a problem space**: "rename doesn't work through chat" (one failure) resolved into three
defects in three classes with three owners and three fixes:

| Defect | Class | Owner |
|---|---|---|
| #1 `prefix→noise` | grounding / example-salience | translation (description layer) |
| #2 `tool_unresolved` | routing (PR20 shadows compile) + extraction | translation (selection + param parse) |
| #3 sequence mangle | contextual/stateful resolution gap | translation (missing world-state→compile injection) |

The room's hypothesis survived contact with evidence: the chain-step graph boundary held, C2 / ratify gate /
executor routing / preview all behaved correctly, and the failures were **translation failures visible at
the graph boundary**. `[[feedback-substrate-pass-translation-open]]` is now grounded by multiple independent
findings, not a preference.

## What's established (the discovery deliverable)

- **Boundary contract (path-dependent):** mutations — chain-step graph IS the translation/substrate
  contract (resolution completes pre-graph); reads — straddle, completion at dispatch (`_step.py:568`).
- **Inventory:** ~6 translation components; resolution at ≥3 lifecycle sites.
- **Taxonomy:** grounding · routing · extraction · entity-resolution · **contextual/stateful resolution**
  (promoted theory→evidenced via defect #3).
- **Cross-cutting class (D3):** example-salience is a *whole-corpus* property — a read tool's docstring
  example (`30sec_21`) supplied a mutation's bad fill; it's the **fill-of-last-resort** for any ungrounded
  param. Defense-in-depth that shrinks the blast radius of the other gaps.
- **Doctrine promoted:** `[[feedback-substrate-pass-translation-open]]`.

---

## Q0 — milestone placement: RESOLVED (DT lean, adopted)

**Run NLT as a standalone discovery/formalize phase (already is); the discovery deliverable IS the Q0
verdict.** Do **not** fold under v1.12 (Mutation Delegation = C2 + Shape B): theme mismatch — NLT spans reads
*and* mutations, and absorbing it recreates the arbitration→everything drift the boundary discipline
prevents. Partial size signal already points milestone-ward (~6 components · ≥3 resolution sites ·
path-dependent · 3+ classes) — not a small surface. **Hold the formal milestone-open as the likely outcome,
sized by Phase 1's inventory; don't pre-commit the version now.** (Discipline: grounding shrinks scope — C2,
DI.2 T4 — so let Phase 1 size before naming.)

## Q2 — uncertainty depth: RESOLVED as a guardrail principle (DT lean, grounded-refined)

**Principle:** default to the *shallowest useful* representation — **per-param provenance** ("grounded from
intent" / "filled from default-or-example" / "unresolved") surfaced at the **existing** preview/ratify gate
— and **measure-first-gate any depth beyond that**. Reject the speculative confidence-scoring /
multi-candidate-disambiguation framework built before evidence (the monolith). It's squarely the cut-line
doctrine: a param filled from an example is *a fact that does not exist presented as grounded* — flagging
its provenance is the doctrine, not new license.

**Grounding refinement (flips "nearly free"):** the resolver already carries per-value `source`
(`resolver.py:249` `{value, source}`) and the precedence chain orders by origin (`_param_extract.py:19-20`,
explicit > memory > resolver) — so origin-stage provenance *is* nearly free. **But the distinction that
matters — intent-grounded vs example-filled — is NOT captured:** an LLM example-lift enters as an
*explicit-looking* step param (`prefix=noise`), laundered into the highest-precedence origin and
indistinguishable from a genuine explicit value. So the provenance flag splits:
- **free:** explicit / memory / resolver origin (already tracked).
- **needs new signal:** "filled from a tool-description example" — and **D3's inventory is the detection
  oracle** (does the value match a known liftable example for this param?). Phase 3 (validation) measures
  example-filled-vs-grounded frequency; that frequency ranks whether any depth beyond the flag is warranted.

---

## Go-forward motion (Creative's 4 phases)

1. **Formalize** — lock the boundary contract (mutations) + document the reads straddle; bound the inventory.
2. **Taxonomy** — formalize the 5 classes above.
3. **Validation** — independent translation-pass / substrate-pass against the graph contract; **gates
   Phase 4** (measure-first); measures example-fill frequency (feeds Q2 depth decision).
4. **Quality** — evidence-ranked smallest slices: strip liftable *value* examples (keep vocab as enum, D3
   value-vs-vocab cut); the PR20-shadows-compile + extraction fix (#2); contextual-context injection into
   compile (#3); per-param provenance flag (Q2). Each independent; rank by measured frequency.

**Guardrail (binding):** decompose → rank → measure-first; smallest useful slices; reject the monolith.

## Forward-pointer — tool-authoring contract (Creative's corpus insight; candidate motion)

D3's cross-tool bleed means **translation reasons over the whole visible tool corpus**, not per-tool. Tool
descriptions currently serve **three conflated roles** — human documentation, LLM grounding, translation
hints — and a human-optimized docstring (`30sec_21`) can be *actively harmful* as translation input. This
points to a formal **tool-authoring contract** (what a description owes each consumer; where examples are
value-vs-vocab; salience rules). Not because the tools are wrong — because they were written before
translation was a first-class concern. Capture as a candidate motion; do not open now (own grounding).

---

## Methodology

- **Discovery partitions, it doesn't patch.** The valuable output was three ownership boundaries, not a fix
  — the canonical shape of a discovery phase done right.
- **Grounding-flip relocates** fired again (Q2 "nearly free" → "the provenance that matters isn't
  captured"); ~7× this arc. Promotion-grade for `[[feedback-ground-specs-in-actual-files]]` — pool with the
  C2 candidates for the dedicated room methodology pass.
