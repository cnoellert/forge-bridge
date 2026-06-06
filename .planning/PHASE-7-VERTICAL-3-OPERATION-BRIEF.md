# BRIEF — Phase 7, Vertical 3: daemon-start the execution runtime (prove it's ALIVE)

**Status:** EXECUTION-READY (D1 ruled full-set by Creative; D2/D3 strong-lean ratified). Grounded against `main @ 3e5891f`. Framing: `PHASE-7-VERTICAL-3-OPERATION-FRAMING.md`.

**Goal:** start the execution-runtime worker *set* in the `:9996` daemon and prove the full generation round-trip runs **through the actual daemon lifecycle**: execution-entry event → dispatch → submit → poll → terminal → audit, with the workers running autonomously (no harness driving them).

**Boundary (Creative — quote in the code/docstrings):** *"V3 establishes the runtime; it does not expand the federation."* The stub driver proves **daemon lifecycle + orchestration**, NOT real generator integration. Real Generators driver = later widening rung.

---

## Load-bearing separation: production wires an EMPTY runtime; the PROOF injects the stub
`bootstrap_daemon` (`mcp/server.py:196`) is *production* init — it must NOT hardcode a stub driver ([[project_forge_bridge_substrate_not_producer]]).
- **Production:** the daemon starts the three workers with a shared **empty** `GenerationDriverRegistry`. On a stock install with no drivers, the consumer runs and dispatch emits `dispatch_no_driver` — correct graceful behavior (drivers arrive later via the deferred Generators-adapter rung).
- **Proof:** an integration test goes through the **real** `bootstrap_daemon` task-startup, injects the V1 faithful stub into the bootstrap-created shared registry, triggers a replay→execution, and asserts the round-trip completes via the **autonomously-running tasks** (the harness seeds a driver + triggers replay + observes; it does NOT drive the workers — they run from their bootstrap tasks). That satisfies "no test-harness involvement" at the worker level.

## Grounded substrate (live reads @ `3e5891f`)
- `bootstrap_daemon` is the single-source-of-truth init; **Step 3 is the precedent**: `asyncio.create_task(watch_synthesized_tools(...), name="watcher_task")`, returned in `_BootstrapResult` for reverse-order teardown (`mcp/server.py:251-255, 286+`). `session_factory = get_async_session_factory()` already in scope (`:259`).
- The three workers each have a `run_forever(shutdown_event=…)` loop built and ready: `GenerationPoller` (`worker.py`), `GraphEngineEventConsumer` (`event_consumer.py`), `DispatchOnExecutionEntryConsumer` (`dispatch_consumer.py`). None is started today.
- The terminal consumer needs a `GraphEngine`; the dispatch consumer needs `session_factory` + the shared registry + an `event_appender`. Bootstrap assembles these (see open items).

## Changes (reference shapes — code owns exact signatures)

### 1. `forge_bridge/mcp/server.py` — `bootstrap_daemon`: establish the execution runtime (D1/D2/D3)
After the singletons + `session_factory` (Step 4-ish), add an execution-runtime step mirroring the Step-3 watcher precedent:
```python
# Step N — execution runtime (Phase 7 V3): one shared registry, three managed tasks.
driver_registry = GenerationDriverRegistry()          # EMPTY in production
exec_shutdown = asyncio.Event()
dispatch_task = asyncio.create_task(
    DispatchOnExecutionEntryConsumer(session_factory, driver_registry=driver_registry, ...).run_forever(shutdown_event=exec_shutdown),
    name="dispatch_consumer_task",
)
poller_task = asyncio.create_task(
    GenerationPoller(session_factory, driver_registry).run_forever(shutdown_event=exec_shutdown),
    name="generation_poller_task",
)
terminal_task = asyncio.create_task(
    GraphEngineEventConsumer(..., graph_engine=...).run_forever(shutdown_event=exec_shutdown),
    name="terminal_consumer_task",
)
```
Carry `driver_registry`, the three tasks, and `exec_shutdown` on `_BootstrapResult` (mirror the watcher_task handle) so teardown cancels them in reverse. Expose the `driver_registry` on the result so a later consumer (or the proof) can register drivers.

### 2. Teardown
On lifespan exit, set `exec_shutdown` and cancel/await the three tasks in reverse (mirror the existing watcher/console teardown).

### 3. Dependency assembly (open items — resolve in bootstrap)
The terminal consumer needs a `GraphEngine` and the consumers need an `event_appender`/session wiring consistent with how they're used elsewhere. Assemble these in bootstrap from what's already there (`session_factory`, the engine the console/replay use). Confirm whether a single `GraphEngine` instance is appropriate at daemon scope.

### 4. Proof test — `tests/test_phase7_daemon_runtime.py` (NEW)
Through the **real** `bootstrap_daemon` (or its task-start path): inject the V1 stub into the result's shared `driver_registry`; trigger a **replay** that reaches `to_stage="execution"`; assert — driven only by the autonomously-running tasks — the round-trip completes: `stage_advanced` consumed → submitted artifact → polled → terminal → terminal consumer advances to audit. Then exercise teardown (shutdown event → tasks cancel cleanly). **Also assert the production-empty path:** with no driver registered, the consumer runs and dispatch emits `dispatch_no_driver` without crashing the loop (graceful degradation).

## Scope
- **IS:** start the execution-runtime set (dispatch consumer + poller + terminal consumer) in the `_lifespan`/`bootstrap_daemon` with one shared (empty-in-prod) `GenerationDriverRegistry`; clean teardown; the daemon round-trip proof injecting the stub; the graceful-empty assertion.
- **IS NOT:** ❌ the primary `routing→execution` trigger (still the deferred separate seam — proof uses replay) · ❌ Pipeline/Vision pathways · ❌ real Generators driver wiring (deferred V1 Q1) · ❌ `poll(request_id)` alignment · ❌ registering any stub in **production** bootstrap · ❌ a separate worker *process* (use the existing lifespan).

## Acceptance
1. **Alive — full round-trip through the daemon lifecycle:** the proof drives a replay→execution and the bootstrap-started tasks (not the harness) carry it to terminal + audit. Demonstrate.
2. **Production wires EMPTY + degrades gracefully:** stock bootstrap starts the runtime with no drivers; the consumer runs, dispatch emits `dispatch_no_driver`, no crash, loop survives.
3. **Clean teardown:** lifespan exit cancels the three tasks via the shutdown event; no orphaned tasks / no teardown errors.
4. **The boundary is documented in code:** the stub-for-proof and "establishes runtime, not real-generator integration / not federation expansion" caveat is loud in the proof + bootstrap comments.
5. Scope-guards: no Pipeline/Vision; no real Generators driver; no stub in production bootstrap; `forge_bridge.__all__`=19. Suite green (`--import-mode=importlib` if the pre-existing `test_capture.py` collision blocks plain collection); ruff clean; the live mandatory-pair discovery proof still green; existing lifespan-wiring tests (`tests/console/test_lifespan_wiring.py`) still green (the new tasks don't regress startup).

## Done-signal + next rungs
One feat commit `feat(phase-7): daemon-start the execution runtime (dispatch consumer + poller + terminal consumer)`. Update the V3 framing → LANDED; note any assumption the daemon-start surfaced. **Then the runtime is ALIVE and widening has a living spine** — next seams (now low-risk): (a) the **primary `routing→execution` trigger** (the deferred half: "what causes a fresh plan to reach execution"); (b) **real Generators driver adapter** + `poll(request_id)` (V1 Q1) — turns the empty prod registry real; (c) **Pipeline** then **Vision** pathways onto the living spine; (d) the E2E demonstrator/manifest capstone.
