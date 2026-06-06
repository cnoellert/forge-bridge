# FRAMING — Phase 7, Vertical 4: widen to Vision (perception) — the family-agnosticism test

**Status:** FRAMING — OPEN. First *widening* rung onto the now-alive spine (V1–V3). Grounded against `main @ afec8b1` (dispatcher + event_consumer + planner + forge-vision). Parent: `PHASE-7-INVOCATION-FRAMING.md`. Sequencing: Creative + Orch concur Vision-first (max contrast with generation).

**Why Vision first (Creative's call, Orch concur):** V1–V3 answered *"does the runtime work?"* The next highest-value question is *"does it stay coherent across fundamentally different capability families — or did we build a generation system that happens to dispatch?"* Vision is the **maximal contrast**: synchronous, immediate result, **no backend, no poll loop, no artifact lifecycle** — the opposite of everything generation taught. If it plugs into the same spine cleanly, the spine is proven *family-agnostic*. That's the single highest-information test available now.

---

## Load-bearing grounding finding: the spine is GENERATION-SHAPED at BOTH ends (not yet family-agnostic)
Live reads @ `afec8b1`:
- **Dispatch is generation-shaped.** `dispatch_plan` (`dispatcher.py`) — module docstring literally "Generation dispatch spine" — finds a step via `_generation_step` (requires `backend_id` + `operator_id`), calls `driver.submit(envelope)` → `insert_submitted` (a `DBOrchGenerationArtifact`) → emits `generation_dispatch_submitted`. **No family routing; assumes generation.** A perception step (no `backend_id`, sync) → `dispatch_no_generation_step`.
- **Completion is generation-shaped.** Execution→audit advancement (`event_consumer.py`, the terminal consumer) is triggered by `generation_artifact_terminal` events and decides via `_partition_run_artifacts` counting `orch_generation_artifact` rows. A sync perception step produces **no artifact and no terminal event** → nothing triggers advancement; the run would sit in execution.
- **No result home for non-generation.** Only `DBOrchGenerationArtifact` exists (V1 grounding). A sync perception *result* has nowhere to be recorded today.
- **The planner emits only generation steps.** `operator_sequence` hard-codes `operator_id="generate_video_from_image"`; `pass_1` fallback enumerates only `by_family("generation")`; `pass_3` reads `by_family("perception")`/`by_family("matte")` *only to insert transforms*, never as operator steps.
- **Vision's real shape** (forge-vision, prior grounding): stateless **sync** `executor.invoke` → result dict + one graph event; no backend_id, no lifecycle.

**⇒ Honest framing:** "family-agnostic" is **not yet true.** Vision-first is the rung that introduces (a) **family routing** in dispatch and (b) a **sync-completion path** — or measures how much the generation-shaped spine must bend. This is exactly the test Creative wanted: it tells us whether we built a capability runtime or a generation runtime with extra steps.

## Open decisions

### D1 — Family routing in dispatch **[Orch lean: a family switch, NOT a uniform handler]**
`dispatch_plan` routes a step by its family → the existing generation handler (async: submit→artifact) vs a new **perception handler** (sync: invoke→result). Keep them as distinct family-shaped functions behind a routing switch; **no uniform `InvocationHandler`** (the 2A ruling — invocation is family-shaped). The step's family (or the absence of `backend_id`) selects the handler.

### D2 — The sync-completion path **[THE CRUX — possibly convergence-worthy]**
Generation completes async (artifact→poll→terminal-event→terminal-consumer→audit). Perception completes **synchronously, inline** — no artifact, no poll, no terminal event. So how does a perception step record its result and advance execution→audit? Candidate shapes:
- **(a) Synthesize a terminal-equivalent:** the sync handler records the result as an already-`complete` candidate and emits the event the existing terminal consumer keys on, so advancement reuses the proven path. *Minimizes spine change; but bends a generation-named artifact/event around a non-generation result.*
- **(b) Generic execution-result + family-agnostic advancement:** introduce a non-generation result record and make execution→audit advancement family-agnostic (counts any terminal result, not just generation artifacts). *Truer family-agnosticism; bigger change to the completion path.*
- **(c) Sync handler advances directly:** the perception handler, having an immediate result, advances the run itself. *Smallest, but puts lifecycle-advancement logic in a handler — risks the "callsite-specific" coupling V2 deliberately avoided.*
This is where the spine's family-agnosticism is genuinely decided. **Orch lean: (b) in principle** (it's the real "capability runtime" answer and matches the V2 doctrine — advancement is the runtime's job, reacting to terminal *results* of any family), **but scoped minimally** — and (a) is the legitimate thin-first option if (b) is too big for one rung. Worth the room's eyes.

### D3 — How a perception step reaches execution **[Orch lean: seed + replay; defer the planner]**
The planner doesn't emit perception steps. Rather than teach it (its own seam), **seed a plan with a perception step and reach execution via replay** — same "prove the spine, defer the planner/primary-trigger" discipline used through V1–V3. The *planner-emits-perception* and the *primary `routing→execution` trigger* both stay deferred. This keeps V4 focused on dispatch + completion family-agnosticism.

### D4 — Faithful Vision stub **[Orch lean: sync stub mirroring the real adapter]**
A faithful sync stub mirroring forge-vision's real shape (`invoke`→result dict + one event), registered/resolved the way a real Vision call would be. Remote Vision call stubbed; the bridge-side sync pathway + completion is real ([[feedback_fixture_shape_mirrors_production]]). Real Vision wiring = later.

## Success criterion
A **perception step reaches execution (via replay)** → the dispatcher **routes it to the sync handler** (not the generation path) → invokes → **records the result** → the run **advances execution→audit** — all **without** the async artifact/poll cycle. That round-trip proves the spine is family-agnostic (or, if it can't be done cleanly, names exactly where it's generation-coupled).

## Scope (CANDIDATE)
- **IS:** family routing in dispatch; the perception (sync) handler; the sync-completion path (D2); a faithful Vision stub; prove a perception step round-trips execution→audit via replay.
- **IS NOT:** ❌ Pipeline (execution/receipt) — V5 · ❌ teaching the planner to emit perception steps (separate seam) · ❌ the primary `routing→execution` trigger (still deferred) · ❌ real Vision sibling wiring · ❌ real Generators driver / generation hardening (later) · ❌ a uniform `InvocationHandler`.

## Recommendation
D1/D3/D4 have strong grounded leans → ratify at discuss. **D2 is the real decision** (sync-completion: synthesize-terminal-equivalent vs family-agnostic-advancement vs handler-advances) — it's where "did we build a capability runtime" is answered, and the options have genuinely different blast radii. Suggested: **converge D2** (even lightly), ratify D1/D3/D4, then I draft the V4 brief. Per the split: DT verifies the sync round-trip is real (routed to the sync path, not the generation path; advancement genuinely family-driven); Creative on D2's runtime-philosophy.

## Orch's prior (held lightly)
Vision-first is right. Expect it to reveal the spine is generation-shaped at the completion end (it is) — that revelation *is* the value. Lean D2-(b) family-agnostic advancement as the true answer, (a) as the acceptable thin-first if (b) overruns; route by family (D1); seed+replay to keep the planner deferred (D3). Converge me on D2.

---

## Convergence so far (DT pending — Orch synthesis after)
**Creative: D2 = (b), with a scope guard. D1/D3/D4 ratify.** Reasoning: (a) only proves "Vision can *pretend* to be Generation" — it dodges the architectural question V4 exists to ask; (c) is near-disqualified (handler-advances escapes the runtime — the exact coupling V2 removed). The three-years-from-now test: a new sync/structured/no-artifact/immediate family should hear "the runtime understands completion independently of generation," not "manufacture a fake generation artifact." This is the referent-resolution echo — *the value isn't getting Vision to run, it's discovering the runtime is **artifact-shaped** instead of **completion-shaped.***

**SCOPE GUARD (Creative, load-bearing):** do NOT build the universal capability runtime in the abstract. Build the **minimum family-agnostic completion primitive** — the smallest thing that lets a synchronous perception result be recorded and execution→audit advance *without* a generation artifact — then run Vision through it. If Vision passes: **completion is now the runtime concept; artifacts are merely one way to reach it.** That's the architectural result, not "Vision works." [[feedback_decomposition_recomposition_validation_arc]]

*Awaiting DT grounding/verify on D2-(b) feasibility (what's the smallest completion primitive that the existing terminal consumer / advancement path can be made to honor?), then Orch synthesis → V4 brief.*
