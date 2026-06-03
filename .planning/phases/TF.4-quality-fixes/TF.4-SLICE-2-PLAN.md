# TF.4 (Quality Fixes) — Slice #2 PLAN: space-mangle / entity-resolution value fidelity

**Status:** SHIPPED S1–S3 (`a7b26c2`/`e9aefac`/`bc15158`, 766 green, verified). **S4 PULLED → TF.3b** — grounding the consumer (`_corpus.py:177`) showed `expected_well_formed` is a well-formedness-tier COUNT field, not a per-graph nit; the shared authored label is right-for-frozen/wrong-for-postgate across 3 fields → architecturally unfixable in one slice, folded into the TF.3b shared-label item. S4 below is retained as the as-planned record; **do not execute it.** S1/S3/E2 as written; S2 ran on postgate.
**Date:** 2026-06-03. **Base:** `main @ b6c3148` (Slice #2 framing committed).
**Framing:** `TF.4-SLICE-2-FRAMING.md`. **Spine (room-blessed):** measurement BUILT + prevention ATTEMPTED + guarantee DEFERRED.

This slice's deliverable solidity is inverted from Slice #1: the **headline is the detector** (deterministic, model-free, the reusable TF.3b entity-resolution instrument); the **prompt clause is the speculative add-on** (cheap, unproven, ship-now). Model-free end-to-end — reads the frozen-and-postgate corpora; no Ollama/daemon/Flame.

---

## The load-bearing grounding finding — the bar's home is POSTGATE, not frozen

Entity value-fidelity is **downstream of the serialization gate**: you cannot observe the inner (entity) defect on a corpus where the outer (serialization) defect is unrepaired. Verified across both corpora for the 4 cases (authored id → corpus IDX):

| ID | IDX | FROZEN `observed_graph` | POSTGATE `observed_graph` (mangle exposed) |
|----|-----|----|----|
| L2 | 5  | `['flame_preview_start_frames', '{"params":{"sequence_name":"30sec_21"}}']` — **detached, wf=False** | `flame_preview_start_frames sequence_name=30sec_21` |
| L7 | 7  | `['flame_rename_shots', '{"params":{"sequence_name":"30sec_21","prefix":"noise"}}']` — **detached, wf=False** | `flame_rename_shots sequence_name=30sec_21 prefix=noise` |
| L3 | 10 | `['forge_list_shots', 'forge_get_shot']` — **no value emitted** | `forge_list_shots project_id=30sec_edit_21 status=pending` |
| L4 | 11 | `['forge_list_shots', 'forge_get_shot']` — **no value emitted** | `forge_list_shots project_id=30sec_edit_21 …` |

**The frozen corpus is structurally incapable of hosting this bar** — 5/7 bury the value in a malformed blob (the serialization gate fires first), 10/11 never emitted the value pre-Slice-1. Postgate is the **first corpus** where the gate is clear enough to expose the entity defect as an extractable param. The detector on postgate flags all 4; on frozen it would flag ≤2. **This is the well-formedness-gates-content tiering showing up in the data — a vindication of the tier, and exactly the TF.3a discipline: do not measure a phenomenon in a corpus that cannot expose it.**

L3/L4 also prove **Flip 3**: the postgate value relocated into `project_id` — a `sequence_name`-keyed comparator reaches 0 of these 2. The detector must be **param-location-blind**.

---

## The detector — signature + invariant (corpus-independent)

```python
def detect_entity_value_fidelity(
    observed_graph: list,
    expected_params: dict,
) -> tuple[bool, Optional[str]]:
    """Return (faithful, reason). Faithful iff EVERY expected entity value
    appears VERBATIM as a parameter value somewhere in the emitted graph —
    param-location-blind (any step, any key), tag-blind, exact (no fuzzy,
    no similarity, no correction). Label-gated: the canonical comes from
    expected_params (authored ground truth), never from the model.
    reason names the first canonical value absent from the graph."""
```

- **Invariant:** for each `value` in `expected_params.values()`, `value` must appear as a **complete extracted parameter value** in some `observed_graph` step (split each step into `key=value` tokens, strip surrounding quotes, exact-equality compare). NOT a raw whole-graph substring search — that false-passes on `canonical ⊂ longer-correct-value`.
- **Param-location-blind:** ignores which key/tool carries the value → survives the routing confound (value relocated to `project_id`). This is *why* it reaches all 4.
- **Orthogonal to routing by construction:** right entity value under a wrong tool/key still passes value-fidelity (routing is the parked sibling's concern). Isolation enforced *in the detector*, not just the labels.
- **Reusable instrument:** iterating all `expected_params` (not just `sequence_name`) makes this the general TF.3b entity-resolution detector; the 4-case bar exercises the `sequence_name` subset.

---

## Steps (model-free; `pytest tests/translation_oracle` green before close)

### Step 1 — `detect_entity_value_fidelity()` + unit pos/neg pairs (substrate primitive, isolated) — UNCHANGED
Add the pure fn to `_detect.py` beside `compute_well_formed` (same return shape). Unit pairs in `tests/translation_oracle/test_detect.py` — **synthetic, corpus-independent**:
- **positive (faithful):** `['flame_rename_shots sequence_name="30sec_21" prefix="tv"']` vs `{"sequence_name":"30sec_21","prefix":"tv"}` → `(True, None)`.
- **negative — conflation:** `['flame_rename_shots sequence_name=30sec_21 prefix=noise']` vs `{"sequence_name":"30sec_edit 21","prefix":"noise"}` → `(False, "30sec_edit 21")`.
- **negative — underscore + routing relocation:** `['forge_list_shots project_id=30sec_edit_21 status=pending']` vs `{"sequence_name":"30sec_edit 21"}` → `(False, "30sec_edit 21")` (param-blind proof — value absent under any key).
- **guard — substring false-pass:** canonical `30sec` must NOT pass against emitted value `30sec_edit_21` (extracted-value equality, not text-contains).
- **routing-orthogonality:** right value under wrong tool/key → `(True, None)`.
No wiring; no `__all__` change (E2 → internal).

### Step 2 — The deterministic bar (Metric A — goal-backward gate) — REPOINTED frozen→POSTGATE
Mirror `test_tf4_well_formedness_bar.py`. Read the **postgate** corpus (`reference/postgate/cases.jsonl`) — the bar's structurally-correct home (see the grounding finding). Select the 4 value-fidelity cases by authored id {L2, L7, L3, L4} (or `expected_params.sequence_name == "30sec_edit 21"`), replay each `(observed_graph, expected_params)` through the production `detect_entity_value_fidelity`. Assert: **all 4 flag `faithful=False`**, `len(selected)==4` (count lock — [[feedback-counts-are-archaeology-grade]]), and a known-correct case (L6 / IDX 6, `30sec_21` faithful) → `(True, None)`. Model-free: reads the postgate JSONL, runs the detector in-memory; the corpus is never mutated. Reads `expected_params` (canonical, correct independent of the S4 nit) — so the bar does **not** depend on S4.

### Step 3 — Prong A: compile-prompt literal-preservation clause (prevention) — UNCHANGED
Add a clause to `_default_compile_system_prompt` (`router.py:426`): a space-bearing entity name is a single quoted literal — preserve the space exactly, never normalize to underscores, never substitute a near-looking known entity. Smoke assertion only (presence), **no deterministic gate** (Metric B is ecological; ship unproven — no N≥3/control gate per the honest ceiling).

### Step 4 — Fix the frozen `expected_well_formed` nit (authored-expectation correction only) — NARROWED
Edit `_authored.py` (the sanctioned label locus — never hand-edit JSONL). **Single-field, observation-preserving:** L2 and L7 carry `expected_well_formed=False`, but a correct rename/segments graph IS well-formed — the False was a category error (it recorded the then-observed serialization malformation into the *expected* field). Fix **only** `expected_well_formed: False→True` for L2 and L7.
- This makes them **clean serialization cases**: expected well-formed, observed (frozen) malformed = serialization translation failure. Consistent in *both* corpora (postgate observed is also well-formed → expected matches).
- **Do NOT flip `defect_ref` or `expected_classes` on L2/L7.** The frozen observation is genuinely `detached_args` — relabeling it entity-resolution would falsify an accurate observation and violate the well-formedness-gates-content doctrine (content classes are uneval-able on a malformed graph). The entity-resolution manifestation of these inputs already lives in the **postgate** corpus (canonical `expected_params` + mangle-exposed observed) — no relabel builds it; it's there.

Rebuild every corpus dir offline (no Ollama):
```
python -m forge_bridge.translation_oracle.run_captures --reuse-observed
python -m forge_bridge.translation_oracle.run_captures --reuse-observed --postgate
```
Verify `pytest tests/translation_oracle` green. Frozen `observed` side unchanged (re-paired; `well_formed` recomputed from the same frozen `observed_graph`).

---

## Escalations — both resolved by the grounding

**E1 — RESOLVED (narrowed).** The framing's "relabel `expected_classes`" and my draft's 3-field relabel are **withdrawn**. Grounding showed the frozen 5/7 observations are accurate serialization failures, not stale; relabeling them entity-resolution falsifies the observation and collapses the tier. Only the `expected_well_formed` authored nit is fixed (S4). `defect_ref` staying `serialization` on the shared label is *correct for frozen* and *wrong for postgate* — a single authored label spanning two manifestations. **That shared-label-across-corpora tension is a TF.3b concern** (it needs corpus-aware or per-manifestation defect_ref to count entity-resolution frequency); flagged as a forward-pointer, **not** solved here.

**E2 — RESOLVED (internal, oracle `__all__` stays 18).** The sibling asymmetry is *consumer-existence*, not inconsistency: `compute_well_formed` is exported because production capture consumes it (computes the `well_formed` field on every trace); the entity detector has no production consumer this slice — only the test bar, which imports the private `_detect` symbol directly (as the Slice-1 bar imported `normalize_chain_shape` without an export). Export when TF.3b/capture actually computes an entity-fidelity field ([[feedback-substrate-before-consumer-landing]]). `forge_bridge.__all__`=19 untouched.

## Goal-backward verification
Goal — *a deterministic, reusable measurement that flags entity value-fidelity failure across the routing confound* — achieved iff S2's bar flags all 4 postgate cases through the *production* detector (not a test-local reimplementation), count-locked at 4. Prong A is prevention (presence-asserted, efficacy explicitly unproven). S4 is an authored-expectation correction, not a gate on the goal.

## Out of scope (parked, named)
TF.3b shared-label/defect_ref-per-manifestation architecture; live membership-validity / honest-decline (desktop-wiring slice, absorbs IDX 8 + 13); routing repair (routing sibling); fuzzy/nearest-match correction (architecturally prohibited — exact only); Metric B ecological emission-rate + `compile_raw` (post-gate pass, needs live stack).

## Commit cadence
S1 (detector + synthetic units) · S2 (postgate bar) · S3 (prompt clause) · S4 (`expected_well_formed` nit + offline rebuild) — atomic per step. E1/E2 resolved (no open forks).
