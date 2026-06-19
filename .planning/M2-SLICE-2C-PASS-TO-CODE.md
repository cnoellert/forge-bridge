# M2 Slice 2c — Pass-to-Code — multi-input merge (deliverable fan-in)

**Date:** 2026-06-18 · **Status:** converged → pass-to-code · **Base:** `main 2341ef5`+ (cut a feature branch).
**Parents:** [[M2-SLICE-2-SEAM-DESIGN]] §S2-C (deferred multi-sink + reduction policy) · [[M2-SLICE-2B-PASS-TO-CODE]] (the substrate + comparator this extends).
**Cadence:** Orch framing → Creative + DT redline → grounded on the real op → converged. Examples are **reference shapes, not rewrite mandates.**

## What 2c is — and the structural shift to state first

The slice-2 reframe extends to **topology**: fan-in and fan-out are **already executor-native** (`executor.py:114` resolves *all* incoming edges by port). So 2c does **not** grow the executor. It proves the **multi-input merge** on a **real op** — `forge_assemble_deliverable_package` (5 required distinct artifact inputs → one `DeliverablePackageArtifact`).

> **The oracle shift (Q1 doctrine, third application — read this before writing tests):** a true fan-in **does not linearize** — legacy chains are linear and have no merge, so there is **no legacy counterpart to compare against**. 2c is therefore the first slice whose validation is **intra-graph self-consistency**, NOT cross-path parity:
> - **sink correctness** — the merge output's `package_content_sha256` + `manifest_sha256` equal the **captured real** deliverable output after identity canonicalization;
> - **declared reduction** — any required input non-flowing → the merge short-circuits;
> - **topology/lineage** — the merge mints one output with `source_artifact_ids` from **all** upstream inputs.
>
> This is *"oracle ended, proof changed"* — not *"oracle absent, anything goes."* Do **not** try to build a legacy `legacy_runner` for the deliverable; there isn't one.

**Value-blind edges hold (#86 unbound):** the merge proves **topology + reduction + lineage** — all value-blind. The five input artifacts are passed as **static `config["arguments"]`** (lifted from the captured fixtures); the five edges carry **lineage only**, exactly as the greenscreen→roto specimen wires roto's args from config and the edge for lineage. Using the inputs *as data-kwargs* is **#86, deferred** as it is on every edge.

## Acceptance vertical (2c is green when this passes)
```
artifact_A ─┐
artifact_B ─┤
artifact_C ─┼─→ forge_assemble_deliverable_package  (MERGE — 5 required input ports)
artifact_D ─┤
artifact_E ─┘
```
- **all flow:** merge dispatches; output content hashes equal the captured sh010 deliverable after canonicalization.
- **any required non-flowing** (drop/skip one input): merge **short-circuits** (deliverable op never dispatched); reduction = `fail`/any-skip.

## Tasks (ordered; one atomic commit each)

### T1 — stage the sh010 fixtures (DT's lift; grounding prerequisite)
Lift from **one coherent** forge-vision `first_light` sh010 run (`forge-vision/out/first_light/packages/deliverable_*/`) into a bridge capture under `tests/composition/fixtures/`:
- the real `DeliverablePackageArtifact` **output** (parity anchors: `package_content_sha256`, `manifest_sha256`, `shot_id=sh010`, plate/holdouts/producer blocks);
- the **five input** artifacts — `NormalizedPlateArtifact`, `DerivedHoldoutsArtifact`, 3× `PackagedReferenceArtifact` (also in forge-vision `tests/test_phase4c_artifacts.py`).
**One run only** — the op cross-validates `shot_id`, so inputs assembled from different runs fail that gate (captured-not-assembled, with teeth). **Lift, do not re-type the `to_dict`s.**

### T2 — admit `forge_assemble_deliverable_package` (6th op) — **PROVISIONAL, #86-flagged**
`admission.py`: roto-mirror profile — `resolved_class="mcp.synchronous_make"`, `synchronous=True`, `returns_reference=True`, `no_state_mutation=True`, `idempotent_result=True` (content-idempotent on the two hashes).
- **Mandatory comment, do not omit:** this op `commit_staged_packages` an entire directory (plate + holdouts EXR + 3 JSONs + manifest) — a far larger side-effect than roto's single matte file. `no_state_mutation=True` **rides #86's permissive reading** (no *canonical-project-state* mutation ≠ no filesystem side-effect). **Flag the admission as provisional-pending-#86**: if #86 resolves toward "side-effect = mutation," this op *and* roto flip to `no_state_mutation=False`. Do not let this slice silently ratify the permissive reading.

### T3 — multi-input merge dispatch + lineage from all N
The MCP boundary already dispatches by `operator_id`; a node with five input ports gets all five resolved by the executor. Ensure the minted merge `NodeResult.source_artifact_ids` draws from **all** resolved upstream inputs (forward-only lineage from every branch). Args come from `config["arguments"]` (value-blind).

### T4 — reduction policy: **node-declared, build only the `fail`/any-skip arm**
Move the reduction from the wrapper-global accidental any-skip to a **node-declared policy** (Creative: *reduction belongs to the merge node; requiredness informs it, does not determine it*). For 2c implement only **`fail`/any-skip** — the sole arm with a real referent (the deliverable op hard-fails on any missing required input; it has **zero** optional inputs). The wrapper/merge reads the node's declared policy (default `fail`/any-skip).
- **Name `degrade` and `omit-continue` as declared values, deferred-unbuilt** — `degrade → NodeResult.partial` ("proceed honestly, declare compromise"); `omit-continue → all-skip-tolerant`. **Trigger:** a real op with a *flowing optional* input (forge-vision v0.2 `preview`, or a second merge consumer). Measure-first: name the policy surface, build only the grounded arm.

### T5 — comparator: deliverable self-consistency + the presence≠correctness firewall
Extend `normalize_terminal_output` for the deliverable's nested volatile paths (roto pattern — strip/canonicalize `artifact_id`, `deliverable_id`, `package_root.path`, `assembly_run.request_id`, and each of the five `*_ref.artifact_id`). Validation = the two content hashes equal the captured output after canonicalization.
- **Firewall — do NOT conflate two failure modes:** `any-skip` governs **flow/presence** (is each input flowing). The op *also* errors on `shot_id` mismatch with all five present — that is **content-validation** (merge runs, *then* errors), a separate failure mode. Reduction-skip and content-error must stay distinct in the comparator/status tokens.

### T6 — fan-in executor-native test (banked continuity move)
A ~10-line test: a multi-incoming-edge node through `GraphExecutor`, asserting `executor.py` byte-untouched vs `main`. Records the milestone-grade claim — *topology fan-in is executor-native* — as already-satisfied.

### T7 — deliverable fan-in specimen + self-consistency test
`parity_corpus.py`: a `DELIVERABLE_FANIN` case — five upstream source nodes emitting the captured input artifacts → the merge node. Two assertions: (a) all-flow → merge output hashes equal the captured deliverable; (b) drop one required input (mint it non-flowing) → merge short-circuits, deliverable op never dispatched. Lineage = all five sources on the merge envelope.

## Mandatory negatives / invariants
- `executor.py` **byte-untouched** vs `main` (assert).
- **Value-blind edges hold** — inputs are lineage-only; args from `config`. #86 stays unbound.
- Deliverable admission **flagged provisional-pending-#86** (the comment is load-bearing).
- Reduction policy **node-declared**; only `fail`/any-skip built; `degrade`/`omit-continue` named-deferred (not built).
- Comparator keeps **reduction-skip ≠ content-validation (shot_id) error** distinct.
- **No legacy `legacy_runner`** for the deliverable — validation is intra-graph self-consistency.
- `len(forge_bridge.__all__)` stays **19**; ruff clean; slice-1 + 2a + 2b tests green.

## Out of scope (do NOT build)
- **optional→all-skip** + **degrade/partial** reduction — no referent (defer, trigger named in T4).
- **Sink-set comparator generalization** (Q3) — nothing emits >1 sink yet; the single-`terminal_node_id` model stays until a real multi-sink producer appears.
- **#86 resolution** — flagged urgent by the packager, but its own arc; 2c proves topology/reduction, not the side-effect semantics.
- Mutations/authority (slice 3) · generation / async make (not admitted) · chain-text→GraphSpec (slice 4) · live reachability (slice 5).

## Instructions for code
1. **Branch:** confirm `git branch --show-current` is `main`, then cut a feature branch (planning-docs-on-main footgun, #95). Land 2c behind a PR.
2. **Order:** T1 → T7. T1 (fixture lift) is the grounding prerequisite; T4 (node-declared reduction) and T5 (the presence≠correctness firewall) are the load-bearing design.
3. **Do not `git add` `.planning/M2-SLICE-2C-*.md`** into the code PR.
4. **Report back:** all-flow self-consistency (hashes match capture); any-skip short-circuit (op not dispatched); fan-in lineage from all five sources; executor byte-untouched; reduction policy node-declared (only fail-arm built); comparator firewall (a shot_id-mismatch case tokens as content-error, not reduction-skip); suite count; `__all__` 19; ruff.
