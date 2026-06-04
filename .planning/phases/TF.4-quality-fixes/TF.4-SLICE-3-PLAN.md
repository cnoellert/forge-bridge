# TF.4 (Quality Fixes) — Slice #3 PLAN: trailing-empty-segment well-formedness salvage

**Status:** Orch draft, grounded against `router.py` (`normalize_chain_shape`, `_validate_chain_shape`, `_parse_compile_output`, `_top_level_chain_segments`). Pending room redline.
**Date:** 2026-06-03. **Base:** `main @ 639e8b1` (Slice #3 framing of-record).
**Framing:** `TF.4-SLICE-3-FRAMING.md`. **Conformance ruling (binding):** malformed structure MUST survive parsing to be observed by `normalize_chain_shape`; no silent parse-level repair.

A2 loosen-then-normalize, Slice-#1 family. Recoverable tier → **carries a deterministic guarantee** (the empty segment is content-free; repair removes zero semantic content).

---

## Grounded design (the mechanism is cleaner than feared)

The three stages, verified: `_top_level_chain_segments` **preserves** empties (`'forge_list_projects ->' → ['forge_list_projects','']`) → `parse_chain` **drops** them → `normalize_chain_shape` salvages what it sees. **Key grounding find:** `_validate_chain_shape` (called at `normalize_chain_shape:569`) **already re-raises on any empty step** (`:520-521`, `empty step at index N`). So the mid-empty re-raise (Sharpening 2) is **already present** — the salvage extension only needs to pop *trailing* empties *before* `_validate_chain_shape` runs; any surviving *mid-chain* empty raises automatically. Guard-moved-not-removed is satisfied by the existing validator.

**The normalize extension (exact):** after the existing detached-args reattach loop produces `normalized`, before `_validate_chain_shape(normalized)`:
```python
    # NEW: drop a TRAILING empty segment observably (content-free; zero semantic loss).
    if normalized and not normalized[-1]:
        while normalized and not normalized[-1]:
            normalized.pop()
        salvage_record = {"salvage_applied": True, "original_reason": "trailing_empty_segment"}
    _validate_chain_shape(normalized)   # SACRED: a surviving MID-chain empty re-raises here
    return normalized, salvage_record
```
This satisfies the 4-case matrix by construction: `['fp','']`→pop→`['fp']`+salvage; `['a','','b']`→no trailing pop→`_validate` raises mid-empty; `['a','b']`→unchanged, no salvage; malformed residual→`_validate` raises.

**Multi-salvage attribution (DT + Creative — make it intentional, never a silent overwrite):** a chain triggering BOTH detached-args reattach AND a trailing-empty pop (e.g. `flame_rename_shots -> {…} ->`) must record **both** reasons, attribution-complete — the trailing-empty reason must NOT overwrite `detached_args` (silent overwrite is the same observability failure the milestone keeps eliminating). Disposition: **accumulate reasons in occurrence order** (detached-args reattach in the loop, then trailing-pop) → `original_reason` carries all of them. **Lean (minimal, no schema change, back-compat):** single-salvage keeps its exact string (`"detached_args"` / `"trailing_empty_segment"`); co-occurrence joins in order (`"detached_args+trailing_empty_segment"`). *Alternative if a structured value is wanted:* an additive `salvage_reasons: list` field (SCHEMA "1", mirroring `compile_raw`). Execute picks the least-invasive that's attribution-complete; confirm no consumer exact-matches `original_reason` as a sole literal on the co-occurrence path (Slice-#1 bar matches `"detached_args"` only on single-salvage cases — unaffected).

**The loosen (Sharpening 1 — source from segments, NOT `parse_chain`):** the text branch of `_parse_compile_output` (`:601-609`) currently raises guard-1 on any empty segment (`:602-607`) then sources from `parse_chain` (which re-drops empties). Replace with: **source steps directly from `_top_level_chain_segments` (empties preserved)** — it splits on `->` at depth-0 identically to `parse_chain`, minus the empty-drop. Do **NOT** modify `parse_chain` (shared by other callers — blast-radius this slice refuses). Guard-2 (`:613-614`, the post-parse empty re-raise) is the moved guard: its empty-check is now owned by `_validate_chain_shape` inside normalize — keep `if not steps: raise CompileUnresolvableIntent` (`:611-612`, all-empty), drop the `step.strip()` empty-raise so empties reach normalize.

---

## Steps (`pytest tests/llm tests/console tests/translation_oracle` green before close)

### Step 1 — extend `normalize_chain_shape` (trailing-empty salvage) + unit pos/neg pairs (isolated, no wiring)
`router.py` — add the trailing-pop block above. Unit pairs in `tests/llm/` = **the 4-case conformance matrix**:
- positive: `['forge_list_projects','']` → `(['forge_list_projects'], {'salvage_applied':True,'original_reason':'trailing_empty_segment'})`.
- negative — mid-chain empty: `['a_tool','','b_tool']` → `pytest.raises(CompileInvalidChainShape)` (via `_validate_chain_shape`).
- negative — already-clean: `['a_tool','b_tool']` → `(['a_tool','b_tool'], None)` (no false salvage).
- negative — malformed residual (bare-args / non-tool) still raises (existing behavior preserved).
- co-existence sanity: a detached-args case still salvages `detached_args` (Slice #1 regression).
- **multi-salvage attribution:** a chain with BOTH detached-args AND a trailing empty → salvage record carries BOTH reasons in order (attribution-complete, no overwrite). Creative close-grades this (#4).

### Step 2 — loosen `_parse_compile_output` text branch (preserve empties → normalize observes) + SACRED integration
`router.py` `:601-614` per the loosen above (source from `_top_level_chain_segments`; move guard-2 empty-check into normalize; `parse_chain` untouched). **Caller audit — RESOLVED safe (DT + Creative), the slice's last blast-radius question:** *Internal:* `compile_intent` has exactly ONE consumer (`_chat_compile.py:175`) and `normalize_chain_shape` runs on the very next line (`:180`); every other `compile_intent` reference is an exception-message string or the recursion guard — no path reaches preserved-empty steps before normalize. Zero internal blast radius. *External:* the public `compile_intent` contract was **already** weakened at Slice #1's A2 (JSON branch serializes bare-args to `{…}` rather than raising) → it is already "parser-faithful, normalize-pending," not "clean steps." #3 extends that already-crossed boundary to the text branch (empties); not a new category.
Integration tests (`tests/console/` / `tests/llm/`): `'forge_list_projects ->'` through the production compile path → `regime` non-error, `salvage_applied=True`, `original_reason='trailing_empty_segment'`, graph `['forge_list_projects']`. **SACRED:** `'a -> -> b'`-shaped (mid-empty) → still `compile_error` / `CompileInvalidChainShape`.

### Step 3 — deterministic bar (Metric A — goal-backward gate, model-free)
`tests/translation_oracle/` — replay the **3 frozen slice2 raws** (`reference/postgate-slice2-run{1,2,3}`, all `compile_raw='forge_list_projects ->'`) through the production parse+normalize → assert all 3 flip to salvaged/well-formed with `trailing_empty_segment`. Plus the 4-case matrix through the production functions (not a test-local reimpl). No Ollama/stack; the frozen corpora are read-only, never mutated.

---

## Goal-backward verification
Achieved iff: (1) the 4-case conformance matrix passes through the *production* `normalize_chain_shape` + loosened parser (trailing→salvage·mid→raise·clean→unchanged·malformed→raise); (2) the 3 frozen slice2 raws replay to salvaged/observable; (3) `salvage_applied`/`trailing_empty_segment` reach `ObservedTrace` via the existing Slice-#1 channel (no silent repair); (4) the SACRED mid-empty re-raise holds at unit + integration. The guarantee claim — repair removes zero semantic content — is proven by the matrix (clean & malformed unchanged/rejected; only the content-free trailing token dropped).

## Out of scope (parked, named)
Mid-chain / non-terminal empties (documented future extension — they re-raise loudly, never silent-drop); a prompt-clause prevention (optional, known-weak from (A)); `non_tool_step` (#4); `parse_chain` drop-behavior change (blast-radius refused); detached-args + trailing-empty co-occurrence precedence (unobserved).

## Constraints (binding)
`forge_bridge.__all__` = **19**; `translation_oracle.__all__` = **18** (no new symbol — reuses the Slice-#1 salvage channel); `SCHEMA_VERSION` = "1" (`trailing_empty_segment` is a reason *value*); no new external libs. Frozen `reference/cases.jsonl` + all `reference/postgate*` dirs **never mutated**.

## Commit cadence
S1 (normalize extension + unit matrix) — isolated · S2 (parser loosen + caller-audit + SACRED integration) · S3 (model-free bar). Atomic per step.
