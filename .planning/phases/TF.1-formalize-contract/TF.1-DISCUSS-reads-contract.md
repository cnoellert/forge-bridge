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

---

## RESOLUTION (DT + Creative — Option B, REFRAMED + hardened)

Option B is adopted, but the room generalized it past "reads have a two-part contract." The grounded
correction (DT, correcting his own D2; Creative's synthesis):

### The axis is NOT reads-vs-mutations — it's **compile-resolved vs context-resolved**

DT confirmed `desktop` is architecturally **only reachable at dispatch** (the chat handler imports no Flame
client; `resolve_query_entities`'s `desktop` is a passed-in Mapping the resolver never fetches; only the
dispatch path via `mcp.call_tool → flame_*` touches Flame — so desktop-at-compile would mean a Flame
round-trip in the hot stateless-compile path). Consequence: **a contextual mutation straddles too.**
"rename *this sequence*" compiles to a graph carrying the unresolved ref; desktop resolves it at dispatch —
**post-ratify**. D2's "mutations: graph IS the contract" held in E2E-01 only because compile happened to
bake a concrete (wrong, example-lifted) name in. So the real contract axis:

| Parameter class | Contract | Applies to |
|---|---|---|
| **compile-resolved** (concrete at compile) | chain-step graph IS the full contract; validate at compile | reads + mutations |
| **context-resolved** (contextual ref needing desktop/runtime: "this sequence", "last 013 shot", "current project", derived step-text) | **two-point**: graph captures intent + dispatch resolves; validate at *both* | reads + mutations |

The TF.1 contract is organized around this axis, not operation type. (Refines the NLT-DISCOVERY-CLOSE
reads/mutations framing — the boundary follows *contextuality*.)

### Shape A coupling (explicit contract clause)

Resolving a mutation's contextual target *after* ratify **is Shape A working as designed** (ratify the rule
+ capability; resolve the concrete target at apply) — not a new integrity violation. Visible consequence the
contract must state: a contextual-mutation preview shows an **unresolved ref** ("rename this sequence"),
ratifiable **only under Shape A**. Defect #3 is the first concrete architectural expression of Shape A. The
fork for the future: **Shape A** = ratify intent, resolve target later (today); **Shape B** = ratify the
concrete resolved target → *requires* desktop-at-compile (the round-trip we reject now). TF.1 records
`defect-#3-fix-at-dispatch ↔ Shape-A` so a future Shape-B motion knows it inherits this.

### First-class integrity invariant (elevated from companion note → contract clause)

> **Dispatch may resolve refs the graph left unresolved (contextual → concrete); it may NOT override a param
> the operator explicitly ratified.**

That is the line between Shape A working (resolving "this sequence") and a hidden mutation of the ratified
graph (`_extract_semantic_step_params` silently changing an explicitly-ratified value on replay). The
Phase-1 audit checks the `_step.py:254` merge (`{**public_inherited, **semantic_params, **user_params}`)
against this *specifically* — **resolves-unresolved: yes / overrides-explicit: no** — not "doesn't override"
in the abstract. *(DT cites the merge as ending in `user_params`; if explicitly-ratified params occupy that
winning position the invariant may already hold by merge order — the audit confirms, doesn't assume.
`[[feedback-ground-specs-in-actual-files]]`.)*

### Net for Phase 1 plan

TF.1 produces: (1) the contract organized on the compile-resolved / context-resolved axis; (2) the Shape-A
coupling clause; (3) the integrity invariant + its `:254`-merge audit; (4) the bounded inventory. Phase 3
validates context-resolved params at both points (reads *and* mutations).
