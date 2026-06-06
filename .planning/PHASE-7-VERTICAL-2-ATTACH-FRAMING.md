# FRAMING — Phase 7, Vertical 2: attach the dispatcher to the real lifecycle

**Status:** RATIFIED — **B (event-driven, execution-stage event → dispatch consumer)**, with Creative's two-seam split (prove via replay; primary `routing→execution` is a separate later seam). Brief: `PHASE-7-VERTICAL-2-ATTACH-BRIEF.md`. Grounded against `main @ ffb7bc9`. Follows V1 (`6d22d14`, RESOLVED). Parent: `PHASE-7-INVOCATION-FRAMING.md`.

**Why this, not Pipeline (Creative's sequencing call, ratified by the room's "ready for the widening"):** *the seam is solved; the attachment point is not.* V1 proved the dispatcher round-trips in isolation. The highest-value unknown now is what happens when it's attached to the **real lifecycle** — that's where hidden assumptions surface. Pipeline/Vision already benefit from V1's spine but don't stress the integration point. **Consume the proven callable, don't redesign it; wire it and see what breaks** — not another abstraction pass. [[feedback_substrate_before_consumer_landing]]

---

## Grounding discovery — "what breaks" is already visible (the gap is structural, not a one-liner)
Live reads @ `ffb7bc9`:
1. **The primary lifecycle never enters execution.** The stage DAG declares `routing → execution` legal (`engine.py:32`; stages `ingest→spec_convergence→routing→execution→audit→promotion→publish`), but **`to_stage="execution"` is performed ONLY in `replay.py:277,321`.** No primary (first-run) path transitions a fresh plan from `routing` into `execution`. So before dispatch can attach, *something must drive routing→execution in the primary path* (or we confirm replay is the only intended trigger today).
2. **No `driver_registry` is threaded near any transition.** A `GenerationDriverRegistry` is held **only** by `worker.py` (`:44`). `engine.py` and `replay.py` have no registry. But `dispatch_plan(plan, *, driver_registry, session_factory, event_appender)` (`dispatcher.py:79-84`) *requires* one. So attaching dispatch means **deciding who owns/threads the registry** to the attach point.
3. There is already an **execution-stage-aware consumer**: `event_consumer.py:82` branches on `lifecycle.current_stage == "execution"`. A natural attach surface may already exist.

⇒ Vertical 2 = (a) ensure a run reaches `execution` with a plan, (b) thread a `driver_registry` to the attach point, (c) call `dispatch_plan` there, (d) **re-run the generation proof through the FULL real lifecycle** (not a direct `dispatch_plan` call). Findings from (a)/(b) — especially any hidden assumption that surfaces — are first-class output, per Creative.

## The one decision — where does dispatch attach? (fork)
- **Option A — inline at the transition:** whatever performs `routing→execution` calls `dispatch_plan` directly afterward.
  - *For:* simplest, explicit, one call site.
  - *Against:* couples transition to dispatch; every transition site (replay + any future primary) must remember to dispatch; registry must thread into the transitioning component.
- **Option B — event-driven via the execution-stage consumer (Orch lean):** the transition just enters `execution` (emitting the stage-entered event); an execution-stage handler/`event_consumer` reacts and calls `dispatch_plan`.
  - *For:* matches the **existing pattern** (`event_consumer.py` already keys on the execution stage); decouples — replay AND any primary path get dispatch *for free* by merely transitioning; keeps the dispatcher a *consumed callable* (Creative's "consume, don't redesign"); the consumer owns the `driver_registry` (mirrors how `worker.py` owns one — likely the *same* instance shared with the poller).
  - *Against:* one more indirection to trace; must ensure exactly-once dispatch on stage entry (not on every event while in-stage).

**Orch lean: B.** It's the established pattern, it makes the attachment point uniform across replay/primary, and it honors "consume the callable." The registry-ownership question resolves cleanly under B: one `GenerationDriverRegistry` instance, owned where the consumer + poller are wired, shared by both (dispatch submits into it, poller polls out of it).

## Scope (CANDIDATE)
- **IS:** drive/confirm `routing→execution` in the lifecycle so a run reaches execution with a plan; thread one `driver_registry` to the attach point; attach `dispatch_plan` (per the fork); **re-run the generation proof end-to-end through the real lifecycle** (stub driver, real everything else); report any hidden assumption surfaced.
- **IS NOT:** ❌ Pipeline/Vision pathways (next, after attach is proven) · ❌ real Generators backend · ❌ `poll(request_id)` signature alignment / real-driver adapter (still deferred — V1 Q1) · ❌ any new abstraction over the dispatcher (Creative: resist generalizing) · ❌ daemon/process-wiring of the continuous poller beyond what the proof needs.

## Recommendation
The fork (A vs B) is the only real decision; my lean is **B (event-driven, existing pattern)**, strong enough to ratify in one breath unless the room prefers A. Everything else is grounded wiring + the discovery re-run. Suggested: **confirm B → I draft the V2 brief.** Per the split: DT then verifies the *full-lifecycle* round-trip (not the isolated one) and reports what the attachment surfaced; Creative already gave the sequencing.

## Orch's prior (held lightly)
Attach event-driven (B); thread one shared registry; prove it by re-running the generation round-trip through `ingest→…→execution→dispatch→submit→poll→terminal`. Expect the attach to surface at least one hidden assumption (the primary path doesn't even transition to execution today — that alone is a finding). That discovery is the point of the rung.

---

## RATIFIED — B, with the two-seam split (Creative, strong; Orch concur; 2026-06-05)
**B ratified as the attachment model:** *"execution" is a STATE, not an action — the dispatcher is what happens **because** something entered execution, not what causes execution to exist.* Inline (A) encodes `transition→dispatch` at every callsite, which is exactly the divergence class grounding already caught (replay enters execution; primary doesn't; a third path would forget too). B flips the dependency: *if a run reaches execution, dispatch happens* — the failure mode becomes "why didn't we reach execution?" not "which codepath forgot to dispatch?" Registry ownership resolves cleanly: one `GenerationDriverRegistry` owned by the execution-runtime path, shared by dispatch-in and poll-out (worker already depends on it).

**The load-bearing refinement — SPLIT the two seams (do NOT solve in one motion):**
1. *"What causes a fresh plan to enter execution?"* — the primary `routing→execution` trigger. **Separate seam, NOT this vertical.**
2. *"What happens after a run reaches execution?"* — dispatch is consumed. **THIS vertical.**
Bundling them makes any failure ambiguous (routing-gap vs dispatch-consumption). So V2 changes **exactly one thing — entering execution causes dispatch — and proves it against the path that ALREADY reaches execution (replay).** Everything else stays identical, so whatever breaks is genuinely lifecycle-attachment-related.

**Success criterion (Creative — NOT "generation completed"):** *a real lifecycle transition reaches execution and the dispatcher is consumed automatically, with **no callsite-specific dispatch logic**.* The generation terminal is the evidence; the *property* being proven is automatic consumption-on-state-entry.

**Architecture symmetry (grounding):** the existing `GraphEngineEventConsumer` already consumes the **end** of execution (`generation_artifact_terminal` → advance to audit). V2's dispatch consumer is its **mirror** — consume the **entry** to execution (the `to_stage="execution"` stage-transition event, `engine.py:166`) → `dispatch_plan`. Both bookends, same event-consumer shape. ⇒ V2 brief: `PHASE-7-VERTICAL-2-ATTACH-BRIEF.md`.
