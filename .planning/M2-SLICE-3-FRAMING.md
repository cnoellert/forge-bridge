# M2 Slice 3 — Orch Framing (mutations / authority) — positions for the room

**Date:** 2026-06-19 · **Status:** CONVERGED (Orch + Creative + DT). Ready for pass-to-code. **Fixtures CAPTURED** (live controlled rename on `30sec_edit 21`, 6 artifacts, byte-exact round-trip verified twice; see "Live capture" below).
**Base:** main `0d7fb61` (arc 2a/2b/2c closed). **Parents:** [[M2-SLICE-3-FRAMING-SEED]] · [[M2-SLICE-2-SEAM-DESIGN]] · the 2a/2b/2c pass-to-code docs.
**Grounded against live reads (2026-06-19):** `graph/commit.py`, `graph/mutation.py`, `graph/stage.py`, `composition/{admission,compare,dispatch}.py`, `console/_chat_compile.py:run_apply_branch`, `tests/composition/test_m2_executor_invariants.py`.

> **Caution flag (carried from the seed):** this is the seam where the operator's assent lives. Every position below is built to keep **assent out of the executor** and **no model prose anywhere near `AssentRecord`** — structurally, not by convention. Redline hardest there.

---

## Thesis

Slice 3 brings the **mutation apply** through the composition substrate (GraphExecutor + a new `CommitBoundary`) **without touching the executor and without moving assent into the graph.** The mechanism already exists in pieces — `CommitNode.verify(held, fresh, assent)` is the gate; `UnifiedDispatch` is the router; `run_apply_branch` is the legacy reference. Slice 3 wires them: **hand-author a `GraphSpec` specimen carrying a `CommitNode`** (the 2a/2b/2c fixture pattern), dispatch it through the pure executor, verify plan-equivalence + post-state, and check against the legacy reference. The state machine (`proposed→ratified→applied|failed`) stays in `AssentRecordRepo`/the harness — the graph only carries *verify-then-apply*.

> **Scope boundary (DT correction):** chain_steps→`GraphSpec` compilation is **slice 4** (text→GraphSpec). Slice 3 hand-authors the specimen exactly like the deliverable fan-in fixture. Do **not** pull `compile_operator_sequence` into slice 3 — it's operator-agnostic and would route a commit step with no edit, but the specimen is hand-authored. What's actually missing for slice 3: `admission(commit)` + `CommitBoundary` + the specimen. The compiler is a non-dependency.

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

**Settled flow:** the `AssentRecord` *lifecycle* (ratify/persist/mark_applied) stays in `run_apply_branch`; only the verify+apply dispatch moves into the graph. The harness ratifies → runs the executor over a (slice-3: hand-authored) `GraphSpec` with a `CommitNode` → reads the terminal `NodeResult` → transitions the `AssentRecord`. **Keep the state machine out of the graph** (assent enters `CommitBoundary` via the dispatch closure, never as executor state, and — DT-2 guard — is **never embedded in a returned `NodeResult`**; the boundary returns a plain ok/error/drift result).

---

## Q2 — the parity oracle for a mutation

**Position:** You cannot double-exec a rename, so the oracle is **plan-equivalence at preview + apply-once + post-state verification**, not cross-path double-exec of the mutated world. *(Creative: post-state verification is not optional — but it is "the single apply produced the expected state transition from held+ratified+matched," NOT "double-exec parity." Do not dodge post-state; do not pretend double execution is available.)* Three walls:

1. **Preview-determinism (intra-graph self-consistency)** = `CommitNode.verify`'s `held == fresh`. This is the same "doesn't linearize" shape as 2c's fan-in: the parity check is *internal* — does the previewed plan still match a fresh recompute at the authority crossing.
2. **Apply-once** = the mutation tool's discover/verify/apply contract guarantees single application; the graph dispatches `apply` exactly once.
3. **Post-state** = the single apply produced the expected controlled state transition. The fair comparison is: same `held` manifest, same `ratified` assent, same `matched` result → one apply against one controlled state → assert the resulting state is the expected one. This is a *state-transition* assertion, not a second execution.

**For the cross-path oracle: compare the plans (held-vs-held manifests), not the post-mutation states.**

> **DT-1 correction — `record_replay` is a stub, not "selected-but-untested."** `compare_strategy_for` returns the string `"record_replay"` (`compare.py:130`), but there is **no `compare_record_replay` function and zero callers** — nothing in `forge_bridge/` or `tests/` calls `compare_strategy_for` at all. So "slice 3 finally exercises that path" was wrong: there is nothing to exercise.
>
> **Scoping (don't over-build):** slice 3 needs **plan-equivalence on manifests** — compare two `MutationManifest`s (held-vs-held), a modest extension of the existing `normalize_terminal_output`/`CompareSnapshot` machinery (the deliverable already taught it manifest-shaped normalization). Build that + the post-state assertion. **Do not** construct a generic double-exec-of-mutated-world replay engine to satisfy a string. Repurpose the `"record_replay"` label to mean "plan-equivalence" or leave it — but don't build the engine.

Concretely: plan-equivalence is `held == fresh` (Commit's verify); apply **once**; assert post-state. **Why plan-equivalence is sufficient here (DT):** under the Q1 decision (apply through the executor via the *shared* commit substrate), same `held` + same apply code + one post-state assertion ⇒ post-state parity *by construction*. The heavy double-apply/rollback fixture is only needed in the rejected branch (apply-stays-legacy), which Q1 closed. A single post-state assertion on the one graph apply discharges the obligation.

**Surface loudly:** the post-state fixture is the genuinely hardest in the milestone — a controlled live rename captured pre/post, **captured-not-assembled**, because capturing a reference *mutates the world the graph would need*. It's an isolation/capture problem, not a missing-capability one (DT-3).

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

**DT-2 — holds by construction.** `CommitBoundary` takes assent via the dispatch closure (the `ForeachBoundary.reenter` pattern: a call-time param threaded by `UnifiedDispatch`, not stored on the executor). The executor calls `self._dispatch(node, resolved_inputs)` and only ever carries `NodeResult`s; it never references assent. So `executor.py` stays byte-identical and token-free; `test_m2_executor_invariants` survives. **Literal-ban guard:** assent must stay boundary-local — **never embed it in a returned `NodeResult`** (the executor *carries* `NodeResult`s; keep assent out of them so the ban is literal, not just spirit).

---

## Q5 — forcing specimen

**Position:** `flame_rename_shots` is the specimen. **Live-grounding update (2026-06-19, Phase 25.0):** `flame_preview_rename` is now a *compatibility shim* that delegates to `flame_rename_shots(dry_run=True)`. The tool **already implements the discover/verify/apply contract** `CommitNode` was designed against: `mode: discover | verify | apply` + a `resolved_plan` (the `ChangeRecord` list). So `held` and `fresh` are both `flame_rename_shots(dry_run=True)` manifests; apply is `mode="apply", resolved_plan=<held plan>`; `CommitBoundary` wraps this existing contract rather than reinventing it. `MutationManifest.apply_counterpart.tool = "flame_rename_shots"`.

**Specimen surface (corrected):** the mutation and its post-state read are both **Flame-side** on a loaded **sequence** — `flame_get_sequence_segments` reads segment names pre/post. Not the canonical `forge_*` shot registry (DT-3 correction above). The capture therefore mutates a Flame sequence in the **currently-loaded Flame project**, so the capture target is a *throwaway sequence*, an operator-authorized choice (assent stays the operator's — fittingly).

**Captured-not-assembled matters MORE here than in reads (Creative — theater risk).** Four fixtures must each be a real capture or controlled live capture, never reconstructed: the **held** manifest (live `flame_preview_rename`), the **ratified** assent, the **fresh** state recompute, and the **post-state** after apply. The drift fixture is a capture where state genuinely changed between preview and recompute. If any of these is assembled rather than captured, the slice looks proven while being theater.

**Build first-moves (for the pass-to-code, not this framing):** `composition/boundary.py` + `primitive_boundary.py` + `foreach_boundary.py` (the boundary shape + closure-threading pattern to clone for `CommitBoundary`), `composition/admission.py` (the new `dispatch_kind="commit"` entry), and the `normalize_terminal_output`/`CompareSnapshot` machinery in `compare.py` (extend to manifest plan-equivalence — **not** the `record_replay` string, which is an unimplemented stub). `composition/compiler.py` is **not** touched (slice 4).

---

## Drift UX — DESIGN COMMITMENT (Creative)

"You ratified but state moved, nothing applied" is **trust-building, not trust-eroding — when explained plainly.** The honest UX: *"I could not apply this because the current state no longer matches what you approved."* The dangerous UX is silently applying after drift. Drift-abort is exactly the promise assent is supposed to keep. → Slice 3 must surface the drift outcome with a plain operator-facing explanation, not a bare error code.

---

## DT grounding — all four resolved

- **DT-1:** `record_replay` is a **stub** — the string is returned but unimplemented, zero callers. Slice 3 builds **plan-equivalence on manifests** (extend `normalize_terminal_output`/`CompareSnapshot`), not a replay engine. *(folded into Q2)*
- **DT-2:** Assent-token-ban **holds by construction** (closure-threaded like `ForeachBoundary.reenter`); `executor.py` stays byte-identical. Guard: never embed assent in a returned `NodeResult`. *(folded into Q4)*
- **DT-3 (CORRECTED 2026-06-19 live grounding):** Post-state read path exists but DT-3 named the **wrong surface**. `flame_rename_shots` mutates **Flame timeline** segments on a `sequence_name`; `forge_get_shot`/`forge_list_shots` read **canonical Postgres** shots by `project_id`. Bridge is substrate-not-producer — the Flame rename is **not** auto-reflected into the canonical registry. The post-state read for this specimen is **Flame-side: `flame_get_sequence_segments`** (re-read segment names pre/post). The slice stays coherent (held==fresh + post-state both Flame-side). *(folded into Q2/Q5)*
- **DT-4:** Compiler is operator-agnostic and **not needed** — slice 3 hand-authors the specimen; chain→GraphSpec is **slice 4**. *(folded into Thesis scope boundary)*

**Resolved:** Q1 (apply through executor — Orch+Creative) · Q2 oracle (plan-equivalence + apply-once + post-state, no replay engine — Creative+DT) · Q4 (token-ban by construction — DT) · drift UX (plain explanation — Creative). **Parked, not blocking:** #86 (rename anchors it, doesn't block; open after the unambiguous mutation lands — operator call on timing).

---

## Pass-to-code (scoped — DT)

**Build:**
1. **`admission(commit)`** — `AdmissionRecord` for the rename op: `dispatch_kind="commit"`, `no_state_mutation=False`, `idempotent_result=False`, `apply_counterpart.tool="flame_rename_shots"`, new `resolved_class` (e.g. `mcp.host_mutation`).
2. **`CommitBoundary`** — closure-threaded assent → `CommitNode.verify(held, fresh, assent)` → gated apply (only on `matched AND ratified`) → plain ok/error/drift `NodeResult` (assent never embedded). Routed by a new `dispatch_kind="commit"` arm in `UnifiedDispatch`.
3. **Plan-equivalence-on-manifests in `compare.py`** — extend `normalize_terminal_output`/`CompareSnapshot` to compare two `MutationManifest`s. Do **not** build a record-replay engine. **Comparator firewall (capture-derived, load-bearing):** held payloads carry `{shot_name, segment_name}`; drift payloads carry `{shot_name}` only. **Do NOT normalize that asymmetry away** — it is real state-moved signal, not volatility (same firewall posture as 2c: reduction-skip ≠ content error). The drift case `matched=False` *depends* on it.
4. **Hand-authored commit `GraphSpec` specimen** — 2a/2b/2c fixture pattern.
5. **Fixtures are captured** (`.slice3-captures/` staging → move to `tests/composition/fixtures/` on the feature branch). Post-state read is Flame-side `flame_get_sequence_segments` (*not* `forge_get_shot`; DT-3 correction). `held`/`fresh` are `flame_rename_shots(dry_run=True)` manifests, byte-identical → `matched=True, drift=0`. Drift fixture is a real `discover` on the post-apply (`dt_*`) world against `held`'s `DATA_*` identities → `matched=False`.
6. **`ratified` `AssentRecord` is minted in-test, NOT captured** — assent is bridge-internal (exec gates it behind `clarification_needed`), so mint a ratified record in-test via the existing `run_apply_branch`/`test_tf1` pattern. This is legitimate: assent is the **operator-authored fact** (not an external tool observation), so captured-not-assembled does *not* apply to it — it applies to the external tool payloads, which are all captured. Constructing the assent ≠ theater; faking a tool payload would be.

**Not in scope:** generic record-replay engine · `compiler.py` changes · chain→GraphSpec compilation (slice 4) · #86 resolution.

**Invariants that must stay green:** `executor.py` byte-for-byte main · assent-token-ban · `len(forge_bridge.__all__) == 19`.

**Three-authors maps onto real code:** `CommitNode.verify` is the mechanical `matched` author; `assent.status == "ratified"` is the operator's out-of-band fact; neither is model-reachable. **The seam holds.**

---

## Live capture (2026-06-19) — DT + operator, blocker cleared

Real controlled rename driven through the v1.7 chain on sequence `30sec_edit 21` (turned out to be **real genesis client footage** `DATA_*` / `1248_genesis_built_to_thrill`, not the assumed `tst_` dogfood — caught, surfaced, operator-OK'd with backup, **fully restored**; source media never touched — rename only relabels timeline segments). Six fixtures, captured-not-assembled; `held.json` + `README.md` persisted to `.slice3-captures/` (staging on the feature branch — **move to `tests/composition/fixtures/`, do not commit the staging dir**).

| fixture | what | key fact |
|---|---|---|
| pre-state | 25 `DATA_*` segments | `== post-reset` (round-trip exact) |
| held | `mutation_plan`, `DATA_*→dt_*` | the `CommitNode.verify` input |
| fresh | second discover | byte-identical to held → `matched=True, drift=0` |
| post-state | 25 `dt_*` segments | the apply landed |
| drift | discover on the `dt_*` world | held's `DATA_*` identities vs `dt_*` → `matched=False`, real state-moved drift |
| apply/reset | 25 renamed each way | round-trip restores byte-for-byte |

**Verified facts that de-risk the slice:** preview-determinism (`held==fresh`) · genuine drift (`matched=False`) from a *real* state change, not synthesized · `MutationManifest` shape matches `graph/mutation.py` + `CommitNode.verify` (`resolved_plan` of `{identity, payload}` + `apply_counterpart`) · the payload-asymmetry comparator nuance (build item 3) · assent minted-in-test, not captured (build item 6).

**Re-capture path:** `tests/composition/fixtures/README.md` documents the exact procedure (proven reversible) alongside the tracked `commit_rename_held.json`. Cleanest for code: lift the captures from the fixture / the handoff transcript rather than re-mutate; live re-capture is the byte-exact-validation fallback. *(The original `.slice3-captures/` scratch dir was removed at M2 close; its content lives in the fixtures README.)*

---

## As-built — RATIFIED at M2 close (2026-06-20)

**Shipped:** PR **#100** (squash `aec9723`) — commits `1b43617` (commit boundary) + `dc52de9` (operator-facing unratified message). Merged WITHOUT ultra (no credits); **DT-verified end-to-end**.

**Built, matching the scoped pass-to-code:**
- `commit` admission (`dispatch_kind="commit"`, first `no_state_mutation=False, idempotent_result=False`, `resolved_class="mcp.host_mutation"`, `returns_reference=False`).
- `forge_bridge/composition/commit_boundary.py::CommitBoundary` — closure-threaded assent → `CommitNode.verify(held, fresh)` → gated apply exactly once → plain `NodeResult` (assent never embedded). `UnifiedDispatch` `"commit"` arm threads `self.assent_record`.
- Plan-equivalence-on-manifests in `compare.py` (`_normalize_mutation_manifest`, early-return; comparator firewall preserved — payload asymmetry not normalized).
- Hand-authored commit `GraphSpec` specimen + the captured `commit_rename_held.json` fixture; `AssentRecord` minted in-test.

**Bar — all five met, both gates mutation-proven non-vacuous.** Three break-conditions held: model authors neither `ratified` nor `matched`; executor never inspects assent; boundary reads `assent.status`, never transitions it. `executor.py` byte-for-byte `main` — **across the whole 2a/2b/2c/3 arc**, authority included. 82 composition green + 3 legacy ratification + 3 executor-invariants; ruff clean; `__all__` 19.

**Deviations from the framing (all folded above):** DT-3 post-state surface corrected (Flame-side `flame_get_sequence_segments`, not canonical); `record_replay` found to be an unimplemented stub → built plan-equivalence-on-manifests instead of a replay engine; unratified abort message made operator-facing (`UNRATIFIED_OPERATOR_MESSAGE`).

**Deferred (tracked):** production wiring `chain_steps → GraphSpec` into `run_apply_branch` = **slice 4** (CommitBoundary is proven-in-isolation, zero production callers, like M1) · finding #2 (assent graph-run-scoped, not node-scoped) · #86 (slice 3 anchors the side-effect-as-mutation contrast).

**M2 MILESTONE CLOSED.** The slice-2 reframe — "executor interprets nothing; everything rides in dispatch/boundaries" — held the entire arc, including the operator's assent. → cursor `[[project_passoff_2026_06_20_m2_closed_slice3_authority_shipped]]`.
