# FRAMING — Phase 7: capability invocation / dispatch (the federation E2E demonstrator)

**Status:** FRAMING — **D1 CONVERGED = generation-first, thin** (unanimous; Orch synthesis at foot). D2–D5 ratifiable at discuss; first-vertical brief next. Opens the next Bridge Discovery frontier after motion 2 closed (`PHASE-6A-RUNG-2B-FRAMING.md` / `…-RUNG-B-CONVERGENCE.md`). Grounded against `main @ 4e43c56` via three parallel Explore passes over forge-bridge + forge-contracts + the three siblings (citations inline). Opened by Orch 2026-06-05.

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
- The planner produces `ExecutionPlan.operator_sequence` (`planner_passes.py:336-351`: a hard-coded `operator_id="generate_video_from_image"`, `backend_id`, `output_artifact_id`) + `backend_assignments`. **Nothing consumes `operator_sequence` for dispatch** — it is read at **4 sites** (`lineage_graph.py`, `rule_checks.py:44`, manifest, `orch_entity_views.py:183`), all provenance/validation, none dispatch (count corrected by DT verify — see § "DT grounding verification").
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

## DT grounding verification (live reads — bridge @ HEAD, sibling repos @ `/Users/cnoellert/GitHub`)
All three flagged findings **VERIFIED**.

**Finding 2 — submit-missing / plan-never-dispatched: VERIFIED.**
- `drivers.py` `GenerationDriverProtocol` is **poll-only** (`async def poll` :27; no `submit`/`invoke`/`dispatch`). `worker.py` `GenerationPoller` = `poll_once`/`run_forever`/`_poll_artifact` — polls *already-submitted* artifacts, no submit.
- `operator_sequence`: produced at `planner_passes.py:336` (hard-coded `operator_id="generate_video_from_image"`); **consumed for provenance/validation only** and **never for dispatch.** ⚠ **Count correction:** it is read at **4 sites** (`lineage_graph.py`, `rule_checks.py:44`, `manifest`, `orch_entity_views.py:183` accessor), not "only `manifest.py:378`." The substantive *no-dispatch-consumer* claim is unaffected.
- `replay.py` execution transition (`:277`, `:321`) stores `plan_id`; spawns/invokes nothing.

**Finding 1 — three irreducible pathways: VERIFIED (sibling protocols read).**
- **generation** (`forge-generators/src/forge_generators/drivers/types.py:45-67`): `BackendDriver` Protocol = `async submit()→(request_id, datetime)` **+** `async poll(request_id)→PollResult` **+** `cancel` — full async lifecycle. Bridge's `GenerationDriverProtocol` has the **poll half only** → submit genuinely missing, and the two protocols diverge.
- **execution** (`forge-pipeline/forge_core/operations/receipts.py`): `ExecutionReceipt` "Durable execution receipts **owned by Pipeline**," points-at bridge identities via contract `Reference`; `contract_registry` advertises "receipt reference for later Bridge reconciliation." Bridge reconciles a *reference*, does not own or poll receipts.
- **perception** (`forge-vision/forge_vision/bridge/adapters.py`): `classify_shot()` calls `forge_vision.runtime.executor.invoke`, returns the §4.1 dict, emits exactly one graph event — stateless **sync** call, no backend_id, no lifecycle.
- ⇒ three genuinely different dispatch shapes; the **2A no-uniform-abstraction ruling reconfirmed.**

**Finding 3 — backend_id-vs-surface keying mismatch: VERIFIED.**
- bridge `GenerationDriverRegistry.get_driver(backend_id)` (`drivers.py:76`) keys by the **composite** `backend_id` (`f"{surface}.{path}"`).
- Generators `bridge/context.py:23` `get_driver(backend_surface)` keys by **surface alone** (`self.drivers[backend_surface]`). `BackendIdentityTriple` = surface+path+auth+revision (`identity.py:23`) — surface is one component. Real bridge-protocol-vs-sibling-protocol mismatch to reconcile at dispatch (D3).

**DT read on D1 (sequencing philosophy is Creative's):** the three things Phase 7 must *newly* build — the submit verb, the now-due `backend_id` seam, and the surface mismatch — **all live in the generation pathway.** So generation-deep genuinely exercises the hard substrate (not a degenerate proof); the grounding supports Orch's lean *on the merits*. The de-risk-hard-vs-hit-proof-bar trade itself remains Creative's call.

## Convergence recommendation
**D1 (thin-vertical shape) is the convergence-worthy decision** — it sequences the entire phase and trades "de-risk the hard substrate" (generation-deep) against "hit the proof bar directly" (all-shallow) against "smallest first step" (Vision-thinnest). D2–D5 have strong enough leans (and direct grounding) to ratify at discuss. Suggested: **converge D1, ratify D2–D5 at discuss, then I draft the first-vertical brief.** Per the split: DT to verify the grounding here (especially the three-pathway claim + the submit-missing / backend_id-vs-surface findings), Creative on D1's sequencing philosophy.

## Orch's prior (held lightly)
Lean **generation-deep first.** It's the family with the most existing substrate and the smallest *new* surface that still exercises the actual hard parts — the dispatcher and the now-due backend_id seam. Vision-first proves a degenerate path; all-shallow pays three fronts before any one is proven. Generation-deep gives a real end-to-end spine that Pipeline (receipt-reconcile) and Vision (sync) then widen onto — exactly the Phase-6A "prove the seam, then widen" shape that's served us. Converge me.

---

## Orch synthesis — D1 CONVERGED (2026-06-05)

**D1 = generation-first, thin. UNANIMOUS** (Orch lean + DT-on-the-merits + Creative vote).

**The decisive reframe (Creative):** generation is chosen **not** because it's the most *realistic* path but because — post-grounding — it's the only path that actually **exercises the missing architecture.** DT's grounding showed the three genuinely-new things Phase 7 must build (the **submit** verb · the now-due **backend_id** seam · the **surface** mismatch) form a **cluster, all on the generation pathway.** A cluster of unimplemented seams on one path is where the architecture still has unanswered questions. ⇒ *Choose the path that teaches the federation the most, not the one that proves it fastest.* Perception-first or execution-first would each be another green check that leaves the hard substrate untouched. (Phase-X echo: the meaningful findings lived exactly where the system met reality it had never been exercised against — loaded-vs-selected, push-vs-pull, `get_value()`. The submit gap has that same smell.) [[feedback_ecological_validity_after_converged_phase]]

**The converged thin-vertical bar (Creative's shape — the proof is the LIFECYCLE, not image generation):**
> capability discovered → capability selected → **submit invoked** → bridge obtains a handle/receipt → **poll finds it again**

If that round-trips, four unknowns retire in one slice: submit exists · backend resolution exists · surface resolution exists · poll attaches to the right thing.

**Scope discipline (carry into the brief):** *don't build all of generation.* Brief-shaping notes for when I draft it:
- **Stub driver, faithfully mirroring Generators' real `BackendDriver` protocol** (`submit()→(request_id, ts)` + `poll(request_id)→PollResult`, **surface keying**) — NOT a real remote backend call. The point is the *bridge-owned* lifecycle. **But the stub must mirror the real sibling protocol exactly** or the vertical proves a degenerate lifecycle and misses the surface-reconciliation ([[feedback_fixture_shape_mirrors_production]]). The resolution path (plan-step `backend_id` → registry → driver) stays **real bridge code** so backend/surface reconciliation is genuinely exercised; only the remote call is stubbed. Real Generators backend = a later widening step.
- **The `backend_id`-vs-`surface` mismatch (D3) MUST be reconciled in this vertical** — it sits on the generation path, so it can't be deferred. Whether bridge re-keys to `surface` or adapts at dispatch is a brief/design call.
- Driver protocol alignment: bridge's poll-only `GenerationDriverProtocol` gains `submit()` to match the sibling.

**D2–D5 — ratifiable at discuss** (their leans now rest on DT-verified facts): D2 dispatcher spine at the execution-stage transition · D3 resolve-and-validate-at-dispatch + protocol/keying reconcile · D4 three pathways no uniform abstraction · D5 bridge-local envelope + Pipeline-owned receipts.

**Next:** ratify D2–D5, then I draft the **first-vertical brief** (generation lifecycle round-trip, stubbed backend, real resolution). Then it's the usual loop — you route to code, DT verifies the round-trip + the surface-reconcile.
