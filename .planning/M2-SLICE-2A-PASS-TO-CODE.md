# M2 Slice 2a — Pass-to-Code Brief — if-gate via skip-propagation

**Date:** 2026-06-18 · **Status:** pass-to-code · **Base:** `main d55afb5`+ (cut a feature branch).
**Parents:** [[M2-SLICE-2-SEAM-DESIGN]] (converged) · [[M2-SLICE-1-PASS-TO-CODE]] (the substrate this extends).
**For:** a code session. Examples are **reference shapes, not rewrite mandates** — match surrounding idiom.

## The principle every task serves (unchanged, now load-bearing)

> **The executor grows only if the outer `GraphSpec` node/edge set changes at runtime.** Any run/skip/route decision is expressible in the dispatch wrapper, because the executor already hands it every input.

Slice 2a is the proof on the cheapest control-flow primitive: **if-gate = conditional skip, entirely in the dispatch layer.** `executor.py` is **NOT touched** (a task asserts it). This generalizes slice-1's `AbortOnFirstErrorDispatch` — same shape, second trigger.

## Acceptance vertical (2a is green when this passes)

```
<read manifest>  →  if(<predicate>)  →  <downstream op>      (LINEAR PRUNE — one terminal)
```
- **gate open** (predicate true): downstream dispatches; both paths → status vector all-`ok`, terminal payloads equal.
- **gate closed** (predicate false): downstream is **skipped**; both paths → `[ok(read), ok(gate), skipped(downstream)]`.

LOCKED to the linear shape (S2-C): no two-branch / re-join / fan-in — that's the deferred multi-sink case and must not sneak in.

---

## Tasks (ordered; one atomic commit each)

### T1 — `NodeResult.control_signal`
**File:** `forge_bridge/composition/node_result.py`
Add `control_signal: str | None = None` (`"skip"` is the only value in 2a). Document it as **orthogonal to `status`**:
- `status` answers *"was a usable output produced?"* (`ok|partial|abstained|error`)
- `control_signal` answers *"what must orchestration do next?"* (`none|skip`)

Do **not** reuse `status`/`reason_code` for skip — the seam rejected both (abstained = "downstream decides" ≠ skip = "downstream must NOT run"; reason codes *explain*, control signals *direct*). Optional additive field on the bridge-internal envelope — does not touch the public 19.

### T2 — admit `if` in the admission table
**File:** `forge_bridge/composition/admission.py`
Register `if` as a primitive (`dispatch_kind="primitive"`, `resolved_class="primitive.if_gate"`), mirroring `filter`. Value-transform primitive declarations apply (bridge-internal; no MCP admission preconditions).

### T3 — if-gate dispatch in `PrimitiveBoundary`
**File:** `forge_bridge/composition/primitive_boundary.py`
Add an `if` branch beside `filter`. Get the predicate from `node.config` the same way `_filter_predicate` does (`config["predicate"]` dict via `FilterPredicate.from_dict`, or `step_text` via `parse_if_step`). Run `IfGateNode(predicate).run(<upstream manifest>)`; mint a `NodeResult`:
- `status="ok"` (the gate **ran** — it succeeded at evaluating),
- `output=<the manifest with execution_state>` (topology-preserving, per `IfGateNode`),
- **`control_signal="skip"` iff the run output's `execution_state == "skipped"`** (predicate false), else `None`,
- `artifact_id` minted (lineage — same as the filter fix), `source_artifact_ids` from upstream, `resolved_class`.

The gate consumes the upstream `output` as its manifest (value-transform input semantics, like filter — not a value-blind-edge violation).

### T4 — `SkipPropagationDispatch` (generalize `AbortOnFirstErrorDispatch`)
**File:** `forge_bridge/composition/compare.py`
Rename/generalize the abort wrapper into `SkipPropagationDispatch`. **Short-circuit a downstream node iff any resolved input is non-flowing**, where the *converged single channel* is `control_signal == "skip"`. Fold abort onto this channel: an **error result also carries `control_signal="skip"`** at mint, so the wrapper has one predicate.
- *Where abort folds:* set `control_signal="skip"` on error mints in `MCPToolBoundary` + `PrimitiveBoundary` (so a plain error still short-circuits downstream — preserves slice-1 abort behavior through the unified channel). **Equivalent fallback if touching error-mints is undesirable:** the wrapper ORs `status == "error"` into its predicate (Design B) — identical compare behavior; pick one and note it.
- The synthetic short-circuit result the wrapper mints carries `control_signal="skip"` (propagates further) + a **did-not-run marker** so the comparator can tell it apart from a node that *ran and emitted skip* (the gate). Track `skipped_node_ids` (as slice 1 did) for the abort/skip parity test.

### T5 — comparator alignment (THE subtle task)
**File:** `forge_bridge/composition/compare.py`
Both paths must produce `skipped` for the **pruned downstream** while the **gate that ran** stays `ok`.
- **Graph side (`_status_token`):** return `"skipped"` for a wrapper **short-circuited** result (the did-not-run marker from T4) — NOT merely for `control_signal == "skip"` (the gate carries `control_signal="skip"` but **ran**, so it must token as its `status` = `"ok"`). Replace the `reason_code == SKIPPED_REASON_CODE` special-case with the unified did-not-run marker (DT: "skipped derives from one place").
- **Legacy side (`normalize_chain_body`):** today it flat-fills `"ok"` for every non-error entry. Teach it: a chain entry is **`"skipped"` iff its `result` has a `skipped_step` key** (the engine-injected skip marker, `_engine.py:41`). Do **NOT** key on `execution_state == "skipped"` — the gate's *own* result also has that when closed (`IfGateNode.run`), yet the gate ran and must stay `"ok"`. `skipped_step` is present **only** on engine-injected downstream skips.
- Result: `read=ok`, `gate=ok`, `downstream=skipped` on both paths. The `success`-status guard from FB-U3 stays (a gate-skip chain is body-status `"success"`, not `"error"`).

### T6 — 2a forcing specimen (linear-prune)
**File:** `forge_bridge/composition/parity_corpus.py`
Add `READ_IFGATE_PRUNE` (named distinctly): `<read manifest> → if(<predicate>) → <downstream op>`, carrying **both** the chain-step form (legacy) and a hand-authored `GraphSpec` (graph) — chain-text→GraphSpec is slice 4. Provide **two cases or one parameterized**: gate-open (downstream runs) and gate-closed (downstream pruned). Ground the read against a real manifest-producing op (captured-not-assembled where a real op is involved).

### T7 — static-outer-set invariant test (proves the reframe)
**File:** a test.
Assert that executing the 2a specimen leaves the outer graph unchanged: the executor's result node-set **==** the `GraphSpec` node-set (no runtime materialization of new outer nodes/edges). This is the mechanical proof that if-gate is behavior-not-topology.

---

## Mandatory negatives / invariants

- **`executor.py` byte-untouched** vs `main` (assert in test; the reframe's whole point).
- **Slice-1 abort still green** through the unified channel — the existing abort-parity test must pass with `SkipPropagationDispatch` (error → downstream skipped, `[ok, error, skipped]`, downstream never dispatched).
- **Gate-ran ≠ skipped:** a closed gate tokens `ok` (it ran); only the *pruned downstream* tokens `skipped`. (Negative test on both legacy `skipped_step`-distinguisher and graph did-not-run marker.)
- **`control_signal` orthogonal to `status`:** a closed gate is `status="ok"`, `control_signal="skip"`.
- **Assent-token-ban invariant** (`test_m2_executor_invariants.py`) stays green.
- `len(forge_bridge.__all__)` stays **19**; ruff clean.

## Out of scope (do NOT build)

- `foreach` / expansion → **slice 2b** (inherits this skip channel).
- Two-branch / re-join / fan-in graphs + the any-skip-vs-all-skip wrapper reduction policy → later (multi-sink).
- Iteration-addressability / runtime outer-graph materialization → the reopen-trigger (seam doc).
- Production honoring of `control_signal` outside the compare harness → rides to slice 5 (same as slice-1 abort lived in the harness; the engine isn't driven in production until then).
- Mutations/authority (slice 3) · chain-text→GraphSpec (slice 4).

## Instructions for code

1. **Branch:** check `git branch --show-current` is `main` first, then cut a feature branch off `main` (planning-docs-on-main footgun, issue #95). Land 2a behind a PR.
2. **Order:** T1 → T2 → T3 → T4 → T5 → T6 → T7. T5 is the subtle one — the `skipped_step` (legacy) vs did-not-run-marker (graph) distinction is the load-bearing alignment; get the gate-ran-stays-ok case explicitly tested.
3. **Ground before T5:** re-read `_engine.py:37-50` (the skip-injection sets `skipped_step`) and `IfGateNode.run` (sets `execution_state` on the gate's own result) so the two `"skipped"`-sources don't get conflated.
4. **One design choice to settle at T4:** error-mints carry `control_signal="skip"` (single predicate, converged) vs wrapper ORs `status=="error"` (untouched boundaries). Equivalent compare behavior — pick one, note it.
5. **Report back:** the two acceptance results (gate-open all-ok; gate-closed `[ok,ok,skipped]` aligned across paths), the slice-1-abort-still-green result, the static-outer-set test, suite count, `__all__` (19), ruff.
