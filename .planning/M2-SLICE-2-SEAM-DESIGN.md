# M2 Slice 2 — Primitive-Node Parity (control-flow) — Seam Design (converged)

**Date:** 2026-06-18 · **Status:** **converged** (Orch draft → DT + Creative redline → folded). Ready for the 2a pass-to-code.
**Parents:** [[M2-PARITY-AND-CUTOVER-FRAMING]] (slice 2 = the *formerly* flagged structural risk — now retired) · [[M2-SLICE-1-SEAM-DESIGN]] (the unified-dispatch + abort substrate this builds on). Slice 1 merged at `main d55afb5`.
**Scope:** the **control-flow** primitives — `foreach` (expansion) and `if-gate` (conditional skip). Value-transform primitives (`filter`/`select`/`collect`) landed in slice 1.

## Headline — the framing's "the executor must grow" claim is RETIRED, and replaced by a sharper invariant

The framing said slice 2 must grow the executor's control model. Grounding the legacy drivers and the actual executor against the room shows that was mis-aimed. The correct line is not "control flow lives in boundaries" — it is narrower and load-bearing (DT):

> **The executor only needs to grow if the outer `GraphSpec` node/edge set must change at runtime. Any run / skip / route decision is expressible in the dispatch wrapper, because the executor already hands the wrapper every resolved input.**

**Grounding (executor.py):** the executor dispatches *every* node in topo order (`executor.py:112-118`) and hands the dispatch callable all resolved inputs. Slice-1's "skip" is **not** the executor declining to schedule — it is `AbortOnFirstErrorDispatch` returning a *synthetic envelope* (`compare.py:72-79`); the executor never skips anything. Topo order is computed from the **static edge set** (Kahn, `_topological_order`), orthogonal to run/skip/route.

**The single trigger that genuinely forces the executor to grow:** a primitive that **materializes new outer-graph nodes/edges at runtime** — data-dependent fan-out where each item becomes an independently-addressable *outer* vertex, or a dynamic goto. **Neither 2a nor 2b introduces that.** (See the foreach-envelope decision below — choosing iteration-addressable vertices *is* this trigger, which is why it defers.)

### Proof-obligation (Creative): the reframe is proven, not asserted

The three cases that *read* as live risks all retire against the invariant — they change execution **behavior**, not graph **topology**, so they live in wrappers/boundaries:
- **nested foreach** — nests inside the foreach boundary's re-entrant dispatch; outer set unchanged.
- **foreach-of-if** — the `if` runs inside the foreach body's re-entrant dispatch; outer set unchanged.
- **gate pruning a fan-in** — the executor hands the merge node *both* inputs; the wrapper applies whatever skip-reduction (any-skip vs all-skip) the merge needs. That forces a richer **wrapper policy**, not an executor change.

**Mechanism-level proof (why nesting composes for free):** foreach re-enters the **same** dispatch substrate (`UnifiedDispatch` + `SkipPropagationDispatch`), never a private control path. So an `if` inside a foreach body is the substrate-with-skip running one level down; a foreach as a gate's downstream is short-circuited by the same wrapper. Re-entry *inherits* control flow. The executor sees none of it.

---

## Split: 2a (if-gate) before 2b (foreach) — LOCKED

Different mechanisms, different risk: 2a = skip-propagation (generalize the abort wrapper, low risk); 2b = re-entrant expansion (medium, but still no executor change). **Ordering rationale (DT):** 2a-first de-risks `foreach-of-if` — a foreach body containing an `if` leans on 2a's skip channel, so building skip *before* expansion means 2b **inherits a proven mechanism**.

---

## Seam S2-A — if-gate via a generalized `SkipPropagationDispatch`, on a first-class `control_signal`

Generalize slice-1's `AbortOnFirstErrorDispatch` into `SkipPropagationDispatch`: short-circuit a downstream node **iff any resolved input carries `control_signal == "skip"`**. **Fold slice-1's abort onto the same channel** — one short-circuit predicate, and the comparator's `skipped` token derives from **one place** instead of the current `reason_code == SKIPPED_REASON_CODE` special-case. Executor untouched; pruning stays in the dispatch composition.

### Q1 RESOLVED — add `NodeResult.control_signal: str | None = None`. It is *required*, not merely preferred, and it is low-risk.

**Why required (the airtight argument — DT):** the tempting alternative is to model a closed gate as a no-usable-output status (`abstained`). It fails by construction against the executor's **propagation doctrine** (`executor.py:37-39`): a non-`ok` upstream is propagated to the downstream node *unchanged* — branching is the node's job. So `abstained` means **"downstream decides."** But a closed gate means **"downstream must NOT run."** Different control semantics. `abstained` is the wrong channel. Gate-skip and abort-skip share *"downstream must not run"* — a short-circuit axis genuinely **orthogonal to `has_usable_output`**. That orthogonality is what earns a dedicated channel.

**Two orthogonal questions, two fields:**
- `status: ok | partial | abstained | error` → **"was a usable output produced?"**
- `control_signal: none | skip` → **"what should orchestration do next?"**

**Why low-risk (not "scary"):** `NodeResult` is declared **bridge-internal, pending promotion** (`node_result.py:6-8` — "promotes to forge-contracts later without a federation-breaking migration"). An optional additive field is the *documented extension path*, not a contracts breach (#91's conformance concern is shared-field *semantics*, not additive optionals).

**Rejected alternatives:** payload-inspection (`output["execution_state"]`) — the crispness violation by name, rejected outright. `reason_code` overload — the honest counter (no new field) but it conflates **explain** (reason codes) with **direct** (control signals) across two registers, which this project has repeatedly rejected (register-conflation discipline).

**Noted future wrapper-policy (not slice-2 work):** when gate-skip meets a true **fan-in**, `SkipPropagationDispatch` needs an any-skip-vs-all-skip reduction policy at the merge node. Deferred with the branching/multi-sink work; the 2a specimen is linear (below), so it isn't forced now.

---

## Seam S2-B — foreach via a re-entrant `ForeachBoundary`; envelope = one outer vertex

Foreach is **one node** in the authoring graph. Its dispatch (`ForeachBoundary`) loops the collection and **re-enters the dispatch substrate** over the body step per item — mirroring the legacy foreach handler (`_step.py:662-693`: sets the iteration payload as `__previous_result__`, dispatches the body through `execute_chain_step`). Body (Phase-N: one step) dispatches per item via `UnifiedDispatch`. The foreach node mints **one envelope `NodeResult`** (`{iterations, foreach, count}`, matching the legacy foreach-step envelope), `source_artifact_ids = (collection_node.artifact_id,)`. The outer executor's static topo-sort does not change — the fan-out lives inside the foreach node's dispatch.

This is the **two-graphs reconciliation** ([[feedback_graph_is_the_goal_not_cli]], [[project_31_grant_run_cardinality_pinned_1_to_many]]): authoring graph = one foreach node (a loop); run-history = N `IterationResult`s (acyclic), carried *inside* the envelope.

### Foreach lineage is NOT an independent question — it is a consequence of the invariant (DT + Creative, collapsing former Q2)

- **M2:** foreach envelope = **one outer lineage vertex**; per-iteration provenance is carried internally in the `IterationResult` records.
- **Later:** **iteration-addressable vertices require runtime materialization** — which is precisely the *one trigger* that reopens the static-executor assumption. So "each iteration independently addressable" is not a lineage-convenience call; it is the executor/topology decision, and it defers to the same later slice as runtime materialization.

---

## Seam S2-C — comparator: defer full multi-sink; pin the 2a specimen to linear-prune

Defer full DAG-wide multi-sink comparison (no specimen forces it yet). **But pin the 2a forcing specimen to the linear-prune shape** so the multi-sink case can't smuggle itself in:

```
read  →  if(pred)  →  downstream      (closed gate prunes the tail; ONE terminal)
```

A two-branch `if/then-else` that re-joins or yields two sinks **is** the deferred fan-in/multi-sink case and must not sneak into 2a. The comparator work 2a actually needs is only: **the skipped downstream's `control_signal`-derived status token aligns across paths** — which slice-1's status vector already does (legacy marks the *next step* skipped at `_engine.py:37`; the graph's `SkipPropagationDispatch` marks the *downstream node* skipped; 1:1 step↔node mapping → vectors align). foreach (2b): the envelope compares as one node's output, normalized per-iteration with the slice-1 `VOLATILE_FIELDS` normalizer.

---

## Forcing specimens

Each carries both a chain-step form (legacy) and a hand-authored `GraphSpec` (graph) — chain-text→GraphSpec is slice 4. Real captures where a real op is involved (captured-not-assembled).
- **2a (if-gate, LOCKED linear-prune):** `<read manifest> → if(<predicate>) → <downstream op>` — gate-true dispatches the downstream, gate-false skips it; status vectors must match across paths.
- **2b (foreach):** `<read collection> → foreach(<per-item op>)` — expansion; envelope matches across paths (per-iteration normalized).

*(Pre-plan task, per slice-1 discipline: ground both specimens against real ops — a manifest-producing read to gate on for 2a, a clean collection→per-item op for 2b.)*

---

## Carry-forward — the trigger that reopens the static-executor assumption

**Authoring-experience watch (DT raised, Creative answered):** foreach-enveloping means iterations are not individually addressable. Will artists hit a wall wanting *"wire iteration[3] somewhere else"*? Creative's read: **eventually yes, immediately no** — the first artist want is *"apply this op to every selected thing"* (the envelope), not *"wire iteration 3 into a custom branch."* Iteration-identity matters once the graph ecosystem is rich enough; that is a later-stage sophistication problem, not a slice-2 forcing function. **Document it as the explicit trigger** that reopens runtime-materialization (= the single executor-growth trigger above). Do not let hypothetical iteration-addressability pull materialization into M2.

---

## Out of scope

- `executor.py` is NOT touched (the whole point). The slice-1 assent-token-ban invariant stays green.
- Multi-step foreach bodies (Phase-N caps the body at one step) → later.
- True multi-independent-sink branching + the fan-in skip-reduction policy → later slice.
- Iteration-addressable vertices / runtime outer-graph materialization → the reopen-trigger above.
- Mutations/authority (slice 3) · chain-text→GraphSpec (slice 4) · live reachability (slice 5) · cutover (slice 6).

---

## Redline resolution (converged 2026-06-18)

- **Reframe** — ACCEPTED and strengthened: restated as the **static-outer-set invariant** (executor grows only if the outer GraphSpec changes at runtime); the three worry-cases retire against it; single named growth-trigger = runtime materialization. Proof-obligation satisfied by the invariant + the re-entry-inherits-control-flow mechanism argument.
- **Q1** — `NodeResult.control_signal: none | skip` added; *required* (abstained = "downstream decides" ≠ skip = "downstream must not run", per the propagation doctrine); abort folded onto the same channel; low-risk (bridge-internal additive optional). Payload-inspection and reason_code-overload rejected.
- **Q2** — COLLAPSED into the invariant: foreach envelope = one outer vertex; iteration-addressable = runtime materialization = deferred.
- **Q3** — defer full multi-sink; **2a specimen pinned to linear-prune**.
- **Split** — 2a before 2b, LOCKED (2b inherits 2a's proven skip channel).

**Next:** the **2a pass-to-code** (the `SkipPropagationDispatch` + `NodeResult.control_signal` + if-gate boundary + linear-prune specimen + compare alignment), the M2 equivalent of the slice-1 pass-to-code brief.
