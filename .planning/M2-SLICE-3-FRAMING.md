# M2 Slice 3 — Orch Framing (mutations / authority) — positions for the room

**Date:** 2026-06-19 · **Status:** ORCH DRAFT + CREATIVE CONVERGED (positions on Q1–Q5; DT grounding pending).
**Base:** main `0d7fb61` (arc 2a/2b/2c closed). **Parents:** [[M2-SLICE-3-FRAMING-SEED]] · [[M2-SLICE-2-SEAM-DESIGN]] · the 2a/2b/2c pass-to-code docs.
**Grounded against live reads (2026-06-19):** `graph/commit.py`, `graph/mutation.py`, `graph/stage.py`, `composition/{admission,compare,dispatch}.py`, `console/_chat_compile.py:run_apply_branch`, `tests/composition/test_m2_executor_invariants.py`.

> **Caution flag (carried from the seed):** this is the seam where the operator's assent lives. Every position below is built to keep **assent out of the executor** and **no model prose anywhere near `AssentRecord`** — structurally, not by convention. Redline hardest there.

---

## Thesis

Slice 3 brings the **mutation apply** through the composition substrate (GraphExecutor + a new `CommitBoundary`) **without touching the executor and without moving assent into the graph.** The mechanism already exists in pieces — `CommitNode.verify(held, fresh, assent)` is the gate; `UnifiedDispatch` is the router; `run_apply_branch` is the legacy reference. Slice 3 wires them: compile a ratified chain into a `GraphSpec` carrying a `CommitNode`, dispatch it through the pure executor, and parity-check the terminal against the legacy `run_apply_branch`. The state machine (`proposed→ratified→applied|failed`) stays in `AssentRecordRepo`/the harness — the graph only carries *verify-then-apply*.

This is the same shape as 2a–2c (the primitive exists; the slice admits + dispatches + compares it), with one new load-bearing constraint: **three different authors must own three different facts**, and no two may collapse.

| Fact | Author | Where |
|------|--------|-------|
| **held** manifest (what to do) | model / `compile_intent` | preview, deterministic manifest — *not* prose |
| **ratified** (whether to proceed) | operator | `fbridge ratify` / Console, out-of-band |
| **matched** (held == fresh) | bridge (mechanical) | `CommitNode.verify`, inside the boundary |
| **applied** (state transition) | harness | `AssentRecordRepo`, outside the graph |

The model touches only **held**. It cannot author **ratified** (operator-only) or **matched** (mechanical). That is the gate the orchestrator/model cannot cross.

**Three break conditions (Creative, load-bearing):** the seam is broken if (1) the model can influence `ratified` or `matched`; (2) the executor inspects assent; (3) `CommitBoundary` mutates the assent lifecycle. Any of these is a stop-the-line event, not a fixup.

---

## Success bar (Creative-converged — explicit, not aspirational)

Slice 3 succeeds **only** when **all** hold:

1. Mutation apply **actually traverses `GraphExecutor` via `CommitBoundary`** — not legacy `run_apply_branch`. *Representation parity (the graph can hold the plan) is not apply parity (the graph can carry the apply).* Plan-equivalence alone is necessary but **not sufficient**.
2. Assent remains **outside executor scope** — it enters `CommitBoundary` through the dispatch closure, never as executor state. Assent-token-ban stays green.
3. **Plan-equivalence proven at preview** (`held == fresh`).
4. **Apply happens exactly once** against one controlled state.
5. **Post-state verification** confirms the single apply produced the expected controlled mutation.

Anything less is representation parity, not apply parity.

---

## Q1 — authority chain ↔ graph dispatch. Where does the ratify gate sit? — **DECIDED (Orch + Creative)**

**Decision: apply runs through `GraphExecutor` this slice.** The earlier "real decision for the room" (through-executor vs legacy-apply) is closed: legacy-apply-with-plan-equivalence would only prove the graph can *represent* the mutation, not *carry* it. Slice 3 has not brought mutation through the substrate unless apply traverses the executor.


**Position:** The gate sits in a new **`CommitBoundary`** — a concrete boundary peer to `MCPToolBoundary` / `PrimitiveBoundary` / `ForeachBoundary`, reached via a new `dispatch_kind="commit"` in `UnifiedDispatch`. Assent flows **into the boundary as a parameter**, never through `GraphExecutor`'s edge-resolution machinery. The executor dispatches a node and gets back a `NodeResult` (ok/error); it never sees an `AssentRecord`. Inside the boundary: recompute `fresh`, call `CommitNode.verify(held, fresh, assent)`, and only on `matched AND assent.status=="ratified"` invoke `apply_counterpart.tool`.

**Why this shape:** it mirrors how `SkipPropagationDispatch` already sits *outside* the executor as an orchestration wrapper. The boundary is where side-effect/authority policy is allowed to live; the executor stays a pure runner. `CommitNode.verify` already returns `assent_valid` and `matched` separately — the boundary maps `(matched, assent_valid)` → apply-or-error.

**Settled flow:** the `AssentRecord` *lifecycle* (ratify/persist/mark_applied) stays in `run_apply_branch`; only the verify+apply dispatch moves into the graph. The harness ratifies → compiles `chain_steps` into a `GraphSpec` with a `CommitNode` → runs the executor → reads the terminal `NodeResult` → transitions the `AssentRecord`. **Keep the state machine out of the graph** (assent enters `CommitBoundary` via the dispatch closure, never as executor state).

---

## Q2 — the parity oracle for a mutation

**Position:** You cannot double-exec a rename, so the oracle is **plan-equivalence at preview + apply-once + post-state verification**, not cross-path double-exec of the mutated world. *(Creative: post-state verification is not optional — but it is "the single apply produced the expected state transition from held+ratified+matched," NOT "double-exec parity." Do not dodge post-state; do not pretend double execution is available.)* Three walls:

1. **Preview-determinism (intra-graph self-consistency)** = `CommitNode.verify`'s `held == fresh`. This is the same "doesn't linearize" shape as 2c's fan-in: the parity check is *internal* — does the previewed plan still match a fresh recompute at the authority crossing.
2. **Apply-once** = the mutation tool's discover/verify/apply contract guarantees single application; the graph dispatches `apply` exactly once.
3. **Post-state** = the single apply produced the expected controlled state transition. The fair comparison is: same `held` manifest, same `ratified` assent, same `matched` result → one apply against one controlled state → assert the resulting state is the expected one. This is a *state-transition* assertion, not a second execution.

**For the cross-path (legacy-vs-graph) oracle the milestone spine demands:** compare the **plans**, not the post-mutation states. `compare_strategy_for` already returns `record_replay` for non-idempotent ops — slice 3 finally exercises that path for real. Concretely: capture the legacy path's resolved plan (what it *would* apply) and the graph path's held manifest, normalize, compare; then apply **once** on one path. This sidesteps the "mutating the world twice" problem entirely.

**Surface loudly:** capturing a legacy-apply reference *mutates the state the graph-apply would need*. So the parity fixture is harder to capture than any read fixture — it must be **captured-not-assembled** from a fresh real state, and the drift case needs a fixture where state genuinely changed between preview and recompute. This is the third application of the oracle wall, and the first where the comparison shape is plan-equivalence rather than result-equivalence.

---

## Q3 — admission profile for a mutating op

**Position:** Admit the rename as the first `no_state_mutation=False, idempotent_result=False` entry. `AdmissionRecord.__post_init__` only checks the bools are present (not their values), and `compare_strategy_for` already branches correctly on `idempotent_result` — so the table mechanically accommodates a mutating op today. New `dispatch_kind="commit"`, new `resolved_class` (e.g. `mcp.host_mutation`), `apply_counterpart.tool="flame_rename_shots"`.

**On #86 (side-effect-as-mutation):** slice 3 is the **forcing contrast**, not the resolver. Rename mutates canonical project state — unambiguously `no_state_mutation=False`. That gives #86 a contrastive anchor it lacked: "rename is a mutation; is the deliverable's *filesystem write* also one?" gets a real comparison case. **But don't block slice 3 on #86** — rename needs no #86 ruling to be admitted honestly. Slice 3 *sharpens* #86; resolving #86 stays a parallel call. (Carry-forward says "resolve #86 before leaning on the deliverable admission" — slice 3 is the moment to *open* that, after it lands the unambiguous mutation.)

---

## Q4 — does executor-untouched hold?

**Position: yes — under a strict rule (Creative): `CommitBoundary` may verify and apply; `GraphExecutor` may only route and carry `NodeResult`s.** Drift becomes `NodeResult(error)`; `SkipPropagationDispatch` handles downstream. Any need to advance or reinterpret `AssentRecord` state mid-graph is a **stop-the-line** event. Grounded:

- The invariant test asserts `executor.py` is byte-for-byte `main` **and** contains none of `{AssentRecord, assent_record, ratified, ratification}`.
- `CommitNode.verify` lives in `graph/commit.py`, takes `assent` as a param, gates on `assent.status`. It is dispatched *by* a boundary, not by the executor.
- Drift produces `NodeResult(status="error", reason_code=PLAN_STATE_DRIFT-ish)`; the **existing** `SkipPropagationDispatch` (already outside the executor) folds the abort downstream. So abort-on-drift composes with the 2a abort-fold with **zero** executor change.

**The one crack to watch (surface loudly):** if Commit ever needs to mutate the `AssentRecord` state machine *mid-graph* (proposed→applied), that would drag assent into the dispatch path. It must not. The transition stays in `run_apply_branch`/`AssentRecordRepo`; the graph returns a result, the harness transitions the record. If a specimen forces the executor or the dispatch generic to become assent-aware, **that is the first crack in the slice-2 reframe — stop and escalate, don't paper over it.**

---

## Q5 — forcing specimen

**Position:** `flame_preview_rename` (discover/preview → `held` manifest) + `flame_rename_shots` (apply) — both are real forge-core MCP tools, and v1.7 already ships this rename through the **legacy** `compile→preview→ratify→apply` chain, so the parity reference already exists. `MutationManifest.apply_counterpart.tool = "flame_rename_shots"`.

**Captured-not-assembled matters MORE here than in reads (Creative — theater risk).** Four fixtures must each be a real capture or controlled live capture, never reconstructed: the **held** manifest (live `flame_preview_rename`), the **ratified** assent, the **fresh** state recompute, and the **post-state** after apply. The drift fixture is a capture where state genuinely changed between preview and recompute. If any of these is assembled rather than captured, the slice looks proven while being theater.

**Build first-moves (for the pass-to-code, not this framing):** `composition/compiler.py` (how `chain_steps` → `GraphSpec`, and where a `CommitNode` is emitted), `composition/boundary.py` + `primitive_boundary.py` (the boundary shape to clone for `CommitBoundary`), and the `record_replay` arm of `compare.py` (selected-but-untested today).

---

## Drift UX — DESIGN COMMITMENT (Creative)

"You ratified but state moved, nothing applied" is **trust-building, not trust-eroding — when explained plainly.** The honest UX: *"I could not apply this because the current state no longer matches what you approved."* The dangerous UX is silently applying after drift. Drift-abort is exactly the promise assent is supposed to keep. → Slice 3 must surface the drift outcome with a plain operator-facing explanation, not a bare error code.

---

## Open for DT (grounding) — Creative converged, operator Q1 decided

- **DT-1:** Does the `record_replay` arm of `compare.py` actually exist to be exercised, or is it a stub? (Slice-1 note says selected-but-untested.)
- **DT-2:** Verify the assent-token-ban stays green under a `CommitBoundary` — i.e., assent reaches the boundary via the dispatch closure with **zero** new tokens in `executor.py`. Confirm the byte-for-byte lock survives.
- **DT-3:** Ground the post-state assertion (Q2 wall 3): is there a real read path to confirm the controlled mutation landed (e.g. re-query shot names post-rename), and can it be captured-not-assembled?
- **DT-4:** Confirm `composition/compiler.py` can emit a `CommitNode` into a `GraphSpec` from ratified `chain_steps`, or surface what's missing.

**Resolved:** Q1 (apply through executor — Orch+Creative) · Q2 oracle shape (plan-equivalence + apply-once + post-state — Creative) · drift UX (plain explanation — Creative). **Parked, not blocking:** #86 (slice 3 gives it the contrast; open it after the unambiguous mutation lands — operator call on timing).
