# M2 Slice 1 — Unified Dispatch + Compare Harness — Seam Design (Orch draft)

**Date:** 2026-06-18 · **Status:** **converged** (Orch draft → DT + Creative redline → folded). Ready for the slice-1 phase plan.
**Parent:** [[M2-PARITY-AND-CUTOVER-FRAMING]] (converged) · **Engine:** [[M1-WIRE-AND-RUN-SEAM-DESIGN]].
**Scope:** slice 1 only — unified operator+primitive dispatch, the boundary admission widening, and the compare harness as slice-1 infrastructure. Slices 2–6 get their own seam passes (slice 2's control-model extension especially — see framing).

## Top-line principle (inherited, governs every seam below)

> **The executor interprets nothing. It executes the graph. It does not decide authority, interpret assent, or interpret error policy. Those belong to orchestration. The executor remains a runtime, not a policy engine.**

All four slice-1 decisions fall out of this one sentence (Creative's decision-map):

| concern | lives in |
|---|---|
| classification | **registry** (grammar → registry → reject) |
| admission | **declaration** (sibling declares; bridge records) |
| comparison | **outcomes** (terminal payload + status vector) |
| authority | **orchestration** |
| assent | **orchestration** (executor carries/forwards, never inspects) |
| abort semantics | **orchestration** |

This is the same rule DT and Creative both surfaced: S1-C's abort-semantics dependency and S1-D's grep-invariant are the *same principle twice* — D guards the assent half in CI now; C surfaces that the error-interpretation half must live in orchestration for the comparator to even work.

In slice 1 this has a concrete consequence the grounding confirms: `GraphExecutor.run` is a pure topo-walker that hands every node to a **single `dispatch` callable** (`executor.py:68,118`) and propagates non-`ok` results unchanged (`executor.py:36–39`). Unified dispatch must therefore be built **in the dispatch layer, not the executor** — the executor stays untouched in slice 1.

---

## The slice-1 forcing vertical (acceptance specimen)

```
forge_is_greenscreen   (operator → MCPToolBoundary)
        ↓  FilterNode( is_greenscreen == true )   (primitive → in-process)
        ↓
forge_roto_ref         (reference-producing operator → MCPToolBoundary)
```

Slice 1 is green when this graph runs end-to-end through one executor via unified dispatch, and **both paths** (`run_chain_steps` legacy + `GraphExecutor`) produce semantically-equal output under the compare harness. The middle (primitive) node here is a **value-transform** filter — it fits the static DAG and needs no control-model extension, so it is in-scope for slice 1. (`foreach`/`if-gate` are slice 2.)

---

## Seam S1-A — Unified dispatch is a *router* `DispatchFn` (executor untouched)

**Grounding.** `DispatchFn = Callable[[NodeSpec, dict[str, NodeResult]], Awaitable[NodeResult]]` (`executor.py:62`). `MCPToolBoundary.dispatch` is the only implementation today and it rejects any non-MCP operator with `UnsupportedCompositionNodeError` (`boundary.py:68–71`). A primitive (`filter`) is not an MCP tool — it computes in-process.

**Seam.** Introduce a `UnifiedDispatch` composing two dispatchers behind the *same* `DispatchFn` signature:

```
UnifiedDispatch(operator_dispatch=MCPToolBoundary.dispatch,
                primitive_dispatch=PrimitiveBoundary.dispatch)
  async def dispatch(node, resolved_inputs) -> NodeResult:
      kind = classify(node)
      return await (primitive_dispatch if kind is PRIMITIVE
                    else operator_dispatch)(node, resolved_inputs)
```

The executor's `for node_id in topo_order: await self._dispatch(...)` loop is **unchanged**. Routing policy lives in `UnifiedDispatch`; both sub-dispatchers still *mint* `NodeResult` (the boundary-mints invariant from M1 holds for primitives too — `PrimitiveBoundary` mints with `run_id`/`artifact_id`/`source_artifact_ids` exactly as `MCPToolBoundary` does at `boundary.py:88–104`).

**RESOLVED (DT + Creative): registry-derived, NOT explicit `NodeSpec.kind`** — but the shorthand "registry-derived" is incomplete. The real model is a **fail-closed two-recognizer chain**:

```
grammar recognizers   (primitives: is_foreach_step / is_if_step — already how they're identified)
        ↓ else
registry classification   (operators, incl. the Seam-A admission registry)
        ↓ else
REJECT   (unknown operator_id fails closed — matches Seam A default-deny)
```

Order is load-bearing: **grammar first → registry lookup → else reject.** An unclassified op must **never** default to "operator."

**Why not explicit `kind` (DT's Phase-3 grounding):** the compiler is structurally operator-agnostic; an explicit `NodeSpec.kind` would force the compiler to know "`forge_roto_ref` is a make" — exactly the operator-knowledge that must stay *out* of it. Registry-derived keeps classification where operator-knowledge already lives (the dispatch/boundary layer, per Phase 4b).

**Two amendments folded:**
1. **One source of truth.** The classification registry and Seam A's admission allow-list (S1-B) are the **same table** — an op's classification *and* its admissibility live in one registration declaration. Two tables would drift (an op classified "read" but not admitted, or vice versa).
2. **Provenance records the resolved class.** Runtime classification stays registry-derived (clean compiler), but each executed `NodeResult` **records the class it actually resolved to**, so a persisted `GraphSpec` replayed months later against a drifted registry is auditable against what *actually* ran — not what the registry says now.

---

## Seam S1-B — Boundary admission becomes a registry carrying the Seam-A criterion + idempotency

**Grounding.** `READ_PERCEPTION_OPERATORS = frozenset({"forge_is_greenscreen"})` (`boundary.py:32`); `allowed_operators` is constructor-injectable (`boundary.py:48`). Admitting roto is *not* "add a string to the set" — the framing's Seam A makes admission a **5-criterion policy**, and Seam C needs a per-operator **idempotency** bit to choose its compare strategy.

**Seam.** Replace the bare frozenset with an **admission registry** — `{operator_id: AdmissionClass}` — where `AdmissionClass` records:

```
AdmissionClass:
  reference_producing: bool   # returns a bounded reference/artifact
  idempotent: bool            # content-hash-addressed → safe to double-exec under compare
  # (the other three criteria — no mutation / no spend / no async lifecycle —
  #  are admission preconditions, asserted at registration, not stored flags)
```

- `forge_is_greenscreen` → `reference_producing=False` (pure perception), `idempotent=True`.
- `forge_roto_ref` → `reference_producing=True`, `idempotent=True` (the live capture shows a `media_content_sha256` + sha-keyed locator: same input → same artifact).
- Membership absence = default-deny (unchanged from M1).

`MCPToolBoundary.dispatch`'s gate at `boundary.py:68` checks registry membership; the `idempotent` bit is read by the **compare harness** (S1-C), not by dispatch — dispatch stays mechanism. **Hard rule preserved:** any operator failing a precondition (mutates state / has a spend path / has an async lifecycle) is rejected here and routed to the slice-3 authority chain, never admitted.

**RESOLVED (DT + Creative): assert at registration — but assert the *declaration*, not the *truth*.** This is the load-bearing honesty correction. Bridge **cannot** mechanically verify "no pipeline-state mutation" or "idempotent" — those are semantic properties of the **sibling tool's implementation, which lives in another repo**; bridge can't prove them from a schema. So registration fails closed iff an op is admitted **without explicitly declaring** all four properties (synchronous / returns-reference / no-state-mutation / re-run-safe). That is a real win — it turns silent allow-list inclusion into a conscious, auditable per-op contract act — but the doc must be honest:

> Registration asserts the **declaration's presence**, not the declaration's **truth**. Truth is a sibling responsibility ([[project_federation_facts_judgment_spine]] — the sibling asserts the fact; bridge records it) and gets real verification when the **#86 specimen** lands. Do not overclaim registration as behavioral verification.

---

## Seam S1-C — Compare harness (slice-1 infrastructure: dual-path runner + normalizer + corpus)

**Grounding.** Legacy path: `run_chain_steps` returns a dict body via `response_body(...)` carrying a `chain` trace + `step_index` (`_engine.py:33,70–`). Graph path: `GraphExecutor.run` returns `dict[str, NodeResult]` (`executor.py:71,120`). These are different shapes — the harness must project *both* onto a common comparison surface.

**Seam — three components, all land in slice 1:**

1. **Dual-path runner** — given a specimen (chain-step text + its compiled `GraphSpec`), execute both paths and capture both raw outputs. For an admitted **non-idempotent** operator this runner uses **run-once-record-replay**; for **idempotent** operators it double-executes live (the make-compare strategy from the framing, keyed off `AdmissionClass.idempotent` from S1-B).
2. **Provenance normalizer** — strip/canonicalize the volatile set before asserting: `artifact_id`, `request_id`, timestamps, `content_hash`/`media_content_sha256`, `graph_event_id`, `run_id`. Bake the volatile-field list into one named constant so the set is auditable and grows in one place.
3. **Equivalence projection + assert** — project both outputs to a *semantic result* (the terminal payload + status + abstention/error reason, modulo volatile provenance) and assert equality. **The normalizer absorbs noise only; a real behavioral divergence (e.g. the slice-3/Seam-D error-abort difference) must fail the compare, never be normalized away.**

**Corpus scaffold** — an append-only specimen registry (mirror the atomic-append-JSONL pattern bridge already uses for its corpora, but **named distinctly** — not coupled to the comprehension or divergence corpora). Slice 1 seeds it with the greenscreen→filter→roto specimen; every later parity specimen appends. By slice 5 the corpus is the parallel-run-compare evidence base.

**RESOLVED (DT + Creative): gate on terminal-payload + status-vector; intermediates are diagnostic, not a gate.**

The decisive grounding: the two paths produce **different intermediate representations** — `run_chain_steps` emits a `chain_trace` of `{step, result}` threaded via `__previous_result__`/`extracted_context` (`_engine.py`); `GraphExecutor` emits a `node_id → NodeResult` map (`executor.py:71`). A full-intermediate equality gate would require a **translation layer** between those shapes — and then you are gating on the *translation's* correctness, which can mask or fabricate equivalence. **Do not certify the translation.**

- **Gate:** terminal-payload + per-node status-vector. For slice 1 this is *sufficient*, not merely pragmatic — the forcing function is **linear**, so the terminal payload is a pure function of all intermediates; terminal-equality + status-vector-equality is a strong signal and the "same-terminal-via-divergent-intermediates" blind spot is small for a linear chain.
- **Diagnostic:** capture intermediates as a logged artifact (not gated), so a failed terminal-compare can be *localized* without having gated on a translation.
- **Slice-2 revisit (flagged):** once graphs branch/fan-in, "the terminal" becomes **multiple sink nodes** — the comparator must grow to compare all sinks + a node-identity-mapped status vector. Linear slice 1 gives a clean 1:1 step↔node mapping; the DAG will not. This is a named carry-forward to the slice-2 seam pass.

**LOAD-BEARING DEPENDENCY the doc must state (DT) — the status vector diverges on error cases *by design* unless reconciled.** `run_chain_steps` aborts-on-first-error (`_engine.py:64` — downstream steps = **not-run**); `GraphExecutor` **propagates** (downstream = **run-with-error-input**, `executor.py:36–39`). A step-2-errors chain gives legacy `[ok, error, NOT_RUN]` vs graph `[ok, error, ran]`. The comparator therefore works **only if the orchestration wrapping `GraphExecutor` replicates abort-on-first-error** — which, per the executor-interprets-nothing principle, is *exactly where abort semantics belong anyway*. **Pin it:** S1-C's comparator implicitly requires the wrapping orchestration's abort behavior to match the legacy path, or every error-path compare fails on a difference that is real, not noise. This is the orchestration-side half of the principle S1-D guards in CI.

---

## Seam S1-D — Plant the assent-conduit grep-invariant now (RESOLVED: plant in slice 1)

Strong agreement (DT + Creative): guards are cheapest to plant when the thing they guard is already true. Right now it is **trivially** true — the M1 `GraphExecutor` does not even take an `assent_record` param yet (reads-only, no authority). Plant the guard at slice 3 instead and slices 1–2 could bake in an inspection *before* the guard arrives, forcing a retrofit or a weakened guard. Plant now.

**SCOPE CORRECTION (DT) — scope to `executor.py`, NOT all of `forge_bridge/composition/`.** The earlier draft (and the framing's Seam B line) said "anywhere in `composition/`" — that is wrong: the **boundary legitimately interprets tool results** (`boundary.py:153–263` decode/status/reason logic), so a blanket `composition/` ban would either false-positive on the boundary or have to be weakened. The invariant belongs on the **executor module specifically**:

```
# CI invariant, scoped to forge_bridge/composition/executor.py:
#   executor MAY carry assent      (param)
#   executor MAY forward assent    (forwarded-arg)
#   executor MAY NOT inspect assent
# Mechanically: zero `assent_record.<field>` accesses, zero conditionals on `assent_record`.
```

Trivially green from day one (executor has no `assent_record` today); bites the instant slice 3 introduces an inspection. That makes Seam B's "cannot regress" a **CI fact, not a doc promise.** (Contrast `_engine.py:12,25,58` — the legacy conduit this models: imports, takes, forwards verbatim; never reads a field.)

> **Propagated delta:** the parent framing's Seam B enforcement line is corrected to the same `executor.py` scope — see [[M2-PARITY-AND-CUTOVER-FRAMING]] Seam B.

---

## Out of slice 1 (deferred to their own seam passes)

- `if-gate` / `foreach` and the executor **control-model extension** (dynamic expansion + conditional pruning) → slice 2, its own seam pass (flagged structural risk in the framing).
- `AssentRecord` threading + preview/ratify/apply parity → slice 3.
- chain-text → `GraphSpec` compilation → slice 4.
- planner/daemon reachability → slice 5; cutover gate + redistribution → slice 6.

---

## Redline resolution (converged 2026-06-18)

- **S1-A** — registry-derived, RESOLVED with sharpenings: fail-closed **grammar → registry → reject** (never default to operator); classification + admission are **one table**; executed `NodeResult` records the **resolved class** for replay-audit. Explicit `kind` rejected (would corrupt the operator-agnostic compiler).
- **S1-B** — assert-at-registration, RESOLVED with the honesty correction: registration asserts the **declaration's presence**, not its truth (cross-repo semantic properties bridge can't verify); truth rides the sibling contract + the #86 specimen.
- **S1-C** — RESOLVED: gate on **terminal-payload + status-vector**; intermediates are **diagnostic-only** (a full-intermediate gate would certify a translation layer). Pinned dependency: the wrapping orchestration **must replicate abort-on-first-error** or every error-path compare diverges for real. Slice-2 revisit flagged (multi-sink comparator).
- **S1-D** — RESOLVED: plant now, **scoped to `executor.py`** (not all of `composition/` — the boundary legitimately interprets); param-or-forwarded-only, zero field-access/conditional. Delta propagated to the framing's Seam B.

**Next:** slice-1 phase plan (unified-dispatch router + admission registry + compare-harness vertical), with the greenscreen→filter→roto specimen as the acceptance gate.
