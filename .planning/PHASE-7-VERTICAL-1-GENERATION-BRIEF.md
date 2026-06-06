# BRIEF — Phase 7, Vertical 1: the generation lifecycle round-trip

**Status:** EXECUTION-READY (D1 converged generation-first; D2–D5 ratified at discuss 2026-06-05). Grounded against `main @ 29c43d6`. Framing: `PHASE-7-INVOCATION-FRAMING.md`.

**Goal — prove the missing bridge-owned lifecycle exists** (Creative's bar; the proof is the *lifecycle*, not image generation):
> capability discovered → capability selected → **submit invoked** → bridge obtains a handle → **poll finds it again** → terminal

If this round-trips, four unknowns retire in one slice: **submit exists · backend resolution exists · surface resolution exists · poll attaches to the right artifact.**

**Principle:** thinnest slice that exercises the *new* substrate (the submit verb + the now-due backend_id seam + the surface reconcile) on the **real resolution path**, with the remote backend **stubbed** (a faithful-lifecycle stub, not a real generator call). [[feedback_brief_examples_as_behavioral_reference_shapes]]

---

## Grounded current state — the void is total (live reads @ `29c43d6`)
- `GenerationArtifactRepo.insert_submitted` exists (`orch_generation_artifact_repo.py:60`) but is **called nowhere in production** (grep: only the def + unrelated `sync_client` thread-submit). Nothing ever creates a submitted artifact.
- `GenerationPoller` is **instantiated nowhere in production** (only defined `worker.py:32` + exported). The poll loop exists but is never fed and never run.
- `to_stage="execution"` transitions appear **only in `replay.py:277,321`** — likely no primary planning→execution path today.
- Bridge driver port is **poll-only** (`drivers.py:17-32`, `poll(artifact)→DriverPollResult`); registry keyed by composite `backend_id=f"{surface}.{path}"` (`drivers.py:76`, `resolve_backend_id` `:42-54`). Generators' real `BackendDriver` is `submit(operator_id, invocation)→(request_id, datetime)` + `poll(request_id)→PollResult` keyed by **surface** (`forge-generators/.../drivers/types.py:44-67`).

⇒ Phase 7 V1 builds the **dispatch + submit half**, reconciles the keying, and proves the existing poll half round-trips against it.

## Scope
- **IS:** (1) add `submit()` to bridge's generation driver port; (2) a `dispatcher` that consumes a plan's generation step → resolves driver → `submit()` → `insert_submitted` with proper `execution_provenance` → emits events/lineage; (3) reconcile the backend_id/surface keying (triple→composite key, consistent across register/plan/resolve); (4) a **faithful-lifecycle stub driver** carrying a `backend_identity_triple`; (5) an end-to-end **round-trip test** (discover→plan→dispatch→`poll_once`→terminal) with real resolution + stubbed backend.
- **IS NOT:** ❌ Pipeline (execution) or Vision (perception) pathways · ❌ a real Generators backend call · ❌ adopting Generators' exact `poll(request_id)` signature / the real-driver adapter (**deferred** — keep bridge's `poll(artifact)`, see open Q1) · ❌ daemon-wiring the continuous poller loop (round-trip proven via `poll_once()`) · ❌ a uniform `InvocationHandler` (D4) · ❌ a contract invocation-envelope type (D5 — bridge-local only) · ❌ absorbing Pipeline receipts · ❌ the full E2E manifest-of-all-three.

## Changes (reference shapes — code owns exact signatures)

### 1. `forge_bridge/orchestration/drivers.py` — add the submit verb (D3)
Extend `GenerationDriverProtocol` with `submit`, returning a backend handle. Keep `poll(artifact)` unchanged (the worker depends on it). Reference shape:
```python
@runtime_checkable
class GenerationDriverProtocol(Protocol):
    backend_id: str
    backend_identity_triple: dict   # {surface, path, ...} — the key source (surface reconcile)
    async def submit(self, invocation: "InvocationEnvelope") -> "DriverSubmitResult": ...
    async def poll(self, artifact: DBOrchGenerationArtifact) -> DriverPollResult: ...   # unchanged
```
`DriverSubmitResult` (new, bridge-local): `{request_id: str, submitted_at, raw_response_summary: dict}`. **Keying reconcile:** derive the registry key from `backend_identity_triple` (→ `f"{surface}.{path}"`) so `register`, the plan's `backend_id_from_snapshot_entry`, and `resolve_backend_id(artifact)` all agree on one value. Document the bridge-`composite` vs Generators-`surface` divergence at the register site (the real-driver adapter reconciles it later — open Q1).

### 2. `forge_bridge/orchestration/dispatcher.py` (NEW) — the dispatch spine (D2)
`async def dispatch_plan(plan, *, driver_registry, session_factory, event_appender) -> DispatchResult`. For the generation step in `plan.operator_sequence`:
1. resolve the step's `backend_id` against `driver_registry.get_driver(...)`; **if no driver → block with a clear refusal** (`dispatch_no_driver` event + a `DispatchResult` refusal; no silent no-op) (D3, [[feedback_pre_orchestration_resolution_paralysis]]).
2. build a bridge-local `InvocationEnvelope` from the step (operator_id + input `ArtifactRef`s on contract reference currency — D5).
3. `handle = await driver.submit(envelope)`.
4. `insert_submitted(body)` with `execution_provenance = {"backend_identity_triple": {...}, "request_id": handle.request_id}` so `resolve_backend_id` reverse-resolves and the poller attaches.
5. emit dispatch events + lineage (the proof bar's "records references, events, lineage, provenance").
Keep it a standalone callable (not yet hooked into a stage transition — see open Q2).

### 3. `InvocationEnvelope` + `DispatchResult` (bridge-local types, D5)
Bridge-owned, built on contract `ArtifactRef`/`Reference` (`forge_contracts.references`). NOT a contract type, NOT Pipeline's receipts. Minimal: envelope = `{operator_id, inputs: list[ArtifactRef], backend_identity_triple}`; result = `{status, artifact_id|None, refusal_code|None}`.

### 4. Faithful-lifecycle stub driver (test fixture or `tests/.../_stub_driver.py`)
Implements the bridge port; mirrors Generators' **lifecycle semantics** (not a degenerate no-op) so the round-trip is real ([[feedback_fixture_shape_mirrors_production]]): `submit()` returns a `request_id` handle; `poll(artifact)` progresses `submitted → polling → complete` across calls (e.g. first poll → `next_state="polling"`, second → terminal with `terminal_provenance`). Carries a `backend_identity_triple` so the keying reconcile is genuinely exercised. **The remote call is faked; the bridge-side lifecycle + resolution are real.**

### 5. Round-trip test — `tests/test_phase7_generation_vertical.py` (NEW)
The proof. Register the stub in a `GenerationDriverRegistry`; build/seed a plan with a generation step whose `backend_id` matches the stub's derived key; `dispatch_plan(...)` → assert a `submitted` artifact exists with correct `execution_provenance`; run `GenerationPoller.poll_once()` (real worker, stub driver) → assert it **finds the artifact, polls it, and drives it to terminal**. Plus the **negative**: a plan step whose `backend_id` has no registered driver → `dispatch_plan` refuses (`dispatch_no_driver`), no artifact created.

## Open design sub-questions (resolve within the guardrails; flag, don't expand scope)
- **Q1 — poll signature:** this vertical keeps bridge's `poll(artifact)` (avoids rippling `worker.py`). Aligning to Generators' `poll(request_id)` + writing the real-driver adapter is the **next widening rung**, not this one. Confirm that's the right cut, or pull it in.
- **Q2 — production dispatch hook:** the only `to_stage="execution"` sites are `replay.py:277,321`; a primary planning→execution transition may not exist. This vertical proves the round-trip via a **direct `dispatch_plan` call in test**; wiring it into the live stage-transition (and finding/confirming the full equivalence class of hook sites — [[feedback_sibling_check_before_fix_scope]]) is a thin follow-on. Confirm prove-the-mechanism-first is acceptable vs requiring the live hook now.

## Acceptance
1. **Round-trip proven:** the test drives discover→plan→dispatch→`poll_once`→terminal with a stubbed-but-faithful driver and **real resolution** (the stub is registered, resolved by derived key, submitted, and the real `GenerationPoller` finds + terminalizes the artifact). Demonstrate, don't assert.
2. **Resolution is real, not bypassed:** the artifact's `execution_provenance.backend_identity_triple` is what `resolve_backend_id` reverse-resolves to the registered driver — i.e. the keying reconcile (triple→composite) actually fires (a deliberately mismatched triple → `no_driver`, proving the path isn't shortcut).
3. **Negative path:** unresolvable `backend_id` → `dispatch_no_driver` refusal, **no** artifact spawned (no silent no-op).
4. `submit()` added to the port; `poll(artifact)` unchanged; `GenerationDriverProtocol` still `@runtime_checkable` and the stub satisfies it.
5. Scope-guard greps: no Pipeline/Vision dispatch added; no `InvocationHandler` superclass; `InvocationEnvelope`/`DispatchResult` are bridge-local (no `forge_contracts` invocation type introduced); `forge_bridge.__all__` unchanged (**19**); orchestration `__all__` adds only the new dispatcher/envelope symbols.
6. Full suite green (`pytest tests/` orchestration subset incl. the existing worker tests) + ruff clean + the live mandatory-pair discovery proof still green.

## Done-signal (post-merge) + next widening rungs
One feat commit `feat(phase-7): generation lifecycle round-trip (dispatch + submit; stubbed backend, real resolution)`. Update `PHASE-7-INVOCATION-FRAMING.md` → V1 LANDED. **Next rungs (widen onto the proven spine):** (a) real-Generators driver adapter + `poll(request_id)` alignment (Q1); (b) production execution-stage hook + poller daemon-wiring (Q2); (c) **Pipeline `execution`** pathway (plugin dispatch + receipt-reference reconcile); (d) **Vision `perception`** pathway (sync call); (e) the full E2E demonstrator + manifest-of-all-three (the proof-sequence capstone).
