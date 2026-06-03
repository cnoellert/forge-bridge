# TF.4 (Quality Fixes) — Slice #1 PLAN (rev 2 — DT + Creative ratified)

**Milestone:** v1.13 Translation Fidelity, the first quality-fix slice (first v1.13 touch of **runtime** code).
**Settles:** `TF.4-FRAMING.md` (Orch → Creative → DT → Creative, converged).
**Goal:** the substrate no longer hands malformed graphs to dispatch for the **detached-args** defect. Deterministically proven (model-free), Prong B load-bearing. Content re-ranking held until the gate clears.
**North-star:** *prove the fix without a fresh model run.*

---

## Two load-bearing design choices — ratified rev 2 (DT + Creative)

The framing settled *what* and *why*; grounding the live parser + `CompileBranchOutcome` surfaced two *how* decisions that revise the framing. **Both blessed in rev 2.** DT: *"A2 is the correct reinterpretation of pre-pass — and the better design; `compile_raw` deferral is grounded-resolved."* The recurring milestone pattern (grounding the live code improved the reviewer's own proposal — A1 was an implementation *shape*, A2 is the *property* A1 was reaching for) is banked in the cursor's methodology pool.

**1. Architecture: "loosen-the-raise + post-parse normalize" (A2), not literal pre-parse normalize (A1).**
DT seam #2 said the pass must fire *before the raise* so the JSON-list manifestation isn't lost. Grounding shows a cleaner mechanism that serves the same requirement:
- **Loosen `_structured_compile_step_text` (`router.py:490-493`)** so a bare-args dict is *serialized to a `{…}` step-string* instead of raising `CompileInvalidChainShape`. The parser stops *destroying* the malformed evidence → the raise manifestation now reaches a step-list, in the **same shape** the text-branch already produces (`["flame_rename_shots", "{…}"]` — empirically confirmed in the frozen corpus).
- **`normalize_chain_shape(steps)` then runs post-parse**, on that unified step-string shape, inside `run_compile_branch` (before `apply_executor_routing`, `:183`).

Why A2 over A1: (a) the deterministic bar replays the *frozen* `observed_graph` (step-strings) through the **identical** production function — no second entrypoint, no shape divergence; (b) `compile_intent` / `_parse_compile_output` keep their `-> list[str]` contract — no return-type churn through production callers; (c) the loosening is itself a faithfulness fix (the parser preserves malformation as data rather than collapsing it to an opaque `compile_error`). **Error semantics preserved:** `normalize_chain_shape` *re-raises* `CompileInvalidChainShape` for residual unrepairable malformed steps, so genuinely-broken output still resolves to `compile_error` — the guard moves into the named pass, it isn't removed. **DT: bless or reject the reinterpretation of "pre-pass."**

**2. `compile_raw` deferred to the post-gate re-capture pass (revises the framing's "this slice").**
The framing put `compile_raw` in this slice. Grounding revises that: (a) surfacing raw from `compile_intent` is the one genuinely invasive change (raw is a local there; the `-> list[str]` contract discards it); (b) **nothing in Slice #1 populates or tests it** — Slice #1 has *no live capture* (all proof is deterministic/synthetic); (c) the first capture that would benefit is the post-gate re-capture, so landing it here vs. there yields *identical* coverage. Substrate-before-consumer ⇒ land `compile_raw` (field + threading) with its first consumer, the post-gate pass, grounded against a live capture. The raise-shape's Slice-1 correctness is fully covered by the synthetic fixture without it.

**`salvage_applied` + `original_reason` stay in Slice #1** — they are *not* deferrable: Step 2 puts `normalize_chain_shape` on the **live production compile path**, so the salvage must be observable from that instant or we ship a live-but-invisible salvage (the exact "erases the evidence" failure DT named). The emission lands with the wiring (S2 → `CompileBranchOutcome`), the instrument mapping lands right behind it (S3).

**Constraints (binding, inherited):** public `forge_bridge.__all__` stays **19**; `translation_oracle.__all__` (currently **18**) absorbs nothing new this slice; no new external libraries. The frozen corpus (`reference/cases.jsonl`) is **never mutated** — the bar reads it and runs normalize in-memory.

---

## The fix surface (grounded)

```
compile prompt        router.py:426   _default_compile_system_prompt   (Prong A — prevention)
compile-output parse  router.py:504   _parse_compile_output            (loosen the JSON-list raise)
                      router.py:490   _structured_compile_step_text    (serialize-not-raise)
the salvage pass      router.py (new) normalize_chain_shape(steps)     (Prong B — load-bearing)
compile branch        _chat_compile.py:149  run_compile_branch         (call normalize @ :183; thread salvage)
outcome envelope      _chat_compile.py:23   CompileBranchOutcome       (+salvage_applied, +salvage_reason)
capture map           _capture.py     observed_trace_from_compile_outcome  (map salvage → trace)
schema fields         _schema.py:79   _OBSERVED_MARKER_TYPES           (+salvage_applied, +original_reason)
well-formedness gate  _detect.py:18   compute_well_formed              (unchanged — the judge)
deterministic bar     tests/translation_oracle/  (Metric A — corpus replay + synthetic)
```

### `normalize_chain_shape` signature + invariant
```python
def normalize_chain_shape(steps: list[str]) -> tuple[list[str], dict | None]:
    """Reattach a detached bare-args step to its immediately-preceding tool-only step.

    Invariant (binding, Creative): reattach arguments ALREADY present in the emitted
    chain; never synthesize, merge, infer, or reorder. Repair only when exactly one
    attachment interpretation exists.

    Returns (normalized_steps, salvage_record | None):
      salvage_record = {"salvage_applied": True, "original_reason": "detached_args"} when it fired, else None.
    Residual unrepairable malformed steps -> raise CompileInvalidChainShape (preserves compile_error).
    """
```
Reattach **iff**: a tool-name-only step (no args) is **immediately** followed by a step whose first non-space char is `{` (a bare args object). Everything else is left for the residual check.

---

## Steps

### Step 1 — `normalize_chain_shape()` + unit pos/neg pairs (substrate primitive, isolated)
- New module-level helper in `router.py` (sibling to `_parse_compile_output` et al. — preserve topology, no new file).
- **No production wiring yet** — the pure function, proven standalone on synthetic step-lists.
- **Verify (`tests/llm/`), positive + negative discipline (mirrors the Tier-1 detector pairs):**
  - **positive:** `["flame_rename_shots", '{"params": {…}}']` → `["flame_rename_shots …"]`, record fired.
  - **negative — orphan args, no preceding tool** → unchanged, residual `CompileInvalidChainShape`, no fabricated attachment.
  - **negative — preceding tool already has args** → unchanged.
  - **negative — two args objects after one tool (ambiguous target)** → unchanged.
  - **negative — non-tool prose step** → unchanged (that is Slice #2's defect, not detached-args).
  - **raise-shape input (synthetic):** the step-list the loosened JSON-list branch *will* produce → repaired (defect-family coverage for the corpus's one unreplayable case).

### Step 2 — Wire into the live compile path + emit observability (atomic)
- **Loosen** `_structured_compile_step_text` (`router.py:490-493`): bare-args dict with no `tool_name`/`step_text` → return `json.dumps(item)` as a `{…}` step-string instead of raising.
- **Call** `steps, salvage = normalize_chain_shape(steps)` in `run_compile_branch` immediately after `compile_intent` returns, **before** `apply_executor_routing` (`_chat_compile.py:183`).
- **Thread** `salvage_applied: bool = False` + `salvage_reason: Optional[str] = None` onto `CompileBranchOutcome` (defaults protect the `compile_error` construction at `:175`; only the success path sets them).
- **Verify (`tests/llm/` + `tests/console/`):** the JSON-list bare-args input no longer raises → produces the `{…}` step-string → normalizes → well-formed graph (this test owns the **JSON-list-bare-dict** manifestation: it proves the loosen produces the convergent shape from the raise-shape's pre-loosen form); `CompileBranchOutcome.salvage_applied` True on a repaired compile, False on a clean one.
- **The residual-re-raise test is SACRED, non-optional at close (DT + Creative keystone):** a genuinely unrepairable malformed compile still yields `regime="compile_error"`. This is the single test that proves the guard *moved into `normalize_chain_shape`* rather than *vanished* — A2's entire safety story ("we moved the guard, we did not remove it") rests on it. If it ever disappears, A2's correctness argument collapses.

### Step 3 — ObservedTrace observability fields + capture mapping
- `_schema.py`: add `"salvage_applied": bool` and `"original_reason": (str, type(None))` to `_OBSERVED_MARKER_TYPES`. **SCHEMA_VERSION stays `"1"`** — additive, type-if-present (the validator only checks `if field in observed`), so existing `cases.jsonl` rows validate untouched. (`compile_raw` deliberately **not** added — design choice #2.)
- `_capture.observed_trace_from_compile_outcome`: map `outcome.salvage_applied` → trace `salvage_applied`; `outcome.salvage_reason` → `original_reason`.
- **Verify (`tests/translation_oracle/`):** an existing field-less corpus row still validates (backward-compat); a `CompileBranchOutcome` with salvage maps onto a trace that carries the two fields and validates.

### Step 4 — Prong A: compile-prompt single-step grammar (prevention)
- Add to `_default_compile_system_prompt` (`router.py:426`) a clause specifying that **a step's arguments travel inline with its tool name** (`tool_name arg=value …`); an args object is never its own step.
- **No deterministic effect-gate** — by design. Prong A's success is **Metric B** (emission-frequency drop), measured ecologically at the post-gate re-capture, never the bar for this slice.
- **Verify:** smoke assertion that the rendered prompt contains the grammar clause (presence, not effect).

### Step 5 — The deterministic bar (Metric A — the goal-backward gate)
- **`tests/translation_oracle/`** — read `reference/cases.jsonl`, select the **4** rows with `well_formed_reason == "detached_args"`, run `normalize_chain_shape(observed_graph)` on each, and assert: graph becomes well-formed under `compute_well_formed`, salvage record fired with `original_reason="detached_args"`, resulting steps structurally valid. **No Ollama / daemon / Flame.**
- **Defect-family completeness by ENUMERATION, not arithmetic (DT + Creative).** The close-statement is *not* "4 corpus + 1 synthetic = family complete." It is the three **input manifestations**, each asserted covered:
  - **text-`->`** (`flame_rename_shots -> {…}`) — frozen corpus pass-through rows, replayed (S5).
  - **JSON-list-of-strings** (`["flame_rename_shots", "{…}"]`) — frozen corpus + S1 unit.
  - **JSON-list-bare-dict** (`["flame_rename_shots", {…}]`, the pre-loosen raise-shape) — S2 loosen-test (produces the `{…}` step-string) → S5 normalize (repairs the convergent shape).
  S2 + S5 *jointly* span the family; the assertion is enumerated-and-covered (`[[feedback-grep-c-completion-invariant]]`), never a count. The synthetic fixture's target shape mirrors a production-observed convergent form (`[[feedback-fixture-shape-mirrors-production]]`), so it is not a hand-guess.

---

## Goal-backward verification
1. Reattaches the unambiguous detached-args case; leaves orphan / already-args / ambiguous / prose untouched → invariant honored, no fabricated graphs. ✓ S1
2. All **three input manifestations** enumerated-and-covered — text-`->`, JSON-list-of-strings, JSON-list-bare-dict — jointly by S2 (loosen) + S5 (replay). ✓ S2, S5
3. `salvage_applied` / `original_reason` reach `CompileBranchOutcome` and `ObservedTrace` → Prong A vs Prong B stay distinguishable the moment salvage goes live. ✓ S2–S3
4. **Metric A proven model-free:** 4 frozen detached-args flip + synthetic raise covered, no live run. ✓ S5
5. Unrepairable malformed output still resolves to `compile_error` → error semantics preserved, not removed. ✓ S2
6. Prong A ships without a deterministic gate (Metric B is ecological) → no per-layer success laundering. ✓ S4
7. Public `__all__` 19; corpus unmutated; no new libs. ✓ all

## Out of scope
- **Slice #2** — prose / non-tool-step normalization (the 1 `non_tool_step` corpus case); its own ambiguity surface.
- **The post-gate re-capture pass** — Metric B (emission-rate drop), the #2–#5 content re-rank, the L8 grounding-on-contextual re-judgement, **and `compile_raw` (field + threading)**. Needs the live stack (Ollama + Flame + daemon).
- Space-mangling (entity-resolution, Phase-4 defect #2); (c) honest-decline restoration.

## Commit cadence
Atomic per step; code + verification test in one commit. `pytest tests/llm tests/console tests/translation_oracle` green before close. Corpus not rebuilt this slice (no live capture); `run_captures` re-run is the post-gate pass.
