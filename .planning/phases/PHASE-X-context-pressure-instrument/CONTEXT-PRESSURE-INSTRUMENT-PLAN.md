# Context Pressure Instrument — PLAN

**Status:** PLAN open (DT + Creative ruled (b): open now, Console ergonomics rides as a parallel redline, not a blocker). **Base:** `main @ <head>`. Discuss settled; all migration-if-wrong decisions closed (SPEC rev 2 + `FOCUS-STATE-DISPOSITION.md`). **No implementation until this PLAN is ratified.**

---

## 1. Background — why the phase opens now (the measurement that simplified the architecture)

Initial architectural concern was that contextual capture would require a **dedicated UI-action surface** (selection appeared to be callback-only, so a console looked selection-blind). **Live focus-state probing (Flame 2026.2.2, probes #1–#3) demonstrated that the existing Flame Python Console can observe the loaded sequence, current segment, timeline selection, batch selection, project state, and desktop state — all on demand.** As a result the operator-surface decision is settled (Console, selection-capable) and no longer blocks planning.

**Withdrawn hypothesis (preserved deliberately):** *"a UI-action surface is required to capture operator context" — REJECTED BY MEASUREMENT.* Only the numeric playhead frame is unreachable, and it is semantically subsumed by `current_segment`. This is a genuine architectural simplification purchased by measurement — the same pattern that drove TF.3a/TF.4: strong intuition → explicit probe → probe overturns intuition → the simpler design survives. The probe even proved the capture contract's own principle on itself (its derived verdict lied; the raw dump corrected it → `raw` load-bearing, `extracted` recomputable).

## 2. Settled substrate (closed — do not relitigate in this PLAN)
Capture contract · captured/authored lock · world-state over-capture · preview-capture (Option B, executor-deferred) · resolver-blind principle · decision metric (resolvable-delta, symmetric reject) · focus-hook (recipe) · surface ruling (Console). Authority: `CONTEXT-PRESSURE-INSTRUMENT-Q1-SPEC.md` (rev 2), `FOCUS-STATE-DISPOSITION.md`.

## 3. What this phase builds — the instrument (then the RUN measures)

The PLAN builds the **instrument**; the phase's value comes from the **RUN** (operators use it → paired corpus → analysis → build/don't-build ruling). Steps ordered dev-box-first (testable in isolation) → Flame-gated (needs a workstation).

### S1 — `forge_bridge/context_pressure/` package + schema  *(dev-box, fully testable)*
Per SPEC rev 2: `ContextPressureRecord` (envelope/payload, captured/authored split), validation mirroring `comprehension/_schema`, vocabs (`CONTEXT_SOURCE_VALUES`; `OUTCOME_VALUES` = SSE taxa + `blocked_at_ratify`; `FAILURE_CLASS_VALUES` seed), atomic-append JSONL with header (mirror `corpus`), own `__all__` + `SCHEMA_VERSION="1"`.
- **No-copy teeth (structural-first):** the capture factory only ever writes `analysis=None` and has no path to populate it; `authored_at`-required-when-`analysis`-non-null is the validation backstop.
- **Acceptance:** record validates; `analysis` non-null ⇒ `authored_at`; `world_state.source == provenance.context_source`; net-new failure vocab; **no touch** to `forge_bridge.__all__` (19) / `translation_oracle.__all__` (19); no new libs. Tests mirror the sibling instruments.

### S2 — focus-state snapshot reader  *(Flame-gated read; reachability proven; assembler dev-testable)*
Implements the `FOCUS-STATE-DISPOSITION.md` recipe as one out-of-band Flame read → `world_state = {source:"flame", raw, extracted}`:
`flame_context` + `flame.batch.{name,opened,current_iteration,selected_nodes,current_node}` + `flame.timeline.clip` + `flame.timeline.current_segment.{shot_name,name,start_frame,record_in/out}` + `flame.timeline.clip.selected_segments[]` + `current_marker/effect/transition`; `playhead_frame → null/unreachable_api`.
- **PyAttribute unwrap (grounded constraint):** Flame scalars return `PyAttribute` wrappers — unwrap into `extracted`; store the stringified form in `raw` so unwrap bugs stay recoverable.
- **Split for testability:** the in-Flame read snippet (Flame-gated) vs the assemble/unwrap logic (dev-box unit-tested against a fixture `raw`).
- **Acceptance:** against live Flame, a complete `world_state.raw` with the full recipe; selection + current_segment present; one `unreachable_api` tenant only.

### S3 — capture flow at the Console surface  *(Flame-gated; needs the running bridge)*
operator prompt → `compile_intent` (existing, **desktop-blind**) → preview via the C2 ratify chain (`preview_emitted`) → assemble a `ContextPressureRecord` {prompt, `observed_translation`:{compiled_graph, ratified_graph}, outcome, `world_state` (S2, **out-of-band**), `analysis`:None} → atomic-append.
- **Option B:** mutations reach preview, `outcome="blocked_at_ratify"` (executor-deferred); reads → `chain_complete`.
- **Resolver-blind guarantee (structural):** `world_state` captured by the separate S2 read, **never threaded into `compile_intent`**.
- **Acceptance:** a real Console prompt yields a valid paired record; `world_state` present; `analysis=None`; no compile path reads `world_state`.

### S4 — counterfactual analysis reader  *(dev-box, testable — the SECOND non-negotiable: ships WITH capture)*
The Q3 metric, computable from captured fields: for each contextual failure (unresolved ref at compile/preview), `world_state_resolvable` = was the referent present in captured `world_state`? + `resolving_signal` + per-signal frequency ranking. Authoring path writes the `analysis` layer (`failure_class`, `referent`, `authored_at`) as a distinct pass.
- **Exercised on a seed corpus at build time** (a handful of hand-authored or early-captured records) so the loop is proven closed *before* real operator data — the CR.1 fix ("capture exists, analysis does not" must not recur).
- **Acceptance:** referent-in-world_state → resolvable=True; absent → False (symmetric); per-signal ranking emitted.

### S5 — transcode path  *(designed; build deferred per substrate-before-consumer)*
Lock the mapping (`context_pressure` record → `translation_oracle.TranslationCase`): `observed_translation.compiled_graph → ObservedTrace.observed_graph`; `outcome → oracle outcome` (only `blocked_at_ratify` needs a map; rest align); **`world_state → label.world_state` by AUTHORING, never copy**; new oracle `capture_provenance="operator-pressure"` (additive bump). **Build when the oracle consumes operator-pressure records — document only this phase.**

## 4. Parallel redline stream — Console ergonomics (non-blocking)
Creative owns the operator-experience pass: persistent console panel vs command-prompt style vs slash-commands vs floating widget vs conversation history. **Redesign-test (must hold):** none of these can invalidate the corpus schema, capture flow, world-state model, transcode path, measurement methodology, or success criteria. If any does, it re-enters the substrate discuss; otherwise it's a surface skin over a settled S1–S4.

## 5. Success criteria (the phase, not just the build)
- **Build:** S1–S4 delivered + tested (S5 documented). The analysis loop (S4) is exercised on a seed corpus — closed before real data.
- **RUN (phase value):** operators drive the Console; the corpus accumulates **paired** records (every record carries world_state, every focus signal captured-or-explicitly-absent-with-reason). Analysis produces the **resolvable-delta** + per-signal ranking.
- **Decision:** phase close answers the 5 Desired-Outcome questions and applies the **symmetric, cost-anchored reject rule** (lives in the Q3/success-criteria artifact — precommit the rule, set the number from data) → **build OR don't-build desktop-wiring**, both valid conclusions.

## 6. Sequencing + what needs a Flame workstation
Dev-box-testable first: **S1** (schema) → **S4** (analysis reader, on seed) → **S2 assembler/unwrap** (fixture-tested). Flame-gated (workstation): **S2 live read** → **S3 capture flow**. This honors substrate-before-consumer (schema + analysis land and test on their own commits before the Flame-side capture rides).

## 7. Constraints (binding)
`context_pressure/` is a 4th instrument: own `__all__` + `SCHEMA_VERSION="1"` (additive); net-new authored `FAILURE_CLASS_VALUES`; observed `OUTCOME_VALUES` aligned to real SSE taxa. **No touch** to `forge_bridge.__all__` (19) or `translation_oracle.__all__` (19). `compile_intent` / `parse_chain` untouched (capture wraps, never modifies). No new external libraries. Frozen + `reference/` corpora of other instruments never touched.

## 8. Out of scope (the brief's boundary stands)
Desktop-contextual resolution; resolver access to desktop state; context injection into `compile_intent`; graph redesign; fixing contextual failures. **Observed contextual failures are data, not bugs.** The desktop-wiring build is the *downstream* phase this instrument exists to justify or reject — not this phase.
