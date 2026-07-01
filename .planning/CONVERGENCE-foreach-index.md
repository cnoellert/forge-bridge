# Convergence — how a graph `foreach` body receives its iteration index

**Date:** 2026-07-01
**Subject:** Close the gate that forces the batch-author foreach offline test (PR #133) to pre-stamp `_position` on source items, so `foreach` bodies can author per-position `$n{width,start,step}` counters for real.
**Cadence:** 3 independent views (minimalist maintainer / contract architect / framing skeptic), redline round, converged lean. This doc is the record; the implementer brief is at the end.

---

## The dispute that settled it (redline)

View C's strongest attack: a stamp would "ride into `wrap_result` → `IterationResult.item` → provenance pollution."

**Adjudicated against C by direct read of `foreach_boundary.py:67–119`:**
- `:68` builds a **separate `payload`** from the item.
- `:84` hands the body that **payload** (`reenter(body_node, {body_port: item_input})`).
- `:111` calls `wrap_result(index=index, item=item, …)` with the **original, untouched `item`**.

So stamping the *payload* reaches the body but never touches the provenance envelope. C attacked a stamp-on-`item` that nobody proposed. The pollution objection fails against the payload stamp.

---

## Converged positions

### Q1 — Where does the ordinal live, and who authors it?
**Lean:** A **reserved-namespace key authored inside `ForEachNode.iteration_payload`** — `_foreach = {"index": <int>}`. Not a boundary side-stamp; not a bare top-level `_position`.

- **B won on authorship.** Stamping from the *boundary* makes the boundary a second author writing into a dict the source produced — a "two authors of one representation" violation ([[project_one_canonical_author_per_representation]]). `iteration_payload` is where `foreach` *already re-authors the payload*, so the index belongs there and `foreach` is the sole author. The ordinal is already computed unconditionally (`enumerate`, `foreach_boundary.py:67`) — this exposes the int we already hold, symmetric with `IterationResult.index` (`foreach.py:40`) which already publishes it on the **output** side.
- **A's surviving refinement:** a reserved *sub-dict* (`_foreach: {…}`), not a flat key, so future per-iteration context (`total`, `is_first`, `is_last`, `source_key`) lands as additive keys with zero new ports or payload renegotiation.
- **Field named `index`** (not `ordinal`) to match the existing output-side vocabulary (`IterationResult` serializes `"index"`, `foreach.py:47`). The ordinal-not-timeline meaning rides on the reserved namespace + docstring.

### Q2 — Does the body read that index *as the counter's position*? [STRUCTURAL SEAM]
**Lean:** Yes for now — **but the key is named `index`, never `position`, and the ordinal→timeline identity is a declared upstream-ordering contract, not a silent coincidence.**

- **C is load-bearing here.** C proved from the CLI that `expand_counter(template, i)` is correct only because `i = enumerate(timeline_sorted(segs))` (`verbs.py:203,263`) — **the sort earns the identity `index == timeline position`.** `foreach`'s `enumerate` is *arrival order*; nothing in the graph enforces the feeding collection is timeline-sorted. Reading `foreach`'s index as the counter number is right *only under an upstream ordering guarantee*.
- **The cheap, non-negotiable insurance (all three views endorse):** naming. Call it `_foreach["index"]` (ordinal), never reuse `_position`; put a comment at the body read that ordinal-as-counter-position is valid *only* under an upstream timeline-sort. Naming blocks the silent weld regardless of how the seam below resolves.

#### The seam
C wants timeline-ordering made a **visible upstream position-annotator node** (`_timeline_position` as first-class graph work, per [[project_representation_transforms_first_class_nodes]] / [[project_graph_represents_work_not_decisions]]); the body reads *that*, and `foreach`'s index is demoted to progress/provenance only. A/B are content with `foreach`'s index + a *declared/asserted* ordering contract at the `foreach` input edge (C offered this as its own fallback — "convert the hidden invariant into a checked one").

**Lean:** Ship the index-in-payload now (closes the gate, unarguable). **Do NOT build the annotator node yet** — we don't yet know whether the resolution-front's `select`/`collect` feeding the live collection *already* emits timeline order. If it does, the node is redundant and the right move is a cheap assertion at the `foreach` edge; if it doesn't, *then* the node earns its place. Building it now risks redundancy or relocating the conflation upstream under a vaguer name (C conceded this risk). Cheap to add later; a wrong node-type now (vocabulary + admission + boundary) is expensive to unwind.

---

## Intentionally unbound
- **Where timeline-ordering authority lives** (assert-at-edge vs. dedicated position-annotator node) — unbound pending the **live collection source being wired**. Re-open trigger: inspect whether the `select`/`collect` feeding `foreach` emits timeline-ordered items. Yes → assert the invariant at the `foreach` input edge. No → build C's position-annotator node. This inspection is part of live cutover anyway.

## Rejected
- **`collect` assigns the counter numbers** — architecturally impossible here: `collect` runs *after* every body executes (`collect.py:59`), but the rename name is authored *inside* the body; a number that only exists at collect-time can't feed a name already built.
- **Typed `IterationInput` envelope / second body input port (1b)** — structurally blocked: every primitive body is invoked `.run(upstream.output)` with a bare payload dict (`primitive_boundary.py:114/159`); a typed envelope changes that calling convention for filter/if_gate/select/collect *and* breaks `infer_topology` (the body stops type-checking as a normal item-shaped step). Disproportionate for one integer, and ports validate topology, not semantic identity — a typed `index:int` port wouldn't even catch the ordinal/timeline mismatch it claims to prevent.

---

## Invariants (all three views proved independently)
- `composition/executor.py` stays **byte-for-byte stable** — zero `foreach`/`enumerate`/`index` references; the iteration loop lives entirely in `ForeachBoundary`. Edit set never includes it.
- `foreach` stays `no_state_mutation=True` (authors deltas, never applies) — the payload is a throwaway copy `iteration_payload` already builds; the source items are never mutated.
- `forge_bridge.__all__` stays 19.

---

## Implementer brief (run AFTER PR #133 merges — targets the merged base on `main`)

**Goal:** Retire the offline `_position` scaffold from #133. Make `ForEachNode` author its iteration index into the payload so `RenameDeltaNode` reads a real value; fix the two-author violation; keep `executor.py` byte-stable.

**Changes:**
1. `forge_bridge/graph/foreach.py`
   - Add a reserved key constant, e.g. `FOREACH_META_KEY = "_foreach"`.
   - `iteration_payload(self, data, item, *, index: int)` — after building the payload copy (existing body), if the payload is a dict, set `payload["_foreach"] = {"index": index}`. Foreach is the sole author. Docstring: this is the **ordinal** iteration index (arrival order), NOT timeline position; correctness of any position-consumer depends on an upstream timeline-ordering guarantee.
   - Confirm `_looks_like_manifest`/`_MANIFEST_MARKERS` and `infer_topology` do not key on `_foreach` (so classification/topology are unaffected).
2. `forge_bridge/composition/foreach_boundary.py:68`
   - `payload = foreach.iteration_payload(upstream.output, item, index=index)` (index already in hand from `:67`).
3. `forge_bridge/graph/editorial_delta.py`
   - `_item_position` reads `item.get("_foreach", {}).get("index", 0)`. **Rename off `_position`.**
   - Inline comment at the read: ordinal-as-counter-position is valid ONLY under an upstream timeline-sort guarantee ([[feedback_inline_authority_boundary_guards]] style).
4. `tests/composition/test_m2_batch_author_foreach.py` (and any test that pre-stamps `_position`)
   - Stop pre-stamping `_position` on source items — the boundary now authors the index for real.
   - Keep the n/n+1 byte-identity parity assertions green.
   - **Add a negative test:** `foreach` over an un-annotated/unordered collection must NOT silently emit plausible-but-wrong counter numbers (the guard against the ordinal/timeline weld).

**Constraints to verify before done:** `git diff --stat` must NOT list `composition/executor.py`; `forge_bridge.__all__` == 19; no new deps; `foreach` admission flags unchanged; full `tests/composition/` + `tests/cli/` green.

**Explicitly OUT of scope (unbound seam):** the timeline-ordering authority decision (assert-at-edge vs. annotator node). This slice only makes the index real and ordinal-honest. The ordering seam re-opens at live cutover.
