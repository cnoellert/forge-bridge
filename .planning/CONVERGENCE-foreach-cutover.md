# Convergence — live cutover of the graph-authored foreach rename

**Date:** 2026-07-01
**Subject:** Wire the graph-authored `foreach` rename fan-out into the live `_run_fanout` path (today: CLI hand-assembly). Sibling to `.planning/CONVERGENCE-foreach-index.md` (which closed the iteration-index gate, #135).
**Cadence:** 3 independent views (adapter-minimalist / graph-purist / skeptic), redline round, converged lean.

---

## The empirical finding that reframed it

Live selected segments arrive **UNSORTED** from Flame (`cli/interactive.py` `_segments()` → natural traversal order). The single load-bearing sort is `timeline_sorted` inside `_segments_of` (`cli/verbs.py:177`). `SelectNode` is identity-only and cannot sort; there is **no** sort primitive in the graph vocabulary. Per the index-convergence's own rule ("not naturally ordered → the graph needs an ordering step"), this looked like it forced a new node — until the redline found the real shape.

## The reframe that carried it (View C)

**Only the `$n` counter is order-sensitive.** Verified: downstream is entirely identity-keyed — `host_resolve` / discover resolve each entry by `{track_idx, record_in, seg_name, source_name}` (`editorial_delta.py:105`), never by position; `collect` merges in arrival order but names are already baked. Literal rename returns the template unchanged for every segment; trims apply per-segment identity-keyed offsets. **So the ordering seam exists for exactly one of four mutations.** A and B both wrongly assumed the first cutover must carry the counter.

---

## Converged lean — the immediate cutover

**Reject the A/B binary as premature. Cut over the order-insensitive path first, branch on `has_counter(value)`** (already a function, `editorial_delta.py:45`): no counter → live graph-authored path; counter → stays on the proven CLI hand-build rail. This proves the live graph mutation path end-to-end — reachability + the preview→ratify→commit rail through a *graph-authored* delta — with **zero ordering decision**.

**Grounding correction to C:** only `RenameDeltaNode` exists as a graph node today; **trims have no graph node** (`_build_trim_delta` is CLI-only). So the truly-zero-new-code first step is **literal (counter-free) rename through the existing `RenameDeltaNode`**. Trims follow once a trim delta node lands. Strategy unchanged; first step is smaller than "rename + trims."

Note the live path *already* runs through a graph (`build_host_mutation_spec` → `op(delta=cli_delta) → delta_to_manifest`). Cutover = replace the CLI-authored `delta` with the graph-authored spec (`source → foreach → collect → host_resolve → delta_to_manifest`), through the same `preview_editorial_delta` / `apply_editorial_delta` rail.

## The deferred seam — when the counter goes live

Lean **A/C mechanism, not B.** Establish ordering **once at the selection/gather boundary** (`_match_selected`) as an invariant of "what a resolved working set *is*" — shared by the CLI and any future web card — and collapse the three defensive re-sorts (`interactive.py:534`, `:472`, `verbs.py:177`) to that one home. Add an **assert-at-edge** turning the `editorial_delta.py:150` guard comment into a fail-closed contract. Ordering is part of *input resolution/lowering* ([[project_tools_are_macros_over_contextual_input_resolution]]), not a pipeline stage.

### Why B (a graph `order` node) lost the redline but isn't dead
B's "generic `order` node, timeline key in *config*" genuinely dissolved A's domain-leak objection (host-neutral mechanism, caller-supplied key — mirrors `FilterPredicate`'s flat AST). Two things sank it **for now**: (1) the graph was architected to *trust* an upstream sort, not perform one — the offline proof itself feeds `fixture_source` a `timeline_sorted` list (`test_m2_batch_author_foreach.py:90`); (2) B's endpoint-parity argument ("no adapter when NL/Console/a peer drives it") is **real but future** — no such caller exists, and the counter path can stay on the CLI rail until one does. Building a general reorder primitive for the one caller that already sorts fine is speculative generality.

---

## Intentionally unbound (with triggers)
- **The graph `order` node (B)** — unbound pending a **second, non-CLI caller that must drive the *counter* fanout without an adapter to pre-sort** (NL/Console/peer). That is when B's endpoint-parity argument becomes load-bearing; decide order-node-vs-per-surface-gather-boundary then, with the actual caller topology visible (the DRY-vs-locality tradeoff is only answerable then).
- **Counter-path cutover** — unbound pending the order-insensitive cutover landing (proves the rail) + the gather-boundary ordering invariant being established.
- **Trim-verb cutover** — unbound pending a trim delta graph node (analog of `RenameDeltaNode`); trims are order-insensitive so they carry no seam, just need the node.

## Rejected
- **Sort inside `foreach`** — breaks arrival-order honesty + ordinal-only + `no_state_mutation` ([[feedback_orchestrator_control_flow_not_meaning]]).
- **Counter reads a timeline field directly** — abandons the clean `start + pos*step` model; couples the renderer to Flame's `record_in_frame`.
- **Sort owned by the delta-builder (status quo)** — three defensive re-sorts owning it nowhere is the recurring-bandaid signal ([[feedback_recurring_bandaid_is_root_cause_signal]]).

## Invariants
- `composition/executor.py` byte-stable; `foreach` ordinal-only + `no_state_mutation=True`; live preview→ratify→commit rail must not regress. `forge_bridge.__all__` == 19; no new deps.

---

## Implementer brief — FIRST STEP (order-insensitive cutover: literal rename → live graph)

**Goal:** In the live `_run_fanout` path, route **counter-free literal rename** through the graph-authored fan-out spec (`source → foreach(rename_delta_entry) → collect → host_resolve → delta_to_manifest`) instead of CLI hand-assembly, via the existing `preview_editorial_delta` / `apply_editorial_delta` rail. Everything else (counter rename, trims) stays on the current CLI path. Dual-path, `has_counter`-gated. No ordering machinery (literal rename is order-agnostic).

**Ground first (read, don't assume):** `cli/interactive.py` `_run_fanout` / `_build_mutation_spec_multi:209` / `_preview_mutation_multi:231` / `_apply_held:258`; the exact signatures of `preview_editorial_delta` / `apply_editorial_delta` / `graph_replay_commit_spec` in `orchestration/apply_editorial_delta.py`; `verbs.build_host_mutation_spec:325` / `host_resolve_operator`; `has_counter` (`graph/editorial_delta.py:45`); the test-only graph assembly `tests/composition/test_m2_batch_author_foreach.py` `_fanout_graph`.

**Do:**
1. **Promote the graph fan-out spec builder from test to production** — extract `_fanout_graph`'s assembly (`source/fixture_source → foreach(rename_delta_entry) → collect → host_resolve → delta_to_manifest`) into a real builder (e.g. `composition/` or `cli/verbs.py` alongside `build_host_mutation_spec`). It takes the segments + rename template + sequence and returns a `GraphSpec`. Reuse admitted operators; the source node must be a real (non-fixture) source of the selected segments.
2. **Branch in `_build_mutation_spec_multi`** (or the tightest seam in `_run_fanout`): `if not has_counter(value)` → build the graph-authored spec; else → the existing CLI `build_host_mutation_spec(build_rename_delta(...))`. Both feed the SAME `preview_editorial_delta` → held → `apply_editorial_delta(graph_replay_commit_spec(held), assent_record=_ratified_assent())`.
3. **Prove parity** — a test that the graph-authored spec yields a byte-identical `MutationManifest` to the CLI path for a literal (counter-free) rename over UNSORTED input (literal is order-agnostic, so unsorted must still match). Use the compare harness idiom already in `test_m2_batch_author_foreach.py`.
4. **Confirm no regression** — the counter path still uses the CLI builder unchanged; full `tests/composition/` + `tests/cli/` + console foreach/step green.

**Constraints:** `git diff --stat` must NOT list `composition/executor.py`; `forge_bridge.__all__` == 19; no new deps; `foreach` admission unchanged. Dual-path only — do NOT touch the counter path's builder, and do NOT add any ordering node or sort step (out of scope; counter path deferred).

**Out of scope:** counter cutover, the gather-boundary ordering invariant, the assert-at-edge, trim graph nodes, the `order` node. First step proves the live graph rail on the safe case only.

**Deliverable:** the production spec builder (file + signature), the branch site, the parity test (+ that it runs over unsorted input), commit hashes, confirmation executor byte-stable + `__all__`==19, and any place the live rail did NOT accept the graph-authored spec cleanly (a real integration mismatch is a finding — report it).
