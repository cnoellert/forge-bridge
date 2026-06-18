# Milestone 2 — "Parity & Cutover" — Framing (converged)

**Date:** 2026-06-18 · **Status:** **converged** (Orch draft → DT + Creative redline → folded). Ready for the seam-design pass.
**Parent:** [[M1-WIRE-AND-RUN-SEAM-DESIGN]] (engine proven, not yet driven) · **Demonstrator-later:** [[AUTHOR-STILL-VIDEO-LOOP-FRAMING]] (#66, the cyclic milestone).
**North star:** [[project_graph_first_priority_nl_can_wait]] — the operator-drivable graph is the goal; this milestone is where the M1 engine stops being proven-in-isolation and becomes the runtime reality.

## Unifying principle (top-line for the seam-design doc)

> **The executor interprets nothing — not assent, not errors, not clarification. The wrapping orchestration interprets everything.**

Seam B (assent), the failure/abort/clarification gap (Seam D), and slice 3 (mutations) are the **same boundary stated three times**. The executor executes and propagates; every act of *interpretation* — deciding ratification, aborting a chain on error, raising a clarification — lives in the orchestration that reads the results map. Hold this line and all three seams fall out consistently. ([[feedback_orchestrator_control_flow_not_meaning]])

---

## What M1 left us (honest state)

`forge_bridge/composition/` is a complete graph-native composition engine — `GraphSpec` (IR of record), `NodeResult` (4-variant), an async fail-before-spend `GraphExecutor`, `MCPToolBoundary` (mints NodeResult, allow-list default-deny), and a structural compiler (linear→degenerate graph). 25 `tests/composition` green, one live round-trip against `forge_is_greenscreen`. **Zero production callers** — `GraphExecutor` is unreachable from any surface (graph/NL/CLI). M2 is the drivable surface.

---

## The boundary decision (converged: ONE milestone, cutover gated dead-last)

Creative argued for splitting Parity and Cutover into two milestones (different success criteria: *"can it carry the workload?"* vs *"do we trust it enough to delete?"*). DT argued for one milestone with cutover gated last (splitting risks parking slices 1–5 behind `run_chain_steps` indefinitely — the exact shelf-ware the operator warned against, and the banner M1 just closed under).

**Resolution: one milestone, cutover dead-last — because the objective gate (below) dissolves Creative's concern rather than overriding it.** Creative's fear is a *judgment-call* retirement debate leaking into and corrupting parity work. A mechanical gate removes the judgment call: "checklist incomplete → delete blocked, full stop." There is nothing to argue about during parity work. The pressure source only exists when the gate is a vibe.

**Creative's distinction is preserved as a hard internal phase wall, not a milestone seam:** **"Parity-complete"** is a named, gated checkpoint. No cutover slice may begin, and **no cutover discussion is permitted, until mutation/authority parity is proven** (slice 3). This keeps the clean conceptual boundary Creative wanted while denying the capability any place to sit undriven.

---

## Forcing function (LOCKED): greenscreen → roto

```
forge_is_greenscreen   (operator node, synchronous MCP perception)
        ↓  FilterNode( is_greenscreen == true )   (primitive node, in-process)
        ↓
forge_roto_ref         (operator node, synchronous MCP "make")
```

Live-verified at #60. DT's live capture confirms `roto_ref` is a **synchronous single round-trip**: call → full `DerivedHoldoutsArtifact` back (sequence_locator path + sha256 + channels), verdict `pass`, **no job handle, no submit/poll, no pending state**. This specimen is locked because:

- It forces **unified node dispatch** — an operator → primitive → operator chain the M1 executor (MCP-dispatch-plus-plumbing) cannot express. This is M2's equivalent of M1's fan-in vertical.
- It does **NOT** smuggle in submit/poll generation — roto is synchronous, so M2's generation-handling (submit/poll/cost/non-determinism) genuinely stays deferred to a later milestone.
- It does **NOT** pull in the authority chain — roto produces a matte **by reference** and stops. Durable pipeline-state mutation (register as a version) is the separate `forge_register_publish` step, which lands in slice 3.

---

## Slice order (LOCKED)

1. **Unified operator + primitive dispatch** — one executor dispatching both node kinds (operator→boundary, primitive→in-process). Stand up the **full compare harness** here — normalizer + dual-path runner + corpus scaffold (Seam C is slice-1 infrastructure).
2. **Primitive-node parity** — ⚠️ **STRUCTURAL RISK, not a dispatch checkbox.** Primitives are two different animals (see Seam D): **value-transform** primitives (filter/select/collect) operate on data, fit the static DAG, dispatch like operators — fine. **Control-flow** primitives change the *execution shape*: `foreach` is topology-expanding (`forge_bridge/graph/foreach.py:1`, its own word — N runtime iterations not known until the collection exists), and `if-gate` is subgraph pruning (`_engine.py:37`, via a `__if_gate_skip_next__` context flag in the linear loop). The M1 `GraphExecutor` is a **static topo-sort over a fixed `graph.nodes`** (`executor.py:72/94/112`) — it has **no mechanism for runtime expansion or conditional pruning**. So slice 2 must grow the executor's control model (dynamic expansion + conditional pruning) — arguably bigger than slice 1's unified dispatch. Flag and scope it as such.
3. **Mutations + authority parity** — THE ARCHITECTURAL GATE (see Seam B). preview→ratify→apply and `AssentRecord` semantics survive graph execution unchanged. *Parity-complete wall sits at the end of this slice.*
4. **Chain-text → GraphSpec** — the NL/chain-step surface compiles into `GraphSpec` instead of a linear step list.
5. **Planner / daemon reachability** — `GraphExecutor` on a real surface, **both paths live**. This is what gives parallel-run-compare teeth: compare on real traffic before any flip.
6. **Cutover** — corpus-wide compare green → flag flip → `GraphExecutor` becomes sole runtime → retire `run_chain_steps`.

Slice 5 (driven) **before** slice 6 (cutover) is deliberate: the engine must be on a real surface with both paths live before the flip, so the compare discipline runs against real traffic, not just fixtures.

---

## Seam A — Boundary admission criterion (the safety-relevant thing slice 1 changes)

M1's allow-list was `READ_PERCEPTION_OPERATORS` — **reads only**, generation rejected by default-deny. That was M1's read-only safety guarantee.

Admitting `roto_ref` widens the boundary. **Do not call the admitted class "makes"** — "make" sounds permissive and someone will later smuggle generation-like behavior through the read boundary on the strength of the word (Creative). Name it precisely:

> **Reference-producing synchronous operators** are admissible at the read boundary. Admission criterion (ALL required):
> 1. **no project/pipeline-state mutation**,
> 2. **no spend-authority path**,
> 3. **no async submit/poll lifecycle**,
> 4. **returns a bounded reference/artifact**,
> 5. **re-run-safe / idempotent — safe to replay under compare** (DT + Creative).

roto qualifies on all five: synchronous round-trip, returns a content-hash-addressed locator (`media_content_sha256` + sha-keyed path per the live capture, so same input → same artifact), no version registration, no spend path.

**Why criterion 5 is load-bearing (DT — Seam A and Seam C would otherwise contradict each other):** parallel-run-compare (Seam C) executes the chain through *both* paths, so an admitted reference-producing operator runs **twice**. A non-idempotent operator can't be double-executed (two roto invocations = two matte writes). The admission criterion must therefore name re-run-safety, and the compare strategy must be pinned:

> **Make-compare strategy:** double-execute **only** idempotent (content-hash-addressed) reference-producers. Anything else uses **run-once-record-replay**, never two live invocations.

**Hard rule:** any operator that mutates pipeline state — even synchronously — routes through the **authority chain**, never the read boundary. The allow-list must not grow past these five criteria without a ratify gate. If a future op fails any criterion (e.g. a synchronous op that *does* mutate state), it is a slice-3 authority case, not a boundary widening.

---

## Seam B — Executor stays an opaque assent-conduit; authority wraps it (the seam DT refuses to let slide)

**Grounding correction (live read, 2026-06-18).** DT's grep for `stage|commit|ratify` in `_engine.py` came back empty — true — but `AssentRecord` **is** imported and threaded:

- `forge_bridge/console/_engine.py:12` — `from forge_bridge.core.assent import AssentRecord`
- `:25` — `run_chain_steps(..., assent_record: Optional[AssentRecord] = None, ...)`
- `:58` — passes it straight down into `execute_chain_step`

So the current executor is not authority-*blind* — it is an authority-**conduit**. It carries an already-decided assent down to the step; it never mints, inspects, or decides ratification. This makes the mechanism/policy line *more* defensible, but the auditable guarantee must be stated precisely:

> **The executor carries `assent_record` as opaque payload — it never inspects, decides, or mints it.** preview→ratify→apply orchestration stays in `_operation_front.py` / `_chat_compile.py` / `handlers.py` / `core/assent.py` and simply hands assent to the graph path instead of to `run_chain_steps`. The "cannot regress ratify byte-for-byte" guarantee is then auditable as *the same orchestration code now calling `GraphExecutor`* — not as authority logic absorbed into a node.

**Regression risk (the line that does not move):** the moment a graph node starts *interpreting* `AssentRecord`, we have rebuilt the thing we are migrating, and the ratify guarantee stops being auditable. Slice 3 makes `stage`/`commit` graph nodes (dispatched like any primitive); the ratify orchestration stays *outside* the executor, wrapping it — the same mechanism-not-policy line held in M1 ("the orchestrator owns control flow, not meaning").

**Enforcement — make it grep-auditable in CI (DT):** "opaque conduit" is not an aspiration, it is a *precise description of existing `run_chain_steps` behavior* — it imports, takes, and forwards `assent_record` verbatim, and never reads a field, branches on it, or mints one. Lock that as a mechanically-checkable invariant: **the executor module must contain zero attribute-accesses or conditionals on `assent_record` — only forward it.** A CI grep over `forge_bridge/composition/` asserting no `assent_record.` access and no `assent_record` in a conditional is the strongest possible form of "cannot regress."

**Decomposition consequence for slice 6:** "Retire `run_chain_steps`" ≠ "retire the authority chain." Different code. The cutover retires the *executor*; the authority orchestration persists and simply calls `GraphExecutor` instead.

---

## Seam C — Parallel-run-compare is milestone-wide, with a provenance-normalizing comparator

**Rule (not a cutover tactic):** every parity specimen runs **both** paths —

```
run_chain_steps   ┐
                  ├─→  normalize → assert semantic equivalence
GraphExecutor     ┘
```

— and compares before the graph path is considered green. By the time Cutover (slice 6) starts, the compare harness and a growing corpus already exist. Cutover becomes a **confidence decision**, not a testing strategy.

**Equivalence is semantic-modulo-volatile-provenance.** Literal "assert identical output" cannot work: captures (greenscreen, roto) carry volatile provenance — `artifact_id`, `request_id`, timestamps, `content_hash`, `graph_event_id` — that differs every run. The comparator must **normalize those fields, then assert.** Without the normalizer, every compare fails on noise and the discipline collapses to eyeballing.

**The whole compare harness is slice-1 infrastructure, not late migration tooling (Creative).** The normalizer, the dual-path runner, and the corpus scaffold land in slice 1 so every subsequent parity specimen (slices 2–4) is born under compare. Treating it as cutover-era tooling defeats the milestone-wide rule — the corpus must already be growing by the time slice 5 puts both paths on real traffic.

**Note (DT):** the comparator's "volatile-provenance" normalization handles *noise*; it does **not** absorb *real* behavioral divergence. The failure-semantics gap below (Seam D) produces genuine divergence on error/clarify cases — that must be reconciled by making the paths behave identically, never by widening the normalizer to swallow it.

---

## Seam D — The cutover gate is objective (Parity-complete wall + mechanical delete gate)

The delete in slice 6 is blocked until **mechanically** earned, not until "it looks done":

1. **Suite-wide parallel-run-compare green** across the corpus.
2. **An explicit parity checklist**, every item ticked. The checklist is structured across three axes — node types, authority happy-path, and authority failure-path. Failure/decline parity is *not* optional polish; the paths diverge there for real, and an un-ticked failure row is an un-migrated behavior.

   **Node types** (the "primitive" cell is split — DT):
   - **operator** (synchronous MCP perception, e.g. `forge_is_greenscreen`)
   - **reference-producing operator** ("make", e.g. `roto_ref`) — under the Seam A criterion + make-compare strategy
   - **value-transform primitive** (filter / select / collect) — fits the static DAG
   - **control-flow primitive** (`if-gate` subgraph pruning, `foreach` topology expansion) — **gated on the slice-2 control-model extension; cannot be ticked until the executor grows dynamic expansion + conditional pruning**

   **Authority — happy path:** preview · ratify · apply · `AssentRecord` threading (opaque-conduit invariant, Seam B) — each proven byte-unchanged.

   **Authority — failure / decline path** (Creative + DT — the gap that bites slice 6 if skipped):
   - **preview rejected**
   - **ratify missing**
   - **assent invalid**
   - **unauthorized mutation**
   - **abort-on-first-error** — `run_chain_steps` (`_engine.py:64–99`) aborts subsequent steps and returns `CHAIN_STEP_FAILED` with the partial trace; `GraphExecutor` *propagates errors and keeps going* (the mechanism-not-policy choice verified in M1). **Different failure semantics → compare will diverge on error cases for real, not as volatile noise.** Reconcile by relocating abort *interpretation* into the orchestration (see redistribution note), not by widening the normalizer.
   - **mid-chain clarification** — `run_chain_steps` early-returns on `clarification_needed` (`_engine.py:65–77`, the reads-fence #77 group-by clarify path); `GraphExecutor` has no clarification concept. Same reconciliation: interpretation moves out to the orchestration.
   - **comparator mismatch** + **volatile-provenance normalization** themselves exercised (the harness must be proven to catch a real mismatch and to normalize the volatile set).

**Cutover redistributes interpretation out of the executor — "retire `run_chain_steps`" is NOT a 1:1 swap (DT).** Today `run_chain_steps` interprets errors and clarification *inline* (`:64`). Consistent with Seam B's principle, that interpretation belongs in the wrapping orchestration that reads the results map, not in the executor. So slice 6 **splits `run_chain_steps`' responsibilities**: execution → `GraphExecutor`, error/clarify/abort *interpretation* → the wrapping orchestration. Flag this redistribution explicitly in the seam design, or slice 6 discovers it the hard way.

**Parity-complete wall:** items 1–2 for everything *except* cutover itself constitute the "Parity-complete" checkpoint at the end of slice 3+. Cutover slices (5→6) do not open until that wall is cleared. This is the structural form of "no cutover discussion before mutation parity is proven."

---

## Out of M2 (deliberate, deferred)

- Generators' billable/async process-node semantics — submit/poll/cost/non-determinism (→ later milestone; the roto specimen is chosen precisely to keep this out).
- Cycles + the cycle→runs compiler (→ #66, [[AUTHOR-STILL-VIDEO-LOOP-FRAMING]]).
- The artist canvas / graph authoring UI.
- Competence-declaration + liveness gate (federation frontier, separate workstream).

---

## Carry-forward folded in / still open

- `#86` (real read-op specimen) — partly retired by locking the roto specimen; reconfirm the multi-input `metadata.scalars` last-wins merge question survives into slice 1–2.
- P4a **sequential dispatch** — independent fan-in nodes still run serially; lift to concurrent only once expensive generative work makes fan-in worth parallelizing (M2 stays synchronous, so no lift needed here).
- `#88`.

---

## Redline resolution (converged 2026-06-18)

- **Boundary call** — CONFIRMED (DT + Creative): one milestone, cutover-last, "Parity-complete" as a hard internal wall. The objective gate dissolves the flip-pressure worry.
- **Seam A** — TIGHTENED: renamed to *reference-producing synchronous operators* (Creative); five-part criterion incl. **re-run-safe/idempotent** (DT) tying it to Seam C; make-compare strategy pinned (double-exec idempotent only, else run-once-record-replay).
- **Seam B** — CONFIRMED as "opaque assent-conduit"; DT withdrew the weaker "authority-blind" framing. Enforcement added: CI grep-invariant (zero attribute-access / conditional on `assent_record` in `forge_bridge/composition/`).
- **Seam C** — ELEVATED to slice-1 infrastructure (Creative); normalizer handles noise only, never real divergence (DT).
- **Seam D** — EXPANDED: primitive cell split into value-transform vs control-flow (DT — `foreach`/`if` flagged as a slice-2 control-model extension, a structural risk); failure/decline parity row added (preview-rejected, ratify-missing, assent-invalid, unauthorized-mutation, abort-on-first-error, mid-chain clarification, comparator-mismatch, provenance-normalization); cutover-redistributes-interpretation note added.

**Next:** seam-design pass (the M2 equivalent of [[M1-WIRE-AND-RUN-SEAM-DESIGN]]), opening on the unifying principle above and the slice-1 unified-dispatch + compare-harness vertical.
