# TF.3a (Ground the Oracle) — PLAN

**Milestone:** v1.13 Translation Fidelity, Phase 3a of 4 (the KEYSTONE). **Settles:** `TF.3a-DISCUSS.md`.
**Goal:** ship a **validated measurement instrument** — labeled corpus + detectors + an oracle that emits
verdict-pairs — trustworthy enough that **3b's verdicts may gate Phase 4**. 3a measures *nothing for ranking*;
it proves the instrument before 3b runs it. North-star: *why should anyone trust this oracle?*

**Constraints (binding, inherited):** public `forge_bridge.__all__` stays **19** (new package carries its own
`__all__`); no new external libraries; mirror the atomic-append-JSONL + versioned-schema pattern of
`comprehension/` and `corpus/` but **never couple schemas** — the three-vocabulary rule (Q5) bites at the
label-field level. Writer's-room cadence; grounded against live reads.

---

## Package layout — `forge_bridge/translation_oracle/`

One package = the one artifact (Q5: DT's reference corpus = Creative's provenance surface = oracle validation).
Two **independently-importable modules** inside it so 3b can pull corpus and detector separately:

```
forge_bridge/translation_oracle/
├── __init__.py        # own __all__; zero shared symbols with comprehension/ or corpus/
├── _schema.py         # SCHEMA_VERSION="1"; the 5-field label; provenance vocab (DISTINCT)
├── _corpus.py         # data: atomic-append JSONL read/write + coverage accounting (the corpus)
├── _detect.py         # logic: Tier-1 + Tier-2 detectors (incl. example-fill, reads the salience set)
└── _oracle.py         # assembly: label + detector outputs → verdict-pair; emits provenance
```

*(Pattern reference, not literal rewrite — `comprehension/_schema.py` is the closest analog: versioned,
frozenset-enum vocab, `validate_*_record`. Reuse the SHAPE; the vocabularies are net-new.)*

---

## Steps

### Step 0 — Re-derive the salience surface **[DONE — gating precondition]**
Deliverable: `TF.3a-SALIENCE-SURFACE.md` (committed). Re-swept all 5 demo kinds × 6 tool files; added the
few-shot blocks D3 missed; produced the machine-consumable value-set (§D) + compound patterns + FP-surface note
(§E). **This unblocks Steps 4–5.** Verify: the detector value-set in §D is the authority `_detect.py` imports —
not D3.

### Step 1 — Package scaffold + label schema (Q1/Q5)
- Create the package + `_schema.py`. `SCHEMA_VERSION="1"`; **5-field label** per record:
  `(input, expected_graph, expected_params, expected_verdict_pair, world_state)` + `provenance` per param.
  - `expected_graph`: step-text list (chain-step shape, no IR — TF.1 §1).
  - `expected_params`: context-resolved refs marked `unresolved-pending-dispatch`, NOT a concrete value
    (TF.1 §2) — the validator must *accept* unresolved where the contract says dispatch resolves.
  - `expected_verdict_pair`: `translation∈{pass,fail} × substrate∈{pass,gap}` (TF.2 §2) — **required**; this is
    the locked floor (Q1). Honest-decline = `(pass, gap)`.
  - `world_state`: the desktop/open-state the input was issued against — **required for contextual labels**,
    nullable for text-sufficient ones (Q1 5th field; "this sequence" is unscorable without it).
  - `provenance` vocab `{grounded-from-intent, from-context, filled-from-example, unresolved}` — **distinct
    frozenset; MUST NOT reuse** comprehension's `{loved,hated,…}` or corpus's divergence vocab (Q5 three-vocab).
- **Verify:** `validate_label_record` rejects a missing verdict-pair; accepts an unresolved context-param;
  rejects a provenance value borrowed from the other two instruments' vocab. Unit test in `tests/`.

### Step 2 — Corpus data layer (`_corpus.py`) + coverage accounting (Q2)
- Atomic-append JSONL writer/reader (mirror `comprehension/_capture.py` topology); date-partitioned under
  `~/.forge-bridge/translation_oracle/`.
- **Coverage accounting [N]:** a function reporting, per the adequacy matrix, whether every **verdict-pair
  cell × translation class × multi-tag pattern × D-series defect** has its required instances —
  **Tier-2 ≥2 per validated cell** (tune + holdout), **Tier-1 ≥1**. Output is a coverage report, not a count.
- **Verify:** coverage report flags an under-covered cell; a deliberately-thin fixture shows RED.

### Step 3 — Seed + author the corpus (Q2)
- **Seed:** the 32 well-formed comprehension traces (drop the 4 malformed) → relabel fresh on the
  translation-correctness axis (discard their legibility `verdict`). Aborts labeled by the decline-vs-misroute
  discriminator (TF.2 §2.1) — a correct abort = `(pass, gap)`.
- **Augment:** the D-series/E2E-01 defects (#1/#2/#3 — pre-diagnosed, cheapest high-value labels).
- **Author to coverage:** write inputs until Step 2's report is GREEN — **with `world_state`** for contextual
  (§3.5) cases (the dogfood almost certainly never exercised them).
- **Verify:** coverage report GREEN across the full adequacy matrix; log what was authored vs seeded
  (no silent gaps).

### Step 4 — Detectors (`_detect.py`) (TF.2 §5 two-tier)
- **Tier-1** (substrate-observable): routing/shadow (`tool_forced` marker), extraction (key-in-text-absent-
  from-params), contextual (state-ref + `desktop` unavailable), substrate-gap (registry read),
  decline-vs-misroute (`:407` fired vs dispatch).
- **Tier-2** (ground-truth): grounding/example-fill (**reads the Step-0 §D value-set + compound patterns**),
  entity-resolution (resolved ≠ labeled canonical), routing/wrong-selection (selected ≠ labeled tool).
- **Verify:** each detector runs against the corpus and emits a class tag + confidence.

### Step 5 — Validate the oracle (Q3) + the example-fill FP rate (Q4)
- **Tier-1 — positive+negative unit pair per detector** (logic-bug surface): fires on the grounded defect
  instance, silent on a clean negative. (NOT a statistical holdout — wrong tool for logic bugs.)
- **Tier-2 — held-out slice + pre-declared agreement threshold** (ground-truth surface); the held-out instance
  comes from Step 2's ≥2-per-cell provisioning. Threshold may be per-class (open: Tier-2 classes differ).
- **Example-fill FP rate:** hand-label corpus values matching the Step-0 §D set as `lifted` vs
  `legitimately-equal` (§E lists the prone literals — `30sec_21`, `noise`, `tst`, `ABC`); report the rate
  **against the complete surface**. **Gate:** grounding-class scoring is not released to 3b until this number
  exists.
- **Verify:** validation report shows Tier-1 pairs pass, Tier-2 meets threshold, FP rate recorded.

### Step 6 — Oracle assembly (`_oracle.py`)
- Compose label + detector outputs → a **verdict-pair** per corpus input, with per-param provenance attached.
  No ranking, no frequency aggregation (that's 3b).
- **Verify:** oracle emits a well-formed verdict-pair + provenance for every corpus record; round-trips through
  `_schema.validate_*`.

---

## Goal-backward verification (does 3a deliver a *trustworthy* instrument?)
1. Every label carries a verdict-pair → the oracle can score honest-decline as success (not just right/wrong). ✓ Step 1
2. Coverage is complete, not just counted → no cell silently unmeasured. ✓ Steps 2–3
3. Tier-1 proven to fail-when-it-should; Tier-2 reproduces held-out labels within threshold → detectors trusted. ✓ Step 5
4. Example-fill measured against the **complete** surface → the FP rate is the real number. ✓ Steps 0 + 5
5. One package, three distinct vocabularies → no schema coupling regression. ✓ Steps 1, 5

## Out of scope (explicitly)
The 3b run, verdict aggregation, frequency counting, defect ranking, and **all Phase-4 fixes** (example-strip,
PR20/extraction, desktop-wiring). 3a ships the instrument; 3b is the first measurement.

## Commit cadence
Atomic per step (Step 0 already committed). Each step: code + its verification test in one commit; coverage and
validation reports committed as artifacts. `pytest tests/translation_oracle/` green before close.
