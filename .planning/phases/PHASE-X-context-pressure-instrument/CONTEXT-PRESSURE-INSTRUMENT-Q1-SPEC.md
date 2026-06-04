# Context Pressure Instrument — Q1 Capture-Schema SPEC (Stage 1, rev 2 — Stage-1b folded)

**Status:** Stage-1 SPEC, **Stage-1b review folded** (DT + Creative converged: 2 contradictions, 1 overclaim, 1 seam-clarity, 1 inert-kept, focus-hook elevated). Awaits Creative's capture-surface experience pass + the focus-state definition discussion before PLAN. **No implementation authorized.** **Base:** `main @ 2f5e1ee`.
**Grounded against (read at draft):** `tools/project.py:638-710` (`flame_context` raw shape), `comprehension/_schema.py` (the captured/authored validation pattern), `translation_oracle/_schema.py` + `_transcode.py` (the lock + transcode precedent).

This is the migration-if-wrong decision. The SPEC locks **record SHAPE** (migration-if-wrong) and leaves **value-sets additive** (measure-first — failure taxonomy is populated by data, not pre-locked). **The one architectural — not wording — finding is the focus-hook below.**

---

## ⭐ FIRST-CLASS ARCHITECTURAL DEPENDENCY — the focus-hook (the real migration-if-wrong surface)

`flame_context` captures desktop **inventory** — `{project, project_folder, workspace, desktop, reel_groups[→reels→items], batch_groups[names]}` — i.e. **what exists.** It does NOT capture **what is in focus**: no active/current sequence, no *which* batch is open, no selected segments, no active tab/playhead. **Contextual references ("this", "selected", "current") resolve against focus, not inventory** — so a corpus built on `flame_context` alone knows what was *available*, not what the operator was *looking at*, and **cannot answer "would context have changed the outcome?"** This is CR.1 one layer deeper.

This is elevated (Creative) from implementation detail to **first-class architectural dependency**, because the migration asymmetry is absolute:
- If `extracted` is wrong → regenerate it from `raw`.
- If `analysis` is wrong → re-author it.
- **If focus state was never captured → the evidence is gone forever.**

Therefore **`world_state.raw` completeness on the focus snapshot is THE migration-if-wrong surface of this phase** — not the record shape (which is sound). `world_state.raw` = `flame_context` output **+ a focus snapshot** (active sequence · open batch · current selection · active tab · playhead · focus state). The focus snapshot is **new hook work** — central, not minor. **The next room discussion (before PLAN) is the focus-hook itself:** what exactly constitutes operator focus state inside Flame, and how do we guarantee we capture it completely enough that future contextual analysis remains possible?

## Package
`forge_bridge/context_pressure/` — 4th instrument (distinct from `comprehension/`, `corpus/`, `translation_oracle/`). Own `__all__`, `SCHEMA_VERSION = "1"`, atomic-append JSONL with a `{"_header": True, ...}` first line (mirror `corpus`/`comprehension`). **Net-new authored vocab** (the distinct-instrument constraint bites on the *authored* `failure_class` — the evaluation vocab). The observed *fact* vocab (`outcome`) is **aligned to the real runtime SSE taxa** (genuinely shared, zero-mapping for the aligned states — see `OUTCOME_VALUES`), with one net-new state for the executor-gap case.

## The record — `ContextPressureRecord`

| key | layer | req? | type / contract |
|---|---|---|---|
| `schema_version` | — | ✓ | str, `== "1"` |
| `captured_at` | captured | ✓ | non-empty str (ISO ts) |
| `provenance` | captured | ✓ | dict — see below; **from day one** |
| `prompt` | captured | ✓ | str (operator prompt, verbatim) |
| `observed_translation` | captured | ✓ | dict `{compiled_graph: list[str], ratified_graph: list[str] \| None}` |
| `outcome` | captured | ✓ | str ∈ `OUTCOME_VALUES` |
| `world_state` | captured | ✓ | dict `{source, raw, extracted}` — the envelope/payload slot |
| `analysis` | **authored** | **optional / nullable-pending** | `None` or dict — see below |

**`provenance`** (all str, all required — Creative's day-one block):
`{context_source ∈ CONTEXT_SOURCE_VALUES, capture_version, capture_surface, capture_adapter}`.

**`world_state`** — agnostic envelope, source-rich payload. Three layers with sharply different care levels:
- `source`: str, must equal `provenance.context_source` (validator tripwire — *inert under single-source capture today, defensive future-proofing against a multi-source/adapter bug; not an active invariant*).
- `raw`: dict — verbatim source dump (Flame: `flame_context` **+ focus snapshot**). **THE load-bearing, over-capture, migration-if-wrong surface.** All care goes here: the focus-hook must dump *everything* into `raw`.
- `extracted`: dict — a **named capture PROJECTION of `raw`**: deterministic, computed at capture, **never authored**, recomputable. Mistakes here are **free** — re-extract from `raw`, no migration. (Lean: source-namespaced keys, e.g. `flame.project`, `flame.active_sequence`, `flame.open_batch`, `flame.selection`, `flame.active_tab`.) It is NOT an analysis surface — `raw → (deterministic) → extracted` vs `captured → (authored reasoning) → analysis` are fundamentally different operations; keep them impossible to confuse.

**`analysis`** (authored, `None` until an analysis pass runs):
- `authored_at`: non-empty str — **REQUIRED when `analysis` is non-null** (the no-copy structural guard, below).
- `failure_class`: `None` or str ∈ `FAILURE_CLASS_VALUES` (additive set).
- `referent`: `None` or str — authored interpretation of the contextual ref.
- `world_state_resolvable`: `None` or bool — **the Q3 counterfactual** (would captured context have resolved it?).
- `resolving_signal`: `None` or str — which `extracted` signal would resolve it (feeds the per-signal "which first" ranking).

## The no-copy principle — encoded as a structural guard (not just doctrine)

> **Observed context MAY inform authored analysis. Observed context MUST NEVER automatically become authored analysis.** (Creative, verbatim.)

The teeth, **strongest-first** (the structural protection is the load-bearing one, the timestamp is a backstop):
1. **Separate code paths (structural — where the real protection is):** the capture factory **only ever writes `analysis=None` and has NO path to populate it.** `analysis` is written *exclusively* by a distinct later authoring pass. Capture structurally *cannot* author.
2. **Separate lifecycle:** capture-time vs a later analysis pass — different operations, different entry points.
3. **`authored_at` validation backstop:** `analysis` non-null ⇒ `authored_at` non-empty. This does NOT make copying impossible (a deliberate copy can stamp a timestamp trivially) — it forces a doctrine violation into a **deliberate, review-visible code path** and catches the accidental/lazy copy. Accurate teeth, not absolute.

The gap between observed context and correct interpretation **is the measurement** (active=A, selected=B, "rename this sequence" → `referent` may be B); collapsing them re-plants the `expected_well_formed` mistake TF.3b retired.

## Vocabularies

- `CONTEXT_SOURCE_VALUES` = `{flame, cli, forge_graph, bridge_ui}` — net-new; additive.
- `OUTCOME_VALUES` = the **real runtime SSE taxa** `{chain_complete, preview_emitted, apply_complete, chain_aborted, compile_error, error}` (genuinely shared → zero transcode mapping for these) **+ `blocked_at_ratify`** as the only net-new state (the Option-B mutation reaching preview but gated at ratify with no executor — a captured outcome, not a failure). Additive. The transcode mapping table now covers only `blocked_at_ratify` → oracle outcome, not a parallel renamed vocab.
- `FAILURE_CLASS_VALUES` — **authored, additive, measure-first.** Seed minimal: `{unresolved_reference, wrong_referent, ambiguous_reference, missing_from_world_state}`. The set grows as analysis observes real failures (do NOT pre-lock a rich taxonomy — measure first). Validation checks membership only when present.

## Validation contract (mirror `comprehension/_schema.validate_*`)
Required-keys check → `schema_version` → `captured_at` non-empty str → `provenance` dict with 4 required str sub-keys + `context_source ∈ CONTEXT_SOURCE_VALUES` → `prompt` str → `observed_translation` dict (`compiled_graph` list-of-str; `ratified_graph` list-of-str or None) → `outcome ∈ OUTCOME_VALUES` → `world_state` dict (`source == provenance.context_source`; `raw` dict; `extracted` dict) → `analysis` is None **or** dict with `authored_at` non-empty + each authored field None-or-typed-or-in-vocab. `SchemaValidationError` / `SchemaVersionMismatch` mirror the sibling instruments.

## Transcode shape (DESIGNED, not built — substrate-before-consumer)
`context_pressure record → translation_oracle.TranslationCase`:
- `observed_translation.compiled_graph` → `ObservedTrace.observed_graph`; `outcome` → `ObservedTrace.outcome` (via a mapping table — sub-decision).
- `provenance.context_source` → a **new oracle `capture_provenance="operator-pressure"`** (additive bump to the oracle, deferred until consumed). This seed type carries the real-compile Tier-1 markers seed-legibility can't → **first seed that can fill oracle Tier-1 cells.**
- `world_state` → `label.world_state` **by AUTHORING, never copy** (the no-copy principle crosses the transcode); `analysis.failure_class` (contextual) → `label.expected_classes` by authoring.

## Acceptance criteria (what a correct implementation satisfies)
1. Captured fields required; `analysis` nullable-pending; **`analysis` non-null ⇒ `authored_at` present** (the validation backstop; the structural protection is the capture factory having no author path — see no-copy §).
2. `world_state.source == provenance.context_source` — present as a defensive tripwire (inert under single-source capture; not an active invariant).
3. **Capture-completeness (not derivation):** the captured fields (`world_state` + `observed_translation`) contain **every INPUT an analyst needs to author `world_state_resolvable`** — no required signal is capture-optional or absent. *(`world_state_resolvable` is authored — deciding "would context have resolved it" needs the authored `referent` — so this criterion is about capture-completeness, NOT offline derivation.)*
4. Provenance block (4 fields) present from record one.
5. Own `__all__` + `SCHEMA_VERSION="1"`; net-new `FAILURE_CLASS_VALUES`; **no touch** to `forge_bridge.__all__` (19) or `translation_oracle.__all__` (19); no new libs.
6. Atomic-append JSONL with header; validation mirrors the sibling instruments' shape.
7. **`world_state.raw` carries the full focus snapshot** (the migration-if-wrong surface — see the focus-hook §); `extracted` mistakes are recoverable, missing `raw` focus state is not.

## Out of scope (the brief's boundary stands)
Desktop-contextual resolution; resolver access to desktop state; context injection into `compile_intent()` (world_state captured out-of-band, never threaded into compile); graph redesign; fixing contextual failures. **Observed contextual failures are data, not bugs.** The capture surface (Flame Python Console ergonomics) is Creative's experience pass, not this SPEC.

## Where the reject threshold lives (relocation confirm — DT + Creative)
Q3's reject threshold ("able to say *don't build it*") is **correctly absent from the record schema** — the schema captures *evidence* (`world_state_resolvable`, `resolving_signal`); Q3 success-criteria defines what evidence is *sufficient*. **Confirmed home: the Q3 / success-criteria artifact** (cost-anchored, symmetric, precommit-the-rule-not-the-percentage). It must not evaporate — the measure-first gate's whole point is that it can conclude *against* desktop-wiring.

## Open sub-decisions (for plan — not migration-if-wrong)
- `FAILURE_CLASS_VALUES` seed — keep minimal; data extends it.
- `blocked_at_ratify → oracle outcome` transcode mapping (the only outcome needing a map now that the rest align).
- `extracted` keys: source-namespaced (my lean) vs flat.
- Oracle `capture_provenance="operator-pressure"` additive bump — land when the transcode is consumed.

*(The focus-snapshot hook was here in rev 1; rev 2 elevated it to the first-class architectural dependency above — it is the migration-if-wrong surface, not an open sub-decision.)*
