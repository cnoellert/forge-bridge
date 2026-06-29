# Convergence — The Resolution Front (DCC pickers + cross-context lowering)

**Date:** 2026-06-29
**Trigger:** dogfood of the #124 web "rename a segment" renderer — operator: "the most user-unfriendly thing we've built." The tool deletes the *resolution front* of the chain (which noun, where it lives) and makes the human type identity by hand.
**Method:** 4 independent views (substrate-maintainer / operator-experience / federation-future / skeptic-YAGNI), each grounded in the live tree, then redlined against each other.

---

## The model being converged on (settled premises, not relitigated)

- A "tool" (rename, export-quicktimes) is a **MACRO over typed input ports**, not a monolith. The mutation is the easy *tail*; resolving the inputs is the missing *front*.
- **Nouns are context-scoped, not global.** Flame ctx = {desktop, batch, reel, sequence, segment, clip}; bridge canonical (`core/entities.py`) = {Project, Sequence, Shot, Asset, Version, Media, Layer, Stack}. `segment`/`reel`/`clip` are Flame-native, **not** canonical.
- A resolver = a **navigator doing contextual drill-down** over a context's containment tree, terminating when a node satisfies the required type. "picker" (full drill-down), "live-selection" (zero-step), and "procedural derivation" (a subgraph) are the **same machine**.

## Headline lean

**There is no navigator engine to build.** The resolution front is `select`/`filter`/`foreach` over a peer-sourced collection, riding the *existing* executor + `host_resolve` + `NodeResult.candidates`. The maintainer's **"dissolution, not deletion"** reframe won and absorbed the skeptic's "don't build an engine." The seed is small and rides the proven preview→ratify→commit rail. Federation's larger asks are **deferred with explicit triggers, not rejected** — with one load-bearing atom pulled forward.

---

## Per-question leans (who won + surviving counter)

### Q1 — Lowering shape: **translate-as-a-separate-visible-node; never picker-emits-canonical.** [STRUCTURAL SEAM]
When lowering *is* needed it's a visible graph node (the `delta_to_manifest` / `HostResolveBoundary` pattern, run the other direction), not folded into the picker.
- **Won:** maintainer + federation. Surviving reasoning: (1) one-canonical-author — N DCC pickers each emitting canonical = drift; (2) lineage requires the lowered value be an addressable node output (`NodeResult.artifact_id`), impossible if hidden in a picker; (3) reuses a proven pattern instead of a second competing one.
- **Operator's "fewer nodes / don't care" reclassified, not rejected:** node-count is a *renderer* concern (`verbs.py` already expands one slash-command into a multi-node subgraph). The renderer collapses the visual; the graph stays honest.
- **Why a seam:** this fossilizes how every future DCC picker is authored. Decided **now in principle** (pickers emit native + declare their map) even though the translate node isn't *built* until triggered — otherwise a peer ships a canonical-emitting picker meanwhile and fossilizes the wrong shape.

### Q2 — Match direction (canonical→native): **peer declares the map entries · contract owns the canonical vocabulary + declaration schema · bridge owns the resolver.**
Mirrors the existing registration spine. A peer's `CapabilityDeclaration` says "I emit native `segment`" + "`segment` lowers to `Shot`"; contract owns the canonical types + the open-vocabulary *shape* of that declaration; bridge matches mechanically via a reverse index (`by_canonical_output(T)`) + the existing `pass_3_insert_transforms`.
- **Won:** maintainer + federation (federation supplied the mechanism). Hard line: the native↔canonical strings in `entities.py` docstrings **stay documentation** — the day they become an executable dict in `composition/`, bridge is a Flame utility.
- **Skeptic honored:** the *resolver machinery* is deferred (below); the *declaration* is cheap + peer-side and can exist now as inert data.

### Q3 — Pick vs auto-collapse: **cardinality-1-of-required-type → collapse; >1 → abstain with candidates; 0 → error. Executor never asks; the surface re-enters.**
Unanimous. This is `select.py` as-is + `NodeResult(status="abstained", candidates=…)`. Operator's aggressive collapse (open sequence → never ask; live selection → zero-step; single child → auto-advance) *is* the cardinality-1 source case — safe because **collapse resolves the noun, never the act**; the preview→ratify gate is untouched.
- Two guardrails survived: (a) **no heuristics** — cardinality + exact type only; reject confidence/fuzzy creep (`select.py` stays exact-match); (b) federation's **pin** — a collapsed referent consumed downstream must be pinned for replay determinism (already true via the held-manifest at commit; load-bearing only once a peer consumes the referent).

### Q4/Q5 — Where it lives + rides substrate: **tree peer-declared · traversal = existing bridge executor · lowering-map = peer-declared entries (NOT centralized in contract).**
Net-new bridge surface is tiny: at most one "source/enumerate" dispatch_kind — likely just *admitting an existing MCP enumerator* (`flame_get_sequence_segments`), not new engine code. Federation self-corrected: the full map in the contract makes it a DCC-knowledge sink; contract holds vocabulary + schema, peers hold entries. Respects `__all__`=19, no deps, executor byte-stable.

### Q6 — Useful space: **transient now; shaped as an artifact so it can promote; no bridge-side store.**
Resolve live/transient (the open Flame state *is* the working set — operator's point), but ensure resolved referents are **node outputs with `artifact_id`, never inline config blobs** (federation's trap) so a future persistent working-set is additive. Skeptic's "kill it" + maintainer's "opt-in capture node later" both land here.

---

## The converged seed slice (segment → existing rename)

Offline-proven through `GraphExecutor`, executor byte-stable, rides the proven rail:

1. **Source/enumerate node** — admit the existing `flame_get_sequence_segments` + a current-sequence read as graph nodes (the DCC-specific, peer-owned, **read-only** picker — no ratify).
2. **`select` node** (exists) — narrow to the named/selected segment; cardinality-1 collapses; ambiguous abstains with candidates; surface re-enters.
3. **Existing rename rail** — `build_rename_delta → op → delta_to_manifest → preview → ratify → commit`. **No new translate node; no invented canonical `Segment`.**
4. **Operator's non-negotiable win** — auto-resolve the open sequence (kill the typed `Sequence` prompt) and default to the live selection, so the artist **types only the new name**. One **shared** resolver across CLI/web/NL (lift it out of `cli.interactive`'s private helpers — the n=3 extraction that #124/#126 trigger anyway).

**The one atom pulled from federation** so peer #2 isn't a rewrite, without building its engine: the resolved referent must be a **node output (`NodeResult`), not a renderer-passed dict or inline config.** That single constraint is where a future translate node attaches.

### Practical staging (live-Flame reality)
- **Open-sequence auto-resolve** = LOW risk (reachable via reflective exec). Ships first; drivable now.
- **Live-selection default** = HIGHER risk: Flame only hands selection to *menu-hook callbacks* (`_show_status(selection)`), not a free query. Needs live-Flame verification / possibly a hook-side selection capture. Follow-up, not a blocker on the first visible win.

---

## Intentionally unbound (with re-open triggers)
- **Visible referent-translate node + `pass_3` auto-insertion + `by_canonical_output` index** — unbound pending the **first graph that wires a resolved noun from one peer into another peer's operator input** (actual cross-peer mix-and-match). Shape decided (Q1/Q2); construction waits for a consumer.
- **`PortTopology` native/canonical discriminator** (so a canonical port rejects a native topology) — unbound pending the same trigger. The one load-bearing future invariant (the port system can't currently tell lowered from un-lowered), but enforcing it now guards nothing live.
- **Persistent canonical working-set** — unbound pending dogfood showing artists want to *pin* a set and click around, OR measured re-read latency too slow on a remote daemon.
- **Live-selection default for the picker** — unbound pending live-Flame verification of a selection read.

## Rejected (with reason)
- **Picker emits canonical directly** — makes a DCC peer the author of canonical semantics → N-author drift + boundary violation.
- **A `NavigatorEngine` / bespoke traversal class** — duplicates `executor.py` + `select`/`filter`/`foreach`. A tree-walker = rebuilding the executor.
- **Adding `Segment`/`reel`/`clip` to `core/entities.py`** — makes canonical Flame-shaped; kills federation by construction.
- **Centralizing the native↔canonical map in forge-contracts** — turns the contract into a per-DCC knowledge sink.

## Top risks
Native topology flowing cross-peer with nothing forcing a translate (the deferred `PortTopology` discriminator is the eventual fix); auto-collapse not pinned when a peer consumes the referent; a native↔canonical dict creeping into `composition/`. All guarded by keeping the seed native-through-to-host and the resolved value an artifact.

## Connection to live work
Merge #124/#126 (they're the tail substrate + the 2nd/3rd renderer that *triggers* lifting resolution into a shared field-kind). First real resolution-front slice = that lift + open-sequence/selection defaults. Separate defect surfaced by two views: **ratify is incoherent across surfaces** — its own small slice.
