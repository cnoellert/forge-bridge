# BRIEF — Phase 7, Vertical 2: attach dispatch to execution-stage entry (event-driven)

**Status:** EXECUTION-READY (B ratified strong by Creative + Orch; two-seam split). Grounded against `main @ ffb7bc9`. Framing: `PHASE-7-VERTICAL-2-ATTACH-FRAMING.md`.

**Goal — change exactly ONE thing: entering execution causes dispatch, automatically.** A run reaching the `execution` stage emits a stage-transition event; a new consumer reacts to it and calls the proven `dispatch_plan`. No callsite calls dispatch. Prove it against the path that *already* reaches execution (**replay**).

**Success criterion (Creative — NOT "generation completed"):** a *real lifecycle transition* reaches execution and the dispatcher is **consumed automatically, with no callsite-specific dispatch logic.** The generation round-trip terminal is the *evidence*; the *property* is automatic-consumption-on-state-entry.

**Principle:** consume the proven callable, don't redesign it ([[feedback_substrate_before_consumer_landing]]). This is wiring + one new consumer, mirroring the existing `GraphEngineEventConsumer`. No abstraction pass.

---

## The two-seam split (load-bearing — do NOT cross it)
- **THIS vertical:** "what happens *after* a run reaches execution" → dispatch is consumed.
- **NOT this vertical (separate later seam):** "what causes a *fresh* plan to reach execution" — the primary `routing→execution` trigger. Grounding found the primary path never performs `to_stage="execution"` (only `replay.py:277,321` does). **Leave that gap untouched.** V2 proves the attach using **replay's already-real execution transition**, so any failure is unambiguously attachment-related, not routing-gap-related. [[feedback_substrate_pass_translation_open]]

## Grounded substrate (live reads @ `ffb7bc9`)
- `GraphEngine.transition` emits a stage-transition event via `_event_type_for_transition(from_stage, to_stage, …)`, payload carries `run_id`/`from_stage`/`to_stage` (`engine.py:164-174`). **The execution-entry trigger event already exists.** (Confirm its exact `event_type` string for `to_stage="execution"`.)
- The **mirror precedent**: `GraphEngineEventConsumer` (`event_consumer.py`) already consumes the *end* of execution (`generation_artifact_terminal` → advance to audit), via `process_pending()`/`run_forever()` polling `DBEvent` by type. V2's consumer is the *entry* mirror — same shape.
- `dispatch_plan(plan, *, driver_registry, session_factory, event_appender)` (`dispatcher.py:79`) is the proven callable to consume. It needs the plan + a `GenerationDriverRegistry`.
- The lifecycle row carries `plan_id` (set at the execution transition, `replay.py:278,322`); the consumer resolves the plan from it.
- Registry is held only by `worker.py` today — V2 establishes one **shared** `GenerationDriverRegistry` owned by the execution-runtime path (consumer + poller).

## Changes (reference shapes — code owns exact signatures)

### 1. New consumer — `forge_bridge/orchestration/dispatch_consumer.py` (mirror of `event_consumer.py`)
A `DispatchOnExecutionEntryConsumer` (name code's call) that:
- Polls `DBEvent` for the **execution-entry stage-transition event** (the `to_stage="execution"` event type from `_event_type_for_transition`) — same `process_pending(after_event_id)` / `run_forever(shutdown_event)` shape as `GraphEngineEventConsumer`.
- For each: read `run_id` from payload → load lifecycle → guard `current_stage == "execution"` (idempotence: skip if already advanced) → resolve `plan_id` → load the plan → call `dispatch_plan(plan, driver_registry=<shared>, session_factory=…, event_appender=…)`.
- **Exactly-once on entry:** dispatch fires once per execution entry, not on every poll while in-stage. Use the same anchor/`after_event_id` progression the terminal consumer uses, plus the stage guard. Emit a `dispatch_consumed`/`dispatch_skipped` event for observability.
- Holds the **shared** `GenerationDriverRegistry` (constructor injection, like `GenerationPoller`).

### 2. Shared registry ownership
One `GenerationDriverRegistry` instance owned by the execution-runtime wiring, injected into **both** the dispatch consumer (submit-in) and the `GenerationPoller` (poll-out). (Where the runtime composes them — confirm; if there's no single composition site yet, the test wires the shared instance and that's sufficient for V2.)

### 3. NO callsite dispatch
Do **not** add a `dispatch_plan` call at `replay.py`'s transition sites or anywhere else. Dispatch lives **only** in the consumer. (This is the success criterion + acceptance #3.)

### 4. Full-lifecycle round-trip test — `tests/test_phase7_attach_vertical.py` (NEW)
Drive a run through replay's **real** execution transition (the existing replay path that reaches `to_stage="execution"` with a `plan_id`), register the V1 faithful stub driver in the shared registry, then:
- run the dispatch consumer's `process_pending()` → assert it **consumes the execution-entry event and dispatches automatically** (a submitted artifact appears with correct `execution_provenance`) — **with no dispatch call anywhere but the consumer**;
- run `GenerationPoller.poll_once()` (shared registry) → artifact reaches terminal;
- (the existing terminal consumer then advances execution→audit — optional to assert, shows both bookends close).
Negative: an execution entry whose plan has an unresolvable `backend_id` → `dispatch_no_driver` (V1's refusal), no artifact, and the consumer doesn't crash the loop.

## Open items (flag, don't expand)
- **Exact trigger event_type:** confirm what `_event_type_for_transition` emits for `routing→execution` and key the consumer on it (don't guess the string).
- **Idempotence shape:** confirm the stage-guard + anchor progression gives exactly-once dispatch on re-entry/replay-of-replay; if the existing terminal consumer's idempotence model transfers cleanly, reuse it.

## Acceptance
1. **Automatic consumption proven:** a real (replay) execution transition → the consumer dispatches with **zero callsite-specific dispatch logic** (grep: `dispatch_plan(` appears only in `dispatcher.py` def + the new consumer + tests — *not* at any transition site). This is the success criterion.
2. **Full-lifecycle round-trip:** replay→execution event → consumer → dispatch → submitted artifact (real resolution, stub backend) → `poll_once` → terminal. Demonstrate.
3. **Two-seam split honored:** no change to the primary `routing→execution` gap; `to_stage="execution"` site count unchanged (still only replay); the rung does not touch primary routing.
4. **Shared registry:** dispatch and poll operate through the *same* `GenerationDriverRegistry` instance in the test.
5. **Negative:** unresolvable backend_id on entry → `dispatch_no_driver`, no artifact, consumer loop survives.
6. Scope-guards: no Pipeline/Vision; no `InvocationHandler`; no `poll(request_id)` change; `forge_bridge.__all__`=19; orchestration `__all__` adds only the new consumer symbol. Suite green (`--import-mode=importlib` if the pre-existing `test_capture.py` collision blocks plain collection — pre-existing, not V2); ruff clean; live mandatory-pair proof still green.

## Done-signal + next rungs
One feat commit `feat(phase-7): attach dispatch to execution-stage entry (event-driven consumer)`. Update the V2 framing → LANDED; note any hidden assumption the attach surfaced (first-class output). **Next seams (now cleanly separable):** (a) the **primary `routing→execution` trigger** — "what causes a fresh plan to reach execution" (the other half Creative split off); (b) real-Generators driver adapter + `poll(request_id)` (V1 Q1); (c) **Pipeline** then **Vision** pathways onto the now-attached spine; (d) the E2E demonstrator/manifest capstone.
