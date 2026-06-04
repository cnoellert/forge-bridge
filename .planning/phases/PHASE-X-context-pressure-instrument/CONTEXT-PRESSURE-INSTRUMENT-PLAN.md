# Context Pressure Instrument — PLAN

**Status:** PLAN open, **plan-check folded** (DT + Creative: passes with one required fix — S4 must detect *both* contextual-failure modes; + reject-threshold cost-anchoring made explicitly pre-delta). **Ratify-ready.** Base: `main @ 77243e0`. Discuss settled; all migration-if-wrong decisions closed (SPEC rev 2 + `FOCUS-STATE-DISPOSITION.md`).

**Authorized now:** S1 (it does not depend on the S4 fix — clean dev-box start). **S4 implementation must carry both failure modes + the mode-(b) seed before S4 is claimed closed**, or the CR.1 fix is only half-made (capture exists, analysis exists, analysis blind to the dominant failure). Console ergonomics (Creative) runs alongside.

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
**The failure set has TWO modes — S4 MUST detect both (DT+Creative ratify-gate; goal-backward).** A contextual resolver fails two ways, and catching only the first systematically under-counts the dominant/most-dangerous failures and biases the ruling toward *don't-build* (it omits exactly what desktop-wiring fixes):
- **(a) Unresolved ref** — "this sequence" → no concrete value (honest-decline / `UNRESOLVED_REQUIRED_PARAM`). **Derivable from `compiled_graph` alone.**
- **(b) Confident-wrong resolution** — "this sequence" → resolved to a *wrong concrete value*, dispatched as if grounded (the IDX-13 case from this phase's own discuss: `world_state` focus = `30sec_edit 21`, compiled `sequence_name=30sec_21`; the TF.4 space-mangle class). **Not unresolved — resolved, confidently, wrong.** This is the common, silent, dangerous mode.

Both ride the captured/authored lock cleanly:
- **Candidate-flagging is AUTOMATIC (captured-derivable):** mode (b) candidate ⇔ `compiled_graph`'s resolved value ≠ the captured `world_state` focus signal. Both operands are captured fields — no authoring needed to *flag*.
- **Confirmation is AUTHORED:** "was that focus signal actually the intended referent?" → `analysis.failure_class` + `referent` + `authored_at`. The system says "this looks suspicious"; only authored analysis says "this was wrong."

The Q3 metric over the confirmed failure set: `world_state_resolvable` = was the referent present in captured `world_state`? + `resolving_signal` + per-signal frequency ranking.
- **Exercised on a seed corpus at build time** so the loop is proven closed *before* real operator data (the CR.1 fix). **The seed MUST contain a mode-(b) IDX-13-shaped case** (operator "this sequence"; `world_state` focus `30sec_edit 21`; compiled `sequence_name=30sec_21`) — else the seed validates only the mode S4 already handles, a false-green analyzer (`[[feedback-fixture-shape-mirrors-production]]`).
- **Acceptance (both modes):** (1) unresolved-ref case → flagged contextual failure; (2) **compiled-value-≠-captured-focus case → flagged contextual-failure candidate**; (3) referent-in-`world_state` → resolvable=True, absent → False (symmetric); (4) per-signal ranking emitted. *Acceptance #2 is the load-bearing addition — without it the analyzer is quietly blind to the dominant failure.*

### S5 — transcode path  *(designed; build deferred per substrate-before-consumer)*
Lock the mapping (`context_pressure` record → `translation_oracle.TranslationCase`): `observed_translation.compiled_graph → ObservedTrace.observed_graph`; `outcome → oracle outcome` (only `blocked_at_ratify` needs a map; rest align); **`world_state → label.world_state` by AUTHORING, never copy**; new oracle `capture_provenance="operator-pressure"` (additive bump). **Build when the oracle consumes operator-pressure records — document only this phase.**

## 4. Parallel redline stream — Console ergonomics (non-blocking)
Creative owns the operator-experience pass: persistent console panel vs command-prompt style vs slash-commands vs floating widget vs conversation history. **Redesign-test (must hold):** none of these can invalidate the corpus schema, capture flow, world-state model, transcode path, measurement methodology, or success criteria. If any does, it re-enters the substrate discuss; otherwise it's a surface skin over a settled S1–S4.

## 5. Success criteria (the phase, not just the build)
- **Build:** S1–S4 delivered + tested (S5 documented). The analysis loop (S4) is exercised on a seed corpus — closed before real data.
- **RUN (phase value):** operators drive the Console; the corpus accumulates **paired** records (every record carries world_state, every focus signal captured-or-explicitly-absent-with-reason). Analysis produces the **resolvable-delta** + per-signal ranking.
- **Decision:** phase close answers the 5 Desired-Outcome questions and applies the **symmetric, cost-anchored reject rule** → **build OR don't-build desktop-wiring**, both valid conclusions.
- **Reject-threshold sequencing (DT+Creative ratify-gate):** the **cost-anchoring method** — *what resolvable-delta justifies the engineering cost of desktop-wiring* — must be **reasoned and written BEFORE the measured delta exists.** Otherwise the threshold gets reverse-engineered from the result ("set X just below the observed delta → always build"). **Precommit the cost reasoning; the data fills the delta, not the threshold.** Lives in the Q3/success-criteria artifact, authored pre-RUN.

## 6. Sequencing + what needs a Flame workstation
Dev-box-testable first: **S1** (schema) → **S4** (analysis reader, on seed) → **S2 assembler/unwrap** (fixture-tested). Flame-gated (workstation): **S2 live read** → **S3 capture flow**. This honors substrate-before-consumer (schema + analysis land and test on their own commits before the Flame-side capture rides).

## 7. Constraints (binding)
`context_pressure/` is a 4th instrument: own `__all__` + `SCHEMA_VERSION="1"` (additive); net-new authored `FAILURE_CLASS_VALUES`; observed `OUTCOME_VALUES` aligned to real SSE taxa. **No touch** to `forge_bridge.__all__` (19) or `translation_oracle.__all__` (19). `compile_intent` / `parse_chain` untouched (capture wraps, never modifies). No new external libraries. Frozen + `reference/` corpora of other instruments never touched.

## 8. Out of scope (the brief's boundary stands)
Desktop-contextual resolution; resolver access to desktop state; context injection into `compile_intent`; graph redesign; fixing contextual failures. **Observed contextual failures are data, not bugs.** The desktop-wiring build is the *downstream* phase this instrument exists to justify or reject — not this phase.
