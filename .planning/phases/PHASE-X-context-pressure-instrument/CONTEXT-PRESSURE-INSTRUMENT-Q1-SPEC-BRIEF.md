# Context Pressure Instrument — Q1 Capture-Schema SPEC BRIEF

**For:** DT, drafting the Q1 capture-schema SPEC (the one migration-if-wrong decision). **Status:** DISCUSS converged (Creative + DT + Orch); SPEC authorized; **no implementation**. **Base:** `main @ cd95ab5`.

This brief is the locked convergence as a constraint list so the SPEC draft doesn't re-derive it. The schema is the TranslationCase decision one instrument downstream — **get the lock right and the rest is plumbing the surfaces that already exist** (Flame hook reads desktop, chat compiles, ratify chain previews).

---

## What this instrument measures (the bar, so the schema serves it)
Not "does context exist" (the useless lower bar — everyone knows it does). **Would ACCESS to the captured context have CHANGED the outcome?** The schema exists to make that counterfactual computable offline. Symmetric by design — it must be able to conclude **"don't build desktop wiring"** (Outcome B) as readily as "build it" (Outcome A). That symmetry is what makes this a measurement phase, not a stealth desktop-wiring phase.

## The package (distinct-instrument, binding)
`forge_bridge/context_pressure/` — a **4th** corpus instrument alongside `comprehension/`, `corpus/`, `translation_oracle/`. Own `__all__`, own `SCHEMA_VERSION`, **net-new vocabularies** (the distinct-instrument constraint bites at the field level — do not reuse the others' label/verdict vocabs). Atomic-append JSONL, mirroring the comprehension/oracle topology. **Transcode-designed** (records map into `translation_oracle` cases later) but **schema-independent** (no import coupling — the transcode is a mapping function, not a shared schema).

## The record — envelope/payload split (the synthesis that reconciles DT and Creative)

`ContextPressureRecord` — **agnosticism is an ENVELOPE property, not a payload constraint.** Guards both failure modes: Flame lock-in (Failure A) and premature abstraction that discards the signal you needed (Failure B).

```
ContextPressureRecord
├── provenance          # see Invariant 4 — from day one
├── prompt              # operator_prompt (captured fact)
├── observed_translation # compiled_graph + ratified_graph (the ObservedTrace-equivalent)
├── outcome             # execution_outcome (incl. "blocked-at-ratify")
├── world_state         # the slot — agnostic envelope, source-rich payload:
│   ├── source          # = "flame" (the context_source tag)
│   ├── raw             # verbatim source-specific dump (over-capture lives HERE)
│   └── extracted       # {project, sequence, selection, batch, active_tab, …}
└── analysis            # AUTHORED, optional, nullable-pending (see Invariant 1)
    ├── failure_class    # NEVER stamped at capture
    ├── referent         # authored interpretation of the contextual ref
    └── world_state_resolvable  # the counterfactual verdict (Q3's metric)
```

The four envelope fields (prompt / world_state / observed_translation / outcome) are DCC-agnostic; the `world_state.raw` + `extracted` payload is unapologetically source-rich. Future Graph / CLI / Bridge UI contribute different payloads inside the same envelope.

## Binding invariants (each is a SPEC acceptance line)

1. **Captured/authored split (the lock).** Captured-observation = required (`provenance`, `prompt`, `observed_translation`, `world_state`, `outcome`). Authored-analysis = optional, **nullable-pending-analysis**. `failure_class` is authored, **never a capture field** — detecting a contextual failure *is* the analysis (it compares graph-resolution against world_state). Stamping it at capture would block capture or auto-misclassify. Same lock as TranslationCase.

2. **Over-capture world-state, inside the payload.** Generous, not a minimal five — CR.1 recursed: you cannot measure the value of a signal you didn't record, and under-capture is *silent* (looks complete until the Q3 delta needs an unrecorded signal). Capture the full cheaply-available desktop state from the Flame API into `world_state.raw`; `extracted` is the narrow analysis surface (cheap to extend by re-extracting from raw — no migration). Storage cheap; lost context unrecoverable.

3. **No-copy transcode (first-class principle — Creative, verbatim):**
   > **Observed context MAY inform authored analysis. Observed context MUST NEVER automatically become authored analysis.**
   Captured `world_state` (observed fact) must never be mechanically copied into authored `analysis.referent` / a future `label.world_state`. The gap between observed context and correct interpretation **is the measurement** (active_sequence=A, selected=B, "rename this sequence" → referent may be B). Collapsing them recreates the exact `expected_well_formed` category mistake TF.3b just retired. The schema must not provide a copy path.

4. **Provenance from day one.** Not just `source`/`context_source` — also `capture_version`, `capture_surface`, `capture_adapter`. Trivial now, painful later: when the corpus answers contextual-resolution questions we'll need to know whether a record came from Python Console v1/v2, a Graph prototype, CLI capture, etc. Bake the full provenance block at record one.

5. **Symmetric, computable Q3.** The schema must let `analysis.world_state_resolvable` be computed offline from `world_state` + `observed_translation` alone (the counterfactual: "was the unresolved referent present in the captured world_state?"). No field required for that check may be capture-optional.

## Grounding anchors (read before drafting — substrate-shape-at-spec-stage)
- **`world_state` source:** `forge_bridge/tools/project.py:638` (`flame_context`) — already snapshots project / workspace / desktop / reels→sequences→segments / batch-names. The `raw` payload is essentially its return. **Known gap:** `selection` and `active_tab` are NOT in `flame_context` today — name the small hook extension as a real cost.
- **Captured/authored split precedent:** `translation_oracle/_schema.py` (ObservedTrace required / Label optional) + `comprehension/_schema.py` (`_REQUIRED_KEYS`, verdict nullable-at-capture).
- **Transcode precedent:** `translation_oracle/_transcode.py` (`transcode_comprehension_record` — import→ObservedTrace, new `capture_provenance`, no schema coupling). Sub-decision for the SPEC: align `outcome` vocab with the oracle's so transcode is cheap, vs net-new with a mapping table. Flag, don't pre-decide.
- **The no-copy lesson source:** `.planning/phases/TF.3b-corpus-instrument/TF.3b-CLOSE.md`.

## Boundaries the SPEC must hold
- **Capture sees desktop; resolver stays blind — structurally.** `world_state` is captured by a separate out-of-band `flame_context` call and stored; it is **never threaded into `compile_intent()`**. The guarantee is a sidecar call, not a flag.
- **Out of scope** (the brief's list stands): desktop-contextual resolution, resolver access to desktop state, graph redesign, context injection into compile, fixing contextual failures. **Observed contextual failures are data, not bugs.**

## Division of labor
- **DT:** the Q1 capture-schema SPEC (this brief) — record shape, required/optional split, world_state envelope/payload, provenance block, vocab decisions, the no-copy schema constraint, transcode-mapping shape.
- **Creative:** the capture-surface experience pass (Flame Python Console operator ergonomics — the axis DT and Orch are light on).
- **Orch:** synthesis + Stage-1b review of DT's SPEC draft (fix-shape + spec-artifact: contradiction, dropped invariants, inert constraints).
- **Deferred to plan:** Q2 mechanics (preview-capture wiring), Q3 reject-threshold number (cost-anchored, set from data — precommit the rule, not the percentage), the transcode implementation (substrate-before-consumer — build when Phase X consumes it).

## Counts/discipline
New package carries its own `__all__` + `SCHEMA_VERSION`; **does not touch** `forge_bridge.__all__` (19) or `translation_oracle.__all__` (19). No new external libraries.
