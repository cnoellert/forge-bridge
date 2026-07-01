# Convergence — the direct-callable generation dispatch entry (bridge #139)

**Date:** 2026-07-01
**Subject:** What entry-point shape lets a Pass-B in-process `forge_generate_*` MCP tool handler submit a generation and get a pollable `artifact_id` in bridge's shared lifecycle? (bridge #139, from generators peer #137 Q1.)
**Cadence:** 3 independent views (substrate architect / ergonomics advocate / skeptic-decomposer), redline, converged lean.

---

## Grounded facts (verified)
- `dispatch_plan(plan: DBOrchExecutionPlan, ...)` (`orchestration/dispatcher.py:111`) → `driver.submit(InvocationEnvelope)` (`:203`) → bridge persists artifact + lifecycle row (`GenerationArtifactRepo.insert_submitted`, `store/…/orch_generation_artifact_repo.py:60`, `~:230`) → lineage events → `DispatchResult(status, artifact_id)`.
- The plan is used ONLY as a parsing prologue: `_generation_step(plan)` (`dispatcher.py:41`) collapses it to `{operator_id, backend_id, inputs, output_artifact_id}`; the backend triple comes from the DRIVER, not the plan; `plan.id` appears in the tail only as provenance STRINGS (`content_provenance.plan_id` / `source_plan_id`), no FK.
- The lifecycle invariant #137 Q1 protects (job lands / pollable by `artifact_id` / cost recorded / not orphaned) lives BENEATH `dispatch_plan` — in `insert_submitted`/`transition` + the two lifecycle events + the status-driven poller (`WorkerPoller.find_non_terminal`). None of it reads a plan or planner.
- `Planner.plan(...)` (`planner.py:162`) consumes a persisted `DBOrchLockedIntent` that REQUIRES `success_criteria[].measurement_spec` (missing → `locked_intent_unresolvable`, `planner_passes.py:67`) + snapshot rows. That is the MEASURED storyboard/vision loop's spine — never on the dispatch→persist path.
- No `plan_and_dispatch` / plan-free entry exists today (net-new).
- `GenerationGrant`/`grant_id` is **design-stage**: only comment placeholders in `orchestration/manual_qc.py:134,217` ("when grant_id lands") + framing docs (`RUNG-C-ENVELOPE-AUTHORITY-FRAMING.md`). No built ratify/grant authority mechanism.

---

## Converged position

**Extract a plan-free dispatch core** out of `dispatch_plan`:

```
dispatch_envelope(envelope: InvocationEnvelope, *, provenance: dict, driver_registry,
                  session_factory, event_appender, run_id: uuid|None=None) -> DispatchResult
```

- `dispatch_plan` KEEPS its signature (back-compat): runs its plan-parsing prologue, builds the envelope + a provenance dict CARRYING `plan_id`, then `return await dispatch_envelope(...)`.
- The direct `forge_generate_*` tool builds the `InvocationEnvelope` (`operator_id` from the tool, `inputs` as `ArtifactRef`s, backend) + a provenance dict with **no** `plan_id`, and calls `dispatch_envelope`. Same lifecycle row, same events, same pollable `artifact_id` — **no planner, no measurement, no fake plan.**
- `plan_id` is demoted from required input → optional provenance (the lineage events must tolerate its absence).
- **Planner stays optional and deferred** above the core.

**One function, two entry modes, one rail** — literally #137's "share, don't duplicate the authority/persistence rail."

## The redline
- **A's mechanism (mint a degenerate `DBOrchExecutionPlan` → feed unchanged `dispatch_plan`) — REJECTED.** C's kill: *"that's fabricating a plan instead of fabricating criteria — the same category error wearing a different hat; the plan-typed signature is the actual defect."* Hollow plan rows (never ran the passes; meaningless `feasibility_verdict`) pollute the plan store, and A's own grounding proved `plan_id` is provenance-only (no FK) — so nothing needs a plan.
- **B + C (plan-free core) — WINS.** B first proposed extracting a shared submit-and-persist helper so both doors share it; C sharpened it — the core should take an `InvocationEnvelope` + provenance (with `plan_id` optional), not a "step," because the plan-typed *signature* is the defect.
- **A's surviving contribution — authority rigor, folded in.** The direct door is a paid, model-reachable spend path, so it must cross the same grant gate: `run_id` flows through (fail-closed), the grant-CAS guard sits at the single `driver.submit()` chokepoint INSIDE the core (both doors gated), but the **ratify/assent decision stays in the tool layer ABOVE the core** — assent never in the core (same as `CommitBoundary` doctrine, [[feedback_orchestrator_control_flow_not_meaning]]).

## Two-half sequencing (the real unblock)
1. **Half 1 — the plan-free core (`dispatch_envelope`). LANDABLE NOW.** Safe refactor; existing dispatcher tests are the parity oracle. THIS is the concrete answer to #137 Q1 and the contract generators build their handler against. Substrate-before-consumer ([[feedback_substrate_before_consumer_landing]]).
2. **Half 2 — the model-reachable `forge_generate_*` tool + ratify preview (with cost, #140) + grant gate. GATED.** Cost on the direct path comes from the **driver/capability `estimated_cost`** (NOT `plan.cost_estimate` — the direct path skips the planner), surfaced in the tool's ratify preview. This half **cannot honestly ship ahead of the `GenerationGrant`/ratify mechanism**, which is design-stage. So #139-consumer + #140 + #142 all ride the authority rail.

## Intentionally unbound / deferred
- **Half 2 (model-reachable tool + cost preview + grant)** — gated on building the `GenerationGrant` ratify authority (design-stage; #31/D6). Re-open trigger: the grant mechanism lands. Until then, a direct paid render is confined to the manual/authorized slice, not model-reachable.
- **Backend selection when the caller can't name a backend** — extract ONLY a standalone capability-router (the routing concern of planner pass 2), never the measurement spine. Unbound pending a caller that needs routing.

## Rejected
- **Degenerate-plan-into-`dispatch_plan`** — fabricates a plan to satisfy a plan-typed signature; the signature is the defect.
- **A second, independent submit/persist path** — forks the rail (orphan jobs the poller never sees; cost no longer sums from one reported-submission source). The shared core is non-negotiable.
- **Mandating `measurement_spec` on a bare render** — category error; measurement is the storyboard loop's semantics, not generation-dispatch's.

## Invariants
`composition/executor.py` untouched (unrelated). `forge_bridge.__all__` == 19. The extraction is behavior-preserving for `dispatch_plan` (dispatcher tests green as oracle).

---

## Implementer brief — HALF 1 (plan-free `dispatch_envelope` core; landable now)

**Goal:** Extract the submit-and-persist tail of `dispatch_plan` into a plan-free `dispatch_envelope`, so `dispatch_plan` becomes a thin caller and a future direct tool can reach the identical lifecycle without a plan. Behavior-preserving for `dispatch_plan`.

**Do:**
1. In `orchestration/dispatcher.py`, extract everything from driver-resolve → `driver.submit(envelope)` → build body → `insert_submitted` → emit `generation_dispatch_submitted` + `_lineage_recorded` → `return DispatchResult` into `dispatch_envelope(envelope, *, provenance, driver_registry, session_factory, event_appender, run_id=None)`.
2. `dispatch_plan` keeps its signature; its prologue (`_sync_perception_steps`, `_generation_step`) builds the envelope + a provenance dict carrying `plan_id`/`source_plan_id`/`planned_output_artifact_id`, then `return await dispatch_envelope(...)`.
3. Make `plan_id` OPTIONAL in the provenance/body construction and in the two lineage events (absent for a plan-free caller). Confirm event consumers tolerate a missing/null `plan_id`.
4. Put the single `driver.submit()` chokepoint (and the future grant-CAS guard site — leave a clearly-named seam/comment, do NOT build the grant) inside `dispatch_envelope` so both doors will be gated when the grant lands.

**Constraints:** behavior-preserving for `dispatch_plan` — existing `tests/…dispatcher` (and orchestration) tests must stay green as the parity oracle; add a test that calls `dispatch_envelope` directly with a hand-built envelope + `plan_id`-absent provenance and asserts the same artifact/lifecycle/events + pollable `artifact_id`. `forge_bridge.__all__` == 19. No new deps. Do NOT build the direct MCP tool, the planner-bypass consumer, cost preview, or the grant — those are half 2 (gated).

**Deliverable:** the `dispatch_envelope` signature + the refactor diff, proof `dispatch_plan` behavior is unchanged (tests green), the plan-free direct-call test, confirmation `plan_id`-absent flows cleanly through events, and any consumer that broke on a null `plan_id` (a real coupling is a finding).
