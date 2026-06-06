# FRAMING — Phase 7, Vertical 3: prove the spine is ALIVE (daemon-start the execution runtime)

**Status:** RATIFIED — **D1 = full execution-runtime set** (Creative ruling; DT direction; Orch concur). Start in `:9996` lifespan; one shared registry (empty in prod); stub injected only for the proof. Boundary: *"V3 establishes the runtime; it does not expand the federation."* Brief: `PHASE-7-VERTICAL-3-OPERATION-BRIEF.md`. Grounded against `main @ 1842996`. Follows V2 (`447fc8d`, DT-verified). Parent: `PHASE-7-INVOCATION-FRAMING.md`.

**Why this, not widening (DT forward-pointer + Creative vote A, Orch concur):** V1 proved dispatch *can* exist; V2 proved it *attaches* to execution. The largest remaining uncertainty is no longer architectural — it's **operational**: the consumer works but **nothing starts it.** Widening to Pipeline/Vision now means debugging capability-family + plugin + daemon-lifecycle differences *at once*; starting the runtime first asks the clean question — *does the proven spine survive contact with the actual daemon lifecycle?* The progression: **V1 can-it-exist → V2 can-it-attach → V3 does-it-run.** [[feedback_substrate_before_consumer_landing]]

---

## Grounding correction — there is NO running precedent to mirror (V3 *establishes* the runtime)
Creative's framing leaned on "mirror the `GenerationPoller` precedent (daemon → starts worker)." **Grounding @ `1842996`: that precedent isn't alive.** `grep` for worker startup outside tests: **none of the three execution-runtime workers is daemon-started** — not `DispatchOnExecutionEntryConsumer`, not `GenerationPoller`, not the terminal `GraphEngineEventConsumer`. All three are referenced only in exports + tests; the only `run_forever` calls in production are unrelated (WS server, shell loop, clients). ⇒ V3 is not "add one sibling worker to an existing managed set" — it's **establishing the execution-runtime managed-task set in the daemon for the first time.**

**Consequence for scope:** Creative said "start the consumer," but the success criterion ("run the full generation proof through the actual daemon") **requires more than the consumer** — the consumer dispatches a *submitted* artifact, but without the poller running in-process it never reaches terminal. So the alive-proof set is at minimum **consumer + poller**, and to close the loop (execution→audit) the **terminal consumer** too. This is not scope-creep; it's what "the full proof through the daemon" demands.

## Grounded substrate
- The `:9996` daemon has a `_lifespan` (`mcp/server.py`) with a documented multi-step startup owning canonical singletons + background tasks (`startup_bridge()`, AsyncClient→state_ws, …). **This is the natural managed home** for execution-runtime workers (asyncio tasks, shutdown on teardown).
- The three workers each already have a `run_forever(shutdown_event=…)` loop (`worker.py`, `event_consumer.py`, the new `dispatch_consumer.py`) — they're *built to be started*, just never started.
- V2 proved dispatch + poll share one `GenerationDriverRegistry`; V3 elevates that to daemon scope.

## Decisions (strong leans — small set)

### D1 — Which workers does V3 start? **[Orch lean: the execution-runtime SET — dispatch consumer + poller + terminal consumer]**
The round-trip-through-the-daemon criterion needs consumer (dispatch) + poller (terminalize) at minimum; the terminal consumer closes execution→audit (both bookends already exist). Start them as one coherent "execution runtime" unit. (Consumer-only would prove "events are consumed" but not "the generation proof runs through the daemon" — Creative wants the latter.)

### D2 — Where do they start? **[Orch lean: the `_lifespan` on :9996, as managed asyncio tasks]**
Co-located with Console/chat in the existing managed lifespan; cancelled on teardown via `shutdown_event`. It's the established managed-task home and what `fbridge up` already brings up. (Alternative — a separate worker process — is heavier ops surface; defer unless the lifespan proves unsuitable.)

### D3 — Registry ownership + the empty-registry wrinkle **[Orch lean: lifespan owns one shared registry; register the faithful stub for the daemon proof]**
One `GenerationDriverRegistry` created in the lifespan, injected into dispatch consumer + poller (V2's shared-registry, daemon-scoped). **Wrinkle (grounded):** a stock daemon has **no drivers registered** (real generation drivers come via the deferred Generators-adapter rung, V1 Q1) — so dispatch would always `dispatch_no_driver`. For V3's alive-proof, **register the V1 faithful-lifecycle stub at daemon scope** so the round-trip completes through the real process. Wiring the *real* Generators driver stays the deferred rung. (This keeps V3 about *aliveness*, not about real backends.)

## Success criterion (Creative — two tiers)
- **Minimal (events consumed):** with the daemon running and **no test harness**, an execution-entry (`stage_advanced`/`to_stage="execution"`) is consumed automatically by the daemon-resident consumer.
- **Full (round-trip alive):** trigger a **replay** against the running daemon → consumer dispatches → poller terminalizes → terminal consumer advances to audit — **all in the daemon process, no harness driving the workers.** This is the V3 bar.

## Scope (CANDIDATE)
- **IS:** start the execution-runtime worker set in the `_lifespan`; one daemon-scoped shared registry; register the stub driver for the proof; prove the full generation round-trip through the actual daemon (triggered via replay — the path that reaches execution); graceful shutdown.
- **IS NOT:** ❌ the primary `routing→execution` trigger (still the separate deferred seam — V3 proves aliveness via replay, not the primary path) · ❌ Pipeline/Vision pathways · ❌ real Generators driver wiring (deferred V1 Q1) · ❌ `poll(request_id)` alignment · ❌ any new abstraction.

## Recommendation
Decisions are small with strong, grounded leans (start the set · in the lifespan · shared registry + stub for the proof). The one thing worth the room's eyes is **D1's scope refinement** — Creative said "start the consumer," grounding says "the full-daemon proof needs consumer+poller(+terminal)." If the room prefers the *minimal* (consumer-only, events-consumed) proof as V3 and defers the poller-in-daemon, that's a smaller V3 — but it doesn't deliver "the full generation proof through the daemon." **Suggested: confirm D1 (full set vs consumer-only) → I draft the V3 brief.** DT then verifies aliveness in the real process (no harness); Creative set the direction.

## Orch's prior (held lightly)
Start the **full execution-runtime set** in the lifespan with a daemon-scoped shared registry and the stub driver, and prove the replay-triggered round-trip end-to-end **in the running daemon, no harness**. That's the truest form of "is it alive," and the grounding correction (nothing runs today) means we're establishing the runtime regardless — better to establish the coherent set than a lone consumer that can't round-trip.
