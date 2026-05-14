---
name: SEED-FLAME-EXEC-OBSERVABILITY-V1.6+
description: Phase 23.1 shipped minimum per-invocation observability for flame_execute_python (code_hash + main_thread + elapsed_ms + status + code_len). The richer instrumentation arc — queue-wait timing, hook-side per-stage breakdown, cross-process correlation IDs — requires Flame hook protocol cooperation and belongs in a v1.6 observability phase, not an in-flight 23.1 patch.
type: forward-looking-feature
planted_during: Phase 23.1 author-walk on portofino 2026-05-14 — Gate 3 surfaced tool_error pathology that the existing log shape (router-side per-iter status only) could not isolate. Cross-writer framing reframed it as "this is now observability work, not one-off fixes."
trigger_when: v1.6 milestone opens OR a future flame_execute_python failure surfaces that 23.1's minimum instrumentation cannot isolate OR the Flame hook is being touched for any reason (protocol extension piggybacks cleanly) OR `fbridge doctor` gains per-tool latency/error rates
---

# SEED-FLAME-EXEC-OBSERVABILITY-V1.6+

## What 23.1 Shipped (Minimum Floor)

Per-invocation logging at the tool wrapper in [forge_bridge/tools/utility.py](forge_bridge/tools/utility.py). Each call to `flame_execute_python` emits an INFO record with five fields:

- **`code_hash`** — first 16 chars of sha256(snippet). Lets operators group log lines by snippet identity across runs without exposing the code itself.
- **`main_thread`** — the boolean flag value. Spots "model is defaulting to main_thread=True on read-only queries" patterns immediately.
- **`elapsed_ms`** — wall-clock from tool entry to exit. Pairs with the router's per-iter elapsed_ms for cross-correlation.
- **`status`** — one of `ok`, `flame_error`, `transport_error`. Distinguishes "Flame Python raised but tool returned cleanly" from "bridge.execute() raised at the transport layer" — the second was indistinguishable from a normal failure pre-23.1.
- **`code_len`** — raw byte length of the snippet. Quick signal for "model wrote a long script" without the cost of hash-collision-checking the content.

This is the floor. It makes the 23.1 author-walk failures legible. It does NOT answer:

- *Where inside the 10-30s did the elapsed time go?*
- *Did the snippet queue waiting for Flame's idle event loop, or did it execute and the result was slow to come back?*
- *Were there N waiting snippets ahead of this one?*
- *Was Flame's main thread busy with UI work, batch rendering, or media I/O at the time?*

Those questions are the richer arc.

## The Richer Arc (Deferred to v1.6)

### Stage 1 — Per-stage timing inside the bridge wrapper

`bridge.execute()` does roughly four things:

1. Serialize the snippet to the POST body.
2. Open the httpx connection to `:9999/exec`.
3. Wait for the hook to respond.
4. Parse the response.

At v1.6 the wrapper should emit per-stage timing for each:

```
bridge.execute code_hash=abc123 serialize_ms=2 connect_ms=1 wait_ms=15234 parse_ms=3
```

This is purely client-side; no hook cooperation needed. Tells us whether the time is in transport or in Flame.

### Stage 2 — Hook-side per-stage timing (requires protocol extension)

The Flame hook at `:9999/exec` runs roughly:

1. Receive request, parse JSON.
2. (Optional) Schedule onto Flame's idle event loop via `schedule_idle_event` when `main_thread=True`.
3. Wait in the idle queue.
4. Execute the snippet on the appropriate thread.
5. Capture stdout/stderr.
6. Serialize the response.

The hook response shape today is `{stdout, stderr, result, error, traceback}`. v1.6 should extend it with:

```json
{
  "stdout": "...",
  "stderr": "...",
  "result": null,
  "error": null,
  "traceback": null,
  "_timing": {
    "received_at": "<wall clock>",
    "scheduled_at": "<wall clock when added to idle queue, null if main_thread=False>",
    "dispatched_at": "<wall clock when execution started>",
    "completed_at": "<wall clock when execution finished>",
    "queue_depth_at_schedule": <int>,
    "main_thread_busy_ms": <int or null>
  }
}
```

The bridge wrapper consumes `_timing` and logs derived quantities:

```
flame_execute_python code_hash=abc123 ... wait_ms=8000 queue_depth=3 main_thread_busy_ms=12000
```

This is the load-bearing instrumentation for "is the model causing the slowness, or is Flame causing it?" — the question 23.1 could not answer.

### Stage 3 — Cross-process correlation IDs

Currently the router log shows `tool=flame_execute_python elapsed_ms=16234 status=tool_error` but operators have to correlate that with the tool wrapper's log line by timestamp. v1.6 should attach a correlation ID at the chat handler boundary that flows through:

- chat handler → router (per-iter logs)
- router → tool wrapper (utility.py log lines)
- tool wrapper → bridge.execute → Flame hook (POST header)
- Flame hook → response `_timing.correlation_id`

So a single `grep correlation_id=<x>` retrieves the entire request lifecycle across four log streams. v1.6's observability phase delivers this; 23.1 doesn't have the protocol-extension scope to do it.

### Stage 4 — `fbridge doctor` per-tool latency

`fbridge doctor` currently reports per-surface health (running/listening/ok). v1.6 should add a per-tool latency surface — rolling p50/p95 elapsed_ms over the last N invocations, derived from the structured log records 23.1 shipped. Operators see "flame_execute_python p95=24s" and know whether the substrate is healthy without re-walking the dogfood query.

## Why This Doesn't Belong in 23.1

Per [.planning/phases/23.1-chat-convergence-ship-blocker/23.1-CONTEXT.md](.planning/phases/23.1-chat-convergence-ship-blocker/23.1-CONTEXT.md) §2.2:

> Out of scope (locked):
> - … anything that requires Flame hook protocol extension or new HTTP route shape

Stages 2-4 above require hook-side cooperation (Stage 2 explicitly, Stages 3-4 via response shape evolution). The 23.1 forcing function is "the dogfood query converges"; stage 1 + the minimum floor are enough to diagnose the live failure. Anything more is feature-creep into an in-flight ship-blocker patch.

The v1.6 framing artifact at [.planning/milestones/v1.6-FRAMING.md](.planning/milestones/v1.6-FRAMING.md) §11.1 names operability surfaces as in-scope but defers proto-node emission until Phase 26. This seed fits naturally into a v1.6 observability phase scoped alongside the proto-node emission work — both are about making invisible runtime state legible.

## Why Plant Now

Three reasons:

1. **The framing matters and decays fast.** The cross-writer reframe at the 23.1 author-walk ("this is now observability work, not one-off fixes") is the architectural shift that justifies a dedicated v1.6 observability phase. Without the seed, the framing fades into "we kept adding log lines."

2. **23.1's minimum floor is forward-compatible.** The five fields (code_hash, main_thread, elapsed_ms, status, code_len) are the strict subset of the richer schema. v1.6's richer instrumentation extends without breaking. Operators who learn to read 23.1's log lines don't have to relearn at v1.6.

3. **The stage breakdown is non-obvious.** Stages 2-4 above are easy to get wrong if a v1.6 phase author starts from scratch ("let's add some timing here"). Encoding the canonical decomposition now means the v1.6 phase has a clear architectural target rather than rediscovering it.

## Activation Triggers

Any of:

1. **v1.6 milestone opens** — natural sequencing; proto-node emission (Phase 26) is the adjacent observability work and this seed composes cleanly into it.
2. **A future flame_execute_python failure surfaces** that the 23.1 minimum floor cannot isolate. Specifically: tool_error rates climb but log lines all look similar; or `main_thread=False` calls suddenly become slow without a clear cause.
3. **The Flame hook is being touched** for any reason (auth, multi-project, threading model). The protocol extension piggybacks cleanly — every hook touch is a chance to advance the observability arc.
4. **`fbridge doctor` is being extended** for per-tool health rather than per-surface health.
5. **CI / benchmarks ship** (per `SEED-CANONICAL-FLAME-INTROSPECTION-QUERY-V1.6+`) and need per-stage timing to be useful as regression signals.

## Cross-References

- 23.1 minimum floor implementation: [forge_bridge/tools/utility.py](forge_bridge/tools/utility.py) — `execute_python` instrumentation block.
- 23.1 test pins: [tests/test_flame_execute_python.py](tests/test_flame_execute_python.py) — observability test section.
- 23.1 CONTEXT: [.planning/phases/23.1-chat-convergence-ship-blocker/23.1-CONTEXT.md](.planning/phases/23.1-chat-convergence-ship-blocker/23.1-CONTEXT.md) §2.2 out-of-scope clauses.
- v1.6 framing: [.planning/milestones/v1.6-FRAMING.md](.planning/milestones/v1.6-FRAMING.md) §11.1 (operability surfaces), Phase 26 (Console Exec view + schema universalization — observability adjacency).
- Sibling seeds: `SEED-CANONICAL-FLAME-INTROSPECTION-QUERY-V1.6+` (the regression fixture this instrumentation supports), `SEED-COLD-LOAD-UX-V1.6+` (the model-warmup observability problem this won't solve but is adjacent to).

## What Success Looks Like in v1.6

After the v1.6 observability phase ships, an operator hitting a chat-convergence problem in production should be able to:

```bash
# 1. Find a failing request by correlation ID
grep "correlation_id=abc123" ~/.forge-bridge/logs/mcp_http.log

# 2. See the full lifecycle: chat handler → router → tool wrapper → hook
# in one timeline, with per-stage timing.

# 3. Identify the bottleneck without re-running the failure:
#    - Was it cold-load? (initial model-load latency in router log)
#    - Was it queue wait? (main_thread_busy_ms in hook log)
#    - Was it snippet pathology? (code_hash + repeat-count + status pattern)
#    - Was it transport? (connect_ms / wait_ms in bridge log)
```

That's the operability story. v1.5's TROUBLESHOOTING.md taught failure modes to *people*; v1.6's observability story teaches failure modes to *the logs themselves*, so operators don't have to memorize the symptom matrix — they can read the answer off the timeline.

Phase 23.1's minimum floor is the first step in that arc. This seed maps the rest.
