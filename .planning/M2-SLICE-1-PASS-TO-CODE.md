# M2 Slice 1 — Pass-to-Code Brief — Unified Dispatch + Compare Harness

**Date:** 2026-06-18 · **Status:** pass-to-code (converged seam design → build brief).
**Parents:** [[M2-PARITY-AND-CUTOVER-FRAMING]] · [[M2-SLICE-1-SEAM-DESIGN]] (read both; this brief assumes their rulings).
**For:** a code session. Examples below are **reference shapes, not rewrite mandates** — match surrounding code idiom; don't conform existing files to the snippets.

---

## The one principle every task serves

> **The executor interprets nothing. It executes the graph. Authority, assent, error policy, abort semantics — all live in orchestration. The executor is a runtime, not a policy engine.**

Concretely for slice 1: `GraphExecutor.run` (`forge_bridge/composition/executor.py:71`) is a pure topo-walker that calls **one** `dispatch` callable per node (`:118`) and propagates non-`ok` unchanged (`:36–39`). **Do not modify `executor.py`'s control flow.** Everything below composes *around* it in the dispatch layer.

---

## Acceptance vertical (slice 1 is green when this passes)

```
forge_is_greenscreen   (operator → MCPToolBoundary)
        ↓  filter( is_greenscreen == true )   (value-transform primitive → PrimitiveBoundary)
        ↓
forge_roto_ref         (reference-producing operator → MCPToolBoundary)
```

Run end-to-end through **one** `GraphExecutor` via unified dispatch, AND prove `run_chain_steps` (legacy) and `GraphExecutor` produce semantically-equal output under the compare harness. Use the live `forge_is_greenscreen` round-trip already proven in M1 + the `forge_roto_ref` specimen (#60, synchronous, content-hash-addressed).

---

## Tasks (ordered; one atomic commit each)

### T1 — `NodeResult.resolved_class` (replay-audit provenance)
**File:** `forge_bridge/composition/node_result.py`
Add `resolved_class: str | None = None` to the `NodeResult` dataclass (`:27`). It records the class a node *actually* resolved to at dispatch (`"operator" | "reference_producing_operator" | "value_transform_primitive"`), so a persisted graph replayed against a drifted registry stays auditable (seam S1-A amendment). Optional field, defaulted — does **not** touch the 19 public symbols. Each dispatcher (T3, T4) stamps it when minting.

### T2 — The one classification + admission table
**File (new):** `forge_bridge/composition/admission.py` (NOT `core/registry.py` — that name is taken)
The single source of truth for both classification *and* admission (seam S1-A amendment #1 — one table, not two). Reference shape:

```python
@dataclass(frozen=True)
class AdmissionClass:
    resolved_class: str          # the NodeResult.resolved_class token
    reference_producing: bool
    idempotent: bool             # content-hash-addressed → compare may double-exec
    # The three hard preconditions (synchronous / returns-reference / no-state-mutation)
    # are asserted-present at registration, not stored as runtime flags.

def register_operator(operator_id, *, reference_producing, idempotent,
                      synchronous, returns_reference, no_state_mutation): ...
```

- **Assert the declaration, not the truth (S1-B):** `register_operator` must **fail closed** if any of `synchronous` / `returns_reference` / `no_state_mutation` is not explicitly passed `True`. Bridge cannot *verify* these (they're sibling-repo semantics) — it asserts the sibling **declared** them. Add a docstring saying exactly this; do not imply behavioral verification (truth rides the sibling contract + the #86 specimen).
- **Primitive partition:** register the value-transform primitives (`filter`, `collect`, `select`) by their canonical token. These are bridge-internal — no admission preconditions, `resolved_class="value_transform_primitive"`.
- **Seed operators:** `forge_is_greenscreen` (perception, `reference_producing=False`, `idempotent=True`), `forge_roto_ref` (`reference_producing=True`, `idempotent=True`).
- **`classify(node: NodeSpec) -> str` — fail-closed, grammar/primitive-first → operator → reject:** primitive-partition lookup first, then operator-partition, else raise (default-deny; an unclassified op must **never** default to `"operator"`).
- Reconcile `boundary.py:32` `READ_PERCEPTION_OPERATORS`: the admitted-operator set must now **derive from this table** (one source). Keep `MCPToolBoundary.allowed_operators` injectable, but its default comes from the table.

> **Slice-1 scope note (state it in the module docstring):** classification keys on `node.operator_id` because slice 1 has no text ingestion — chain-text→GraphSpec is slice 4. The `is_*_step(text)` grammar recognizers in `forge_bridge/graph/` are the *text front* that assigns the primitive token; they wire in at slice 4 against this same table. Slice 1 reserves the primitive token namespace so slice 4 adds the front without reclassifying.

### T3 — `PrimitiveBoundary` (the in-process dispatch half)
**File (new):** `forge_bridge/composition/primitive_boundary.py`
A `DispatchFn` (`async (NodeSpec, dict[str, NodeResult]) -> NodeResult`, matching `executor.py:62`) for value-transform primitives. For slice 1, dispatch `filter` via `FilterNode` (`forge_bridge/graph/filter.py:153`): build the `FilterPredicate` from `node.config`, run `FilterNode(predicate).run(<upstream output>)`, **mint** a `NodeResult` (status `ok`, `resolved_class="value_transform_primitive"`, `source_artifact_ids` from resolved upstream — same minting discipline as `MCPToolBoundary` at `boundary.py:88–104`).

> **Deliberate input-semantics split — document it in the docstring:** a value-transform primitive **consumes the upstream `NodeResult.output` as its data** (that's its whole job). This is *not* a violation of M1's value-blind-edge rule — that rule governs **operator** invocation-lowering (output = lineage only, kwargs from config). Primitives are the data-transform layer where lineage *is* the data. Keep the two boundaries' input semantics distinct and named.

### T4 — `UnifiedDispatch` (compose the two halves; executor untouched)
**File (new):** `forge_bridge/composition/dispatch.py`
One `DispatchFn` that routes by `classify(node)` (T2): primitive → `PrimitiveBoundary.dispatch`, operator/reference-producing-operator → `MCPToolBoundary.dispatch`, else the classify-raise propagates (reject). Stamp `resolved_class` on the minted result. The executor's loop is unchanged — it just receives this composed callable. Add a test asserting the executor object/code is untouched (the dispatch is injected, per `GraphExecutor.__init__` at `executor.py:68`).

### T5 — Compare harness (milestone infrastructure — a real module, not test-only)
**File (new):** `forge_bridge/composition/compare.py` (+ corpus in T6)
Three components (seam S1-C):
1. **Dual-path runner** — given a specimen `{chain_steps: list[str], graph: GraphSpec}`, run `run_chain_steps` (`forge_bridge/console/_engine.py:17`) and `GraphExecutor.run`, capture both raw outputs. **Make-compare strategy keyed off `AdmissionClass.idempotent`:** idempotent operators → double-exec live; non-idempotent → **run-once-record-replay** (build the branch even though every slice-1 specimen is idempotent, and add a test that a non-idempotent op takes it — assert the op is invoked exactly once via a spy).
2. **Provenance normalizer** — one named constant `VOLATILE_FIELDS = {"artifact_id", "request_id", "content_hash", "media_content_sha256", "graph_event_id", "run_id", <timestamps>}`; canonicalize before asserting. The set lives in **one place** so the comparator and future capture code share it.
3. **Equivalence: terminal-payload + per-node status-vector, modulo volatile fields.** Project the legacy `chain` trace's **last non-skipped step result** and the graph path's **terminal node `NodeResult`** to a common semantic surface; compare payloads + the status vector. **Intermediates are captured as a logged diagnostic artifact, NOT gated** (a full-intermediate gate would certify a translation layer between the two shapes — forbidden, S1-C).

> **Abort-on-first-error — the pinned dependency (S1-C), resolved for slice 1 as a dispatch-layer wrapper:** legacy aborts-on-first-error (`_engine.py:64`; downstream = NOT-RUN) but `GraphExecutor` propagates (downstream = run-with-error-input). To make the status-vector compare meaningful **and** keep the executor pure, the harness's graph-path runner composes an **`AbortOnFirstError` dispatch wrapper** around `UnifiedDispatch`: once it observes an `error` result, it short-circuits every subsequent dispatch (returns a harness-level *skipped* marker; do NOT invent a 5th `NodeResult` status — `skipped` is a status-vector token, not a `NodeResult` variant). This is real abort (no downstream side effects, matches legacy exactly) and it lives in orchestration (the dispatch composition), never in the executor or in `UnifiedDispatch`'s classifier. **This wrapper is the slice-1 home of abort semantics; it migrates into the real wrapping orchestration at slice 5.** ⟵ *If the room wants abort handled differently, this is the one design choice in the brief to challenge before code starts.*

### T6 — Parity corpus scaffold (distinctly named — never coupled to existing corpora)
**File (new):** `forge_bridge/composition/parity_corpus.py` → atomic-append JSONL at `~/.forge-bridge/parity/specimens.jsonl`.
Mirror the atomic-append-JSONL + versioned-schema pattern bridge already uses, but **named distinctly** — it is NOT the `comprehension/` (CR.1) corpus and NOT the v1.6 `corpus/` divergence instrument; never couple their schemas (binding constraint). Seed it with the greenscreen→filter→roto specimen. Every later parity specimen (slices 2–4) appends here; by slice 5 it is the parallel-run-compare evidence base.

### T7 — Plant the assent-conduit grep-invariant in CI (scoped to `executor.py`)
**File:** a CI check (test or lint rule).
Scoped to **`forge_bridge/composition/executor.py` only** — NOT all of `composition/` (the boundary legitimately interprets results). Assert: zero `assent_record.<field>` accesses and zero conditionals on `assent_record` in `executor.py`. Trivially green today (the executor has no `assent_record`); it becomes a tripwire the instant slice 3 introduces an inspection. This makes Seam B's "cannot regress" a CI fact (S1-D).

---

## Mandatory negative tests (M1 discipline — honest failure > plausible success)

- **Admission fails closed:** `register_operator` without one of the three precondition declarations → raises. (S1-B)
- **Unknown operator_id rejects:** `classify` on an unregistered op → raises; does **not** default to `"operator"`. (S1-A)
- **Abort parity:** a specimen whose middle node errors → graph status vector matches legacy `[ok, error, skipped]`, and the downstream operator is **never dispatched** (assert via spy — no side effect). (S1-C)
- **Make-compare routing:** a non-idempotent op routes to record-replay, invoked exactly once (spy). (S1-C)
- **One-table invariant:** the classify table and the boundary's admitted-operator set are the same source (assert derived, not two literals). (S1-A)
- **Value-blind preserved for operators:** an operator node still draws kwargs from config only, never from upstream `output` (the existing M1 negative test still passes; don't regress it).

---

## Out of slice 1 (do NOT build — deferred to their own passes)

- Control-flow primitives (`foreach`/`if_gate`) + the executor **control-model extension** (dynamic expansion / conditional pruning) → **slice 2** (its own seam pass; flagged structural risk). The multi-sink comparator also waits for slice 2.
- `AssentRecord` threading + preview/ratify/apply parity → **slice 3**.
- chain-text → `GraphSpec` compilation (the grammar text-front) → **slice 4**.
- Real wrapping orchestration on a live surface; real (non-harness) abort → **slice 5**.

---

## Constraints (binding)

- Public `forge_bridge.__all__` stays at **19** — untouched. New modules carry their own `__all__`. No new external libraries.
- `executor.py` control flow is **not** modified (T4 test guards this).
- Parity corpus is named distinctly and never coupled to `comprehension/` or `corpus/`.
- Negative tests are mandatory, not optional (above).

---

## Instructions for code

1. **Branch:** cut a feature branch off `main` (`548fd4d`); do not commit to `main` directly. Land the slice behind a PR (this project ships slices as PRs — see #82/#84/#85/#87/#90).
2. **Order:** T1 → T2 → T3 → T4 → T5 → T6 → T7. T1–T4 are the runnable vertical; T5–T6 are the compare infrastructure; T7 is the CI tripwire. Each task = one atomic commit with a green test.
3. **Test-first where it bites:** write the negative tests alongside the task they guard (admission-fail-closed with T2, abort-parity with T5). The acceptance vertical (greenscreen→filter→roto, both paths, semantic-equal) is the slice's exit gate — it should be the last test to go green.
4. **Ground, don't assume:** read `_engine.py` `response_body` (`forge_bridge/console/_recovery.py`) for the exact legacy output field names before writing the normalizer/projection — the `VOLATILE_FIELDS` set and the "last non-skipped step result" extraction must match real shapes, not these reference names.
5. **One design choice needs a nod before you start T5:** the `AbortOnFirstError` dispatch-wrapper approach (above). It's the brief's recommendation and it's principle-faithful, but it's the single place a reviewer might route abort differently. Flag it if you disagree; otherwise proceed.
6. **Report back** with: the acceptance-vertical compare result (green/diff), the negative-test outcomes, and the new public `__all__` count per new module (should not touch the top-level 19).
