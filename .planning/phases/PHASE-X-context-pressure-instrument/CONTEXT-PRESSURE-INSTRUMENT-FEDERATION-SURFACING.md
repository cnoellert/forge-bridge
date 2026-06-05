# PHASE X — Federation Context Surfacing · DT pass (→ Orch / Creative redline)

**Status:** SURFACING. No implementation authorized; no re-scope of Phase X proposed. Reframes what the instrument *is*, not what it *does*. Operator has agreed the read; this opens it to the room.
**Grounded against (live reads, 2026-06-05):** `forge-contracts/docs/adr/ADR-000-ecosystem-constitution.md`, `forge-contracts/docs/FEDERATION-PROOF-SEQUENCE.md`, `forge-contracts/src/forge_contracts/references.py` (the shipped contract), `forge-pipeline` @ `a3bf4ec` (Phase 32-03 menu-gate + Phase 34 HDEP), `forge-vision`/`forge-generators` READMEs + git. Base: forge-bridge `main @ 4beb90b` (clean).

---

## What changed in our understanding (not in the code)

We have been building Phase X embedded — measuring "does the desktop selection resolve the artist's deictic reference" as a chat-legibility instrument. Stepping out to the sibling repos reframes it: **forge-bridge is one peer in a contract federation, not a hub**, and **Phase X is the measurement pass for a contract the federation already shipped.** Nothing we built is wrong; the *frame* was one altitude too low.

## The constitution in one breath (ADR-000)

Forge = capability domains coordinated through versioned contracts, not shared implementation. **Bridge plans and remembers; it is NOT the implementation home for capabilities.** Pipeline owns execution truth (the `FORGE_PIPELINE_MENUS` gate is pipeline enacting peer-independence — menus-off, bridge-scriptable). Media bytes never transit bridge. No sibling reads another's internals. And the line that governs us: **"references are first-class objects with explicit success, failure, and ambiguity outcomes."**

## The keystone — we've been prototyping a shipped contract

`forge-contracts/references.py` v0.1 ships **`ReferenceResolution`**:

```
ResolutionStatus = Literal["resolved", "unresolved", "ambiguous"]
ReferenceResolution: status · reference · locations[] · candidates[] · reason_code · message
```

Our S4 analysis is this contract under another name. The map is **partial, not exact** (corrected post-redline — see footer):

| Phase X / capture-model (`_analysis.py`) | `ReferenceResolution` |
|---|---|
| Phase X (real, today — `_analysis.py`) | `ReferenceResolution` |
| S4 success (correct referent) | `status="resolved"` + `locations` |
| flag `wrong_resolution` / authored `wrong_referent` | `status="resolved"` but wrong — the ratify-caught case *(taxonomy drift between the two names is a real defect to reconcile)* |
| `unresolved_reference` | `status="unresolved"` |
| `unreachable_api` / `unreconstructable_guard` | `reason_code` (our honest-absence pattern) |
| **UNMEASURED — no S4 path today** | `status="ambiguous"` + `candidates[]` |

The last row is the redline's sharpest catch: **S4 cannot produce `ambiguous` today** — `_selected_value` (`_analysis.py:125`) returns a single scalar referent and the comparison is scalar `compiled != focus` (:186). The contract has a first-class `ambiguous` arm (ADR-000 §6) the instrument is currently *blind to*. That's a **finding** (a measurement hole to close), not a populated mapping — recording it honestly is the point.

The §2.3 op→(context, required-selection-type) map is the bridge-side *knowledge that produces* a `ReferenceResolution`. So Phase X is, unframed, **a measurement pass for bridge's reference-resolution quality** — same concern as the contract, one altitude down.

## Why this is load-bearing — the bottleneck (corrected, de-inflated)

Federation Proof Sequence: Phase 2 Vision ✅, Phase 3 Pipeline ✅, Phase 4 contract-stability ✅ (v0.1 stable), Phase 6 Generators in flight. **Phase 5 (Bridge Discovery) is capability-*family* routing** ("which declared capability satisfies this step?", FEDERATION-PROOF-SEQUENCE.md:131-154) — **orthogonal to deictic referent resolution; Phase X does NOT gate it.** Phase X strengthens the **Phase 7 E2E Demonstrator** (plan → invoke → record references/lineage) by making bridge's reference-resolution trustworthy, but it is not a hard gate on the proof sequence. The honest claim: chat/orchestration maturity is bridge's own long pole (the v1.7→v1.13→Phase X grind), and reference-resolution is a real part of it — but "the federation is blocked on this seam" was an overstatement. **Why this correction matters: inflating Phase X's federation importance is exactly the lever that would license hurrying a blind measurement. De-inflating it protects measure-first.**

## DT positions (strong, for redline)

1. **Do NOT re-scope Phase X.** The measure-first discipline and the blind Q3 threshold stand untouched. This is a vocabulary alignment, not a new mission (ruling iii holds). The instrument was correct; we now know its output has a name and a second consumer.
2. **If Q3's R clears BUILD, the resolver emits `ReferenceResolution`** — the shipped contract — not a bridge-internal shape. Recorded as §8 of the capture-model spec. This costs us nothing now and saves a parallel-vocabulary migration later.
3. **The §2.3 op→type map should become pipeline-declared capability metadata** (extending `CapabilityDeclaration`), consumed by bridge — not reverse-engineered from hook source. Our current derivation-by-reading-`forge_tools` is an ADR-000 boundary violation we should name as interim, not entrench. The output contract exists; the missing half is pipeline *declaring* "forge_rename requires a selected PySequence."

## Asks

**→ Orch (synthesis).** Does the `ReferenceResolution` mapping change how we frame the milestone — do we re-cast Phase X's close as "reference-resolution measurement pass" explicitly, so the federation read is legible to Phase 5/7? And does the bottleneck re-rank our sequencing — does the federation-level consumer raise the priority of the live re-capture + resolver-build relative to other bridge work, or is measure-first still the only gate that matters and urgency stays out of it?

**→ Creative (experience).** Two things land in your lane. (a) The contract's `ambiguous` + `candidates[]` path is an *experience affordance* — when "this sequence" matches ≥2 selections, do we design the disambiguation surface now (candidates offered to the operator) or defer it past the first resolver? (b) The op→type-as-capability-metadata move is partly yours — it's the federation-clean form of your hooks-as-ontology read (the hook already *is* the guard; the question is whether pipeline *declares* that guard as metadata vs. bridge re-deriving it). Does declaring it shift where the resolver should live?

**Not asked / explicitly held:** the live re-capture still waits for a real dogfood moment AND a settled hook-deployment state (pipeline is mid Phase 32/34 — bridge-scriptable substrate confirmed up, ontology confirmed byte-stable, no re-ground needed). No capture is gated on this surfacing.

---

## Room verdict (Orch + Creative redline folded, 2026-06-05)

Full passes: `CONTEXT-PRESSURE-INSTRUMENT-FEDERATION-ORCH.md` · `CONTEXT-PRESSURE-INSTRUMENT-FEDERATION-CREATIVE.md`.

**On DT's 3 positions:** (1) no-rescope — **both ENDORSE unconditionally.** (2) resolver-emits-`ReferenceResolution` — **both ENDORSE, sharpened:** the win isn't "migration thrift / costs nothing" (DT undersold *and* overclaimed — the `ambiguous` arm is unmeasured, so it's cheap-not-free); the real win (Creative) is the contract makes `unresolved`/`ambiguous` first-class siblings of `resolved`, structurally forcing honest-decline away from a `{resolved: bool, value}` shape. (3) op→type-as-declared-metadata — **ENDORSE direction; both CONTEST it as a blanket:** §2.4 heterogeneity means only the *nominal* `isinstance` guards (the dominant PySequence-rename class) declare faithfully; duck-typed/cardinality guards flatten lossily. Land it as **"nominal declared; heterogeneous stays in the hook until the contract can express predicates."** (Orch's "predicate descriptor, not type name" and Creative's framing are the same finding from two angles.)

**Two DT grounding misses, verified against code and corrected above:** the S4↔contract table was not 1:1 (no `ambiguous`/`candidates` path exists in `_analysis.py`); the Phase 5 dependency was inflated (Phase 5 = capability-family routing, not referent resolution).

**Orch asks resolved:** re-cast the close at the **legibility layer, not the obligation layer** (make it readable to Phase 7; do NOT bind Phase X to contract conformance — its native success criterion stays the Q3 delta). **Do NOT re-rank sequencing** — measure-first stays the only gate; the federation read raises only the *payoff if BUILD fires* (one resolver, two consumers), recorded strictly downstream of the gate.

**Creative asks resolved:** (a) disambiguation — **record the `ambiguous`+`candidates` signal from day one** (free, and a measurement hole if collapsed into `unresolved`); **defer the interactive picker** (gated on measured frequency). The honest decline ("2 match — pick one") IS the first-resolver disambiguation surface; ratify-CAUGHT makes deferral safe. (b) the resolver lives in **bridge** (orchestration → ADR-000 Rule 3; honest decline must be local/fast); guard *evaluation* splits by style — bridge evaluates nominal guards from declared metadata, emits `unresolved`+`reason_code="unreconstructable_guard"` for guards it can't reconstruct rather than relocate or flatten-guess.

**Creative's sharpest catch (new work, not in DT's pass):** `reason_code` and `message` are **separate fields by design** (`references.py:41-42`). A populated `reason_code` with `message=None` satisfies the contract and fails the artist — "chat returns dispatch envelopes, not human answers" (the v1.9 thesis) recurring one layer down. **`message` is authored content — a deliverable, not a passthrough.** The resolver must ship a door ("pick one, or name it"), not a wall with a status code on it. *The contract gives the shape of honest decline; it does not give the decline — and the decline is the experience.*
