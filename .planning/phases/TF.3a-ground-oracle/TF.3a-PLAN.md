# TF.3a (Ground the Oracle) — PLAN (rev 2, post DT plan-check)

**Milestone:** v1.13 Translation Fidelity, Phase 3a of 4 (the KEYSTONE). **Settles:** `TF.3a-DISCUSS.md`.
**Goal:** ship a **validated measurement instrument** — labeled corpus + frozen observed traces + detectors +
an oracle that emits verdict-pairs — trustworthy enough that **3b's verdicts may gate Phase 4**. 3a measures
*nothing for ranking*; it proves the instrument. North-star: *why should anyone trust this oracle?*

**rev 2 (DT plan-check):** the corpus record is `Label (expected) + ObservedTrace (observed)`, **ratified
before Step 1 code** (Finding 1 — the seed traces carry none of the Tier-1 runtime markers). Findings 2–3
folded into Steps 5 and 1.

**Constraints (binding, inherited):** public `forge_bridge.__all__` stays **19** (new package carries its own
`__all__`); no new external libraries; mirror the atomic-append-JSONL + versioned-schema pattern of
`comprehension/` / `corpus/` but **never couple schemas** — three-vocabulary rule (Q5) at the label-field level.

---

## Substrate reality (grounded; drives the rev-2 schema)

Verified against `~/.forge-bridge/comprehension/comprehension-2026-06-01.jsonl` (live):
- A record carries `{question, chain[{step, result}], answer, model, outcome, verdict, wall_clock_ms,
  schema_version, captured_at}`. `result` is the raw observed tool value.
- **NONE of the Tier-1 fine markers are present** (full-blob grep False for `tool_forced`, `tools_filtered`,
  `unresolved`, `407`, `stop_reason`, `tool_selection`, `resolved_param`). They were never captured (legibility
  grain) and **cannot be backfilled**.
- `outcome` **is** populated (`chain_aborted:21, answered:11, null:4`) — a **coarse** observed signal (an abort
  occurred) but **not** the fine one (`:407` honest-decline vs other abort). *(Corrects DT's "outcome is null".)*
- `world_state` is not structurally captured (the `desktop` hit in one blob is answer-text, not a state field).

**Consequence (Finding 1):** the seed-32 can feed **Tier-2 value-comparison** (observed `result` vs labeled
canonical — grounding, entity-resolution) and **expected-graph authoring** — but it **cannot feed any Tier-1
detector**, nor contextual `world_state`. Those require **fresh instrumented capture**. So the corpus is far
more *authored + freshly-captured-with-instrumentation* and far less *seed-32-relabeled* than rev 1 read.

## The ratified record model (Option A — capture-rich observed trace)

```
TranslationCase = {
  label:    Label,           # EXPECTED (authored) — the 5 fields
  observed: ObservedTrace,   # OBSERVED (frozen snapshot from instrumented compile/dispatch)
}
verdict_pair = compare(label, observed)     # what the oracle computes
```
- **Why not Option B (re-run detectors live):** rejected — model variance + pinned-env dependence makes the
  instrument a function of a live environment (the exact v1.10 measurement-instability the keystone escapes).
- **Why not Option C (infer Tier-1 from chain/answer text):** rejected — that reintroduces the "no compile line
  can't discriminate shadow from clean compile" ambiguity TF.2 *removed* by switching to the positive
  `tool_forced` marker. Inferring from signal-poor traces undoes that.
- **Capture has model non-determinism, but freezes ONCE** into the corpus → detectors/oracle then run
  deterministically against frozen snapshots. The freeze is the point: it's a snapshot of real translation
  behavior, which is what fidelity is measured against.

---

## Package layout — `forge_bridge/translation_oracle/`

```
forge_bridge/translation_oracle/
├── __init__.py     # own __all__; zero shared symbols with comprehension/ or corpus/
├── _schema.py      # SCHEMA_VERSION="1"; Label + ObservedTrace; two provenance roles; distinct vocabs
├── _capture.py     # instrumented compile/dispatch run → frozen ObservedTrace (the rev-2 addition)
├── _corpus.py      # data: atomic-append JSONL + coverage accounting
├── _detect.py      # logic: Tier-1 (reads ObservedTrace markers) + Tier-2 (compares label vs observed)
└── _oracle.py      # assembly: compare(label, observed) → verdict-pair + emitted provenance
```
*(Shape reference, not literal rewrite — `comprehension/_schema.py` + `_capture.py` are the closest analogs.)*

---

## Steps

### Step 0 — Re-derive the salience surface **[DONE]**
`TF.3a-SALIENCE-SURFACE.md` (committed). Detector value-set = §D there (NOT D3).

### Step 1 — Package scaffold + schema (Q1/Q5 + Findings 1 & 3) — **the ratified fork**
- `_schema.py`, `SCHEMA_VERSION="1"`, two structures:
  - **`Label` (expected, authored)** — 5 fields: `input`, `expected_graph` (step-text list, no IR — TF.1 §1),
    `expected_params` (context refs marked `unresolved-pending-dispatch`, NOT a concrete value — TF.1 §2),
    `expected_verdict_pair` (`translation∈{pass,fail} × substrate∈{pass,gap}` — **required**, the locked floor;
    honest-decline = `(pass,gap)`), `world_state` (**required for contextual labels**, nullable otherwise),
    plus **`expected_provenance`** per param.
  - **`ObservedTrace` (observed, captured)** — the observed-signals group: `observed_graph`,
    `observed_resolved_params`, `outcome`, and the Tier-1 markers `tool_forced`, `tools_filtered`,
    `abort_reason` (incl. `:407`-fired), `tool_selected`.
- **Two provenance roles, distinct fields (Finding 3):** `label.expected_provenance` vs
  `oracle.emitted_provenance`; the grounding/entity verdict = `compare(expected, emitted)`. Do not collapse.
- **Provenance vocab** `{grounded-from-intent, from-context, filled-from-example, unresolved}` — distinct
  frozenset; MUST NOT reuse comprehension's `{loved,hated,…}` or corpus's divergence vocab (Q5).
- **Verify:** `validate_*` rejects a missing verdict-pair; accepts an unresolved context-param; rejects a
  provenance value borrowed from the other instruments; round-trips a `Label`+`ObservedTrace` pair.

### Step 2 — Instrumented capture (`_capture.py`) (Finding 1's mechanism)
- Run an authored input through the **real** compile/dispatch path, recording the `ObservedTrace` markers it
  emits — **reuse, do not reimplement** (a reimplementation would diverge from production behavior).
- **Open sub-question for the executor (name, don't silently pick):** capture-by-return (instrument the
  compile/dispatch fns to surface the markers structurally) vs capture-from-logs (parse the emitted log lines).
  Lean: capture-by-return — logs are lossy and the markers already exist as response fields (`tool_forced`,
  `handlers.py:868`). Resolve at Step 2 with a live read of the dispatch return shape.
- **Contextual capture:** needs a constructed `world_state` fixture (desktop is unwired → the observed trace
  will show the *failed* resolution; the label's `world_state` holds the ground truth it should have resolved).
- **Verify:** capture of one known input freezes an `ObservedTrace` whose `tool_forced`/`outcome` match a
  hand-checked live run.

### Step 3 — Corpus data layer + coverage accounting (`_corpus.py`) (Q2)
- Atomic-append JSONL under `~/.forge-bridge/translation_oracle/` (mirror `comprehension/_capture.py` topology).
- **Coverage accounting [N]:** report per the adequacy matrix — every **verdict-pair cell × translation class ×
  multi-tag pattern × D-series defect** — with **Tier-2 ≥2 per validated cell** (tune + holdout), **Tier-1 ≥1**.
- **Verify:** report flags an under-covered cell; thin fixture shows RED.

### Step 4 — Seed + author the corpus (Q2 + Finding 1 split)
- **Tier-2 + expected-graph from seed-32:** relabel the 32 well-formed traces on the translation-correctness
  axis (discard legibility `verdict`); use observed `result` for value-comparison. Aborts → decline-vs-misroute
  via `outcome` + (where present) `abort_reason`; a correct abort = `(pass,gap)`.
- **Tier-1 + contextual from fresh capture:** author inputs and run them through Step 2's `_capture.py` (Tier-1
  markers only exist here); author contextual cases **with `world_state`**.
- **Author to GREEN:** until Step 3's report is complete; **log authored-vs-seeded provenance** (no silent gaps).
- **Verify:** coverage GREEN; the Tier-1 cells are fresh-captured (not backfilled from seed).

### Step 5 — Validate the instrument (Q3 + Finding 2)
- **Tier-1 — positive+negative unit pair per detector** (logic-bug surface): fires on the grounded defect,
  silent on a clean negative. Not a statistical holdout (wrong tool for logic bugs).
- **Tier-2 — pass/fail traps at low n, NOT an agreement rate (Finding 2 reframe):** at ≥2/cell the held-out
  instance is **one trap**; the gate = **the oracle must pass every trap**. This catches gross instrument
  errors. **Name the honest ceiling [N]:** a real *agreement rate* needs a materially larger authored corpus
  than hand-authoring affords this phase — 3b must NOT inherit "validated within threshold" as statistical
  confidence (`[[feedback-operational-maturity-not-completeness]]`; the v1.10 measurement-debt lesson).
- **Example-fill FP rate (Q4):** hand-label corpus values matching the Step-0 §D set as `lifted` vs
  `legitimately-equal` (§E prone literals: `30sec_21`,`noise`,`tst`,`ABC`); report against the **complete**
  surface. **Gate:** grounding-class scoring not released to 3b without this number.
- **Verify:** Tier-1 pairs pass; every Tier-2 trap passes; FP rate recorded with the ceiling stated.

### Step 6 — Oracle assembly (`_oracle.py`)
- `compare(label, observed)` → verdict-pair + `emitted_provenance` per param. No ranking, no frequency (3b).
- **Verify:** well-formed verdict-pair + emitted provenance for every case; round-trips `_schema.validate_*`.

---

## Goal-backward verification
1. Verdict-pair on every label → honest-decline scorable as success. ✓ S1
2. Tier-1 reads real captured markers (not inferred / not backfilled) → no wedge, no TF.2-ambiguity regression. ✓ S1–2, 4
3. Coverage complete, not counted → no cell silently unmeasured. ✓ S3–4
4. Tier-1 fail-when-should + Tier-2 traps all pass → detectors trusted at honestly-stated confidence (not overclaimed). ✓ S5
5. Example-fill measured vs the complete surface → FP rate is the real number. ✓ S0 + S5
6. One package, distinct vocabs, two provenance roles → no schema coupling/collapse. ✓ S1

## Out of scope
The 3b run, verdict aggregation, frequency, ranking, and **all Phase-4 fixes**. 3a ships the instrument; 3b
measures.

## Commit cadence
Atomic per step (S0 committed). Each step: code + verification test in one commit; coverage + validation reports
committed as artifacts. `pytest tests/translation_oracle/` green before close.
