# M2 Slice 2b — Seam Convergence + Pass-to-Code — foreach via re-entrant ForeachBoundary

**Date:** 2026-06-18 · **Status:** converged → built → **merged (`b92de05`, PR #98)**. As-built doctrine at the foot.
**Parents:** [[M2-SLICE-2-SEAM-DESIGN]] §S2-B (envelope = one outer vertex; iteration-addressability deferred) · [[M2-SLICE-2A-PASS-TO-CODE]] (the dispatch substrate this re-enters).
**Cadence:** Orch draft → DT + Creative redline → folded → pass-to-code → built → ultra → fixback (see [[M2-SLICE-2B-FIXBACK]]).

## The principle every task serves (unchanged, load-bearing)

> **The executor grows only if the outer `GraphSpec` node/edge set changes at runtime.** foreach loops *internally* and mints **one outer `NodeResult`**; the N iterations live *inside* the envelope, never as outer vertices. `executor.py` is **NOT touched**.

2b-specific invariant (Creative): **`ForeachBoundary` owns *iteration*, not *execution*.** It re-enters the **one shared dispatch substrate** per item — no alternate dispatcher, no per-operator special-casing in the loop.

## The seam was already converged; 2b needed the mechanism-level pass

§S2-B settled envelope = one outer vertex, no executor growth, iteration-addressability deferred. What 2b's pass resolved were five mechanism questions. The substrate was friendlier than feared — `ForEachNode` (`graph/foreach.py`) already existed with `items`/`iteration_payload`/`wrap_result`/`envelope`/`IterationResult` and **does not execute the body** (`body_step` feeds only the envelope label).

### Q-A — Body representation: **embedded body `NodeSpec`** (Creative + DT endorsed)
The foreach `NodeSpec.config["body"]` carries an **embedded `NodeSpec`** (the per-item operator). Legacy keeps `foreach(<text>)` on its side of the parity pair; the graph carries structure ("the graph is the view of record"). Body-as-`step_text` parsed in the boundary was rejected — it drags slice-4's text→GraphSpec work into a dispatch boundary. **DT consequence:** the envelope's `foreach.body` is representation-divergent (text on legacy, NodeSpec/absent on graph) → the comparator **strips it** (same category as `content_hash`/`request_id`).

### Q-B — Re-entrancy wiring: **call-time threading** (DT corrected Orch's settable-reference)
`UnifiedDispatch.dispatch` routes a foreach node to `self.foreach_boundary.dispatch(node, resolved_inputs, reenter=self.dispatch)`. **No construction cycle, no stored reference, boundary stateless.** Third `dispatch_kind="foreach"` (explicit routing beats overloading `PrimitiveBoundary`). Per-item plumbing mirrors legacy (`_step.py:670`): mint a per-item input `NodeResult` wrapping `iteration_payload(item)` as `output`, feed as the body's resolved input. Per-item input is **lineage-bearing only** — kwarg derivation from item values stays unbound (#86; value-blind edges hold).

### Q-C — Iteration skip/error semantics: **error fail-fast; skip-in-body has no oracle → deferred** (DT grounding collapsed the choice)
Legacy is fail-fast — first body error returns `{error: {iteration_index, foreach_step_index, body_step}}`; graph mints the matching foreach-wide error envelope (parity-forced). **Skip-in-body has no legacy oracle:** the legacy foreach loop never reads the skip flag, and a one-step body has no "next step" to skip — legacy de-facto is *record-and-continue*, so there is nothing to parity-match. Skip-in-body therefore deferred (fail-closed in the boundary), **not** invented into 2b. Creative's *record-and-continue* is the **presumptive future** semantic, explicitly deferred to the same milestone as multi-step bodies / per-item gating.

### Q-D — Comparator: **re-root, not suffix-match** (DT corrected Orch)
The envelope nests volatile fields at `iterations[i].result.<...>`. The comparator strips the recognized `("iterations", <int>, "result")` **prefix**, then applies slice-1's surgical absolute-path ruleset **unchanged** — preserving the deliberately-surgical property (suffix-matching would over-canonicalize any field sharing a leaf name). Plus strip `foreach.body` (Q-A).

### Q-E — Compose-profile: **body-derived** (cheap because of Q-A)
`admitted_records_for` recurses into the foreach node's `config["body"]` and folds in the body's `idempotent_result`; `compare_strategy_for` derives the strategy honestly rather than foreach asserting a profile it can't own.

## Tasks as built (T1–T7)
1. **admit `foreach`** — third `dispatch_kind="foreach"`, `resolved_class="primitive.foreach"`.
2. **`ForeachBoundary`** (new `foreach_boundary.py`) — stateless; `dispatch(node, resolved_inputs, *, reenter)`; one upstream, fail-closed; per-item input minted from `iteration_payload`; first body error → foreach-wide error; all-ok → `node.envelope(iterations)` as one `NodeResult`, `source_artifact_ids=(collection.artifact_id,)`.
3. **route foreach in `UnifiedDispatch`** — `reenter=self.dispatch`.
4. **comparator re-root + strip `foreach.body`** (`compare.py`).
5. **compose-profile** — recurse into body NodeSpec.
6. **forcing specimen** `READ_FOREACH_EXPAND` — `forge_is_greenscreen` (collection) → `foreach(forge_roto_ref)`, body as embedded NodeSpec.
7. **static-outer-set invariant test** — executor node-set == GraphSpec node-set.

## FIXBACK-1 — parity proven at N≥2 (the original specimen was N=1)
The first specimen resolved to **N=1** (the real greenscreen capture is single-item), where foreach is observationally pass-through — the [[feedback_specimen_size_masks_divergence]] lesson the room had already applied to the 2a if-gate. Extended to an **N=3** fixture derived from the real capture (real per-item shape, distinct identities): ordered indices `[0,1,2]`, `item[i] == collection[i]`, distinctness, aggregation, and **fail-stop** (error injected at iteration 1 → both paths `("ok","error")` and **exactly two roto calls** → iteration 2 never dispatches). Per-iteration outputs identical **by design** (static body args; per-item output divergence = #86). Full detail: [[M2-SLICE-2B-FIXBACK]] FIXBACK-1.

## FIXBACK-2 — post-ultra boundary-surface findings
Cloud ultra on #98 surfaced four boundary-surface gaps (uncovered because the corpus only feeds ok/error): FB1 abstained body fell through to a faked iteration; FB2 error envelope dropped lineage; FB3 malformed `config["body"]` raised out of the executor; FB4 `reason_code` casing split. All four folded **before merge** and DT-verified (incl. an FB1 guard mutation). Full detail: [[M2-SLICE-2B-FIXBACK]] FIXBACK-2.

---

## RATIFIED AS-BUILT DOCTRINE (DT + Orch + Creative)

- **The slice-2 reframe is fully proven.** Across both control-flow primitives — if-gate (2a) and foreach (2b) — the executor stayed byte-untouched. Control flow lives in the dispatch wrapper / boundary; **the executor grows only if the outer GraphSpec changes at runtime**, which neither primitive does.
- **Re-entry inherits control flow.** foreach re-enters the *same* dispatch substrate one level down — not a private control path — so nesting (foreach-of-if, nested foreach) composes for free; the executor sees none of it.
- **foreach = one outer vertex.** The authoring graph is one foreach node (a loop); run-history is N `IterationResult`s carried *inside* the envelope. Iteration-addressability (wiring `iteration[3]` as a vertex) is **THE named trigger** that reopens runtime outer-graph materialization — the moment the outer graph goes dynamic. Explicitly deferred, not forgotten.
- **N=1 ≡ pass-through for foreach.** A parity oracle must be exercised at N≥2 (distinguishable items + a non-first-iteration failure) before "expansion proven" stands. The N=3 fixture is the guardrail.
- **The fail-stop semantic surface (FB1):** `usable output → continue` · `skip signal → continue intentionally` · `non-usable output → stop` · `error → stop`. Record-and-continue on a non-usable (abstained) body would open a *second, implicit skip channel*, blurring the explicit status/control distinction 2a built — rejected. Honest *partial-foreach* needs per-iteration disposition machinery and defers.
- **Crispness held under pressure (FB1 trap):** `if not body_result.has_usable_output` is a clean discriminator check. Catching an "empty-output partial" would require inspecting `output` for emptiness — the exact crispness violation the fix invokes. Trust the discriminator; `partial → usable → record`.

## Open frontier (next seams)
- **Slice 2c — multi-sink comparator:** full DAG-wide multi-sink comparison + the any-skip-vs-all-skip wrapper reduction policy at a true fan-in (deferred since the seam; no specimen forced it through 2a/2b's linear/single-sink shapes).
- **Carry-forward (non-blocking):** #86 per-item kwarg derivation (also unlocks a true multi-shot capture; the N=3 fixture is a 3× identity-varied clone of one real item) · `__filtered_collection__` not mirrored in `ForeachBoundary` (fine for static-arg bodies) · `graph/foreach.py` uppercase reason_codes (separate cleanup, legacy `_step.py` consumers — NOT smuggled into FB4) · skip-in-body / multi-step body / nested foreach / honest partial-foreach.
- Remaining: slices 3 (mutations/authority) · 4 (chain-text→GraphSpec) · 5 (live reachability / production `control_signal` honoring) · 6 (cutover).
