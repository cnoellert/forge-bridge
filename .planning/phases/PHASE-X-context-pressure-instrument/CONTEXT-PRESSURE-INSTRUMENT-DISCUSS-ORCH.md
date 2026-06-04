# PHASE X — Operator Pressure Corpus · Orch DISCUSS pass (→ DT / Creative redline)

**Status:** DISCUSS. No implementation authorized. Responds to Creative's PHASE-X brief.
**Grounded against:** `translation_oracle/_transcode.py`, `_schema.py` (`world_state`), `comprehension/_schema.py` (the CR.1 instrument), `tools/project.py:638` (`flame_context`). Base `main @ cd95ab5` (v1.13 CLOSED).

I endorse the phase's thesis and its two framings (Flame = authoritative context source; measure-before-architect). One grounded catch reshapes Q1, and the CR.1 precedent adds a second non-negotiable. Strong positions on all three Qs below.

---

## The catch that governs Q1 — captured world-state is an OBSERVATION, not a label (we just paid down this exact bug)

The oracle's `world_state` lives on the **Label** (`_schema.py:225`, `_authored.py:45`): authored, per-input, stable — *"for this input, the relevant desktop context is X."* The world-state Phase X captures at interaction-time is a **per-observation** fact — *"the desktop happened to look like X when this interaction occurred."* **These are different layers.** Putting captured desktop-state where `label.world_state` lives would repeat the precise mistake TF.3b just retired: a per-manifestation fact smuggled into the per-input intent layer (`expected_well_formed`, RIP). The TranslationCase lock — verdict↔observation (volatile) / intent↔label (stable) — applies to Phase X **before a line is written**:

- Captured world-state → **ObservedTrace lineage** (a sidecar on the observation).
- Any later `label.world_state` → **derived** from a captured observation during authoring, a separate stable artifact.

This is the answer to Creative's "mistakes here become migrations": the migration trap *is* conflating these two. Keep them separate from record one.

## Q1 — Capture shape: broad-verbatim + narrow-extracted, its own 4th instrument

**A fourth corpus instrument** (`operator_pressure/`), own `__all__` / `SCHEMA_VERSION` / net-new vocab — the distinct-instrument constraint is binding (comprehension / corpus / translation_oracle / +pressure). Agreed with Creative's independence.

**The schema shape — the load-bearing decision.** Avoid both traps:
- Rich typed world_state upfront → the migration trap (every new field is a schema bump; you can't predict which desktop signals matter before measuring).
- Schemaless blob → the **CR.1 trap** ("capture exists, analysis does not" — unanalyzable).

**Resolution (mirrors the TF.4 `compile_raw` decision — keep the raw, extract the view):**
- `world_state_raw`: the **verbatim `flame_context` JSON**, captured opaque. Insurance against under-capture — you can re-extract a new signal later *without re-capturing*, and you cannot analyze what you never captured. This is the non-negotiable's real teeth.
- `world_state`: a **small set of named, queryable extracted fields** the analysis actually consumes — `project`, `open_sequence`, `open_batch`, `selection` (segment set), `active_tab`. The analysis surface. Cheap to extend (re-extract from raw, no migration).

Capture-broad / extract-narrow. The named fields are where the counterfactual (Q3) runs; the raw blob is why a missing field is never fatal.

**Transcode path — the richest seed type.** `transcode_comprehension_record` is the precedent: import → ObservedTrace, new `capture_provenance`, no schema coupling. But note the upgrade: an operator-pressure capture runs the **real compile/ratify path** (unlike `seed-legibility`), so its transcoded ObservedTrace carries the **Tier-1 runtime markers** seed-legibility can't (`tool_forced`, `tools_filtered`, the fine abort reason). **Operator-pressure is the first seed type that can fill the oracle's Tier-1 coverage cells** — real pressure replacing synthetic seed is not just lineage, it's a coverage upgrade. Sub-decision for the plan: add a new oracle `capture_provenance` value (`operator-pressure`, additive SCHEMA bump) vs. transcode-as-`instrumented-translation`. I lean a distinct value — operator-real and harness-real are worth telling apart in coverage.

## Q2 — Full ratify flow (Option B), but the contextual-failure signal is executor-INDEPENDENT

**Strong reco: Option B.** Reads-only under-samples exactly what Phase X exists to measure — contextual resolution is load-bearing *most* on mutations ("rename **this** sequence", "publish the **selected** shots"). Measuring context-value on reads only is measuring it where it matters least.

**But dissolve Option B's stated con.** The brief lists "requires executor-path availability" (the bootstrap-console-executor-gap — supervised daemon runs executor-less, `[[project-bootstrap-console-executor-gap]]`). It doesn't, for the thing we're measuring: **a contextual failure is visible at the compile/preview seam — an unresolved "this sequence" ref in the graph — which is BEFORE apply.** Capture full intent distribution (reads + mutation-requests through preview), measure contextual failure at compile/preview (exists today, executor-independent); only the *apply-outcome tail* rides executor availability. So: Option B for intent coverage, compile/preview for the failure signal, executor deferred for the outcome tail. The con evaporates.

## Q3 — Success criteria: the counterfactual, not the count (CR.1's lesson made binding)

CR.1 is the cautionary instrument: it **built the capture and the analysis never happened.** So success must NOT be occupancy (N records). The decisive criterion is the **counterfactual-resolution rate**, computable offline from the paired world_state **without building the resolver**:

> For each contextual failure (unresolved ref at compile/preview), **was the referent present in the captured `world_state`?**

- High → desktop wiring is **justified** (the context was right there; the resolver just couldn't see it).
- Low → desktop wiring is **rejected** (the referent wasn't in desktop state; the problem is elsewhere).

This is measure-first-can-say-*don't*-build (`[[feedback-measure-first-gate-rung-not-built]]`) realized: paired world_state lets the room answer "would desktop wiring have helped?" by inspection, before one line of resolver. The five Desired-Outcome questions all fall out of: **contextual-failure frequency · counterfactual-resolution rate · failure-family ranking · coverage by contextual-reference-TYPE** (not operator count — coverage-not-count, the oracle's doctrine; success ≠ adoption, per the brief).

## Second non-negotiable (from CR.1) — the analysis ships WITH the capture

The brief's non-negotiable is *world_state paired with every record*. CR.1 proves a second is needed: **the counterfactual-analysis reader must ship in the SAME phase as the capture instrument**, exercised over a tiny seed corpus, so the loop is proven closed *before* real operator data arrives. A capture instrument without its first consumer is a dormant instrument — the substrate-before-consumer / measure-first lesson. Don't ship capture in Phase X and analysis "later"; later is where CR.1 died.

## Structural seams (caution — name before building)

1. **world_state on observation, not label** (above) — the governing seam.
2. **Capture sees desktop; resolver stays blind — enforce it structurally.** world_state is captured by a *separate out-of-band `flame_context` call* at capture time and stored on the record; it is **never threaded into `compile_intent()`**. The guarantee is structural (a sidecar call), not a flag — same shape as CR.1's answer-pass living only in the non-mutating branch.
3. **Capture-contract gap (grounded):** `flame_context` covers project / sequence / segments / batch-names, but **`selection` and `active_tab` are not in it today** — those need a small hook extension. Named as a real cost, not assumed free.

## Phase shape (proposed) + what this phase IS in the two-stroke

A **human-pressure measurement phase that gates a possible future substrate phase** (desktop-wiring). It honors the two-stroke cleanly: pressure first (real operators, real desktop, this phase) → substrate (desktop-wiring) *only if* the counterfactual data justifies it. It is not yet the "communicate uncertainty back to the operator" milestone — it's the instrument that earns (or kills) the desktop-wiring deferral from the v1.13 bucket.

Proposed in-scope, re-ordered by dependency: (1) `operator_pressure/` schema — broad-raw + narrow-extracted, world_state on the observation; (2) world_state snapshot wrapper over `flame_context` (+ selection/active-tab hook extension); (3) capture surface in Flame (Python Console candidate — surface is secondary, contract is primary, agreed); (4) the counterfactual-analysis reader (the second non-negotiable); (5) translation-oracle transcode path (new provenance). Out-of-scope exactly as the brief states — observed contextual failures are **data, not bugs**.

## Open questions back to the room
- **Q-a:** new oracle `capture_provenance="operator-pressure"` (additive bump, my lean) vs reuse `instrumented-translation`?
- **Q-b:** does Phase X open a new milestone (v1.14), or run as a standalone gating phase before the milestone is named? (It's measurement; I lean standalone-gating, name the milestone once the counterfactual data says what the milestone IS.)
- **Q-c:** the counterfactual "referent present in world_state?" check needs a referent-extraction from the unresolved ref — is that cheap (string-match against world_state names) or does it need the entity vocabulary? Grounding call for the plan.

---

## Orch synthesis (post-DT redline) — converged, with two thin spots sharpened

DT's redline converges with the brief and this pass. Folded as settled:
- **Q1a — captured/authored split (the lock).** Captured-observation (required: `timestamp`, `operator_prompt`, `world_state`, `compiled_graph`, `ratified_graph`, `execution_outcome`) vs authored-analysis (optional). **`failure_class` is authored, nullable-pending-analysis — NOT a capture field**, because *detecting a contextual failure IS the analysis* (compare graph-resolution against world_state). Forcing it at capture either blocks capture or stamps a wrong auto-class. Same lock as TranslationCase, one instrument downstream.
- **Q1b — over-capture world-state.** Generous, not the minimal five (CR.1 recursed: you can't measure a signal you didn't record; under-capture is *silent* — looks complete until the Q3 delta needs a signal that isn't there). Capture the full cheaply-available Flame desktop state; trim later.
- **Q2 — Option B, capture at compile→preview.** The C2 ratify chain emits `preview_emitted` with the *structural* compiled graph **before apply**, so a mutation's contextual resolution is capturable today with no executor; `execution_outcome` records `blocked-at-ratify`. Executor-wiring is a follow-on, needed only if mutation-request sampling decays.
- **Q3 — resolvable-delta as the decision metric, symmetric (must be able to reject).** Frequency/usage are *inputs*; the decision is "of the contextual failures, how many would the captured world-state demonstrably have resolved?" Rank the resolvable set by signal-type → "which first."

**Two thin spots I'm sharpening (both are the `expected_well_formed` lesson, recursed):**

1. **The transcode "captured `world_state` → oracle `label.world_state`" must be an AUTHORING DERIVATION, not a copy.** DT's shorthand is right in the clean case but load-bearing if taken literally: captured world_state is an **observed fact**; `label.world_state` is **authored ground-truth**. Mechanically copying observed→label re-plants exactly the verdict-in-the-label seed TF.3b just paid down. And the discrimination is not precious — it *is* the phase's core measurement: when the operator says "this sequence" meaning a selected-but-not-active one, `captured.active_sequence` ≠ the intended referent, and copying it would author a **wrong** ground-truth. The authoring step ("yes, the captured context is what they meant") is the contextual-resolution signal itself. **Synthesis: the transcode carries captured world_state as observed evidence; `label.world_state` is derived by authoring. Defer the mechanism (substrate-before-consumer — don't design the transcode until Phase X consumes it); flag the no-copy constraint now so the schema doesn't bake a copy path.**

2. **Q3's reject threshold precommits to the RULE, not a guessed %.** DT is right that it must be named up front (precommitment prevents post-hoc rationalization — Desired Outcome #5, the discipline's whole point). But a guessed `<X%` up front risks the inverse measure-first sin: a fabricated number steering the conclusion. **Synthesis: precommit to the decision RULE and its direction (symmetric; can-reject) and anchor the threshold in desktop-wiring's engineering cost — the resolvable-delta must clear the cost-of-building bar — rather than an arbitrary percentage set before the data exists.** Precommit the rule and the cost-anchor; let the data + cost set the number.

**Sequencing (endorsed):** settle Q1 in full (the lock) → derive Q2 as preview-capture/executor-deferred → define Q3 as resolvable-delta-with-reject-rule that Q1's generous capture feeds. Everything else is plumbing the existing surfaces already provide (Flame hook reads desktop, chat compiles, ratify chain previews).

**Greenlight:** DT drafts the **Q1 capture-schema SPEC** (the one migration-if-wrong decision) — carrying the captured/authored split, generous world-state, versioned-JSONL/own-package/transcode-designed, and the **no-copy transcode constraint** (thin spot #1) baked in as a schema constraint. Creative's redline still wanted on the **capture-surface experience** (operator-in-Flame-console UX) — the axis DT and I are both light on. Phase X stays DISCUSS until the Q1 SPEC lands and Creative's experience pass clears.

---

## Orch synthesis (post-Creative redline) — the reframe is right, with one guard

**Adopted: PHASE X — CONTEXT PRESSURE INSTRUMENT** (Flame Python Console = *first deployment target*, not the phase identity). Creative's success-metric sharpening is the same resolvable-delta, stated at the right altitude: *the corpus measures whether ACCESS to context would have CHANGED the outcome — not whether context exists* (everyone knows context exists; that's the lower, useless bar).

**Where I sit on the reframe — endorse, and on principle:** "Flame operator surface" *implicitly binds* to one interface (retrofit debt the day Forge Graph / CLI / Bridge UI become context sources); "Context Pressure Instrument, Flame first" is **deferral language that preserves maneuverability** (`[[feedback-explicitly-unbound-vs-implicitly-rejected]]`). The four fields (intent / world_state / translation / outcome) are already abstract. The reframe is correct.

**The guard (the load-bearing synthesis) — agnosticism is an ENVELOPE property, not a payload constraint.** The reframe collides with DT's over-capture mandate: Q1b wants the *full, cheaply-available Flame desktop state* (open reels, active version, playhead, batch iterations — Flame-specific); Creative wants "world_state, not Flame-specific details." Taken literally together they pull opposite ways, and the failure mode is insidious: *"make it DCC-agnostic" → "capture only fields all DCCs share" → under-capture → CR.1 death in a generality costume.* Resolution:
- **Agnostic envelope** (reusable across sources): four-field record + `world_state` slot + captured/authored analysis layer + a **`context_source` tag from record one** (the cheap structural discriminator that buys multi-DCC reuse, analogous to the oracle's `capture_provenance`).
- **Source-tagged, generous payload:** the `world_state` slot holds `{source, raw: <verbatim source-specific dump>, extracted: <named fields>}`. DT's over-capture operates **here** — Flame-richness inside a Flame-tagged payload is correct, not a leak.

**Over-capture wins inside the payload; agnosticism wins at the envelope.** That reconciles DT and Creative without sacrificing either, and it forecloses stealth-under-capture. The `context_source` tag also *strengthens* the transcode story — a source-tagged pressure record transcodes as cleanly as the oracle already imports multiple seed sources.

**Net convergence (all three voices):** Q1 is the phase; the captured/authored lock + generous source-tagged world-state is the TranslationCase decision one instrument downstream; Q2 = preview-capture (executor-deferred); Q3 = resolvable-delta with a symmetric, cost-anchored reject rule. DT drafts the Q1 SPEC under the retitled instrument + the envelope/payload split + no-copy-transcode. Creative's experience pass owns the capture-surface UX.
