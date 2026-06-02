# TF.1 (Formalize) — DISCUSS: the reads-contract decision

**Milestone:** v1.13 Translation Fidelity, Phase 1 (Formalize). **Opens:** room-review-endorsed framing.
**The one open call:** reads = *consolidate resolution pre-graph* vs *explicit two-part contract* (DT Q2).
Phase 1's other deliverables (lock the mutation contract; bound the ~6-component inventory) are
documentation the discovery pre-delivered; this discuss is the genuine decision.

---

## Grounding (how reads resolution actually flows — read before deciding)

For **reads**, resolution runs at **two text-only points**, and the chain-step graph straddles them:

- **Pre-compile enrichment** — `handlers.py:1657`: `resolve_query_entities(last_user_text)` → enriches the
  LLM messages. **No `desktop` arg.**
- **Dispatch-time** — `_step.py:254` → `_extract_semantic_step_params(step_text)` (`:555-568`):
  `resolve_query_entities(step_text)` projects entity/numeric/format params into the step at execution.
  **No `desktop` arg.** Runs on the *step text*, which may be **derived mid-chain** (post source-routing,
  post prior-step output) — text that did not exist at compile.

Two facts that decide this:

1. **Neither point uses runtime state today** — both are text-only. So consolidation is *not* blocked by a
   runtime dependency in the current code.
2. **`resolve_query_entities` has a `desktop` param, built but never wired** (`resolver.py:61` — "accepted
   for the eventual live-Flame validation pass"). **This unwired `desktop` IS the contextual-resolution gap**
   (defect #3): the open sequence lives in desktop state; the resolver can take it; nobody passes it → "this
   sequence" falls through → the LLM fills from a docstring example (`30sec_21`, D3). The Phase-4 contextual
   fix = wiring `desktop` into resolution — and **desktop/runtime state is most naturally available at
   dispatch (live Flame), not at compile.**

---

## The decision

**Option A — consolidate reads resolution pre-graph.** Hoist all reads resolution to compile so the graph
carries resolved refs (uniform single contract, like mutations). *Cost:* (a) can't resolve **derived
step-text** that doesn't exist until runtime; (b) fights the contextual fix — forces **desktop state to be
available at compile**, against the runtime grain.

**Option B — explicit two-part reads contract.** Formalize the reads "Resolved Intent" as **graph-shape +
dispatch-resolution-output**; Phase 3 validates *both* points. *Cost:* the reads verdict is two-part (not a
single graph check); preserves topology.

### Lean: **Option B (two-part contract)** — grounded, not a preference

1. **The straddle is real, not accidental.** Reads genuinely complete resolution at dispatch, for a reason:
   derived step-text doesn't exist at compile. Consolidation can't cover that class.
2. **The contextual fix wants dispatch.** Wiring `desktop` (defect #3) belongs where runtime state lives —
   dispatch/live-Flame. Option B makes the dispatch resolution point the natural, *named* home for it;
   Option A would have to hoist runtime state into compile.
3. **Formalize-not-build.** B preserves the battle-tested topology and hardens it with a contract; A is an
   invasive resolution-site move (`[[feedback-brief-examples-as-behavioral-reference-shapes]]`).

So: **reads = two-part contract** (graph-shape validated at compile; resolution-output validated at
dispatch), and the Phase-3 oracle scores reads at both points (no blind spot on the majority chat path).

---

## Two companion items Phase 1 must also settle (surfaced by the grounding)

- **Mutation-contract integrity check (verify, don't assume).** `_extract_semantic_step_params` (`:254`)
  runs for *every* step at execution — including the C2 executor step at **apply**. Phase 1 must verify that
  apply-time semantic extraction does **not** override the **ratified** graph's explicit params — else
  "graph IS the contract" for mutations is violated (applied ≠ ratified). Likely fine (D2 showed the wrong
  value was already in the ratified graph), but it's an integrity claim to confirm, not assume.
- **Redundant text-only resolution (minor).** Enrichment (pre-compile) and dispatch both run text-only
  `resolve_query_entities`. Under Option B they stay (different inputs: original message vs derived step
  text), but Phase 1 should document *why both exist* so it doesn't read as accidental duplication.

---

## What this feeds

- **Phase 3a** validates reads at both contract points (the oracle's reads verdict is two-part).
- **Phase 4** lands the contextual fix at the dispatch resolution point (wire `desktop`) — Option B names
  where it goes.
