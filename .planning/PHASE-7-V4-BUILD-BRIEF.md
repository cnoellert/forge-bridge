# Phase 7 V4 — Vision Widening: Build Brief

**Executor:** code (DT verifies). **Source:** DT D2 grounding + Creative D2(b) shape call + ratified D1/D3/D4 leans.
**Goal:** prove the execution runtime is **capability-family agnostic** — a sync, artifact-less Vision step advances `execution → audit` **without impersonating generation.** This is the *minimum family-agnostic completion primitive* (D2(b) scope guard), NOT a universal capability runtime.

---

## The two load-bearing invariants (protect these above all)

1. **Completion is family-agnostic; evidence of completion is family-specific.** For generation, evidence is an artifact reaching a terminal state. For sync Vision, evidence is a terminal execution-result. Once normalized to `{candidate, diagnostic, in_flight}`, the consumer must not care which family produced it.
2. **Double no-impersonation:**
   - **Vision must not impersonate a generation artifact** — no synthesized `generation_artifact_terminal`, no fake `orch_generation_artifact` row. (Easier green path; wrong ontology — rejected.)
   - **The Vision handler must not impersonate the lifecycle engine** — it *reports* completion; the consumer/lifecycle *decides* advancement. No direct run advancement from the handler (preserves the V2 no-callsite-coupling). Ties to orchestrator-owns-control-flow-not-meaning.

## Grounded seam (confirmed)

The spine is generation-shaped at both ends (driver `submit()`+`poll(artifact)` → `orch_generation_artifact` entity → per-artifact `generation_artifact_terminal` → consumer re-partitions). Family-specificity lives in **exactly three narrow bindings** in `event_consumer.py`:
- **Trigger:** `TERMINAL_EVENT_TYPE = "generation_artifact_terminal"` (:43, enforced :56-58).
- **Count source:** `_partition_run_artifacts` reads `GenerationArtifactRepo` (:16), entity `orch_generation_artifact` (~:209).
- **Status→disposition map** (~:219-224).

The decision layer is **already family-agnostic** and must stay **untouched**: lifecycle gate `current_stage == "execution"` (:82), the `candidate/diagnostic/in_flight` trichotomy, the advance/pause decision (`in_flight==0 → candidates>0 ? audit : pause`, :95-134), idempotent re-partition-on-any-terminal.

## Build steps (reference shapes, not rewrite mandates)

1. **D1 — family routing (the switch).** Dispatcher/planner routes a *perception* (Vision) step to the sync-perception path, NOT the generation `submit/poll` path. No uniform handler — each family takes its own path. (This interlocks with D2: D1 *routes*, D2 *provides the family-agnostic terminal+count*.)
2. **Family-agnostic terminal event.** Add `execution_step_terminal` (carries `run_id`, `step_id`, `family`). `generation_artifact_terminal` becomes **one instance/source** of it — do not retire it, do not synthesize it for Vision.
3. **Execution-result record — the countable home (load-bearing).** Minimal persisted record keyed by `run_id, step_id, family, disposition ∈ {candidate, diagnostic, in_flight}`, + optional result payload/ref. **This is the load-bearing change** (per DT): because the partition counts the *whole run*, a sync result needs a countable home *alongside* artifacts — the event alone is insufficient.
4. **Generalize the count.** `_partition_run_artifacts` unions: generation artifacts (mapped by `status` as today) **+** execution-result records (already carrying `disposition`) → the same `candidate/diagnostic/in_flight` counts. Decision layer (:82, :95-134) **unchanged**. Mixed runs aggregate naturally.
5. **Generalize the trigger.** Consumer reacts to `execution_step_terminal` (with `generation_artifact_terminal` as one instance), re-partitions the run. Keep the idempotent pattern.
6. **D4 — faithful Vision sync stub.** Writes **one** execution-result with the *real* Vision disposition (`candidate` on success / `diagnostic` on failure) + emits `execution_step_terminal`. **No submit, no poll, no artifact, no direct advancement.**
7. **D3 — seed + replay.** Seed a perception step into a run via replay/fixture; **defer full planner integration.** Minimum primitive only.

## Verification (the proof V4 exists to produce)

- **Sync Vision run** advances `execution → audit` with **no generation artifact, no poll, no direct handler advancement.**
- **Generation still works unchanged** (the 3-binding generalization is additive; existing path intact).
- **Mixed run** (generation + Vision steps in one run) aggregates correctly into the family-agnostic counts → the **strongest proof** the partition is genuinely family-agnostic, not two parallel paths bolted together.

## Scope guard
Minimum family-agnostic completion primitive. **Do NOT:** build the planner (D3 defers it), generalize `orch_generation_artifact` into a protocol/view (Creative — preserves the wrong ontology), let Vision impersonate generation, or let the handler impersonate the lifecycle. The referent-resolution echo of V4 is the *discovery* that the runtime was artifact-shaped not completion-shaped — making it completion-shaped is the deliverable, not "Vision works."

## Cross-refs
DT D2 grounding (this thread) · `.planning/PHASE-7-VERTICAL-4-VISION-FRAMING.md` · seam sites in `event_consumer.py` (:16/:43/:82/:95-134/:209/:219-224), `drivers.py:32-42`, `dispatcher.py:121-145`, `worker.py:186-198`.
