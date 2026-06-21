# M2 Slice 4 — Framing Seed (chain-text → GraphSpec / first production caller) — grounding for the framing pass

**Date:** 2026-06-20 · **Status:** SEED (grounded seam map + open questions; the Orch framing-with-positions comes next, for DT/Creative redline).
**Base:** main `24773d6` (M2 parity phase complete; slice 3 shipped, `CommitBoundary` proven in isolation).
**Parents:** [[project_passoff_2026_06_20_m2_closed_slice3_authority_shipped]] · `M2-PARITY-AND-CUTOVER-FRAMING.md` (slice 4 = "Chain-text → GraphSpec", first cutover slice) · `M2-SLICE-3-FRAMING.md`.

## What slice 4 is
The **first cutover slice.** Give the composition engine — and `CommitBoundary` specifically — its **first production caller**: compile a ratified chain (`AssentRecord.chain_steps`, text) into a `GraphSpec` and run it through `GraphExecutor` from `run_apply_branch`, instead of (or alongside) the legacy `run_chain_steps` replay. Parity oracle: graph-apply produces the same outcome as the legacy replay. (Slice 5 makes both paths live for real-traffic compare; slice 4 makes graph-apply *work* and parity-test it offline.)

## Grounded seam map (verified 2026-06-20)
- **Legacy apply path:** `run_apply_branch` (`console/_chat_compile.py:272`) → `run_chain_steps` (`console/_engine.py:17`) → per-step `execute_chain_step` (`console/_step.py`). Steps are **text** (`list[str]`); control-flow is **context flags in a linear loop** (`__if_gate_skip_next__`, `__previous_result__`); `assent_record` is threaded **per-step**.
- **Existing compiler:** `composition/compiler.py::compile_operator_sequence` compiles a **structured `operator_sequence`** (step dicts with `operator_id` / `inputs` / `output_artifact_id`) → `GraphSpec`, wiring implicit `output_artifact_id → inputs` edges. **It does NOT consume text `chain_steps`.** ← the representation gap slice 4 must close.
- **Graph runtime:** `GraphSpec` → pure `GraphExecutor` → `UnifiedDispatch` (`assent_record` field) → boundaries incl. `CommitBoundary`. Control-flow primitives (`if_gate`, `foreach`) already have boundaries (slices 2a/2b).
- **Preview/commit production flow:** `run_compile_branch` (`_chat_compile.py:172`) compiles NL → chain-step **text** via `router.compile_intent`; the compile system prompt teaches the `->` syntax and the `commit` keyword for an authority transition. A commit-containing graph (`graph_contains_commit_node`) → `build_preview_from_steps` (TEXT-shaped preview: `{step_text, tool_name, args_preview, would_mutate}`) → persist a **proposed `AssentRecord` storing `chain_steps` text**. **No held `MutationManifest` is persisted.**

## Load-bearing finding — where `held` comes from in production
In the slice-3 unit test, `held` sat in `node.config`. **In production there is no persisted held manifest** — the operator ratifies *text*. So `held` must be recomputed at apply time: the rename **discover** step runs (producing the manifest), and the commit step verifies that against a **fresh** recompute. In graph terms the ratified mutation compiles to **`[rename discover node] --edge--> [commit node]`**, where the commit node's `held` arrives from the **discover node's output via a resolved input**, not from config. **Therefore `CommitBoundary` must learn to read `held` from `resolved_inputs` (an upstream edge), not only `node.config`** — a concrete slice-4 extension. (Open: is the drift window then preview→apply, or only discover→apply within one apply-time run? See Q3.)

## Inherited binding constraints
- **Executor untouched** — `executor.py` byte-for-byte `main` (tested invariant). Slice 4 adds a compiler + wires `GraphExecutor` into `run_apply_branch`; the executor itself stays untouched.
- **Three-authors / assent out of the executor** — unchanged; assent still enters via `UnifiedDispatch.assent_record` → `CommitBoundary`, never the executor, never a `NodeResult`.
- `len(forge_bridge.__all__)` stays **19**; writer's-room cadence; captured-not-assembled.

## Open framing questions (for the Orch framing pass to take positions on)
- **Q1 — the text→GraphSpec compiler.** Build a new `chain_steps(text) → GraphSpec` compiler, or reuse the per-step parse/classify already in `execute_chain_step` / `_step.py` to emit `NodeSpec`s? **Do not duplicate the chat step-parser.** Where does the parse boundary live so legacy and graph share one grammar?
- **Q2 — scope of slice 4.** The locked framing says "the NL/chain-step surface compiles into `GraphSpec`." The operator's framing narrows to the **ratified-apply path** (`run_apply_branch`), where `CommitBoundary` needs its first caller and parity stakes are highest. Lean: **start with the apply path** (narrow, high-value), widen to read/non-mutating chains after. Flag the decision explicitly.
- **Q3 — `held` provenance + the drift window.** Confirm the legacy commit step recomputes `held` from the prior discover step's context (TOCTOU = discover→apply within one run), vs any preview→apply anchor. Then decide: does the graph preserve exactly that window, or does slice 4 tighten/loosen it? This sets what "drift" *means* in production and must match legacy for parity.
- **Q4 — `CommitBoundary` held-from-edge.** Extend `_held_manifest` to accept `held` from `resolved_inputs` (upstream discover node) in addition to `config`. Keep the config path for hand-authored specimens. Negative test: held-from-edge and held-from-config produce identical verification.
- **Q5 — parity oracle (production-vs-production).** graph-apply vs legacy `run_chain_steps` replay of the same `chain_steps`. Both mutate once → same plan-equivalence + post-state shape as slice 3, now across the two production paths. Captured-not-assembled chain fixtures (the slice-3 `30sec_edit 21` capture extends here).
- **Q6 — full step vocabulary in a ratified chain.** A ratified chain may carry reads + `if`-gates before `commit`. The compiler must emit those as graph nodes too (filter / if_gate boundaries exist). Slice 4's compiler handles the whole admitted vocabulary that can appear pre-commit, not just the commit step. Also handle `_strip_commit_for_exact_read_graph` (commit-containing-but-all-reads) coherently.

## First moves for the framing pass
1. Read `console/_step.py::execute_chain_step` (the per-step parse/dispatch — the reuse candidate for Q1) and how the commit step gets its `held` from context (Q3).
2. Read `composition/compiler.py` again with Q1 in mind — extend it (text front-end) or build a sibling `chain_compiler.py`.
3. Confirm `CommitBoundary._held_manifest` change surface (Q4) and that the assent-token-ban + executor byte-lock survive wiring into `run_apply_branch`.
4. Then draft the Orch framing with positions on Q1–Q6, lead with views, hand to the room (DT grounding / Creative experience). **Caution: this is the first slice that touches the production apply path — `run_apply_branch` is live in the chat surface.**
