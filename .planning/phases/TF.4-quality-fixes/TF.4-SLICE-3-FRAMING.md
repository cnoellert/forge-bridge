# TF.4 Quality Fixes — Slice #3 Framing: trailing-empty-segment well-formedness salvage

**Status:** Orch draft. Scope **pre-converged by the room** (DT + Creative, point-for-point) off the (A) post-gate #2 raw; this framing assembles their agreed scope + one grounded design note. Light redline expected.
**Date:** 2026-06-03. **Base:** `main @ 6eaca91` (Slice #2 + (A) post-gate #2 closed).
**Scope of this slice:** the **trailing-terminal-empty-segment** invalid-chain-shape defect only — raw-scoped, stable 3/3. NOT mid-chain empties (documented future extension), NOT `non_tool_step` (different raw shape).

Ranked **#3 by live measurement** ((A) post-gate #2, `TF.4-POSTGATE2-FINDINGS.md`), and **scoped from observation, not prediction** — the `compile_raw` instrument (S1) made the shape visible, and DT's read-before-scoping gate caught a misclassification (below).

---

## The defect (grounded, raw-anchored)

`list the projects` reproduces 3/3 as `CompileInvalidChainShape`, empty graph. The captured raw is stable:

```
compile_raw = "forge_list_projects ->"
```

The model **selects the correct capability, emits the correct tool name, enters chain syntax — then emits one trailing `->` with nothing after it.** Mechanism (verified):
- `_top_level_chain_segments("forge_list_projects ->")` → `['forge_list_projects', '']` (trailing empty segment).
- `_parse_compile_output`'s segment-loop (`router.py:602-607`) **raises** `CompileInvalidChainShape: empty step at index 1` — *before* `parse_chain` runs.
- But `parse_chain("forge_list_projects ->")` already returns `['forge_list_projects']` cleanly (it drops empties). **The guard is over-strict; the tolerant path exists one line away.**

## The reclassification — #3 is WELL-FORMEDNESS, not routing (DT + Creative)

The roadmap-provisional shape was "`list projects` → routing/selection failure." **The raw refutes it.** The defect is a single extra structural token after a correct tool — chain-step serialization, the **same tier as Slice #1's detached-args**. There is no remaining evidence for routing, capability selection, contextual resolution, or tool discovery as the primary mode. Had we scoped from archaeology we'd have built a content/selection fix for a serialization bug. **3rd milestone instance of direct observation overturning the provisional shape** (serialization-dominant → frozen-can't-host → list-projects-is-well-formedness).

## Why this slice carries a real guarantee (unlike Slice #2)

#3 sits in the **recoverable tier**. The durable taxonomy the room named (cursor-worthy): the well-formedness/content tiering predicts **fixability**, not just shape —

| tier | defects | faithful value | recovery | guarantee |
|---|---|---|---|---|
| **well-formedness (recoverable)** | #1 detached-args, **#3 trailing-empty** | EXISTS | deterministic salvage | **achievable (Slice-#1-grade)** |
| content (non-recoverable) | #2 space-mangle | absent | ecological prevention only | deferred |

A trailing terminal empty segment is **content-free**. Dropping it removes zero semantic content → `['forge_list_projects']` → well-formed. So #3 has a **deterministic, faithful repair** — the thing Slice #2 structurally could not have.

**Safety proof (Creative, primary):** `repair() removes ZERO semantic content` — there is nothing after the arrow to lose, so faithfulness holds *intrinsically*, before any downstream gate. The DI.1 mutation-block is the **secondary** net: a truncated mutation (`flame_rename_shots … ->` with a dropped `commit`) would lose its commit → DI.1 blocks → cannot mutate. Faithful and safe across reads and mutations.

## The room-converged scope (binding)

1. **Repair in the observable salvage family** — extend `normalize_chain_shape` (or a sibling in the same well-formedness pass), **A2 loosen-then-normalize**. `salvage_applied=True` + a distinct reason **`trailing_empty_segment`** (reuse the Slice-#1 salvage channel — `CompileBranchOutcome.salvage_applied`/`salvage_reason` → ObservedTrace).
2. **Observable, NEVER a silent parser strip** — the milestone's central win is hidden→observable repairs; a silent drop destroys the evidence trail that saved us from misreading detached-args.
3. **Scope ONLY the observed shape** — trailing terminal empty segment. Mid-chain empties (`a -> -> b`, `a -> "" -> b`) are plausibly content-free too but were **not observed** → document as future extension, **do not build** (SACRED no-speculative-generalization).
4. **Model-free deterministic bar** — replay the 3 frozen slice2 raws (`forge_list_projects ->`) through the repair → well-formed + salvage record. No Ollama/stack. Slice-#1-shaped.
5. **Guard MOVED not removed** — genuinely-malformed shapes (mid-chain empty, all-empty) still raise `CompileInvalidChainShape` → still `compile_error`. The residual-re-raise is **SACRED / non-optional at close** (Slice #1's lesson).

## FRAMING REQUIREMENT (architectural ruling — Creative, ratified): observability survives parsing

> **Malformed structure MUST survive parsing long enough to be observed and normalized. Any implementation that silently repairs the trailing-empty shape before `normalize_chain_shape` executes is NON-CONFORMANT, because it defeats salvage observability.**

This is not a plan-stage implementation detail — it is a **conformance rule for the slice** (and, generalized, for the entire recoverable tier). It is the Slice-#1 doctrine made explicit: the value of `salvage_applied`/`original_reason` was preventing the false narrative (A) post-gate #1 later caught — *"0 detached-args"* could have been misread as *"salvage worked."* A silent malformed→well-formed conversion before the salvage layer is architecturally wrong **even if the end graph is correct**, because it destroys the measurement surface that justified the fix.

**Grounded mechanism (the trap to avoid):** `normalize_chain_shape` runs post-parse, and `parse_chain` silently drops the trailing empty *upstream* of it. So the naive loosen (delete the `:602-607` guard) yields a **silent** fix — `parse_chain` produces `['forge_list_projects']`, normalize sees a clean list, `salvage_applied=False`, `well_formed=True`. **Non-conformant.**

**The conformant pattern (required):**
```
observed malformed shape → represented faithfully (survives parse)
  → normalize observes it → normalize repairs OR rejects → observability emitted
```
i.e. the loosen must **PRESERVE the trailing-empty into the step-list** (exactly as Slice #1's loosen preserved the bare-args `{…}` token), AND the second empty-guard (`:613-614`, "parsed chain contains empty step") must move into/after normalize. Two precision points the plan MUST carry (DT — without them the "observable" fix ships silent anyway):

- **Sharpening 1 — the dropper is `parse_chain` itself, not just guard 1.** `parse_chain("forge_list_projects ->") → ['forge_list_projects']` (it eats the empty internally; mid-empties too: `'a -> -> b' → ['a','b']`). So "preserve into the step-list" means **source the empty-bearing text-branch from `_top_level_chain_segments`** (which keeps `['forge_list_projects','']`), **NOT from `parse_chain`**. And **do NOT "fix" `parse_chain` to stop dropping** — it is shared by other callers; changing its drop behavior is blast-radius this slice does not want.
- **Sharpening 2 — trailing-vs-mid is enforced in normalize's re-raise, or mid-empties become a THIRD silent path.** Once empties are preserved into the step-list, normalize **salvages the trailing empty (observable)** AND **re-raises `CompileInvalidChainShape` on a mid-chain empty** (the SACRED guard-moved re-raise → mid stays a *loud* failure; "documented-not-built" = still fails, never silently dropped). If the loosen instead lets everything fall through to `parse_chain`, mid-empties get silently dropped — neither raised nor salvaged — the exact silent path relocated. So the conservative scope is **not optional polish; it is what keeps mid-empties loud.**

The salvage stays in the normalize family — never a `parse_chain`/parse-level silent strip. *(Plan settles the exact preserve-into-steps mechanism.)*

**The deeper TF.4 pattern this names:** detached-args and trailing-empty are *both* "preserve malformed token → normalize repairs" because the missing semantic content is zero; space-mangle differs because there is no faithful value to recover. The tiering doctrine gains **predictive power**: recoverable well-formedness defects → deterministic guarantee possible; content defects → guarantee unavailable until an external ground-truth source exists.

## Conformance test matrix (the proof — Creative; non-optional at close)

The slice is observable, conservative, and faithful **iff** all four hold (the residual-re-raise test is SACRED — Slice #1's "guard moved, not removed"):

| input shape | example | required behavior |
|---|---|---|
| **trailing empty** | `forge_list_projects ->` | **salvaged** → `['forge_list_projects']`, `salvage_applied=True`, `reason="trailing_empty_segment"`, `well_formed=True` |
| **mid-chain empty** | `a -> -> b` | **re-raise `CompileInvalidChainShape`** (loud failure, NOT silently dropped, NOT salvaged) |
| **already-clean chain** | `a -> b` | **unchanged**, `salvage_applied=False` (no false salvage) |
| **genuinely malformed residual** | (other unrepairable) | **`CompileInvalidChainShape`** |

The three-stage pipeline this rests on: `_top_level_chain_segments` (preserves empties) → ~~`parse_chain` (drops empties — bypassed for the empty-bearing path)~~ → `normalize_chain_shape` (salvages trailing / re-raises mid). Normalize can only salvage what it can see; the matrix is the proof it sees the right things and rejects the rest.

## Constraints (binding)

`forge_bridge.__all__` = **19**; `translation_oracle.__all__` = **18** (no new public symbol — the salvage channel already exists from Slice #1); `pyproject` = `1.5.1`; SCHEMA_VERSION = "1" (`trailing_empty_segment` is a reason *value*, not a schema change); no new external libs. Frozen corpus + all `reference/postgate*` dirs **never mutated** — the bar reads the 3 slice2 raws and runs the repair in-memory.

## Out of scope (parked, named)
Mid-chain / non-terminal empty segments (future extension, unobserved); a Prong-A-style prompt clause (optional, and now *known weak* — (A) showed the Slice-#2 clause didn't move its target; prevention rides only if useful); `non_tool_step` (#4, intermittent, different raw shape — do NOT merge); desktop-wiring (C) (investigation-gated per (A) Findings 3); TF.3b shared-label item.

## Forward-pointers (plan stage — `TF.4-SLICE-3-PLAN.md`)
- Resolve the preserve-into-steps mechanism (loosen `:602-607` + move `:610-611` into normalize) vs a parse-level sibling — settle which keeps the salvage observable with least churn; ground the exact `normalize_chain_shape` extension + `_validate_chain_shape` re-raise.
- Unit pos/neg pairs: positive (`['forge_list_projects','']` → `['forge_list_projects']` + salvage); negatives (mid-chain empty still raises; clean list untouched, no salvage).
- The deterministic bar replaying the 3 frozen slice2 raws.
- Whether `non_tool_step` (#4) is the slice-after-this, or re-measure first.
