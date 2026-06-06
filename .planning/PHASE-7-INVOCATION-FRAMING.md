# FRAMING — Phase 7: capability invocation / dispatch (the federation E2E demonstrator)

**Status:** FRAMING — OPEN (not ratified, not started). Opens the next Bridge Discovery frontier after motion 2 closed (`PHASE-6A-RUNG-2B-FRAMING.md` / `…-RUNG-B-CONVERGENCE.md`). Grounded against `main @ 4e43c56` via three parallel Explore passes over forge-bridge + forge-contracts + the three siblings (citations inline). Opened by Orch 2026-06-05.

**Naming:** the proof sequence (`forge-contracts/docs/FEDERATION-PROOF-SEQUENCE.md:174`) calls this **"Phase 7 — End-To-End Demonstrator"** (ADR-000 = Phase 0, so this is *planning* Phase 8 in offset numbering). Use the name **Phase 7 / E2E demonstrator**. This is bridge's deliverable and the capstone of the federation proof.

---

## What Phase 7 is
The proof-sequence minimal bar (`FEDERATION-PROOF-SEQUENCE.md:174-186`), one real topology proof:
> Bridge discovers siblings → plans by declared capability → **invokes Vision, Pipeline, AND Generators** → records references, events, lineage, and provenance → **reconciles execution receipts** → assembles manifest/package.

Discovery (Phase 6A) and planning (phase-4b six-pass) are **done**. Phase 7 is the missing verb: **actually executing a planned capability**, across all three sibling families, and folding the results back into bridge's orchestration memory.

---

## Grounded current state — the void between plan and execution

**Execution today is `generation`-only AND poll-only.** (Explore pass 1)
- The only execution loop is `worker.py` `GenerationPoller` — it *polls already-submitted* generation artifacts (`worker.py:32-212`); it does not submit/launch anything.
- The driver protocol is **poll-only**: `GenerationDriverProtocol` declares `backend_id` + async `poll(artifact)` (`drivers.py:17-32`) — **no `submit()`/`invoke()`**.
- The planner produces `ExecutionPlan.operator_sequence` (`planner_passes.py:336-351`: a hard-coded `operator_id="generate_video_from_image"`, `backend_id`, `output_artifact_id`) + `backend_assignments`. **Nothing consumes `operator_sequence` for dispatch** — only `manifest.py:378` reads it, for provenance.
- Transition to the `"execution"` stage just stores `plan_id` (`replay.py:274-324`) — **no artifact is spawned, nothing is invoked.**

**⇒ The gap (the void):** plan produced → lifecycle says "execution" → **[nothing executes]**. Even for generation, the submit step doesn't exist; for execution/perception families, no invocation machinery exists at all.

## The family-shaped reality — THREE pathways, not two (refines the 2A constraint)
(Explore pass 3, grounded in sibling repos. The 2A ruling said "invocation is family-shaped, no uniform abstraction"; grounding shows **three** distinct shapes:)

| Family (sibling) | Invocation mechanism | Identity | Bridge's role | Exists in bridge? |
|---|---|---|---|---|
| **generation** (forge-generators) | driver `submit()→request_id` then `poll(request_id)` async lifecycle (`drivers/types.py:45-68`) | `BackendIdentityTriple` (surface/path/auth/revision), keyed by **surface** (`artifacts/identity.py:22-40`) | **hold + drive** the driver; submit then poll to terminal | poll half only; **submit missing**; registry keyed by `backend_id` not `surface` |
| **execution** (forge-pipeline) | Pipeline-owned **plugin entry-point** `forge_core.plugins` + `dispatch(request)→OperationResult`; **receipts Pipeline-owned** (`bridge/contract_registry.py:58-60`, `operations/receipts.py:53-69`) | none — Pipeline is **stateless**, no backend_id | **dispatch then hold a receipt REFERENCE** for reconciliation; bridge does **NOT** poll | **nothing** |
| **perception/validation/editorial** (forge-vision) | stateless sync tool-call, request/response, one graph event (`bridge/adapters.py`); `legacy_fastmcp_surface` | none | **call directly**, record result | **nothing** (only used as planner transform-providers today) |

**This is the load-bearing architectural fact of Phase 7:** three irreducibly different dispatch pathways (async-driver / plugin-receipt / sync-call). The 2A ruling holds and strengthens: **do NOT build a uniform `InvocationHandler`** — build three pathways onto one dispatcher spine.

## The `backend_id` reconciliation seam is now DUE
2A named this seam and set its maturation condition: *"a plan step first needs to execute a selected capability (Phase 7)."* That condition has **arrived.** Three unreconciled id systems (Explore pass 1):
- **A — registration:** registry keyed by the driver's own `handler.backend_id` (`registration.py:82-114`).
- **B — planning:** `backend_id_from_snapshot_entry` derives `f"{surface}.{path}"` from declaration metadata `backend_identity_triple` (`planner_passes.py:23-27`).
- **C — execution:** `resolve_backend_id(artifact)` formats the same triple off the runtime artifact's `execution_provenance` (`drivers.py:42-54`).

They must match by value; **nothing validates it.** Phase 7 dispatch is exactly where B→A (resolve plan-step id to a registered driver) and C (stamp the artifact so the poller reverse-resolves) get bridged. **Extra wrinkle (grounded):** bridge's registry keys by `backend_id` while Generators' real driver keys by `surface` (`bridge/context.py:12-29`) — the seam has a *bridge-protocol-vs-sibling-protocol* mismatch to reconcile too.

## Contract-light invocation (constitutional — not an oversight)
(Explore pass 2.) The contract defines **no** invocation-envelope / dispatch / receipt protocol in v0.1. ADR-000 mentions "invocation envelopes" but no type exists. **Execution receipts are Pipeline-owned execution truth — constitutionally kept OUT of `forge-contracts`** (`ADR-000:130-137`: "Bridge does not own the fact that execution occurred… not a reason to move receipt storage into forge-contracts"). The currency the contract *does* provide: `ArtifactRef`, `Reference`, `ArtifactLocation`, `ReferenceResolution` (`references.py:14-57`). ⇒ **Bridge defines its OWN bridge-local invocation envelope** built on contract reference vocabulary; it does **not** wait for a contract type and does **not** absorb Pipeline's receipts — it holds receipt *references* and reconciles.

---

## Open decisions (Orch leans; the structural one flagged for convergence)

### D1 — Thin-vertical shape: which family first, one-deep vs all-shallow? **[Orch lean: generation-deep first — CONVERGENCE-WORTHY]**
The proof bar needs all three families invoked — but that's the *capstone*, not the de-risking step. Following the Phase-6A "prove the seam, then widen" pattern, the first vertical should exercise the **genuinely new substrate** (the dispatcher + the backend_id seam) with the least incidental surface.
- **Generation-deep first** (my lean): the most machinery already exists (poll loop, artifact store, driver registry); the gap is `submit()` + dispatcher + backend_id reconcile — which *is* the new substrate. It exercises the named seam end-to-end. Async lifecycle is the hard case; proving it first de-risks the most.
- **Counter — Vision/perception-thinnest first:** simplest pathway (sync, no lifecycle, no backend_id) — proves "plan → invoke → record" minimally, but **skips the hard parts** (dispatcher-to-async, the seam, receipts) — a degenerate proof.
- **Counter — all-three-shallow:** directly targets the proof bar, but pays all three pathways at once (big, multi-front).
This is the convergence question — it sets the whole Phase-7 sequence.

### D2 — The dispatcher (the new substrate spine) **[Orch lean: a plan-consuming dispatch service at the execution-stage transition]**
A service that reads `ExecutionPlan.operator_sequence` when a run enters `"execution"`, and per step routes to the family-appropriate pathway. This is the spine all three pathways plug into. Open: does it live as a new `orchestration/` module (e.g. `dispatcher.py`) consuming the same engine/worker substrate? (Grounding: `engine.py`/`worker.py` exist; the dispatcher slots between plan-storage and the poll loop.)

### D3 — Fill the `backend_id` seam **[Orch lean: resolve-and-validate at dispatch]**
Dispatch resolves plan-step `backend_id` (B) against the driver registry (A), **blocks with a clear refusal if no driver/plugin matches** (no silent no-op), and stamps the artifact's `execution_provenance` (C). Plus: align bridge's `GenerationDriverProtocol` with Generators' real `submit()+poll()` + reconcile the `backend_id`-vs-`surface` keying. [[feedback_pre_orchestration_resolution_paralysis]] (relax discovery, tighten action — validate at the action boundary).

### D4 — Three pathways, no uniform abstraction **[Orch lean: ratify — it's the 2A ruling, reconfirmed]**
generation (driver submit/poll) · execution (plugin dispatch + receipt-reference reconcile) · perception (sync call). One dispatcher spine, three family-shaped handlers. **No `InvocationHandler` superclass** until two families demonstrably need the same one (they don't). [[feedback_transitional_structure_naming]]

### D5 — Bridge-local invocation envelope + Pipeline-owned receipts **[Orch lean: ratify]**
Define a bridge-local invocation envelope on contract reference currency (`ArtifactRef`/`Reference`); receipts stay Pipeline-owned, bridge holds references and reconciles (honors ADR-000). Don't wait for / don't push a contract invocation type.

---

## Scope guard (CANDIDATE — to be ratified at discuss)
- **IS (proposed):** a dispatcher spine that executes a planned capability; the first thin vertical (family TBD by D1) end-to-end (plan → invoke → record references/events/lineage/provenance); fill the backend_id seam at dispatch; align the generation driver protocol (submit+poll).
- **IS NOT (this first vertical):** ❌ all three families at once (unless D1 says all-shallow) · ❌ a contract invocation-envelope type (contract-light is constitutional) · ❌ absorbing Pipeline's receipts into bridge (reference + reconcile only) · ❌ a uniform `InvocationHandler` · ❌ the full E2E demonstrator/manifest-of-all-three (that's the capstone the vertical builds toward).

## Convergence recommendation
**D1 (thin-vertical shape) is the convergence-worthy decision** — it sequences the entire phase and trades "de-risk the hard substrate" (generation-deep) against "hit the proof bar directly" (all-shallow) against "smallest first step" (Vision-thinnest). D2–D5 have strong enough leans (and direct grounding) to ratify at discuss. Suggested: **converge D1, ratify D2–D5 at discuss, then I draft the first-vertical brief.** Per the split: DT to verify the grounding here (especially the three-pathway claim + the submit-missing / backend_id-vs-surface findings), Creative on D1's sequencing philosophy.

## Orch's prior (held lightly)
Lean **generation-deep first.** It's the family with the most existing substrate and the smallest *new* surface that still exercises the actual hard parts — the dispatcher and the now-due backend_id seam. Vision-first proves a degenerate path; all-shallow pays three fronts before any one is proven. Generation-deep gives a real end-to-end spine that Pipeline (receipt-reconcile) and Vision (sync) then widen onto — exactly the Phase-6A "prove the seam, then widen" shape that's served us. Converge me.
