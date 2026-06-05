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

Our S4 analysis is this contract under another name. The map is exact:

| Phase X / capture-model (`_analysis.py`) | `ReferenceResolution` |
|---|---|
| S4 success (correct referent) | `status="resolved"` + `locations` |
| `failure_class="wrong_referent"` | `status="resolved"` but wrong — the ratify-caught case |
| `failure_class="unresolved_reference"` | `status="unresolved"` |
| ≥2 selections, can't disambiguate | `status="ambiguous"` + `candidates` |
| `unreachable_api` / `unreconstructable_guard` | `reason_code` (our honest-absence pattern) |

The §2.3 op→(context, required-selection-type) map is the bridge-side *knowledge that produces* a `ReferenceResolution`. So Phase X is, unframed, **the measurement pass for bridge's reference-resolution quality** — same concern as the contract, one altitude down.

## Why this is load-bearing, not trivia — the bottleneck

Federation Proof Sequence: Phase 2 Vision ✅, Phase 3 Pipeline ✅, Phase 4 contract-stability ✅ (v0.1 stable), Phase 6 Generators in flight. **Phase 5 (Bridge Discovery) and Phase 7 (E2E Demonstrator) — the ecosystem payoff — gate on bridge orchestrating**: discover siblings → plan by declared capability → invoke Vision/Pipeline/Generators → record lineage. Bridge cannot plan-and-invoke until it resolves the artist's references into the identifiers siblings need. The siblings run standalone today; **composition *through* bridge is blocked on our reference-resolution maturity** — the v1.7→v1.13→Phase X grind. Chat working ⊃ references resolving ⊃ Phase 5/7 unblocked. The federation has been waiting on this seam.

## DT positions (strong, for redline)

1. **Do NOT re-scope Phase X.** The measure-first discipline and the blind Q3 threshold stand untouched. This is a vocabulary alignment, not a new mission (ruling iii holds). The instrument was correct; we now know its output has a name and a second consumer.
2. **If Q3's R clears BUILD, the resolver emits `ReferenceResolution`** — the shipped contract — not a bridge-internal shape. Recorded as §8 of the capture-model spec. This costs us nothing now and saves a parallel-vocabulary migration later.
3. **The §2.3 op→type map should become pipeline-declared capability metadata** (extending `CapabilityDeclaration`), consumed by bridge — not reverse-engineered from hook source. Our current derivation-by-reading-`forge_tools` is an ADR-000 boundary violation we should name as interim, not entrench. The output contract exists; the missing half is pipeline *declaring* "forge_rename requires a selected PySequence."

## Asks

**→ Orch (synthesis).** Does the `ReferenceResolution` mapping change how we frame the milestone — do we re-cast Phase X's close as "reference-resolution measurement pass" explicitly, so the federation read is legible to Phase 5/7? And does the bottleneck re-rank our sequencing — does the federation-level consumer raise the priority of the live re-capture + resolver-build relative to other bridge work, or is measure-first still the only gate that matters and urgency stays out of it?

**→ Creative (experience).** Two things land in your lane. (a) The contract's `ambiguous` + `candidates[]` path is an *experience affordance* — when "this sequence" matches ≥2 selections, do we design the disambiguation surface now (candidates offered to the operator) or defer it past the first resolver? (b) The op→type-as-capability-metadata move is partly yours — it's the federation-clean form of your hooks-as-ontology read (the hook already *is* the guard; the question is whether pipeline *declares* that guard as metadata vs. bridge re-deriving it). Does declaring it shift where the resolver should live?

**Not asked / explicitly held:** the live re-capture still waits for a real dogfood moment AND a settled hook-deployment state (pipeline is mid Phase 32/34 — bridge-scriptable substrate confirmed up, ontology confirmed byte-stable, no re-ground needed). No capture is gated on this surfacing.
