# CONVERGENCE SEED — D3 / Rung B: does raw `CapabilityDeclaration` adoption earn its planner re-ripple?

**Status:** CONVERGENCE — OPEN. Seed drafted by Orch for DT + Creative (+ operator). Grounded against `main @ 9761fa6` (2A `a9ca444`, D4 `85ce467`, D2 `02293f6` all landed + verified). Parent framing: `PHASE-6A-RUNG-2B-FRAMING.md` § D3.

This is the **last piece of motion 2**. D1 (split), D4 (perceptual routing defect), D2 (context de-shadow) are closed. D3 is the one genuinely contested call — opened as a convergence, **not** a foregone "do B."

---

## The question (narrow, burden-flipped)
> Post-2A / D4 / D2 — with `ToolRegistration` duck-typing cleanly, all downstream declaration-pure, the context shadow already retired, and **no proven defect attributable to the record-shadow** — does Rung B (store `CapabilityDeclaration` raw, accept planner coupling to contract churn) earn its planner re-ripple? Or does motion 2 close at **name-alignment-with-insulation**, or at **"don't do B" entirely**?

The burden has flipped. The original question was *"should we stop shadowing the contract?"* (a tidiness goal). Post-cleanup the operative question is the sharper one: **what defect remains that ONLY raw `CapabilityDeclaration` adoption solves?** If the answer is "none," the contest is between B′ (name-align) and C (don't).

## Why this is a convergence, not a brief
Every prior rung had **positive evidence** of a wrong thing: 2A (handler stored in a discovery record, read nowhere downstream), D4 (dead `perceptual` vocab mis-routing a content-policy transform). D3 has none — only an *aesthetic/coupling preference*. Multiple valid end-states, the ripple depends on which philosophy wins, and the cost (planner coupling) is paid against a benefit that is so far unproven. That is convergence territory. [[feedback_arbitration_boundary_discipline]]

---

## Grounded state — the evidence record (live reads @ `9761fa6`)

**What the registry stores today** (`ToolRegistration`, bridge-owned, post-2A): `{tool_id, family, payload_family, schema, capabilities}` — declaration-only (handler removed in 2A).

**The contract type** (`CapabilityDeclaration`, 9 fields): `{contract_version, capability_id, family, owner, summary, payload_family, input_schema, output_schema, metadata}`.

**The existing adapter** (`registration.py:45-59`, `tool_registration_from_capability`) already maps contract→bridge:
`capability_id→tool_id` · `input_schema→schema` · `metadata→capabilities` · `family`/`payload_family` pass through. **This adapter is the insulation seam** the whole contest turns on — it exists today and absorbs contract field names so nothing else sees them.

**The B ripple surface** — every planner read of the record shape (what raw adoption forces to be retargeted):
- `planner_passes.py:84` `tool.capabilities` → `.metadata`
- `planner_passes.py:86, 92, 258, 261` `tool.tool_id` → `.capability_id` (×4 incl. `provider.tool_id`)
- `ToolRegistry.by_family(...)` reads `.family` (unchanged name — but the method moves onto the contract type)
- snapshot persistence already declaration-pure; `pass_1` fallback enumerates `by_family("generation")` only (generation-centric — **survives B unchanged**, see DT grounding item 3).

**Standing facts (DT-grounded, not asserted):**
- The record duck-types; **nothing downstream depends on it being bridge-owned.**
- **Zero proven defect** is attributable to the shadow record post-2A.
- The 4 contract fields bridge does **not** consume — `contract_version, owner, summary, output_schema` — would come along for free under raw adoption (unused surface) or stay excluded under a bridge-owned record.

---

## The three candidate end-states

### Position A — Adopt raw `CapabilityDeclaration`
Registry stores the contract type directly; **delete `ToolRegistration` and the adapter**; planner reads `.capability_id`/`.metadata`/`.input_schema`.
- **For:** single source of truth; registry *is* the contract; no bridge-owned twin to maintain; future contract fields (`owner`, `output_schema`) available the moment Phase 7 invocation wants them.
- **Against:** **couples the planner to contract churn** — any contract field rename/restructure ripples straight into `planner_passes.py`; imports 4 unconsumed fields now; removes the only insulation seam; pays a planner re-ripple cost for no present defect.

### Position B′ — Name-alignment-with-insulation
Keep a **bridge-owned** record but rename its fields to the contract's (`capability_id`, `input_schema`, `metadata`); the adapter becomes near-identity; planner reads contract-shaped names **through** the bridge type.
- **For:** planner gets contract-vocabulary legibility (the readability win of A) **and** keeps the adapter seam (contract churn is absorbed in one place, not the planner); no unconsumed fields.
- **Against:** still a "shadow" by strict reading (a bridge type mirroring a contract type); two names for one concept persists at the type level; the adapter must be maintained (it already is).

### Position C — Don't do B (close motion 2 at D2)
Leave `ToolRegistration` as-is. Motion 2 ends here.
- **For:** YAGNI — it duck-types, downstream is declaration-pure, no defect; the burden-flip says don't pay a planner ripple for tidiness; every rung so far earned its keep with positive evidence and this one can't.
- **Against:** leaves a known naming divergence (`tool_id` vs `capability_id`) as latent cognitive cost; defers a reconciliation that Phase 7 invocation *might* force anyway (see open question 3); "stop shadowing the contract" stays partially unmet.

---

## What the convergence must settle (questions for the panel)
1. **Is there ANY defect or coupling attributable to the record-shadow post-2A/D4/D2?** (Burden-flip core. If no — A loses its strongest justification.)
2. **Does Phase 7 invocation change the calculus?** The family-shaped-invocation finding + the named-but-unfilled `backend_id` reconciliation seam are downstream. Does building the invocation/dispatch path *need* `CapabilityDeclaration`'s unconsumed fields (`owner`, `output_schema`) or the raw type — i.e., does A pay off later in a way B′/C can't cheaply retrofit? Or is that inventing requirements before the path exists? [[feedback_transitional_structure_naming]]
3. **Insulation vs single-source — which does bridge actually want at the registry seam?** Is the adapter a liability (drift risk, double-maintenance) or an asset (churn shock-absorber)? This is the philosophical crux separating A from B′.
4. **Cost of the naming divergence under C** — is `tool_id`≠`capability_id` a real ongoing cost, or harmless once documented?
5. **Reversibility** — which positions are cheap to change later? (C→B′ and C→A are both adapter-local; A→B′ requires re-introducing a type. Does "start minimal, escalate on evidence" favor C/B′?)

## What each voice brings
- **DT (grounding/verify):** is question 1 truly "no defect"? Confirm the planner ripple surface is exactly the 5 sites above and nothing reads the record reflectively elsewhere. Ground question 2 against the actual Phase-7 invocation needs if any are knowable.
- **Creative (experience/architecture):** the insulation-vs-single-source philosophy (Q3); whether the naming divergence (Q4) is felt friction; whether B is an inherited pre-2A obligation that should simply be retired.
- **Orch (synthesis):** converge to a lean + the pass-to-code shape (or a "close motion 2, no B" ruling).

## Orch's prior (held lightly — this is a convergence, not a brief)
Leaning **B′ or C over A.** The burden-flip is decisive for me: A pays a planner re-ripple and removes the insulation seam for *no present defect*, betting on a Phase-7 payoff that doesn't exist yet — which is exactly the "design the reconciler before an execution path exists" trap we've named elsewhere. Between B′ and C: B′ if the `tool_id`/`capability_id` divergence is felt friction worth one contained rename; C if it isn't. I do **not** see positive evidence for A today — but Q2 (Phase-7) is the one place that could flip it, and that's DT's to ground. Converge me.
