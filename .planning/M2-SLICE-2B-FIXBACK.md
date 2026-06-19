# M2 Slice 2b — FIXBACK Brief — foreach parity at N≥2

**Date:** 2026-06-18 · **Status:** fixback · **Branch:** `feat/m2-slice2b-foreach` (continue on it) · **Base:** `a73f9d5`.
**Parents:** [[M2-SLICE-2-SEAM-DESIGN]] §S2-B · the 2b pass-to-code (foreach via re-entrant ForeachBoundary).
**Routing note:** this doc belongs on `main` (docs-on-main / code-on-branch, mirroring the 2a split). Do **not** fold it into a `feat/m2-slice2b-foreach` commit (issue #95 — planning-docs-on-shared-worktree footgun).

## Disposition (DT + Creative, ratified)

Architecture and mechanism **validated**. The slice is **NOT parity-proven**, because every foreach test resolves to **N=1**, the size at which foreach is observationally equivalent to pass-through.

- **Do not reopen the design.** No source changes to `foreach_boundary.py` / `compare.py` / `dispatch.py` / `admission.py`.
- This is **specimen + assertions only**, plus one test-only mock affordance (call-indexed failure).
- Standing verdict: *architecture validated · mechanism validated · parity pending specimen expansion.*

### Why (one line)

N=1 validates **mechanism**; **N≥2 validates semantics** — and iteration *is* foreach's semantic (the same lesson the room applied to the 2a if-gate; see [[feedback_specimen_size_masks_divergence]]). The review note being pre-empted: *"you proved foreach at the one size where foreach disappears."*

### What N=1 leaves unproven

`iteration · routing · ordering · aggregation · fail-fast · index assignment` — none of these becomes observable until there is more than one item. At N=1 a broken "process the first item and return" implementation passes every current assertion.

## The #86 reconciliation (thread this — do NOT assert the impossible)

Creative's per-item assertion "iteration[0] output ≠ iteration[1] output, tied to inputs" is **not fully achievable in 2b's scope**. The body runs **static args** (`shot_id=gs_010` hardcoded); per-item *output* divergence requires data-dependent kwarg derivation from the item, which is **#86 (value-blind edges), explicitly deferred**. Both iterations therefore produce the **same** roto payload *by design*.

What N≥2 **can and must** prove in 2b: distinct **items** routed to distinct iterations, correct **index**, **ordering**, **aggregation**, and **fail-stop**. Output-tied-to-input rides to #86. Assert the identical-per-iteration result **explicitly** so a future reviewer reads it as intended, not as a bug.

## Tasks

### F1 — multi-item collection fixture (captured-not-assembled)
The N=1 source is `_load_real_greenscreen_collection()` (a single real item). Produce a **≥2 distinct-item** collection that preserves the *real* per-item shape — do **not** substitute a thin `{id, is_greenscreen}` stub for the load-bearing fixture.
- **Preferred:** a real `forge_is_greenscreen` capture over a ≥2-shot input.
- **Acceptable fallback (note it in the test):** derive items from the real capture with **distinct identities** (`id`/shot differs), real shape otherwise.
- Lean toward **N=3** so F4's "later iteration never ran" is provable.
- *Judgment call for the room:* if a real multi-shot capture isn't cheap, distinct-identity derivation is the pragmatic floor — but it must keep the real item shape ([[feedback_captured_not_assembled]]).

### F2 — expansion asserts (replace the N=1 asserts in `test_compare_harness_aligns_foreach_expand_iterations`)
- `count == N`, `len(iterations) == N`, `foreach.input_count == foreach.output_count == N`.
- `iterations[i]["item"] == collection[i]` for every i (routing), and `item[0] != item[1]` (distinctness).
- `iterations[i]["index"] == i` (index correctness — not merely envelope count).
- Iteration order == collection order.
- **Keep the cross-path roto-capture equality** (legacy = capture `a`, graph = capture `b`, normalized equal) — that is the real volatile-normalization proof; do not drop it.
- Per-iteration *results* are expected **identical across items** (static body; output-divergence = #86, out of scope) — assert that explicitly.

### F3 — mock affordance: call-indexed roto failure
`_FakeMCP` currently raises `roto_error` on *every* roto call. Add a way to fail on the **k-th** `forge_roto_ref` call only (a counter over `self.calls`). Minimal, test-only.

### F4 — fail-stop asserts (rework `test_compare_harness_aligns_foreach_first_body_error` → non-first failure)
With N≥3 and failure injected at **iteration index 1**:
- iteration 0 dispatched (roto called for it),
- iteration 1 errored → **foreach-wide error** `NodeResult`; `status_vector == ("ok","error")` on both paths,
- **iteration 2 never dispatched** — assert via `mcp.calls`: exactly **2** `forge_roto_ref` calls, not 3.
- *Minimal alternative if N=2:* fail at index 0, assert exactly **1** roto call (proves the loop stopped). N≥3 / fail-at-1 is stronger — it proves a middle iteration both *ran-before* and *stopped-after*; prefer it.

### F5 — static-outer-set test stays, asserts updated
`test_foreach_expansion_preserves_static_outer_node_set`: keep `set(results) == {"read_collection","foreach_roto"}`, update `count` / `len(iterations)` to **N**. The invariant — N iterations live *inside* one envelope, never as outer vertices — gets *stronger* at N≥2.

## Invariants (unchanged — must stay green)
`executor.py` byte-untouched · `ForeachBoundary` stateless / call-time `reenter` · re-root normalization · compose-profile · skip fail-close · `len(forge_bridge.__all__) == 19` · ruff clean · slice-1 + 2a tests green.

## Out of scope (do NOT pull in)
- Per-item kwarg derivation / data-dependent body output → **#86**. (This is *why* per-iteration outputs are identical; do not "fix" it.)
- Skip-in-body · multi-step body · iteration-addressable vertices → deferred per the seam doc.

## Report back
Envelope at N≥2 with item-routing + index + ordering asserts · cross-path normalized equality preserved · fail-stop proven by roto call-count (loop stopped after the failed iteration) · static-set at N · suite count · `__all__` 19 · ruff.

---

# FIXBACK-2 — ultra review findings on PR #98 (boundary surface)

**Date:** 2026-06-18 · **Status:** fixback (post-ultra) · **Branch:** `feat/m2-slice2b-foreach` · **Source:** cloud ultra review of #98.
**Scope:** four findings, all on the **`ForeachBoundary` surface** — the substrate consumers reuse — none touching architecture, parity, or the executor. The parity corpus only feeds ok/error collection-shaped inputs, so these gaps are real but uncovered. **Contained to `foreach_boundary.py` + test assertions. No design reopened.**

**Disposition (Orch recommendation):** fold all four before merging #98 — correctness-on-the-substrate, cheap, and the PR isn't merged. Same fixback-before-merge discipline as slice-1/2a.

## Tasks

### FB1 — abstained/non-usable body must not fake-succeed (bug_001, normal) — **RATIFIED fail-stop (Creative + DT)**
**File:** `forge_bridge/composition/foreach_boundary.py` (the body-result branch, ~line 84).
Today the loop halts only on `body_result.status == "error"`. `NodeResult` has four statuses; an **`abstained`** body carries **no usable output** yet falls through and gets wrapped as a successful iteration `{"value": None}`, with the envelope reporting `status="ok"`, `count=N`. That launders a non-output into success — a direct violation of the M1 crispness invariant (*usable-output is derivable from the discriminator ALONE; never inspect `output` to recover branch semantics*).

**Ratified semantic surface (the reason it's fail-stop, not record-and-continue):** record-and-continue on abstention would open a **second, implicit skip channel** — `status=abstained` *and* `control_signal=skip` both meaning "continue" — blurring the explicit status/control distinction 2a built. Keep it crisp:
- usable output → continue
- skip signal → continue **intentionally**
- non-usable output → **stop**
- error → **stop**

- **Fix:** replace `if body_result.status == "error":` with **exactly `if not body_result.has_usable_output:`** → `_foreach_error(...)`. Symmetric with the upstream check (line ~39) and `PrimitiveBoundary` (`primitive_boundary.py:80,125`). This folds `abstained` + `error` into one uniform fail-stop.
- **DT trap — do NOT "complete" this:** `not has_usable_output` catches `abstained` + `error` but **not `partial`** (partial is usable by status). Do **not** add an output-emptiness probe to catch an "empty-output partial" — inspecting `output` for emptiness *is* the exact crispness violation this fix invokes. Trust the discriminator: `partial → usable → record`. (Earlier "and an empty-output partial" wording was a red herring — dropped.)
- **Preserve the fact:** let the body's own `reason_code`/`message` flow through `_foreach_error` (it already does `body_result.reason_code or "foreach_body_error"`), so the envelope says **`abstained`**, not a flattened `foreach_body_error`. An abstaining body and an erroring body are different facts — preserve which.
- **Ordering:** keep the `control_signal == "skip"` fail-close *after* this check — a closed-gate body is `status="ok"` + `control_signal="skip"` (has usable output), so it correctly falls past into the skip branch.
- **Test (boundary-unit, NOT parity):** mirror `test_foreach_boundary_first_body_error_fails_whole_node` with a **fake `reenter` returning `NodeResult(status="abstained", …)`** → assert foreach-wide error carrying the abstained `reason_code`. Do **not** coax abstained out of `_FakeMCP`/`MCPToolBoundary` (it mints from a payload; abstained-from-roto isn't a clean mapping). No legacy oracle → unit test, not parity.
- **Verify (DT, on return):** mutation on the new guard — defeat the `not has_usable_output` fail-stop and confirm the abstained test reds (proves the guard is non-vacuous, like the N=3 fail-stop).
- **Deferred (named):** honest *partial-foreach* ("skip the abstaining item, do the rest") needs per-iteration disposition marking in the envelope — the same deferred machinery as skip-in-body. Fail-stop is the 2b floor; whether partial-foreach earns priority in the eventual milestone is a Creative call that does **not** change the 2b decision.

### FB2 — body-error envelope must carry upstream lineage (bug_006, normal)
**File:** `forge_bridge/composition/foreach_boundary.py` — `_foreach_error` + its call site (~line 80).
`_foreach_error` calls `_error` without `source_artifact_ids`, so the fail-stop envelope carries the empty-tuple default while **every** sibling path threads `source_artifact_ids=_source_artifact_ids(resolved_inputs)`. Breaks the documented forward-only lineage contract on exactly the path the N=3 fixture exercises.
- **Fix:** thread `resolved_inputs` into `_foreach_error`; pass `source_artifact_ids=_source_artifact_ids(resolved_inputs)` into the `_error` call; update the single call site.
- **Test:** in the boundary unit test (`test_foreach_boundary_first_body_error_fails_whole_node`), assert the error envelope's `source_artifact_ids == (upstream_artifact_id,)`.

### FB3 — malformed `config["body"]` must fail-closed, not raise out of the executor (bug_002, nit)
**File:** `forge_bridge/composition/foreach_boundary.py` — `_body_node` is called as the first statement of `dispatch` (~line 28), before any try/except, so a missing/non-`NodeSpec` `body` raises a bare `TypeError` **out of `GraphExecutor.run`** instead of fail-closing. Structural pre-pass and admission don't inspect operator-specific config.
- **Fix:** wrap the `_body_node(node)` call in `dispatch` with `try/except TypeError` → `_error("invalid_foreach_config", str(exc), node, source_artifact_ids=_source_artifact_ids(resolved_inputs))`. Mirrors `PrimitiveBoundary`'s `PredicateParseError` handling. **Guarding the `_body_node(node)` call (line ~28) alone suffices** — `ForEachNode(operator_id)` (line ~29) can't throw once `body_node` is valid (DT).
- **Test:** malformed foreach NodeSpec (no `body`, and a dict-instead-of-NodeSpec) → returns an error NodeResult, does not raise.

### FB4 — `reason_code` casing consistency (bug_005, nit) — contained fix only
**File:** `forge_bridge/composition/foreach_boundary.py` — the `ForeachInputError` passthrough (~line 51).
Boundary pre-checks emit lowercase `invalid_foreach_input`; the passthrough propagates `exc.code` verbatim = uppercase `INVALID_FOREACH_INPUT` (from `graph/foreach.py`). Two strings for one failure; sibling primitives are uniformly lowercase.
- **Fix (slice-scoped):** `.lower()` the propagated code at the passthrough: `getattr(exc, "code", "invalid_foreach_input").lower()`.
- **No parity teeth (DT, grounded):** `reason_code` is **never** parity-compared — the comparator nulls `terminal_output` on error and the status vector uses `_status_token` → `"error"` only; the `reason_code` string never enters the comparison. So lowercasing at the passthrough has **zero** parity impact — it's purely internal consistency, converging with the boundary's own pre-check codes.
- **Explicitly OUT of scope:** normalizing the uppercase codes in `graph/foreach.py` — those are the **pre-existing legacy node**, and the legacy `_step.py` handler consumes them; that's a wider blast radius and gets its own cleanup with its own legacy-consumer check. Do **not** smuggle it into this fixback.

## Invariants (unchanged — must stay green)
`executor.py` byte-untouched · `ForeachBoundary` stateless / call-time `reenter` · re-root normalization · compose-profile · skip fail-close · N≥2 parity (FIXBACK-1) intact · `len(forge_bridge.__all__) == 19` · ruff clean · slice-1 + 2a tests green.

## Report back
FB1 `not has_usable_output`→fail-stop (no output-emptiness probe) + boundary-unit abstained test preserving the body `reason_code` · FB2 lineage on error envelope + asserted `== (upstream_artifact_id,)` · FB3 malformed-config fail-closed + test · FB4 lowercase passthrough (graph/foreach.py untouched) · suite count · `__all__` 19 · ruff. **On return, DT runs the FB1 guard mutation** (defeat fail-stop → abstained test must red).
